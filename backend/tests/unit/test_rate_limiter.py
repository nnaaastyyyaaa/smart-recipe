import asyncio

import pytest

from app.infrastructure.ai import rate_limiter as rate_limiter_module
from app.infrastructure.ai.rate_limiter import (
    AIRateLimitExceededError,
    InMemoryGeminiRateLimiter,
)
from tests.helpers import req


@pytest.fixture
def clock(monkeypatch):
    state = {"now": 1000.0}
    monkeypatch.setattr(rate_limiter_module.time, "monotonic", lambda: state["now"])
    return state


@req("NFR-4")
@pytest.mark.parametrize("rpm", [0, -1])
def test_rejects_non_positive_limit(rpm):
    with pytest.raises(ValueError):
        InMemoryGeminiRateLimiter(requests_per_minute=rpm)


@req("NFR-4")
async def test_allows_requests_up_to_limit_then_blocks(clock):
    limiter = InMemoryGeminiRateLimiter(requests_per_minute=3)

    for _ in range(3):
        await limiter.acquire()

    with pytest.raises(AIRateLimitExceededError) as error:
        await limiter.acquire()

    assert 1 <= error.value.retry_after <= 61


@req("NFR-4")
async def test_retry_after_reflects_time_until_window_frees(clock):
    limiter = InMemoryGeminiRateLimiter(requests_per_minute=1)
    await limiter.acquire()

    clock["now"] += 20

    with pytest.raises(AIRateLimitExceededError) as error:
        await limiter.acquire()

    assert error.value.retry_after == 41


@req("NFR-4")
async def test_window_slides_after_a_minute(clock):
    limiter = InMemoryGeminiRateLimiter(requests_per_minute=2)
    await limiter.acquire()
    await limiter.acquire()

    clock["now"] += 60
    await limiter.acquire()

    assert len(limiter.requests) == 1


@req("NFR-4")
async def test_blocked_request_is_not_counted(clock):
    limiter = InMemoryGeminiRateLimiter(requests_per_minute=1)
    await limiter.acquire()

    for _ in range(5):
        with pytest.raises(AIRateLimitExceededError):
            await limiter.acquire()

    assert len(limiter.requests) == 1


@req("NFR-4")
async def test_concurrent_requests_never_exceed_limit():
    limiter = InMemoryGeminiRateLimiter(requests_per_minute=5)

    results = await asyncio.gather(
        *(limiter.acquire() for _ in range(20)),
        return_exceptions=True,
    )

    allowed = [r for r in results if r is None]
    blocked = [r for r in results if isinstance(r, AIRateLimitExceededError)]

    assert len(allowed) == 5
    assert len(blocked) == 15
