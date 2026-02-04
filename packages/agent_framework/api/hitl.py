"""
Human-in-the-Loop API Endpoints.

Provides REST API for:
- HITL queue management
- Request assignment and response
- Escalation management
- Reviewer dashboard
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ..core.agent_registry import AgentRegistry
from ..hitl.escalation import EscalationLevel
from ..hitl.manager import HITLManager
from ..hitl.queue import HITLPriority, HITLRequestType

router = APIRouter(prefix="/hitl", tags=["Human-in-the-Loop"])


_hitl_manager: Optional[HITLManager] = None
_registry: Optional[AgentRegistry] = None


def get_hitl_manager() -> HITLManager:
    global _hitl_manager, _registry
    if _hitl_manager is None:
        if _registry is None:
            _registry = AgentRegistry()
        _hitl_manager = HITLManager(registry=_registry)
    return _hitl_manager


def get_registry() -> AgentRegistry:
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry


class RegisterReviewerRequest(BaseModel):
    """Request to register a reviewer."""

    reviewer_id: str
    tenant_id: str
    name: str
    skills: Optional[List[str]] = None


class RespondToRequestRequest(BaseModel):
    """Request to respond to a HITL request."""

    response: Dict[str, Any]
    reviewer_id: str


class ManualEscalationRequest(BaseModel):
    """Request to manually escalate."""

    agent_id: str
    reason: str
    level: Optional[str] = "l2"
    context: Optional[Dict[str, Any]] = None


class CreateEscalationPolicyRequest(BaseModel):
    """Request to create an escalation policy."""

    tenant_id: str
    name: str
    description: Optional[str] = ""
    include_default_rules: bool = True


@router.get("/queue")
async def get_queue(
    tenant_id: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    request_type: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    hitl_manager: HITLManager = Depends(get_hitl_manager),
) -> Dict[str, Any]:
    """Get pending HITL requests."""
    hitl_priority = None
    if priority:
        try:
            hitl_priority = HITLPriority(priority)
        except ValueError:
            pass

    hitl_type = None
    if request_type:
        try:
            hitl_type = HITLRequestType(request_type)
        except ValueError:
            pass

    requests = hitl_manager.queue.get_pending(
        tenant_id=tenant_id,
        priority=hitl_priority,
        request_type=hitl_type,
        limit=limit,
    )

    return {
        "total": len(requests),
        "requests": [r.to_dict() for r in requests],
    }


@router.get("/queue/{request_id}")
async def get_request(
    request_id: str,
    hitl_manager: HITLManager = Depends(get_hitl_manager),
) -> Dict[str, Any]:
    """Get a specific HITL request."""
    request = hitl_manager.queue.get_request(request_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request '{request_id}' not found",
        )

    return request.to_dict()


@router.post("/queue/{request_id}/assign")
async def assign_request(
    request_id: str,
    reviewer_id: str = Query(...),
    hitl_manager: HITLManager = Depends(get_hitl_manager),
) -> Dict[str, Any]:
    """Assign a request to a reviewer."""
    success = hitl_manager.queue.assign(request_id, reviewer_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to assign request (may already be assigned or completed)",
        )

    return {"request_id": request_id, "assigned_to": reviewer_id, "success": True}


@router.post("/queue/{request_id}/unassign")
async def unassign_request(
    request_id: str,
    hitl_manager: HITLManager = Depends(get_hitl_manager),
) -> Dict[str, Any]:
    """Unassign a request."""
    success = hitl_manager.queue.unassign(request_id)

    return {"request_id": request_id, "unassigned": success}


@router.post("/queue/{request_id}/respond")
async def respond_to_request(
    request_id: str,
    request: RespondToRequestRequest,
    hitl_manager: HITLManager = Depends(get_hitl_manager),
) -> Dict[str, Any]:
    """Provide a response to a HITL request."""
    success = await hitl_manager.provide_response(
        request_id=request_id,
        response=request.response,
        reviewer_id=request.reviewer_id,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to respond to request",
        )

    return {
        "request_id": request_id,
        "responded": True,
        "reviewer_id": request.reviewer_id,
    }


@router.post("/queue/{request_id}/cancel")
async def cancel_request(
    request_id: str,
    reason: str = Query(""),
    hitl_manager: HITLManager = Depends(get_hitl_manager),
) -> Dict[str, Any]:
    """Cancel a HITL request."""
    success = hitl_manager.queue.cancel(request_id, reason)

    return {"request_id": request_id, "cancelled": success}


@router.post("/reviewers")
async def register_reviewer(
    request: RegisterReviewerRequest,
    hitl_manager: HITLManager = Depends(get_hitl_manager),
) -> Dict[str, Any]:
    """Register a new reviewer."""
    hitl_manager.register_reviewer(
        reviewer_id=request.reviewer_id,
        tenant_id=request.tenant_id,
        name=request.name,
        skills=request.skills,
    )

    return {
        "reviewer_id": request.reviewer_id,
        "registered": True,
    }


@router.put("/reviewers/{reviewer_id}/availability")
async def set_reviewer_availability(
    reviewer_id: str,
    available: bool = Query(...),
    hitl_manager: HITLManager = Depends(get_hitl_manager),
) -> Dict[str, Any]:
    """Set reviewer availability."""
    success = hitl_manager.set_reviewer_availability(reviewer_id, available)

    return {
        "reviewer_id": reviewer_id,
        "available": available,
        "updated": success,
    }


@router.get("/reviewers/{reviewer_id}/dashboard")
async def get_reviewer_dashboard(
    reviewer_id: str,
    hitl_manager: HITLManager = Depends(get_hitl_manager),
) -> Dict[str, Any]:
    """Get dashboard data for a reviewer."""
    dashboard = hitl_manager.get_reviewer_dashboard(reviewer_id)

    if "error" in dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=dashboard["error"],
        )

    return dashboard


@router.get("/reviewers/{reviewer_id}/assignments")
async def get_reviewer_assignments(
    reviewer_id: str,
    hitl_manager: HITLManager = Depends(get_hitl_manager),
) -> Dict[str, Any]:
    """Get all assignments for a reviewer."""
    assignments = hitl_manager.queue.get_user_assignments(reviewer_id)

    return {
        "reviewer_id": reviewer_id,
        "total": len(assignments),
        "assignments": [a.to_dict() for a in assignments],
    }


@router.post("/escalate")
async def manual_escalate(
    request: ManualEscalationRequest,
    hitl_manager: HITLManager = Depends(get_hitl_manager),
    registry: AgentRegistry = Depends(get_registry),
) -> Dict[str, Any]:
    """Manually escalate an agent's task."""
    agent = registry.get_agent(request.agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{request.agent_id}' not found",
        )

    try:
        level = EscalationLevel(request.level) if request.level else EscalationLevel.L2
    except ValueError:
        level = EscalationLevel.L2

    escalation = await hitl_manager.escalate(
        agent=agent,
        reason=request.reason,
        level=level,
        context=request.context,
    )

    return escalation


@router.post("/escalation-policies")
async def create_escalation_policy(
    request: CreateEscalationPolicyRequest,
    hitl_manager: HITLManager = Depends(get_hitl_manager),
) -> Dict[str, Any]:
    """Create an escalation policy for a tenant."""
    policy = hitl_manager.escalation_manager.create_policy(
        tenant_id=request.tenant_id,
        name=request.name,
        description=request.description or "",
        include_default_rules=request.include_default_rules,
    )

    return policy.to_dict()


@router.get("/escalation-policies/{tenant_id}")
async def get_escalation_policy(
    tenant_id: str,
    hitl_manager: HITLManager = Depends(get_hitl_manager),
) -> Dict[str, Any]:
    """Get escalation policy for a tenant."""
    policy = hitl_manager.escalation_manager.get_tenant_policy(tenant_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No escalation policy found for tenant '{tenant_id}'",
        )

    return policy.to_dict()


@router.get("/stats")
async def get_hitl_stats(
    tenant_id: Optional[str] = Query(None),
    hitl_manager: HITLManager = Depends(get_hitl_manager),
) -> Dict[str, Any]:
    """Get HITL statistics."""
    return hitl_manager.get_stats(tenant_id)


@router.get("/queue/stats")
async def get_queue_stats(
    tenant_id: Optional[str] = Query(None),
    hitl_manager: HITLManager = Depends(get_hitl_manager),
) -> Dict[str, Any]:
    """Get queue statistics."""
    return hitl_manager.queue.get_queue_stats(tenant_id)
