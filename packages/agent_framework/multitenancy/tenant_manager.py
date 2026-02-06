"""
Tenant Manager - Central management for multi-tenant deployments.

Handles:
- Tenant lifecycle (create, activate, suspend, delete)
- Resource allocation and limits
- Cross-tenant isolation
- Tenant discovery and lookup
"""

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import Any, Optional

from ..core.agent_registry import AgentRegistry
from ..governance.audit import AuditEventType, AuditLogger
from .tenant import Tenant, TenantConfig, TenantLimits, TenantStatus, TenantTier


class TenantManager:
    """
    Central manager for multi-tenant agent deployments.

    Provides:
    - Tenant CRUD operations
    - Usage tracking and enforcement
    - Rate limiting
    - Tenant isolation
    """

    _instance: Optional["TenantManager"] = None

    def __new__(cls) -> "TenantManager":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._tenants: dict[str, Tenant] = {}
        self._tenant_by_api_key: dict[str, str] = {}
        self._registry: AgentRegistry | None = None
        self._audit_logger: AuditLogger | None = None
        self._rate_limit_task: asyncio.Task | None = None
        self._on_tenant_change_callbacks: list[Callable] = []
        self._initialized = True

    def set_registry(self, registry: AgentRegistry) -> None:
        """Set the agent registry for tenant-agent coordination."""
        self._registry = registry

    def set_audit_logger(self, logger: AuditLogger) -> None:
        """Set the audit logger."""
        self._audit_logger = logger

    def on_tenant_change(self, callback: Callable) -> None:
        """Register callback for tenant changes."""
        self._on_tenant_change_callbacks.append(callback)

    async def _notify_change(self, tenant: Tenant, event: str) -> None:
        """Notify callbacks of tenant change."""
        for callback in self._on_tenant_change_callbacks:
            try:
                result = callback(tenant, event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                print(f"Tenant change callback error: {e}")

    async def _log_event(
        self,
        event_type: AuditEventType,
        tenant_id: str,
        details: dict[str, Any],
    ) -> None:
        """Log tenant event."""
        if self._audit_logger:
            await self._audit_logger.log_agent_event(
                event_type=event_type,
                agent_id="",
                tenant_id=tenant_id,
                details=details,
            )

    async def create_tenant(
        self,
        name: str,
        tier: TenantTier = TenantTier.STARTER,
        owner_id: str | None = None,
        allowed_blueprints: list[str] | None = None,
        custom_limits: TenantLimits | None = None,
        settings: dict[str, Any] | None = None,
        auto_activate: bool = False,
    ) -> Tenant:
        """
        Create a new tenant.

        Args:
            name: Tenant name
            tier: Subscription tier
            owner_id: Owner user ID
            allowed_blueprints: List of allowed agent blueprints
            custom_limits: Custom resource limits
            settings: Additional settings
            auto_activate: Activate immediately

        Returns:
            Created tenant
        """
        config = TenantConfig(
            name=name,
            tier=tier,
            allowed_blueprints=allowed_blueprints or [],
            custom_limits=custom_limits,
            settings=settings or {},
        )

        tenant = Tenant(
            config=config,
            owner_id=owner_id,
            status=TenantStatus.ACTIVE if auto_activate else TenantStatus.PENDING,
        )

        if auto_activate:
            tenant.activated_at = datetime.utcnow()

        self._tenants[tenant.tenant_id] = tenant

        await self._log_event(
            AuditEventType.AGENT_CREATED,
            tenant.tenant_id,
            {"event": "tenant_created", "name": name, "tier": tier.value},
        )

        await self._notify_change(tenant, "created")

        return tenant

    def get_tenant(self, tenant_id: str) -> Tenant | None:
        """Get a tenant by ID."""
        return self._tenants.get(tenant_id)

    def get_tenant_by_api_key(self, api_key_hash: str) -> Tenant | None:
        """Get a tenant by API key hash."""
        tenant_id = self._tenant_by_api_key.get(api_key_hash)
        if tenant_id:
            return self._tenants.get(tenant_id)
        return None

    def list_tenants(
        self,
        status: TenantStatus | None = None,
        tier: TenantTier | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Tenant]:
        """List tenants with optional filters."""
        tenants = list(self._tenants.values())

        if status:
            tenants = [t for t in tenants if t.status == status]

        if tier:
            tenants = [t for t in tenants if t.tier == tier]

        tenants.sort(key=lambda t: t.created_at, reverse=True)

        return tenants[offset : offset + limit]

    async def activate_tenant(self, tenant_id: str) -> bool:
        """Activate a tenant."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False

        tenant.activate()

        await self._log_event(
            AuditEventType.AGENT_UPDATED,
            tenant_id,
            {"event": "tenant_activated"},
        )

        await self._notify_change(tenant, "activated")

        return True

    async def suspend_tenant(self, tenant_id: str, reason: str = "") -> bool:
        """Suspend a tenant."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False

        tenant.suspend(reason)

        if self._registry:
            agents = self._registry.get_tenant_agents(tenant_id)
            for agent in agents:
                if agent.state and agent.state.status.value == "running":
                    pass

        await self._log_event(
            AuditEventType.AGENT_UPDATED,
            tenant_id,
            {"event": "tenant_suspended", "reason": reason},
        )

        await self._notify_change(tenant, "suspended")

        return True

    async def update_tenant(
        self,
        tenant_id: str,
        name: str | None = None,
        tier: TenantTier | None = None,
        allowed_blueprints: list[str] | None = None,
        custom_limits: TenantLimits | None = None,
        settings: dict[str, Any] | None = None,
    ) -> Tenant | None:
        """Update tenant configuration."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return None

        if name:
            tenant.config.name = name
        if tier:
            tenant.config.tier = tier
        if allowed_blueprints is not None:
            tenant.config.allowed_blueprints = allowed_blueprints
        if custom_limits:
            tenant.config.custom_limits = custom_limits
        if settings:
            tenant.config.settings.update(settings)

        tenant.updated_at = datetime.utcnow()

        await self._log_event(
            AuditEventType.AGENT_UPDATED,
            tenant_id,
            {"event": "tenant_updated"},
        )

        await self._notify_change(tenant, "updated")

        return tenant

    async def delete_tenant(self, tenant_id: str, force: bool = False) -> bool:
        """
        Delete a tenant.

        Args:
            tenant_id: Tenant to delete
            force: Force delete even if tenant has active agents

        Returns:
            True if deleted
        """
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False

        if self._registry and not force:
            agents = self._registry.get_tenant_agents(tenant_id)
            if agents:
                raise RuntimeError(
                    f"Cannot delete tenant with {len(agents)} active agents. "
                    "Use force=True to override."
                )

        if self._registry:
            agents = self._registry.get_tenant_agents(tenant_id)
            for agent in agents:
                self._registry.remove_agent(agent.agent_id)

        del self._tenants[tenant_id]

        keys_to_remove = [k for k, v in self._tenant_by_api_key.items() if v == tenant_id]
        for key in keys_to_remove:
            del self._tenant_by_api_key[key]

        await self._log_event(
            AuditEventType.AGENT_DELETED,
            tenant_id,
            {"event": "tenant_deleted", "force": force},
        )

        return True

    def set_api_key(self, tenant_id: str, api_key_hash: str) -> bool:
        """Set API key for a tenant."""
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False

        if tenant.config.api_key_hash:
            old_hash = tenant.config.api_key_hash
            if old_hash in self._tenant_by_api_key:
                del self._tenant_by_api_key[old_hash]

        tenant.config.api_key_hash = api_key_hash
        self._tenant_by_api_key[api_key_hash] = tenant_id

        return True

    def check_limit(self, tenant_id: str, metric: str) -> bool:
        """
        Check if tenant is within limits for a metric.

        Args:
            tenant_id: Tenant to check
            metric: Metric name (agents, concurrent_executions, etc.)

        Returns:
            True if within limits
        """
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False

        if not tenant.is_active():
            return False

        limits = tenant.limits
        usage = tenant._current_usage.get(metric, 0)

        limit_map = {
            "agents": limits.max_agents,
            "concurrent_executions": limits.max_concurrent_executions,
            "requests_this_minute": limits.max_requests_per_minute,
            "storage_mb": limits.max_storage_mb,
            "vector_documents": limits.max_vector_documents,
            "hitl_queue_size": limits.max_hitl_queue_size,
        }

        limit = limit_map.get(metric)
        if limit is None:
            return True

        return usage < limit

    def record_usage(self, tenant_id: str, metric: str, amount: int = 1) -> bool:
        """
        Record usage for a tenant.

        Args:
            tenant_id: Tenant ID
            metric: Metric name
            amount: Amount to add

        Returns:
            True if recorded (within limits)
        """
        if not self.check_limit(tenant_id, metric):
            return False

        tenant = self._tenants.get(tenant_id)
        if tenant:
            tenant.increment_usage(metric, amount)
            return True
        return False

    def release_usage(self, tenant_id: str, metric: str, amount: int = 1) -> None:
        """Release usage for a tenant."""
        tenant = self._tenants.get(tenant_id)
        if tenant:
            tenant.decrement_usage(metric, amount)

    def get_usage(self, tenant_id: str) -> dict[str, Any] | None:
        """Get usage statistics for a tenant."""
        tenant = self._tenants.get(tenant_id)
        if tenant:
            return tenant.get_usage()
        return None

    async def _reset_rate_limits(self) -> None:
        """Reset rate limits for all tenants (called every minute)."""
        for tenant in self._tenants.values():
            tenant.reset_rate_limit()

    async def start_rate_limit_reset(self) -> None:
        """Start background task to reset rate limits."""

        async def reset_loop():
            while True:
                await asyncio.sleep(60)
                await self._reset_rate_limits()

        self._rate_limit_task = asyncio.create_task(reset_loop())

    def stop_rate_limit_reset(self) -> None:
        """Stop rate limit reset task."""
        if self._rate_limit_task:
            self._rate_limit_task.cancel()
            self._rate_limit_task = None

    def get_stats(self) -> dict[str, Any]:
        """Get overall tenant statistics."""
        tenants = list(self._tenants.values())

        by_status = {}
        for status in TenantStatus:
            by_status[status.value] = len([t for t in tenants if t.status == status])

        by_tier = {}
        for tier in TenantTier:
            by_tier[tier.value] = len([t for t in tenants if t.tier == tier])

        total_agents = 0
        if self._registry:
            total_agents = len(self._registry._agents)

        return {
            "total_tenants": len(tenants),
            "by_status": by_status,
            "by_tier": by_tier,
            "total_agents": total_agents,
        }

    def reset(self) -> None:
        """Reset manager state (for testing)."""
        self._tenants.clear()
        self._tenant_by_api_key.clear()
        if self._rate_limit_task:
            self._rate_limit_task.cancel()
            self._rate_limit_task = None
