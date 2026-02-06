"""
QA Test Agent Blueprint - Automated test generation and validation agent.

Generates test cases for agent responses, validates output quality,
runs regression checks, and reports coverage gaps.
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
from .validation_models import (
    CheckRegressionInput,
    GenerateTestsInput,
    ValidateOutputInput,
)


class QATestAgent(BaseAgent):
    """
    Automated QA testing agent for validating agent outputs.

    Workflow:
    1. Analyze the target agent's input/output contract
    2. Generate test cases (happy path, edge cases, adversarial)
    3. Execute test cases and collect results
    4. Validate outputs against expected criteria
    5. Generate coverage report and flag regressions
    """

    TEST_GENERATION_PROMPT = ChatPromptTemplate.from_template(
        "You are a QA engineer generating test cases for an AI agent.\n\n"
        "Agent Name: {agent_name}\n"
        "Agent Description: {agent_description}\n"
        "Sample Input: {sample_input}\n"
        "Sample Output: {sample_output}\n\n"
        "Generate comprehensive test cases in JSON format:\n"
        "{{\n"
        '  "test_cases": [\n'
        "    {{\n"
        '      "id": "TC-001",\n'
        '      "category": "happy_path|edge_case|adversarial|regression",\n'
        '      "name": "descriptive test name",\n'
        '      "input": {{}},\n'
        '      "expected_behavior": "what should happen",\n'
        '      "validation_criteria": ["criterion1", "criterion2"],\n'
        '      "priority": "critical|high|medium|low"\n'
        "    }}\n"
        "  ],\n"
        '  "coverage_areas": ["area1", "area2"],\n'
        '  "total_cases": 0\n'
        "}}"
    )

    VALIDATION_PROMPT = ChatPromptTemplate.from_template(
        "You are a QA engineer validating an AI agent's output.\n\n"
        "Test Case: {test_case}\n"
        "Agent Input: {agent_input}\n"
        "Agent Output: {agent_output}\n"
        "Validation Criteria: {criteria}\n\n"
        "Evaluate the output and provide results in JSON format:\n"
        "{{\n"
        '  "passed": true|false,\n'
        '  "score": 0-100,\n'
        '  "criteria_results": [\n'
        '    {{"criterion": "...", "met": true|false, "notes": "..."}}\n'
        "  ],\n"
        '  "issues": ["issue description"],\n'
        '  "suggestions": ["improvement suggestion"]\n'
        "}}"
    )

    REGRESSION_PROMPT = ChatPromptTemplate.from_template(
        "You are a QA engineer checking for regressions.\n\n"
        "Previous Output: {previous_output}\n"
        "Current Output: {current_output}\n"
        "Test Case: {test_case}\n\n"
        "Compare outputs and check for regressions in JSON format:\n"
        "{{\n"
        '  "has_regression": true|false,\n'
        '  "severity": "critical|high|medium|low|none",\n'
        '  "changes": [\n'
        '    {{"field": "...", "previous": "...", "current": "...", "is_regression": true|false}}\n'
        "  ],\n"
        '  "summary": "brief comparison summary"\n'
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
        self._register_default_tools()

    def _lazy_init(self) -> None:
        if self._initialized:
            return
        if self._llm is None:
            with contextlib.suppress(Exception):
                self._llm = ChatOpenAI(temperature=0.2)
        self._initialized = True

    @property
    def llm(self) -> Any | None:
        self._lazy_init()
        return self._llm

    def _register_default_tools(self) -> None:
        self.register_tool(
            Tool(
                name="generate_tests",
                description="Generate test cases for an agent",
                func=self._generate_tests,
            )
        )
        self.register_tool(
            Tool(
                name="validate_output",
                description="Validate agent output against criteria",
                func=self._validate_output,
            )
        )
        self.register_tool(
            Tool(
                name="check_regression",
                description="Check for regressions between outputs",
                func=self._check_regression,
            )
        )
        self.register_tool(
            Tool(
                name="report_failure",
                description="Report a critical test failure for human review",
                func=self._report_failure,
                requires_approval=True,
            )
        )

    @llm_retry(max_attempts=3)
    async def _generate_tests(
        self,
        agent_name: str,
        agent_description: str,
        sample_input: str = "",
        sample_output: str = "",
    ) -> dict[str, Any]:
        validated = GenerateTestsInput(
            agent_name=agent_name,
            agent_description=agent_description,
            sample_input=sample_input,
            sample_output=sample_output,
        )
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.TEST_GENERATION_PROMPT | self.llm
            result = await chain.ainvoke({
                "agent_name": validated.agent_name,
                "agent_description": validated.agent_description,
                "sample_input": validated.sample_input,
                "sample_output": validated.sample_output,
            })
            timer.set_tokens(input_tokens=200, output_tokens=len(result.content) // 4)
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            return {
                "test_cases": [],
                "coverage_areas": [],
                "total_cases": 0,
                "error": "Failed to parse test generation output",
            }

    @llm_retry(max_attempts=3)
    async def _validate_output(
        self,
        test_case: dict[str, Any],
        agent_input: dict[str, Any],
        agent_output: dict[str, Any],
        criteria: list[str],
    ) -> dict[str, Any]:
        validated = ValidateOutputInput(
            test_case=test_case,
            agent_input=agent_input,
            agent_output=agent_output,
            criteria=criteria,
        )
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.VALIDATION_PROMPT | self.llm
            result = await chain.ainvoke({
                "test_case": json.dumps(validated.test_case),
                "agent_input": json.dumps(validated.agent_input),
                "agent_output": json.dumps(validated.agent_output),
                "criteria": json.dumps(validated.criteria),
            })
            timer.set_tokens(input_tokens=300, output_tokens=len(result.content) // 4)
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            return {
                "passed": False,
                "score": 0,
                "criteria_results": [],
                "issues": ["Validation parse error"],
            }

    @llm_retry(max_attempts=3)
    async def _check_regression(
        self,
        previous_output: dict[str, Any],
        current_output: dict[str, Any],
        test_case: dict[str, Any],
    ) -> dict[str, Any]:
        validated = CheckRegressionInput(
            previous_output=previous_output,
            current_output=current_output,
            test_case=test_case,
        )
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.REGRESSION_PROMPT | self.llm
            result = await chain.ainvoke({
                "previous_output": json.dumps(validated.previous_output),
                "current_output": json.dumps(validated.current_output),
                "test_case": json.dumps(validated.test_case),
            })
            timer.set_tokens(input_tokens=300, output_tokens=len(result.content) // 4)
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            return {
                "has_regression": False,
                "severity": "none",
                "changes": [],
                "summary": "Unable to compare",
            }

    async def _report_failure(
        self, test_id: str, description: str, severity: str, evidence: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "reported": True,
            "test_id": test_id,
            "description": description,
            "severity": severity,
            "evidence": evidence,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def plan(self, state: AgentState) -> dict[str, Any]:
        step = state.current_step

        if step == 0:
            return {
                "action": "generate_tests",
                "action_input": {
                    "agent_name": state.input_data.get("agent_name", "Unknown"),
                    "agent_description": state.input_data.get("agent_description", ""),
                    "sample_input": str(state.input_data.get("sample_input", "")),
                    "sample_output": str(state.input_data.get("sample_output", "")),
                },
            }
        elif step == 1:
            test_data = state.intermediate_steps[-1] if state.intermediate_steps else {}
            test_cases = test_data.get("test_cases", [])
            if test_cases:
                tc = test_cases[0]
                return {
                    "action": "validate_output",
                    "action_input": {
                        "test_case": tc,
                        "agent_input": tc.get("input", {}),
                        "agent_output": state.input_data.get("sample_output", {}),
                        "criteria": tc.get("validation_criteria", []),
                    },
                }
            return {"action": "complete", "action_input": {}}
        elif step == 2:
            validation = state.intermediate_steps[-1] if state.intermediate_steps else {}
            if not validation.get("passed", True) and validation.get("score", 100) < 50:
                return {
                    "action": "report_failure",
                    "action_input": {
                        "test_id": "TC-001",
                        "description": "; ".join(validation.get("issues", ["Test failed"])),
                        "severity": "high",
                        "evidence": validation,
                    },
                    "requires_approval": True,
                }
            return {"action": "complete", "action_input": {}}

        return {"action": "complete", "action_input": {}}

    async def execute_step(self, state: AgentState, action: dict[str, Any]) -> dict[str, Any]:
        action_name = action.get("action")
        action_input = action.get("action_input", {})

        if action_name == "generate_tests":
            result = await self._generate_tests(**action_input)
            return {"action": action_name, **result}
        elif action_name == "validate_output":
            result = await self._validate_output(**action_input)
            state.output_data["validation"] = result
            return {"action": action_name, **result}
        elif action_name == "check_regression":
            result = await self._check_regression(**action_input)
            return {"action": action_name, **result}
        elif action_name == "report_failure":
            result = await self._report_failure(**action_input)
            await track_agent_decision(
                self._evalai_tracer,
                agent_name="qa_test",
                decision_type="report_failure",
                chosen="escalate",
                confidence=90,
                reasoning=action_input.get("description", "")[:200],
            )
            await self.request_human_feedback(
                question="Critical test failure detected. Review required.",
                context=result,
                options=["acknowledge", "investigate", "dismiss"],
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


QATestBlueprint = AgentBlueprint(
    name="qa_test",
    agent_class=QATestAgent,
    description="Automated QA agent for test generation, output validation, and regression detection",
    default_config={
        "max_iterations": 5,
        "timeout_seconds": 120,
        "confidence_threshold": 0.8,
        "require_human_approval": False,
    },
    required_tools=["generate_tests", "validate_output"],
    version="1.0.0",
)
