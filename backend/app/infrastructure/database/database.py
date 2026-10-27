import asyncio
import logging
import os
from collections.abc import AsyncGenerator

from sqlalchemy.exc import OperationalError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database_connection() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def wait_for_database(max_attempts: int = 10, delay_seconds: float = 2) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            await check_database_connection()
            logger.info("PostgreSQL connection established.")
            return

        except OperationalError as exc:
            if attempt == max_attempts:
                raise RuntimeError(
                    f"PostgreSQL is unavailable after {max_attempts} attempts."
                ) from exc

            logger.warning(
                "Database unavailable (attempt %s/%s). Retrying in %s seconds.",
                attempt,
                max_attempts,
                delay_seconds
            )

            await asyncio.sleep(delay_seconds)