"""
Global exception handler middleware for consistent error responses.
"""

import traceback
from typing import Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from src.core.exceptions import AppException
from src.core.logging import get_logger

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for handling all exceptions and returning structured error responses."""

    async def dispatch(self, request: Request, call_next: Callable):
        try:
            return await call_next(request)
        except AppException as exc:
            # Handle our custom application exceptions
            logger.warning(
                "application_exception",
                error_code=exc.error_code,
                message=exc.message,
                status_code=exc.status_code,
                details=exc.details,
                path=request.url.path
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "code": exc.error_code,
                        "message": exc.message,
                        "details": exc.details
                    }
                }
            )
        except IntegrityError as exc:
            # Handle database integrity errors (unique constraints, etc.)
            logger.error(
                "database_integrity_error",
                error=str(exc.orig),
                path=request.url.path,
                exc_info=True
            )
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "error": {
                        "code": "INTEGRITY_ERROR",
                        "message": "Database constraint violation",
                        "details": {"error": str(exc.orig)}
                    }
                }
            )
        except SQLAlchemyError as exc:
            # Handle other database errors
            logger.error(
                "database_error",
                error=str(exc),
                path=request.url.path,
                exc_info=True
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "DATABASE_ERROR",
                        "message": "Database operation failed",
                        "details": {}
                    }
                }
            )
        except RequestValidationError as exc:
            # Handle Pydantic validation errors
            logger.warning(
                "validation_error",
                errors=exc.errors(),
                path=request.url.path
            )
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Request validation failed",
                        "details": {"errors": exc.errors()}
                    }
                }
            )
        except Exception as exc:
            # Handle unexpected errors
            logger.error(
                "unexpected_error",
                error=str(exc),
                error_type=type(exc).__name__,
                path=request.url.path,
                traceback=traceback.format_exc(),
                exc_info=True
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred",
                        "details": {}
                    }
                }
            )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Exception handler for AppException and its subclasses.

    This can be registered directly with FastAPI using:
    app.add_exception_handler(AppException, app_exception_handler)
    """
    logger.warning(
        "application_exception",
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        path=request.url.path
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "details": exc.details
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Exception handler for Pydantic validation errors.

    This can be registered directly with FastAPI using:
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    """
    logger.warning(
        "validation_error",
        errors=exc.errors(),
        path=request.url.path
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"errors": exc.errors()}
            }
        }
    )
