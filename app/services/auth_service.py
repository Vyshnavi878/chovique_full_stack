from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repository import UserRepository
from app.repositories.refresh_token_repository import RefreshTokenRepository

from app.schemas.auth import RegisterRequest, LoginRequest

from app.services.mail_service import MailService
from app.services.otp_service import OTPService
from app.services.google_service import GoogleService

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)

from app.core.config import settings


class AuthService:

    def __init__(self, db: AsyncSession):

        self.db = db

        self.user_repo = UserRepository(db)
        self.refresh_repo = RefreshTokenRepository(db)

        self.mail_service = MailService()
        self.otp_service = OTPService()
        self.google_service = GoogleService()


    # ======================================================
    # REGISTER
    # ======================================================

    async def register(
        self,
        request: RegisterRequest
    ):

        # Check password confirmation

        if request.password != request.confirm_password:
            raise ValueError(
                "Passwords do not match."
            )


        # Check existing user

        existing_user = await self.user_repo.get_by_email(
            request.email
        )

        if existing_user:
            raise ValueError(
                "Email already registered."
            )


        # Generate OTP

        otp = self.otp_service.generate_otp()


        # Save OTP

        await self.otp_service.save_otp(
            email=request.email,
            otp=otp,
            purpose="register",
        )


        # Send OTP mail

        await self.mail_service.send_registration_otp(
            email=request.email,
            otp=otp,
        )


        return {
            "message": "OTP sent successfully."
        }



    # ======================================================
    # VERIFY REGISTRATION OTP
    # ======================================================

    async def verify_registration_otp(
        self,
        email: str,
        otp: str,
        full_name: str,
        password: str,
    ):


        # Verify OTP

        is_valid = await self.otp_service.verify_otp(
            email=email,
            otp=otp,
            purpose="register",
        )


        if not is_valid:
            raise ValueError(
                "Invalid or expired OTP."
            )


        # Check user again

        existing_user = await self.user_repo.get_by_email(
            email
        )

        if existing_user:
            raise ValueError(
                "Email already registered."
            )


        # Hash password

        hashed_password = hash_password(
            password
        )


        # Create user

        user = await self.user_repo.create(
            full_name=full_name,
            email=email,
            hashed_password=hashed_password,
            role="customer",
            is_email_verified=True,
            is_active=True,
        )


        # Generate tokens

        access_token = create_access_token(
            str(user.id)
        )


        refresh_token, jti = create_refresh_token(
            str(user.id)
        )


        # Save refresh token

        expires_at = (
            datetime.now(timezone.utc)
            +
            timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        )


        await self.refresh_repo.create(
            user_id=user.id,
            jti=jti,
            hashed_token=hash_password(
                refresh_token
            ),
            expires_at=expires_at,
        )


        return {

            "message": "Registration successful.",

            "user": user,

            "access_token": access_token,

            "refresh_token": refresh_token,
        }
        # ======================================================
    # LOGIN
    # ======================================================

    async def login(
        self,
        request: LoginRequest
    ):

        # Find user

        user = await self.user_repo.get_by_email(
            request.email
        )


        if not user:
            raise ValueError(
                "Invalid email or password."
            )


        # Check active account

        if not user.is_active:
            raise ValueError(
                "Account is disabled."
            )


        # Google users don't have password

        if not user.hashed_password:

            raise ValueError(
                "Please login using Google."
            )


        # Verify password

        if not verify_password(
            request.password,
            user.hashed_password,
        ):

            raise ValueError(
                "Invalid email or password."
            )


        # Create tokens

        access_token = create_access_token(
            str(user.id)
        )


        refresh_token, jti = create_refresh_token(
            str(user.id)
        )


        # Save refresh token

        expires_at = (
            datetime.now(timezone.utc)
            +
            timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        )


        await self.refresh_repo.create(

            user_id=user.id,

            jti=jti,

            hashed_token=hash_password(
                refresh_token
            ),

            expires_at=expires_at,
        )


        # Update last login

        await self.user_repo.update_last_login(
            user.id,
            datetime.now(timezone.utc),
        )


        return {

            "message": "Login successful.",

            "user": user,

            "access_token": access_token,

            "refresh_token": refresh_token,
        }



    # ======================================================
    # GOOGLE LOGIN
    # ======================================================

    async def google_login(
        self,
        id_token: str
    ):


        # Verify Google token

        google_user = await self.google_service.verify_google_token(
            id_token
        )


        if not google_user:
            raise ValueError(
                "Invalid Google token."
            )


        # Find user

        user = await self.user_repo.get_by_email(
            google_user["email"]
        )


        # First time Google login

        if not user:


            user = await self.user_repo.create(

                full_name=google_user["full_name"],

                email=google_user["email"],

                hashed_password=None,

                google_id=google_user["google_id"],

                avatar_url=google_user["avatar_url"],

                role="customer",

                is_email_verified=True,

                is_active=True,
            )


        # Existing email user linking Google

        elif not user.google_id:


            await self.user_repo.update_google_data(

                user.id,

                google_id=google_user["google_id"],

                avatar_url=google_user["avatar_url"],

            )



        # Generate tokens


        access_token = create_access_token(
            str(user.id)
        )


        refresh_token, jti = create_refresh_token(
            str(user.id)
        )


        expires_at = (
            datetime.now(timezone.utc)
            +
            timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        )


        await self.refresh_repo.create(

            user_id=user.id,

            jti=jti,

            hashed_token=hash_password(
                refresh_token
            ),

            expires_at=expires_at,
        )


        await self.user_repo.update_last_login(
            user.id,
            datetime.now(timezone.utc),
        )


        return {

            "message": "Login successful.",

            "user": user,

            "access_token": access_token,

            "refresh_token": refresh_token,
        }




    # ======================================================
    # SET PASSWORD (GOOGLE USERS)
    # ======================================================

    async def set_password(

        self,

        user_id: str,

        password: str,

        confirm_password: str,

    ):


        user = await self.user_repo.get_by_id(
            user_id
        )


        if not user:
            raise ValueError(
                "User not found."
            )


        if password != confirm_password:

            raise ValueError(
                "Passwords do not match."
            )


        if user.hashed_password:

            raise ValueError(
                "Password already set."
            )


        hashed_password = hash_password(
            password
        )


        await self.user_repo.update_password(

            user.id,

            hashed_password

        )


        access_token = create_access_token(
            str(user.id)
        )


        refresh_token, jti = create_refresh_token(
            str(user.id)
        )


        expires_at = (
            datetime.now(timezone.utc)
            +
            timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        )


        await self.refresh_repo.create(

            user_id=user.id,

            jti=jti,

            hashed_token=hash_password(
                refresh_token
            ),

            expires_at=expires_at,
        )


        return {

            "message": "Password set successfully.",

            "user": user,

            "access_token": access_token,

            "refresh_token": refresh_token,
        }





    # ======================================================
    # FORGOT PASSWORD
    # ======================================================

    async def forgot_password(
        self,
        email: str
    ):


        user = await self.user_repo.get_by_email(
            email
        )


        # Don't expose email existence

        if not user:

            return {

                "message":
                "If email exists OTP has been sent."

            }



        otp = self.otp_service.generate_otp()


        await self.otp_service.save_otp(

            email=email,

            otp=otp,

            purpose="forgot",

        )


        await self.mail_service.send_forgot_password_otp(

            email=email,

            otp=otp,

        )


        return {

            "message":
            "If email exists OTP has been sent."

        }




    # ======================================================
    # RESET PASSWORD
    # ======================================================

    async def reset_password(

        self,

        email: str,

        otp: str,

        password: str,

        confirm_password: str,

    ):


        if password != confirm_password:

            raise ValueError(
                "Passwords do not match."
            )


        valid = await self.otp_service.verify_otp(

            email=email,

            otp=otp,

            purpose="forgot",

        )


        if not valid:

            raise ValueError(
                "Invalid or expired OTP."
            )



        user = await self.user_repo.get_by_email(
            email
        )


        if not user:

            raise ValueError(
                "User not found."
            )



        await self.user_repo.update_password(

            user.id,

            hash_password(password)

        )


        # Invalidate old sessions

        await self.refresh_repo.revoke_all_user_tokens(
            user.id
        )


        return {

            "message":
            "Password reset successful."

        }
        # ======================================================
    # CHANGE PASSWORD
    # ======================================================

    async def change_password(

        self,

        user_id: str,

        current_password: str,

        new_password: str,

        confirm_password: str,

    ):


        user = await self.user_repo.get_by_id(
            user_id
        )


        if not user:

            raise ValueError(
                "User not found."
            )


        # Google user without password

        if not user.hashed_password:

            raise ValueError(
                "Please set password first."
            )


        # Verify old password

        if not verify_password(

            current_password,

            user.hashed_password,

        ):

            raise ValueError(
                "Current password is incorrect."
            )


        if new_password != confirm_password:

            raise ValueError(
                "Passwords do not match."
            )


        # Update password

        await self.user_repo.update_password(

            user.id,

            hash_password(
                new_password
            )

        )


        # Logout all devices

        await self.refresh_repo.revoke_all_user_tokens(
            user.id
        )


        return {

            "message":
            "Password changed successfully."

        }




    # ======================================================
    # REFRESH TOKEN
    # ======================================================

    async def refresh_token(

        self,

        refresh_token: str,

    ):


        # Decode token

        payload = decode_token(
            refresh_token
        )


        if not payload:

            raise ValueError(
                "Invalid refresh token."
            )


        if payload.get("type") != "refresh":

            raise ValueError(
                "Invalid token type."
            )


        user_id = payload.get(
            "sub"
        )


        jti = payload.get(
            "jti"
        )


        if not user_id or not jti:

            raise ValueError(
                "Invalid token payload."
            )



        # Find token in DB

        db_token = await self.refresh_repo.get_by_jti(
            jti
        )


        if not db_token:

            raise ValueError(
                "Refresh token not found."
            )


        if db_token.revoked_at:

            raise ValueError(
                "Refresh token revoked."
            )


        if db_token.expires_at < datetime.now(
            timezone.utc
        ):

            raise ValueError(
                "Refresh token expired."
            )



        # Compare hashed token

        if not verify_password(

            refresh_token,

            db_token.hashed_token,

        ):

            raise ValueError(
                "Invalid refresh token."
            )



        # Create new tokens

        access_token = create_access_token(
            user_id
        )


        new_refresh_token, new_jti = create_refresh_token(
            user_id
        )


        expires_at = (
            datetime.now(timezone.utc)
            +
            timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )
        )



        # Revoke old refresh token

        await self.refresh_repo.revoke(
            jti
        )



        # Save new refresh token

        await self.refresh_repo.create(

            user_id=user_id,

            jti=new_jti,

            hashed_token=hash_password(
                new_refresh_token
            ),

            expires_at=expires_at,

        )



        return {

            "access_token":
            access_token,


            "refresh_token":
            new_refresh_token,

        }





    # ======================================================
    # LOGOUT
    # ======================================================

    async def logout(

        self,

        refresh_token: str,

    ):


        payload = decode_token(
            refresh_token
        )


        if payload:

            jti = payload.get(
                "jti"
            )


            if jti:

                await self.refresh_repo.revoke(
                    jti
                )



        return {

            "message":
            "Logout successful."

        }

        