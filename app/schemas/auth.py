from pydantic import BaseModel, EmailStr, Field, field_validator
import re

from app.schemas.user import UserResponse


# ==========================================================
# Register
# ==========================================================

PASSWORD_POLICY_ERROR = (
    "Password must be at least 8 characters and include at least one uppercase letter, "
    "one lowercase letter, one number, and one special character."
)


class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if (
            len(v) < 8
            or not re.search(r"[A-Z]", v)
            or not re.search(r"[a-z]", v)
            or not re.search(r"[0-9]", v)
            or not re.search(r"[^A-Za-z0-9]", v)
        ):
            raise ValueError(PASSWORD_POLICY_ERROR)
        return v


# ==========================================================
# Verify Registration OTP
# ==========================================================

class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    full_name: str = Field(..., min_length=2, max_length=120)
    password: str = Field(..., min_length=8, max_length=128)


VerifyRegistrationOTPRequest = VerifyOTPRequest


# ==========================================================
# Login
# ==========================================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ==========================================================
# Google Login
# ==========================================================

class GoogleLoginRequest(BaseModel):
    id_token: str


# ==========================================================
# Set Password
# ==========================================================

class SetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=8)
    confirm_password: str


# ==========================================================
# Forgot Password
# ==========================================================

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


# ==========================================================
# Resend Registration OTP
# ==========================================================

class ResendOTPRequest(BaseModel):
    email: EmailStr



# ==========================================================
# Resend Forgot Password OTP
# ==========================================================

class ResendForgotOTPRequest(BaseModel):
    email: EmailStr


# ==========================================================
# Reset Password
# ==========================================================

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)
    password: str = Field(..., min_length=8)
    confirm_password: str


# ==========================================================
# Change Password
# ==========================================================

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    confirm_password: str


# ==========================================================
# Response Wrappers
# ==========================================================
# These describe the exact JSON shape the auth endpoints return,
# so FastAPI validates the response and Swagger shows accurate
# request/response schemas instead of "any" objects.

class OTPSentResponse(BaseModel):
    """Response for register / resend-otp (no user object yet)."""
    message: str
    email: EmailStr
    expires_in: int


class AuthUserResponse(BaseModel):
    """Response for endpoints that return a token pair + user profile
    (verify-otp, login, google, set-password)."""
    message: str
    user: UserResponse