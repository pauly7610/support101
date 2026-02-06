"""
Agent Permissions System.

Provides fine-grained access control for agents:
- Tool-level permissions
- Tenant-based isolation
- Role-based access control
- Permission inheritance
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class PermissionLevel(StrEnum):
    """Permission access levels."""

    NONE = "none"
    READ = "read"
    EXECUTE = "execute"
    ADMIN = "admin"


@dataclass
class Permission:
    """A single permission grant."""

    resource: str
    level: PermissionLevel
    conditions: dict[str, Any] = field(default_factory=dict)
    granted_at: datetime = field(default_factory=datetime.utcnow)
    granted_by: str | None = None
    expires_at: datetime | None = None

    def is_expired(self) -> bool:
        """Check if permission has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def matches_conditions(self, context: dict[str, Any]) -> bool:
        """Check if context matches permission conditions."""
        for key, value in self.conditions.items():
            if key not in context:
                return False
            if isinstance(value, list):
                if context[key] not in value:
                    return False
            elif context[key] != value:
                return False
        return True


@dataclass
class Role:
    """A role with a set of permissions."""

    name: str
    description: str
    permissions: list[Permission] = field(default_factory=list)
    inherits_from: list[str] = field(default_factory=list)


class AgentPermissions:
    """
    Permission manager for agents.

    Supports:
    - Direct permission grants
    - Role-based permissions
    - Tenant isolation
    - Conditional permissions
    """

    def __init__(self) -> None:
        self._agent_permissions: dict[str, list[Permission]] = {}
        self._agent_roles: dict[str, set[str]] = {}
        self._roles: dict[str, Role] = {}
        self._tenant_permissions: dict[str, dict[str, list[Permission]]] = {}
        self._initialize_default_roles()

    def _initialize_default_roles(self) -> None:
        """Set up default roles."""
        self._roles["viewer"] = Role(
            name="viewer",
            description="Read-only access to agent data",
            permissions=[
                Permission(resource="agent:*", level=PermissionLevel.READ),
                Permission(resource="execution:*", level=PermissionLevel.READ),
            ],
        )

        self._roles["operator"] = Role(
            name="operator",
            description="Can execute agents and view results",
            permissions=[
                Permission(resource="agent:*", level=PermissionLevel.EXECUTE),
                Permission(resource="execution:*", level=PermissionLevel.EXECUTE),
                Permission(resource="tool:*", level=PermissionLevel.EXECUTE),
            ],
            inherits_from=["viewer"],
        )

        self._roles["admin"] = Role(
            name="admin",
            description="Full administrative access",
            permissions=[
                Permission(resource="*", level=PermissionLevel.ADMIN),
            ],
            inherits_from=["operator"],
        )

        self._roles["support_agent"] = Role(
            name="support_agent",
            description="Support agent with limited tool access",
            permissions=[
                Permission(resource="tool:search_knowledge_base", level=PermissionLevel.EXECUTE),
                Permission(resource="tool:create_ticket", level=PermissionLevel.EXECUTE),
                Permission(
                    resource="tool:escalate_to_human",
                    level=PermissionLevel.EXECUTE,
                    conditions={"requires_approval": True},
                ),
            ],
            inherits_from=["viewer"],
        )

    def create_role(self, role: Role) -> None:
        """Create a new role."""
        if role.name in self._roles:
            raise ValueError(f"Role '{role.name}' already exists")
        self._roles[role.name] = role

    def get_role(self, role_name: str) -> Role | None:
        """Get a role by name."""
        return self._roles.get(role_name)

    def assign_role(self, agent_id: str, role_name: str) -> None:
        """Assign a role to an agent."""
        if role_name not in self._roles:
            raise ValueError(f"Role '{role_name}' not found")

        if agent_id not in self._agent_roles:
            self._agent_roles[agent_id] = set()
        self._agent_roles[agent_id].add(role_name)

    def revoke_role(self, agent_id: str, role_name: str) -> bool:
        """Revoke a role from an agent."""
        if agent_id in self._agent_roles:
            self._agent_roles[agent_id].discard(role_name)
            return True
        return False

    def grant_permission(
        self,
        agent_id: str,
        permission: Permission,
        tenant_id: str | None = None,
    ) -> None:
        """Grant a permission to an agent."""
        if tenant_id:
            if tenant_id not in self._tenant_permissions:
                self._tenant_permissions[tenant_id] = {}
            if agent_id not in self._tenant_permissions[tenant_id]:
                self._tenant_permissions[tenant_id][agent_id] = []
            self._tenant_permissions[tenant_id][agent_id].append(permission)
        else:
            if agent_id not in self._agent_permissions:
                self._agent_permissions[agent_id] = []
            self._agent_permissions[agent_id].append(permission)

    def revoke_permission(
        self,
        agent_id: str,
        resource: str,
        tenant_id: str | None = None,
    ) -> bool:
        """Revoke a permission from an agent."""
        permissions_list = None

        if tenant_id and tenant_id in self._tenant_permissions:
            permissions_list = self._tenant_permissions[tenant_id].get(agent_id)
        elif agent_id in self._agent_permissions:
            permissions_list = self._agent_permissions[agent_id]

        if permissions_list:
            original_len = len(permissions_list)
            permissions_list[:] = [p for p in permissions_list if p.resource != resource]
            return len(permissions_list) < original_len

        return False

    def _get_role_permissions(
        self, role_name: str, visited: set[str] | None = None
    ) -> list[Permission]:
        """Get all permissions for a role, including inherited ones."""
        if visited is None:
            visited = set()

        if role_name in visited:
            return []
        visited.add(role_name)

        role = self._roles.get(role_name)
        if not role:
            return []

        permissions = list(role.permissions)

        for parent_role in role.inherits_from:
            permissions.extend(self._get_role_permissions(parent_role, visited))

        return permissions

    def get_agent_permissions(
        self,
        agent_id: str,
        tenant_id: str | None = None,
    ) -> list[Permission]:
        """Get all permissions for an agent."""
        permissions: list[Permission] = []

        permissions.extend(self._agent_permissions.get(agent_id, []))

        for role_name in self._agent_roles.get(agent_id, set()):
            permissions.extend(self._get_role_permissions(role_name))

        if tenant_id and tenant_id in self._tenant_permissions:
            permissions.extend(self._tenant_permissions[tenant_id].get(agent_id, []))

        return [p for p in permissions if not p.is_expired()]

    def check_permission(
        self,
        agent_id: str,
        resource: str,
        required_level: PermissionLevel,
        tenant_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """
        Check if an agent has a specific permission.

        Args:
            agent_id: Agent to check
            resource: Resource identifier (e.g., "tool:search_knowledge_base")
            required_level: Minimum required permission level
            tenant_id: Optional tenant context
            context: Optional additional context for conditional permissions

        Returns:
            True if permission is granted
        """
        context = context or {}
        permissions = self.get_agent_permissions(agent_id, tenant_id)

        level_hierarchy = {
            PermissionLevel.NONE: 0,
            PermissionLevel.READ: 1,
            PermissionLevel.EXECUTE: 2,
            PermissionLevel.ADMIN: 3,
        }

        required_level_value = level_hierarchy[required_level]

        for permission in permissions:
            if (
                (
                    permission.resource == "*"
                    or self._resource_matches(permission.resource, resource)
                )
                and level_hierarchy[permission.level] >= required_level_value
                and permission.matches_conditions(context)
            ):
                return True

        return False

    def _resource_matches(self, pattern: str, resource: str) -> bool:
        """Check if a resource matches a pattern (supports wildcards)."""
        if pattern == resource:
            return True

        if pattern.endswith(":*"):
            prefix = pattern[:-1]
            return resource.startswith(prefix)

        return False

    def list_roles(self) -> list[dict[str, Any]]:
        """List all available roles."""
        return [
            {
                "name": role.name,
                "description": role.description,
                "permissions_count": len(role.permissions),
                "inherits_from": role.inherits_from,
            }
            for role in self._roles.values()
        ]

    def get_agent_roles(self, agent_id: str) -> list[str]:
        """Get all roles assigned to an agent."""
        return list(self._agent_roles.get(agent_id, set()))
