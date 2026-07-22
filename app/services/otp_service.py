import random

from app.core.config import settings
from app.db.redis import redis_client


class OTPService:

    REGISTER_PREFIX = "otp:register:"
    FORGOT_PREFIX = "otp:forgot:"
    ATTEMPT_PREFIX = "otp:attempt:"
    RESEND_PREFIX = "otp:resend:"

    # ======================================================
    # Generate OTP
    # ======================================================

    @staticmethod
    def generate_otp() -> str:
        return f"{random.randint(100000, 999999)}"

    # ======================================================
    # Save OTP
    # ======================================================

    @staticmethod
    async def save_otp(
        email: str,
        otp: str,
        purpose: str,
    ) -> None:

        prefix = (
            OTPService.REGISTER_PREFIX
            if purpose == "register"
            else OTPService.FORGOT_PREFIX
        )

        await redis_client.setex(
            f"{prefix}{email}",
            settings.OTP_EXPIRE_SECONDS,
            otp,
        )

    # ======================================================
    # Get OTP
    # ======================================================

    @staticmethod
    async def get_otp(
        email: str,
        purpose: str,
    ):

        prefix = (
            OTPService.REGISTER_PREFIX
            if purpose == "register"
            else OTPService.FORGOT_PREFIX
        )

        return await redis_client.get(f"{prefix}{email}")

    # ======================================================
    # Verify OTP
    # ======================================================

    @staticmethod
    async def verify_otp(
        email: str,
        otp: str,
        purpose: str,
    ) -> bool:

        stored_otp = await OTPService.get_otp(
            email,
            purpose,
        )

        if stored_otp is None:
            return False

        if stored_otp != otp:
            return False

        await OTPService.delete_otp(
            email,
            purpose,
        )

        return True

    # ======================================================
    # Delete OTP
    # ======================================================

    @staticmethod
    async def delete_otp(
        email: str,
        purpose: str,
    ) -> None:

        prefix = (
            OTPService.REGISTER_PREFIX
            if purpose == "register"
            else OTPService.FORGOT_PREFIX
        )

        await redis_client.delete(f"{prefix}{email}")

    # ======================================================
    # OTP Attempts
    # ======================================================

    @staticmethod
    async def increment_attempts(email: str) -> int:

        key = f"{OTPService.ATTEMPT_PREFIX}{email}"

        attempts = await redis_client.incr(key)

        await redis_client.expire(
            key,
            settings.OTP_EXPIRE_SECONDS,
        )

        return attempts

    @staticmethod
    async def reset_attempts(email: str) -> None:

        await redis_client.delete(
            f"{OTPService.ATTEMPT_PREFIX}{email}"
        )

    # ======================================================
    # Resend Cooldown
    # ======================================================

    @staticmethod
    async def start_resend_cooldown(email: str):

        await redis_client.setex(
            f"{OTPService.RESEND_PREFIX}{email}",
            60,
            "1",
        )

    @staticmethod
    async def can_resend(email: str) -> bool:

        value = await redis_client.get(
            f"{OTPService.RESEND_PREFIX}{email}"
        )

        return value is None