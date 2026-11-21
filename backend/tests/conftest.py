from __future__ import annotations

import json
import os
from pathlib import Path

from sqlalchemy.engine import make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _resolve_test_database_url() -> str:
    explicit = os.getenv("TEST_DATABASE_URL")

    if explicit:
        url = make_url(explicit)
    else:
        url = make_url(
            os.getenv(
                "DATABASE_URL",
                "postgresql+asyncpg://postgres:password@localhost:5432/smart_recipe_db",
            )
        )

        if not (url.database or "").endswith("_test"):
            url = url.set(database=f"{url.database}_test")

    if not (url.database or "").endswith("_test"):
        raise RuntimeError()

    return url.render_as_string(hide_password=False)


TEST_DATABASE_URL = _resolve_test_database_url()

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("GEMINI_API_KEY", "test-api-key")
os.environ.setdefault("GEMINI_MODEL", "test-model")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-key-minimum-32-characters-long")

import httpx 
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from tests.fakes import FakeRecipeGenerator
from tests.helpers import Catalog


def pytest_collection_modifyitems(items):
    for item in items:
        parts = Path(str(item.fspath)).parts

        for layer in ("unit", "component", "system"):
            if layer in parts:
                item.add_marker(getattr(pytest.mark, layer))


def pytest_collection_finish(session):
    target = os.getenv("REQ_REPORT")

    if not target:
        return

    mapping: dict[str, list[str]] = {}

    for item in session.items:
        for marker in item.iter_markers(name="req"):
            for requirement in marker.args:
                mapping.setdefault(requirement, []).append(item.nodeid)

    Path(target).write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def pytest_sessionfinish(session, exitstatus):
    from tests.helpers import PERF

    target = os.getenv("PERF_REPORT")

    if target and PERF:
        Path(target).write_text(json.dumps(PERF, ensure_ascii=False, indent=2), encoding="utf-8")


async def recreate_database(database_url: str) -> None:
    url = make_url(database_url)
    maintenance = url.set(database="postgres")

    engine = create_async_engine(
        maintenance,
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )

    try:
        async with engine.connect() as connection:
            await connection.execute(
                text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)')
            )
            await connection.execute(text(f'CREATE DATABASE "{url.database}"'))
    finally:
        await engine.dispose()


async def drop_database(database_url: str) -> None:
    url = make_url(database_url)
    engine = create_async_engine(
        url.set(database="postgres"),
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )

    try:
        async with engine.connect() as connection:
            await connection.execute(
                text(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)')
            )
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    from app.infrastructure.database.base import Base
    import app.infrastructure.database.models

    await recreate_database(TEST_DATABASE_URL)

    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()
    await drop_database(TEST_DATABASE_URL)


@pytest.fixture(scope="session")
def session_factory(db_engine):
    return async_sessionmaker(
        db_engine,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture
async def clean_db(db_engine):
    from app.infrastructure.database.base import Base

    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)

    async with db_engine.begin() as connection:
        await connection.execute(
            text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE")
        )

    yield


@pytest_asyncio.fixture
async def db(session_factory, clean_db):
    async with session_factory() as session:
        yield session

        try:
            await session.commit()
        except Exception:
            await session.rollback()


@pytest.fixture
def fake_ai():
    return FakeRecipeGenerator()


@pytest.fixture
def api_app(session_factory, clean_db, fake_ai, monkeypatch):
    from app.infrastructure.database import database
    from app.infrastructure.generation.in_memory_generation_session_repository import (
        InMemoryGenerationSessionRepository,
    )
    from app.main import app

    monkeypatch.setattr(database, "AsyncSessionLocal", session_factory)

    app.state.recipe_generator = fake_ai
    app.state.generation_sessions = InMemoryGenerationSessionRepository()

    yield app


def make_client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://testserver",
    )


@pytest_asyncio.fixture
async def client(api_app):
    async with make_client(api_app) as http_client:
        yield http_client


@pytest_asyncio.fixture
async def client_factory(api_app):
    created: list[httpx.AsyncClient] = []

    def factory() -> httpx.AsyncClient:
        http_client = make_client(api_app)
        created.append(http_client)
        return http_client

    yield factory

    for http_client in created:
        await http_client.aclose()


@pytest_asyncio.fixture
async def catalog(session_factory, clean_db) -> Catalog:
    from app.infrastructure.database.models import (
        CategoryModel,
        DietaryRestrictionModel,
        ProductModel,
    )

    categories = {
        "veg": "Овочі",
        "meat": "М'ясо",
        "dairy": "Молочні продукти",
        "grains": "Крупи та борошно",
    }
    restrictions = {
        "vegan": "Веганське",
        "gluten": "Без глютену",
        "lactose": "Безлактозне",
    }
    products = {
        "tomato": ("Помідор", "veg", []),
        "cucumber": ("Огірок", "veg", []),
        "carrot": ("Морква", "veg", []),
        "potato": ("Картопля", "veg", []),
        "chicken": ("Куряче філе", "meat", ["vegan"]),
        "beef": ("Яловичина", "meat", ["vegan"]),
        "milk": ("Молоко", "dairy", ["vegan", "lactose"]),
        "cheese": ("Сир", "dairy", ["vegan", "lactose"]),
        "rice": ("Рис", "grains", []),
        "flour": ("Борошно", "grains", ["gluten"]),
        "pasta": ("Макарони", "grains", ["gluten"]),
    }

    result = Catalog()

    async with session_factory() as session:
        category_models = {k: CategoryModel(name=v) for k, v in categories.items()}
        restriction_models = {k: DietaryRestrictionModel(name=v) for k, v in restrictions.items()}
        session.add_all([*category_models.values(), *restriction_models.values()])
        await session.flush()

        product_models = {}

        for key, (name, category_key, _) in products.items():
            model = ProductModel(name=name, category_id=category_models[category_key].id)
            model.restrictions = []
            product_models[key] = model

        session.add_all(product_models.values())
        await session.flush()

        for key, (_, _, restriction_keys) in products.items():
            product_models[key].restrictions = [restriction_models[r] for r in restriction_keys]

        await session.commit()

        result.categories = {k: m.id for k, m in category_models.items()}
        result.restrictions = {k: m.id for k, m in restriction_models.items()}
        result.products = {k: m.id for k, m in product_models.items()}
        result.names = {k: v[0] for k, v in products.items()}

    return result


@pytest_asyncio.fixture
async def authed(client):
    from tests.helpers import register

    client.user = await register(client)
    return client
