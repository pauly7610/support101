"""FastAPI routers for Agent Framework."""

from .agents import router as agents_router
from .governance import router as governance_router
from .hitl import router as hitl_router
from .tenants import router as tenants_router

__all__ = [
    "agents_router",
    "governance_router",
    "hitl_router",
    "tenants_router",
]
