"""
Rate limiting middleware for API endpoints.
"""

from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import Config
from src.core.rate_limiter import check_all_rate_limits
from src.core.logging import get_logger

config = Config()
logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces rate limiting on all requests.

    Rate limiting is applied per IP address by default.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        if not config.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Get client identifier (IP address)
        client_ip = request.client.host if request.client else "unknown"

        # Skip rate limiting for health check endpoints
        if request.url.path in ["/health", "/health/ready", "/metrics"]:
            return await call_next(request)

        try:
            # Check all rate limits (minute, hour, day)
            check_all_rate_limits(client_ip)

            # Proceed with request
            response = await call_next(request)
            return response

        except Exception as exc:
            # Rate limit errors are handled by ErrorHandlerMiddleware
            raise
