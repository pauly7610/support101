"""
Activity Graph backed by Apache AGE (Postgres graph extension).

Provides a knowledge graph linking customers, tickets, resolutions,
articles, agents, and playbooks. Supports Cypher queries for traversal
and pattern discovery.

Falls back to relational SQL queries on existing tables when AGE
extension is not installed.

Requires:
    - PostgreSQL with Apache AGE extension (optional)
    - DATABASE_URL or AGENT_FRAMEWORK_DATABASE_URL env var
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .graph_models import (
    AgentNode,
    ArticleNode,
    CustomerNode,
    GraphEdge,
    PlaybookNode,
    ResolutionNode,
    TicketNode,
    executed_by_edge,
    resolved_by_edge,
    used_article_edge,
)

logger = logging.getLogger(__name__)

_SQLALCHEMY_AVAILABLE = False

try:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    _SQLALCHEMY_AVAILABLE = True
except ImportError:
    logger.debug("SQLAlchemy not installed; ActivityGraph will use in-memory fallback")


class ActivityGraph:
    """
    Knowledge graph for agent framework activity.

    Uses Apache AGE (Postgres extension) for graph storage and Cypher queries.
    Falls back to in-memory graph when AGE or Postgres is unavailable.

    Graph name: configurable via ACTIVITY_GRAPH_NAME env var (default: support101)

    Usage::

        graph = ActivityGraph()
        await graph.initialize()
        await graph.record_resolution(...)
        results = await graph.find_similar_resolutions(category="billing")
    """

    def __init__(
        self,
        graph_name: Optional[str] = None,
        database_url: Optional[str] = None,
    ) -> None:
        self._graph_name = graph_name or os.getenv("ACTIVITY_GRAPH_NAME", "support101")
        self._db_url = database_url or os.getenv("AGENT_FRAMEWORK_DATABASE_URL") or os.getenv("DATABASE_URL")
        self._engine = None
        self._session_factory = None
        self._age_available = False
        self._initialized = False

        # In-memory fallback
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._edges: List[Dict[str, Any]] = []

    @property
    def available(self) -> bool:
        return self._initialized

    @property
    def using_age(self) -> bool:
        return self._age_available

    async def initialize(self) -> bool:
        """Initialize the graph. Returns True if AGE is available."""
        if self._initialized:
            return self._age_available

        if not _SQLALCHEMY_AVAILABLE or not self._db_url:
            logger.info("ActivityGraph: no DB configured, using in-memory fallback")
            self._initialized = True
            return False

        try:
            db_url = self._db_url
            if not db_url.startswith("postgresql+asyncpg://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

            self._engine = create_async_engine(db_url, echo=False, pool_size=3)
            self._session_factory = sessionmaker(
                self._engine, class_=AsyncSession, expire_on_commit=False
            )

            # Check if AGE extension is available
            async with self._session_factory() as session:
                try:
                    await session.execute(text("LOAD 'age';"))
                    await session.execute(
                        text("SET search_path = ag_catalog, '$user', public;")
                    )
                    # Try to create graph if it doesn't exist
                    result = await session.execute(
                        text(
                            "SELECT count(*) FROM ag_catalog.ag_graph "
                            f"WHERE name = '{self._graph_name}';"
                        )
                    )
                    count = result.scalar()
                    if count == 0:
                        await session.execute(
                            text(f"SELECT create_graph('{self._graph_name}');")
                        )
                    await session.commit()
                    self._age_available = True
                    logger.info("ActivityGraph: Apache AGE initialized (graph=%s)", self._graph_name)
                except Exception as e:
                    logger.info("ActivityGraph: AGE not available (%s), using relational fallback", e)
                    self._age_available = False

            self._initialized = True
            return self._age_available

        except Exception as e:
            logger.warning("ActivityGraph: initialization failed: %s", e)
            self._initialized = True
            return False

    async def _execute_cypher(self, cypher: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query via AGE."""
        if not self._age_available or self._session_factory is None:
            return []

        async with self._session_factory() as session:
            try:
                await session.execute(text("LOAD 'age';"))
                await session.execute(text("SET search_path = ag_catalog, '$user', public;"))

                # AGE uses SELECT * FROM cypher('graph_name', $$ CYPHER $$) as (col agtype);
                sql = f"SELECT * FROM cypher('{self._graph_name}', $$ {cypher} $$) as (result agtype);"
                result = await session.execute(text(sql))
                rows = result.fetchall()
                await session.commit()
                return [{"result": str(row[0])} for row in rows]
            except Exception as e:
                logger.debug("Cypher query failed: %s", e)
                await session.rollback()
                return []

    # ── Node Operations ───────────────────────────────────────

    async def upsert_node(self, label: str, node_id: str, properties: Dict[str, Any]) -> bool:
        """Create or update a node in the graph."""
        if self._age_available:
            props_str = ", ".join(f"{k}: '{v}'" if isinstance(v, str) else f"{k}: {v}" for k, v in properties.items())
            cypher = f"MERGE (n:{label} {{id: '{node_id}'}}) SET n += {{{props_str}}} RETURN n"
            result = await self._execute_cypher(cypher)
            return len(result) > 0

        # In-memory fallback
        key = f"{label}:{node_id}"
        self._nodes[key] = {"label": label, "id": node_id, **properties}
        return True

    async def create_edge(self, edge: GraphEdge) -> bool:
        """Create an edge between two nodes."""
        if self._age_available:
            props_str = ""
            if edge.properties:
                parts = []
                for k, v in edge.properties.items():
                    if isinstance(v, str):
                        parts.append(f"{k}: '{v}'")
                    else:
                        parts.append(f"{k}: {v}")
                props_str = " {" + ", ".join(parts) + "}"

            cypher = (
                f"MATCH (a:{edge.from_label} {{id: '{edge.from_id}'}}), "
                f"(b:{edge.to_label} {{id: '{edge.to_id}'}}) "
                f"CREATE (a)-[r:{edge.label}{props_str}]->(b) RETURN r"
            )
            result = await self._execute_cypher(cypher)
            return len(result) > 0

        # In-memory fallback
        self._edges.append({
            "label": edge.label,
            "from_id": edge.from_id,
            "from_label": edge.from_label,
            "to_id": edge.to_id,
            "to_label": edge.to_label,
            "properties": edge.properties,
        })
        return True

    # ── High-Level Operations ─────────────────────────────────

    async def record_resolution(
        self,
        golden_path_id: str = "",
        agent_blueprint: str = "",
        category: str = "",
        input_query: str = "",
        steps: Optional[List[str]] = None,
        articles: Optional[List[str]] = None,
        success: bool = True,
        confidence: float = 0.0,
        tenant_id: str = "",
        ticket_id: str = "",
        customer_id: str = "",
        agent_id: str = "",
    ) -> str:
        """Record a resolution outcome in the graph."""
        resolution_id = golden_path_id or f"res-{uuid4().hex[:12]}"

        # Upsert Resolution node
        resolution = ResolutionNode(
            id=resolution_id,
            method=category,
            confidence=confidence,
            approved=success,
            success=success,
            steps=steps or [],
            tenant_id=tenant_id,
        )
        await self.upsert_node("Resolution", resolution_id, resolution.to_props())

        # Upsert Agent node and create edge
        if agent_blueprint or agent_id:
            aid = agent_id or agent_blueprint
            agent = AgentNode(id=aid, blueprint=agent_blueprint, tenant_id=tenant_id)
            await self.upsert_node("Agent", aid, agent.to_props())
            await self.create_edge(executed_by_edge(resolution_id, aid))

        # Upsert Ticket node and create edge
        if ticket_id:
            ticket = TicketNode(id=ticket_id, category=category, tenant_id=tenant_id, subject=input_query[:200])
            await self.upsert_node("Ticket", ticket_id, ticket.to_props())
            await self.create_edge(resolved_by_edge(ticket_id, resolution_id))

        # Upsert Article nodes and create edges
        for article_id in (articles or []):
            article = ArticleNode(id=article_id, tenant_id=tenant_id)
            await self.upsert_node("Article", article_id, article.to_props())
            await self.create_edge(used_article_edge(resolution_id, article_id))

        # Upsert Customer node and create FILED edge
        if customer_id and ticket_id:
            customer = CustomerNode(id=customer_id, tenant_id=tenant_id)
            await self.upsert_node("Customer", customer_id, customer.to_props())
            from .graph_models import filed_edge
            await self.create_edge(filed_edge(customer_id, ticket_id))

        return resolution_id

    async def find_similar_resolutions(
        self,
        category: str = "",
        tenant_id: str = "",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find successful resolutions for a given category."""
        if self._age_available:
            where_parts = ["r.success = true"]
            if category:
                where_parts.append(f"r.method = '{category}'")
            if tenant_id:
                where_parts.append(f"r.tenant_id = '{tenant_id}'")
            where_clause = " AND ".join(where_parts)

            cypher = (
                f"MATCH (t:Ticket)-[:RESOLVED_BY]->(r:Resolution)-[:EXECUTED_BY]->(a:Agent) "
                f"WHERE {where_clause} "
                f"RETURN r, a, t ORDER BY r.confidence DESC LIMIT {limit}"
            )
            return await self._execute_cypher(cypher)

        # In-memory fallback
        resolutions = []
        for key, node in self._nodes.items():
            if not key.startswith("Resolution:"):
                continue
            if not node.get("success", False):
                continue
            if category and node.get("method") != category:
                continue
            if tenant_id and node.get("tenant_id") != tenant_id:
                continue
            resolutions.append(node)

        resolutions.sort(key=lambda r: r.get("confidence", 0), reverse=True)
        return resolutions[:limit]

    async def get_customer_journey(
        self,
        customer_id: str,
        tenant_id: str = "",
    ) -> List[Dict[str, Any]]:
        """Get the full journey for a customer (tickets, resolutions, articles)."""
        if self._age_available:
            cypher = (
                f"MATCH (c:Customer {{id: '{customer_id}'}})-[:FILED]->(t:Ticket)"
                f"-[:RESOLVED_BY]->(r:Resolution) "
                f"RETURN c, t, r ORDER BY t.created_at DESC"
            )
            return await self._execute_cypher(cypher)

        # In-memory fallback
        journey = []
        customer_tickets = [
            e for e in self._edges
            if e["label"] == "FILED" and e["from_id"] == customer_id
        ]
        for edge in customer_tickets:
            ticket_key = f"Ticket:{edge['to_id']}"
            ticket = self._nodes.get(ticket_key, {})
            resolutions = [
                self._nodes.get(f"Resolution:{re['to_id']}", {})
                for re in self._edges
                if re["label"] == "RESOLVED_BY" and re["from_id"] == edge["to_id"]
            ]
            journey.append({"ticket": ticket, "resolutions": resolutions})
        return journey

    async def get_playbook_candidates(
        self,
        category: str,
        tenant_id: str = "",
        min_count: int = 3,
    ) -> List[Dict[str, Any]]:
        """Find resolution patterns that could become playbooks."""
        if self._age_available:
            where_parts = [f"r.method = '{category}'", "r.success = true"]
            if tenant_id:
                where_parts.append(f"r.tenant_id = '{tenant_id}'")
            where_clause = " AND ".join(where_parts)

            cypher = (
                f"MATCH (r:Resolution)-[:EXECUTED_BY]->(a:Agent) "
                f"WHERE {where_clause} "
                f"WITH a.blueprint AS blueprint, collect(r) AS resolutions "
                f"WHERE size(resolutions) >= {min_count} "
                f"RETURN blueprint, resolutions"
            )
            return await self._execute_cypher(cypher)

        # In-memory fallback
        by_blueprint: Dict[str, List[Dict[str, Any]]] = {}
        for edge in self._edges:
            if edge["label"] != "EXECUTED_BY":
                continue
            res_key = f"Resolution:{edge['from_id']}"
            res = self._nodes.get(res_key, {})
            if not res.get("success"):
                continue
            if category and res.get("method") != category:
                continue
            if tenant_id and res.get("tenant_id") != tenant_id:
                continue
            agent_key = f"Agent:{edge['to_id']}"
            agent = self._nodes.get(agent_key, {})
            bp = agent.get("blueprint", "unknown")
            by_blueprint.setdefault(bp, []).append(res)

        return [
            {"blueprint": bp, "resolutions": ress, "count": len(ress)}
            for bp, ress in by_blueprint.items()
            if len(ress) >= min_count
        ]

    async def get_resolution_stats(
        self, tenant_id: str = ""
    ) -> Dict[str, Any]:
        """Get graph statistics."""
        if self._age_available:
            results = {}
            for label in ["Customer", "Ticket", "Agent", "Article", "Resolution", "Playbook"]:
                cypher = f"MATCH (n:{label}) RETURN count(n)"
                rows = await self._execute_cypher(cypher)
                results[label.lower() + "_count"] = len(rows)
            return results

        # In-memory fallback
        label_counts: Dict[str, int] = {}
        for key in self._nodes:
            label = key.split(":")[0]
            label_counts[label.lower() + "_count"] = label_counts.get(label.lower() + "_count", 0) + 1

        return {
            **label_counts,
            "edge_count": len(self._edges),
            "using_age": self._age_available,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Synchronous stats for dashboard."""
        return {
            "initialized": self._initialized,
            "using_age": self._age_available,
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "graph_name": self._graph_name,
        }
