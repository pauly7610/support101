"""
Enterprise Agent Framework SDK.

Main entry point for using the agent framework.
Provides a unified interface for all framework capabilities.
"""

from typing import Any, Callable, Dict, List, Optional

from .core.agent_registry import AgentBlueprint, AgentRegistry
from .core.agent_executor import AgentExecutor
from .core.base_agent import AgentConfig, AgentState, AgentStatus, BaseAgent, Tool
from .governance.audit import AuditEventType, AuditLogger
from .governance.permissions import AgentPermissions, Permission, PermissionLevel
from .hitl.manager import HITLManager
from .hitl.queue import HITLPriority, HITLQueue, HITLRequestType
from .hitl.escalation import EscalationLevel, EscalationManager, EscalationPolicy
from .multitenancy.tenant import Tenant, TenantConfig, TenantTier
from .multitenancy.tenant_manager import TenantManager
from .multitenancy.isolation import IsolationContext, TenantIsolator
from .templates.support_agent import SupportAgentBlueprint
from .templates.triage_agent import TriageAgentBlueprint


class AgentFramework:
    """
    Main SDK class for the Enterprise Agent Framework.
    
    Provides unified access to:
    - Agent registry and blueprints
    - Agent execution
    - Human-in-the-loop management
    - Multi-tenant deployment
    - Governance and audit
    
    Usage:
        framework = AgentFramework()
        
        # Create a tenant
        tenant = await framework.create_tenant("Acme Corp", tier="professional")
        
        # Create an agent
        agent = framework.create_agent(
            blueprint="support_agent",
            tenant_id=tenant.tenant_id,
            name="Support Bot"
        )
        
        # Execute the agent
        result = await framework.execute(agent, {"query": "How do I reset my password?"})
    """
    
    def __init__(self) -> None:
        self.registry = AgentRegistry()
        self.tenant_manager = TenantManager()
        self.audit_logger = AuditLogger()
        self.permissions = AgentPermissions()
        
        self.executor = AgentExecutor(self.registry)
        self.executor.set_audit_callback(self._audit_execution_event)
        
        self.hitl_manager = HITLManager(
            registry=self.registry,
            audit_logger=self.audit_logger,
        )
        
        self.isolator = TenantIsolator(self.tenant_manager)
        
        self.tenant_manager.set_registry(self.registry)
        self.tenant_manager.set_audit_logger(self.audit_logger)
        
        self._register_default_blueprints()
    
    def _register_default_blueprints(self) -> None:
        """Register built-in agent blueprints."""
        self.registry.register_blueprint(SupportAgentBlueprint)
        self.registry.register_blueprint(TriageAgentBlueprint)
    
    async def _audit_execution_event(self, event: Dict[str, Any]) -> None:
        """Callback for execution audit events."""
        event_type_map = {
            "execution_started": AuditEventType.EXECUTION_STARTED,
            "execution_completed": AuditEventType.EXECUTION_COMPLETED,
            "execution_failed": AuditEventType.EXECUTION_FAILED,
            "execution_timeout": AuditEventType.EXECUTION_TIMEOUT,
            "execution_cancelled": AuditEventType.EXECUTION_CANCELLED,
            "human_feedback_provided": AuditEventType.HUMAN_FEEDBACK_PROVIDED,
        }
        
        event_type = event_type_map.get(
            event.get("event_type", ""),
            AuditEventType.STEP_EXECUTED,
        )
        
        await self.audit_logger.log_execution_event(
            event_type=event_type,
            agent_id=event.get("agent_id", ""),
            tenant_id=event.get("tenant_id", ""),
            execution_id=event.get("execution_id", ""),
            details=event.get("details", {}),
        )
    
    def register_blueprint(self, blueprint: AgentBlueprint) -> None:
        """Register a custom agent blueprint."""
        self.registry.register_blueprint(blueprint)
    
    def list_blueprints(self) -> List[Dict[str, Any]]:
        """List all available blueprints."""
        return self.registry.list_blueprints()
    
    async def create_tenant(
        self,
        name: str,
        tier: str = "starter",
        owner_id: Optional[str] = None,
        auto_activate: bool = True,
    ) -> Tenant:
        """Create a new tenant."""
        tenant_tier = TenantTier(tier)
        return await self.tenant_manager.create_tenant(
            name=name,
            tier=tenant_tier,
            owner_id=owner_id,
            auto_activate=auto_activate,
        )
    
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get a tenant by ID."""
        return self.tenant_manager.get_tenant(tenant_id)
    
    def create_agent(
        self,
        blueprint: str,
        tenant_id: str,
        name: str,
        config_overrides: Optional[Dict[str, Any]] = None,
    ) -> BaseAgent:
        """
        Create a new agent from a blueprint.
        
        Args:
            blueprint: Name of the blueprint to use
            tenant_id: Tenant ID for isolation
            name: Human-readable agent name
            config_overrides: Optional configuration overrides
            
        Returns:
            Created agent instance
        """
        tenant = self.tenant_manager.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant '{tenant_id}' not found")
        
        if not tenant.is_active():
            raise RuntimeError(f"Tenant '{tenant_id}' is not active")
        
        if not tenant.can_create_agent():
            raise RuntimeError("Agent limit reached for tenant")
        
        agent = self.registry.create_agent(
            blueprint_name=blueprint,
            tenant_id=tenant_id,
            agent_name=name,
            config_overrides=config_overrides,
        )
        
        tenant.increment_usage("agents")
        
        self.permissions.assign_role(agent.agent_id, "support_agent")
        
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get an agent by ID."""
        return self.registry.get_agent(agent_id)
    
    def list_agents(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[AgentStatus] = None,
    ) -> List[Dict[str, Any]]:
        """List agents with optional filters."""
        return self.registry.list_agents(tenant_id=tenant_id, status=status)
    
    async def execute(
        self,
        agent: BaseAgent,
        input_data: Dict[str, Any],
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Execute an agent with tenant isolation.
        
        Args:
            agent: Agent to execute
            input_data: Input data for the agent
            timeout: Optional timeout override
            
        Returns:
            Execution result
        """
        tenant = self.tenant_manager.get_tenant(agent.tenant_id)
        if tenant:
            if not tenant.is_active():
                raise RuntimeError("Tenant is not active")
            if not tenant.can_execute():
                raise RuntimeError("Concurrent execution limit reached")
            if not tenant.check_rate_limit():
                raise RuntimeError("Rate limit exceeded")
            
            tenant.increment_usage("concurrent_executions")
            tenant.increment_usage("requests_this_minute")
        
        try:
            async with self.isolator.isolation_scope(agent.tenant_id):
                result = await self.executor.execute(agent, input_data, timeout)
                return result.to_dict()
        finally:
            if tenant:
                tenant.decrement_usage("concurrent_executions")
    
    async def execute_by_id(
        self,
        agent_id: str,
        input_data: Dict[str, Any],
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute an agent by its ID."""
        agent = self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent '{agent_id}' not found")
        return await self.execute(agent, input_data, timeout)
    
    async def request_human_approval(
        self,
        agent: BaseAgent,
        action: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Request human approval for an agent action.
        
        Returns:
            HITL request ID
        """
        request = await self.hitl_manager.request_approval(agent, action, context)
        return request.request_id
    
    async def provide_human_response(
        self,
        request_id: str,
        response: Dict[str, Any],
        reviewer_id: str,
    ) -> bool:
        """Provide a response to a HITL request."""
        return await self.hitl_manager.provide_response(
            request_id=request_id,
            response=response,
            reviewer_id=reviewer_id,
        )
    
    def get_pending_hitl_requests(
        self,
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get pending HITL requests."""
        return self.hitl_manager.get_pending_requests(tenant_id=tenant_id)
    
    async def escalate(
        self,
        agent: BaseAgent,
        reason: str,
        level: str = "l2",
    ) -> Dict[str, Any]:
        """Escalate an agent's task."""
        esc_level = EscalationLevel(level)
        return await self.hitl_manager.escalate(agent, reason, esc_level)
    
    def grant_permission(
        self,
        agent_id: str,
        resource: str,
        level: str,
        tenant_id: Optional[str] = None,
    ) -> None:
        """Grant a permission to an agent."""
        perm_level = PermissionLevel(level)
        permission = Permission(resource=resource, level=perm_level)
        self.permissions.grant_permission(agent_id, permission, tenant_id)
    
    def check_permission(
        self,
        agent_id: str,
        resource: str,
        level: str,
        tenant_id: Optional[str] = None,
    ) -> bool:
        """Check if an agent has a permission."""
        perm_level = PermissionLevel(level)
        return self.permissions.check_permission(
            agent_id=agent_id,
            resource=resource,
            required_level=perm_level,
            tenant_id=tenant_id,
        )
    
    def get_audit_history(
        self,
        agent_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get audit history."""
        if agent_id:
            return self.audit_logger.get_agent_history(agent_id, limit)
        
        events = self.audit_logger.query(tenant_id=tenant_id, limit=limit)
        return [e.to_dict() for e in events]
    
    def get_governance_dashboard(
        self,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get governance dashboard data."""
        agents = self.list_agents(tenant_id=tenant_id)
        
        active = [a for a in agents if a.get("status") == "running"]
        awaiting = [a for a in agents if a.get("status") == "awaiting_human"]
        
        return {
            "agents": {
                "total": len(agents),
                "active": len(active),
                "awaiting_human": len(awaiting),
            },
            "hitl": self.hitl_manager.get_stats(tenant_id),
            "audit": self.audit_logger.get_stats(tenant_id),
            "tenants": self.tenant_manager.get_stats() if not tenant_id else None,
        }
    
    async def start(self) -> None:
        """Start background services."""
        await self.hitl_manager.start()
        await self.tenant_manager.start_rate_limit_reset()
    
    def stop(self) -> None:
        """Stop background services."""
        self.hitl_manager.stop()
        self.tenant_manager.stop_rate_limit_reset()


def create_framework() -> AgentFramework:
    """Factory function to create an AgentFramework instance."""
    return AgentFramework()
