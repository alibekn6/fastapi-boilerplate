"""
Enhanced security utilities for password hashing, token generation, and input sanitization.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Any
import secrets
import re
import html

import bcrypt
import jwt

from src.core.config import Config
from src.core.logging import get_logger

logger = get_logger(__name__)

# Load configuration
config = Config()


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    # Convert password to bytes and hash it
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string for storage
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception as e:
        logger.error("password_verification_failed", error=str(e))
        return False


def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Dictionary containing claims to encode in the token
        expires_delta: Optional custom expiration delta

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access"
    })

    logger.debug("creating_access_token", user_id=data.get("sub"), expires_at=expire.isoformat())

    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt


def generate_refresh_token() -> str:
    """
    Generate a cryptographically secure random refresh token.

    Returns:
        URL-safe random token string (256 bits of entropy)
    """
    return secrets.token_urlsafe(32)


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        jwt.ExpiredSignatureError: If token has expired
        jwt.InvalidTokenError: If token is invalid
    """
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[config.ALGORITHM])

        if payload.get("type") != "access":
            logger.warning("invalid_token_type", token_type=payload.get("type"))
            raise jwt.InvalidTokenError("Invalid token type")

        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("token_expired")
        raise
    except jwt.InvalidTokenError as e:
        logger.warning("invalid_token", error=str(e))
        raise


def generate_password_reset_token() -> str:
    """
    Generate a secure token for password reset.

    Returns:
        URL-safe random token string (256 bits of entropy)
    """
    return secrets.token_urlsafe(32)


def generate_email_verification_token() -> str:
    """
    Generate a secure token for email verification.

    Returns:
        URL-safe random token string (256 bits of entropy)
    """
    return secrets.token_urlsafe(32)


def generate_csrf_token() -> str:
    """
    Generate a CSRF token for form protection.

    Returns:
        URL-safe random token string (256 bits of entropy)
    """
    return secrets.token_urlsafe(32)


def sanitize_html(text: str) -> str:
    """
    Sanitize HTML content to prevent XSS attacks.

    Args:
        text: Input text that may contain HTML

    Returns:
        Sanitized text with HTML entities escaped
    """
    if not text:
        return text
    return html.escape(text)


def sanitize_sql(text: str) -> str:
    """
    Basic SQL injection prevention for text inputs.

    Note: This is a defense-in-depth measure. Always use parameterized queries.

    Args:
        text: Input text

    Returns:
        Sanitized text
    """
    if not text:
        return text

    # Remove SQL comment indicators
    text = text.replace("--", "").replace("/*", "").replace("*/", "")

    # Remove common SQL keywords used in injection attacks
    dangerous_patterns = [
        r"\bDROP\b", r"\bDELETE\b", r"\bTRUNCATE\b",
        r"\bEXEC\b", r"\bEXECUTE\b",
        r"\bUNION\b.*\bSELECT\b",
        r"\bINSERT\b.*\bINTO\b",
        r"\bUPDATE\b.*\bSET\b"
    ]

    for pattern in dangerous_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return text.strip()


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Validate password against security requirements.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    if len(password) < config.PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {config.PASSWORD_MIN_LENGTH} characters long")

    if config.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")

    if config.PASSWORD_REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")

    if config.PASSWORD_REQUIRE_DIGITS and not re.search(r"\d", password):
        errors.append("Password must contain at least one digit")

    if config.PASSWORD_REQUIRE_SPECIAL and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("Password must contain at least one special character")

    # Check for common weak passwords
    common_passwords = [
        "password", "123456", "12345678", "qwerty", "abc123",
        "password123", "admin", "letmein", "welcome"
    ]
    if password.lower() in common_passwords:
        errors.append("Password is too common")

    return len(errors) == 0, errors


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data for logging (e.g., email addresses, tokens).

    Args:
        data: Sensitive data to mask
        visible_chars: Number of characters to leave visible

    Returns:
        Masked string
    """
    if not data or len(data) <= visible_chars:
        return "*" * len(data) if data else ""

    return data[:visible_chars] + "*" * (len(data) - visible_chars)
