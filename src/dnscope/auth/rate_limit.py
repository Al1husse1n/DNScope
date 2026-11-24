import math
import threading
import time
from collections import deque
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any, Self
from uuid import UUID


@dataclass
class _Window:
    timestamps: deque[float] = field(default_factory=deque)


class RateLimitResult(tuple[bool, float]):
    """Tuple subclass allowing both sync and await call patterns."""

    def __new__(cls, allowed: bool, retry_after: float) -> Self:
        return super().__new__(cls, (allowed, retry_after))

    @property
    def allowed(self) -> bool:
        return self[0]

    @property
    def retry_after(self) -> float:
        return self[1]

    def __await__(self) -> Generator[Any, None, "RateLimitResult"]:
        async def _coro() -> "RateLimitResult":
            return self

        return _coro().__await__()


class InMemoryRateLimiter:
    """Sliding-window rate limiter.

    NOT thread-safe across processes (in-process only).
    Acceptable for P5 single-process deployment; P7 replaces with Redis if multi-process is needed.
    """

    def __init__(self, limit_per_minute: int, window_seconds: float = 60.0) -> None:
        self.limit_per_minute = limit_per_minute
        self.window_seconds = window_seconds
        self._windows: dict[UUID, _Window] = {}
        self._lock = threading.Lock()

    def check(self, key_id: UUID) -> RateLimitResult:
        """Return (allowed, retry_after_seconds).

        If allowed: record this hit and return (True, 0.0).
        If not allowed: return (False, seconds_until_oldest_expires).
        Thread-safety via Lock inside check().
        """
        now = time.monotonic()
        with self._lock:
            window = self._windows.setdefault(key_id, _Window())
            cutoff = now - self.window_seconds

            # Evict timestamps older than sliding window cutoff
            while window.timestamps and window.timestamps[0] <= cutoff:
                window.timestamps.popleft()

            if len(window.timestamps) < self.limit_per_minute:
                window.timestamps.append(now)
                return RateLimitResult(True, 0.0)

            oldest = window.timestamps[0]
            retry_after = max(1.0, math.ceil(oldest + self.window_seconds - now))
            return RateLimitResult(False, float(retry_after))
