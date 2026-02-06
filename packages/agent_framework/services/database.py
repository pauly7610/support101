"""
Async Postgres database service for agent framework.

Wraps SQLAlchemy async sessions for ticket, customer, and knowledge base operations.
Users must set DATABASE_URL in their environment to enable real DB calls.
Falls back to stub responses when DB is unavailable.
"""

import logging
import os
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_AVAILABLE = False
_engine = None
_session_factory = None

try:
    from sqlalchemy import (
        Boolean,
        Column,
        DateTime,
        Integer,
        String,
        Text,
        func,
        select,
    )
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import declarative_base, sessionmaker

    _AVAILABLE = True
except ImportError:
    logger.debug("SQLAlchemy not installed; DatabaseService will use stubs")

if _AVAILABLE:
    Base = declarative_base()

    class TicketModel(Base):
        __tablename__ = "support_tickets"

        id = Column(Integer, primary_key=True, autoincrement=True)
        ticket_id = Column(String(64), nullable=False, unique=True, index=True)
        tenant_id = Column(String(64), nullable=False, index=True)
        customer_id = Column(String(64), nullable=False, index=True)
        subject = Column(String(512), nullable=False)
        description = Column(Text, nullable=False, default="")
        priority = Column(String(16), nullable=False, default="medium")
        status = Column(String(32), nullable=False, default="open")
        category = Column(String(64), nullable=True)
        assigned_agent_id = Column(String(64), nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    class CustomerModel(Base):
        __tablename__ = "support_customers"

        id = Column(Integer, primary_key=True, autoincrement=True)
        customer_id = Column(String(64), nullable=False, unique=True, index=True)
        tenant_id = Column(String(64), nullable=False, index=True)
        name = Column(String(256), nullable=True)
        email = Column(String(256), nullable=True)
        tier = Column(String(32), nullable=False, default="standard")
        is_vip = Column(Boolean, default=False)
        created_at = Column(DateTime, default=datetime.utcnow)

    class KnowledgeArticleModel(Base):
        __tablename__ = "knowledge_articles"

        id = Column(Integer, primary_key=True, autoincrement=True)
        article_id = Column(String(64), nullable=False, unique=True, index=True)
        tenant_id = Column(String(64), nullable=False, index=True)
        title = Column(String(512), nullable=False)
        content = Column(Text, nullable=False)
        tags = Column(Text, nullable=True)
        status = Column(String(32), nullable=False, default="published")
        last_reviewed_at = Column(DateTime, nullable=True)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

else:
    Base = None
    TicketModel = None
    CustomerModel = None
    KnowledgeArticleModel = None


def _get_engine():
    global _engine, _session_factory
    if _engine is not None:
        return _engine
    db_url = os.getenv("AGENT_FRAMEWORK_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url or not _AVAILABLE:
        return None
    if not db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    _engine = create_async_engine(db_url, echo=False, pool_size=5, max_overflow=10)
    _session_factory = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)
    return _engine


class DatabaseService:
    """
    Async Postgres service for agent operations.

    Requires env var: DATABASE_URL or AGENT_FRAMEWORK_DATABASE_URL
    Falls back to stub dicts when DB is not configured.
    """

    def __init__(self) -> None:
        self._engine = _get_engine()
        self._initialized = False

    @property
    def available(self) -> bool:
        return self._engine is not None and _AVAILABLE

    async def initialize(self) -> None:
        if not self.available or self._initialized:
            return
        try:
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            self._initialized = True
            logger.info("DatabaseService: tables created/verified")
        except Exception as e:
            logger.warning("DatabaseService: failed to initialize tables: %s", e)

    def _session(self) -> "AsyncSession":
        return _session_factory()

    # ── Tickets ──────────────────────────────────────────────────────

    async def create_ticket(
        self,
        ticket_id: str,
        tenant_id: str,
        customer_id: str,
        subject: str,
        description: str = "",
        priority: str = "medium",
        category: str | None = None,
    ) -> dict[str, Any]:
        if not self.available:
            return {
                "ticket_created": True,
                "ticket_id": ticket_id,
                "subject": subject,
                "priority": priority,
                "source": "stub",
                "timestamp": datetime.utcnow().isoformat(),
            }
        await self.initialize()
        async with self._session() as session:
            ticket = TicketModel(
                ticket_id=ticket_id,
                tenant_id=tenant_id,
                customer_id=customer_id,
                subject=subject,
                description=description,
                priority=priority,
                category=category,
            )
            session.add(ticket)
            await session.commit()
            return {
                "ticket_created": True,
                "ticket_id": ticket_id,
                "subject": subject,
                "priority": priority,
                "source": "database",
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def get_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        if not self.available:
            return None
        await self.initialize()
        async with self._session() as session:
            result = await session.execute(
                select(TicketModel).where(TicketModel.ticket_id == ticket_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            return {
                "ticket_id": row.ticket_id,
                "tenant_id": row.tenant_id,
                "customer_id": row.customer_id,
                "subject": row.subject,
                "description": row.description,
                "priority": row.priority,
                "status": row.status,
                "category": row.category,
                "assigned_agent_id": row.assigned_agent_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }

    async def assign_ticket(self, ticket_id: str, agent_id: str) -> dict[str, Any]:
        if not self.available:
            return {
                "assigned": True,
                "ticket_id": ticket_id,
                "agent_id": agent_id,
                "source": "stub",
                "assigned_at": datetime.utcnow().isoformat(),
            }
        await self.initialize()
        async with self._session() as session:
            result = await session.execute(
                select(TicketModel).where(TicketModel.ticket_id == ticket_id)
            )
            ticket = result.scalar_one_or_none()
            if ticket:
                ticket.assigned_agent_id = agent_id
                ticket.status = "assigned"
                ticket.updated_at = datetime.utcnow()
                await session.commit()
            return {
                "assigned": ticket is not None,
                "ticket_id": ticket_id,
                "agent_id": agent_id,
                "source": "database",
                "assigned_at": datetime.utcnow().isoformat(),
            }

    # ── Customers ────────────────────────────────────────────────────

    async def get_customer_history(self, customer_id: str) -> dict[str, Any]:
        if not self.available:
            return {
                "customer_id": customer_id,
                "total_tickets": 0,
                "open_tickets": 0,
                "avg_satisfaction": None,
                "is_vip": False,
                "notes": [],
                "source": "stub",
            }
        await self.initialize()
        async with self._session() as session:
            customer_result = await session.execute(
                select(CustomerModel).where(CustomerModel.customer_id == customer_id)
            )
            customer = customer_result.scalar_one_or_none()

            total_q = await session.execute(
                select(func.count())
                .select_from(TicketModel)
                .where(TicketModel.customer_id == customer_id)
            )
            total_tickets = total_q.scalar() or 0

            open_q = await session.execute(
                select(func.count())
                .select_from(TicketModel)
                .where(
                    TicketModel.customer_id == customer_id,
                    TicketModel.status.in_(["open", "assigned", "in_progress"]),
                )
            )
            open_tickets = open_q.scalar() or 0

            return {
                "customer_id": customer_id,
                "name": customer.name if customer else None,
                "email": customer.email if customer else None,
                "tier": customer.tier if customer else "standard",
                "total_tickets": total_tickets,
                "open_tickets": open_tickets,
                "avg_satisfaction": None,
                "is_vip": customer.is_vip if customer else False,
                "notes": [],
                "source": "database",
            }

    # ── Knowledge Articles ───────────────────────────────────────────

    async def list_articles(
        self, tenant_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        if not self.available:
            return []
        await self.initialize()
        async with self._session() as session:
            query = select(KnowledgeArticleModel)
            if tenant_id:
                query = query.where(KnowledgeArticleModel.tenant_id == tenant_id)
            query = query.limit(limit)
            result = await session.execute(query)
            rows = result.scalars().all()
            return [
                {
                    "article_id": r.article_id,
                    "title": r.title,
                    "content": r.content[:500],
                    "tags": r.tags,
                    "status": r.status,
                    "last_reviewed_at": (
                        r.last_reviewed_at.isoformat() if r.last_reviewed_at else None
                    ),
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in rows
            ]

    async def update_article(
        self, article_id: str, title: str | None = None, content: str | None = None
    ) -> dict[str, Any]:
        if not self.available:
            return {"updated": False, "article_id": article_id, "source": "stub"}
        await self.initialize()
        async with self._session() as session:
            result = await session.execute(
                select(KnowledgeArticleModel).where(KnowledgeArticleModel.article_id == article_id)
            )
            article = result.scalar_one_or_none()
            if article:
                if title:
                    article.title = title
                if content:
                    article.content = content
                article.updated_at = datetime.utcnow()
                await session.commit()
            return {
                "updated": article is not None,
                "article_id": article_id,
                "source": "database",
            }

    async def close(self) -> None:
        if self._engine:
            await self._engine.dispose()


_db_service: DatabaseService | None = None


def get_database_service() -> DatabaseService:
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
