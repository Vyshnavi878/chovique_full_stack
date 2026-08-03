import logging

from fastapi import (
    APIRouter,
    Depends,
    Response,
    HTTPException,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import (
    RegisterRequest,
    VerifyOTPRequest,
    LoginRequest,
    GoogleLoginRequest,
    SetPasswordRequest,
    ForgotPasswordRequest,
    ResendOTPRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    ResendForgotOTPRequest,
    OTPSentResponse,
    AuthUserResponse,
)
from app.schemas.token import MessageResponse
from app.schemas.user import UserResponse
from app.api.deps import get_current_user_id, _extract_token
from app.middleware.rate_limit_middleware import RateLimiter
from app.core.config import settings
from app.core.exceptions import (
    InvalidOTPError,
    MaxAttemptsExceededError,
    OTPExpiredError,
)
from fastapi import Cookie, Header

logger = logging.getLogger(__name__)

router = APIRouter( prefix="/auth", tags=["Authentication"])


# ======================================================
# OTP Exception Handler Helper
# ======================================================

def _handle_otp_exception(e: Exception):
    """Convert OTP exceptions to appropriate HTTP errors."""

    if isinstance(e, MaxAttemptsExceededError):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=e.message,
        )

    if isinstance(e, OTPExpiredError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )

    if isinstance(e, InvalidOTPError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


# ======================================================
# Cookie Helpers
# ======================================================

def set_auth_cookies( response: Response, access_token: str, refresh_token: str,):

    # Access Token Cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=60 * settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    # Refresh Token Cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=60 * 60 * 24 * settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )


# ======================================================
# REGISTER
# ======================================================

@router.post("/register", response_model=OTPSentResponse)
async def register( request: RegisterRequest, db: AsyncSession = Depends(get_db),):

    try:
        service = AuthService(db)
        return await service.register(
            request
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# ======================================================
# RESEND OTP (Registration)
# ======================================================

@router.post( "/resend-otp", response_model=OTPSentResponse)
async def resend_otp(
    request: ResendOTPRequest,
    db: AsyncSession = Depends(get_db),
):

    try:
        service = AuthService(db)
        return await service.resend_otp(
            request.email
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# ======================================================
# VERIFY OTP (Registration)
# ======================================================

@router.post( "/verify-otp", response_model=AuthUserResponse)
async def verify_otp(
    request: VerifyOTPRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        service = AuthService(db)
        result = await service.verify_registration_otp(
            email=request.email,
            otp=request.otp,
            full_name=request.full_name,
            password=request.password,
        )
        # Set JWT Cookies
        set_auth_cookies(
            response,
            result["access_token"],
            result["refresh_token"],
        )

        return {
            "message":
            result["message"],
            "user":
            UserResponse.from_orm_user(result["user"]),
        }
    except (InvalidOTPError, OTPExpiredError, MaxAttemptsExceededError) as e:
        _handle_otp_exception(e)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ======================================================
# LOGIN
# ======================================================

@router.post("/login", response_model=AuthUserResponse, dependencies=[Depends(RateLimiter(times=5, seconds=60))])
async def login(
    request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):

    try:
        service = AuthService(db)
        result = await service.login(
            request
        )
        # Set JWT Cookies
        set_auth_cookies(
            response,
            result["access_token"],
            result["refresh_token"],
        )
        return {
            "message":
            result["message"],
            "user": UserResponse.from_orm_user(result["user"]),
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# ======================================================
# GOOGLE LOGIN
# ======================================================

@router.post("/google", summary="Google OAuth login / registration", response_model=AuthUserResponse)
async def google_login(
    request: GoogleLoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):

    try:
        service = AuthService(db)
        result = await service.google_login(
            request.id_token
        )
        set_auth_cookies(
            response,
            result["access_token"],
            result["refresh_token"],
        )
        return {
            "message":
            result["message"],
            "user":
            UserResponse.from_orm_user(result["user"]),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# ======================================================
# SET PASSWORD
# ======================================================

@router.post("/set-password", response_model=AuthUserResponse)
async def set_password(
    request: SetPasswordRequest,
    response: Response,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):

    try:
        service = AuthService(db)
        result = await service.set_password(
            user_id=user_id,
            password=request.password,
            confirm_password=request.confirm_password,
        )
        set_auth_cookies(
            response,
            result["access_token"],
            result["refresh_token"],
        )
        return {
            "message":
            result["message"],
            "user":
            UserResponse.from_orm_user(result["user"]),
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# ======================================================
# FORGOT PASSWORD
# ======================================================

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):

    try:
        service = AuthService(db)
        return await service.forgot_password(
            request.email
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ======================================================
# RESEND FORGOT PASSWORD OTP
# ======================================================

@router.post("/resend-forgot-otp", response_model=MessageResponse)
async def resend_forgot_password_otp(
    request: ResendForgotOTPRequest,
    db: AsyncSession = Depends(get_db),
):

    try:
        service = AuthService(db)
        return await service.resend_forgot_password_otp(
            email=request.email,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# ======================================================
# RESET PASSWORD
# ======================================================

@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):

    try:
        service = AuthService(db)
        return await service.reset_password(
            email=request.email,
            otp=request.otp,
            password=request.password,
            confirm_password=request.confirm_password,
        )
    except (InvalidOTPError, OTPExpiredError, MaxAttemptsExceededError) as e:
        _handle_otp_exception(e)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# ======================================================
# CHANGE PASSWORD
# ======================================================

@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):

    try:
        service = AuthService(db)
        result = await service.change_password(
            user_id=user_id,
            current_password=request.current_password,
            new_password=request.new_password,
            confirm_password=request.confirm_password,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# ======================================================
# REFRESH TOKEN
# ======================================================

@router.post("/refresh", response_model=MessageResponse)
async def refresh_token(
    response: Response,
    refresh_token: str | None = Cookie(
        default=None
    ),
    db: AsyncSession = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing."
        )
    try:
        service = AuthService(db)
        result = await service.refresh_token(
            refresh_token
        )
        # Replace old cookies
        set_auth_cookies(
            response,
            result["access_token"],
            result["refresh_token"],
        )
        return {
            "message":
            "Token refreshed successfully."
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

# ======================================================
# LOGOUT
# ======================================================

@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(
        default=None
    ),
    access_token: str | None = Cookie(
        default=None
    ),
    authorization: str | None = Header(
        default=None
    ),
    db: AsyncSession = Depends(get_db),
):
    try:
        service = AuthService(db)
        extracted_access_token = _extract_token(access_token, authorization)

        await service.logout(
            refresh_token=refresh_token,
            access_token=extracted_access_token
        )
        # Delete cookies
        response.delete_cookie(
            key="access_token"
        )
        response.delete_cookie(
            key="refresh_token"
        )
        return {
            "message":
            "Logout successful."
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )