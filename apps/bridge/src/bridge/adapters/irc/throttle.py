"""IRC flood control: token bucket for rate limiting."""

from __future__ import annotations

import time


class TokenBucket:
    """Token bucket for IRC message rate limiting."""

    def __init__(self, limit: int, refill_rate: float = 1.0) -> None:
        self._limit = limit
        self._tokens = float(limit)
        self._refill_rate = refill_rate
        self._last_refill = time.monotonic()

    def use_token(self) -> bool:
        """Consume one token. Returns True if token was available, False otherwise."""
        self._refill()
        if self._tokens >= 1:
            self._tokens -= 1
            return True
        return False

    def acquire(self) -> float:
        """Return seconds to wait before a token is available. 0 if available now."""
        self._refill()
        if self._tokens >= 1:
            return 0.0
        # Need 1 - tokens more; at refill_rate per second
        return (1 - self._tokens) / self._refill_rate

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._limit, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now
