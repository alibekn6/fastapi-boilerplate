# Quick Reference Guide

Essential code snippets and commands for common operations.

---

## Table of Contents
1. [Running the Application](#running-the-application)
2. [Database Operations](#database-operations)
3. [Creating Endpoints](#creating-endpoints)
4. [Testing](#testing)
5. [Common Patterns](#common-patterns)
6. [Configuration](#configuration)
7. [Debugging](#debugging)

---

## Running the Application

### Development
```bash
# Install dependencies
uv sync

# Run with auto-reload
uvicorn src.main:app --reload

# Or using FastAPI CLI
fastapi dev src.main:app

# Specify host and port
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### Production
```bash
# Install production dependencies
uv sync --no-dev

# Run with multiple workers
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4

# Or use Gunicorn with Uvicorn workers
gunicorn src.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

---

## Database Operations

### Migrations
```bash
# Create a new migration
alembic revision --autogenerate -m "Add new field to users"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current revision
alembic current

# Rollback to specific revision
alembic downgrade <revision_id>
```

### Direct Database Access
```python
from src.db.database import AsyncSessionLocal
from src.models.user import User
from sqlalchemy import select

async def example():
    async with AsyncSessionLocal() as db:
        # Query users
        result = await db.execute(select(User))
        users = result.scalars().all()

        # Create user
        user = User(username="test", email="test@example.com")
        db.add(user)
        await db.commit()
        await db.refresh(user)
```

---

## Creating Endpoints

### 1. Define Pydantic Schemas
```python
# src/schemas/my_feature.py
from pydantic import BaseModel, Field

class MyRequestSchema(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None

class MyResponseSchema(BaseModel):
    id: int
    name: str
    description: str | None

    class Config:
        from_attributes = True  # For SQLAlchemy models
```

### 2. Create Database Model
```python
# src/models/my_feature.py
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String
from src.db.database import Base

class MyModel(Base):
    __tablename__ = "my_table"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(500))
```

### 3. Create Repository
```python
# src/repositories/my_repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.my_feature import MyModel

class MyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> list[MyModel]:
        result = await self.session.execute(select(MyModel))
        return result.scalars().all()

    async def get_by_id(self, id: int) -> MyModel | None:
        result = await self.session.execute(
            select(MyModel).where(MyModel.id == id)
        )
        return result.scalar_one_or_none()

    async def create(self, name: str, description: str | None) -> MyModel:
        obj = MyModel(name=name, description=description)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj
```

### 4. Create Service
```python
# src/services/my_service.py
from src.repositories.my_repository import MyRepository
from src.schemas.my_feature import MyRequestSchema, MyResponseSchema
from src.core.exceptions import NotFoundError

class MyService:
    def __init__(self, repository: MyRepository):
        self.repository = repository

    async def get_all(self) -> list[MyResponseSchema]:
        items = await self.repository.get_all()
        return [MyResponseSchema.model_validate(item) for item in items]

    async def get_by_id(self, id: int) -> MyResponseSchema:
        item = await self.repository.get_by_id(id)
        if not item:
            raise NotFoundError(f"Item {id} not found")
        return MyResponseSchema.model_validate(item)

    async def create(self, data: MyRequestSchema) -> MyResponseSchema:
        item = await self.repository.create(
            name=data.name,
            description=data.description
        )
        return MyResponseSchema.model_validate(item)
```

### 5. Create API Endpoints
```python
# src/api/v1/my_feature.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.repositories.my_repository import MyRepository
from src.services.my_service import MyService
from src.schemas.my_feature import MyRequestSchema, MyResponseSchema
from src.core.dependencies import CurrentUser

router = APIRouter(prefix="/my-feature")

def get_my_service(db: AsyncSession = Depends(get_db)) -> MyService:
    repository = MyRepository(db)
    return MyService(repository)

@router.get("", response_model=list[MyResponseSchema])
async def list_items(
    service: MyService = Depends(get_my_service),
    current_user: CurrentUser = None  # Optional auth
):
    """List all items."""
    return await service.get_all()

@router.get("/{id}", response_model=MyResponseSchema)
async def get_item(
    id: int,
    service: MyService = Depends(get_my_service)
):
    """Get item by ID."""
    return await service.get_by_id(id)

@router.post("", response_model=MyResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_item(
    data: MyRequestSchema,
    service: MyService = Depends(get_my_service),
    current_user: CurrentUser  # Requires auth
):
    """Create new item."""
    return await service.create(data)
```

### 6. Register Router in main.py
```python
# src/main.py
from src.api.v1.my_feature import router as my_feature_router

app.include_router(
    my_feature_router,
    prefix=f"/api/{config.API_VERSION}",
    tags=["My Feature"]
)
```

---

## Testing

### Unit Tests
```python
# tests/services/test_my_service.py
import pytest
from unittest.mock import AsyncMock
from src.services.my_service import MyService
from src.schemas.my_feature import MyRequestSchema

@pytest.mark.asyncio
async def test_create_item():
    # Mock repository
    mock_repo = AsyncMock()
    mock_repo.create.return_value = MockModel(id=1, name="test")

    # Test service
    service = MyService(mock_repo)
    data = MyRequestSchema(name="test")
    result = await service.create(data)

    assert result.name == "test"
    mock_repo.create.assert_called_once()
```

### Integration Tests
```python
# tests/api/v1/test_my_feature.py
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_create_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/my-feature",
            json={"name": "test"}
        )
        assert response.status_code == 201
        assert response.json()["name"] == "test"
```

### Run Tests
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/api/v1/test_auth.py

# Run specific test function
pytest tests/api/v1/test_auth.py::test_register

# Run with coverage
pytest --cov=src --cov-report=html
```

---

## Common Patterns

### Pagination
```python
from src.core.pagination import PaginationParams, PaginatedResponse, paginate

@router.get("", response_model=PaginatedResponse[MyResponseSchema])
async def list_items(
    pagination: PaginationParams = Depends(),
    service: MyService = Depends(get_my_service)
):
    items, total = await service.get_paginated(pagination)
    return PaginatedResponse.create(items, total, pagination.page, pagination.page_size)
```

### Exception Handling
```python
from src.core.exceptions import NotFoundError, ConflictError

# In service
async def get_by_id(self, id: int):
    item = await self.repository.get_by_id(id)
    if not item:
        raise NotFoundError(f"Item {id} not found")
    return item

async def create(self, data: MyRequestSchema):
    existing = await self.repository.get_by_name(data.name)
    if existing:
        raise ConflictError(f"Item with name '{data.name}' already exists")
    return await self.repository.create(data)
```

### Admin-Only Endpoints
```python
from src.core.dependencies import CurrentAdmin

@router.delete("/{id}")
async def delete_item(
    id: int,
    current_admin: CurrentAdmin,  # Requires admin
    service: MyService = Depends(get_my_service)
):
    await service.delete(id)
    return {"message": "Item deleted"}
```

### Rate Limiting Custom
```python
from src.core.rate_limiter import check_rate_limit_per_minute

@router.post("/expensive-operation")
async def expensive_operation(request: Request):
    # Custom rate limit for this endpoint
    client_ip = request.client.host
    check_rate_limit_per_minute(f"expensive:{client_ip}", max_requests=5)

    # Do expensive operation
    return {"status": "success"}
```

### Background Tasks
```python
from fastapi import BackgroundTasks

def send_email_background(email: str):
    # Send email logic
    pass

@router.post("/register")
async def register(
    data: UserRegister,
    background_tasks: BackgroundTasks,
    service: AuthService = Depends(get_auth_service)
):
    user = await service.register_user(data)
    background_tasks.add_task(send_email_background, user.email)
    return user
```

---

## Configuration

### Access Configuration
```python
from src.core.config import Config

config = Config()

# Use configuration values
if config.DEBUG:
    print("Debug mode enabled")

max_size = config.MAX_UPLOAD_SIZE
allowed_exts = config.allowed_extensions  # Property method
db_url = config.db_url  # Computed property
```

### Environment Variables
```bash
# Set in .env file
DEBUG=true
RATE_LIMIT_PER_MINUTE=100

# Override in production
ENVIRONMENT=production
DEBUG=false
```

### Per-Environment Config
```python
# Development settings
if config.ENVIRONMENT == "development":
    # Enable debug features

# Production settings
if config.ENVIRONMENT == "production":
    # Strict security
```

---

## Debugging

### Enable Debug Logging
```python
# In .env
DEBUG=true
LOG_LEVEL=DEBUG
LOG_FORMAT=console
```

### Add Logging
```python
from src.core.logging import get_logger

logger = get_logger(__name__)

# Log levels
logger.debug("Debug message", extra_data="value")
logger.info("Info message", user_id=123)
logger.warning("Warning message", error="something")
logger.error("Error message", exc_info=True)
```

### Database Query Logging
```python
# In src/db/database.py
engine = create_async_engine(
    config.db_url,
    echo=True,  # Enable SQL query logging
)
```

### FastAPI Debug Mode
```bash
# Shows detailed errors in browser
uvicorn src.main:app --reload --log-level debug
```

### Interactive Debugging
```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use ipdb (install first)
import ipdb; ipdb.set_trace()

# Or modern breakpoint()
breakpoint()
```

### Check Database Connection
```python
from src.db.database import check_db_connection

async def test_db():
    connected = await check_db_connection()
    print(f"Database connected: {connected}")
```

---

## Quick Commands Reference

### Development
```bash
# Start dev server
uvicorn src.main:app --reload

# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Run tests
pytest

# Install dependencies
uv sync
```

### Database
```bash
# Access PostgreSQL
psql -U postgres -d myapp

# Reset database (careful!)
alembic downgrade base
alembic upgrade head

# View migrations
alembic history
```

### Code Quality
```bash
# Format code (if black installed)
black src/

# Lint code (if ruff installed)
ruff check src/

# Type check (if mypy installed)
mypy src/
```

---

## API Testing with curl

### Register
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","email":"test@example.com","password":"Password123"}'
```

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"Password123"}'
```

### Authenticated Request
```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### With jq for Pretty Output
```bash
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" | jq
```

---

## Common Issues & Solutions

### Import Errors
```bash
# Make sure src is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/testing"
```

### Database Connection Errors
```bash
# Check PostgreSQL is running
pg_isready

# Check .env has correct credentials
cat .env | grep DB_

# Test connection
psql -U $DB_USER -d $DB_NAME
```

### Migration Conflicts
```bash
# If multiple heads
alembic merge

# Start fresh (development only!)
alembic downgrade base
rm alembic/versions/*.py
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

### Rate Limit During Testing
```python
# Disable rate limiting in .env for tests
RATE_LIMIT_ENABLED=false
```

---

## Environment Setup Checklist

- [ ] Python 3.13+ installed
- [ ] uv package manager installed
- [ ] PostgreSQL running
- [ ] Redis running (optional, for Celery/rate limiting)
- [ ] .env file configured (copy from .env.example)
- [ ] Dependencies installed (`uv sync`)
- [ ] Database created
- [ ] Migrations applied (`alembic upgrade head`)
- [ ] Application starts (`uvicorn src.main:app`)
- [ ] Health check passes (`curl http://localhost:8000/health`)

---

## Production Deployment Checklist

- [ ] `ENVIRONMENT=production`
- [ ] `DEBUG=false`
- [ ] Strong `SECRET_KEY` generated
- [ ] Database credentials secured
- [ ] HTTPS enabled
- [ ] CORS_ORIGINS set to production domains
- [ ] Rate limiting enabled
- [ ] Logging configured (JSON format)
- [ ] Error tracking enabled (Sentry)
- [ ] Database backups scheduled
- [ ] Redis configured (for rate limiting)
- [ ] Multiple workers configured
- [ ] Health checks in load balancer
- [ ] Monitoring and alerts set up

---

## Useful Links

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **SQLAlchemy Docs**: https://docs.sqlalchemy.org/
- **Pydantic Docs**: https://docs.pydantic.dev/
- **Alembic Docs**: https://alembic.sqlalchemy.org/
- **Project Architecture**: `/Users/alibekanuarbek/Desktop/py/testing/ARCHITECTURE.md`
- **Implementation Summary**: `/Users/alibekanuarbek/Desktop/py/testing/IMPLEMENTATION_SUMMARY.md`
- **Auth Flow Diagrams**: `/Users/alibekanuarbek/Desktop/py/testing/AUTH_FLOW_DIAGRAMS.md`
