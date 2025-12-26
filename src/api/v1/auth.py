"""
Authentication API endpoints.

This module provides endpoints for user registration, login, token refresh,
and other authentication-related operations.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    UserResponse,
    RefreshTokenRequest,
    LogoutRequest,
    MessageResponse
)
from src.services.auth_service import AuthService
from src.repositories.auth_repository import AuthRepository
from src.core.logging import get_logger
from src.core.dependencies import CurrentUser
from src.core.rate_limit_config import limiter

logger = get_logger(__name__)

router = APIRouter(prefix="/auth")


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """
    Dependency to get AuthService instance.

    Args:
        db: Database session

    Returns:
        AuthService instance
    """
    auth_repository = AuthRepository(db)
    return AuthService(auth_repository)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute;20/hour;50/day")
async def register(
    user_data: UserRegister,
    request: Request,
    service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user.

    Rate Limits: 5 requests/minute, 20 requests/hour, 50 requests/day

    Creates a new user account and returns access and refresh tokens.

    Args:
        user_data: User registration data (username, email, password)
        request: FastAPI request object for extracting metadata
        service: AuthService dependency

    Returns:
        TokenResponse with access_token and refresh_token

    Raises:
        HTTPException 400: If username or email already exists
        HTTPException 500: If registration fails
    """
    try:
        # Extract request metadata
        user_agent = request.headers.get("user-agent")
        ip_address = request.client.host if request.client else None

        logger.info(
            "registration_request",
            username=user_data.username,
            email=user_data.email,
            ip_address=ip_address
        )

        # Register user
        tokens = await service.register_user(
            user_data=user_data,
            user_agent=user_agent,
            ip_address=ip_address
        )

        logger.info(
            "registration_successful",
            username=user_data.username
        )

        return tokens

    except ValueError as e:
        logger.warning(
            "registration_validation_error",
            username=user_data.username,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "registration_failed",
            username=user_data.username,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register user"
        )


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute;50/hour;200/day")
async def login(
    login_data: UserLogin,
    request: Request,
    service: AuthService = Depends(get_auth_service)
):
    """
    Login a user.

    Rate Limits: 10 requests/minute, 50 requests/hour, 200 requests/day

    Authenticates a user with username and password, returning access and refresh tokens.

    Args:
        login_data: User login credentials (username, password)
        request: FastAPI request object for extracting metadata
        service: AuthService dependency

    Returns:
        TokenResponse with access_token and refresh_token

    Raises:
        HTTPException 401: If credentials are invalid or user is inactive
        HTTPException 500: If login fails
    """
    try:
        # Extract request metadata
        user_agent = request.headers.get("user-agent")
        ip_address = request.client.host if request.client else None

        logger.info(
            "login_request",
            username=login_data.username,
            ip_address=ip_address
        )

        # Login user
        tokens = await service.login_user(
            login_data=login_data,
            user_agent=user_agent,
            ip_address=ip_address
        )

        logger.info(
            "login_endpoint_successful",
            username=login_data.username
        )

        return tokens

    except ValueError as e:
        logger.warning(
            "login_authentication_error",
            username=login_data.username,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "login_endpoint_failed",
            username=login_data.username,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to login"
        )


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute;20/hour;100/day")
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    request: Request,
    service: AuthService = Depends(get_auth_service)
):
    """
    Refresh access token.

    Rate Limits: 5 requests/minute, 20 requests/hour, 100 requests/day (STRICT)

    Validates the refresh token and returns a new access token.
    Optionally rotates the refresh token for enhanced security.

    Args:
        refresh_data: Refresh token request with refresh_token
        request: FastAPI request object for extracting metadata
        service: AuthService dependency

    Returns:
        TokenResponse with new access_token and refresh_token

    Raises:
        HTTPException 401: If refresh token is invalid, expired, or revoked
        HTTPException 500: If token refresh fails
    """
    try:
        # Extract request metadata
        user_agent = request.headers.get("user-agent")
        ip_address = request.client.host if request.client else None

        logger.info(
            "refresh_token_request",
            ip_address=ip_address
        )

        # Refresh access token
        tokens = await service.refresh_access_token(
            refresh_token=refresh_data.refresh_token,
            user_agent=user_agent,
            ip_address=ip_address,
            rotate_refresh_token=True  # Enable refresh token rotation
        )

        logger.info(
            "refresh_token_endpoint_successful",
            ip_address=ip_address
        )

        return tokens

    except ValueError as e:
        logger.warning(
            "refresh_token_validation_error",
            error=str(e),
            ip_address=request.client.host if request.client else None
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "refresh_token_endpoint_failed",
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )


@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
@limiter.limit("20/minute;100/hour")
async def logout(
    logout_data: LogoutRequest,
    current_user: CurrentUser,
    request: Request,
    service: AuthService = Depends(get_auth_service)
):
    """
    Logout a user.

    Rate Limits: 20 requests/minute, 100 requests/hour

    Revokes the refresh token to prevent further use.
    Requires authentication via access token.

    Args:
        logout_data: Logout request with refresh_token
        current_user: Current authenticated user from JWT token
        service: AuthService dependency

    Returns:
        MessageResponse with success message

    Raises:
        HTTPException 400: If refresh token is invalid or doesn't belong to user
        HTTPException 401: If access token is invalid
        HTTPException 500: If logout fails

    Headers:
        Authorization: Bearer <access_token>
    """
    try:
        logger.info(
            "logout_request",
            user_id=current_user.id,
            username=current_user.username
        )

        # Logout user by revoking refresh token
        await service.logout_user(
            refresh_token=logout_data.refresh_token,
            user_id=current_user.id
        )

        logger.info(
            "logout_endpoint_successful",
            user_id=current_user.id,
            username=current_user.username
        )

        return MessageResponse(
            message="Successfully logged out"
        )

    except ValueError as e:
        logger.warning(
            "logout_validation_error",
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "logout_endpoint_failed",
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to logout"
        )


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit("60/minute;500/hour")
async def get_current_user_info(
    current_user: CurrentUser,
    request: Request,
    service: AuthService = Depends(get_auth_service)
):
    """
    Get current authenticated user information.

    Rate Limits: 60 requests/minute, 500 requests/hour

    Returns the profile information of the currently authenticated user
    based on the JWT token in the Authorization header.

    Args:
        current_user: Current authenticated user from JWT token
        service: AuthService dependency

    Returns:
        UserResponse with user profile information

    Raises:
        HTTPException 401: If token is invalid or expired
        HTTPException 403: If user account is inactive

    Headers:
        Authorization: Bearer <access_token>
    """
    logger.info(
        "get_current_user_request",
        user_id=current_user.id,
        username=current_user.username
    )

    return service.get_user_response(current_user)
