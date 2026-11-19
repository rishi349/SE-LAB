"""In-memory sliding-window rate limiter for sensitive operations.

Kept deliberately simple: one process, one dictionary. Limits reset on restart, which is
acceptable for this single-instance deployment (see docs/decisions.md).
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

# scope -> (max requests, window in seconds)
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "register": (5, 60),
    "login": (10, 60),
    "transfer": (10, 60),
    "lookup": (30, 60),
    "profile_update": (10, 60),
    "account_deletion": (5, 60),
    "admin_funding": (30, 60),
    "reconciliation": (5, 60),
}


class SlidingWindowRateLimiter:
    def __init__(self, clock=time.monotonic) -> None:
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: int) -> int | None:
        """Record a request. Returns None if allowed, else seconds to wait before retrying."""
        now = self._clock()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return max(1, int(hits[0] + window_seconds - now) + 1)
            hits.append(now)
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
