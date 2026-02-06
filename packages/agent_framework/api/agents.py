"""
Agent Management API Endpoints.

Provides REST API for:
- Agent CRUD operations
- Blueprint management
- Agent execution
- State management
"""

import contextlib
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ..core.agent_executor import AgentExecutor
from ..core.agent_registry import AgentRegistry
from ..core.base_agent import AgentStatus
from ..governance.audit import AuditEventType, AuditLogger
from ..multitenancy.tenant_manager import TenantManager

router = APIRouter(prefix="/agents", tags=["Agents"])


_registry: AgentRegistry | None = None
_executor: AgentExecutor | None = None
_tenant_manager: TenantManager | None = None
_audit_logger: AuditLogger | None = None


def get_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


def get_executor() -> AgentExecutor:
    global _executor
    if _executor is None:
        _executor = AgentExecutor(get_registry())
    return _executor


def get_tenant_manager() -> TenantManager:
    global _tenant_manager
    if _tenant_manager is None:
        _tenant_manager = TenantManager()
    return _tenant_manager


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


class CreateAgentRequest(BaseModel):
    """Request to create a new agent."""

    blueprint_name: str
    tenant_id: str
    name: str
    description: str | None = None
    config_overrides: dict[str, Any] | None = None


class ExecuteAgentRequest(BaseModel):
    """Request to execute an agent."""

    input_data: dict[str, Any]
    timeout: int | None = None


class AgentResponse(BaseModel):
    """Agent response model."""

    agent_id: str
    tenant_id: str
    name: str
    blueprint: str
    status: str
    created_at: str
    config: dict[str, Any]


class ExecutionResponse(BaseModel):
    """Execution result response."""

    agent_id: str
    execution_id: str
    status: str
    output: dict[str, Any]
    steps_count: int
    duration_ms: int
    error: str | None = None


class BlueprintResponse(BaseModel):
    """Blueprint response model."""

    name: str
    description: str
    version: str
    required_tools: list[str]
    default_config: dict[str, Any]


@router.get("/blueprints", response_model=list[BlueprintResponse])
async def list_blueprints(
    registry: AgentRegistry = Depends(get_registry),
) -> list[dict[str, Any]]:
    """List all available agent blueprints."""
    return registry.list_blueprints()


@router.get("/blueprints/{blueprint_name}", response_model=BlueprintResponse)
async def get_blueprint(
    blueprint_name: str,
    registry: AgentRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get a specific blueprint by name."""
    blueprint = registry.get_blueprint(blueprint_name)
    if not blueprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Blueprint '{blueprint_name}' not found",
        )
    return blueprint.to_dict()


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: CreateAgentRequest,
    registry: AgentRegistry = Depends(get_registry),
    tenant_manager: TenantManager = Depends(get_tenant_manager),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> dict[str, Any]:
    """Create a new agent from a blueprint."""
    tenant = tenant_manager.get_tenant(request.tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{request.tenant_id}' not found",
        )

    if not tenant.is_active():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is not active",
        )

    if not tenant.can_create_agent():
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Agent limit reached for tenant",
        )

    try:
        agent = registry.create_agent(
            blueprint_name=request.blueprint_name,
            tenant_id=request.tenant_id,
            agent_name=request.name,
            config_overrides=request.config_overrides,
        )

        tenant.increment_usage("agents")

        await audit_logger.log_agent_event(
            event_type=AuditEventType.AGENT_CREATED,
            agent_id=agent.agent_id,
            tenant_id=request.tenant_id,
            details={
                "name": request.name,
                "blueprint": request.blueprint_name,
            },
        )

        return {
            "agent_id": agent.agent_id,
            "tenant_id": agent.tenant_id,
            "name": agent.config.name,
            "blueprint": agent.config.blueprint_name,
            "status": "created",
            "created_at": agent.config.created_at.isoformat(),
            "config": agent.config.model_dump(),
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    tenant_id: str | None = Query(None),
    blueprint_name: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    registry: AgentRegistry = Depends(get_registry),
) -> list[dict[str, Any]]:
    """List agents with optional filters."""
    agent_status = None
    if status_filter:
        with contextlib.suppress(ValueError):
            agent_status = AgentStatus(status_filter)

    agents = registry.list_agents(
        tenant_id=tenant_id,
        status=agent_status,
        blueprint_name=blueprint_name,
    )

    return agents[offset : offset + limit]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    registry: AgentRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get a specific agent by ID."""
    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    return {
        "agent_id": agent.agent_id,
        "tenant_id": agent.tenant_id,
        "name": agent.config.name,
        "blueprint": agent.config.blueprint_name,
        "status": agent.state.status.value if agent.state else "not_started",
        "created_at": agent.config.created_at.isoformat(),
        "config": agent.config.model_dump(),
    }


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    registry: AgentRegistry = Depends(get_registry),
    tenant_manager: TenantManager = Depends(get_tenant_manager),
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> None:
    """Delete an agent."""
    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    tenant_id = agent.tenant_id

    if not registry.remove_agent(agent_id):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete agent",
        )

    tenant = tenant_manager.get_tenant(tenant_id)
    if tenant:
        tenant.decrement_usage("agents")

    await audit_logger.log_agent_event(
        event_type=AuditEventType.AGENT_DELETED,
        agent_id=agent_id,
        tenant_id=tenant_id,
        details={},
    )


@router.post("/{agent_id}/execute", response_model=ExecutionResponse)
async def execute_agent(
    agent_id: str,
    request: ExecuteAgentRequest,
    executor: AgentExecutor = Depends(get_executor),
    tenant_manager: TenantManager = Depends(get_tenant_manager),
    registry: AgentRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Execute an agent with the given input."""
    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    tenant = tenant_manager.get_tenant(agent.tenant_id)
    if tenant:
        if not tenant.is_active():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant is not active",
            )

        if not tenant.can_execute():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Concurrent execution limit reached",
            )

        if not tenant.check_rate_limit():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )

        tenant.increment_usage("concurrent_executions")
        tenant.increment_usage("requests_this_minute")

    try:
        result = await executor.execute(
            agent=agent,
            input_data=request.input_data,
            timeout=request.timeout,
        )

        return result.to_dict()

    finally:
        if tenant:
            tenant.decrement_usage("concurrent_executions")


@router.get("/{agent_id}/state")
async def get_agent_state(
    agent_id: str,
    registry: AgentRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get the current state of an agent."""
    agent = registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' not found",
        )

    if not agent.state:
        return {"status": "not_started", "state": None}

    return {
        "status": agent.state.status.value,
        "state": agent.state.model_dump(),
    }


@router.get("/stats/overview")
async def get_agent_stats(
    tenant_id: str | None = Query(None),
    registry: AgentRegistry = Depends(get_registry),
) -> dict[str, Any]:
    """Get agent statistics."""
    stats = registry.get_stats()

    if tenant_id:
        agents = registry.list_agents(tenant_id=tenant_id)
        stats["tenant_agents"] = len(agents)

    return stats
