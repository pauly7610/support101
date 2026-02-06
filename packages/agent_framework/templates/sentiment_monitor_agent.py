"""
Sentiment Monitor Agent Blueprint - Real-time customer sentiment tracking agent.

Monitors customer interactions for sentiment shifts, detects frustration
and urgency signals, triggers escalation when thresholds are breached,
and generates sentiment trend reports.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..core.agent_registry import AgentBlueprint
from ..core.base_agent import AgentConfig, AgentState, AgentStatus, BaseAgent, Tool
from ..services.external_api import get_external_api_client
from ..services.llm_helpers import LLMCallTimer, llm_retry, track_agent_decision
from .validation_models import AnalyzeSentimentInput, TrackTrajectoryInput, TriggerEscalationInput


class SentimentMonitorAgent(BaseAgent):
    """
    Real-time customer sentiment monitoring agent.

    Workflow:
    1. Analyze message sentiment and emotional signals
    2. Track sentiment trajectory across conversation
    3. Detect frustration, urgency, and churn risk indicators
    4. Trigger escalation for negative sentiment breaches
    5. Generate sentiment summary with recommendations
    """

    SENTIMENT_PROMPT = ChatPromptTemplate.from_template(
        "You are a sentiment analysis specialist. Analyze the following customer message.\n\n"
        "Message: {message}\n"
        "Conversation History:\n{history}\n\n"
        "Provide detailed sentiment analysis in JSON format:\n"
        "{{\n"
        '  "sentiment": "very_positive|positive|neutral|negative|very_negative",\n'
        '  "sentiment_score": -1.0 to 1.0,\n'
        '  "emotions": [\n'
        '    {{"emotion": "frustration|anger|confusion|satisfaction|gratitude|anxiety|impatience",'
        ' "intensity": 0-100}}\n'
        "  ],\n"
        '  "urgency": "critical|high|medium|low",\n'
        '  "churn_risk": "high|medium|low",\n'
        '  "key_phrases": ["phrase indicating sentiment"],\n'
        '  "escalation_recommended": true|false,\n'
        '  "escalation_reason": "reason or null"\n'
        "}}"
    )

    TRAJECTORY_PROMPT = ChatPromptTemplate.from_template(
        "You are a sentiment trend analyst. Analyze the sentiment trajectory.\n\n"
        "Sentiment History (oldest to newest):\n{sentiment_history}\n\n"
        "Analyze the trajectory in JSON format:\n"
        "{{\n"
        '  "trend": "improving|stable|declining|volatile",\n'
        '  "trend_score": -1.0 to 1.0,\n'
        '  "turning_points": [\n'
        '    {{"message_index": 0, "from": "neutral", "to": "negative", "trigger": "..."}}\n'
        "  ],\n"
        '  "risk_level": "critical|high|medium|low",\n'
        '  "predicted_next": "positive|neutral|negative",\n'
        '  "intervention_needed": true|false,\n'
        '  "recommended_action": "description of recommended action"\n'
        "}}"
    )

    SUMMARY_PROMPT = ChatPromptTemplate.from_template(
        "You are a customer experience analyst. Summarize the sentiment analysis.\n\n"
        "Current Sentiment: {current_sentiment}\n"
        "Trajectory Analysis: {trajectory}\n"
        "Customer Context: {customer_context}\n\n"
        "Provide a summary in JSON format:\n"
        "{{\n"
        '  "overall_assessment": "brief assessment",\n'
        '  "satisfaction_score": 0-100,\n'
        '  "key_concerns": ["concern1"],\n'
        '  "positive_signals": ["signal1"],\n'
        '  "recommendations": [\n'
        '    {{"action": "...", "priority": "high|medium|low", "expected_impact": "..."}}\n'
        "  ],\n"
        '  "follow_up_needed": true|false\n'
        "}}"
    )

    ESCALATION_THRESHOLDS = {
        "sentiment_score": -0.5,
        "frustration_intensity": 70,
        "anger_intensity": 60,
        "consecutive_negative": 3,
    }

    def __init__(
        self,
        config: AgentConfig,
        llm: Optional[Any] = None,
        evalai_tracer: Optional[Any] = None,
    ) -> None:
        super().__init__(config)
        self._llm = llm
        self._evalai_tracer = evalai_tracer
        self._initialized = False
        self._sentiment_history: List[Dict[str, Any]] = []
        self._api = get_external_api_client()
        self._register_default_tools()

    def _lazy_init(self) -> None:
        if self._initialized:
            return
        if self._llm is None:
            try:
                self._llm = ChatOpenAI(temperature=0.1)
            except Exception:
                pass
        self._initialized = True

    @property
    def llm(self) -> Optional[Any]:
        self._lazy_init()
        return self._llm

    def _register_default_tools(self) -> None:
        self.register_tool(
            Tool(
                name="analyze_sentiment",
                description="Analyze sentiment of a customer message",
                func=self._analyze_sentiment,
            )
        )
        self.register_tool(
            Tool(
                name="track_trajectory",
                description="Analyze sentiment trajectory over conversation",
                func=self._track_trajectory,
            )
        )
        self.register_tool(
            Tool(
                name="generate_summary",
                description="Generate sentiment summary with recommendations",
                func=self._generate_summary,
            )
        )
        self.register_tool(
            Tool(
                name="trigger_escalation",
                description="Trigger escalation due to negative sentiment",
                func=self._trigger_escalation,
                requires_approval=True,
            )
        )

    @llm_retry(max_attempts=3)
    async def _analyze_sentiment(
        self, message: str, history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        validated = AnalyzeSentimentInput(message=message, history=history)
        history_str = "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}" for m in validated.history[-10:]
        ) if validated.history else "No previous messages"

        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.SENTIMENT_PROMPT | self.llm
            result = await chain.ainvoke({"message": validated.message, "history": history_str})
            timer.set_tokens(input_tokens=len(validated.message) // 4, output_tokens=len(result.content) // 4)
        try:
            analysis = json.loads(result.content)
        except json.JSONDecodeError:
            analysis = {
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "emotions": [],
                "urgency": "medium",
                "churn_risk": "low",
                "key_phrases": [],
                "escalation_recommended": False,
                "escalation_reason": None,
            }

        self._sentiment_history.append(analysis)
        return analysis

    @llm_retry(max_attempts=3)
    async def _track_trajectory(
        self, sentiment_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        validated = TrackTrajectoryInput(sentiment_history=sentiment_history)
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.TRAJECTORY_PROMPT | self.llm
            result = await chain.ainvoke({
                "sentiment_history": json.dumps(validated.sentiment_history, indent=2),
            })
            timer.set_tokens(input_tokens=300, output_tokens=len(result.content) // 4)
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            return {
                "trend": "stable",
                "trend_score": 0.0,
                "turning_points": [],
                "risk_level": "low",
                "predicted_next": "neutral",
                "intervention_needed": False,
                "recommended_action": "Continue monitoring",
            }

    @llm_retry(max_attempts=3)
    async def _generate_summary(
        self,
        current_sentiment: Dict[str, Any],
        trajectory: Dict[str, Any],
        customer_context: str = "",
    ) -> Dict[str, Any]:
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.SUMMARY_PROMPT | self.llm
            result = await chain.ainvoke({
                "current_sentiment": json.dumps(current_sentiment),
                "trajectory": json.dumps(trajectory),
                "customer_context": customer_context or "No additional context",
            })
            timer.set_tokens(input_tokens=300, output_tokens=len(result.content) // 4)
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            return {
                "overall_assessment": "Unable to generate summary",
                "satisfaction_score": 50,
                "key_concerns": [],
                "positive_signals": [],
                "recommendations": [],
                "follow_up_needed": False,
            }

    async def _trigger_escalation(
        self, reason: str, sentiment_data: Dict[str, Any], urgency: str
    ) -> Dict[str, Any]:
        validated = TriggerEscalationInput(
            reason=reason, sentiment_data=sentiment_data, urgency=urgency
        )
        await self._api.send_notification(
            channel="escalations",
            message=f"Sentiment escalation: {validated.reason}",
            urgency=validated.urgency,
            metadata={"agent_id": self.agent_id, "tenant_id": self.tenant_id},
        )
        await track_agent_decision(
            self._evalai_tracer,
            agent_name="sentiment_monitor",
            decision_type="escalate",
            chosen="trigger_escalation",
            confidence=85,
            reasoning=validated.reason[:200],
        )
        return {
            "escalated": True,
            "reason": validated.reason,
            "urgency": validated.urgency,
            "sentiment_data": validated.sentiment_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def _check_escalation_needed(self, sentiment: Dict[str, Any]) -> bool:
        score = sentiment.get("sentiment_score", 0)
        if score < self.ESCALATION_THRESHOLDS["sentiment_score"]:
            return True

        for emotion in sentiment.get("emotions", []):
            name = emotion.get("emotion", "")
            intensity = emotion.get("intensity", 0)
            if name == "frustration" and intensity > self.ESCALATION_THRESHOLDS["frustration_intensity"]:
                return True
            if name == "anger" and intensity > self.ESCALATION_THRESHOLDS["anger_intensity"]:
                return True

        if sentiment.get("escalation_recommended"):
            return True

        return False

    async def plan(self, state: AgentState) -> Dict[str, Any]:
        step = state.current_step

        if step == 0:
            messages = state.input_data.get("messages", [])
            current_msg = messages[-1].get("content", "") if messages else state.input_data.get("message", "")
            return {
                "action": "analyze_sentiment",
                "action_input": {
                    "message": current_msg,
                    "history": messages[:-1] if len(messages) > 1 else [],
                },
            }
        elif step == 1:
            sentiment = state.intermediate_steps[-1] if state.intermediate_steps else {}
            if self._check_escalation_needed(sentiment):
                return {
                    "action": "trigger_escalation",
                    "action_input": {
                        "reason": sentiment.get("escalation_reason", "Negative sentiment detected"),
                        "sentiment_data": sentiment,
                        "urgency": sentiment.get("urgency", "high"),
                    },
                    "requires_approval": True,
                }
            return {
                "action": "track_trajectory",
                "action_input": {"sentiment_history": self._sentiment_history},
            }
        elif step == 2:
            sentiment = state.intermediate_steps[0] if state.intermediate_steps else {}
            trajectory = state.intermediate_steps[-1] if len(state.intermediate_steps) > 1 else {}
            return {
                "action": "generate_summary",
                "action_input": {
                    "current_sentiment": sentiment,
                    "trajectory": trajectory,
                    "customer_context": state.input_data.get("customer_context", ""),
                },
            }

        return {"action": "complete", "action_input": {}}

    async def execute_step(self, state: AgentState, action: Dict[str, Any]) -> Dict[str, Any]:
        action_name = action.get("action")
        action_input = action.get("action_input", {})

        if action_name == "analyze_sentiment":
            result = await self._analyze_sentiment(
                action_input.get("message", ""),
                action_input.get("history", []),
            )
            return {"action": action_name, **result}
        elif action_name == "track_trajectory":
            result = await self._track_trajectory(action_input.get("sentiment_history", []))
            return {"action": action_name, **result}
        elif action_name == "generate_summary":
            result = await self._generate_summary(
                action_input.get("current_sentiment", {}),
                action_input.get("trajectory", {}),
                action_input.get("customer_context", ""),
            )
            state.output_data["sentiment_summary"] = result
            return {"action": action_name, **result}
        elif action_name == "trigger_escalation":
            result = await self._trigger_escalation(
                action_input.get("reason", ""),
                action_input.get("sentiment_data", {}),
                action_input.get("urgency", "high"),
            )
            state.output_data["escalation"] = result
            await self.request_human_feedback(
                question="Negative sentiment escalation triggered",
                context=result,
                options=["acknowledge", "intervene_now", "monitor"],
            )
            return {"action": action_name, **result}
        elif action_name == "complete":
            return {"action": "complete", "completed": True}

        return {"action": action_name, "error": "Unknown action"}

    def should_continue(self, state: AgentState) -> bool:
        if state.current_step >= self.config.max_iterations:
            return False
        if state.status in [AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.AWAITING_HUMAN]:
            return False
        if state.intermediate_steps and state.intermediate_steps[-1].get("action") == "complete":
            return False
        return True


SentimentMonitorBlueprint = AgentBlueprint(
    name="sentiment_monitor",
    agent_class=SentimentMonitorAgent,
    description="Real-time customer sentiment monitoring with escalation triggers and trend analysis",
    default_config={
        "max_iterations": 4,
        "timeout_seconds": 30,
        "confidence_threshold": 0.7,
        "require_human_approval": False,
    },
    required_tools=["analyze_sentiment", "track_trajectory"],
    version="1.0.0",
)
