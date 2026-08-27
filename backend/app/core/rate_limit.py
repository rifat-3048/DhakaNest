"""Process-local tenant rate limiting for provider-backed endpoints."""

import time
from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock


class SlidingWindowRateLimiter:
    """Bound requests per identity over a fixed rolling interval."""

    def __init__(
        self,
        *,
        limit: int,
        window_seconds: float = 60.0,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.time_fn = time_fn
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, identity: str) -> tuple[bool, int]:
        now = self.time_fn()
        cutoff = now - self.window_seconds
        with self._lock:
            events = self._events[identity]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                retry_after = max(1, int(events[0] + self.window_seconds - now) + 1)
                return False, retry_after
            events.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
