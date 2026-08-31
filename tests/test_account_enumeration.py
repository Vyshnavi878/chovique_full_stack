"""
Unit and Integration Tests for Account Enumeration Defense (AUTH-002 Remediation).

Verifies:
1. Google OAuth-only accounts (with hashed_password=None) return standard "Invalid email or password." on POST /auth/login.
2. Non-existent accounts return standard "Invalid email or password." on POST /auth/login.
3. Incorrect password returns standard "Invalid email or password." on POST /auth/login.
4. Deactivated accounts with incorrect password do not leak deactivation status and return "Invalid email or password.".
5. Resending registration OTP for an already verified email returns generic success without leaking registration state.
6. Forgot password requests return identical generic messages for registered and unregistered emails.
7. Legitimate login with valid password succeeds normally (HTTP 200).
"""

import pytest
from httpx import AsyncClient
from app.repositories.user_repository import UserRepository
from app.core.security import hash_password

pytestmark = pytest.mark.asyncio


class TestAccountEnumerationDefense:

    async def test_oauth_user_password_login_returns_generic_error(self, client: AsyncClient, db_session):
        """Google OAuth user without password hash receives generic 'Invalid email or password.' on login."""
        # Create Google OAuth user (hashed_password=None)
        user_repo = UserRepository(db_session)
        await user_repo.create(
            full_name="OAuth User",
            email="oauth_only@example.com",
            hashed_password=None,
            google_id="google-123456",
            role="customer",
            is_email_verified=True,
            is_active=True,
        )

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "oauth_only@example.com",
                "password": "SomeRandomPassword1!",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid email or password."

    async def test_nonexistent_user_login_returns_generic_error(self, client: AsyncClient):
        """Non-existent user receives generic 'Invalid email or password.' on login."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent_user_987@example.com",
                "password": "SomePassword1!",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid email or password."

    async def test_wrong_password_returns_generic_error(self, client: AsyncClient, db_session):
        """Existing password user with incorrect password receives generic 'Invalid email or password.'."""
        user_repo = UserRepository(db_session)
        await user_repo.create(
            full_name="Standard User",
            email="standard_user@example.com",
            hashed_password=hash_password("CorrectPassword1!"),
            role="customer",
            is_email_verified=True,
            is_active=True,
        )

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "standard_user@example.com",
                "password": "WrongPassword1!",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid email or password."

    async def test_deactivated_user_with_wrong_password_does_not_leak_deactivation(self, client: AsyncClient, db_session):
        """Deactivated user with wrong password receives generic 'Invalid email or password.' (no deactivation leak)."""
        user_repo = UserRepository(db_session)
        await user_repo.create(
            full_name="Deactivated User",
            email="deactivated_user@example.com",
            hashed_password=hash_password("CorrectPassword1!"),
            role="customer",
            is_email_verified=True,
            is_active=False,
        )

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "deactivated_user@example.com",
                "password": "IncorrectPassword1!",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid email or password."

    async def test_resend_otp_for_verified_user_returns_generic_success(self, client: AsyncClient, db_session):
        """Resend OTP on verified email returns generic success response without disclosing registration state."""
        user_repo = UserRepository(db_session)
        await user_repo.create(
            full_name="Verified User",
            email="verified_registered@example.com",
            hashed_password=hash_password("Password123!"),
            role="customer",
            is_email_verified=True,
            is_active=True,
        )

        response = await client.post(
            "/api/v1/auth/resend-otp",
            json={"email": "verified_registered@example.com"},
        )
        assert response.status_code == 200
        assert response.json()["message"] == "OTP resent successfully."

    async def test_forgot_password_generic_response(self, client: AsyncClient, db_session):
        """Forgot password returns identical generic response for existing and non-existing accounts."""
        user_repo = UserRepository(db_session)
        await user_repo.create(
            full_name="Forgot User",
            email="forgot_existing@example.com",
            hashed_password=hash_password("Password123!"),
            role="customer",
            is_email_verified=True,
            is_active=True,
        )

        res_existing = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "forgot_existing@example.com"},
        )
        res_nonexisting = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "forgot_nonexisting@example.com"},
        )

        assert res_existing.status_code == 200
        assert res_nonexisting.status_code == 200
        assert res_existing.json()["message"] == "If email exists, OTP has been sent."
        assert res_nonexisting.json()["message"] == "If email exists, OTP has been sent."

    async def test_legitimate_login_success(self, client: AsyncClient, db_session):
        """Legitimate user with valid password logs in successfully (HTTP 200)."""
        user_repo = UserRepository(db_session)
        await user_repo.create(
            full_name="Valid User",
            email="valid_login_user@example.com",
            hashed_password=hash_password("CorrectPass1!"),
            role="customer",
            is_email_verified=True,
            is_active=True,
        )

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "valid_login_user@example.com",
                "password": "CorrectPass1!",
            },
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Login successful."
        assert response.json()["user"]["email"] == "valid_login_user@example.com"
        assert "access_token" in response.cookies
        assert "refresh_token" in response.cookies
