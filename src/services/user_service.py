"""
User service layer for business logic.

This service handles user-related operations including profile management.
"""

from __future__ import annotations

from typing import Optional

from src.core.logging import get_logger
from src.schemas.auth import UpdateUserRequest, UserResponse
from src.repositories.auth_repository import AuthRepository
from src.models.user import User

logger = get_logger(__name__)


class UserService:
    """Service for managing user-related business logic."""

    def __init__(self, auth_repository: AuthRepository):
        self.auth_repository = auth_repository

    async def update_user_profile(
        self,
        user_id: int,
        update_data: UpdateUserRequest
    ) -> UserResponse:
        """
        Update user profile information.

        Args:
            user_id: ID of the user to update
            update_data: Update data containing optional username and email

        Returns:
            UserResponse with updated user information

        Raises:
            ValueError: If username or email already exists, or user not found

        Example:
            >>> service = UserService(auth_repository)
            >>> updated_user = await service.update_user_profile(user_id, update_data)
        """
        logger.info(
            "updating_user_profile",
            user_id=user_id,
            has_username=update_data.username is not None,
            has_email=update_data.email is not None
        )

        # Check if at least one field is being updated
        if update_data.username is None and update_data.email is None:
            logger.warning(
                "no_update_fields_provided",
                user_id=user_id
            )
            raise ValueError("No fields to update")

        # Check if username already exists (if updating username)
        if update_data.username:
            existing_user = await self.auth_repository.get_user_by_username(update_data.username)
            if existing_user and existing_user.id != user_id:
                logger.warning(
                    "update_failed_username_exists",
                    user_id=user_id,
                    username=update_data.username,
                    existing_user_id=existing_user.id
                )
                raise ValueError("Username already exists")

        # Check if email already exists (if updating email)
        if update_data.email:
            existing_email = await self.auth_repository.get_user_by_email(update_data.email)
            if existing_email and existing_email.id != user_id:
                logger.warning(
                    "update_failed_email_exists",
                    user_id=user_id,
                    email=update_data.email,
                    existing_user_id=existing_email.id
                )
                raise ValueError("Email already exists")

        try:
            # Update user
            updated_user = await self.auth_repository.update_user(
                user_id=user_id,
                username=update_data.username,
                email=update_data.email
            )

            if not updated_user:
                logger.error(
                    "update_failed_user_not_found",
                    user_id=user_id
                )
                raise ValueError("User not found")

            logger.info(
                "user_profile_updated_successfully",
                user_id=user_id,
                username=updated_user.username,
                email=updated_user.email
            )

            return self.get_user_response(updated_user)

        except Exception as e:
            logger.error(
                "user_profile_update_failed",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            raise

    async def delete_user_account(self, user_id: int) -> bool:
        """
        Delete (deactivate) a user account.

        Performs a soft delete by setting is_active to False.

        Args:
            user_id: ID of the user to delete

        Returns:
            True if user was deactivated successfully

        Raises:
            ValueError: If user not found

        Example:
            >>> service = UserService(auth_repository)
            >>> await service.delete_user_account(user_id)
        """
        logger.info(
            "deleting_user_account",
            user_id=user_id
        )

        try:
            # Deactivate user
            success = await self.auth_repository.deactivate_user(user_id)

            if not success:
                logger.error(
                    "delete_failed_user_not_found",
                    user_id=user_id
                )
                raise ValueError("User not found")

            logger.info(
                "user_account_deleted_successfully",
                user_id=user_id
            )

            return True

        except Exception as e:
            logger.error(
                "user_account_deletion_failed",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            raise

    def get_user_response(self, user: User) -> UserResponse:
        """
        Convert a User database model to UserResponse.

        Args:
            user: User database model

        Returns:
            UserResponse with user information

        Example:
            >>> service = UserService(auth_repository)
            >>> user_response = service.get_user_response(user)
        """
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            email_verified=user.email_verified,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
