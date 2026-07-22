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
    ResetPasswordRequest,
    ChangePasswordRequest,
)
from fastapi import Cookie

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)



# ======================================================
# Cookie Helpers
# ======================================================

def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
):

    # Access Token Cookie

    response.set_cookie(

        key="access_token",

        value=access_token,

        httponly=True,

        secure=True,

        samesite="lax",

        max_age=60 * 15,

    )


    # Refresh Token Cookie

    response.set_cookie(

        key="refresh_token",

        value=refresh_token,

        httponly=True,

        secure=True,

        samesite="lax",

        max_age=60 * 60 * 24 * 7,

    )





# ======================================================
# REGISTER
# ======================================================

@router.post(
    "/register"
)
async def register(

    request: RegisterRequest,

    db: AsyncSession = Depends(get_db),

):

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
# VERIFY OTP
# ======================================================

@router.post(
    "/verify-otp"
)
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
            result["user"],

        }


    except ValueError as e:

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail=str(e)

        )





# ======================================================
# LOGIN
# ======================================================

@router.post(
    "/login"
)
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

            "user":
            result["user"],

        }


    except ValueError as e:

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail=str(e)

        )
# ======================================================
# GOOGLE LOGIN
# ======================================================

@router.post(
    "/google"
)
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
            result["user"],

        }


    except ValueError as e:

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail=str(e)

        )
# ======================================================
# SET PASSWORD
# ======================================================

@router.post(
    "/set-password"
)
async def set_password(

    request: SetPasswordRequest,

    response: Response,

    db: AsyncSession = Depends(get_db),

):

    try:

        service = AuthService(db)


        # user_id comes from access token middleware
        # for now coming from request

        result = await service.set_password(

            user_id=request.user_id,

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
            result["user"],

        }


    except ValueError as e:

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail=str(e)

        )
# ======================================================
# FORGOT PASSWORD
# ======================================================

@router.post(
    "/forgot-password"
)
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
# RESET PASSWORD
# ======================================================

@router.post(
    "/reset-password"
)
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


    except ValueError as e:

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail=str(e)

        )
# ======================================================
# CHANGE PASSWORD
# ======================================================

@router.post(
    "/change-password"
)
async def change_password(

    request: ChangePasswordRequest,

    db: AsyncSession = Depends(get_db),

):

    try:

        service = AuthService(db)


        result = await service.change_password(

            user_id=request.user_id,

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

@router.post(
    "/refresh"
)
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

@router.post(
    "/logout"
)
async def logout(

    response: Response,

    refresh_token: str | None = Cookie(
        default=None
    ),

    db: AsyncSession = Depends(get_db),

):


    try:

        service = AuthService(db)


        if refresh_token:

            await service.logout(
                refresh_token
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
