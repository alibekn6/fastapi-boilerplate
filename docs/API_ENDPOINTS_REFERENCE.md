# API Endpoints Reference

Quick reference guide for all available API endpoints.

## Base URL

- Development: `http://localhost:8000`
- Production: Your production URL

## API Version

All endpoints are prefixed with: `/api/v1`

---

## Authentication Endpoints

### 1. Register User

**Endpoint:** `POST /api/v1/auth/register`

**Request:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "SecurePass123"
}
```

**Response:** `201 Created`
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "XjK8_p...",
  "token_type": "bearer"
}
```

**Errors:**
- `400 Bad Request` - Username or email already exists
- `422 Unprocessable Entity` - Validation error

---

### 2. Login User

**Endpoint:** `POST /api/v1/auth/login`

**Request:**
```json
{
  "username": "john_doe",
  "password": "SecurePass123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "XjK8_p...",
  "token_type": "bearer"
}
```

**Errors:**
- `401 Unauthorized` - Invalid credentials or inactive account
- `422 Unprocessable Entity` - Validation error

---

### 3. Refresh Access Token

**Endpoint:** `POST /api/v1/auth/refresh`

**Request:**
```json
{
  "refresh_token": "XjK8_p..."
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJhbGc...",
  "refresh_token": "YmN9_q...",
  "token_type": "bearer"
}
```

**Features:**
- Automatically rotates refresh token (old one is revoked)
- Issues new access token

**Errors:**
- `401 Unauthorized` - Invalid, expired, or revoked token
- `422 Unprocessable Entity` - Validation error

---

### 4. Logout User

**Endpoint:** `POST /api/v1/auth/logout`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "refresh_token": "XjK8_p..."
}
```

**Response:** `200 OK`
```json
{
  "message": "Successfully logged out"
}
```

**Errors:**
- `400 Bad Request` - Invalid refresh token or doesn't belong to user
- `401 Unauthorized` - Invalid or expired access token
- `422 Unprocessable Entity` - Validation error

---

### 5. Get Current User Info

**Endpoint:** `GET /api/v1/auth/me`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "is_active": true,
  "is_admin": false,
  "email_verified": false,
  "created_at": "2025-12-26T10:00:00Z",
  "updated_at": "2025-12-26T10:00:00Z"
}
```

**Errors:**
- `401 Unauthorized` - Invalid or expired access token
- `403 Forbidden` - Inactive user account

---

## User Management Endpoints

### 6. Get Current User Profile

**Endpoint:** `GET /api/v1/users/me`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "is_active": true,
  "is_admin": false,
  "email_verified": false,
  "created_at": "2025-12-26T10:00:00Z",
  "updated_at": "2025-12-26T10:00:00Z"
}
```

**Note:** Same as `/auth/me` but under users router for RESTful consistency.

---

### 7. Update Current User Profile

**Endpoint:** `PUT /api/v1/users/me`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "username": "john_doe_updated",
  "email": "john.new@example.com"
}
```

**Notes:**
- Both fields are optional
- Can update one or both fields
- Username must be alphanumeric with underscores/hyphens
- Email must be valid format

**Response:** `200 OK`
```json
{
  "id": 1,
  "username": "john_doe_updated",
  "email": "john.new@example.com",
  "is_active": true,
  "is_admin": false,
  "email_verified": false,
  "created_at": "2025-12-26T10:00:00Z",
  "updated_at": "2025-12-26T10:30:00Z"
}
```

**Errors:**
- `400 Bad Request` - No fields provided, username or email already exists
- `401 Unauthorized` - Invalid or expired access token
- `422 Unprocessable Entity` - Validation error

---

### 8. Delete Current User Account

**Endpoint:** `DELETE /api/v1/users/me`

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:** `200 OK`
```json
{
  "message": "User account successfully deleted",
  "details": {
    "user_id": 1,
    "username": "john_doe"
  }
}
```

**Notes:**
- Performs soft delete (sets `is_active = False`)
- User cannot login after deletion
- Data is preserved for audit purposes

**Errors:**
- `400 Bad Request` - User not found
- `401 Unauthorized` - Invalid or expired access token

---

## Health Check Endpoints

### 9. Basic Health Check

**Endpoint:** `GET /health`

**Response:** `200 OK`
```json
{
  "status": "healthy",
  "service": "FastAPI App",
  "environment": "development"
}
```

---

### 10. Readiness Check

**Endpoint:** `GET /health/ready`

**Response:** `200 OK` (if database connected)
```json
{
  "status": "ready",
  "service": "FastAPI App",
  "environment": "development",
  "database": "connected"
}
```

**Response:** `503 Service Unavailable` (if database disconnected)
```json
{
  "status": "unavailable",
  "service": "FastAPI App",
  "database": "disconnected"
}
```

---

## Common HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request data or business logic error
- `401 Unauthorized` - Authentication required or failed
- `403 Forbidden` - Authenticated but not authorized
- `404 Not Found` - Resource not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error
- `503 Service Unavailable` - Service temporarily unavailable

---

## Authentication Flow

### Initial Authentication
1. Register or login to get tokens
2. Store both `access_token` and `refresh_token` securely
3. Use `access_token` in `Authorization: Bearer` header for requests

### Token Refresh Flow
1. When `access_token` expires (returns 401), use refresh endpoint
2. Send `refresh_token` to `/api/v1/auth/refresh`
3. Receive new `access_token` and `refresh_token`
4. Store new tokens and retry original request

### Logout Flow
1. Send logout request with both tokens
2. `refresh_token` is revoked in database
3. Clear tokens from client storage

---

## Usage Examples

### cURL Examples

#### Register
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePass123"
  }'
```

#### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "SecurePass123"
  }'
```

#### Get Profile
```bash
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <your_access_token>"
```

#### Update Profile
```bash
curl -X PUT http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe_new",
    "email": "john.new@example.com"
  }'
```

#### Refresh Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<your_refresh_token>"
  }'
```

#### Logout
```bash
curl -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "<your_refresh_token>"
  }'
```

---

## Python Client Example

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# Register
response = requests.post(
    f"{BASE_URL}/auth/register",
    json={
        "username": "john_doe",
        "email": "john@example.com",
        "password": "SecurePass123"
    }
)
tokens = response.json()
access_token = tokens["access_token"]
refresh_token = tokens["refresh_token"]

# Get profile
response = requests.get(
    f"{BASE_URL}/users/me",
    headers={"Authorization": f"Bearer {access_token}"}
)
user = response.json()

# Update profile
response = requests.put(
    f"{BASE_URL}/users/me",
    headers={"Authorization": f"Bearer {access_token}"},
    json={
        "username": "john_doe_updated",
        "email": "john.new@example.com"
    }
)
updated_user = response.json()

# Refresh token
response = requests.post(
    f"{BASE_URL}/auth/refresh",
    json={"refresh_token": refresh_token}
)
new_tokens = response.json()

# Logout
response = requests.post(
    f"{BASE_URL}/auth/logout",
    headers={"Authorization": f"Bearer {access_token}"},
    json={"refresh_token": refresh_token}
)
```

---

## Interactive API Documentation

When running in development mode (DEBUG=True):

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

These provide interactive documentation and allow you to test endpoints directly in the browser.
