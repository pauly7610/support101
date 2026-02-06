"""
Prometheus metrics for agent framework.

Provides comprehensive metrics for monitoring agent performance.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

try:
    from prometheus_client import Counter, Gauge, Histogram

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


@dataclass
class AgentMetrics:
    """Metrics data for an agent."""

    agent_id: str
    tenant_id: str
    blueprint: str
    executions_total: int = 0
    executions_successful: int = 0
    executions_failed: int = 0
    avg_execution_time_ms: float = 0.0
    avg_steps_per_execution: float = 0.0
    hitl_requests_total: int = 0
    escalations_total: int = 0
    last_execution_at: datetime | None = None


class MetricsCollector:
    """
    Prometheus metrics collector for agent framework.

    Tracks:
    - Agent execution counts and durations
    - HITL queue metrics
    - Tenant resource usage
    - Circuit breaker states
    """

    def __init__(self, namespace: str = "agent_framework") -> None:
        self._namespace = namespace
        self._initialized = False
        self._metrics: dict[str, Any] = {}

        if PROMETHEUS_AVAILABLE:
            self._initialize_metrics()

    def _initialize_metrics(self) -> None:
        """Initialize Prometheus metrics."""
        if self._initialized:
            return

        ns = self._namespace

        self._metrics["agent_executions_total"] = Counter(
            f"{ns}_agent_executions_total",
            "Total number of agent executions",
            ["tenant_id", "blueprint", "status"],
        )

        self._metrics["agent_execution_duration_seconds"] = Histogram(
            f"{ns}_agent_execution_duration_seconds",
            "Agent execution duration in seconds",
            ["tenant_id", "blueprint"],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
        )

        self._metrics["agent_steps_total"] = Counter(
            f"{ns}_agent_steps_total",
            "Total number of agent steps executed",
            ["tenant_id", "blueprint", "action"],
        )

        self._metrics["active_agents"] = Gauge(
            f"{ns}_active_agents",
            "Number of currently active agents",
            ["tenant_id", "blueprint"],
        )

        self._metrics["hitl_queue_size"] = Gauge(
            f"{ns}_hitl_queue_size",
            "Current size of HITL queue",
            ["tenant_id", "priority"],
        )

        self._metrics["hitl_requests_total"] = Counter(
            f"{ns}_hitl_requests_total",
            "Total HITL requests",
            ["tenant_id", "request_type", "status"],
        )

        self._metrics["hitl_response_time_seconds"] = Histogram(
            f"{ns}_hitl_response_time_seconds",
            "Time to respond to HITL requests",
            ["tenant_id", "priority"],
            buckets=(60, 300, 600, 1800, 3600, 7200, 14400),
        )

        self._metrics["escalations_total"] = Counter(
            f"{ns}_escalations_total",
            "Total escalations triggered",
            ["tenant_id", "trigger", "level"],
        )

        self._metrics["tenant_agents_count"] = Gauge(
            f"{ns}_tenant_agents_count",
            "Number of agents per tenant",
            ["tenant_id", "tier"],
        )

        self._metrics["tenant_rate_limit_remaining"] = Gauge(
            f"{ns}_tenant_rate_limit_remaining",
            "Remaining rate limit for tenant",
            ["tenant_id"],
        )

        self._metrics["circuit_breaker_state"] = Gauge(
            f"{ns}_circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=open, 2=half_open)",
            ["name"],
        )

        self._metrics["circuit_breaker_failures"] = Counter(
            f"{ns}_circuit_breaker_failures_total",
            "Total circuit breaker failures",
            ["name"],
        )

        self._metrics["llm_calls_total"] = Counter(
            f"{ns}_llm_calls_total",
            "Total LLM API calls",
            ["tenant_id", "model", "status"],
        )

        self._metrics["llm_call_duration_seconds"] = Histogram(
            f"{ns}_llm_call_duration_seconds",
            "LLM API call duration",
            ["tenant_id", "model"],
            buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0),
        )

        self._metrics["vector_store_queries_total"] = Counter(
            f"{ns}_vector_store_queries_total",
            "Total vector store queries",
            ["tenant_id", "status"],
        )

        self._initialized = True

    def record_execution_start(
        self,
        tenant_id: str,
        blueprint: str,
    ) -> None:
        """Record start of agent execution."""
        if not PROMETHEUS_AVAILABLE:
            return
        self._metrics["active_agents"].labels(
            tenant_id=tenant_id,
            blueprint=blueprint,
        ).inc()

    def record_execution_end(
        self,
        tenant_id: str,
        blueprint: str,
        status: str,
        duration_seconds: float,
        steps: int,
    ) -> None:
        """Record end of agent execution."""
        if not PROMETHEUS_AVAILABLE:
            return

        self._metrics["agent_executions_total"].labels(
            tenant_id=tenant_id,
            blueprint=blueprint,
            status=status,
        ).inc()

        self._metrics["agent_execution_duration_seconds"].labels(
            tenant_id=tenant_id,
            blueprint=blueprint,
        ).observe(duration_seconds)

        self._metrics["active_agents"].labels(
            tenant_id=tenant_id,
            blueprint=blueprint,
        ).dec()

    def record_step(
        self,
        tenant_id: str,
        blueprint: str,
        action: str,
    ) -> None:
        """Record an agent step execution."""
        if not PROMETHEUS_AVAILABLE:
            return
        self._metrics["agent_steps_total"].labels(
            tenant_id=tenant_id,
            blueprint=blueprint,
            action=action,
        ).inc()

    def record_hitl_request(
        self,
        tenant_id: str,
        request_type: str,
        priority: str,
    ) -> None:
        """Record a new HITL request."""
        if not PROMETHEUS_AVAILABLE:
            return
        self._metrics["hitl_requests_total"].labels(
            tenant_id=tenant_id,
            request_type=request_type,
            status="created",
        ).inc()

        self._metrics["hitl_queue_size"].labels(
            tenant_id=tenant_id,
            priority=priority,
        ).inc()

    def record_hitl_response(
        self,
        tenant_id: str,
        priority: str,
        response_time_seconds: float,
        status: str,
    ) -> None:
        """Record HITL request response."""
        if not PROMETHEUS_AVAILABLE:
            return
        self._metrics["hitl_requests_total"].labels(
            tenant_id=tenant_id,
            request_type="response",
            status=status,
        ).inc()

        self._metrics["hitl_response_time_seconds"].labels(
            tenant_id=tenant_id,
            priority=priority,
        ).observe(response_time_seconds)

        self._metrics["hitl_queue_size"].labels(
            tenant_id=tenant_id,
            priority=priority,
        ).dec()

    def record_escalation(
        self,
        tenant_id: str,
        trigger: str,
        level: str,
    ) -> None:
        """Record an escalation."""
        if not PROMETHEUS_AVAILABLE:
            return
        self._metrics["escalations_total"].labels(
            tenant_id=tenant_id,
            trigger=trigger,
            level=level,
        ).inc()

    def set_tenant_agents(
        self,
        tenant_id: str,
        tier: str,
        count: int,
    ) -> None:
        """Set tenant agent count."""
        if not PROMETHEUS_AVAILABLE:
            return
        self._metrics["tenant_agents_count"].labels(
            tenant_id=tenant_id,
            tier=tier,
        ).set(count)

    def set_rate_limit_remaining(
        self,
        tenant_id: str,
        remaining: int,
    ) -> None:
        """Set remaining rate limit for tenant."""
        if not PROMETHEUS_AVAILABLE:
            return
        self._metrics["tenant_rate_limit_remaining"].labels(
            tenant_id=tenant_id,
        ).set(remaining)

    def set_circuit_breaker_state(
        self,
        name: str,
        state: str,
    ) -> None:
        """Set circuit breaker state."""
        if not PROMETHEUS_AVAILABLE:
            return
        state_value = {"closed": 0, "open": 1, "half_open": 2}.get(state, 0)
        self._metrics["circuit_breaker_state"].labels(name=name).set(state_value)

    def record_circuit_breaker_failure(self, name: str) -> None:
        """Record circuit breaker failure."""
        if not PROMETHEUS_AVAILABLE:
            return
        self._metrics["circuit_breaker_failures"].labels(name=name).inc()

    def record_llm_call(
        self,
        tenant_id: str,
        model: str,
        status: str,
        duration_seconds: float,
    ) -> None:
        """Record an LLM API call."""
        if not PROMETHEUS_AVAILABLE:
            return
        self._metrics["llm_calls_total"].labels(
            tenant_id=tenant_id,
            model=model,
            status=status,
        ).inc()

        self._metrics["llm_call_duration_seconds"].labels(
            tenant_id=tenant_id,
            model=model,
        ).observe(duration_seconds)

    def record_vector_query(
        self,
        tenant_id: str,
        status: str,
    ) -> None:
        """Record a vector store query."""
        if not PROMETHEUS_AVAILABLE:
            return
        self._metrics["vector_store_queries_total"].labels(
            tenant_id=tenant_id,
            status=status,
        ).inc()


_default_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get the default metrics collector."""
    global _default_collector
    if _default_collector is None:
        _default_collector = MetricsCollector()
    return _default_collector
