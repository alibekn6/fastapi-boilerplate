"""
Enhanced configuration with comprehensive security and feature settings.
"""

from typing import List, Optional
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings

load_dotenv()


class Config(BaseSettings):
    """Application configuration with validation and defaults."""

    # Application Settings
    APP_NAME: str = "Testing"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    API_VERSION: str = "v1"

    # Database Settings
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DB_HOST: str
    DB_PORT: int = 5432

    # JWT Configuration
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Security Settings
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "GET,POST,PUT,DELETE,PATCH,OPTIONS"
    CORS_ALLOW_HEADERS: str = "*"

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    RATE_LIMIT_PER_DAY: int = 10000

    # Password Requirements
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGITS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = False

    # Session Management
    MAX_SESSIONS_PER_USER: int = 5
    SESSION_ABSOLUTE_TIMEOUT_DAYS: int = 30

    # Email Configuration (Optional)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_FROM_NAME: Optional[str] = "Testing App"
    EMAIL_VERIFICATION_ENABLED: bool = False

    # Redis Configuration (for Celery, rate limiting)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # Celery Configuration
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    # File Upload Settings
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_UPLOAD_EXTENSIONS: str = "jpg,jpeg,png,pdf,doc,docx"
    UPLOAD_DIR: str = "/tmp/uploads"

    # Admin Settings
    ADMIN_REGISTRATION_ENABLED: bool = False
    REQUIRE_REGISTRATION_TOKEN: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or console

    # Monitoring
    METRICS_ENABLED: bool = True
    SENTRY_DSN: Optional[str] = None

    @property
    def db_url(self) -> str:
        """Construct database URL."""
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def celery_broker(self) -> str:
        """Get Celery broker URL."""
        return self.CELERY_BROKER_URL or self.redis_url

    @property
    def celery_backend(self) -> str:
        """Get Celery result backend URL."""
        return self.CELERY_RESULT_BACKEND or self.redis_url

    @property
    def allowed_extensions(self) -> List[str]:
        """Parse allowed file extensions into a list."""
        return [ext.strip().lower() for ext in self.ALLOWED_UPLOAD_EXTENSIONS.split(",")]

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment setting."""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}")
        return v

    @field_validator("LOG_FORMAT")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format setting."""
        allowed = ["json", "console"]
        if v not in allowed:
            raise ValueError(f"LOG_FORMAT must be one of {allowed}")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True
