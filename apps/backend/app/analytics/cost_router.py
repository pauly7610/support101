"""
FastAPI router for LLM cost tracking dashboard.

Endpoints:
- GET  /v1/analytics/costs          — Cost dashboard summary
- GET  /v1/analytics/costs/tenant   — Per-tenant usage
- POST /v1/analytics/costs/record   — Record a usage event (internal)
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi_limiter.depends import RateLimiter

from apps.backend.app.auth.jwt import get_current_user
from packages.llm_engine.cost_tracker import get_cost_tracker

router = APIRouter(prefix="/costs", tags=["Cost Tracking"])


@router.get("")
async def get_cost_dashboard(
    _user=Depends(get_current_user),
    _limiter: None = Depends(RateLimiter(times=30, seconds=60)),
) -> dict[str, Any]:
    """Get the LLM cost dashboard with spend, budget, and breakdowns."""
    tracker = get_cost_tracker()
    return tracker.get_dashboard()


@router.get("/tenant")
async def get_tenant_costs(
    tenant_id: str = Query(..., description="Tenant ID to get costs for"),
    _user=Depends(get_current_user),
    _limiter: None = Depends(RateLimiter(times=30, seconds=60)),
) -> dict[str, Any]:
    """Get cost breakdown for a specific tenant."""
    tracker = get_cost_tracker()
    return tracker.get_tenant_usage(tenant_id)


@router.post("/record")
async def record_usage(
    model: str = Query(..., description="Model name"),
    prompt_tokens: int = Query(..., ge=0, description="Number of prompt tokens"),
    completion_tokens: int = Query(..., ge=0, description="Number of completion tokens"),
    provider: str = Query("openai", description="LLM provider"),
    request_type: str = Query("chat", description="Request type"),
    tenant_id: str = Query("", description="Tenant ID"),
    agent_id: str = Query("", description="Agent ID"),
    _user=Depends(get_current_user),
    _limiter: None = Depends(RateLimiter(times=60, seconds=60)),
) -> dict[str, Any]:
    """Record an LLM usage event. Typically called internally by the RAG chain."""
    tracker = get_cost_tracker()
    record = tracker.record_usage(
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        provider=provider,
        request_type=request_type,
        tenant_id=tenant_id,
        agent_id=agent_id,
    )
    return {
        "recorded": True,
        "estimated_cost_usd": record.estimated_cost_usd,
        "total_tokens": record.total_tokens,
    }
