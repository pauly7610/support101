"""
Tenant Management API Endpoints.

Provides REST API for:
- Tenant CRUD operations
- Usage tracking
- Tenant configuration
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from ..multitenancy.tenant import Tenant, TenantConfig, TenantLimits, TenantStatus, TenantTier
from ..multitenancy.tenant_manager import TenantManager
from ..governance.audit import AuditLogger


router = APIRouter(prefix="/tenants", tags=["Tenants"])


_tenant_manager: Optional[TenantManager] = None
_audit_logger: Optional[AuditLogger] = None


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


class CreateTenantRequest(BaseModel):
    """Request to create a tenant."""
    name: str
    tier: str = "starter"
    owner_id: Optional[str] = None
    allowed_blueprints: Optional[List[str]] = None
    settings: Optional[Dict[str, Any]] = None
    auto_activate: bool = False


class UpdateTenantRequest(BaseModel):
    """Request to update a tenant."""
    name: Optional[str] = None
    tier: Optional[str] = None
    allowed_blueprints: Optional[List[str]] = None
    settings: Optional[Dict[str, Any]] = None


class CustomLimitsRequest(BaseModel):
    """Request to set custom limits."""
    max_agents: Optional[int] = None
    max_concurrent_executions: Optional[int] = None
    max_requests_per_minute: Optional[int] = None
    max_storage_mb: Optional[int] = None
    max_vector_documents: Optional[int] = None
    max_hitl_queue_size: Optional[int] = None


class TenantResponse(BaseModel):
    """Tenant response model."""
    tenant_id: str
    name: str
    tier: str
    status: str
    owner_id: Optional[str]
    created_at: str
    limits: Dict[str, int]
    usage: Dict[str, Any]


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    request: CreateTenantRequest,
    tenant_manager: TenantManager = Depends(get_tenant_manager),
) -> Dict[str, Any]:
    """Create a new tenant."""
    try:
        tier = TenantTier(request.tier)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier: {request.tier}. Valid options: {[t.value for t in TenantTier]}",
        )
    
    tenant = await tenant_manager.create_tenant(
        name=request.name,
        tier=tier,
        owner_id=request.owner_id,
        allowed_blueprints=request.allowed_blueprints,
        settings=request.settings,
        auto_activate=request.auto_activate,
    )
    
    return tenant.to_dict()


@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    status_filter: Optional[str] = Query(None, alias="status"),
    tier: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    tenant_manager: TenantManager = Depends(get_tenant_manager),
) -> List[Dict[str, Any]]:
    """List tenants with optional filters."""
    tenant_status = None
    if status_filter:
        try:
            tenant_status = TenantStatus(status_filter)
        except ValueError:
            pass
    
    tenant_tier = None
    if tier:
        try:
            tenant_tier = TenantTier(tier)
        except ValueError:
            pass
    
    tenants = tenant_manager.list_tenants(
        status=tenant_status,
        tier=tenant_tier,
        limit=limit,
        offset=offset,
    )
    
    return [t.to_dict() for t in tenants]


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    tenant_manager: TenantManager = Depends(get_tenant_manager),
) -> Dict[str, Any]:
    """Get a specific tenant."""
    tenant = tenant_manager.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )
    
    return tenant.to_dict()


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    request: UpdateTenantRequest,
    tenant_manager: TenantManager = Depends(get_tenant_manager),
) -> Dict[str, Any]:
    """Update a tenant."""
    tier = None
    if request.tier:
        try:
            tier = TenantTier(request.tier)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tier: {request.tier}",
            )
    
    tenant = await tenant_manager.update_tenant(
        tenant_id=tenant_id,
        name=request.name,
        tier=tier,
        allowed_blueprints=request.allowed_blueprints,
        settings=request.settings,
    )
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )
    
    return tenant.to_dict()


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    force: bool = Query(False),
    tenant_manager: TenantManager = Depends(get_tenant_manager),
) -> None:
    """Delete a tenant."""
    try:
        success = await tenant_manager.delete_tenant(tenant_id, force=force)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant '{tenant_id}' not found",
            )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{tenant_id}/activate")
async def activate_tenant(
    tenant_id: str,
    tenant_manager: TenantManager = Depends(get_tenant_manager),
) -> Dict[str, Any]:
    """Activate a tenant."""
    success = await tenant_manager.activate_tenant(tenant_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )
    
    return {"tenant_id": tenant_id, "status": "active", "activated": True}


@router.post("/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: str,
    reason: str = Query(""),
    tenant_manager: TenantManager = Depends(get_tenant_manager),
) -> Dict[str, Any]:
    """Suspend a tenant."""
    success = await tenant_manager.suspend_tenant(tenant_id, reason)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )
    
    return {"tenant_id": tenant_id, "status": "suspended", "reason": reason}


@router.get("/{tenant_id}/usage")
async def get_tenant_usage(
    tenant_id: str,
    tenant_manager: TenantManager = Depends(get_tenant_manager),
) -> Dict[str, Any]:
    """Get usage statistics for a tenant."""
    usage = tenant_manager.get_usage(tenant_id)
    if usage is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )
    
    return {
        "tenant_id": tenant_id,
        "usage": usage,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.put("/{tenant_id}/limits")
async def set_custom_limits(
    tenant_id: str,
    request: CustomLimitsRequest,
    tenant_manager: TenantManager = Depends(get_tenant_manager),
) -> Dict[str, Any]:
    """Set custom resource limits for a tenant."""
    tenant = tenant_manager.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )
    
    current_limits = tenant.limits
    
    custom_limits = TenantLimits(
        max_agents=request.max_agents or current_limits.max_agents,
        max_concurrent_executions=request.max_concurrent_executions or current_limits.max_concurrent_executions,
        max_requests_per_minute=request.max_requests_per_minute or current_limits.max_requests_per_minute,
        max_storage_mb=request.max_storage_mb or current_limits.max_storage_mb,
        max_vector_documents=request.max_vector_documents or current_limits.max_vector_documents,
        max_hitl_queue_size=request.max_hitl_queue_size or current_limits.max_hitl_queue_size,
    )
    
    await tenant_manager.update_tenant(
        tenant_id=tenant_id,
        custom_limits=custom_limits,
    )
    
    return {
        "tenant_id": tenant_id,
        "limits": custom_limits.to_dict(),
    }


@router.post("/{tenant_id}/api-key")
async def set_api_key(
    tenant_id: str,
    api_key_hash: str = Query(...),
    tenant_manager: TenantManager = Depends(get_tenant_manager),
) -> Dict[str, Any]:
    """Set API key for a tenant."""
    success = tenant_manager.set_api_key(tenant_id, api_key_hash)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found",
        )
    
    return {"tenant_id": tenant_id, "api_key_set": True}


@router.get("/stats/overview")
async def get_tenant_stats(
    tenant_manager: TenantManager = Depends(get_tenant_manager),
) -> Dict[str, Any]:
    """Get overall tenant statistics."""
    return tenant_manager.get_stats()
