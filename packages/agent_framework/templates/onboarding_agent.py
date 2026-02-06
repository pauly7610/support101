"""
Onboarding Agent Blueprint - Customer onboarding and setup guidance agent.

Guides new customers through product setup, collects preferences,
configures initial settings, and provides personalized getting-started
recommendations.
"""

import contextlib
import json
from datetime import datetime
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..core.agent_registry import AgentBlueprint
from ..core.base_agent import AgentConfig, AgentState, AgentStatus, BaseAgent, Tool
from ..services.external_api import get_external_api_client
from ..services.llm_helpers import LLMCallTimer, llm_retry, track_agent_decision
from .validation_models import (
    AssessCustomerInput,
    GenerateChecklistInput,
    ProvideGuidanceInput,
    ValidateCompletionInput,
)


class OnboardingAgent(BaseAgent):
    """
    Customer onboarding and setup guidance agent.

    Workflow:
    1. Assess customer profile and needs
    2. Generate personalized setup checklist
    3. Guide through configuration steps
    4. Validate setup completion
    5. Provide getting-started recommendations
    """

    ASSESSMENT_PROMPT = ChatPromptTemplate.from_template(
        "You are a customer onboarding specialist. Assess the new customer's needs.\n\n"
        "Customer Info:\n{customer_info}\n\n"
        "Product/Service: {product}\n\n"
        "Provide an assessment in JSON format:\n"
        "{{\n"
        '  "customer_segment": "enterprise|professional|starter|individual",\n'
        '  "experience_level": "expert|intermediate|beginner",\n'
        '  "primary_use_case": "description",\n'
        '  "estimated_complexity": "high|medium|low",\n'
        '  "recommended_plan": "plan name",\n'
        '  "key_features_needed": ["feature1", "feature2"],\n'
        '  "potential_challenges": ["challenge1"],\n'
        '  "personalization_notes": "notes for tailoring the experience"\n'
        "}}"
    )

    CHECKLIST_PROMPT = ChatPromptTemplate.from_template(
        "You are an onboarding specialist creating a setup checklist.\n\n"
        "Customer Assessment:\n{assessment}\n"
        "Product: {product}\n\n"
        "Generate a personalized onboarding checklist in JSON format:\n"
        "{{\n"
        '  "checklist": [\n'
        "    {{\n"
        '      "step_id": "S1",\n'
        '      "title": "step title",\n'
        '      "description": "what to do",\n'
        '      "category": "account|integration|configuration|training",\n'
        '      "required": true|false,\n'
        '      "estimated_minutes": 5,\n'
        '      "dependencies": [],\n'
        '      "help_article": "relevant help article title or null"\n'
        "    }}\n"
        "  ],\n"
        '  "total_steps": 0,\n'
        '  "estimated_total_minutes": 0,\n'
        '  "priority_order": ["S1", "S2"]\n'
        "}}"
    )

    GUIDANCE_PROMPT = ChatPromptTemplate.from_template(
        "You are a friendly onboarding guide helping a customer with setup.\n\n"
        "Current Step: {step_title}\n"
        "Step Description: {step_description}\n"
        "Customer Level: {experience_level}\n"
        "Customer Question: {question}\n\n"
        "Provide helpful, clear guidance. If the customer is a beginner,\n"
        "be extra detailed. If expert, be concise.\n\n"
        "Respond in JSON format:\n"
        "{{\n"
        '  "guidance": "step-by-step instructions",\n'
        '  "tips": ["helpful tip"],\n'
        '  "common_mistakes": ["mistake to avoid"],\n'
        '  "next_step_preview": "what comes next",\n'
        '  "estimated_time_remaining": "X minutes"\n'
        "}}"
    )

    COMPLETION_PROMPT = ChatPromptTemplate.from_template(
        "You are an onboarding specialist validating setup completion.\n\n"
        "Checklist:\n{checklist}\n"
        "Completed Steps: {completed_steps}\n"
        "Customer Profile:\n{customer_profile}\n\n"
        "Validate completion and provide recommendations in JSON format:\n"
        "{{\n"
        '  "completion_percentage": 0-100,\n'
        '  "missing_steps": ["step_id"],\n'
        '  "critical_missing": ["step_id that must be done"],\n'
        '  "ready_to_use": true|false,\n'
        '  "getting_started_tips": [\n'
        '    {{"tip": "...", "priority": "high|medium|low"}}\n'
        "  ],\n"
        '  "recommended_next_actions": ["action1"],\n'
        '  "personalized_resources": ["resource link or title"]\n'
        "}}"
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
        self._api = get_external_api_client()
        self._register_default_tools()

    def _lazy_init(self) -> None:
        if self._initialized:
            return
        if self._llm is None:
            with contextlib.suppress(Exception):
                self._llm = ChatOpenAI(temperature=0.3)
        self._initialized = True

    @property
    def llm(self) -> Any | None:
        self._lazy_init()
        return self._llm

    def _register_default_tools(self) -> None:
        self.register_tool(
            Tool(
                name="assess_customer",
                description="Assess new customer profile and needs",
                func=self._assess_customer,
            )
        )
        self.register_tool(
            Tool(
                name="generate_checklist",
                description="Generate personalized onboarding checklist",
                func=self._generate_checklist,
            )
        )
        self.register_tool(
            Tool(
                name="provide_guidance",
                description="Provide step-by-step guidance for a setup step",
                func=self._provide_guidance,
            )
        )
        self.register_tool(
            Tool(
                name="validate_completion",
                description="Validate onboarding completion and recommend next steps",
                func=self._validate_completion,
            )
        )
        self.register_tool(
            Tool(
                name="request_setup_help",
                description="Request human assistance for complex setup issues",
                func=self._request_setup_help,
                requires_approval=True,
            )
        )

    @llm_retry(max_attempts=3)
    async def _assess_customer(
        self, customer_info: dict[str, Any], product: str = ""
    ) -> dict[str, Any]:
        validated = AssessCustomerInput(customer_info=customer_info, product=product)
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.ASSESSMENT_PROMPT | self.llm
            result = await chain.ainvoke(
                {
                    "customer_info": json.dumps(validated.customer_info, indent=2),
                    "product": validated.product,
                }
            )
            timer.set_tokens(input_tokens=200, output_tokens=len(result.content) // 4)
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            return {
                "customer_segment": "starter",
                "experience_level": "beginner",
                "primary_use_case": "general",
                "estimated_complexity": "medium",
                "recommended_plan": "starter",
                "key_features_needed": [],
                "potential_challenges": [],
                "personalization_notes": "",
            }

    @llm_retry(max_attempts=3)
    async def _generate_checklist(
        self, assessment: dict[str, Any], product: str = ""
    ) -> dict[str, Any]:
        validated = GenerateChecklistInput(assessment=assessment, product=product)
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.CHECKLIST_PROMPT | self.llm
            result = await chain.ainvoke(
                {
                    "assessment": json.dumps(validated.assessment, indent=2),
                    "product": validated.product,
                }
            )
            timer.set_tokens(input_tokens=200, output_tokens=len(result.content) // 4)
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            return {
                "checklist": [],
                "total_steps": 0,
                "estimated_total_minutes": 0,
                "priority_order": [],
            }

    @llm_retry(max_attempts=3)
    async def _provide_guidance(
        self,
        step_title: str,
        step_description: str,
        experience_level: str = "beginner",
        question: str = "",
    ) -> dict[str, Any]:
        validated = ProvideGuidanceInput(
            step_title=step_title,
            step_description=step_description,
            experience_level=experience_level,
            question=question,
        )
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.GUIDANCE_PROMPT | self.llm
            result = await chain.ainvoke(
                {
                    "step_title": validated.step_title,
                    "step_description": validated.step_description,
                    "experience_level": validated.experience_level,
                    "question": validated.question or "How do I complete this step?",
                }
            )
            timer.set_tokens(input_tokens=200, output_tokens=len(result.content) // 4)
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            return {
                "guidance": result.content[:500],
                "tips": [],
                "common_mistakes": [],
                "next_step_preview": "",
                "estimated_time_remaining": "unknown",
            }

    @llm_retry(max_attempts=3)
    async def _validate_completion(
        self,
        checklist: list[dict[str, Any]],
        completed_steps: list[str],
        customer_profile: dict[str, Any],
    ) -> dict[str, Any]:
        validated = ValidateCompletionInput(
            checklist=checklist,
            completed_steps=completed_steps,
            customer_profile=customer_profile,
        )
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.COMPLETION_PROMPT | self.llm
            result = await chain.ainvoke(
                {
                    "checklist": json.dumps(validated.checklist, indent=2),
                    "completed_steps": json.dumps(validated.completed_steps),
                    "customer_profile": json.dumps(validated.customer_profile, indent=2),
                }
            )
            timer.set_tokens(input_tokens=300, output_tokens=len(result.content) // 4)
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            return {
                "completion_percentage": 0,
                "missing_steps": [],
                "critical_missing": [],
                "ready_to_use": False,
                "getting_started_tips": [],
                "recommended_next_actions": [],
                "personalized_resources": [],
            }

    async def _request_setup_help(
        self, issue: str, step_id: str, customer_info: dict[str, Any]
    ) -> dict[str, Any]:
        await self._api.send_notification(
            channel="onboarding",
            message=f"Setup help needed: {issue}",
            urgency="normal",
            metadata={"step_id": step_id, "agent_id": self.agent_id},
        )
        await track_agent_decision(
            self._evalai_tracer,
            agent_name="onboarding",
            decision_type="request_help",
            chosen="human_assist",
            confidence=70,
            reasoning=f"Customer needs help with step {step_id}: {issue[:100]}",
        )
        return {
            "help_requested": True,
            "issue": issue,
            "step_id": step_id,
            "customer_info": customer_info,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def plan(self, state: AgentState) -> dict[str, Any]:
        step = state.current_step

        if step == 0:
            return {
                "action": "assess_customer",
                "action_input": {
                    "customer_info": state.input_data.get("customer_info", {}),
                    "product": state.input_data.get("product", ""),
                },
            }
        elif step == 1:
            assessment = state.intermediate_steps[-1] if state.intermediate_steps else {}
            return {
                "action": "generate_checklist",
                "action_input": {
                    "assessment": assessment,
                    "product": state.input_data.get("product", ""),
                },
            }
        elif step == 2:
            completed = state.input_data.get("completed_steps", [])
            checklist_data = (
                state.intermediate_steps[-1] if len(state.intermediate_steps) > 1 else {}
            )
            checklist = checklist_data.get("checklist", [])
            assessment = state.intermediate_steps[0] if state.intermediate_steps else {}
            return {
                "action": "validate_completion",
                "action_input": {
                    "checklist": checklist,
                    "completed_steps": completed,
                    "customer_profile": assessment,
                },
            }

        return {"action": "complete", "action_input": {}}

    async def execute_step(self, state: AgentState, action: dict[str, Any]) -> dict[str, Any]:
        action_name = action.get("action")
        action_input = action.get("action_input", {})

        if action_name == "assess_customer":
            result = await self._assess_customer(
                action_input.get("customer_info", {}),
                action_input.get("product", ""),
            )
            state.output_data["assessment"] = result
            return {"action": action_name, **result}
        elif action_name == "generate_checklist":
            result = await self._generate_checklist(
                action_input.get("assessment", {}),
                action_input.get("product", ""),
            )
            state.output_data["checklist"] = result
            return {"action": action_name, **result}
        elif action_name == "provide_guidance":
            result = await self._provide_guidance(**action_input)
            return {"action": action_name, **result}
        elif action_name == "validate_completion":
            result = await self._validate_completion(
                action_input.get("checklist", []),
                action_input.get("completed_steps", []),
                action_input.get("customer_profile", {}),
            )
            state.output_data["completion"] = result
            return {"action": action_name, **result}
        elif action_name == "request_setup_help":
            result = await self._request_setup_help(**action_input)
            await self.request_human_feedback(
                question="Customer needs setup assistance",
                context=result,
                options=["assist_now", "schedule_call", "send_guide"],
            )
            return {"action": action_name, **result}
        elif action_name == "complete":
            return {"action": "complete", "completed": True}

        return {"action": action_name, "error": "Unknown action"}

    def should_continue(self, state: AgentState) -> bool:
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


OnboardingBlueprint = AgentBlueprint(
    name="onboarding",
    agent_class=OnboardingAgent,
    description="Customer onboarding agent with personalized setup checklists and guided configuration",
    default_config={
        "max_iterations": 5,
        "timeout_seconds": 60,
        "confidence_threshold": 0.7,
        "require_human_approval": False,
    },
    required_tools=["assess_customer", "generate_checklist", "validate_completion"],
    version="1.0.0",
)
