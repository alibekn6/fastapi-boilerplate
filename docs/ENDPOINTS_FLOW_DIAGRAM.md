# API Endpoints Flow Diagram

Visual representation of request flows through the layered architecture.

---

## 1. Refresh Token Flow

```
Client Request
     |
     | POST /api/v1/auth/refresh
     | Body: { "refresh_token": "..." }
     |
     v
┌─────────────────────────────────────────────────────────────────┐
│ API Layer: /src/api/v1/auth.py                                  │
│                                                                  │
│ @router.post("/refresh")                                        │
│ async def refresh_token(refresh_data: RefreshTokenRequest)      │
│   - Validate request schema (Pydantic)                          │
│   - Extract IP address and user agent                           │
│   - Log request                                                 │
└─────────────────────────────────────────────────────────────────┘
     |
     | service.refresh_access_token(token, user_agent, ip)
     v
┌─────────────────────────────────────────────────────────────────┐
│ Service Layer: /src/services/auth_service.py                    │
│                                                                  │
│ async def refresh_access_token(...)                             │
│   - Get refresh token from repository                           │
│   - Validate token not revoked                                  │
│   - Validate token not expired                                  │
│   - Get user from repository                                    │
│   - Validate user is active                                     │
│   - Generate new access token                                   │
│   - If rotate=True:                                             │
│     * Revoke old refresh token                                  │
│     * Generate new refresh token                                │
│     * Store new refresh token                                   │
│   - Log success                                                 │
│   - Return TokenResponse                                        │
└─────────────────────────────────────────────────────────────────┘
     |
     | repository methods
     v
┌─────────────────────────────────────────────────────────────────┐
│ Repository Layer: /src/repositories/auth_repository.py          │
│                                                                  │
│ - get_refresh_token(token) -> RefreshToken                      │
│   SELECT * FROM refresh_tokens WHERE token = ?                  │
│                                                                  │
│ - get_user_by_id(user_id) -> User                               │
│   SELECT * FROM users WHERE id = ?                              │
│                                                                  │
│ - revoke_refresh_token(token) -> bool                           │
│   UPDATE refresh_tokens SET is_revoked = TRUE WHERE token = ?   │
│                                                                  │
│ - create_refresh_token(...) -> RefreshToken                     │
│   INSERT INTO refresh_tokens (...)                              │
└─────────────────────────────────────────────────────────────────┘
     |
     | Database operations via SQLAlchemy
     v
┌─────────────────────────────────────────────────────────────────┐
│ Database Layer: PostgreSQL                                      │
│                                                                  │
│ Tables:                                                          │
│ - users (id, username, email, hashed_password, is_active, ...)  │
│ - refresh_tokens (id, token, user_id, expires_at, ...)          │
└─────────────────────────────────────────────────────────────────┘
     |
     | Response
     v
Client Response
{
  "access_token": "eyJhbGc...",
  "refresh_token": "new_token...",
  "token_type": "bearer"
}
```

---

## 2. Logout Flow

```
Client Request
     |
     | POST /api/v1/auth/logout
     | Headers: Authorization: Bearer <access_token>
     | Body: { "refresh_token": "..." }
     |
     v
┌─────────────────────────────────────────────────────────────────┐
│ Dependencies: /src/core/dependencies.py                         │
│                                                                  │
│ async def get_current_user(credentials, db)                     │
│   - Extract Bearer token from Authorization header              │
│   - Decode and validate JWT token                               │
│   - Extract user_id from token payload                          │
│   - Fetch user from database                                    │
│   - Validate user is active                                     │
│   - Return User object                                          │
└─────────────────────────────────────────────────────────────────┘
     |
     | CurrentUser dependency injected
     v
┌─────────────────────────────────────────────────────────────────┐
│ API Layer: /src/api/v1/auth.py                                  │
│                                                                  │
│ @router.post("/logout")                                         │
│ async def logout(logout_data, current_user: CurrentUser)        │
│   - Validate request schema                                     │
│   - Log logout request                                          │
└─────────────────────────────────────────────────────────────────┘
     |
     | service.logout_user(token, user_id)
     v
┌─────────────────────────────────────────────────────────────────┐
│ Service Layer: /src/services/auth_service.py                    │
│                                                                  │
│ async def logout_user(refresh_token, user_id)                   │
│   - Get refresh token from repository                           │
│   - Validate token exists                                       │
│   - Validate token belongs to user (user_id match)              │
│   - Check if already revoked (idempotent)                       │
│   - Revoke refresh token via repository                         │
│   - Log success                                                 │
│   - Return True                                                 │
└─────────────────────────────────────────────────────────────────┘
     |
     | repository.revoke_refresh_token(token)
     v
┌─────────────────────────────────────────────────────────────────┐
│ Repository Layer: /src/repositories/auth_repository.py          │
│                                                                  │
│ - get_refresh_token(token)                                      │
│   SELECT * FROM refresh_tokens WHERE token = ?                  │
│                                                                  │
│ - revoke_refresh_token(token)                                   │
│   UPDATE refresh_tokens SET is_revoked = TRUE WHERE token = ?   │
└─────────────────────────────────────────────────────────────────┘
     |
     v
Client Response
{
  "message": "Successfully logged out"
}
```

---

## 3. Update User Profile Flow

```
Client Request
     |
     | PUT /api/v1/users/me
     | Headers: Authorization: Bearer <access_token>
     | Body: { "username": "new_name", "email": "new@email.com" }
     |
     v
┌─────────────────────────────────────────────────────────────────┐
│ Dependencies: get_current_user()                                │
│   - Validates access token                                      │
│   - Returns authenticated User object                           │
└─────────────────────────────────────────────────────────────────┘
     |
     v
┌─────────────────────────────────────────────────────────────────┐
│ API Layer: /src/api/v1/users.py                                 │
│                                                                  │
│ @router.put("/me")                                              │
│ async def update_current_user_profile(update_data, current_user)│
│   - Validate UpdateUserRequest schema                           │
│   - Log update request                                          │
└─────────────────────────────────────────────────────────────────┘
     |
     | service.update_user_profile(user_id, update_data)
     v
┌─────────────────────────────────────────────────────────────────┐
│ Service Layer: /src/services/user_service.py                    │
│                                                                  │
│ async def update_user_profile(user_id, update_data)             │
│   - Validate at least one field provided                        │
│   - If updating username:                                       │
│     * Check username doesn't exist (different user)             │
│   - If updating email:                                          │
│     * Check email doesn't exist (different user)                │
│   - Update user via repository                                  │
│   - Log success                                                 │
│   - Return UserResponse                                         │
└─────────────────────────────────────────────────────────────────┘
     |
     | repository methods
     v
┌─────────────────────────────────────────────────────────────────┐
│ Repository Layer: /src/repositories/auth_repository.py          │
│                                                                  │
│ - get_user_by_username(username)                                │
│   SELECT * FROM users WHERE username = ?                        │
│                                                                  │
│ - get_user_by_email(email)                                      │
│   SELECT * FROM users WHERE email = ?                           │
│                                                                  │
│ - update_user(user_id, username, email)                         │
│   UPDATE users SET username = ?, email = ? WHERE id = ?         │
│   (only updates provided fields)                                │
└─────────────────────────────────────────────────────────────────┘
     |
     v
Client Response
{
  "id": 1,
  "username": "new_name",
  "email": "new@email.com",
  "is_active": true,
  "is_admin": false,
  "email_verified": false,
  "created_at": "2025-12-26T10:00:00Z",
  "updated_at": "2025-12-26T10:30:00Z"
}
```

---

## 4. Delete User Account Flow

```
Client Request
     |
     | DELETE /api/v1/users/me
     | Headers: Authorization: Bearer <access_token>
     |
     v
┌─────────────────────────────────────────────────────────────────┐
│ Dependencies: get_current_user()                                │
│   - Returns authenticated User object                           │
└─────────────────────────────────────────────────────────────────┘
     |
     v
┌─────────────────────────────────────────────────────────────────┐
│ API Layer: /src/api/v1/users.py                                 │
│                                                                  │
│ @router.delete("/me")                                           │
│ async def delete_current_user_account(current_user)             │
│   - Log delete request                                          │
└─────────────────────────────────────────────────────────────────┘
     |
     | service.delete_user_account(user_id)
     v
┌─────────────────────────────────────────────────────────────────┐
│ Service Layer: /src/services/user_service.py                    │
│                                                                  │
│ async def delete_user_account(user_id)                          │
│   - Deactivate user via repository (soft delete)                │
│   - Validate user was found                                     │
│   - Log success                                                 │
│   - Return True                                                 │
└─────────────────────────────────────────────────────────────────┘
     |
     | repository.deactivate_user(user_id)
     v
┌─────────────────────────────────────────────────────────────────┐
│ Repository Layer: /src/repositories/auth_repository.py          │
│                                                                  │
│ - deactivate_user(user_id)                                      │
│   UPDATE users SET is_active = FALSE WHERE id = ?               │
└─────────────────────────────────────────────────────────────────┘
     |
     v
Client Response
{
  "message": "User account successfully deleted",
  "details": {
    "user_id": 1,
    "username": "john_doe"
  }
}
```

---

## 5. Admin-Only Endpoint Flow

```
Client Request
     |
     | DELETE /api/v1/admin/users/123
     | Headers: Authorization: Bearer <access_token>
     |
     v
┌─────────────────────────────────────────────────────────────────┐
│ Dependencies Chain:                                             │
│                                                                  │
│ 1. get_current_user(credentials, db)                            │
│    - Validates JWT token                                        │
│    - Fetches user from database                                 │
│    - Validates user is active                                   │
│    - Returns User object                                        │
│                                                                  │
│ 2. require_admin(current_user: User)                            │
│    - Checks current_user.is_admin == True                       │
│    - If False: raises HTTPException(403)                        │
│    - If True: returns User object                               │
│                                                                  │
│ Type Alias: CurrentAdmin = Annotated[User, Depends(...)]        │
└─────────────────────────────────────────────────────────────────┘
     |
     | Admin user validated
     v
┌─────────────────────────────────────────────────────────────────┐
│ API Layer: Admin endpoint                                       │
│                                                                  │
│ @router.delete("/admin/users/{user_id}")                        │
│ async def delete_user(admin: CurrentAdmin, user_id: int)        │
│   - Admin privileges confirmed by dependency                    │
│   - Proceed with admin action                                   │
└─────────────────────────────────────────────────────────────────┘
     |
     v
Response (admin action performed)

---

If user is not admin:
┌─────────────────────────────────────────────────────────────────┐
│ Dependencies: require_admin()                                   │
│                                                                  │
│ Raises HTTPException:                                           │
│   status_code: 403 Forbidden                                    │
│   detail: "Admin privileges required"                           │
└─────────────────────────────────────────────────────────────────┘
     |
     v
Client Response
{
  "detail": "Admin privileges required"
}
Status: 403 Forbidden
```

---

## Error Handling Flow

All endpoints follow this error handling pattern:

```
┌─────────────────────────────────────────────────────────────────┐
│ API Layer: Exception Handling                                   │
│                                                                  │
│ try:                                                            │
│     result = await service.method(...)                          │
│     return result                                               │
│                                                                  │
│ except ValueError as e:                                         │
│     # Business logic errors (400 or 401)                        │
│     logger.warning("operation_failed", error=str(e))            │
│     raise HTTPException(status_code=400/401, detail=str(e))     │
│                                                                  │
│ except Exception as e:                                          │
│     # Unexpected errors (500)                                   │
│     logger.error("operation_failed", error=str(e), exc_info=True)│
│     raise HTTPException(status_code=500, detail="...")          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Dependency Injection Flow

FastAPI's dependency injection system automatically handles the dependency chain:

```
Endpoint Parameter: admin: CurrentAdmin
     |
     | Resolves to: Annotated[User, Depends(require_admin)]
     |
     v
Call: require_admin(current_user: User = Depends(get_current_user))
     |
     | Requires: current_user parameter
     |
     v
Call: get_current_user(credentials: HTTPBearer, db: AsyncSession)
     |
     | Requires: credentials and db
     |
     v
Call: security (HTTPBearer) - extracts Authorization header
Call: get_db() - provides database session
     |
     v
Returns: User object (if valid and admin)
```

---

## Layer Responsibilities Summary

```
┌─────────────────────────────────────────────────────────────────┐
│ API Layer (FastAPI Routers)                                     │
│ - HTTP protocol handling                                        │
│ - Request/response serialization                                │
│ - HTTP status code mapping                                      │
│ - Dependency injection                                          │
│ - Input validation (Pydantic)                                   │
└─────────────────────────────────────────────────────────────────┘
                           |
                           v
┌─────────────────────────────────────────────────────────────────┐
│ Service Layer (Business Logic)                                  │
│ - Business rule enforcement                                     │
│ - Data validation and transformation                            │
│ - Coordination between repositories                             │
│ - Error handling and logging                                    │
│ - Transaction orchestration                                     │
└─────────────────────────────────────────────────────────────────┘
                           |
                           v
┌─────────────────────────────────────────────────────────────────┐
│ Repository Layer (Data Access)                                  │
│ - Database queries (SQLAlchemy)                                 │
│ - CRUD operations                                               │
│ - Data persistence                                              │
│ - Query construction                                            │
└─────────────────────────────────────────────────────────────────┘
                           |
                           v
┌─────────────────────────────────────────────────────────────────┐
│ Database Layer (PostgreSQL)                                     │
│ - Data storage                                                  │
│ - Constraints enforcement                                       │
│ - Indexing                                                      │
│ - Transactions                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Complete Request Lifecycle

```
1. Request arrives at FastAPI application
2. Middleware stack processes request (CORS, rate limiting, etc.)
3. Router matches URL pattern
4. Dependencies are resolved (authentication, database session, etc.)
5. Pydantic validates request body/params
6. API endpoint function called
7. Service layer method called with validated data
8. Service coordinates business logic
9. Repository executes database queries
10. Results returned through layers
11. Response serialized to JSON
12. Middleware processes response (security headers, etc.)
13. Response sent to client
```

---

All flows follow this consistent layered architecture pattern for maintainability and testability.
