"""
OpenTelemetry tracing for agent framework.

Provides distributed tracing for agent executions.
"""

import functools
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeVar

T = TypeVar("T")

try:
    from opentelemetry import trace
    from opentelemetry.trace import Span, Status, StatusCode, Tracer
    from opentelemetry.trace.propagation.tracecontext import (
        TraceContextTextMapPropagator,
    )

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    Span = Any
    Tracer = Any


@dataclass
class SpanContext:
    """Context for a trace span."""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: datetime | None = None
    status: str = "ok"
    events: list = field(default_factory=list)

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add an event to the span."""
        self.events.append(
            {
                "name": name,
                "timestamp": datetime.utcnow().isoformat(),
                "attributes": attributes or {},
            }
        )

    def set_status(self, status: str, description: str = "") -> None:
        """Set span status."""
        self.status = status
        if description:
            self.attributes["status_description"] = description

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "attributes": self.attributes,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "events": self.events,
        }


class TracingProvider:
    """
    OpenTelemetry tracing provider for agent framework.

    Provides:
    - Distributed tracing across agent executions
    - Span creation and management
    - Context propagation
    """

    def __init__(
        self,
        service_name: str = "agent_framework",
        enabled: bool = True,
    ) -> None:
        self._service_name = service_name
        self._enabled = enabled and OTEL_AVAILABLE
        self._tracer: Tracer | None = None

        if self._enabled:
            self._tracer = trace.get_tracer(service_name)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @asynccontextmanager
    async def start_span(
        self,
        name: str,
        attributes: dict[str, Any] | None = None,
        parent: SpanContext | None = None,
    ):
        """
        Start a new trace span.

        Usage:
            async with tracer.start_span("my_operation") as span:
                # do work
                span.add_event("checkpoint")
        """
        if not self._enabled or not self._tracer:
            ctx = SpanContext(
                trace_id="disabled",
                span_id="disabled",
                attributes=attributes or {},
            )
            yield ctx
            return

        with self._tracer.start_as_current_span(
            name,
            attributes=attributes,
        ) as span:
            span_context = span.get_span_context()
            ctx = SpanContext(
                trace_id=format(span_context.trace_id, "032x"),
                span_id=format(span_context.span_id, "016x"),
                attributes=attributes or {},
            )

            try:
                yield ctx
                span.set_status(Status(StatusCode.OK))
                ctx.status = "ok"
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                ctx.set_status("error", str(e))
                raise
            finally:
                ctx.end_time = datetime.utcnow()

    def create_span_context(
        self,
        trace_id: str,
        span_id: str,
        attributes: dict[str, Any] | None = None,
    ) -> SpanContext:
        """Create a span context manually."""
        return SpanContext(
            trace_id=trace_id,
            span_id=span_id,
            attributes=attributes or {},
        )

    def inject_context(self, carrier: dict[str, str]) -> None:
        """Inject trace context into a carrier (e.g., HTTP headers)."""
        if not self._enabled:
            return

        propagator = TraceContextTextMapPropagator()
        propagator.inject(carrier)

    def extract_context(self, carrier: dict[str, str]) -> SpanContext | None:
        """Extract trace context from a carrier."""
        if not self._enabled:
            return None

        propagator = TraceContextTextMapPropagator()
        context = propagator.extract(carrier)

        span = trace.get_current_span(context)
        if span:
            span_context = span.get_span_context()
            return SpanContext(
                trace_id=format(span_context.trace_id, "032x"),
                span_id=format(span_context.span_id, "016x"),
            )
        return None


_default_provider: TracingProvider | None = None


def get_tracing_provider() -> TracingProvider:
    """Get the default tracing provider."""
    global _default_provider
    if _default_provider is None:
        _default_provider = TracingProvider()
    return _default_provider


def trace_agent_execution(
    name: str | None = None,
    attributes: dict[str, Any] | None = None,
) -> Callable:
    """
    Decorator for tracing agent execution methods.

    Usage:
        @trace_agent_execution("execute_step")
        async def execute_step(self, state, action):
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        span_name = name or func.__name__

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            provider = get_tracing_provider()

            span_attrs = dict(attributes or {})
            span_attrs["function"] = func.__name__

            if args and hasattr(args[0], "agent_id"):
                span_attrs["agent_id"] = args[0].agent_id
            if args and hasattr(args[0], "tenant_id"):
                span_attrs["tenant_id"] = args[0].tenant_id

            async with provider.start_span(span_name, span_attrs) as span:
                result = await func(*args, **kwargs)

                if isinstance(result, dict) and "action" in result:
                    span.add_event("action", {"action": result["action"]})

                return result

        return wrapper

    return decorator


class AgentTracer:
    """
    Specialized tracer for agent executions.

    Provides high-level tracing methods for common agent operations.
    """

    def __init__(self, provider: TracingProvider | None = None) -> None:
        self._provider = provider or get_tracing_provider()

    @asynccontextmanager
    async def trace_execution(
        self,
        agent_id: str,
        tenant_id: str,
        execution_id: str,
        blueprint: str,
    ):
        """Trace an entire agent execution."""
        async with self._provider.start_span(
            "agent_execution",
            {
                "agent.id": agent_id,
                "agent.tenant_id": tenant_id,
                "agent.execution_id": execution_id,
                "agent.blueprint": blueprint,
            },
        ) as span:
            yield span

    @asynccontextmanager
    async def trace_step(
        self,
        agent_id: str,
        step_number: int,
        action: str,
    ):
        """Trace an agent step."""
        async with self._provider.start_span(
            f"agent_step_{action}",
            {
                "agent.id": agent_id,
                "step.number": step_number,
                "step.action": action,
            },
        ) as span:
            yield span

    @asynccontextmanager
    async def trace_llm_call(
        self,
        agent_id: str,
        model: str,
        prompt_tokens: int | None = None,
    ):
        """Trace an LLM API call."""
        attrs = {
            "agent.id": agent_id,
            "llm.model": model,
        }
        if prompt_tokens:
            attrs["llm.prompt_tokens"] = prompt_tokens

        async with self._provider.start_span("llm_call", attrs) as span:
            yield span

    @asynccontextmanager
    async def trace_vector_query(
        self,
        agent_id: str,
        query_text: str,
        top_k: int,
    ):
        """Trace a vector store query."""
        async with self._provider.start_span(
            "vector_query",
            {
                "agent.id": agent_id,
                "query.length": len(query_text),
                "query.top_k": top_k,
            },
        ) as span:
            yield span

    @asynccontextmanager
    async def trace_hitl_request(
        self,
        agent_id: str,
        request_id: str,
        request_type: str,
    ):
        """Trace a HITL request."""
        async with self._provider.start_span(
            "hitl_request",
            {
                "agent.id": agent_id,
                "hitl.request_id": request_id,
                "hitl.type": request_type,
            },
        ) as span:
            yield span
