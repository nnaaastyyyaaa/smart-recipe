"""Системні тести БД: міграції Alembic та початкове наповнення довідників (FR-D1).

Міграції виконуються в підпроцесі на окремій порожній БД ``<тестова>_migrations`` —
так само, як це робить docker-compose (``alembic upgrade head``).
"""
import os
import subprocess
import sys

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from tests.conftest import BACKEND_DIR, TEST_DATABASE_URL, drop_database, recreate_database
from tests.helpers import req

ALEMBIC_INI = "app/infrastructure/database/alembic.ini"
MIGRATION_DB_URL = make_url(TEST_DATABASE_URL).set(
    database=f"{make_url(TEST_DATABASE_URL).database}_migrations"
).render_as_string(hide_password=False)

EXPECTED_TABLES = {
    "users", "sessions", "categories", "products", "dietary_restrictions",
    "product_restrictions", "recipes", "saved_recipes", "alembic_version",
}


def alembic(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "alembic", "-c", ALEMBIC_INI, *args],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": MIGRATION_DB_URL.replace("%", "%%")},
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest_asyncio.fixture(scope="module")
async def migrated_engine():
    await recreate_database(MIGRATION_DB_URL)
    result = alembic("upgrade", "head")
    assert result.returncode == 0, f"alembic upgrade head впав:\n{result.stderr}"

    engine = create_async_engine(MIGRATION_DB_URL, poolclass=NullPool)
    yield engine

    await engine.dispose()
    await drop_database(MIGRATION_DB_URL)


async def scalar(engine, sql: str):
    async with engine.connect() as connection:
        return (await connection.execute(text(sql))).scalar_one()


async def rows(engine, sql: str):
    async with engine.connect() as connection:
        return (await connection.execute(text(sql))).all()


@req("FR-D1")
def test_migration_history_has_single_head():
    result = alembic("heads")

    assert result.returncode == 0, result.stderr
    heads = [line for line in result.stdout.splitlines() if "(head)" in line]
    assert len(heads) == 1, f"Знайдено кілька head-ревізій: {heads}"


@req("FR-D1")
def test_upgrade_head_is_idempotent(migrated_engine):
    assert alembic("upgrade", "head").returncode == 0


@req("FR-D1")
async def test_all_expected_tables_exist(migrated_engine):
    tables = {r[0] for r in await rows(migrated_engine, "SELECT table_name FROM information_schema.tables WHERE table_schema='public'")}

    assert EXPECTED_TABLES <= tables


async def test_profile_restrictions_table_was_dropped(migrated_engine):
    tables = {r[0] for r in await rows(migrated_engine, "SELECT table_name FROM information_schema.tables WHERE table_schema='public'")}

    assert "user_dietary_restrictions" not in tables


@req("FR-D1")
@pytest.mark.parametrize("table", ["categories", "products", "dietary_restrictions", "product_restrictions"])
async def test_reference_tables_are_seeded(migrated_engine, table):
    assert await scalar(migrated_engine, f"SELECT count(*) FROM {table}") > 0, (
        f"Таблиця {table} порожня після `alembic upgrade head` — початкове наповнення не виконано"
    )


@req("FR-D1")
async def test_user_tables_start_empty(migrated_engine):
    for table in ("users", "sessions", "recipes", "saved_recipes"):
        assert await scalar(migrated_engine, f"SELECT count(*) FROM {table}") == 0


@req("FR-D1", "FR-B3")
async def test_every_seeded_product_belongs_to_existing_category(migrated_engine):
    orphans = await scalar(
        migrated_engine,
        "SELECT count(*) FROM products p LEFT JOIN categories c ON c.id = p.category_id WHERE c.id IS NULL",
    )

    assert orphans == 0


@req("FR-D1", "FR-B3")
async def test_every_category_contains_products(migrated_engine):
    empty = await rows(
        migrated_engine,
        "SELECT c.name FROM categories c LEFT JOIN products p ON p.category_id = c.id GROUP BY c.id, c.name HAVING count(p.id) = 0",
    )

    assert empty == [], f"Порожні категорії: {[r[0] for r in empty]}"


@req("FR-D1", "FR-B2")
async def test_each_restriction_leaves_enough_products_for_a_recipe(migrated_engine):
    """Для будь-якого одного обмеження лишається щонайменше 2 продукти (мінімум для генерації)."""
    too_few = await rows(
        migrated_engine,
        """
        SELECT r.name,
               (SELECT count(*) FROM products p
                 WHERE NOT EXISTS (SELECT 1 FROM product_restrictions pr
                                    WHERE pr.product_id = p.id AND pr.restriction_id = r.id)) AS allowed
          FROM dietary_restrictions r
        """,
    )

    assert too_few, "немає жодного дієтичного обмеження"
    assert all(allowed >= 2 for _, allowed in too_few), f"Замало продуктів: {too_few}"


@req("FR-D1", "FR-B2")
async def test_dietary_filtering_is_meaningful(migrated_engine):
    """Хоча б одне обмеження справді виключає частину продуктів (інакше фільтр безглуздий)."""
    assert await scalar(migrated_engine, "SELECT count(DISTINCT restriction_id) FROM product_restrictions") >= 1
    assert await scalar(migrated_engine, "SELECT count(DISTINCT product_id) FROM product_restrictions") >= 1


@req("FR-D1")
async def test_catalog_names_are_not_blank_and_fit_limits(migrated_engine):
    for table in ("categories", "products", "dietary_restrictions"):
        bad = await scalar(migrated_engine, f"SELECT count(*) FROM {table} WHERE btrim(name) = '' OR length(name) > 60")
        assert bad == 0, table


@req("FR-D1")
async def test_seeded_catalog_works_through_the_api(migrated_engine, session_factory):
    """Інтеграція: застосунок читає дані, наповнені міграціями (а не лише тестові фікстури)."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.infrastructure.database.repositories.product_repository import SQLAlchemyProductRepository

    factory = async_sessionmaker(migrated_engine, expire_on_commit=False)

    async with factory() as session:
        products = await SQLAlchemyProductRepository(session).get_all(limit=200)

    assert len(products) > 0
