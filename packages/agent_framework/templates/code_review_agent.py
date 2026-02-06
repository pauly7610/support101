"""
Code Review Agent Blueprint - LLM-powered automated code review agent.

Analyzes code changes for quality, security vulnerabilities, performance
issues, and best practice adherence. Provides structured feedback with
severity levels and actionable suggestions.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..core.agent_registry import AgentBlueprint
from ..core.base_agent import AgentConfig, AgentState, AgentStatus, BaseAgent, Tool
from ..services.llm_helpers import LLMCallTimer, llm_retry, track_agent_decision
from .validation_models import BlockMergeInput, CodeReviewInput


class CodeReviewAgent(BaseAgent):
    """
    LLM-powered code review agent.

    Workflow:
    1. Parse code diff / file contents
    2. Analyze for security vulnerabilities
    3. Check code quality and best practices
    4. Assess performance implications
    5. Generate structured review with severity-ranked findings
    6. Request human review for critical/security findings
    """

    SECURITY_PROMPT = ChatPromptTemplate.from_template(
        "You are a senior security engineer performing a code review.\n"
        "Analyze the following code for security vulnerabilities.\n\n"
        "Language: {language}\n"
        "Code:\n```\n{code}\n```\n\n"
        "Check for:\n"
        "- SQL injection, XSS, CSRF\n"
        "- Hardcoded secrets or API keys\n"
        "- Insecure deserialization\n"
        "- Path traversal\n"
        "- Improper authentication/authorization\n"
        "- Dependency vulnerabilities\n\n"
        "Provide findings in JSON format:\n"
        "{{\n"
        '  "vulnerabilities": [\n'
        '    {{"type": "...", "severity": "critical|high|medium|low", '
        '"line": null, "description": "...", "fix": "..."}}\n'
        "  ],\n"
        '  "security_score": 0-100,\n'
        '  "has_critical": true|false\n'
        "}}"
    )

    QUALITY_PROMPT = ChatPromptTemplate.from_template(
        "You are a senior software engineer performing a code quality review.\n"
        "Analyze the following code for quality and best practices.\n\n"
        "Language: {language}\n"
        "Code:\n```\n{code}\n```\n\n"
        "Check for:\n"
        "- Code complexity and readability\n"
        "- DRY principle violations\n"
        "- Error handling completeness\n"
        "- Type safety and input validation\n"
        "- Naming conventions\n"
        "- Documentation completeness\n"
        "- Test coverage gaps\n\n"
        "Provide findings in JSON format:\n"
        "{{\n"
        '  "issues": [\n'
        '    {{"category": "...", "severity": "high|medium|low|info", '
        '"description": "...", "suggestion": "...", "line": null}}\n'
        "  ],\n"
        '  "quality_score": 0-100,\n'
        '  "complexity": "simple|moderate|complex|very_complex",\n'
        '  "maintainability": "excellent|good|fair|poor"\n'
        "}}"
    )

    PERFORMANCE_PROMPT = ChatPromptTemplate.from_template(
        "You are a performance engineer reviewing code.\n"
        "Analyze the following code for performance issues.\n\n"
        "Language: {language}\n"
        "Code:\n```\n{code}\n```\n\n"
        "Check for:\n"
        "- N+1 queries or unnecessary database calls\n"
        "- Memory leaks or excessive allocations\n"
        "- Blocking operations in async contexts\n"
        "- Missing caching opportunities\n"
        "- Inefficient algorithms or data structures\n"
        "- Unnecessary network calls\n\n"
        "Provide findings in JSON format:\n"
        "{{\n"
        '  "issues": [\n'
        '    {{"type": "...", "impact": "high|medium|low", '
        '"description": "...", "optimization": "..."}}\n'
        "  ],\n"
        '  "performance_score": 0-100,\n'
        '  "estimated_impact": "significant|moderate|minimal"\n'
        "}}"
    )

    SUMMARY_PROMPT = ChatPromptTemplate.from_template(
        "You are a tech lead summarizing a code review.\n"
        "Based on the following analysis results, provide a concise review summary.\n\n"
        "Security Analysis:\n{security}\n\n"
        "Quality Analysis:\n{quality}\n\n"
        "Performance Analysis:\n{performance}\n\n"
        "Provide a summary in JSON format:\n"
        "{{\n"
        '  "verdict": "approve|request_changes|block",\n'
        '  "summary": "2-3 sentence overall assessment",\n'
        '  "critical_items": ["item requiring immediate attention"],\n'
        '  "improvements": ["suggested improvement"],\n'
        '  "positive_notes": ["what was done well"],\n'
        '  "overall_score": 0-100,\n'
        '  "confidence": 0-100\n'
        "}}"
    )

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
        self._register_default_tools()

    def _lazy_init(self) -> None:
        """Lazy initialization of LLM dependencies."""
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
        """Get LLM, initializing if needed."""
        self._lazy_init()
        return self._llm

    def _register_default_tools(self) -> None:
        """Register default tools for code review operations."""
        self.register_tool(
            Tool(
                name="security_scan",
                description="Scan code for security vulnerabilities",
                func=self._security_scan,
            )
        )
        self.register_tool(
            Tool(
                name="quality_check",
                description="Check code quality and best practices",
                func=self._quality_check,
            )
        )
        self.register_tool(
            Tool(
                name="performance_review",
                description="Review code for performance issues",
                func=self._performance_review,
            )
        )
        self.register_tool(
            Tool(
                name="generate_summary",
                description="Generate overall review summary",
                func=self._generate_summary,
            )
        )
        self.register_tool(
            Tool(
                name="block_merge",
                description="Block merge due to critical findings",
                func=self._block_merge,
                requires_approval=True,
            )
        )

    @llm_retry(max_attempts=3)
    async def _security_scan(
        self,
        code: str,
        language: str = "python",
    ) -> Dict[str, Any]:
        """Scan code for security vulnerabilities."""
        validated = CodeReviewInput(code=code, language=language)
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.SECURITY_PROMPT | self.llm
            result = await chain.ainvoke(
                {"code": validated.code[:5000], "language": validated.language}
            )
            timer.set_tokens(input_tokens=len(validated.code) // 4, output_tokens=len(result.content) // 4)
        try:
            findings = json.loads(result.content)
        except json.JSONDecodeError:
            findings = {
                "vulnerabilities": [],
                "security_score": 70,
                "has_critical": False,
            }
        return findings

    @llm_retry(max_attempts=3)
    async def _quality_check(
        self,
        code: str,
        language: str = "python",
    ) -> Dict[str, Any]:
        """Check code quality and best practices."""
        validated = CodeReviewInput(code=code, language=language)
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.QUALITY_PROMPT | self.llm
            result = await chain.ainvoke(
                {"code": validated.code[:5000], "language": validated.language}
            )
            timer.set_tokens(input_tokens=len(validated.code) // 4, output_tokens=len(result.content) // 4)
        try:
            findings = json.loads(result.content)
        except json.JSONDecodeError:
            findings = {
                "issues": [],
                "quality_score": 70,
                "complexity": "moderate",
                "maintainability": "good",
            }
        return findings

    @llm_retry(max_attempts=3)
    async def _performance_review(
        self,
        code: str,
        language: str = "python",
    ) -> Dict[str, Any]:
        """Review code for performance issues."""
        validated = CodeReviewInput(code=code, language=language)
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.PERFORMANCE_PROMPT | self.llm
            result = await chain.ainvoke(
                {"code": validated.code[:5000], "language": validated.language}
            )
            timer.set_tokens(input_tokens=len(validated.code) // 4, output_tokens=len(result.content) // 4)
        try:
            findings = json.loads(result.content)
        except json.JSONDecodeError:
            findings = {
                "issues": [],
                "performance_score": 80,
                "estimated_impact": "minimal",
            }
        return findings

    @llm_retry(max_attempts=3)
    async def _generate_summary(
        self,
        security: Dict[str, Any],
        quality: Dict[str, Any],
        performance: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate overall review summary."""
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.SUMMARY_PROMPT | self.llm
            result = await chain.ainvoke(
                {
                    "security": json.dumps(security, indent=2),
                    "quality": json.dumps(quality, indent=2),
                    "performance": json.dumps(performance, indent=2),
                }
            )
            timer.set_tokens(input_tokens=300, output_tokens=len(result.content) // 4)
        try:
            summary = json.loads(result.content)
        except json.JSONDecodeError:
            summary = {
                "verdict": "request_changes",
                "summary": result.content[:500],
                "critical_items": [],
                "improvements": [],
                "positive_notes": [],
                "overall_score": 60,
                "confidence": 50,
            }
        return summary

    async def _block_merge(
        self,
        reason: str,
        critical_findings: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Block merge due to critical findings."""
        validated = BlockMergeInput(reason=reason, critical_findings=critical_findings)
        await track_agent_decision(
            self._evalai_tracer,
            agent_name="code_review",
            decision_type="block_merge",
            chosen="block",
            alternatives=["approve", "request_changes"],
            confidence=95,
            reasoning=validated.reason,
        )
        return {
            "blocked": True,
            "reason": validated.reason,
            "critical_findings": validated.critical_findings,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def plan(self, state: AgentState) -> Dict[str, Any]:
        """Determine next review action based on current state."""
        step = state.current_step
        code = state.input_data.get("code", "")
        language = state.input_data.get("language", "python")

        if step == 0:
            return {
                "action": "security_scan",
                "action_input": {"code": code, "language": language},
            }
        elif step == 1:
            return {
                "action": "quality_check",
                "action_input": {"code": code, "language": language},
            }
        elif step == 2:
            return {
                "action": "performance_review",
                "action_input": {"code": code, "language": language},
            }
        elif step == 3:
            security = state.intermediate_steps[0] if len(state.intermediate_steps) > 0 else {}
            quality = state.intermediate_steps[1] if len(state.intermediate_steps) > 1 else {}
            performance = state.intermediate_steps[2] if len(state.intermediate_steps) > 2 else {}
            return {
                "action": "generate_summary",
                "action_input": {
                    "security": security,
                    "quality": quality,
                    "performance": performance,
                },
            }
        elif step == 4:
            summary = state.intermediate_steps[-1] if state.intermediate_steps else {}
            security = state.intermediate_steps[0] if state.intermediate_steps else {}

            if summary.get("verdict") == "block" or security.get("has_critical"):
                critical = security.get("vulnerabilities", [])
                critical_items = [v for v in critical if v.get("severity") == "critical"]
                return {
                    "action": "block_merge",
                    "action_input": {
                        "reason": "Critical security vulnerabilities detected",
                        "critical_findings": critical_items,
                    },
                    "requires_approval": True,
                }
            return {"action": "complete", "action_input": {}}

        return {"action": "complete", "action_input": {}}

    async def execute_step(self, state: AgentState, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single review step."""
        action_name = action.get("action")
        action_input = action.get("action_input", {})

        if action_name == "security_scan":
            result = await self._security_scan(
                code=action_input.get("code", ""),
                language=action_input.get("language", "python"),
            )
            return {"action": action_name, **result}

        elif action_name == "quality_check":
            result = await self._quality_check(
                code=action_input.get("code", ""),
                language=action_input.get("language", "python"),
            )
            return {"action": action_name, **result}

        elif action_name == "performance_review":
            result = await self._performance_review(
                code=action_input.get("code", ""),
                language=action_input.get("language", "python"),
            )
            return {"action": action_name, **result}

        elif action_name == "generate_summary":
            result = await self._generate_summary(
                security=action_input.get("security", {}),
                quality=action_input.get("quality", {}),
                performance=action_input.get("performance", {}),
            )
            state.output_data["review"] = result
            await track_agent_decision(
                self._evalai_tracer,
                agent_name="code_review",
                decision_type="verdict",
                chosen=result.get("verdict", "request_changes"),
                alternatives=["approve", "request_changes", "block"],
                confidence=result.get("confidence", 50),
                reasoning=result.get("summary", "")[:200],
            )
            return {"action": action_name, **result}

        elif action_name == "block_merge":
            result = await self._block_merge(
                reason=action_input.get("reason", ""),
                critical_findings=action_input.get("critical_findings", []),
            )
            state.output_data["block"] = result
            await self.request_human_feedback(
                question="Critical security findings detected. Review and confirm merge block.",
                context=result,
                options=["confirm_block", "override_allow", "request_fix"],
            )
            return {"action": action_name, **result}

        elif action_name == "complete":
            return {"action": "complete", "completed": True}

        return {"action": action_name, "error": "Unknown action"}

    def should_continue(self, state: AgentState) -> bool:
        """Check if review should continue."""
        if state.current_step >= self.config.max_iterations:
            return False
        if state.status in [AgentStatus.COMPLETED, AgentStatus.FAILED, AgentStatus.AWAITING_HUMAN]:
            return False
        if state.intermediate_steps and state.intermediate_steps[-1].get("action") == "complete":
            return False
        return True


CodeReviewBlueprint = AgentBlueprint(
    name="code_review",
    agent_class=CodeReviewAgent,
    description="LLM-powered code review agent with security, quality, and performance analysis",
    default_config={
        "max_iterations": 6,
        "timeout_seconds": 180,
        "confidence_threshold": 0.7,
        "require_human_approval": False,
    },
    required_tools=["security_scan", "quality_check", "generate_summary"],
    version="1.0.0",
)
