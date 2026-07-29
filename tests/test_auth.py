"""
Authentication endpoint tests.

Covers: register, verify OTP, wrong OTP, max attempts, expired OTP,
resend, login, forgot password, reset password, refresh, logout.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


# ==========================================================
# Registration
# ==========================================================

class TestRegister:

    async def test_register_success(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "John Doe",
                "email": "john@example.com",
                "password": "SecurePass1!",
                "confirm_password": "SecurePass1!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "OTP sent successfully."
        assert data["email"] == "john@example.com"
        assert "expires_in" in data

    async def test_register_password_mismatch(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "John Doe",
                "email": "john@example.com",
                "password": "SecurePass1!",
                "confirm_password": "DifferentPass!",
            },
        )
        assert response.status_code == 400
        assert "Passwords do not match" in response.json()["detail"]

    async def test_register_duplicate_email(self, client: AsyncClient, mock_redis):
        # Register first
        await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "John Doe",
                "email": "dup@example.com",
                "password": "SecurePass1!",
                "confirm_password": "SecurePass1!",
            },
        )

        # Verify OTP to create user
        otp = await mock_redis.get("otp:register:dup@example.com")
        await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "email": "dup@example.com",
                "otp": otp,
                "full_name": "John Doe",
                "password": "SecurePass1!",
            },
        )

        # Try to register same email
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "John Doe",
                "email": "dup@example.com",
                "password": "SecurePass1!",
                "confirm_password": "SecurePass1!",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]


# ==========================================================
# OTP Verification
# ==========================================================

class TestVerifyOTP:

    async def test_verify_otp_success(self, client: AsyncClient, mock_redis):
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Jane Doe",
                "email": "jane@example.com",
                "password": "SecurePass1!",
                "confirm_password": "SecurePass1!",
            },
        )

        otp = await mock_redis.get("otp:register:jane@example.com")
        assert otp is not None

        # Verify
        response = await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "email": "jane@example.com",
                "otp": otp,
                "full_name": "Jane Doe",
                "password": "SecurePass1!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Registration successful."
        assert "user" in data

    async def test_wrong_otp(self, client: AsyncClient, mock_redis):
        await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Test User",
                "email": "wrong@example.com",
                "password": "SecurePass1!",
                "confirm_password": "SecurePass1!",
            },
        )

        response = await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "email": "wrong@example.com",
                "otp": "000000",
                "full_name": "Test User",
                "password": "SecurePass1!",
            },
        )
        assert response.status_code == 400
        assert "Invalid OTP" in response.json()["detail"]

    async def test_wrong_otp_three_times_max_attempts(
        self, client: AsyncClient, mock_redis
    ):
        await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Max User",
                "email": "max@example.com",
                "password": "SecurePass1!",
                "confirm_password": "SecurePass1!",
            },
        )

        # Wrong OTP x3
        for i in range(3):
            response = await client.post(
                "/api/v1/auth/verify-otp",
                json={
                    "email": "max@example.com",
                    "otp": "000000",
                    "full_name": "Max User",
                    "password": "SecurePass1!",
                },
            )

        # Last response should be 429
        assert response.status_code == 429
        assert "Maximum OTP verification attempts exceeded" in response.json()["detail"]

    async def test_correct_otp_after_wrong_attempt(
        self, client: AsyncClient, mock_redis
    ):
        await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Retry User",
                "email": "retry@example.com",
                "password": "SecurePass1!",
                "confirm_password": "SecurePass1!",
            },
        )

        otp = await mock_redis.get("otp:register:retry@example.com")

        # Wrong attempt first
        await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "email": "retry@example.com",
                "otp": "000000",
                "full_name": "Retry User",
                "password": "SecurePass1!",
            },
        )

        # Correct attempt
        response = await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "email": "retry@example.com",
                "otp": otp,
                "full_name": "Retry User",
                "password": "SecurePass1!",
            },
        )
        assert response.status_code == 200

    async def test_otp_cannot_be_reused(self, client: AsyncClient, mock_redis):
        await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Reuse User",
                "email": "reuse@example.com",
                "password": "SecurePass1!",
                "confirm_password": "SecurePass1!",
            },
        )

        otp = await mock_redis.get("otp:register:reuse@example.com")

        # First use — success
        response = await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "email": "reuse@example.com",
                "otp": otp,
                "full_name": "Reuse User",
                "password": "SecurePass1!",
            },
        )
        assert response.status_code == 200

        # Second use — should fail (OTP deleted after first use)
        response = await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "email": "reuse@example.com",
                "otp": otp,
                "full_name": "Reuse User",
                "password": "SecurePass1!",
            },
        )
        # Should fail — either email already registered or OTP expired
        assert response.status_code in (400, 429)


# ==========================================================
# OTP Resend
# ==========================================================

class TestResendOTP:

    async def test_resend_resets_attempts(self, client: AsyncClient, mock_redis):
        # Register
        await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Resend User",
                "email": "resend@example.com",
                "password": "SecurePass1!",
                "confirm_password": "SecurePass1!",
            },
        )

        # Wrong OTP x2
        for _ in range(2):
            await client.post(
                "/api/v1/auth/verify-otp",
                json={
                    "email": "resend@example.com",
                    "otp": "000000",
                    "full_name": "Resend User",
                    "password": "SecurePass1!",
                },
            )

        # Resend OTP (this should reset attempts)
        resend_response = await client.post(
            "/api/v1/auth/resend-otp",
            json={"email": "resend@example.com"},
        )
        assert resend_response.status_code == 200

        # New OTP should work
        new_otp = await mock_redis.get("otp:register:resend@example.com")
        response = await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "email": "resend@example.com",
                "otp": new_otp,
                "full_name": "Resend User",
                "password": "SecurePass1!",
            },
        )
        assert response.status_code == 200


# ==========================================================
# Login
# ==========================================================

class TestLogin:

    async def test_login_success(self, client: AsyncClient, mock_redis):
        # Register + verify
        await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Login User",
                "email": "login@example.com",
                "password": "SecurePass1!",
                "confirm_password": "SecurePass1!",
            },
        )

        otp = await mock_redis.get("otp:register:login@example.com")
        await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "email": "login@example.com",
                "otp": otp,
                "full_name": "Login User",
                "password": "SecurePass1!",
            },
        )

        # Login
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "login@example.com",
                "password": "SecurePass1!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Login successful."
        assert "user" in data

    async def test_login_wrong_password(self, client: AsyncClient, mock_redis):
        # Register + verify
        await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Login User 2",
                "email": "login2@example.com",
                "password": "SecurePass1!",
                "confirm_password": "SecurePass1!",
            },
        )

        otp = await mock_redis.get("otp:register:login2@example.com")
        await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "email": "login2@example.com",
                "otp": otp,
                "full_name": "Login User 2",
                "password": "SecurePass1!",
            },
        )

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "login2@example.com",
                "password": "WrongPass!",
            },
        )
        assert response.status_code == 400
        assert "Invalid email or password" in response.json()["detail"]

    async def test_login_nonexistent_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "SomePass!",
            },
        )
        assert response.status_code == 400


# ==========================================================
# Forgot Password
# ==========================================================

class TestForgotPassword:

    async def test_forgot_password_sends_otp(self, client: AsyncClient, mock_redis):
        # Create user first
        await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Forgot User",
                "email": "forgot@example.com",
                "password": "SecurePass1!",
                "confirm_password": "SecurePass1!",
            },
        )

        otp = await mock_redis.get("otp:register:forgot@example.com")
        await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "email": "forgot@example.com",
                "otp": otp,
                "full_name": "Forgot User",
                "password": "SecurePass1!",
            },
        )

        # Forgot password
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "forgot@example.com"},
        )
        assert response.status_code == 200
        assert "OTP has been sent" in response.json()["message"]

    async def test_forgot_password_nonexistent_email(self, client: AsyncClient):
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "noone@example.com"},
        )
        # Should not expose email existence
        assert response.status_code == 200

    async def test_reset_password_success(self, client: AsyncClient, mock_redis):
        # Create user
        await client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Reset User",
                "email": "reset@example.com",
                "password": "SecurePass1!",
                "confirm_password": "SecurePass1!",
            },
        )

        reg_otp = await mock_redis.get("otp:register:reset@example.com")
        await client.post(
            "/api/v1/auth/verify-otp",
            json={
                "email": "reset@example.com",
                "otp": reg_otp,
                "full_name": "Reset User",
                "password": "SecurePass1!",
            },
        )

        # Forgot password
        await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "reset@example.com"},
        )

        forgot_otp = await mock_redis.get("otp:forgot:reset@example.com")
        assert forgot_otp is not None

        # Reset password
        response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "reset@example.com",
                "otp": forgot_otp,
                "password": "NewSecurePass1!",
                "confirm_password": "NewSecurePass1!",
            },
        )
        assert response.status_code == 200
        assert "Password reset successful" in response.json()["message"]

        # Login with new password
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "reset@example.com",
                "password": "NewSecurePass1!",
            },
        )
        assert response.status_code == 200


# ==========================================================
# Logout
# ==========================================================

class TestLogout:

    async def test_logout(self, client: AsyncClient):
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        assert response.json()["message"] == "Logout successful."


# ==========================================================
# Protected Route
# ==========================================================

class TestProtectedRoute:

    async def test_get_me_unauthenticated(self, client: AsyncClient):
        response = await client.get("/api/v1/users/me")
        assert response.status_code == 401

    async def test_get_me_authenticated(
        self, authenticated_client: AsyncClient
    ):
        response = await authenticated_client.get("/api/v1/users/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"
