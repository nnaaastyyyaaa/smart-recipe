import asyncio
import logging
import os
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_database_connection() -> None:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


async def wait_for_database(max_attempts: int = 10, delay_seconds: float = 2) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            await asyncio.to_thread(check_database_connection)

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