"""
EvalAI Platform integration for agent workflow tracing.

Sends execution traces, agent decisions, cost records, and workflow
definitions to the EvalAI REST API for monitoring, auditing, and
governance.

Uses the REST API from @pauly4010/evalai-sdk (AI Evaluation Platform):
    POST /api/traces      — Create/update execution traces
    POST /api/decisions   — Record agent decisions with alternatives
    POST /api/costs       — Track LLM token usage and costs
    POST /api/workflows   — Register workflow DAG definitions

Requires env vars:
    EVALAI_API_KEY          — Bearer token for auth
    EVALAI_BASE_URL         — Platform URL (e.g. https://ai-evaluation-platform.vercel.app)
    EVALAI_ORGANIZATION_ID  — Integer org ID

Gracefully degrades when httpx is unavailable or env vars are not set.
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False


# ── Data models ─────────────────────────────────────────────────


@dataclass
class EvalAIDecision:
    """A decision made by an agent during workflow execution."""

    agent: str
    type: str  # 'action' | 'tool' | 'delegate' | 'respond' | 'route'
    chosen: str
    alternatives: List[Dict[str, Any]]
    reasoning: Optional[str] = None
    confidence: Optional[int] = None  # 0-100
    input_context: Optional[Dict[str, Any]] = None


@dataclass
class EvalAICostRecord:
    """Token usage and cost for an LLM call."""

    provider: str  # 'openai' | 'anthropic' | 'google' | 'cohere' | 'mistral' | 'custom'
    model: str
    input_tokens: int
    output_tokens: int
    category: str = "llm"  # 'llm' | 'tool' | 'embedding' | 'other'
    is_retry: bool = False
    retry_number: int = 0


@dataclass
class EvalAIWorkflowNode:
    """A node in a workflow DAG definition."""

    id: str
    type: str  # 'agent' | 'tool' | 'decision' | 'parallel' | 'human' | 'llm'
    name: str
    config: Optional[Dict[str, Any]] = None


@dataclass
class EvalAIWorkflowEdge:
    """An edge connecting two nodes in a workflow DAG."""

    from_node: str
    to_node: str
    condition: Optional[str] = None
    label: Optional[str] = None


@dataclass
class EvalAIWorkflowDefinition:
    """Complete workflow DAG definition for EvalAI visualization."""

    nodes: List[EvalAIWorkflowNode]
    edges: List[EvalAIWorkflowEdge]
    entrypoint: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [
                {"id": n.id, "type": n.type, "name": n.name, "config": n.config or {}}
                for n in self.nodes
            ],
            "edges": [
                {
                    "from": e.from_node,
                    "to": e.to_node,
                    "condition": e.condition,
                    "label": e.label,
                }
                for e in self.edges
            ],
            "entrypoint": self.entrypoint,
            "metadata": self.metadata,
        }


@dataclass
class EvalAISpanContext:
    """Context for an active agent span."""

    span_id: int
    agent_name: str
    start_time: float
    parent_span_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class EvalAIWorkflowContext:
    """Context for an active workflow trace."""

    trace_id: int
    workflow_id: Optional[int]
    name: str
    started_at: str
    metadata: Optional[Dict[str, Any]] = None


# ── Governance ──────────────────────────────────────────────────


@dataclass
class EvalAIGovernanceConfig:
    """Governance configuration matching EvalAI compliance presets."""

    confidence_threshold: float = 0.7
    amount_threshold: float = 500.0
    require_approval_for_sensitive_data: bool = True
    require_approval_for_pii: bool = True
    allowed_models: List[str] = field(default_factory=list)
    max_cost_per_run: float = 10.0
    audit_level: str = "SOC2"  # 'BASIC' | 'SOC2' | 'GDPR' | 'HIPAA' | 'FINRA_4511' | 'PCI_DSS'


COMPLIANCE_PRESETS: Dict[str, EvalAIGovernanceConfig] = {
    "BASIC": EvalAIGovernanceConfig(
        confidence_threshold=0.6,
        amount_threshold=1000.0,
        require_approval_for_sensitive_data=False,
        require_approval_for_pii=False,
        audit_level="BASIC",
    ),
    "SOC2": EvalAIGovernanceConfig(
        confidence_threshold=0.7,
        amount_threshold=500.0,
        require_approval_for_sensitive_data=True,
        require_approval_for_pii=True,
        audit_level="SOC2",
    ),
    "GDPR": EvalAIGovernanceConfig(
        confidence_threshold=0.75,
        amount_threshold=250.0,
        require_approval_for_sensitive_data=True,
        require_approval_for_pii=True,
        audit_level="GDPR",
    ),
    "HIPAA": EvalAIGovernanceConfig(
        confidence_threshold=0.8,
        amount_threshold=100.0,
        require_approval_for_sensitive_data=True,
        require_approval_for_pii=True,
        audit_level="HIPAA",
    ),
    "FINRA_4511": EvalAIGovernanceConfig(
        confidence_threshold=0.85,
        amount_threshold=100.0,
        require_approval_for_sensitive_data=True,
        require_approval_for_pii=True,
        audit_level="FINRA_4511",
    ),
    "PCI_DSS": EvalAIGovernanceConfig(
        confidence_threshold=0.8,
        amount_threshold=50.0,
        require_approval_for_sensitive_data=True,
        require_approval_for_pii=True,
        audit_level="PCI_DSS",
    ),
}


def check_governance(
    decision: EvalAIDecision,
    config: EvalAIGovernanceConfig,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Evaluate a decision against governance rules.

    Returns dict with requires_approval, blocked, reasons, and audit_level.
    Mirrors the JS GovernanceEngine.evaluate() interface.
    """
    ctx = context or {}
    reasons: List[str] = []
    requires_approval = False
    blocked = False

    # Confidence threshold
    if decision.confidence is not None:
        confidence_normalized = decision.confidence / 100.0
        if confidence_normalized < config.confidence_threshold:
            requires_approval = True
            reasons.append(
                f"Confidence {decision.confidence}% below threshold "
                f"{config.confidence_threshold * 100}%"
            )
        if confidence_normalized < 0.3:
            blocked = True
            reasons.append(f"Confidence {decision.confidence}% critically low (<30%)")

    # Amount threshold
    amount = ctx.get("amount")
    if amount is not None and amount > config.amount_threshold:
        requires_approval = True
        reasons.append(
            f"Amount ${amount} exceeds threshold ${config.amount_threshold}"
        )

    # Sensitive data / PII
    if config.require_approval_for_sensitive_data and ctx.get("sensitiveData"):
        requires_approval = True
        reasons.append("Sensitive data detected")

    if config.require_approval_for_pii and ctx.get("piiDetected"):
        requires_approval = True
        reasons.append("PII detected")

    # Blocking rules: fraud/security in alternatives
    for alt in decision.alternatives:
        action = alt.get("action", "").lower()
        alt_confidence = alt.get("confidence", 0)
        if "fraud" in action and alt_confidence > 30:
            blocked = True
            reasons.append(f"Fraud-related alternative '{action}' with confidence {alt_confidence}%")
        if "security" in action and alt_confidence > 40:
            blocked = True
            reasons.append(
                f"Security-related alternative '{action}' with confidence {alt_confidence}%"
            )

    return {
        "requires_approval": requires_approval,
        "blocked": blocked,
        "reasons": reasons,
        "audit_level": config.audit_level,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Main tracer ─────────────────────────────────────────────────


class EvalAITracer:
    """
    Async Python client for the EvalAI REST API.

    Mirrors the JS WorkflowTracer interface but calls REST endpoints
    directly using httpx. Gracefully degrades if httpx is unavailable
    or if env vars are not set.

    Usage:
        tracer = EvalAITracer()

        # Context manager pattern
        async with tracer.workflow("My Pipeline"):
            span = await tracer.start_agent_span("RouterAgent", {"query": "help"})
            await tracer.record_decision(EvalAIDecision(...))
            await tracer.record_cost(EvalAICostRecord(...))
            await tracer.end_agent_span(span, {"result": "routed"})

        # Manual pattern
        await tracer.start_workflow("My Pipeline")
        # ... work ...
        await tracer.end_workflow(output={"result": "done"})
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        organization_id: Optional[int] = None,
        enabled: bool = True,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        self._api_key = api_key or os.environ.get("EVALAI_API_KEY", "")
        self._base_url = (
            base_url or os.environ.get("EVALAI_BASE_URL", "")
        ).rstrip("/")

        raw_org_id = organization_id or os.environ.get("EVALAI_ORGANIZATION_ID", "0")
        try:
            self._organization_id = int(raw_org_id)
        except (ValueError, TypeError):
            self._organization_id = 0

        self._timeout = timeout
        self._max_retries = max_retries

        self._enabled = (
            enabled
            and HTTPX_AVAILABLE
            and bool(self._api_key)
            and bool(self._base_url)
            and self._organization_id > 0
        )

        self._client: Optional["httpx.AsyncClient"] = None
        self._current_trace_id: Optional[int] = None
        self._current_workflow_id: Optional[int] = None
        self._workflow_start_time: Optional[float] = None
        self._costs: List[Dict[str, Any]] = []
        self._decisions: List[Dict[str, Any]] = []
        self._handoffs: List[Dict[str, Any]] = []

        if not self._enabled:
            if not HTTPX_AVAILABLE:
                logger.info("EvalAI tracer disabled: httpx not installed")
            elif not self._api_key:
                logger.info("EvalAI tracer disabled: EVALAI_API_KEY not set")
            elif not self._base_url:
                logger.info("EvalAI tracer disabled: EVALAI_BASE_URL not set")
            elif self._organization_id <= 0:
                logger.info("EvalAI tracer disabled: EVALAI_ORGANIZATION_ID not set")
        else:
            logger.info(
                "EvalAI tracer enabled: %s (org %d)",
                self._base_url,
                self._organization_id,
            )

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def current_trace_id(self) -> Optional[int]:
        return self._current_trace_id

    @property
    def current_workflow_id(self) -> Optional[int]:
        return self._current_workflow_id

    # ── HTTP client ─────────────────────────────────────────────

    async def _get_client(self) -> "httpx.AsyncClient":
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self._timeout,
            )
        return self._client

    async def _post(
        self, path: str, json: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if not self._enabled:
            return None
        client = await self._get_client()
        last_error: Optional[Exception] = None
        for attempt in range(self._max_retries):
            try:
                resp = await client.post(path, json=json)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status in (429, 500, 502, 503, 504):
                    last_error = e
                    logger.warning(
                        "EvalAI %s returned %d, retrying (%d/%d)",
                        path,
                        status,
                        attempt + 1,
                        self._max_retries,
                    )
                    await self._backoff(attempt)
                    continue
                logger.error(
                    "EvalAI API error %s (HTTP %d): %s",
                    path,
                    status,
                    e.response.text[:200],
                )
                return None
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_error = e
                logger.warning(
                    "EvalAI %s network error, retrying (%d/%d): %s",
                    path,
                    attempt + 1,
                    self._max_retries,
                    e,
                )
                await self._backoff(attempt)
                continue
        logger.error(
            "EvalAI API %s failed after %d retries: %s",
            path,
            self._max_retries,
            last_error,
        )
        return None

    @staticmethod
    async def _backoff(attempt: int) -> None:
        delay = min(2**attempt, 10)
        await asyncio.sleep(delay)

    @staticmethod
    def _iso_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Workflow lifecycle ──────────────────────────────────────

    async def start_workflow(
        self,
        name: str,
        definition: Optional[EvalAIWorkflowDefinition] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[EvalAIWorkflowContext]:
        """
        Start a new workflow trace.

        Creates a trace in EvalAI and optionally registers the workflow
        DAG definition for visualization.

        Returns:
            EvalAIWorkflowContext if successful, None if disabled/failed.
        """
        self._workflow_start_time = time.time()
        self._costs = []
        self._decisions = []
        self._handoffs = []

        trace_id_str = f"workflow-{int(time.time() * 1000)}-{os.urandom(4).hex()}"
        trace = await self._post(
            "/api/traces",
            {
                "name": f"Workflow: {name}",
                "traceId": trace_id_str,
                "organizationId": self._organization_id,
                "status": "pending",
                "metadata": metadata or {},
            },
        )
        if trace:
            self._current_trace_id = trace["id"]
        else:
            return None

        workflow_id: Optional[int] = None
        if definition:
            wf = await self._post(
                "/api/workflows",
                {
                    "name": name,
                    "organizationId": self._organization_id,
                    "definition": definition.to_dict(),
                    "status": "active",
                },
            )
            if wf:
                workflow_id = wf.get("id")
                self._current_workflow_id = workflow_id

        return EvalAIWorkflowContext(
            trace_id=self._current_trace_id,
            workflow_id=workflow_id,
            name=name,
            started_at=self._iso_now(),
            metadata=metadata,
        )

    async def end_workflow(
        self,
        output: Optional[Dict[str, Any]] = None,
        status: str = "completed",
    ) -> None:
        """
        End the current workflow trace.

        Args:
            output: Final workflow output/result data.
            status: 'completed' | 'failed' | 'cancelled'
        """
        if not self._enabled or self._current_trace_id is None:
            return

        duration_ms = int(
            (time.time() - (self._workflow_start_time or time.time())) * 1000
        )

        evalai_status = "success" if status == "completed" else "error"

        # Update the trace with final status and duration
        # The traces API uses POST for creation; we send a new span to mark completion
        await self._post(
            f"/api/traces/{self._current_trace_id}/spans",
            {
                "name": f"Workflow End ({status})",
                "spanId": f"workflow-end-{int(time.time() * 1000)}",
                "startTime": self._iso_now(),
                "durationMs": duration_ms,
                "metadata": {
                    "type": "workflow_end",
                    "status": evalai_status,
                    "durationMs": duration_ms,
                    "totalCost": self.get_total_cost(),
                    "decisionsCount": len(self._decisions),
                    "handoffsCount": len(self._handoffs),
                    "output": output or {},
                },
            },
        )

        self._current_trace_id = None
        self._current_workflow_id = None
        self._workflow_start_time = None

    # ── Agent spans ─────────────────────────────────────────────

    async def start_agent_span(
        self,
        agent_name: str,
        input_data: Optional[Dict[str, Any]] = None,
        parent_span_id: Optional[str] = None,
    ) -> Optional[EvalAISpanContext]:
        """
        Start a span for an agent's execution within the current workflow.

        Args:
            agent_name: Name of the agent being traced.
            input_data: Input data for this agent step.
            parent_span_id: Optional parent span for nested agents.

        Returns:
            EvalAISpanContext to pass to end_agent_span().
        """
        if not self._enabled or self._current_trace_id is None:
            return None

        span_id_str = f"agent-{agent_name}-{int(time.time() * 1000)}"
        span = await self._post(
            f"/api/traces/{self._current_trace_id}/spans",
            {
                "name": f"Agent: {agent_name}",
                "spanId": span_id_str,
                "parentSpanId": parent_span_id,
                "startTime": self._iso_now(),
                "metadata": {
                    "type": "agent_execution",
                    "agentName": agent_name,
                    "input": input_data or {},
                },
            },
        )
        if span:
            return EvalAISpanContext(
                span_id=span["id"],
                agent_name=agent_name,
                start_time=time.time(),
                parent_span_id=parent_span_id,
                metadata=input_data,
            )
        return None

    async def end_agent_span(
        self,
        span: Optional[EvalAISpanContext],
        output: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        End an agent span, recording output or error.

        Creates a completion span linked to the original agent span.
        """
        if not self._enabled or span is None or self._current_trace_id is None:
            return

        duration_ms = int((time.time() - span.start_time) * 1000)
        await self._post(
            f"/api/traces/{self._current_trace_id}/spans",
            {
                "name": f"Agent Complete: {span.agent_name}",
                "spanId": f"agent-end-{span.agent_name}-{int(time.time() * 1000)}",
                "parentSpanId": str(span.span_id),
                "startTime": self._iso_now(),
                "durationMs": duration_ms,
                "metadata": {
                    "type": "agent_completion",
                    "agentName": span.agent_name,
                    "durationMs": duration_ms,
                    "output": output or {},
                    "error": error,
                },
            },
        )

    # ── Decisions ───────────────────────────────────────────────

    async def record_decision(
        self,
        decision: EvalAIDecision,
        span_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Record an agent decision with alternatives and confidence.

        Args:
            decision: The decision data.
            span_id: Optional span ID to attach the decision to.

        Returns:
            The created decision record, or None.
        """
        if not self._enabled:
            return None

        payload: Dict[str, Any] = {
            "spanId": span_id or self._current_trace_id or 0,
            "agentName": decision.agent,
            "decisionType": decision.type,
            "chosen": decision.chosen,
            "alternatives": decision.alternatives,
        }
        if self._current_workflow_id:
            payload["workflowRunId"] = self._current_workflow_id
        if decision.reasoning:
            payload["reasoning"] = decision.reasoning
        if decision.confidence is not None:
            payload["confidence"] = decision.confidence
        if decision.input_context:
            payload["inputContext"] = decision.input_context

        result = await self._post("/api/decisions", payload)
        if result:
            self._decisions.append(result)
        return result

    # ── Cost tracking ───────────────────────────────────────────

    async def record_cost(
        self,
        cost: EvalAICostRecord,
        span_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Record LLM token usage and cost.

        EvalAI auto-calculates cost from built-in model pricing tables.

        Args:
            cost: Token usage data.
            span_id: Optional span ID to attach the cost to.

        Returns:
            The created cost record (includes totalCost), or None.
        """
        if not self._enabled:
            return None

        payload: Dict[str, Any] = {
            "spanId": span_id or self._current_trace_id or 0,
            "provider": cost.provider,
            "model": cost.model,
            "inputTokens": cost.input_tokens,
            "outputTokens": cost.output_tokens,
            "category": cost.category,
            "isRetry": cost.is_retry,
            "retryNumber": cost.retry_number,
        }
        if self._current_workflow_id:
            payload["workflowRunId"] = self._current_workflow_id

        result = await self._post("/api/costs", payload)
        if result:
            self._costs.append(result)
        return result

    # ── Handoffs ────────────────────────────────────────────────

    async def record_handoff(
        self,
        from_agent: Optional[str],
        to_agent: str,
        context: Optional[Dict[str, Any]] = None,
        handoff_type: str = "delegation",
    ) -> None:
        """
        Record an agent-to-agent handoff.

        Args:
            from_agent: Source agent name (None for entry point).
            to_agent: Target agent name.
            context: Handoff context data.
            handoff_type: 'delegation' | 'escalation' | 'parallel' | 'fallback'
        """
        if not self._enabled or self._current_trace_id is None:
            return

        handoff_data = {
            "type": "handoff",
            "handoffType": handoff_type,
            "fromAgent": from_agent,
            "toAgent": to_agent,
            "context": context or {},
        }

        await self._post(
            f"/api/traces/{self._current_trace_id}/spans",
            {
                "name": f"Handoff: {from_agent or 'entry'} -> {to_agent}",
                "spanId": f"handoff-{int(time.time() * 1000)}-{os.urandom(2).hex()}",
                "startTime": self._iso_now(),
                "metadata": handoff_data,
            },
        )

        self._handoffs.append(handoff_data)

    # ── Utility methods ─────────────────────────────────────────

    def get_total_cost(self) -> float:
        """Get total cost across all recorded cost entries."""
        return sum(float(c.get("totalCost", 0)) for c in self._costs)

    def get_cost_breakdown(self) -> Dict[str, float]:
        """Get cost breakdown by category."""
        breakdown: Dict[str, float] = {
            "llm": 0.0,
            "tool": 0.0,
            "embedding": 0.0,
            "other": 0.0,
        }
        for c in self._costs:
            category = c.get("category", "other")
            breakdown[category] = breakdown.get(category, 0.0) + float(
                c.get("totalCost", 0)
            )
        return breakdown

    def get_decisions(self) -> List[Dict[str, Any]]:
        """Get all recorded decisions for the current workflow."""
        return list(self._decisions)

    def get_handoffs(self) -> List[Dict[str, Any]]:
        """Get all recorded handoffs for the current workflow."""
        return list(self._handoffs)

    def get_costs(self) -> List[Dict[str, Any]]:
        """Get all recorded cost entries for the current workflow."""
        return list(self._costs)

    def is_workflow_active(self) -> bool:
        """Check if a workflow is currently being traced."""
        return self._current_trace_id is not None

    # ── Context manager ─────────────────────────────────────────

    @asynccontextmanager
    async def workflow(
        self,
        name: str,
        definition: Optional[EvalAIWorkflowDefinition] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator["EvalAITracer"]:
        """
        Context manager for workflow tracing.

        Usage:
            async with tracer.workflow("My Pipeline"):
                await tracer.record_decision(...)
                await tracer.record_cost(...)
        """
        await self.start_workflow(name, definition, metadata)
        try:
            yield self
        except Exception as e:
            await self.end_workflow(output={"error": str(e)}, status="failed")
            raise
        else:
            await self.end_workflow(status="completed")

    # ── Cleanup ─────────────────────────────────────────────────

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
