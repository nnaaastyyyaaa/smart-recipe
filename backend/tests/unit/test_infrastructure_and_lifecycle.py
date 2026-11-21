import pytest
from sqlalchemy.exc import OperationalError

import app.main as main_module
from app.infrastructure.database import database
from tests.helpers import req


class FakeSession:
    def __init__(self):
        self.commits = self.rollbacks = 0

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


@pytest.fixture
def fake_session(monkeypatch):
    session = FakeSession()
    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: session)
    return session


async def test_get_db_commits_on_success(fake_session):
    generator = database.get_db()
    assert await generator.__anext__() is fake_session

    with pytest.raises(StopAsyncIteration):
        await generator.__anext__()

    assert (fake_session.commits, fake_session.rollbacks) == (1, 0)


async def test_get_db_rolls_back_and_reraises_on_error(fake_session):
    generator = database.get_db()
    await generator.__anext__()

    with pytest.raises(ValueError):
        await generator.athrow(ValueError("boom"))

    assert (fake_session.commits, fake_session.rollbacks) == (0, 1)


def operational_error():
    return OperationalError("SELECT 1", {}, Exception("down"))


async def test_wait_for_database_returns_immediately_when_available(monkeypatch):
    calls = []

    async def ok():
        calls.append(1)

    monkeypatch.setattr(database, "check_database_connection", ok)

    await database.wait_for_database(max_attempts=3, delay_seconds=0)

    assert len(calls) == 1


@req("NFR-1")
async def test_wait_for_database_retries_until_available(monkeypatch):
    attempts = []

    async def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise operational_error()

    monkeypatch.setattr(database, "check_database_connection", flaky)

    await database.wait_for_database(max_attempts=5, delay_seconds=0)

    assert len(attempts) == 3


@req("NFR-1")
async def test_wait_for_database_gives_up_after_max_attempts(monkeypatch):
    attempts = []

    async def down():
        attempts.append(1)
        raise operational_error()

    monkeypatch.setattr(database, "check_database_connection", down)

    with pytest.raises(RuntimeError, match="unavailable after 4 attempts"):
        await database.wait_for_database(max_attempts=4, delay_seconds=0)

    assert len(attempts) == 4


class SpyGenerator:
    instances: list = []

    def __init__(self, api_key, model, rate_limiter):
        self.api_key, self.model, self.rate_limiter = api_key, model, rate_limiter
        self.closed = False
        SpyGenerator.instances.append(self)

    async def close(self):
        self.closed = True


@pytest.fixture
def lifespan_env(monkeypatch):
    waited = []

    async def fake_wait():
        waited.append(True)

    SpyGenerator.instances = []
    monkeypatch.setattr(main_module, "wait_for_database", fake_wait)
    monkeypatch.setattr(main_module, "GeminiRecipeGenerator", SpyGenerator)
    monkeypatch.setattr(main_module, "GEMINI_API_KEY", "key")
    monkeypatch.setattr(main_module, "GEMINI_MODEL", "model")
    monkeypatch.setattr(main_module, "GEMINI_APP_RPM_LIMIT", 7)
    monkeypatch.setattr(main_module, "JWT_SECRET", "x" * 32)
    return waited


@req("NFR-4")
async def test_lifespan_wires_generator_with_rpm_limiter_and_session_store(lifespan_env):
    application = main_module.FastAPI()

    async with main_module.lifespan(application):
        generator = application.state.recipe_generator

        assert lifespan_env == [True]
        assert generator.api_key == "key" and generator.model == "model"
        assert generator.rate_limiter.requests_per_minute == 7
        assert application.state.generation_sessions is not None
        assert generator.closed is False

    assert generator.closed is True


@pytest.mark.parametrize("name", ["GEMINI_API_KEY", "GEMINI_MODEL"])
async def test_lifespan_fails_fast_without_gemini_settings(lifespan_env, monkeypatch, name):
    monkeypatch.setattr(main_module, name, None)

    with pytest.raises(RuntimeError, match=name):
        async with main_module.lifespan(main_module.FastAPI()):
            pass


def test_app_exposes_routes_and_cors():
    paths = set(main_module.app.openapi()["paths"])

    assert "/api/health" in paths
    assert "/api/auth/login" in paths
    assert "/api/generations" in paths
    assert "/api/recipes/saved" in paths
    assert any(m.cls.__name__ == "CORSMiddleware" for m in main_module.app.user_middleware)


def test_removed_profile_restriction_endpoints_are_gone():
    paths = set(main_module.app.openapi()["paths"])

    assert "/api/users/me" in paths
    assert "/api/users/me/dietary-restrictions" not in paths
    assert "/api/recipes/suggestions" not in paths
    assert "/api/recipes/generate" not in paths


@pytest.mark.parametrize(
    "raw,expected",
    [("1", True), ("true", True), ("TRUE", True), (" yes ", True), ("on", True),
     ("0", False), ("false", False), ("no", False), ("", False), ("abc", False)],
)
def test_get_bool_parses_environment_values(monkeypatch, raw, expected):
    from app.core.config import _get_bool

    monkeypatch.setenv("SOME_FLAG", raw)

    assert _get_bool("SOME_FLAG", default=not expected) is expected


def test_get_bool_uses_default_when_variable_is_missing(monkeypatch):
    from app.core.config import _get_bool

    monkeypatch.delenv("SOME_FLAG", raising=False)

    assert _get_bool("SOME_FLAG", True) is True
    assert _get_bool("SOME_FLAG", False) is False


def test_generation_limits_match_specification():
    from app.core import config

    assert config.MAX_RECIPE_SUGGESTIONS == 16
    assert config.SUGGESTIONS_PAGE_SIZE == 8
    assert config.GENERATION_SESSION_TTL_MINUTES > 0


@req("NFR-3")
@pytest.mark.parametrize("secret", [None, "", "short-secret"])
async def test_lifespan_fails_fast_without_strong_jwt_secret(lifespan_env, monkeypatch, secret):
    monkeypatch.setattr(main_module, "JWT_SECRET", secret)

    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        async with main_module.lifespan(main_module.FastAPI()):
            pass


def test_cors_exposes_total_count_header():
    cors = next(m for m in main_module.app.user_middleware if m.cls.__name__ == "CORSMiddleware")

    assert "X-Total-Count" in cors.kwargs["expose_headers"]
