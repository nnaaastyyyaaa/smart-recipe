"""Компонентні тести /api/health."""
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers import API, req


@req("NFR-1")
async def test_health_is_ok_when_database_is_reachable(client):
    response = await client.get(f"{API}/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


@req("NFR-1")
async def test_health_returns_503_when_database_is_down(api_app, client):
    from app.infrastructure.database.database import get_db

    class BrokenSession(AsyncSession):
        async def execute(self, *args, **kwargs):
            raise ConnectionError("db down")

    async def broken_db():
        yield BrokenSession()

    api_app.dependency_overrides[get_db] = broken_db
    try:
        response = await client.get(f"{API}/health")
    finally:
        api_app.dependency_overrides.pop(get_db, None)

    assert response.status_code == 503
    assert response.json()["detail"] == "database unavailable"
