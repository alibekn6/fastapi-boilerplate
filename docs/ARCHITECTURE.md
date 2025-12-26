# Production-Ready FastAPI Backend Architecture

## Overview
This document describes the comprehensive production-ready architecture for the FastAPI application with JWT authentication, refresh tokens, rate limiting, security headers, and more.

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Security Features](#security-features)
3. [Authentication Flow](#authentication-flow)
4. [Middleware Stack](#middleware-stack)
5. [Dependency Injection](#dependency-injection)
6. [Database Models](#database-models)
7. [API Endpoints](#api-endpoints)
8. [Implementation Priorities](#implementation-priorities)

---

## Architecture Overview

### Layered Architecture Pattern
```
┌─────────────────────────────────────────┐
│         API Layer (FastAPI)             │
│  - HTTP Endpoints                       │
│  - Request/Response Handling            │
│  - Input Validation (Pydantic)          │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│         Service Layer                   │
│  - Business Logic                       │
│  - Orchestration                        │
│  - Domain Model Transformation          │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│      Repository Layer                   │
│  - Database Queries                     │
│  - Data Access                          │
│  - SQLAlchemy Operations                │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│       Database Layer (PostgreSQL)       │
│  - Connection Management                │
│  - Transaction Handling                 │
│  - Schema & Migrations (Alembic)        │
└─────────────────────────────────────────┘
```

---

## Security Features

### 1. Authentication & Authorization
- **JWT Access Tokens**: Short-lived (30 minutes) stateless tokens
- **Refresh Tokens**: Long-lived (7 days) database-backed tokens with rotation
- **Password Hashing**: bcrypt with automatic salt generation
- **Password Requirements**: Configurable complexity (uppercase, lowercase, digits, special chars)

### 2. Rate Limiting
- **Per-Minute Limit**: 60 requests/minute (configurable)
- **Per-Hour Limit**: 1,000 requests/hour (configurable)
- **Per-Day Limit**: 10,000 requests/day (configurable)
- **Sliding Window Algorithm**: Accurate rate limiting
- **Production**: Use Redis-backed implementation for horizontal scaling

### 3. Security Headers
- **X-Frame-Options**: DENY (clickjacking protection)
- **X-Content-Type-Options**: nosniff (MIME sniffing protection)
- **X-XSS-Protection**: 1; mode=block (XSS protection)
- **Content-Security-Policy**: Restrictive CSP (production only)
- **Strict-Transport-Security**: HSTS with preload (production only)
- **Referrer-Policy**: strict-origin-when-cross-origin
- **Permissions-Policy**: Disable dangerous browser features

### 4. Input Validation & Sanitization
- **Pydantic Validation**: All request inputs validated
- **HTML Sanitization**: XSS prevention via HTML escaping
- **SQL Injection Prevention**: Parameterized queries + defense-in-depth
- **CSRF Protection**: Token-based (for cookie-based sessions)

### 5. CORS Configuration
- **Configurable Origins**: Whitelist-based origin control
- **Credentials Support**: Allow credentials for authenticated requests
- **Method Restrictions**: Control allowed HTTP methods

---

## Authentication Flow

### Registration Flow
```
┌──────────┐         ┌──────────┐         ┌──────────┐         ┌──────────┐
│  Client  │         │   API    │         │ Service  │         │   DB     │
└────┬─────┘         └────┬─────┘         └────┬─────┘         └────┬─────┘
     │                    │                    │                    │
     │  POST /auth/register                    │                    │
     ├───────────────────►│                    │                    │
     │                    │  validate_password │                    │
     │                    ├───────────────────►│                    │
     │                    │                    │  check_existing    │
     │                    │                    ├───────────────────►│
     │                    │                    │◄───────────────────┤
     │                    │                    │  hash_password     │
     │                    │                    │  create_user       │
     │                    │                    ├───────────────────►│
     │                    │                    │◄───────────────────┤
     │                    │                    │  create_tokens     │
     │                    │                    │  store_refresh_token
     │                    │                    ├───────────────────►│
     │                    │◄───────────────────┤                    │
     │◄───────────────────┤                    │                    │
     │  {access, refresh} │                    │                    │
```

### Login Flow
```
┌──────────┐         ┌──────────┐         ┌──────────┐         ┌──────────┐
│  Client  │         │   API    │         │ Service  │         │   DB     │
└────┬─────┘         └────┬─────┘         └────┬─────┘         └────┬─────┘
     │                    │                    │                    │
     │  POST /auth/login  │                    │                    │
     ├───────────────────►│                    │                    │
     │                    │  authenticate      │                    │
     │                    ├───────────────────►│                    │
     │                    │                    │  get_user          │
     │                    │                    ├───────────────────►│
     │                    │                    │◄───────────────────┤
     │                    │                    │  verify_password   │
     │                    │                    │  check_active      │
     │                    │                    │  create_tokens     │
     │                    │                    │  store_refresh_token
     │                    │                    ├───────────────────►│
     │                    │◄───────────────────┤                    │
     │◄───────────────────┤                    │                    │
     │  {access, refresh} │                    │                    │
```

### Token Refresh Flow
```
┌──────────┐         ┌──────────┐         ┌──────────┐         ┌──────────┐
│  Client  │         │   API    │         │ Service  │         │   DB     │
└────┬─────┘         └────┬─────┘         └────┬─────┘         └────┬─────┘
     │                    │                    │                    │
     │  POST /auth/refresh                     │                    │
     ├───────────────────►│                    │                    │
     │                    │  validate_refresh  │                    │
     │                    ├───────────────────►│                    │
     │                    │                    │  verify_token      │
     │                    │                    ├───────────────────►│
     │                    │                    │◄───────────────────┤
     │                    │                    │  revoke_old_token  │
     │                    │                    ├───────────────────►│
     │                    │                    │  create_new_tokens │
     │                    │                    │  store_new_refresh │
     │                    │                    ├───────────────────►│
     │                    │◄───────────────────┤                    │
     │◄───────────────────┤                    │                    │
     │  {access, refresh} │                    │                    │
```

---

## Middleware Stack

Middleware execution order (outside-in):
```
1. ErrorHandlerMiddleware       # Global exception handling
2. SecurityHeadersMiddleware    # Security headers (HSTS, CSP, etc.)
3. CORSMiddleware               # CORS handling
4. RateLimitMiddleware          # Rate limiting
5. CorrelationIdMiddleware      # Request tracking
6. LoggingMiddleware            # Request/response logging
7. Application Routes           # Your endpoints
```

### Configuration in main.py
```python
from fastapi.middleware.cors import CORSMiddleware
from src.api.middlewares.error_handler import ErrorHandlerMiddleware
from src.api.middlewares.security_headers import SecurityHeadersMiddleware
from src.api.middlewares.rate_limit import RateLimitMiddleware

app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins_list,
    allow_credentials=config.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.add_middleware(RateLimitMiddleware)
```

---

## Dependency Injection

### Database Session
```python
# src/db/database.py
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Service Dependencies
```python
# src/api/v1/auth.py
def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    auth_repository = AuthRepository(db)
    return AuthService(auth_repository)
```

### Authentication Dependencies
```python
# src/core/dependencies.py
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: AsyncSession = Depends(get_db)
) -> User:
    token = credentials.credentials
    payload = decode_access_token(token)
    user = await auth_repository.get_user_by_id(int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401)
    return user

# Type alias for cleaner endpoint signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
```

### Admin Authorization
```python
# src/core/dependencies.py
async def get_current_admin_user(
    current_user: CurrentUser
) -> User:
    if not current_user.is_admin:
        raise AuthorizationError("Admin access required")
    return current_user

CurrentAdmin = Annotated[User, Depends(get_current_admin_user)]
```

---

## Database Models

### Users Table
```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]

    # Relationships
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(back_populates="user")
```

### Refresh Tokens Table
```python
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime]
    created_at: Mapped[datetime]
    is_revoked: Mapped[bool] = mapped_column(default=False)
    user_agent: Mapped[str | None] = mapped_column(String(500))
    ip_address: Mapped[str | None] = mapped_column(String(45))

    # Relationships
    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
```

### Password Reset Tokens Table
```python
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    expires_at: Mapped[datetime]
    created_at: Mapped[datetime]
    is_used: Mapped[bool] = mapped_column(default=False)
```

---

## API Endpoints

### Authentication Endpoints

#### POST /api/v1/auth/register
Register a new user account.
```json
Request:
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "SecurePass123"
}

Response (201):
{
  "access_token": "eyJ...",
  "refresh_token": "abc123...",
  "token_type": "bearer"
}
```

#### POST /api/v1/auth/login
Authenticate and get tokens.
```json
Request:
{
  "username": "johndoe",
  "password": "SecurePass123"
}

Response (200):
{
  "access_token": "eyJ...",
  "refresh_token": "abc123...",
  "token_type": "bearer"
}
```

#### POST /api/v1/auth/refresh
Refresh access token using refresh token.
```json
Request:
{
  "refresh_token": "abc123..."
}

Response (200):
{
  "access_token": "eyJ...",
  "refresh_token": "xyz789...",
  "token_type": "bearer"
}
```

#### POST /api/v1/auth/logout
Revoke current refresh token.
```json
Request:
{
  "refresh_token": "abc123..."
}

Response (200):
{
  "message": "Successfully logged out"
}
```

#### POST /api/v1/auth/logout-all
Revoke all refresh tokens for current user.
```json
Headers:
Authorization: Bearer <access_token>

Response (200):
{
  "message": "All sessions terminated",
  "revoked_count": 3
}
```

#### GET /api/v1/auth/me
Get current user information.
```json
Headers:
Authorization: Bearer <access_token>

Response (200):
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "is_active": true,
  "is_admin": false,
  "email_verified": false
}
```

#### POST /api/v1/auth/password-reset-request
Request password reset token.
```json
Request:
{
  "email": "john@example.com"
}

Response (200):
{
  "message": "Password reset email sent"
}
```

#### POST /api/v1/auth/password-reset-confirm
Reset password using token.
```json
Request:
{
  "token": "reset_token_here",
  "new_password": "NewSecurePass123"
}

Response (200):
{
  "message": "Password reset successful"
}
```

### Session Management Endpoints

#### GET /api/v1/sessions
Get all active sessions for current user.
```json
Headers:
Authorization: Bearer <access_token>

Response (200):
{
  "items": [
    {
      "id": 1,
      "user_agent": "Mozilla/5.0...",
      "ip_address": "192.168.1.1",
      "created_at": "2025-12-25T10:00:00Z",
      "expires_at": "2026-01-01T10:00:00Z",
      "is_current": true
    }
  ],
  "total": 1
}
```

#### DELETE /api/v1/sessions/{session_id}
Revoke a specific session.
```json
Headers:
Authorization: Bearer <access_token>

Response (200):
{
  "message": "Session revoked"
}
```

---

## Implementation Priorities

### Phase 1: Core Security (Complete)
- [x] Enhanced configuration with security settings
- [x] Custom exception classes
- [x] Global error handler middleware
- [x] Security headers middleware
- [x] Rate limiting (in-memory)
- [x] Enhanced security utilities (sanitization, password validation)
- [x] Pagination helpers

### Phase 2: Extended Authentication (In Progress)
- [ ] Enhanced auth schemas (refresh, logout, password reset)
- [ ] Auth repository enhancements (token management)
- [ ] Auth service enhancements (refresh, logout, password reset)
- [ ] Additional auth endpoints (refresh, logout, password reset)
- [ ] Session management endpoints

### Phase 3: User Management
- [ ] User repository (CRUD operations)
- [ ] User service
- [ ] User endpoints (list, get, update, delete)
- [ ] User profile endpoints

### Phase 4: Admin Features
- [ ] Admin authorization dependency
- [ ] Admin repository
- [ ] Admin service
- [ ] Admin endpoints (user management, metrics)

### Phase 5: Email & Background Tasks
- [ ] Email service (SMTP integration)
- [ ] Celery setup (background tasks)
- [ ] Email verification flow
- [ ] Password reset email templates

### Phase 6: File Upload
- [ ] File upload utilities
- [ ] File validation
- [ ] Storage service
- [ ] File upload endpoints

### Phase 7: Production Readiness
- [ ] Redis-backed rate limiting
- [ ] Prometheus metrics integration
- [ ] Sentry error tracking
- [ ] Database connection pooling optimization
- [ ] Load testing
- [ ] Security audit

---

## Configuration

### Environment Variables (.env)
```bash
# Application
APP_NAME=Testing
DEBUG=false
ENVIRONMENT=production

# Database
DB_USER=postgres
DB_PASSWORD=secure_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=myapp

# JWT
SECRET_KEY=your-256-bit-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Security
CORS_ORIGINS=https://yourfrontend.com
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_PER_HOUR=1000

# Email (Optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@yourapp.com

# Redis (Optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
```

---

## Testing Strategy

### Unit Tests
- Service layer business logic
- Repository layer database operations
- Security utilities (password hashing, token generation)

### Integration Tests
- API endpoints (authentication flow)
- Database operations
- Middleware stack

### Load Tests
- Rate limiting effectiveness
- Concurrent user sessions
- Token refresh under load

---

## Deployment Considerations

### Production Checklist
1. Set `ENVIRONMENT=production` in .env
2. Generate strong SECRET_KEY (256-bit random)
3. Enable HTTPS (required for HSTS)
4. Configure proper CORS origins
5. Set up Redis for rate limiting
6. Configure SMTP for emails
7. Set up database backups
8. Enable monitoring (Sentry, Prometheus)
9. Configure log aggregation
10. Set up CI/CD pipeline

### Docker Deployment
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes Health Checks
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 3
```
