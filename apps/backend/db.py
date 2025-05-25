import os

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

POSTGRES_URL = os.getenv(
    "POSTGRES_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/support101"
)

engine = create_async_engine(POSTGRES_URL, echo=True, future=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
Base = declarative_base()


class Escalation(Base):
    __tablename__ = "escalations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64))
    text = Column(Text)
    timestamp = Column(Float)
    last_updated = Column(DateTime)
    confidence = Column(Float, nullable=True)
    source_url = Column(Text, nullable=True)


def get_engine() -> create_async_engine:
    return engine


def get_session() -> AsyncSession:
    return SessionLocal()


def get_base() -> declarative_base:
    return Base


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


class Escalation(Base):
    __tablename__ = "escalations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(64))
    text = Column(Text)
    timestamp = Column(Float)
    last_updated = Column(DateTime)
    confidence = Column(Float, nullable=True)
    source_url = Column(Text, nullable=True)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
