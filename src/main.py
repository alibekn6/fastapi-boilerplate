"""
Main FastAPI application with comprehensive middleware stack and security features.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.v1.auth import router as auth_router
from src.api.v1.users import router as users_router
from src.api.middlewares.error_handler import (
    ErrorHandlerMiddleware,
    app_exception_handler,
    validation_exception_handler
)
from src.api.middlewares.security_headers import SecurityHeadersMiddleware
from src.core.config import Config
from src.core.exceptions import AppException
from src.core.logging import get_logger, setup_logging
from src.core.rate_limit_config import limiter
from src.db.database import check_db_connection, close_db

config = Config()

setup_logging(
    level="DEBUG" if config.DEBUG else config.LOG_LEVEL,
    json_logs=(config.LOG_FORMAT == "json"),
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events, including database connectivity checks.
    """
    logger.info(
        "application_startup",
        app_name=config.APP_NAME,
        environment=config.ENVIRONMENT,
        debug=config.DEBUG
    )

    # Check database connection on startup
    db_connected = await check_db_connection()
    if not db_connected:
        logger.error("database_connection_failed_on_startup")
        # In production, you might want to fail startup if DB is not available
        # raise RuntimeError("Database connection failed")

    yield

    # Cleanup on shutdown
    logger.info("application_shutdown", app_name=config.APP_NAME)
    await close_db()


app = FastAPI(
    title=config.APP_NAME,
    description="Production-ready FastAPI application with comprehensive security",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if config.DEBUG else None,  # Disable docs in production
    redoc_url="/redoc" if config.DEBUG else None,
)

# Attach limiter to app state for access in routers
app.state.limiter = limiter

# ============================================================================
# MIDDLEWARE STACK (order matters - executed outside-in)
# ============================================================================

# 1. Error Handler - Must be first to catch all exceptions
app.add_middleware(ErrorHandlerMiddleware)

# 2. Security Headers - Add security headers to all responses
app.add_middleware(SecurityHeadersMiddleware)

# 3. CORS - Configure cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins_list,
    allow_credentials=config.CORS_ALLOW_CREDENTIALS,
    allow_methods=config.CORS_ALLOW_METHODS.split(","),
    allow_headers=config.CORS_ALLOW_HEADERS.split(",") if config.CORS_ALLOW_HEADERS != "*" else ["*"],
    expose_headers=["X-Correlation-ID", "X-Request-ID"],
)

# Note: Rate limiting is now handled per-endpoint using SlowAPI decorators
# Old global rate limit middleware removed in favor of flexible per-endpoint limits
# Note: CorrelationIdMiddleware and LoggingMiddleware can be added here
# if they exist in your codebase


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ============================================================================
# HEALTH CHECK ENDPOINTS
# ============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """
    Basic liveness probe.

    Returns 200 if the service is running.
    """
    return {
        "status": "healthy",
        "service": config.APP_NAME,
        "environment": config.ENVIRONMENT
    }


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """
    Readiness probe with database connectivity check.

    Returns 200 if the service is ready to accept traffic.
    Returns 503 if database is not available.
    """
    db_connected = await check_db_connection()

    if not db_connected:
        from fastapi import status
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unavailable",
                "service": config.APP_NAME,
                "database": "disconnected"
            }
        )

    return {
        "status": "ready",
        "service": config.APP_NAME,
        "environment": config.ENVIRONMENT,
        "database": "connected"
    }


# ============================================================================
# API ROUTERS
# ============================================================================

app.include_router(
    auth_router,
    prefix=f"/api/{config.API_VERSION}",
    tags=["Authentication"]
)

app.include_router(
    users_router,
    prefix=f"/api/{config.API_VERSION}",
    tags=["Users"]
)

# Add more routers here as you build them:
# app.include_router(admin_router, prefix=f"/api/{config.API_VERSION}", tags=["Admin"])


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": config.APP_NAME,
        "version": "1.0.0",
        "environment": config.ENVIRONMENT,
        "docs_url": "/docs" if config.DEBUG else None,
        "api_version": config.API_VERSION
    }
