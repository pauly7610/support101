from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
import os

POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/support101")

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

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
