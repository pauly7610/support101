"""
Database-based state store implementation using SQLAlchemy.

Provides persistent storage with full query capabilities.
"""

import json
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Index, Integer, String, Text, and_, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .base import StateStore

Base = declarative_base()


class AgentStateModel(Base):
    """SQLAlchemy model for agent state."""

    __tablename__ = "agent_framework_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(64), nullable=False, index=True)
    execution_id = Column(String(64), nullable=False, index=True)
    state_data = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (Index("ix_agent_execution", "agent_id", "execution_id", unique=True),)


class HITLRequestModel(Base):
    """SQLAlchemy model for HITL requests."""

    __tablename__ = "agent_framework_hitl_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), nullable=False, unique=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    agent_id = Column(String(64), index=True)
    status = Column(String(32), nullable=False, index=True)
    priority = Column(String(16), nullable=False)
    request_data = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditEventModel(Base):
    """SQLAlchemy model for audit events."""

    __tablename__ = "agent_framework_audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(64), nullable=False, unique=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(64), index=True)
    agent_id = Column(String(64), index=True)
    execution_id = Column(String(64), index=True)
    event_data = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class TenantModel(Base):
    """SQLAlchemy model for tenants."""

    __tablename__ = "agent_framework_tenants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(64), nullable=False, unique=True, index=True)
    status = Column(String(32), nullable=False, index=True)
    tenant_data = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DatabaseStateStore(StateStore):
    """
    SQLAlchemy-based implementation of StateStore.

    Supports PostgreSQL, MySQL, SQLite with async drivers.
    """

    def __init__(
        self,
        database_url: str,
        echo: bool = False,
    ) -> None:
        self._database_url = database_url
        self._engine = create_async_engine(database_url, echo=echo)
        self._session_factory = sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self._initialized = False

    async def initialize(self) -> None:
        """Create tables if they don't exist."""
        if not self._initialized:
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            self._initialized = True

    async def _get_session(self) -> AsyncSession:
        await self.initialize()
        return self._session_factory()

    async def save_agent_state(
        self,
        agent_id: str,
        execution_id: str,
        state: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> bool:
        async with await self._get_session() as session:
            stmt = select(AgentStateModel).where(
                and_(
                    AgentStateModel.agent_id == agent_id,
                    AgentStateModel.execution_id == execution_id,
                )
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.state_data = json.dumps(state)
                existing.updated_at = datetime.utcnow()
            else:
                model = AgentStateModel(
                    agent_id=agent_id,
                    execution_id=execution_id,
                    state_data=json.dumps(state),
                )
                session.add(model)

            await session.commit()
            return True

    async def get_agent_state(
        self,
        agent_id: str,
        execution_id: str,
    ) -> dict[str, Any] | None:
        async with await self._get_session() as session:
            stmt = select(AgentStateModel).where(
                and_(
                    AgentStateModel.agent_id == agent_id,
                    AgentStateModel.execution_id == execution_id,
                )
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model:
                return json.loads(model.state_data)
            return None

    async def delete_agent_state(
        self,
        agent_id: str,
        execution_id: str,
    ) -> bool:
        async with await self._get_session() as session:
            stmt = select(AgentStateModel).where(
                and_(
                    AgentStateModel.agent_id == agent_id,
                    AgentStateModel.execution_id == execution_id,
                )
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model:
                await session.delete(model)
                await session.commit()
                return True
            return False

    async def list_agent_executions(
        self,
        agent_id: str,
        limit: int = 100,
    ) -> list[str]:
        async with await self._get_session() as session:
            stmt = (
                select(AgentStateModel.execution_id)
                .where(AgentStateModel.agent_id == agent_id)
                .order_by(AgentStateModel.created_at.desc())
                .limit(limit)
            )
            result = await session.execute(stmt)
            return [row[0] for row in result.fetchall()]

    async def save_hitl_request(
        self,
        request_id: str,
        request_data: dict[str, Any],
        ttl_seconds: int | None = None,
    ) -> bool:
        async with await self._get_session() as session:
            model = HITLRequestModel(
                request_id=request_id,
                tenant_id=request_data.get("tenant_id", ""),
                agent_id=request_data.get("agent_id"),
                status=request_data.get("status", "pending"),
                priority=request_data.get("priority", "medium"),
                request_data=json.dumps(request_data),
            )
            session.add(model)
            await session.commit()
            return True

    async def get_hitl_request(
        self,
        request_id: str,
    ) -> dict[str, Any] | None:
        async with await self._get_session() as session:
            stmt = select(HITLRequestModel).where(HITLRequestModel.request_id == request_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model:
                return json.loads(model.request_data)
            return None

    async def update_hitl_request(
        self,
        request_id: str,
        updates: dict[str, Any],
    ) -> bool:
        async with await self._get_session() as session:
            stmt = select(HITLRequestModel).where(HITLRequestModel.request_id == request_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if not model:
                return False

            data = json.loads(model.request_data)
            data.update(updates)

            model.request_data = json.dumps(data)
            model.status = data.get("status", model.status)
            model.updated_at = datetime.utcnow()

            await session.commit()
            return True

    async def list_hitl_requests(
        self,
        tenant_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        async with await self._get_session() as session:
            stmt = select(HITLRequestModel)

            conditions = []
            if tenant_id:
                conditions.append(HITLRequestModel.tenant_id == tenant_id)
            if status:
                conditions.append(HITLRequestModel.status == status)

            if conditions:
                stmt = stmt.where(and_(*conditions))

            stmt = stmt.order_by(HITLRequestModel.created_at.desc()).limit(limit)
            result = await session.execute(stmt)

            return [json.loads(row.request_data) for row in result.scalars()]

    async def save_audit_event(
        self,
        event_id: str,
        event_data: dict[str, Any],
    ) -> bool:
        async with await self._get_session() as session:
            model = AuditEventModel(
                event_id=event_id,
                event_type=event_data.get("event_type", ""),
                tenant_id=event_data.get("tenant_id"),
                agent_id=event_data.get("agent_id"),
                execution_id=event_data.get("execution_id"),
                event_data=json.dumps(event_data),
                timestamp=(
                    datetime.fromisoformat(
                        event_data.get("timestamp", datetime.utcnow().isoformat()).replace(
                            "Z", "+00:00"
                        )
                    )
                    if event_data.get("timestamp")
                    else datetime.utcnow()
                ),
            )
            session.add(model)
            await session.commit()
            return True

    async def query_audit_events(
        self,
        tenant_id: str | None = None,
        agent_id: str | None = None,
        event_type: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        async with await self._get_session() as session:
            stmt = select(AuditEventModel)

            conditions = []
            if tenant_id:
                conditions.append(AuditEventModel.tenant_id == tenant_id)
            if agent_id:
                conditions.append(AuditEventModel.agent_id == agent_id)
            if event_type:
                conditions.append(AuditEventModel.event_type == event_type)
            if start_time:
                conditions.append(AuditEventModel.timestamp >= start_time)
            if end_time:
                conditions.append(AuditEventModel.timestamp <= end_time)

            if conditions:
                stmt = stmt.where(and_(*conditions))

            stmt = stmt.order_by(AuditEventModel.timestamp.desc()).offset(offset).limit(limit)
            result = await session.execute(stmt)

            return [json.loads(row.event_data) for row in result.scalars()]

    async def save_tenant(
        self,
        tenant_id: str,
        tenant_data: dict[str, Any],
    ) -> bool:
        async with await self._get_session() as session:
            stmt = select(TenantModel).where(TenantModel.tenant_id == tenant_id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.tenant_data = json.dumps(tenant_data)
                existing.status = tenant_data.get("status", existing.status)
                existing.updated_at = datetime.utcnow()
            else:
                model = TenantModel(
                    tenant_id=tenant_id,
                    status=tenant_data.get("status", "pending"),
                    tenant_data=json.dumps(tenant_data),
                )
                session.add(model)

            await session.commit()
            return True

    async def get_tenant(
        self,
        tenant_id: str,
    ) -> dict[str, Any] | None:
        async with await self._get_session() as session:
            stmt = select(TenantModel).where(TenantModel.tenant_id == tenant_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()

            if model:
                return json.loads(model.tenant_data)
            return None

    async def list_tenants(
        self,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        async with await self._get_session() as session:
            stmt = select(TenantModel)

            if status:
                stmt = stmt.where(TenantModel.status == status)

            stmt = stmt.order_by(TenantModel.created_at.desc()).limit(limit)
            result = await session.execute(stmt)

            return [json.loads(row.tenant_data) for row in result.scalars()]

    async def health_check(self) -> bool:
        try:
            async with await self._get_session() as session:
                await session.execute(select(1))
                return True
        except Exception:
            return False

    async def close(self) -> None:
        await self._engine.dispose()
