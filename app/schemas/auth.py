from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ==========================================================
# Register
# ==========================================================

class RegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str


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
    user_id: str
    password: str = Field(..., min_length=8)
    confirm_password: str


# ==========================================================
# Forgot Password
# ==========================================================

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


# ==========================================================
# Verify Forgot Password OTP
# ==========================================================

class VerifyForgotPasswordOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)


# ==========================================================
# Reset Password
# ==========================================================

class ResetPasswordRequest(BaseModel):
    email: EmailStr
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
# User Response
# ==========================================================

class UserResponse(BaseModel):
    id: str
    full_name: str
    email: EmailStr
    role: str
    is_email_verified: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)