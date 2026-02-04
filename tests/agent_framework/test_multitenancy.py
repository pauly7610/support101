"""
Unit tests for multi-tenancy components.

Tests:
- Tenant model and configuration
- TenantManager lifecycle
- Resource limits and quotas
"""

import pytest

from packages.agent_framework.multitenancy.tenant import (
    TIER_LIMITS,
    Tenant,
    TenantConfig,
    TenantLimits,
    TenantStatus,
    TenantTier,
)
from packages.agent_framework.multitenancy.tenant_manager import TenantManager


class TestTenant:
    """Tests for Tenant model."""

    def test_default_tenant(self):
        config = TenantConfig(name="Test Tenant")
        tenant = Tenant(config=config)

        assert tenant.name == "Test Tenant"
        assert tenant.tier == TenantTier.STARTER
        assert tenant.status == TenantStatus.PENDING

    def test_tenant_activation(self):
        config = TenantConfig(name="Test")
        tenant = Tenant(config=config)

        tenant.activate()

        assert tenant.status == TenantStatus.ACTIVE
        assert tenant.activated_at is not None

    def test_tenant_suspension(self):
        config = TenantConfig(name="Test")
        tenant = Tenant(config=config)
        tenant.activate()

        tenant.suspend("Policy violation")

        assert tenant.status == TenantStatus.SUSPENDED
        assert tenant.metadata["suspension_reason"] == "Policy violation"

    def test_can_create_agent(self):
        config = TenantConfig(name="Test", tier=TenantTier.FREE)
        tenant = Tenant(config=config)

        assert tenant.can_create_agent() is True

        tenant._current_usage["agents"] = TIER_LIMITS[TenantTier.FREE].max_agents
        assert tenant.can_create_agent() is False

    def test_usage_tracking(self):
        config = TenantConfig(name="Test")
        tenant = Tenant(config=config)

        tenant.increment_usage("agents", 1)
        assert tenant._current_usage["agents"] == 1

        tenant.decrement_usage("agents", 1)
        assert tenant._current_usage["agents"] == 0

    def test_get_usage(self):
        config = TenantConfig(name="Test", tier=TenantTier.STARTER)
        tenant = Tenant(config=config)
        tenant._current_usage["agents"] = 2

        usage = tenant.get_usage()

        assert usage["agents"]["current"] == 2
        assert usage["agents"]["limit"] == TIER_LIMITS[TenantTier.STARTER].max_agents


class TestTenantLimits:
    """Tests for TenantLimits."""

    def test_tier_limits_exist(self):
        assert TenantTier.FREE in TIER_LIMITS
        assert TenantTier.STARTER in TIER_LIMITS
        assert TenantTier.PROFESSIONAL in TIER_LIMITS
        assert TenantTier.ENTERPRISE in TIER_LIMITS

    def test_tier_limits_hierarchy(self):
        free = TIER_LIMITS[TenantTier.FREE]
        starter = TIER_LIMITS[TenantTier.STARTER]
        pro = TIER_LIMITS[TenantTier.PROFESSIONAL]
        enterprise = TIER_LIMITS[TenantTier.ENTERPRISE]

        assert free.max_agents < starter.max_agents
        assert starter.max_agents < pro.max_agents
        assert pro.max_agents < enterprise.max_agents

    def test_custom_limits(self):
        custom = TenantLimits(
            max_agents=50,
            max_concurrent_executions=25,
        )
        config = TenantConfig(name="Custom", custom_limits=custom)
        tenant = Tenant(config=config)

        assert tenant.limits.max_agents == 50
        assert tenant.limits.max_concurrent_executions == 25


class TestTenantManager:
    """Tests for TenantManager."""

    def setup_method(self):
        self.manager = TenantManager()
        self.manager.reset()

    @pytest.mark.asyncio
    async def test_create_tenant(self):
        tenant = await self.manager.create_tenant(
            name="Acme Corp",
            tier=TenantTier.PROFESSIONAL,
            auto_activate=True,
        )

        assert tenant.name == "Acme Corp"
        assert tenant.tier == TenantTier.PROFESSIONAL
        assert tenant.status == TenantStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_get_tenant(self):
        tenant = await self.manager.create_tenant(
            name="Test",
            auto_activate=True,
        )

        retrieved = self.manager.get_tenant(tenant.tenant_id)
        assert retrieved is not None
        assert retrieved.tenant_id == tenant.tenant_id

    @pytest.mark.asyncio
    async def test_list_tenants(self):
        await self.manager.create_tenant(name="Tenant 1", auto_activate=True)
        await self.manager.create_tenant(name="Tenant 2", auto_activate=True)

        tenants = self.manager.list_tenants()
        assert len(tenants) == 2

    @pytest.mark.asyncio
    async def test_suspend_tenant(self):
        tenant = await self.manager.create_tenant(
            name="Test",
            auto_activate=True,
        )

        success = await self.manager.suspend_tenant(tenant.tenant_id, "Test reason")
        assert success is True

        updated = self.manager.get_tenant(tenant.tenant_id)
        assert updated.status == TenantStatus.SUSPENDED

    @pytest.mark.asyncio
    async def test_check_limit(self):
        tenant = await self.manager.create_tenant(
            name="Test",
            tier=TenantTier.FREE,
            auto_activate=True,
        )

        within_limit = self.manager.check_limit(tenant.tenant_id, "agents")
        assert within_limit is True

    @pytest.mark.asyncio
    async def test_record_usage(self):
        tenant = await self.manager.create_tenant(
            name="Test",
            auto_activate=True,
        )

        success = self.manager.record_usage(tenant.tenant_id, "agents", 1)
        assert success is True

        usage = self.manager.get_usage(tenant.tenant_id)
        assert usage["agents"]["current"] == 1

    def test_get_stats(self):
        stats = self.manager.get_stats()

        assert "total_tenants" in stats
        assert "by_status" in stats
        assert "by_tier" in stats
