"""
Security headers middleware for enhanced application security.
"""

from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.config import Config

config = Config()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all HTTP responses.

    Implements best practices from OWASP Security Headers project:
    https://owasp.org/www-project-secure-headers/
    """

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)

        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy - control information sent in Referer header
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy (CSP)
        # Adjust this based on your application's needs
        if config.ENVIRONMENT == "production":
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",  # Adjust for your needs
                "style-src 'self' 'unsafe-inline'",
                "img-src 'self' data: https:",
                "font-src 'self' data:",
                "connect-src 'self'",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'self'"
            ]
            response.headers["Content-Security-Policy"] = "; ".join(csp_directives)

        # HTTP Strict Transport Security (HSTS)
        # Only enable in production with HTTPS
        if config.ENVIRONMENT == "production":
            # 1 year max-age, include subdomains, allow preload
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Permissions Policy (formerly Feature Policy)
        # Disable potentially dangerous browser features
        permissions_policy = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()"
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_policy)

        # Remove server identification headers
        if "Server" in response.headers:
            del response.headers["Server"]
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]

        return response
