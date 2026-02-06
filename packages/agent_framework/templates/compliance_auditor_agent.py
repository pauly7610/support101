"""
Compliance Auditor Agent Blueprint - Automated compliance and policy enforcement agent.

Scans conversations and agent actions for policy violations, PII leaks,
regulatory non-compliance, and security issues. Generates compliance
reports and triggers remediation workflows.
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
    CheckPolicyInput,
    GenerateReportInput,
    ScanPIIInput,
    TriggerRemediationInput,
)


class ComplianceAuditorAgent(BaseAgent):
    """
    Automated compliance auditing agent.

    Workflow:
    1. Scan content for PII and sensitive data
    2. Check against policy rules (GDPR, HIPAA, SOC2, etc.)
    3. Identify policy violations and risk areas
    4. Generate compliance report with severity ratings
    5. Trigger remediation for critical violations
    """

    PII_SCAN_PROMPT = ChatPromptTemplate.from_template(
        "You are a data privacy specialist. Scan the following content for PII and sensitive data.\n\n"
        "Content to scan:\n{content}\n\n"
        "Scan for:\n"
        "- Names, email addresses, phone numbers\n"
        "- Social security numbers, credit card numbers\n"
        "- Medical records, health information\n"
        "- Financial data, account numbers\n"
        "- IP addresses, geolocation data\n"
        "- Passwords, API keys, tokens\n\n"
        "Provide findings in JSON format:\n"
        "{{\n"
        '  "pii_found": true|false,\n'
        '  "findings": [\n'
        "    {{\n"
        '      "type": "email|phone|ssn|credit_card|medical|financial|credential|other",\n'
        '      "severity": "critical|high|medium|low",\n'
        '      "description": "what was found",\n'
        '      "location": "approximate location in content",\n'
        '      "remediation": "recommended action"\n'
        "    }}\n"
        "  ],\n"
        '  "risk_score": 0-100,\n'
        '  "data_categories": ["category1"]\n'
        "}}"
    )

    POLICY_CHECK_PROMPT = ChatPromptTemplate.from_template(
        "You are a compliance officer. Check the following agent action against policy rules.\n\n"
        "Agent Action:\n{action}\n"
        "Agent Response:\n{response}\n"
        "Applicable Policies: {policies}\n\n"
        "Check for:\n"
        "- Unauthorized data sharing\n"
        "- Inappropriate response content\n"
        "- Missing required disclaimers\n"
        "- Exceeding authorized scope\n"
        "- Regulatory non-compliance\n\n"
        "Provide findings in JSON format:\n"
        "{{\n"
        '  "compliant": true|false,\n'
        '  "violations": [\n'
        "    {{\n"
        '      "policy": "policy name",\n'
        '      "rule": "specific rule violated",\n'
        '      "severity": "critical|high|medium|low",\n'
        '      "description": "what happened",\n'
        '      "evidence": "relevant excerpt",\n'
        '      "remediation": "required action"\n'
        "    }}\n"
        "  ],\n"
        '  "warnings": ["potential issue that needs monitoring"],\n'
        '  "compliance_score": 0-100\n'
        "}}"
    )

    REPORT_PROMPT = ChatPromptTemplate.from_template(
        "You are a compliance reporting specialist. Generate a compliance audit report.\n\n"
        "PII Scan Results:\n{pii_results}\n"
        "Policy Check Results:\n{policy_results}\n"
        "Audit Scope: {scope}\n\n"
        "Generate a comprehensive report in JSON format:\n"
        "{{\n"
        '  "report_id": "AUD-timestamp",\n'
        '  "overall_status": "compliant|non_compliant|needs_review",\n'
        '  "overall_score": 0-100,\n'
        '  "critical_findings": 0,\n'
        '  "high_findings": 0,\n'
        '  "medium_findings": 0,\n'
        '  "low_findings": 0,\n'
        '  "executive_summary": "2-3 sentence summary",\n'
        '  "top_risks": [\n'
        '    {{"risk": "...", "impact": "...", "likelihood": "high|medium|low"}}\n'
        "  ],\n"
        '  "required_actions": [\n'
        '    {{"action": "...", "deadline": "immediate|24h|7d|30d", "owner": "suggested owner"}}\n'
        "  ],\n"
        '  "regulatory_impact": {{\n'
        '    "gdpr": "compliant|non_compliant|not_applicable",\n'
        '    "hipaa": "compliant|non_compliant|not_applicable",\n'
        '    "soc2": "compliant|non_compliant|not_applicable",\n'
        '    "ccpa": "compliant|non_compliant|not_applicable"\n'
        "  }}\n"
        "}}"
    )

    SUPPORTED_POLICIES = [
        "GDPR",
        "HIPAA",
        "SOC2",
        "CCPA",
        "PCI_DSS",
        "FINRA_4511",
    ]

    def __init__(
        self,
        config: AgentConfig,
        llm: Any | None = None,
        policies: list[str] | None = None,
        evalai_tracer: Any | None = None,
    ) -> None:
        super().__init__(config)
        self._llm = llm
        self._policies = policies or ["GDPR", "SOC2"]
        self._evalai_tracer = evalai_tracer
        self._initialized = False
        self._api = get_external_api_client()
        self._register_default_tools()

    def _lazy_init(self) -> None:
        if self._initialized:
            return
        if self._llm is None:
            with contextlib.suppress(Exception):
                self._llm = ChatOpenAI(temperature=0.1)
        self._initialized = True

    @property
    def llm(self) -> Any | None:
        self._lazy_init()
        return self._llm

    def _register_default_tools(self) -> None:
        self.register_tool(
            Tool(
                name="scan_pii",
                description="Scan content for PII and sensitive data",
                func=self._scan_pii,
            )
        )
        self.register_tool(
            Tool(
                name="check_policy",
                description="Check agent actions against compliance policies",
                func=self._check_policy,
            )
        )
        self.register_tool(
            Tool(
                name="generate_report",
                description="Generate compliance audit report",
                func=self._generate_report,
            )
        )
        self.register_tool(
            Tool(
                name="trigger_remediation",
                description="Trigger remediation workflow for critical violations",
                func=self._trigger_remediation,
                requires_approval=True,
            )
        )

    @llm_retry(max_attempts=3)
    async def _scan_pii(self, content: str) -> dict[str, Any]:
        validated = ScanPIIInput(content=content)
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.PII_SCAN_PROMPT | self.llm
            result = await chain.ainvoke({"content": validated.content[:5000]})
            timer.set_tokens(
                input_tokens=len(validated.content) // 4,
                output_tokens=len(result.content) // 4,
            )
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            return {
                "pii_found": False,
                "findings": [],
                "risk_score": 0,
                "data_categories": [],
            }

    @llm_retry(max_attempts=3)
    async def _check_policy(
        self,
        action: str,
        response: str,
        policies: list[str] | None = None,
    ) -> dict[str, Any]:
        validated = CheckPolicyInput(action=action, response=response, policies=policies)
        active_policies = validated.policies or self._policies
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.POLICY_CHECK_PROMPT | self.llm
            result = await chain.ainvoke({
                "action": validated.action[:2000],
                "response": validated.response[:3000],
                "policies": ", ".join(active_policies),
            })
            timer.set_tokens(
                input_tokens=(len(validated.action) + len(validated.response)) // 4,
                output_tokens=len(result.content) // 4,
            )
        try:
            return json.loads(result.content)
        except json.JSONDecodeError:
            return {
                "compliant": True,
                "violations": [],
                "warnings": [],
                "compliance_score": 50,
            }

    @llm_retry(max_attempts=3)
    async def _generate_report(
        self,
        pii_results: dict[str, Any],
        policy_results: dict[str, Any],
        scope: str = "",
    ) -> dict[str, Any]:
        validated = GenerateReportInput(
            pii_results=pii_results, policy_results=policy_results, scope=scope
        )
        async with LLMCallTimer(self._evalai_tracer, "openai", "gpt-4o") as timer:
            chain = self.REPORT_PROMPT | self.llm
            result = await chain.ainvoke({
                "pii_results": json.dumps(validated.pii_results, indent=2),
                "policy_results": json.dumps(validated.policy_results, indent=2),
                "scope": validated.scope or "Full agent interaction audit",
            })
            timer.set_tokens(input_tokens=400, output_tokens=len(result.content) // 4)
        try:
            report = json.loads(result.content)
        except json.JSONDecodeError:
            report = {
                "report_id": f"AUD-{int(datetime.utcnow().timestamp())}",
                "overall_status": "needs_review",
                "overall_score": 50,
                "critical_findings": 0,
                "high_findings": 0,
                "medium_findings": 0,
                "low_findings": 0,
                "executive_summary": "Audit completed. Manual review recommended.",
                "top_risks": [],
                "required_actions": [],
                "regulatory_impact": {},
            }

        report["generated_at"] = datetime.utcnow().isoformat()
        report["policies_checked"] = self._policies
        return report

    async def _trigger_remediation(
        self,
        violation_type: str,
        severity: str,
        details: dict[str, Any],
        required_action: str,
    ) -> dict[str, Any]:
        validated = TriggerRemediationInput(
            violation_type=violation_type,
            severity=severity,
            details=details,
            required_action=required_action,
        )
        await self._api.send_notification(
            channel="compliance",
            message=f"Compliance violation: {validated.violation_type} ({validated.severity})",
            urgency="high" if validated.severity in ("critical", "high") else "normal",
            metadata={"agent_id": self.agent_id, "tenant_id": self.tenant_id},
        )
        await track_agent_decision(
            self._evalai_tracer,
            agent_name="compliance_auditor",
            decision_type="remediation",
            chosen="trigger_remediation",
            confidence=95,
            reasoning=f"{validated.violation_type}: {validated.required_action[:150]}",
        )
        return {
            "remediation_triggered": True,
            "violation_type": validated.violation_type,
            "severity": validated.severity,
            "details": validated.details,
            "required_action": validated.required_action,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def plan(self, state: AgentState) -> dict[str, Any]:
        step = state.current_step

        if step == 0:
            content = state.input_data.get("content", "")
            if not content:
                messages = state.input_data.get("messages", [])
                content = "\n".join(m.get("content", "") for m in messages)
            return {
                "action": "scan_pii",
                "action_input": {"content": content},
            }
        elif step == 1:
            action_desc = state.input_data.get("agent_action", "Customer interaction")
            response = state.input_data.get("agent_response", state.input_data.get("content", ""))
            return {
                "action": "check_policy",
                "action_input": {
                    "action": action_desc,
                    "response": response,
                    "policies": state.input_data.get("policies", self._policies),
                },
            }
        elif step == 2:
            pii_results = state.intermediate_steps[0] if len(state.intermediate_steps) > 0 else {}
            policy_results = (
                state.intermediate_steps[1] if len(state.intermediate_steps) > 1 else {}
            )
            return {
                "action": "generate_report",
                "action_input": {
                    "pii_results": pii_results,
                    "policy_results": policy_results,
                    "scope": state.input_data.get("audit_scope", ""),
                },
            }
        elif step == 3:
            report = state.intermediate_steps[-1] if state.intermediate_steps else {}
            if (
                report.get("critical_findings", 0) > 0
                or report.get("overall_status") == "non_compliant"
            ):
                actions = report.get("required_actions", [])
                immediate = [a for a in actions if a.get("deadline") == "immediate"]
                return {
                    "action": "trigger_remediation",
                    "action_input": {
                        "violation_type": "compliance_breach",
                        "severity": (
                            "critical" if report.get("critical_findings", 0) > 0 else "high"
                        ),
                        "details": report,
                        "required_action": (
                            immediate[0].get("action", "Review and remediate")
                            if immediate
                            else "Review compliance report"
                        ),
                    },
                    "requires_approval": True,
                }
            return {"action": "complete", "action_input": {}}

        return {"action": "complete", "action_input": {}}

    async def execute_step(self, state: AgentState, action: dict[str, Any]) -> dict[str, Any]:
        action_name = action.get("action")
        action_input = action.get("action_input", {})

        if action_name == "scan_pii":
            result = await self._scan_pii(action_input.get("content", ""))
            return {"action": action_name, **result}
        elif action_name == "check_policy":
            result = await self._check_policy(
                action_input.get("action", ""),
                action_input.get("response", ""),
                action_input.get("policies"),
            )
            return {"action": action_name, **result}
        elif action_name == "generate_report":
            result = await self._generate_report(
                action_input.get("pii_results", {}),
                action_input.get("policy_results", {}),
                action_input.get("scope", ""),
            )
            state.output_data["compliance_report"] = result
            return {"action": action_name, **result}
        elif action_name == "trigger_remediation":
            result = await self._trigger_remediation(
                action_input.get("violation_type", ""),
                action_input.get("severity", "high"),
                action_input.get("details", {}),
                action_input.get("required_action", ""),
            )
            state.output_data["remediation"] = result
            await self.request_human_feedback(
                question="Critical compliance violation requires immediate remediation",
                context=result,
                options=["remediate_now", "escalate_to_legal", "acknowledge_risk"],
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


ComplianceAuditorBlueprint = AgentBlueprint(
    name="compliance_auditor",
    agent_class=ComplianceAuditorAgent,
    description="Automated compliance auditor with PII scanning, policy checks, and remediation workflows",
    default_config={
        "max_iterations": 5,
        "timeout_seconds": 120,
        "confidence_threshold": 0.8,
        "require_human_approval": True,
    },
    required_tools=["scan_pii", "check_policy", "generate_report"],
    version="1.0.0",
)
