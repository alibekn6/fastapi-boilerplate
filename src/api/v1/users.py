"""
User management API endpoints.

This module provides endpoints for user profile management including
getting, updating, and deleting user accounts.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.schemas.auth import UpdateUserRequest, UserResponse, MessageResponse
from src.services.user_service import UserService
from src.repositories.auth_repository import AuthRepository
from src.core.logging import get_logger
from src.core.dependencies import CurrentUser
from src.core.rate_limit_config import limiter

logger = get_logger(__name__)

router = APIRouter(prefix="/users")


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    """
    Dependency to get UserService instance.

    Args:
        db: Database session

    Returns:
        UserService instance
    """
    auth_repository = AuthRepository(db)
    return UserService(auth_repository)


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit("100/minute;1000/hour")
async def get_current_user_profile(
    current_user: CurrentUser,
    request: Request,
    service: UserService = Depends(get_user_service)
):
    """
    Get current user profile.

    Rate Limits: 100 requests/minute, 1000 requests/hour

    Returns the profile information of the currently authenticated user.

    Args:
        current_user: Current authenticated user from JWT token
        service: UserService dependency

    Returns:
        UserResponse with user profile information

    Raises:
        HTTPException 401: If token is invalid or expired
        HTTPException 403: If user account is inactive

    Headers:
        Authorization: Bearer <access_token>
    """
    logger.info(
        "get_user_profile_request",
        user_id=current_user.id,
        username=current_user.username
    )

    return service.get_user_response(current_user)


@router.put("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute;50/hour")
async def update_current_user_profile(
    update_data: UpdateUserRequest,
    current_user: CurrentUser,
    request: Request,
    service: UserService = Depends(get_user_service)
):
    """
    Update current user profile.

    Rate Limits: 10 requests/minute, 50 requests/hour

    Updates the profile information of the currently authenticated user.
    Can update username and/or email. At least one field must be provided.

    Args:
        update_data: Update data containing optional username and email
        current_user: Current authenticated user from JWT token
        service: UserService dependency

    Returns:
        UserResponse with updated user profile information

    Raises:
        HTTPException 400: If no fields provided or username/email already exists
        HTTPException 401: If token is invalid or expired
        HTTPException 403: If user account is inactive
        HTTPException 500: If update fails

    Headers:
        Authorization: Bearer <access_token>
    """
    try:
        logger.info(
            "update_user_profile_request",
            user_id=current_user.id,
            username=current_user.username,
            new_username=update_data.username,
            new_email=update_data.email
        )

        # Update user profile
        updated_user = await service.update_user_profile(
            user_id=current_user.id,
            update_data=update_data
        )

        logger.info(
            "update_user_profile_successful",
            user_id=current_user.id,
            username=updated_user.username
        )

        return updated_user

    except ValueError as e:
        logger.warning(
            "update_user_profile_validation_error",
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "update_user_profile_failed",
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )


@router.delete("/me", response_model=MessageResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute;10/hour")
async def delete_current_user_account(
    current_user: CurrentUser,
    request: Request,
    service: UserService = Depends(get_user_service)
):
    """
    Delete current user account.

    Rate Limits: 5 requests/minute, 10 requests/hour (STRICT - destructive action)

    Performs a soft delete by deactivating the user account.
    The user will no longer be able to login or access protected resources.

    Args:
        current_user: Current authenticated user from JWT token
        service: UserService dependency

    Returns:
        MessageResponse with success message

    Raises:
        HTTPException 400: If user not found
        HTTPException 401: If token is invalid or expired
        HTTPException 403: If user account is inactive
        HTTPException 500: If deletion fails

    Headers:
        Authorization: Bearer <access_token>
    """
    try:
        logger.info(
            "delete_user_account_request",
            user_id=current_user.id,
            username=current_user.username
        )

        # Delete (deactivate) user account
        await service.delete_user_account(current_user.id)

        logger.info(
            "delete_user_account_successful",
            user_id=current_user.id,
            username=current_user.username
        )

        return MessageResponse(
            message="User account successfully deleted",
            details={
                "user_id": current_user.id,
                "username": current_user.username
            }
        )

    except ValueError as e:
        logger.warning(
            "delete_user_account_validation_error",
            user_id=current_user.id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "delete_user_account_failed",
            user_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user account"
        )
