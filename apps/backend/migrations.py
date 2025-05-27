import asyncio

from apps.backend.app.core.db import Base, engine


async def run_migrations() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Migrations complete.")


if __name__ == "__main__":
    asyncio.run(run_migrations())
