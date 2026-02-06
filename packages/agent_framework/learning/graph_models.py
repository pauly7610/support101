"""
Graph node and edge type definitions for the Activity Graph.

Defines the schema for the Apache AGE knowledge graph:
  Nodes: Customer, Ticket, Agent, Article, Resolution, Playbook
  Edges: FILED, RESOLVED_BY, USED_ARTICLE, EXECUTED_BY, FOLLOWED,
         SIMILAR_TO, ESCALATED_TO, HAS_SENTIMENT
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# ── Node Types ────────────────────────────────────────────────


@dataclass
class CustomerNode:
    """A customer in the knowledge graph."""

    id: str = ""
    name: str = ""
    email: str = ""
    tier: str = "standard"
    tenant_id: str = ""
    is_vip: bool = False
    created_at: str = ""

    @property
    def label(self) -> str:
        return "Customer"

    def to_props(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "tier": self.tier,
            "tenant_id": self.tenant_id,
            "is_vip": self.is_vip,
            "created_at": self.created_at or datetime.utcnow().isoformat(),
        }


@dataclass
class TicketNode:
    """A support ticket in the knowledge graph."""

    id: str = ""
    subject: str = ""
    priority: str = "medium"
    status: str = "open"
    category: str = "general"
    tenant_id: str = ""
    created_at: str = ""

    @property
    def label(self) -> str:
        return "Ticket"

    def to_props(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject,
            "priority": self.priority,
            "status": self.status,
            "category": self.category,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at or datetime.utcnow().isoformat(),
        }


@dataclass
class AgentNode:
    """An agent in the knowledge graph."""

    id: str = ""
    blueprint: str = ""
    name: str = ""
    tenant_id: str = ""

    @property
    def label(self) -> str:
        return "Agent"

    def to_props(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "blueprint": self.blueprint,
            "name": self.name,
            "tenant_id": self.tenant_id,
        }


@dataclass
class ArticleNode:
    """A knowledge base article in the graph."""

    id: str = ""
    title: str = ""
    topic: str = ""
    tenant_id: str = ""

    @property
    def label(self) -> str:
        return "Article"

    def to_props(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "topic": self.topic,
            "tenant_id": self.tenant_id,
        }


@dataclass
class ResolutionNode:
    """A resolution outcome in the graph."""

    id: str = ""
    method: str = ""
    confidence: float = 0.0
    approved: bool = False
    success: bool = False
    steps: list[str] = field(default_factory=list)
    tenant_id: str = ""
    created_at: str = ""

    @property
    def label(self) -> str:
        return "Resolution"

    def to_props(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "method": self.method,
            "confidence": self.confidence,
            "approved": self.approved,
            "success": self.success,
            "steps": ",".join(self.steps),
            "tenant_id": self.tenant_id,
            "created_at": self.created_at or datetime.utcnow().isoformat(),
        }


@dataclass
class PlaybookNode:
    """A playbook (auto-generated resolution pattern) in the graph."""

    id: str = ""
    name: str = ""
    category: str = ""
    steps: list[str] = field(default_factory=list)
    success_rate: float = 0.0
    sample_count: int = 0
    tenant_id: str = ""
    created_at: str = ""

    @property
    def label(self) -> str:
        return "Playbook"

    def to_props(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "steps": ",".join(self.steps),
            "success_rate": self.success_rate,
            "sample_count": self.sample_count,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at or datetime.utcnow().isoformat(),
        }


# ── Edge Types ────────────────────────────────────────────────


@dataclass
class GraphEdge:
    """A generic edge in the knowledge graph."""

    label: str = ""
    from_id: str = ""
    from_label: str = ""
    to_id: str = ""
    to_label: str = ""
    properties: dict[str, Any] = field(default_factory=dict)

    def to_props(self) -> dict[str, Any]:
        return {**self.properties}


# Convenience edge constructors


def filed_edge(customer_id: str, ticket_id: str) -> GraphEdge:
    return GraphEdge(
        label="FILED",
        from_id=customer_id,
        from_label="Customer",
        to_id=ticket_id,
        to_label="Ticket",
    )


def resolved_by_edge(ticket_id: str, resolution_id: str, duration_ms: int = 0) -> GraphEdge:
    return GraphEdge(
        label="RESOLVED_BY",
        from_id=ticket_id,
        from_label="Ticket",
        to_id=resolution_id,
        to_label="Resolution",
        properties={"duration_ms": duration_ms},
    )


def used_article_edge(resolution_id: str, article_id: str) -> GraphEdge:
    return GraphEdge(
        label="USED_ARTICLE",
        from_id=resolution_id,
        from_label="Resolution",
        to_id=article_id,
        to_label="Article",
    )


def executed_by_edge(resolution_id: str, agent_id: str) -> GraphEdge:
    return GraphEdge(
        label="EXECUTED_BY",
        from_id=resolution_id,
        from_label="Resolution",
        to_id=agent_id,
        to_label="Agent",
    )


def followed_edge(resolution_id: str, playbook_id: str) -> GraphEdge:
    return GraphEdge(
        label="FOLLOWED",
        from_id=resolution_id,
        from_label="Resolution",
        to_id=playbook_id,
        to_label="Playbook",
    )


def similar_to_edge(ticket_id_a: str, ticket_id_b: str, similarity: float = 0.0) -> GraphEdge:
    return GraphEdge(
        label="SIMILAR_TO",
        from_id=ticket_id_a,
        from_label="Ticket",
        to_id=ticket_id_b,
        to_label="Ticket",
        properties={"similarity": similarity},
    )


def escalated_to_edge(from_agent_id: str, to_agent_id: str, reason: str = "") -> GraphEdge:
    return GraphEdge(
        label="ESCALATED_TO",
        from_id=from_agent_id,
        from_label="Agent",
        to_id=to_agent_id,
        to_label="Agent",
        properties={"reason": reason},
    )


def has_sentiment_edge(customer_id: str, ticket_id: str, score: float = 0.0) -> GraphEdge:
    return GraphEdge(
        label="HAS_SENTIMENT",
        from_id=customer_id,
        from_label="Customer",
        to_id=ticket_id,
        to_label="Ticket",
        properties={"score": score, "timestamp": datetime.utcnow().isoformat()},
    )
