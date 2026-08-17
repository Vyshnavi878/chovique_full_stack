"""
Pytest configuration and fixtures for async testing.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.db.session import get_db
from app.main import app


# ==========================================================
# Event Loop
# ==========================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ==========================================================
# Test Database Engine (SQLite in-memory)
# ==========================================================

from sqlalchemy.pool import StaticPool

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


# ==========================================================
# Database Setup / Teardown
# ==========================================================

@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create tables before each test, drop after."""

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ==========================================================
# Override get_db dependency
# ==========================================================

async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


# ==========================================================
# Mock Redis (using fakeredis)
# ==========================================================

@pytest.fixture(autouse=True)
def mock_redis():
    """Replace the real Redis client with fakeredis for all tests."""
    import fakeredis.aioredis

    fake_redis = fakeredis.aioredis.FakeRedis(decode_responses=True)

    with patch("app.services.otp_service.redis_client", fake_redis):
        with patch("app.db.redis.redis_client", fake_redis):
            yield fake_redis


# ==========================================================
# Mock Mail Service
# ==========================================================

@pytest.fixture(autouse=True)
def mock_mail():
    """Prevent actual emails from being sent during tests."""
    with patch(
        "app.services.mail_service.MailService.send_registration_otp",
        new_callable=AsyncMock,
    ) as mock_reg:
        with patch(
            "app.services.mail_service.MailService.send_forgot_password_otp",
            new_callable=AsyncMock,
        ) as mock_forgot:
            yield {"registration": mock_reg, "forgot": mock_forgot}


# ==========================================================
# Async HTTP Client
# ==========================================================

@pytest_asyncio.fixture
async def client():
    """Async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as ac:
        yield ac


# ==========================================================
# Test DB Session
# ==========================================================

@pytest_asyncio.fixture
async def db_session():
    """Provide a test database session."""
    async with TestSessionLocal() as session:
        yield session


# ==========================================================
# Helper: Register + Verify a test user
# ==========================================================

@pytest_asyncio.fixture
async def authenticated_client(client: AsyncClient, mock_redis):
    """
    Returns an AsyncClient with auth cookies set after
    registering and verifying a test user.
    """

    # Register
    await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "TestPass123!",
            "confirm_password": "TestPass123!",
        },
    )

    # Get OTP from mock Redis
    otp = await mock_redis.get("otp:register:test@example.com")

    # Verify OTP
    response = await client.post(
        "/api/v1/auth/verify-otp",
        json={
            "email": "test@example.com",
            "otp": otp,
            "full_name": "Test User",
            "password": "TestPass123!",
        },
    )

    assert response.status_code == 200
    csrf = response.cookies.get("csrf_token")
    if csrf:
        client.headers["x-csrf-token"] = csrf

    # The cookies are set on the client automatically
    yield client
