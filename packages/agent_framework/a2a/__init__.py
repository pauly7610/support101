"""
Agent-to-Agent (A2A) Protocol implementation.

Exposes agents as A2A-compatible endpoints for multi-vendor orchestration,
following the Google A2A protocol specification.
"""

from .protocol import A2AServer, AgentCard, AgentSkill
from .router import router as a2a_router

__all__ = [
    "A2AServer",
    "AgentCard",
    "AgentSkill",
    "a2a_router",
]
