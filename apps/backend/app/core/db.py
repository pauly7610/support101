import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

print("DATABASE_URL at import (core/db.py):", os.getenv("DATABASE_URL"))

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/support101"
)
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

__all__ = ["Base", "engine", "SessionLocal", "AsyncSession"]


async def get_db():
    async with SessionLocal() as session:
        yield session
