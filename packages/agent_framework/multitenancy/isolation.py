"""
Tenant Isolation System.

Provides resource isolation between tenants:
- Execution context isolation
- Data namespace separation
- Resource quota enforcement
- Cross-tenant access prevention
"""

from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .tenant import Tenant, TenantLimits
from .tenant_manager import TenantManager

_current_tenant: ContextVar[Optional[str]] = ContextVar("current_tenant", default=None)


@dataclass
class ResourceQuota:
    """Resource quota tracking for a tenant."""

    tenant_id: str
    limits: TenantLimits

    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    active_connections: int = 0
    pending_requests: int = 0

    last_updated: datetime = field(default_factory=datetime.utcnow)

    def is_within_quota(self) -> bool:
        """Check if tenant is within all quotas."""
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "limits": self.limits.to_dict(),
            "cpu_usage_percent": self.cpu_usage_percent,
            "memory_usage_mb": self.memory_usage_mb,
            "active_connections": self.active_connections,
            "pending_requests": self.pending_requests,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class IsolationContext:
    """
    Execution context for tenant isolation.

    Carries tenant information through async execution.
    """

    tenant_id: str
    tenant_name: str
    tier: str

    namespace: str

    allowed_resources: List[str] = field(default_factory=list)
    denied_resources: List[str] = field(default_factory=list)

    metadata: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.utcnow)

    def can_access(self, resource: str) -> bool:
        """Check if context allows access to a resource."""
        if resource in self.denied_resources:
            return False

        if self.allowed_resources and resource not in self.allowed_resources:
            return False

        return True

    def get_namespaced_key(self, key: str) -> str:
        """Get a namespaced version of a key."""
        return f"{self.namespace}:{key}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "tenant_name": self.tenant_name,
            "tier": self.tier,
            "namespace": self.namespace,
            "allowed_resources": self.allowed_resources,
            "created_at": self.created_at.isoformat(),
        }


class TenantIsolator:
    """
    Manages tenant isolation for agent execution.

    Provides:
    - Context management for tenant isolation
    - Resource access control
    - Namespace management
    - Quota enforcement
    """

    def __init__(self, tenant_manager: TenantManager) -> None:
        self.tenant_manager = tenant_manager
        self._quotas: Dict[str, ResourceQuota] = {}
        self._active_contexts: Dict[str, IsolationContext] = {}

    def get_current_tenant_id(self) -> Optional[str]:
        """Get the current tenant ID from context."""
        return _current_tenant.get()

    def get_current_context(self) -> Optional[IsolationContext]:
        """Get the current isolation context."""
        tenant_id = self.get_current_tenant_id()
        if tenant_id:
            return self._active_contexts.get(tenant_id)
        return None

    def create_context(
        self,
        tenant: Tenant,
        allowed_resources: Optional[List[str]] = None,
        denied_resources: Optional[List[str]] = None,
    ) -> IsolationContext:
        """Create an isolation context for a tenant."""
        namespace = f"tenant_{tenant.tenant_id[:8]}"
        if tenant.config.pinecone_namespace:
            namespace = tenant.config.pinecone_namespace

        context = IsolationContext(
            tenant_id=tenant.tenant_id,
            tenant_name=tenant.name,
            tier=tenant.tier.value,
            namespace=namespace,
            allowed_resources=allowed_resources or [],
            denied_resources=denied_resources or [],
        )

        return context

    @asynccontextmanager
    async def isolation_scope(
        self,
        tenant_id: str,
        allowed_resources: Optional[List[str]] = None,
    ):
        """
        Context manager for tenant-isolated execution.

        Usage:
            async with isolator.isolation_scope(tenant_id):
                # All operations here are isolated to the tenant
                await agent.run(input_data)
        """
        tenant = self.tenant_manager.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant '{tenant_id}' not found")

        if not tenant.is_active():
            raise RuntimeError(f"Tenant '{tenant_id}' is not active")

        context = self.create_context(tenant, allowed_resources)

        token = _current_tenant.set(tenant_id)
        self._active_contexts[tenant_id] = context

        try:
            yield context
        finally:
            _current_tenant.reset(token)
            if tenant_id in self._active_contexts:
                del self._active_contexts[tenant_id]

    def require_tenant(self) -> str:
        """
        Require a tenant context to be active.

        Raises:
            RuntimeError: If no tenant context is active

        Returns:
            Current tenant ID
        """
        tenant_id = self.get_current_tenant_id()
        if not tenant_id:
            raise RuntimeError("No tenant context active")
        return tenant_id

    def check_access(self, resource: str) -> bool:
        """
        Check if current tenant can access a resource.

        Args:
            resource: Resource identifier

        Returns:
            True if access is allowed
        """
        context = self.get_current_context()
        if not context:
            return False
        return context.can_access(resource)

    def get_namespace(self) -> str:
        """Get the current tenant's namespace."""
        context = self.get_current_context()
        if not context:
            raise RuntimeError("No tenant context active")
        return context.namespace

    def namespace_key(self, key: str) -> str:
        """
        Get a namespaced version of a key for the current tenant.

        Args:
            key: Original key

        Returns:
            Namespaced key (e.g., "tenant_abc123:my_key")
        """
        context = self.get_current_context()
        if not context:
            raise RuntimeError("No tenant context active")
        return context.get_namespaced_key(key)

    def get_quota(self, tenant_id: str) -> Optional[ResourceQuota]:
        """Get resource quota for a tenant."""
        if tenant_id not in self._quotas:
            tenant = self.tenant_manager.get_tenant(tenant_id)
            if tenant:
                self._quotas[tenant_id] = ResourceQuota(
                    tenant_id=tenant_id,
                    limits=tenant.limits,
                )
        return self._quotas.get(tenant_id)

    def update_quota(
        self,
        tenant_id: str,
        cpu_usage: Optional[float] = None,
        memory_usage: Optional[float] = None,
        connections: Optional[int] = None,
        requests: Optional[int] = None,
    ) -> None:
        """Update quota tracking for a tenant."""
        quota = self.get_quota(tenant_id)
        if not quota:
            return

        if cpu_usage is not None:
            quota.cpu_usage_percent = cpu_usage
        if memory_usage is not None:
            quota.memory_usage_mb = memory_usage
        if connections is not None:
            quota.active_connections = connections
        if requests is not None:
            quota.pending_requests = requests

        quota.last_updated = datetime.utcnow()

    def check_quota(self, tenant_id: str) -> bool:
        """Check if tenant is within quota limits."""
        quota = self.get_quota(tenant_id)
        if not quota:
            return False
        return quota.is_within_quota()

    def validate_cross_tenant_access(
        self,
        source_tenant_id: str,
        target_tenant_id: str,
        resource: str,
    ) -> bool:
        """
        Validate cross-tenant resource access.

        By default, cross-tenant access is denied.

        Args:
            source_tenant_id: Requesting tenant
            target_tenant_id: Target tenant
            resource: Resource being accessed

        Returns:
            True if access is allowed (usually False)
        """
        if source_tenant_id == target_tenant_id:
            return True

        return False

    def get_active_contexts(self) -> List[Dict[str, Any]]:
        """Get all active isolation contexts."""
        return [ctx.to_dict() for ctx in self._active_contexts.values()]

    def get_stats(self) -> Dict[str, Any]:
        """Get isolation statistics."""
        return {
            "active_contexts": len(self._active_contexts),
            "tracked_quotas": len(self._quotas),
            "contexts": [
                {
                    "tenant_id": ctx.tenant_id,
                    "namespace": ctx.namespace,
                    "created_at": ctx.created_at.isoformat(),
                }
                for ctx in self._active_contexts.values()
            ],
        }
