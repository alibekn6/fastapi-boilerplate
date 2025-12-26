# Authentication Flow Diagrams

Visual representations of all authentication flows in the system.

---

## 1. Registration Flow

```
┌─────────┐                                                     ┌──────────┐
│ Client  │                                                     │ Database │
└────┬────┘                                                     └─────┬────┘
     │                                                                 │
     │ POST /api/v1/auth/register                                     │
     │ {username, email, password}                                    │
     ├───────────────────────────────►┌──────────────────┐            │
     │                                │  API Handler     │            │
     │                                │  (auth.py)       │            │
     │                                └────────┬─────────┘            │
     │                                         │                      │
     │                                         │ 1. Validate input    │
     │                                         │    (Pydantic)        │
     │                                         │                      │
     │                                         ▼                      │
     │                                ┌──────────────────┐            │
     │                                │  AuthService     │            │
     │                                │ register_user()  │            │
     │                                └────────┬─────────┘            │
     │                                         │                      │
     │                                         │ 2. Check username    │
     │                                         │    exists            │
     │                                         ├─────────────────────►│
     │                                         │                      │
     │                                         │◄─────────────────────┤
     │                                         │                      │
     │                                         │ 3. Check email       │
     │                                         │    exists            │
     │                                         ├─────────────────────►│
     │                                         │                      │
     │                                         │◄─────────────────────┤
     │                                         │                      │
     │                                         │ 4. Hash password     │
     │                                         │    (bcrypt)          │
     │                                         │                      │
     │                                         │ 5. Create user       │
     │                                         ├─────────────────────►│
     │                                         │                      │
     │                                         │◄─────────────────────┤
     │                                         │                      │
     │                                         │ 6. Generate access   │
     │                                         │    token (JWT)       │
     │                                         │                      │
     │                                         │ 7. Generate refresh  │
     │                                         │    token (random)    │
     │                                         │                      │
     │                                         │ 8. Store refresh     │
     │                                         │    token in DB       │
     │                                         ├─────────────────────►│
     │                                         │                      │
     │                                         │◄─────────────────────┤
     │                                         │                      │
     │◄────────────────────────────────────────┤                      │
     │ 201 CREATED                                                    │
     │ {access_token, refresh_token, token_type}                      │
     │                                                                 │
```

**Key Points**:
- Password is hashed with bcrypt (never stored plaintext)
- Username and email uniqueness checked before creation
- Both access and refresh tokens returned immediately
- Refresh token stored in database with metadata (user_agent, IP)

---

## 2. Login Flow

```
┌─────────┐                                                     ┌──────────┐
│ Client  │                                                     │ Database │
└────┬────┘                                                     └─────┬────┘
     │                                                                 │
     │ POST /api/v1/auth/login                                        │
     │ {username, password}                                           │
     ├───────────────────────────────►┌──────────────────┐            │
     │                                │  API Handler     │            │
     │                                └────────┬─────────┘            │
     │                                         │                      │
     │                                         ▼                      │
     │                                ┌──────────────────┐            │
     │                                │  AuthService     │            │
     │                                │  login_user()    │            │
     │                                └────────┬─────────┘            │
     │                                         │                      │
     │                                         │ 1. Get user by       │
     │                                         │    username          │
     │                                         ├─────────────────────►│
     │                                         │                      │
     │                                         │◄─────────────────────┤
     │                                         │                      │
     │                                         │ 2. Verify password   │
     │                                         │    (bcrypt.checkpw)  │
     │                                         │                      │
     │                                         │ 3. Check is_active   │
     │                                         │                      │
     │                                         │ 4. Generate tokens   │
     │                                         │                      │
     │                                         │ 5. Store refresh     │
     │                                         │    token in DB       │
     │                                         ├─────────────────────►│
     │                                         │                      │
     │◄────────────────────────────────────────┤                      │
     │ 200 OK                                                         │
     │ {access_token, refresh_token, token_type}                      │
     │                                                                 │
```

**Security Features**:
- Generic error message ("Invalid username or password") to prevent username enumeration
- Account status check (is_active)
- New refresh token created for each login session
- Session metadata tracked (user_agent, IP address)

---

## 3. Token Refresh Flow (with Rotation)

```
┌─────────┐                                                     ┌──────────┐
│ Client  │                                                     │ Database │
└────┬────┘                                                     └─────┬────┘
     │                                                                 │
     │ POST /api/v1/auth/refresh                                      │
     │ {refresh_token}                                                │
     ├───────────────────────────────►┌──────────────────┐            │
     │                                │  API Handler     │            │
     │                                └────────┬─────────┘            │
     │                                         │                      │
     │                                         ▼                      │
     │                                ┌──────────────────┐            │
     │                                │  AuthService     │            │
     │                                │ refresh_tokens() │            │
     │                                └────────┬─────────┘            │
     │                                         │                      │
     │                                         │ 1. Get refresh       │
     │                                         │    token from DB     │
     │                                         ├─────────────────────►│
     │                                         │                      │
     │                                         │◄─────────────────────┤
     │                                         │                      │
     │                                         │ 2. Validate:         │
     │                                         │    - Not revoked     │
     │                                         │    - Not expired     │
     │                                         │    - User active     │
     │                                         │                      │
     │                                         │ 3. REVOKE old token  │
     │                                         │    (is_revoked=True) │
     │                                         ├─────────────────────►│
     │                                         │                      │
     │                                         │ 4. Generate NEW      │
     │                                         │    access token      │
     │                                         │                      │
     │                                         │ 5. Generate NEW      │
     │                                         │    refresh token     │
     │                                         │                      │
     │                                         │ 6. Store NEW         │
     │                                         │    refresh token     │
     │                                         ├─────────────────────►│
     │                                         │                      │
     │◄────────────────────────────────────────┤                      │
     │ 200 OK                                                         │
     │ {access_token, refresh_token, token_type}                      │
     │ (Both tokens are NEW)                                          │
     │                                                                 │
```

**Token Rotation Benefits**:
- Old refresh token is immediately revoked
- New refresh token is generated (different value)
- Prevents token replay attacks
- If stolen token is used, legitimate user's next refresh fails (detection)
- Limits blast radius of token theft

---

## 4. Logout Flow (Single Session)

```
┌─────────┐                                                     ┌──────────┐
│ Client  │                                                     │ Database │
└────┬────┘                                                     └─────┬────┘
     │                                                                 │
     │ POST /api/v1/auth/logout                                       │
     │ {refresh_token}                                                │
     ├───────────────────────────────►┌──────────────────┐            │
     │                                │  API Handler     │            │
     │                                └────────┬─────────┘            │
     │                                         │                      │
     │                                         ▼                      │
     │                                ┌──────────────────┐            │
     │                                │  AuthService     │            │
     │                                │   logout()       │            │
     │                                └────────┬─────────┘            │
     │                                         │                      │
     │                                         │ 1. Find refresh      │
     │                                         │    token in DB       │
     │                                         ├─────────────────────►│
     │                                         │                      │
     │                                         │◄─────────────────────┤
     │                                         │                      │
     │                                         │ 2. Mark as revoked   │
     │                                         │    (is_revoked=True) │
     │                                         ├─────────────────────►│
     │                                         │                      │
     │◄────────────────────────────────────────┤                      │
     │ 200 OK                                                         │
     │ {message: "Successfully logged out"}                           │
     │                                                                 │
```

**Note**: Access token remains valid until expiration (stateless design).

---

## 5. Logout All Sessions Flow

```
┌─────────┐                                                     ┌──────────┐
│ Client  │                                                     │ Database │
└────┬────┘                                                     └─────┬────┘
     │                                                                 │
     │ POST /api/v1/auth/logout-all                                   │
     │ Headers: Authorization: Bearer <access_token>                  │
     ├───────────────────────────────►┌──────────────────┐            │
     │                                │  API Handler     │            │
     │                                │  (requires auth) │            │
     │                                └────────┬─────────┘            │
     │                                         │                      │
     │                                         │ 1. Extract user_id   │
     │                                         │    from JWT          │
     │                                         │                      │
     │                                         ▼                      │
     │                                ┌──────────────────┐            │
     │                                │  AuthService     │            │
     │                                │  logout_all()    │            │
     │                                └────────┬─────────┘            │
     │                                         │                      │
     │                                         │ 2. Revoke ALL        │
     │                                         │    refresh tokens    │
     │                                         │    for user          │
     │                                         ├─────────────────────►│
     │                                         │ UPDATE refresh_tokens│
     │                                         │ SET is_revoked=TRUE  │
     │                                         │ WHERE user_id=X      │
     │                                         │◄─────────────────────┤
     │                                         │                      │
     │◄────────────────────────────────────────┤                      │
     │ 200 OK                                                         │
     │ {message: "All sessions terminated", revoked_count: 3}         │
     │                                                                 │
```

**Use Cases**:
- Password change (force logout everywhere)
- Security incident (suspicious activity detected)
- User-initiated "logout all devices"

---

## 6. Protected Endpoint Access

```
┌─────────┐                                                     ┌──────────┐
│ Client  │                                                     │ Database │
└────┬────┘                                                     └─────┬────┘
     │                                                                 │
     │ GET /api/v1/auth/me                                            │
     │ Headers: Authorization: Bearer <access_token>                  │
     ├───────────────────────────────►┌──────────────────┐            │
     │                                │ Middleware Stack │            │
     │                                │ - Rate Limit     │            │
     │                                │ - Auth Check     │            │
     │                                └────────┬─────────┘            │
     │                                         │                      │
     │                                         │ 1. Decode JWT        │
     │                                         │    (verify signature)│
     │                                         │                      │
     │                                         │ 2. Extract user_id   │
     │                                         │    from payload      │
     │                                         │                      │
     │                                         │ 3. Get user from DB  │
     │                                         ├─────────────────────►│
     │                                         │                      │
     │                                         │◄─────────────────────┤
     │                                         │                      │
     │                                         │ 4. Check is_active   │
     │                                         │                      │
     │                                         ▼                      │
     │                                ┌──────────────────┐            │
     │                                │  API Handler     │            │
     │                                │  (current_user   │            │
     │                                │   injected)      │            │
     │                                └────────┬─────────┘            │
     │                                         │                      │
     │◄────────────────────────────────────────┤                      │
     │ 200 OK                                                         │
     │ {id, username, email, is_active, ...}                          │
     │                                                                 │
```

**Dependency Injection Flow**:
1. `get_db()` → Creates database session
2. `get_current_user()` → Validates JWT, fetches user from DB
3. `CurrentUser` → Type alias for dependency injection

---

## 7. Password Reset Flow

```
┌─────────┐                                                     ┌──────────┐
│ Client  │                                                     │ Database │
└────┬────┘                                                     └─────┬────┘
     │                                                                 │
     │ STEP 1: Request Password Reset                                 │
     │ ─────────────────────────────────────────────────              │
     │ POST /api/v1/auth/password-reset-request                       │
     │ {email}                                                        │
     ├───────────────────────────────►┌──────────────────┐            │
     │                                │  AuthService     │            │
     │                                └────────┬─────────┘            │
     │                                         │                      │
     │                                         │ 1. Find user by email│
     │                                         ├─────────────────────►│
     │                                         │                      │
     │                                         │ 2. Generate reset    │
     │                                         │    token (random)    │
     │                                         │                      │
     │                                         │ 3. Store token in DB │
     │                                         │    (expires in 1h)   │
     │                                         ├─────────────────────►│
     │                                         │                      │
     │                                         │ 4. Send email with   │
     │                                         │    reset link        │
     │                                         │    (background task) │
     │                                         │                      │
     │◄────────────────────────────────────────┤                      │
     │ 200 OK                                                         │
     │ {message: "Password reset email sent"}                         │
     │                                                                 │
     │                                                                 │
     │ STEP 2: Confirm Password Reset                                 │
     │ ─────────────────────────────────────────────────              │
     │ POST /api/v1/auth/password-reset-confirm                       │
     │ {token, new_password}                                          │
     ├───────────────────────────────►┌──────────────────┐            │
     │                                │  AuthService     │            │
     │                                └────────┬─────────┘            │
     │                                         │                      │
     │                                         │ 1. Find token in DB  │
     │                                         ├─────────────────────►│
     │                                         │                      │
     │                                         │ 2. Validate:         │
     │                                         │    - Not used        │
     │                                         │    - Not expired     │
     │                                         │                      │
     │                                         │ 3. Hash new password │
     │                                         │                      │
     │                                         │ 4. Update user       │
     │                                         │    password          │
     │                                         ├─────────────────────►│
     │                                         │                      │
     │                                         │ 5. Mark token as used│
     │                                         ├─────────────────────►│
     │                                         │                      │
     │                                         │ 6. Revoke all refresh│
     │                                         │    tokens (logout    │
     │                                         │    everywhere)       │
     │                                         ├─────────────────────►│
     │                                         │                      │
     │◄────────────────────────────────────────┤                      │
     │ 200 OK                                                         │
     │ {message: "Password reset successful"}                         │
     │                                                                 │
```

**Security Features**:
- Token expires in 1 hour (configurable)
- Token can only be used once
- All sessions terminated after password reset
- Generic success message (doesn't reveal if email exists)

---

## 8. Session Management Flow

```
┌─────────┐                                                     ┌──────────┐
│ Client  │                                                     │ Database │
└────┬────┘                                                     └─────┬────┘
     │                                                                 │
     │ GET /api/v1/auth/sessions                                      │
     │ Headers: Authorization: Bearer <access_token>                  │
     ├───────────────────────────────►┌──────────────────┐            │
     │                                │  AuthService     │            │
     │                                │ get_user_sessions│            │
     │                                └────────┬─────────┘            │
     │                                         │                      │
     │                                         │ 1. Get all active    │
     │                                         │    refresh tokens    │
     │                                         │    for current user  │
     │                                         ├─────────────────────►│
     │                                         │ SELECT * FROM        │
     │                                         │ refresh_tokens       │
     │                                         │ WHERE user_id=X      │
     │                                         │ AND is_revoked=FALSE │
     │                                         │ AND expires_at > NOW │
     │                                         │◄─────────────────────┤
     │                                         │                      │
     │                                         │ 2. Mark current      │
     │                                         │    session (compare  │
     │                                         │    with current      │
     │                                         │    refresh token)    │
     │                                         │                      │
     │◄────────────────────────────────────────┤                      │
     │ 200 OK                                                         │
     │ {items: [                                                      │
     │   {id: 1, user_agent: "Chrome", ip: "1.2.3.4",                 │
     │    created_at, expires_at, is_current: true},                  │
     │   {id: 2, user_agent: "Firefox", ip: "5.6.7.8",                │
     │    created_at, expires_at, is_current: false}                  │
     │ ]}                                                              │
     │                                                                 │
```

**Features**:
- View all active sessions (devices)
- See user agent, IP address, login time
- Identify current session
- Revoke specific sessions

---

## Security Principles Applied

### 1. Defense in Depth
- Multiple layers: validation, sanitization, parameterized queries, rate limiting
- No single point of failure

### 2. Principle of Least Privilege
- Access tokens short-lived (30 minutes)
- Refresh tokens scoped to user
- Admin-only endpoints protected

### 3. Secure by Default
- HTTPS enforced in production (HSTS)
- Security headers enabled
- CORS restricted to whitelist
- Rate limiting enabled

### 4. Fail Securely
- Generic error messages (no information leakage)
- Exceptions caught and logged
- Database errors don't expose schema

### 5. Separation of Concerns
- Authentication separate from authorization
- Business logic in services
- Data access in repositories

### 6. Auditability
- All sessions tracked with metadata
- Correlation IDs for request tracing
- Structured logging for analysis

---

## Rate Limiting Behavior

```
Client makes 61 requests in 60 seconds:

Request 1-60:  200 OK (allowed)
Request 61:    429 Too Many Requests
               {
                 "error": {
                   "code": "RATE_LIMIT_EXCEEDED",
                   "message": "Rate limit exceeded. Try again in 45 seconds.",
                   "details": {"retry_after": 45}
                 }
               }
               Headers: Retry-After: 45

Request 62-N:  429 Too Many Requests (until window expires)

After 60s:     Oldest requests drop from window, new requests allowed
```

**Sliding Window**:
- More accurate than fixed window
- No burst at window boundaries
- Per-IP by default (can extend to per-user)

---

## Error Handling Flow

```
Any Request
    │
    ├─► Middleware Stack
    │   │
    │   ├─► Rate Limit Check
    │   │   └─► 429 if exceeded
    │   │
    │   ├─► Authentication
    │   │   └─► 401 if invalid token
    │   │
    │   └─► Authorization
    │       └─► 403 if not allowed
    │
    ├─► Route Handler
    │   │
    │   ├─► Pydantic Validation
    │   │   └─► 422 if invalid input
    │   │
    │   ├─► Service Layer
    │   │   ├─► Business Logic
    │   │   │   └─► Raise AppException
    │   │   │
    │   │   └─► Repository Layer
    │   │       ├─► Database Query
    │   │       │   ├─► IntegrityError → 409
    │   │       │   └─► SQLAlchemyError → 500
    │   │       │
    │   │       └─► Return Data
    │   │
    │   └─► Return Response
    │
    └─► ErrorHandlerMiddleware (if exception)
        └─► Convert to structured JSON response
```

All errors return consistent format:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {}
  }
}
```

---

## Middleware Execution Order

```
Request comes in
    │
    ├─► 1. ErrorHandlerMiddleware (outer)
    │   └─► Catches all exceptions from inner layers
    │
    ├─► 2. SecurityHeadersMiddleware
    │   └─► Adds security headers to response
    │
    ├─► 3. CORSMiddleware
    │   └─► Validates origin, adds CORS headers
    │
    ├─► 4. RateLimitMiddleware
    │   └─► Checks rate limit, raises RateLimitError if exceeded
    │
    ├─► 5. CorrelationIdMiddleware (if added)
    │   └─► Generates/extracts correlation ID
    │
    ├─► 6. LoggingMiddleware (if added)
    │   └─► Logs request/response
    │
    └─► 7. Route Handler
        └─► Your endpoint logic

Response goes out
    ▲
    │
    └─── Middleware stack (reverse order)
         - Logging
         - Correlation ID
         - Rate Limit
         - CORS
         - Security Headers
         - Error Handler
```

**Key Point**: Order matters! ErrorHandlerMiddleware must be outermost to catch exceptions from all other layers.
