"""
Enterprise Agent Framework for Support101.

Provides:
- Agent Template System (swappable blueprints)
- Human-in-the-Loop Queue (escalation management)
- Multi-Tenant Agent Deployment (isolated instances)
- Agent Governance (audit trails, permissions)

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

from .sdk import AgentFramework, create_framework

from .core.base_agent import BaseAgent, AgentConfig, AgentState, AgentStatus, Tool
from .core.agent_registry import AgentRegistry, AgentBlueprint
from .core.agent_executor import AgentExecutor

from .templates.support_agent import SupportAgentBlueprint, SupportAgent
from .templates.triage_agent import TriageAgentBlueprint, TriageAgent

from .governance.permissions import AgentPermissions, Permission, PermissionLevel
from .governance.audit import AuditLogger, AuditEvent, AuditEventType

from .hitl.queue import HITLQueue, HITLRequest, HITLPriority, HITLRequestType
from .hitl.manager import HITLManager
from .hitl.escalation import EscalationManager, EscalationPolicy, EscalationLevel

from .multitenancy.tenant import Tenant, TenantConfig, TenantTier, TenantStatus
from .multitenancy.tenant_manager import TenantManager
from .multitenancy.isolation import TenantIsolator, IsolationContext

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
]
