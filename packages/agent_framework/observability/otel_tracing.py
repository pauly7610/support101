"""
OpenTelemetry-based LLM tracing using OpenLLMetry / Traceloop.

Replaces placeholder observability stubs with real distributed tracing.
Gracefully degrades when traceloop-sdk or opentelemetry packages are
not installed.

Environment variables:
    TRACELOOP_API_KEY: Traceloop cloud API key (optional — traces go to OTEL collector if unset)
    OTEL_EXPORTER_OTLP_ENDPOINT: OTLP collector endpoint (default: http://localhost:4318)
    OTEL_SERVICE_NAME: Service name for traces (default: support101-agent-framework)
    TRACELOOP_ENABLED: Set to "false" to disable tracing (default: true)
"""

import logging
import os
import time
from collections.abc import Generator
from contextlib import contextmanager, suppress
from typing import Any

logger = logging.getLogger(__name__)

_initialized = False
_tracer = None


def _is_enabled() -> bool:
    """Check if tracing is enabled via environment."""
    return os.getenv("TRACELOOP_ENABLED", "true").lower() != "false"


def initialize_tracing(
    service_name: str | None = None,
    api_key: str | None = None,
) -> bool:
    """
    Initialize OpenTelemetry tracing with Traceloop SDK.

    Returns True if initialization succeeded, False otherwise.
    """
    global _initialized, _tracer

    if _initialized:
        return True

    if not _is_enabled():
        logger.info("Tracing disabled via TRACELOOP_ENABLED=false")
        return False

    svc_name = service_name or os.getenv("OTEL_SERVICE_NAME", "support101-agent-framework")
    key = api_key or os.getenv("TRACELOOP_API_KEY")

    try:
        from traceloop.sdk import Traceloop

        Traceloop.init(
            app_name=svc_name,
            api_key=key,
            disable_batch=False,
        )
        _initialized = True
        logger.info("Traceloop tracing initialized for service: %s", svc_name)
        return True
    except ImportError:
        logger.debug("traceloop-sdk not installed, trying raw opentelemetry")

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": svc_name})
        provider = TracerProvider(resource=resource)

        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")

        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces")
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except ImportError:
            logger.debug("OTLP HTTP exporter not available, traces will be in-memory only")

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(svc_name)
        _initialized = True
        logger.info("OpenTelemetry tracing initialized for service: %s", svc_name)
        return True
    except ImportError:
        logger.info("OpenTelemetry not installed — tracing disabled")
        return False


def get_tracer():
    """Get the current tracer instance, or None if not initialized."""
    global _tracer
    if _tracer:
        return _tracer
    try:
        from opentelemetry import trace

        return trace.get_tracer("support101-agent-framework")
    except ImportError:
        return None


class SpanContext:
    """Lightweight span wrapper that no-ops when tracing is unavailable."""

    def __init__(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self.name = name
        self.attributes = attributes or {}
        self._span = None
        self._start_time = time.time()

    def set_attribute(self, key: str, value: Any) -> None:
        """Set an attribute on the span."""
        self.attributes[key] = value
        if self._span:
            with suppress(Exception):
                self._span.set_attribute(
                    key,
                    (str(value) if not isinstance(value, (str, int, float, bool)) else value),
                )

    def set_status_ok(self) -> None:
        """Mark span as successful."""
        if self._span:
            try:
                from opentelemetry.trace import StatusCode

                self._span.set_status(StatusCode.OK)
            except (ImportError, Exception):
                pass

    def set_status_error(self, message: str) -> None:
        """Mark span as errored."""
        if self._span:
            try:
                from opentelemetry.trace import StatusCode

                self._span.set_status(StatusCode.ERROR, message)
            except (ImportError, Exception):
                pass

    def record_exception(self, exc: Exception) -> None:
        """Record an exception on the span."""
        if self._span:
            with suppress(Exception):
                self._span.record_exception(exc)

    @property
    def duration_ms(self) -> float:
        return (time.time() - self._start_time) * 1000


@contextmanager
def trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
) -> Generator[SpanContext, None, None]:
    """
    Context manager for creating a traced span.

    Usage:
        with trace_span("rag.generate", {"query": question}) as span:
            result = await chain.generate(question)
            span.set_attribute("tokens", result.token_count)
    """
    ctx = SpanContext(name, attributes)
    tracer = get_tracer()

    if tracer:
        try:
            with tracer.start_as_current_span(name) as span:
                ctx._span = span
                for k, v in (attributes or {}).items():
                    safe_v = str(v) if not isinstance(v, (str, int, float, bool)) else v
                    span.set_attribute(k, safe_v)
                yield ctx
                span.set_attribute("duration_ms", ctx.duration_ms)
        except Exception as e:
            logger.debug("Tracing span error: %s", e)
            yield ctx
    else:
        yield ctx


@contextmanager
def trace_llm_call(
    model: str,
    prompt_tokens: int | None = None,
    provider: str = "openai",
) -> Generator[SpanContext, None, None]:
    """
    Specialized span for LLM API calls.

    Automatically records model, provider, token counts, and latency.
    """
    attrs = {
        "llm.model": model,
        "llm.provider": provider,
        "gen_ai.system": provider,
        "gen_ai.request.model": model,
    }
    if prompt_tokens is not None:
        attrs["gen_ai.usage.prompt_tokens"] = prompt_tokens

    with trace_span(f"llm.{provider}.chat", attrs) as span:
        yield span


@contextmanager
def trace_vector_search(
    index_name: str,
    query_text: str,
    top_k: int = 5,
) -> Generator[SpanContext, None, None]:
    """Specialized span for vector store queries."""
    attrs = {
        "db.system": "pinecone",
        "db.operation": "query",
        "db.pinecone.index": index_name,
        "db.pinecone.top_k": top_k,
        "db.statement": query_text[:200],
    }
    with trace_span("vector_store.query", attrs) as span:
        yield span


@contextmanager
def trace_agent_execution(
    agent_id: str,
    blueprint: str,
    tenant_id: str = "",
) -> Generator[SpanContext, None, None]:
    """Specialized span for agent execution."""
    attrs = {
        "agent.id": agent_id,
        "agent.blueprint": blueprint,
        "agent.tenant_id": tenant_id,
    }
    with trace_span(f"agent.execute.{blueprint}", attrs) as span:
        yield span


@contextmanager
def trace_tool_call(
    tool_name: str,
    arguments: dict[str, Any] | None = None,
) -> Generator[SpanContext, None, None]:
    """Specialized span for tool invocations."""
    attrs = {
        "tool.name": tool_name,
        "tool.arguments_count": len(arguments) if arguments else 0,
    }
    with trace_span(f"tool.{tool_name}", attrs) as span:
        yield span


# ── Prometheus Metrics Integration ───────────────────────────────

_metrics_initialized = False


def initialize_metrics() -> bool:
    """
    Initialize Prometheus metrics for LLM observability.

    Metrics:
    - llm_request_duration_seconds: Histogram of LLM call latency
    - llm_token_usage_total: Counter of tokens used
    - agent_execution_duration_seconds: Histogram of agent execution time
    - vector_store_query_duration_seconds: Histogram of vector search latency
    """
    global _metrics_initialized
    if _metrics_initialized:
        return True

    try:
        from prometheus_client import Counter, Histogram

        globals()["llm_request_duration"] = Histogram(
            "llm_request_duration_seconds",
            "LLM API call duration in seconds",
            ["model", "provider", "status"],
        )
        globals()["llm_token_usage"] = Counter(
            "llm_token_usage_total",
            "Total tokens used in LLM calls",
            ["model", "provider", "type"],
        )
        globals()["agent_execution_duration"] = Histogram(
            "agent_execution_duration_seconds",
            "Agent execution duration in seconds",
            ["blueprint", "status"],
        )
        globals()["vector_query_duration"] = Histogram(
            "vector_store_query_duration_seconds",
            "Vector store query duration in seconds",
            ["index", "status"],
        )

        _metrics_initialized = True
        logger.info("Prometheus LLM metrics initialized")
        return True
    except ImportError:
        logger.debug("prometheus_client not installed — metrics disabled")
        return False
