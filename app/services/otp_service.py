import logging
import random

from app.core.config import settings
from app.core.exceptions import (
    InvalidOTPError,
    MaxAttemptsExceededError,
    OTPExpiredError,
)
from app.db.redis import redis_client

logger = logging.getLogger(__name__)


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

        # Save new OTP with expiry
        await redis_client.setex(
            f"{prefix}{email}",
            settings.OTP_EXPIRE_SECONDS,
            otp,
        )

        # Reset attempts counter when a new OTP is generated
        # This ensures resend resets attempts back to 0
        await OTPService.reset_attempts(email, purpose)

        logger.info(
            "OTP saved for %s (purpose=%s, expires=%ds)",
            email,
            purpose,
            settings.OTP_EXPIRE_SECONDS,
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
        """
        Verify OTP with attempts tracking.

        Raises:
            MaxAttemptsExceededError: When max attempts (3) are reached.
            OTPExpiredError: When the OTP has expired or doesn't exist.
            InvalidOTPError: When the OTP code is incorrect.

        Returns:
            True if OTP is valid.
        """

        max_attempts = settings.MAX_OTP_ATTEMPTS

        # Step 1: Check if already exceeded attempts
        current_attempts = await OTPService.get_attempts(email, purpose)

        if current_attempts >= max_attempts:
            # Invalidate any remaining OTP
            await OTPService.delete_otp(email, purpose)
            logger.warning(
                "OTP max attempts already exceeded for %s (purpose=%s)",
                email,
                purpose,
            )
            raise MaxAttemptsExceededError()

        # Step 2: Get the stored OTP
        stored_otp = await OTPService.get_otp(email, purpose)

        # Step 3: OTP expired or not found
        if stored_otp is None:
            # Increment attempts atomically — expired counts as an attempt
            new_attempts = await OTPService.increment_attempts(email, purpose)
            remaining = max(0, max_attempts - new_attempts)

            logger.info(
                "OTP expired/not found for %s (purpose=%s, attempts=%d/%d)",
                email,
                purpose,
                new_attempts,
                max_attempts,
            )

            if new_attempts >= max_attempts:
                raise MaxAttemptsExceededError()

            raise OTPExpiredError(remaining_attempts=remaining)

        # Step 4: OTP doesn't match
        if stored_otp != otp:
            # Increment attempts atomically
            new_attempts = await OTPService.increment_attempts(email, purpose)
            remaining = max(0, max_attempts - new_attempts)

            logger.info(
                "Invalid OTP for %s (purpose=%s, attempts=%d/%d)",
                email,
                purpose,
                new_attempts,
                max_attempts,
            )

            if new_attempts >= max_attempts:
                # Invalidate the OTP since max attempts reached
                await OTPService.delete_otp(email, purpose)
                raise MaxAttemptsExceededError()

            raise InvalidOTPError(remaining_attempts=remaining)

        # Step 5: OTP is valid
        # Delete OTP so it cannot be reused
        await OTPService.delete_otp(email, purpose)

        # Reset attempts on success
        await OTPService.reset_attempts(email, purpose)

        logger.info(
            "OTP verified successfully for %s (purpose=%s)",
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
    async def get_attempts(email: str, purpose: str = "") -> int:
        """Get current attempt count for an email+purpose combination."""

        key = f"{OTPService.ATTEMPT_PREFIX}{purpose}:{email}"
        value = await redis_client.get(key)

        return int(value) if value else 0

    @staticmethod
    async def increment_attempts(email: str, purpose: str = "") -> int:
        """
        Atomically increment attempts counter.

        Redis INCR is atomic (single-threaded), so concurrent requests
        cannot bypass the limit.
        """

        key = f"{OTPService.ATTEMPT_PREFIX}{purpose}:{email}"

        attempts = await redis_client.incr(key)

        # Set expiry on the counter so it auto-resets
        await redis_client.expire(
            key,
            settings.OTP_EXPIRE_SECONDS,
        )

        return attempts

    @staticmethod
    async def reset_attempts(email: str, purpose: str = "") -> None:
        """Reset attempts counter to 0."""

        key = f"{OTPService.ATTEMPT_PREFIX}{purpose}:{email}"

        await redis_client.delete(key)

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