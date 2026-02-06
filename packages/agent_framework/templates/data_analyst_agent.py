"""
Data Analyst Agent Blueprint - LLM-powered data analysis and reporting agent.

Analyzes structured and unstructured data, generates insights,
creates summaries, and produces actionable recommendations.
"""

import contextlib
import json
from datetime import datetime
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..core.agent_registry import AgentBlueprint
from ..core.base_agent import AgentConfig, AgentState, AgentStatus, BaseAgent, Tool
from ..services.llm_helpers import LLMCallTimer, llm_retry, track_agent_decision
from .validation_models import AnalyzeDataInput, GenerateInsightsInput, QueryDataInput


class DataAnalystAgent(BaseAgent):
    """
    LLM-powered data analysis agent.

    Workflow:
    1. Parse and validate input data
    2. Identify patterns and anomalies
    3. Generate statistical summary
    4. Produce actionable insights and recommendations
    5. Request human review for high-impact findings
    """

    ANALYSIS_PROMPT = ChatPromptTemplate.from_template(
        "You are a senior data analyst. Analyze the following dataset and provide insights.\n\n"
        "Data Description: {description}\n"
        "Data Sample:\n{data_sample}\n"
        "Analysis Type: {analysis_type}\n\n"
        "Provide analysis in JSON format:\n"
        "{{\n"
        '  "summary": "brief overview of the data",\n'
        '  "key_metrics": {{"metric_name": "value"}},\n'
        '  "patterns": ["pattern1", "pattern2"],\n'
        '  "anomalies": ["anomaly1"],\n'
        '  "trends": ["trend1", "trend2"],\n'
        '  "data_quality_score": 0.0-1.0,\n'
        '  "confidence": 0-100\n'
        "}}"
    )

    INSIGHT_PROMPT = ChatPromptTemplate.from_template(
        "You are a senior data analyst. Based on the following analysis results,\n"
        "generate actionable insights and recommendations.\n\n"
        "Analysis Results:\n{analysis}\n\n"
        "Business Context: {context}\n\n"
        "Provide insights in JSON format:\n"
        "{{\n"
        '  "insights": [\n'
        '    {{"finding": "...", "impact": "high|medium|low", "confidence": 0-100, '
        '"recommendation": "..."}}\n'
        "  ],\n"
        '  "executive_summary": "2-3 sentence summary for leadership",\n'
        '  "next_steps": ["step1", "step2"],\n'
        '  "risks": ["risk1"]\n'
        "}}"
    )

    QUERY_PROMPT = ChatPromptTemplate.from_template(
        "You are a data analyst assistant. Answer the following question about the data.\n\n"
        "Data Context:\n{data_context}\n\n"
        "Previous Analysis:\n{previous_analysis}\n\n"
        "Question: {question}\n\n"
        "Provide a clear, data-driven answer with supporting evidence."
    )

    def __init__(
        self,
        config: AgentConfig,
        llm: Any | None = None,
        evalai_tracer: Any | None = None,
    ) -> None:
        super().__init__(config)
        self._llm = llm
        self._evalai_tracer = evalai_tracer
        self._initialized = False
        self._register_default_tools()

    def _lazy_init(self) -> None:
        """Lazy initialization of LLM dependencies."""
        if self._initialized:
            return
        if self._llm is None:
            with contextlib.suppress(Exception):
                self._llm = ChatOpenAI(temperature=0.2)
        self._initialized = True

    @property
    def llm(self) -> Any | None:
        """Get LLM, initializing if needed."""
        self._lazy_init()
        return self._llm

    def _register_default_tools(self) -> None:
        """Register default tools for data analysis operations."""
        self.register_tool(
            Tool(
                name="analyze_data",
                description="Analyze a dataset and extract patterns, anomalies, and metrics",
                func=self._analyze_data,
            )
        )
        self.register_tool(
            Tool(
                name="generate_insights",
                description="Generate actionable insights from analysis results",
                func=self._generate_insights,
            )
        )
        self.register_tool(
            Tool(
                name="query_data",
                description="Answer a specific question about the data",
                func=self._query_data,
            )
        )
        self.register_tool(
            Tool(
                name="flag_for_review",
                description="Flag high-impact findings for human review",
                func=self._flag_for_review,
                requires_approval=True,
            )
        )

    @llm_retry(max_attempts=3)
    async def _analyze_data(
        self,
        data_sample: str,
        description: str = "",
        analysis_type: str = "exploratory",
    ) -> dict[str, Any]:
        """Analyze data using LLM."""
        validated = AnalyzeDataInput(
            data_sample=data_sample,
            description=description,
            analysis_type=analysis_type,
        )
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.ANALYSIS_PROMPT | self.llm
            result = await chain.ainvoke({
                "data_sample": validated.data_sample[:3000],
                "description": validated.description,
                "analysis_type": validated.analysis_type,
            })
            timer.set_tokens(
                input_tokens=len(validated.data_sample) // 4,
                output_tokens=len(result.content) // 4,
            )
        try:
            analysis = json.loads(result.content)
        except json.JSONDecodeError:
            analysis = {
                "summary": result.content[:500],
                "key_metrics": {},
                "patterns": [],
                "anomalies": [],
                "trends": [],
                "data_quality_score": 0.5,
                "confidence": 50,
            }
        return analysis

    @llm_retry(max_attempts=3)
    async def _generate_insights(
        self,
        analysis: dict[str, Any],
        context: str = "",
    ) -> dict[str, Any]:
        """Generate insights from analysis results."""
        validated = GenerateInsightsInput(analysis=analysis, context=context)
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.INSIGHT_PROMPT | self.llm
            result = await chain.ainvoke({
                "analysis": json.dumps(validated.analysis, indent=2),
                "context": validated.context or "General business analysis",
            })
            timer.set_tokens(input_tokens=200, output_tokens=len(result.content) // 4)
        try:
            insights = json.loads(result.content)
        except json.JSONDecodeError:
            insights = {
                "insights": [
                    {
                        "finding": result.content[:300],
                        "impact": "medium",
                        "confidence": 50,
                        "recommendation": "Review raw analysis data",
                    }
                ],
                "executive_summary": "Analysis completed. Review insights for details.",
                "next_steps": ["Review detailed analysis"],
                "risks": [],
            }
        return insights

    @llm_retry(max_attempts=3)
    async def _query_data(
        self,
        question: str,
        data_context: str = "",
        previous_analysis: str = "",
    ) -> dict[str, Any]:
        """Answer a question about the data."""
        validated = QueryDataInput(
            question=question,
            data_context=data_context,
            previous_analysis=previous_analysis,
        )
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.QUERY_PROMPT | self.llm
            result = await chain.ainvoke({
                "question": validated.question,
                "data_context": validated.data_context,
                "previous_analysis": validated.previous_analysis,
            })
            timer.set_tokens(
                input_tokens=len(validated.question) // 4,
                output_tokens=len(result.content) // 4,
            )
        return {
            "question": question,
            "answer": result.content,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _flag_for_review(
        self,
        finding: str,
        impact: str,
        evidence: dict[str, Any],
    ) -> dict[str, Any]:
        """Flag a finding for human review."""
        return {
            "flagged": True,
            "finding": finding,
            "impact": impact,
            "evidence": evidence,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def plan(self, state: AgentState) -> dict[str, Any]:
        """Determine next analysis action based on current state."""
        step = state.current_step

        if step == 0:
            return {
                "action": "analyze_data",
                "action_input": {
                    "data_sample": str(state.input_data.get("data", ""))[:3000],
                    "description": state.input_data.get("description", ""),
                    "analysis_type": state.input_data.get("analysis_type", "exploratory"),
                },
            }
        elif step == 1:
            analysis = state.intermediate_steps[-1] if state.intermediate_steps else {}
            return {
                "action": "generate_insights",
                "action_input": {
                    "analysis": analysis,
                    "context": state.input_data.get("business_context", ""),
                },
            }
        elif step == 2:
            insights = state.intermediate_steps[-1] if state.intermediate_steps else {}
            high_impact = [i for i in insights.get("insights", []) if i.get("impact") == "high"]
            if high_impact:
                return {
                    "action": "flag_for_review",
                    "action_input": {
                        "finding": high_impact[0].get("finding", ""),
                        "impact": "high",
                        "evidence": high_impact[0],
                    },
                    "requires_approval": True,
                }
            return {"action": "complete", "action_input": {}}
        elif step == 3:
            question = state.input_data.get("question")
            if question:
                prev_analysis = (
                    json.dumps(state.intermediate_steps[0]) if state.intermediate_steps else ""
                )
                return {
                    "action": "query_data",
                    "action_input": {
                        "question": question,
                        "data_context": str(state.input_data.get("data", ""))[:1000],
                        "previous_analysis": prev_analysis[:1000],
                    },
                }
            return {"action": "complete", "action_input": {}}

        return {"action": "complete", "action_input": {}}

    async def execute_step(self, state: AgentState, action: dict[str, Any]) -> dict[str, Any]:
        """Execute a single analysis step."""
        action_name = action.get("action")
        action_input = action.get("action_input", {})

        if action_name == "analyze_data":
            result = await self._analyze_data(
                data_sample=action_input.get("data_sample", ""),
                description=action_input.get("description", ""),
                analysis_type=action_input.get("analysis_type", "exploratory"),
            )
            return {"action": action_name, **result}

        elif action_name == "generate_insights":
            result = await self._generate_insights(
                analysis=action_input.get("analysis", {}),
                context=action_input.get("context", ""),
            )
            state.output_data["insights"] = result
            return {"action": action_name, **result}

        elif action_name == "query_data":
            result = await self._query_data(
                question=action_input.get("question", ""),
                data_context=action_input.get("data_context", ""),
                previous_analysis=action_input.get("previous_analysis", ""),
            )
            state.output_data["query_result"] = result
            return {"action": action_name, **result}

        elif action_name == "flag_for_review":
            result = await self._flag_for_review(
                finding=action_input.get("finding", ""),
                impact=action_input.get("impact", "medium"),
                evidence=action_input.get("evidence", {}),
            )
            await track_agent_decision(
                self._evalai_tracer,
                agent_name="data_analyst",
                decision_type="flag",
                chosen="human_review",
                confidence=90,
                reasoning=f"High-impact finding: {action_input.get('finding', '')[:100]}",
            )
            await self.request_human_feedback(
                question="Review high-impact data finding",
                context=result,
                options=["acknowledge", "investigate_further", "dismiss"],
            )
            return {"action": action_name, **result}

        elif action_name == "complete":
            return {"action": "complete", "completed": True}

        return {"action": action_name, "error": "Unknown action"}

    def should_continue(self, state: AgentState) -> bool:
        """Check if analysis should continue."""
        if state.current_step >= self.config.max_iterations:
            return False
        if state.status in [
            AgentStatus.COMPLETED,
            AgentStatus.FAILED,
            AgentStatus.AWAITING_HUMAN,
        ]:
            return False
        return not (
            state.intermediate_steps and state.intermediate_steps[-1].get("action") == "complete"
        )


DataAnalystBlueprint = AgentBlueprint(
    name="data_analyst",
    agent_class=DataAnalystAgent,
    description="LLM-powered data analysis agent with pattern detection, insights, and reporting",
    default_config={
        "max_iterations": 5,
        "timeout_seconds": 120,
        "confidence_threshold": 0.7,
        "require_human_approval": False,
    },
    required_tools=["analyze_data", "generate_insights"],
    version="1.0.0",
)
