from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from app.domain.entities.generation_session import GenerationSession
from app.infrastructure.generation.in_memory_generation_session_repository import (
    InMemoryGenerationSessionRepository,
)
from tests.helpers import req

pytestmark = req("FR-B1")


def make_session(user_id: UUID | None = None) -> GenerationSession:
    return GenerationSession.start(user_id or uuid4(), ttl_minutes=30)


async def test_get_unknown_returns_none():
    assert await InMemoryGenerationSessionRepository().get(uuid4()) is None


async def test_save_then_get_returns_same_session():
    repo = InMemoryGenerationSessionRepository()
    session = make_session()

    await repo.save(session)

    assert await repo.get(session.id) is session


async def test_expired_session_is_not_returned_and_is_removed():
    repo = InMemoryGenerationSessionRepository()
    session = make_session()
    await repo.save(session)

    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    assert await repo.get(session.id) is None
    assert session.id not in repo._sessions
    assert session.user_id not in repo._by_user


async def test_new_session_replaces_previous_one_of_same_user():
    repo = InMemoryGenerationSessionRepository()
    user_id = uuid4()
    first, second = make_session(user_id), make_session(user_id)

    await repo.save(first)
    await repo.save(second)

    assert await repo.get(first.id) is None
    assert await repo.get(second.id) is second


async def test_sessions_of_different_users_are_independent():
    repo = InMemoryGenerationSessionRepository()
    a, b = make_session(), make_session()

    await repo.save(a)
    await repo.save(b)

    assert await repo.get(a.id) is a
    assert await repo.get(b.id) is b


async def test_resaving_same_session_keeps_it():
    repo = InMemoryGenerationSessionRepository()
    session = make_session()

    await repo.save(session)
    await repo.save(session)

    assert await repo.get(session.id) is session


async def test_save_purges_other_expired_sessions():
    repo = InMemoryGenerationSessionRepository()
    stale = make_session()
    await repo.save(stale)
    stale.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)

    await repo.save(make_session())

    assert stale.id not in repo._sessions
    assert len(repo._sessions) == 1
