"""
In-memory rate limiter with sliding window algorithm.

For production with multiple instances, use Redis-backed rate limiting.
"""

import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from threading import Lock

from src.core.config import Config
from src.core.exceptions import RateLimitError

config = Config()


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    For production with horizontal scaling, replace with Redis-backed implementation.
    """

    def __init__(self):
        # Structure: {identifier: [(timestamp, count)]}
        self._requests: Dict[str, List[Tuple[float, int]]] = defaultdict(list)
        self._lock = Lock()

    def _clean_old_requests(self, identifier: str, window_seconds: int) -> None:
        """Remove requests older than the window."""
        current_time = time.time()
        cutoff_time = current_time - window_seconds

        with self._lock:
            if identifier in self._requests:
                self._requests[identifier] = [
                    (ts, count) for ts, count in self._requests[identifier]
                    if ts > cutoff_time
                ]
                if not self._requests[identifier]:
                    del self._requests[identifier]

    def check_rate_limit(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if identifier has exceeded rate limit.

        Args:
            identifier: Unique identifier (e.g., IP address, user ID)
            max_requests: Maximum number of requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        current_time = time.time()
        self._clean_old_requests(identifier, window_seconds)

        with self._lock:
            request_count = sum(count for _, count in self._requests[identifier])

            if request_count >= max_requests:
                # Calculate retry_after from oldest request
                if self._requests[identifier]:
                    oldest_timestamp = min(ts for ts, _ in self._requests[identifier])
                    retry_after = int(window_seconds - (current_time - oldest_timestamp)) + 1
                    return False, retry_after
                return False, window_seconds

            # Add new request
            self._requests[identifier].append((current_time, 1))
            return True, None

    def check_rate_limit_or_raise(
        self,
        identifier: str,
        max_requests: int,
        window_seconds: int
    ) -> None:
        """
        Check rate limit and raise RateLimitError if exceeded.

        Args:
            identifier: Unique identifier
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds

        Raises:
            RateLimitError: If rate limit is exceeded
        """
        is_allowed, retry_after = self.check_rate_limit(identifier, max_requests, window_seconds)
        if not is_allowed:
            raise RateLimitError(
                message=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                retry_after=retry_after
            )

    def reset(self, identifier: str) -> None:
        """Reset rate limit for an identifier."""
        with self._lock:
            if identifier in self._requests:
                del self._requests[identifier]


# Global rate limiter instance
rate_limiter = RateLimiter()


def check_rate_limit_per_minute(identifier: str) -> None:
    """Check per-minute rate limit."""
    if config.RATE_LIMIT_ENABLED:
        rate_limiter.check_rate_limit_or_raise(
            identifier=f"minute:{identifier}",
            max_requests=config.RATE_LIMIT_PER_MINUTE,
            window_seconds=60
        )


def check_rate_limit_per_hour(identifier: str) -> None:
    """Check per-hour rate limit."""
    if config.RATE_LIMIT_ENABLED:
        rate_limiter.check_rate_limit_or_raise(
            identifier=f"hour:{identifier}",
            max_requests=config.RATE_LIMIT_PER_HOUR,
            window_seconds=3600
        )


def check_rate_limit_per_day(identifier: str) -> None:
    """Check per-day rate limit."""
    if config.RATE_LIMIT_ENABLED:
        rate_limiter.check_rate_limit_or_raise(
            identifier=f"day:{identifier}",
            max_requests=config.RATE_LIMIT_PER_DAY,
            window_seconds=86400
        )


def check_all_rate_limits(identifier: str) -> None:
    """Check all rate limits (minute, hour, day)."""
    check_rate_limit_per_minute(identifier)
    check_rate_limit_per_hour(identifier)
    check_rate_limit_per_day(identifier)
