"""
Unit tests for agent framework core components.

Tests:
- AgentConfig and AgentState models
- AgentRegistry blueprint registration
- AgentPermissions RBAC
- AuditLogger event tracking
"""

import pytest

from packages.agent_framework.core.agent_registry import (
    AgentRegistry,
)
from packages.agent_framework.core.base_agent import (
    AgentConfig,
    AgentState,
    AgentStatus,
)
from packages.agent_framework.governance.audit import (
    AuditEvent,
    AuditEventType,
    AuditLogger,
)
from packages.agent_framework.governance.permissions import (
    AgentPermissions,
    Permission,
    PermissionLevel,
)


class TestAgentConfig:
    """Tests for AgentConfig model."""

    def test_default_config(self):
        config = AgentConfig(tenant_id="t1", blueprint_name="test", name="Test Agent")
        assert config.tenant_id == "t1"
        assert config.blueprint_name == "test"
        assert config.name == "Test Agent"
        assert config.max_iterations == 10
        assert config.timeout_seconds == 300
        assert config.confidence_threshold == 0.75

    def test_custom_config(self):
        config = AgentConfig(
            tenant_id="t1",
            blueprint_name="test",
            name="Custom Agent",
            max_iterations=5,
            require_human_approval=True,
        )
        assert config.max_iterations == 5
        assert config.require_human_approval is True


class TestAgentState:
    """Tests for AgentState model."""

    def test_initial_state(self):
        state = AgentState(agent_id="a1", tenant_id="t1")
        assert state.status == AgentStatus.IDLE
        assert state.current_step == 0
        assert state.intermediate_steps == []
        assert state.error is None

    def test_state_with_data(self):
        state = AgentState(
            agent_id="a1",
            tenant_id="t1",
            input_data={"query": "test"},
            status=AgentStatus.RUNNING,
        )
        assert state.input_data == {"query": "test"}
        assert state.status == AgentStatus.RUNNING


class TestAgentRegistry:
    """Tests for AgentRegistry."""

    def setup_method(self):
        """Reset registry before each test."""
        self.registry = AgentRegistry()
        self.registry.reset()

    def test_singleton(self):
        r1 = AgentRegistry()
        r2 = AgentRegistry()
        assert r1 is r2

    def test_list_blueprints_empty(self):
        blueprints = self.registry.list_blueprints()
        assert blueprints == []

    def test_get_stats(self):
        stats = self.registry.get_stats()
        assert "total_blueprints" in stats
        assert "total_agents" in stats
        assert "total_tenants" in stats


class TestAgentPermissions:
    """Tests for AgentPermissions RBAC."""

    def setup_method(self):
        self.permissions = AgentPermissions()

    def test_default_roles_exist(self):
        roles = self.permissions.list_roles()
        role_names = [r["name"] for r in roles]
        assert "viewer" in role_names
        assert "operator" in role_names
        assert "admin" in role_names
        assert "support_agent" in role_names

    def test_assign_role(self):
        self.permissions.assign_role("agent_1", "operator")
        roles = self.permissions.get_agent_roles("agent_1")
        assert "operator" in roles

    def test_check_permission_with_role(self):
        self.permissions.assign_role("agent_1", "operator")
        has_perm = self.permissions.check_permission(
            "agent_1", "agent:test", PermissionLevel.EXECUTE
        )
        assert has_perm is True

    def test_check_permission_denied(self):
        has_perm = self.permissions.check_permission(
            "agent_no_role", "agent:test", PermissionLevel.EXECUTE
        )
        assert has_perm is False

    def test_grant_direct_permission(self):
        permission = Permission(
            resource="tool:custom_tool",
            level=PermissionLevel.EXECUTE,
        )
        self.permissions.grant_permission("agent_2", permission)
        has_perm = self.permissions.check_permission(
            "agent_2", "tool:custom_tool", PermissionLevel.EXECUTE
        )
        assert has_perm is True


class TestAuditLogger:
    """Tests for AuditLogger."""

    def setup_method(self):
        self.logger = AuditLogger()
        self.logger.clear()

    @pytest.mark.asyncio
    async def test_log_event(self):
        event = AuditEvent(
            event_type=AuditEventType.AGENT_CREATED,
            agent_id="a1",
            tenant_id="t1",
            details={"name": "Test Agent"},
        )
        event_id = await self.logger.log(event)
        assert event_id == event.event_id

    @pytest.mark.asyncio
    async def test_query_events(self):
        event = AuditEvent(
            event_type=AuditEventType.AGENT_CREATED,
            agent_id="a1",
            tenant_id="t1",
        )
        await self.logger.log(event)

        events = self.logger.query(tenant_id="t1")
        assert len(events) == 1
        assert events[0].agent_id == "a1"

    @pytest.mark.asyncio
    async def test_query_by_event_type(self):
        await self.logger.log(
            AuditEvent(
                event_type=AuditEventType.AGENT_CREATED,
                agent_id="a1",
                tenant_id="t1",
            )
        )
        await self.logger.log(
            AuditEvent(
                event_type=AuditEventType.EXECUTION_STARTED,
                agent_id="a1",
                tenant_id="t1",
            )
        )

        events = self.logger.query(event_type=AuditEventType.AGENT_CREATED)
        assert len(events) == 1
        assert events[0].event_type == AuditEventType.AGENT_CREATED

    def test_get_stats(self):
        stats = self.logger.get_stats()
        assert "total_events" in stats
        assert "events_by_type" in stats
