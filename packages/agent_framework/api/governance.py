"""
Agent Governance Dashboard API Endpoints.

Provides REST API for:
- Real-time agent monitoring
- Permission management
- Audit trail access
- Compliance reporting
"""

import contextlib
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ..core.agent_registry import AgentRegistry
from ..governance.audit import AuditEventType, AuditLogger
from ..governance.permissions import AgentPermissions, Permission, PermissionLevel, Role
from ..multitenancy.tenant_manager import TenantManager

router = APIRouter(prefix="/governance", tags=["Governance"])


_permissions: AgentPermissions | None = None
_audit_logger: AuditLogger | None = None
_registry: AgentRegistry | None = None
_tenant_manager: TenantManager | None = None


def get_permissions() -> AgentPermissions:
    global _permissions
    if _permissions is None:
        _permissions = AgentPermissions()
    return _permissions


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def get_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def get_tenant_manager() -> TenantManager:
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantManager()
    return _tenant_manager


class AssignRoleRequest(BaseModel):
    """Request to assign a role to an agent."""

    agent_id: str
    role_name: str


class GrantPermissionRequest(BaseModel):
    """Request to grant a permission."""

    agent_id: str
    resource: str
    level: str
    tenant_id: str | None = None
    conditions: dict[str, Any] | None = None
    expires_in_hours: int | None = None


class CreateRoleRequest(BaseModel):
    """Request to create a custom role."""

    name: str
    description: str
    permissions: list[dict[str, Any]]
    inherits_from: list[str] | None = None


class AuditQueryParams(BaseModel):
    """Parameters for audit log queries."""

    tenant_id: str | None = None
    agent_id: str | None = None
    event_type: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    user_id: str | None = None
    limit: int = 100
    offset: int = 0


@router.get("/dashboard")
async def get_governance_dashboard(
    tenant_id: str | None = Query(None),
    registry: AgentRegistry = Depends(get_registry),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    tenant_manager: TenantManager = Depends(get_tenant_manager),
) -> dict[str, Any]:
    """
    Get comprehensive governance dashboard data.

    Returns real-time view of all agents, permissions, and recent activity.
    """
    agents = registry.list_agents(tenant_id=tenant_id)

    active_agents = [a for a in agents if a.get("status") == "running"]
    idle_agents = [a for a in agents if a.get("status") in ["idle", "not_started"]]
    awaiting_human = [a for a in agents if a.get("status") == "awaiting_human"]
    failed_agents = [a for a in agents if a.get("status") == "failed"]

    recent_events = audit_logger.query(
        tenant_id=tenant_id,
        limit=20,
    )

    audit_stats = audit_logger.get_stats(tenant_id=tenant_id)

    tenant_stats = None
    if tenant_id:
        tenant = tenant_manager.get_tenant(tenant_id)
        if tenant:
            tenant_stats = tenant.get_usage()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "agents": {
            "total": len(agents),
            "active": len(active_agents),
            "idle": len(idle_agents),
            "awaiting_human": len(awaiting_human),
            "failed": len(failed_agents),
            "by_blueprint": _count_by_field(agents, "blueprint"),
        },
        "recent_activity": [
            {
                "event_id": e.event_id,
                "event_type": e.event_type.value,
                "agent_id": e.agent_id,
                "timestamp": e.timestamp.isoformat(),
                "details": e.details,
            }
            for e in recent_events[:10]
        ],
        "audit_summary": audit_stats,
        "tenant_usage": tenant_stats,
    }


def _count_by_field(items: list[dict], field: str) -> dict[str, int]:
    """Count items by a field value."""
    counts: dict[str, int] = {}
    for item in items:
        value = item.get(field, "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts


@router.get("/agents/active")
async def get_active_agents(
    tenant_id: str | None = Query(None),
    registry: AgentRegistry = Depends(get_registry),
) -> list[dict[str, Any]]:
    """Get all currently active agents with their states."""
    agents = registry.list_agents(tenant_id=tenant_id)

    active = []
    for agent_summary in agents:
        if agent_summary.get("status") in ["running", "awaiting_human"]:
            agent = registry.get_agent(agent_summary["agent_id"])
            if agent and agent.state:
                active.append({
                    "agent_id": agent.agent_id,
                    "name": agent.config.name,
                    "tenant_id": agent.tenant_id,
                    "blueprint": agent.config.blueprint_name,
                    "status": agent.state.status.value,
                    "current_step": agent.state.current_step,
                    "started_at": (
                        agent.state.started_at.isoformat() if agent.state.started_at else None
                    ),
                    "execution_id": agent.state.execution_id,
                    "has_human_request": agent.state.human_feedback_request is not None,
                })

    return active


@router.get("/roles")
async def list_roles(
    permissions: AgentPermissions = Depends(get_permissions),
) -> list[dict[str, Any]]:
    """List all available roles."""
    return permissions.list_roles()


@router.post("/roles", status_code=status.HTTP_201_CREATED)
async def create_role(
    request: CreateRoleRequest,
    permissions_mgr: AgentPermissions = Depends(get_permissions),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> dict[str, Any]:
    """Create a custom role."""
    role_permissions = []
    for p in request.permissions:
        role_permissions.append(
            Permission(
                resource=p["resource"],
                level=PermissionLevel(p["level"]),
                conditions=p.get("conditions", {}),
            )
        )

    role = Role(
        name=request.name,
        description=request.description,
        permissions=role_permissions,
        inherits_from=request.inherits_from or [],
    )

    try:
        permissions_mgr.create_role(role)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    await audit_logger.log(
        audit_logger.query.__self__.__class__(
            event_type=AuditEventType.PERMISSION_GRANTED,
            resource=f"role:{request.name}",
            action="create_role",
            outcome="created",
            details={"role_name": request.name},
        )
    )

    return {
        "name": role.name,
        "description": role.description,
        "permissions_count": len(role.permissions),
        "inherits_from": role.inherits_from,
    }


@router.post("/roles/assign")
async def assign_role(
    request: AssignRoleRequest,
    permissions_mgr: AgentPermissions = Depends(get_permissions),
    registry: AgentRegistry = Depends(get_registry),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> dict[str, Any]:
    """Assign a role to an agent."""
    agent = registry.get_agent(request.agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{request.agent_id}' not found",
        )

    try:
        permissions_mgr.assign_role(request.agent_id, request.role_name)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    await audit_logger.log_agent_event(
        event_type=AuditEventType.ROLE_ASSIGNED,
        agent_id=request.agent_id,
        tenant_id=agent.tenant_id,
        details={"role": request.role_name},
    )

    return {
        "agent_id": request.agent_id,
        "role": request.role_name,
        "assigned": True,
    }


@router.delete("/roles/{agent_id}/{role_name}")
async def revoke_role(
    agent_id: str,
    role_name: str,
    permissions_mgr: AgentPermissions = Depends(get_permissions),
    registry: AgentRegistry = Depends(get_registry),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> dict[str, Any]:
    """Revoke a role from an agent."""
    agent = registry.get_agent(agent_id)

    success = permissions_mgr.revoke_role(agent_id, role_name)

    if agent:
        await audit_logger.log_agent_event(
            event_type=AuditEventType.ROLE_REVOKED,
            agent_id=agent_id,
            tenant_id=agent.tenant_id,
            details={"role": role_name},
        )

    return {"agent_id": agent_id, "role": role_name, "revoked": success}


@router.get("/permissions/{agent_id}")
async def get_agent_permissions(
    agent_id: str,
    tenant_id: str | None = Query(None),
    permissions_mgr: AgentPermissions = Depends(get_permissions),
) -> dict[str, Any]:
    """Get all permissions for an agent."""
    perms = permissions_mgr.get_agent_permissions(agent_id, tenant_id)
    roles = permissions_mgr.get_agent_roles(agent_id)

    return {
        "agent_id": agent_id,
        "roles": roles,
        "permissions": [
            {
                "resource": p.resource,
                "level": p.level.value,
                "conditions": p.conditions,
                "expires_at": p.expires_at.isoformat() if p.expires_at else None,
            }
            for p in perms
        ],
    }


@router.post("/permissions/grant")
async def grant_permission(
    request: GrantPermissionRequest,
    permissions_mgr: AgentPermissions = Depends(get_permissions),
    registry: AgentRegistry = Depends(get_registry),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> dict[str, Any]:
    """Grant a permission to an agent."""
    try:
        level = PermissionLevel(request.level)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permission level: {request.level}",
        ) from e

    expires_at = None
    if request.expires_in_hours:
        expires_at = datetime.utcnow() + timedelta(hours=request.expires_in_hours)

    permission = Permission(
        resource=request.resource,
        level=level,
        conditions=request.conditions or {},
        expires_at=expires_at,
    )

    permissions_mgr.grant_permission(
        request.agent_id,
        permission,
        request.tenant_id,
    )

    agent = registry.get_agent(request.agent_id)
    if agent:
        await audit_logger.log_agent_event(
            event_type=AuditEventType.PERMISSION_GRANTED,
            agent_id=request.agent_id,
            tenant_id=agent.tenant_id,
            details={
                "resource": request.resource,
                "level": request.level,
            },
        )

    return {
        "agent_id": request.agent_id,
        "resource": request.resource,
        "level": request.level,
        "granted": True,
    }


@router.delete("/permissions/{agent_id}/{resource}")
async def revoke_permission(
    agent_id: str,
    resource: str,
    tenant_id: str | None = Query(None),
    permissions_mgr: AgentPermissions = Depends(get_permissions),
    registry: AgentRegistry = Depends(get_registry),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> dict[str, Any]:
    """Revoke a permission from an agent."""
    success = permissions_mgr.revoke_permission(agent_id, resource, tenant_id)

    agent = registry.get_agent(agent_id)
    if agent:
        await audit_logger.log_agent_event(
            event_type=AuditEventType.PERMISSION_REVOKED,
            agent_id=agent_id,
            tenant_id=agent.tenant_id,
            details={"resource": resource},
        )

    return {"agent_id": agent_id, "resource": resource, "revoked": success}


@router.get("/permissions/check")
async def check_permission(
    agent_id: str,
    resource: str,
    level: str,
    tenant_id: str | None = Query(None),
    permissions_mgr: AgentPermissions = Depends(get_permissions),
) -> dict[str, Any]:
    """Check if an agent has a specific permission."""
    try:
        perm_level = PermissionLevel(level)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid permission level: {level}",
        ) from e

    has_permission = permissions_mgr.check_permission(
        agent_id=agent_id,
        resource=resource,
        required_level=perm_level,
        tenant_id=tenant_id,
    )

    return {
        "agent_id": agent_id,
        "resource": resource,
        "level": level,
        "has_permission": has_permission,
    }


@router.get("/audit")
async def query_audit_logs(
    tenant_id: str | None = Query(None),
    agent_id: str | None = Query(None),
    event_type: str | None = Query(None),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    user_id: str | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> dict[str, Any]:
    """Query audit logs with filters."""
    audit_event_type = None
    if event_type:
        with contextlib.suppress(ValueError):
            audit_event_type = AuditEventType(event_type)

    events = audit_logger.query(
        tenant_id=tenant_id,
        agent_id=agent_id,
        event_type=audit_event_type,
        start_time=start_time,
        end_time=end_time,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )

    return {
        "total": len(events),
        "offset": offset,
        "limit": limit,
        "events": [e.to_dict() for e in events],
    }


@router.get("/audit/agent/{agent_id}")
async def get_agent_audit_history(
    agent_id: str,
    limit: int = Query(50, le=200),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> dict[str, Any]:
    """Get complete audit history for an agent."""
    history = audit_logger.get_agent_history(agent_id, limit)

    return {
        "agent_id": agent_id,
        "total_events": len(history),
        "events": history,
    }


@router.get("/audit/execution/{execution_id}")
async def get_execution_audit_trail(
    execution_id: str,
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> dict[str, Any]:
    """Get complete audit trail for an execution."""
    trail = audit_logger.get_execution_trail(execution_id)

    return {
        "execution_id": execution_id,
        "total_events": len(trail),
        "events": trail,
    }


@router.get("/audit/human-interactions")
async def get_human_interactions(
    tenant_id: str | None = Query(None),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> dict[str, Any]:
    """Get all human-in-the-loop interactions."""
    interactions = audit_logger.get_human_interactions(
        tenant_id=tenant_id,
        start_time=start_time,
        end_time=end_time,
    )

    return {
        "total": len(interactions),
        "interactions": interactions,
    }


@router.get("/audit/security")
async def get_security_events(
    tenant_id: str | None = Query(None),
    limit: int = Query(100, le=500),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> dict[str, Any]:
    """Get security-related audit events."""
    events = audit_logger.get_security_events(tenant_id, limit)

    return {
        "total": len(events),
        "events": events,
    }


@router.get("/audit/export")
async def export_audit_logs(
    tenant_id: str | None = Query(None),
    format: str = Query("json", pattern="^(json|csv)$"),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> Any:
    """Export audit logs in JSON or CSV format."""
    return audit_logger.export(format=format, tenant_id=tenant_id)


@router.get("/stats")
async def get_governance_stats(
    tenant_id: str | None = Query(None),
    audit_logger: AuditLogger = Depends(get_audit_logger),
    registry: AgentRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get comprehensive governance statistics."""
    audit_stats = audit_logger.get_stats(tenant_id)
    registry_stats = registry.get_stats()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "audit": audit_stats,
        "agents": registry_stats,
    }
