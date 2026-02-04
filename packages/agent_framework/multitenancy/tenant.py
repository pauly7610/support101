"""
Tenant Model and Configuration.

Defines tenant structure for multi-tenant agent deployment.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class TenantStatus(str, Enum):
    """Tenant lifecycle status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DEACTIVATED = "deactivated"


class TenantTier(str, Enum):
    """Tenant subscription tiers."""

    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class TenantLimits:
    """Resource limits for a tenant."""

    max_agents: int = 5
    max_concurrent_executions: int = 10
    max_requests_per_minute: int = 60
    max_storage_mb: int = 100
    max_vector_documents: int = 10000
    max_hitl_queue_size: int = 100

    def to_dict(self) -> Dict[str, int]:
        return {
            "max_agents": self.max_agents,
            "max_concurrent_executions": self.max_concurrent_executions,
            "max_requests_per_minute": self.max_requests_per_minute,
            "max_storage_mb": self.max_storage_mb,
            "max_vector_documents": self.max_vector_documents,
            "max_hitl_queue_size": self.max_hitl_queue_size,
        }


TIER_LIMITS = {
    TenantTier.FREE: TenantLimits(
        max_agents=2,
        max_concurrent_executions=2,
        max_requests_per_minute=10,
        max_storage_mb=50,
        max_vector_documents=1000,
        max_hitl_queue_size=10,
    ),
    TenantTier.STARTER: TenantLimits(
        max_agents=5,
        max_concurrent_executions=5,
        max_requests_per_minute=30,
        max_storage_mb=200,
        max_vector_documents=5000,
        max_hitl_queue_size=50,
    ),
    TenantTier.PROFESSIONAL: TenantLimits(
        max_agents=20,
        max_concurrent_executions=20,
        max_requests_per_minute=100,
        max_storage_mb=1000,
        max_vector_documents=50000,
        max_hitl_queue_size=200,
    ),
    TenantTier.ENTERPRISE: TenantLimits(
        max_agents=100,
        max_concurrent_executions=100,
        max_requests_per_minute=1000,
        max_storage_mb=10000,
        max_vector_documents=500000,
        max_hitl_queue_size=1000,
    ),
}


@dataclass
class TenantConfig:
    """Configuration for a tenant."""

    name: str
    tier: TenantTier = TenantTier.STARTER

    allowed_blueprints: List[str] = field(default_factory=list)

    custom_limits: Optional[TenantLimits] = None

    pinecone_namespace: Optional[str] = None
    database_schema: Optional[str] = None

    api_key_hash: Optional[str] = None
    webhook_url: Optional[str] = None

    settings: Dict[str, Any] = field(default_factory=dict)

    def get_limits(self) -> TenantLimits:
        """Get effective limits (custom or tier-based)."""
        if self.custom_limits:
            return self.custom_limits
        return TIER_LIMITS.get(self.tier, TIER_LIMITS[TenantTier.STARTER])


@dataclass
class Tenant:
    """A tenant in the multi-tenant system."""

    tenant_id: str = field(default_factory=lambda: str(uuid4()))
    config: TenantConfig = field(default_factory=lambda: TenantConfig(name="Default"))
    status: TenantStatus = TenantStatus.PENDING

    owner_id: Optional[str] = None
    admin_ids: List[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    activated_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    _current_usage: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self._current_usage:
            self._current_usage = {
                "agents": 0,
                "concurrent_executions": 0,
                "requests_this_minute": 0,
                "storage_mb": 0,
                "vector_documents": 0,
                "hitl_queue_size": 0,
            }

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def tier(self) -> TenantTier:
        return self.config.tier

    @property
    def limits(self) -> TenantLimits:
        return self.config.get_limits()

    def is_active(self) -> bool:
        """Check if tenant is active."""
        return self.status == TenantStatus.ACTIVE

    def can_create_agent(self) -> bool:
        """Check if tenant can create more agents."""
        return self._current_usage.get("agents", 0) < self.limits.max_agents

    def can_execute(self) -> bool:
        """Check if tenant can start more executions."""
        return (
            self._current_usage.get("concurrent_executions", 0)
            < self.limits.max_concurrent_executions
        )

    def check_rate_limit(self) -> bool:
        """Check if tenant is within rate limits."""
        return (
            self._current_usage.get("requests_this_minute", 0) < self.limits.max_requests_per_minute
        )

    def increment_usage(self, metric: str, amount: int = 1) -> None:
        """Increment a usage metric."""
        self._current_usage[metric] = self._current_usage.get(metric, 0) + amount

    def decrement_usage(self, metric: str, amount: int = 1) -> None:
        """Decrement a usage metric."""
        self._current_usage[metric] = max(0, self._current_usage.get(metric, 0) - amount)

    def reset_rate_limit(self) -> None:
        """Reset rate limit counter (called every minute)."""
        self._current_usage["requests_this_minute"] = 0

    def get_usage(self) -> Dict[str, Any]:
        """Get current usage with limits."""
        limits = self.limits
        return {
            "agents": {
                "current": self._current_usage.get("agents", 0),
                "limit": limits.max_agents,
            },
            "concurrent_executions": {
                "current": self._current_usage.get("concurrent_executions", 0),
                "limit": limits.max_concurrent_executions,
            },
            "requests_this_minute": {
                "current": self._current_usage.get("requests_this_minute", 0),
                "limit": limits.max_requests_per_minute,
            },
            "storage_mb": {
                "current": self._current_usage.get("storage_mb", 0),
                "limit": limits.max_storage_mb,
            },
            "vector_documents": {
                "current": self._current_usage.get("vector_documents", 0),
                "limit": limits.max_vector_documents,
            },
        }

    def activate(self) -> None:
        """Activate the tenant."""
        self.status = TenantStatus.ACTIVE
        self.activated_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def suspend(self, reason: str = "") -> None:
        """Suspend the tenant."""
        self.status = TenantStatus.SUSPENDED
        self.suspended_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.metadata["suspension_reason"] = reason

    def deactivate(self) -> None:
        """Deactivate the tenant."""
        self.status = TenantStatus.DEACTIVATED
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize tenant."""
        return {
            "tenant_id": self.tenant_id,
            "name": self.name,
            "tier": self.tier.value,
            "status": self.status.value,
            "owner_id": self.owner_id,
            "admin_ids": self.admin_ids,
            "limits": self.limits.to_dict(),
            "usage": self.get_usage(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "settings": self.config.settings,
        }
