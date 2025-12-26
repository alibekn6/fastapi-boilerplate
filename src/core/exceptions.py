"""
Custom exception classes for structured error handling.
"""

from typing import Any, Dict, Optional


class AppException(Exception):
    """Base exception class for application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(AppException):
    """Authentication failed."""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_ERROR",
            details=details
        )


class AuthorizationError(AppException):
    """User not authorized to perform action."""

    def __init__(self, message: str = "Not authorized", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=403,
            error_code="AUTHORIZATION_ERROR",
            details=details
        )


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=404,
            error_code="NOT_FOUND",
            details=details
        )


class ValidationError(AppException):
    """Input validation failed."""

    def __init__(self, message: str = "Validation failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details
        )


class ConflictError(AppException):
    """Resource conflict (e.g., duplicate username)."""

    def __init__(self, message: str = "Resource conflict", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=409,
            error_code="CONFLICT",
            details=details
        )


class RateLimitError(AppException):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        details = details or {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(
            message=message,
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details=details
        )


class TokenExpiredError(AuthenticationError):
    """JWT token has expired."""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(message=message, details={"error_type": "token_expired"})


class InvalidTokenError(AuthenticationError):
    """JWT token is invalid."""

    def __init__(self, message: str = "Invalid token"):
        super().__init__(message=message, details={"error_type": "invalid_token"})


class InactiveUserError(AuthorizationError):
    """User account is inactive."""

    def __init__(self, message: str = "User account is inactive"):
        super().__init__(message=message, details={"error_type": "inactive_user"})


class SessionLimitError(ConflictError):
    """Maximum number of sessions exceeded."""

    def __init__(self, message: str = "Maximum number of sessions exceeded", max_sessions: int = 5):
        super().__init__(
            message=message,
            details={"error_type": "session_limit", "max_sessions": max_sessions}
        )
