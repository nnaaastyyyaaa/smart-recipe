import asyncio
import time
from collections import deque


class AIRateLimitExceededError(Exception):

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after


class InMemoryGeminiRateLimiter:

    def __init__(self, requests_per_minute: int) -> None:
        if requests_per_minute < 1:
            raise ValueError("RPM limit must be greater than 0.")

        self.requests_per_minute = requests_per_minute
        self.requests: deque[float] = deque()
        self.lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self.lock:
            now = time.monotonic()

            while (
                self.requests
                and now - self.requests[0] >= 60
            ):
                self.requests.popleft()

            if len(self.requests) >= self.requests_per_minute:
                retry_after = max(
                    1,
                    int(60 - (now - self.requests[0])) + 1,
                )

                raise AIRateLimitExceededError(retry_after)

            self.requests.append(now)