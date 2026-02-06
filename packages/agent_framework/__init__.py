"""
Enterprise Agent Framework for Support101.

Provides:
- Agent Template System (swappable blueprints)
- Human-in-the-Loop Queue (escalation management)
- Multi-Tenant Agent Deployment (isolated instances)
- Agent Governance (audit trails, permissions)
- Persistence Layer (Redis, Database, In-Memory)
- Resilience Patterns (Retry, Circuit Breaker)
- Observability (Prometheus metrics, OpenTelemetry tracing)
- Real-time Updates (WebSocket support)
- Configuration Validation (Pydantic schemas)

Usage:
    from packages.agent_framework import AgentFramework, create_framework

    # Create framework instance
    framework = create_framework()

    # Create a tenant
    tenant = await framework.create_tenant("Acme Corp", tier="professional")

    # Create an agent from a blueprint
    agent = framework.create_agent(
        blueprint="support_agent",
        tenant_id=tenant.tenant_id,
        name="Support Bot"
    )

    # Execute the agent
    result = await framework.execute(agent, {"query": "How do I reset my password?"})
"""

from .container import Container, Injectable, get_container
from .core.agent_executor import AgentExecutor
from .core.agent_registry import AgentBlueprint, AgentRegistry
from .core.base_agent import AgentConfig, AgentState, AgentStatus, BaseAgent, Tool
from .governance.audit import AuditEvent, AuditEventType, AuditLogger
from .governance.permissions import AgentPermissions, Permission, PermissionLevel
from .hitl.escalation import EscalationLevel, EscalationManager, EscalationPolicy
from .hitl.manager import HITLManager
from .hitl.queue import HITLPriority, HITLQueue, HITLRequest, HITLRequestType
from .multitenancy.isolation import IsolationContext, TenantIsolator
from .multitenancy.tenant import Tenant, TenantConfig, TenantStatus, TenantTier
from .multitenancy.tenant_manager import TenantManager
from .observability.evalai_tracer import (
    COMPLIANCE_PRESETS,
    EvalAICostRecord,
    EvalAIDecision,
    EvalAIGovernanceConfig,
    EvalAISpanContext,
    EvalAITracer,
    EvalAIWorkflowContext,
    EvalAIWorkflowDefinition,
    EvalAIWorkflowEdge,
    EvalAIWorkflowNode,
    check_governance,
)
from .observability.metrics import MetricsCollector, get_metrics_collector
from .observability.tracing import SpanContext, TracingProvider, trace_agent_execution
from .persistence.base import StateSerializer, StateStore
from .persistence.database import DatabaseStateStore
from .persistence.memory import InMemoryStateStore
from .persistence.redis_store import RedisStateStore
from .realtime.events import Event, EventBus, EventType, get_event_bus
from .realtime.websocket import ConnectionManager, WebSocketManager
from .resilience.circuit_breaker import CircuitBreaker, CircuitBreakerOpen, CircuitState
from .resilience.retry import (
    ExponentialBackoff,
    RetryPolicy,
    retry_with_policy,
    with_retry,
)
from .sdk import AgentFramework, create_framework
from .templates.support_agent import SupportAgent, SupportAgentBlueprint
from .templates.triage_agent import TriageAgent, TriageAgentBlueprint
from .validation.blueprint import BlueprintValidator, ValidationError, ValidationResult
from .validation.config import ConfigSchema, validate_config

__all__ = [
    # SDK
    "AgentFramework",
    "create_framework",
    # Core
    "BaseAgent",
    "AgentConfig",
    "AgentState",
    "AgentStatus",
    "Tool",
    "AgentRegistry",
    "AgentBlueprint",
    "AgentExecutor",
    # Templates
    "SupportAgentBlueprint",
    "SupportAgent",
    "TriageAgentBlueprint",
    "TriageAgent",
    # Governance
    "AgentPermissions",
    "Permission",
    "PermissionLevel",
    "AuditLogger",
    "AuditEvent",
    "AuditEventType",
    # HITL
    "HITLQueue",
    "HITLRequest",
    "HITLPriority",
    "HITLRequestType",
    "HITLManager",
    "EscalationManager",
    "EscalationPolicy",
    "EscalationLevel",
    # Multi-tenancy
    "Tenant",
    "TenantConfig",
    "TenantTier",
    "TenantStatus",
    "TenantManager",
    "TenantIsolator",
    "IsolationContext",
    # Persistence
    "StateStore",
    "StateSerializer",
    "InMemoryStateStore",
    "RedisStateStore",
    "DatabaseStateStore",
    # Resilience
    "RetryPolicy",
    "retry_with_policy",
    "ExponentialBackoff",
    "with_retry",
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerOpen",
    # Observability
    "MetricsCollector",
    "get_metrics_collector",
    "TracingProvider",
    "SpanContext",
    "trace_agent_execution",
    # EvalAI Integration
    "EvalAITracer",
    "EvalAIDecision",
    "EvalAICostRecord",
    "EvalAISpanContext",
    "EvalAIWorkflowContext",
    "EvalAIWorkflowDefinition",
    "EvalAIWorkflowNode",
    "EvalAIWorkflowEdge",
    "EvalAIGovernanceConfig",
    "COMPLIANCE_PRESETS",
    "check_governance",
    # Real-time
    "WebSocketManager",
    "ConnectionManager",
    "EventBus",
    "Event",
    "EventType",
    "get_event_bus",
    # Validation
    "BlueprintValidator",
    "ValidationError",
    "ValidationResult",
    "ConfigSchema",
    "validate_config",
    # DI Container
    "Container",
    "get_container",
    "Injectable",
]
