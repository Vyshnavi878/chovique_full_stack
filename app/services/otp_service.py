import logging
import secrets

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
    UPDATE_PASSWORD_PREFIX = "otp:update_password:"
    VERIFIED_PREFIX = "otp:verified:"
    ATTEMPT_PREFIX = "otp:attempt:"
    RESEND_PREFIX = "otp:resend:"

    @staticmethod
    def _get_prefix(purpose: str) -> str:
        if purpose == "register":
            return OTPService.REGISTER_PREFIX
        if purpose == "update_password":
            return OTPService.UPDATE_PASSWORD_PREFIX
        return OTPService.FORGOT_PREFIX

    # ======================================================
    # Generate OTP
    # ======================================================

    @staticmethod
    def generate_otp() -> str:
        return f"{secrets.randbelow(900000) + 100000}"

    # ======================================================
    # Save OTP
    # ======================================================

    @staticmethod
    async def save_otp(
        email: str,
        otp: str,
        purpose: str,
    ) -> None:

        prefix = OTPService._get_prefix(purpose)

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

        prefix = OTPService._get_prefix(purpose)

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

        prefix = OTPService._get_prefix(purpose)

        await redis_client.delete(f"{prefix}{email}")

    # ======================================================
    # Verified State
    # ======================================================

    @staticmethod
    async def mark_otp_verified(email: str, purpose: str) -> None:
        # Keep the verified state for 10 minutes
        await redis_client.setex(
            f"{OTPService.VERIFIED_PREFIX}{purpose}:{email}",
            600,
            "1"
        )

    @staticmethod
    async def is_otp_verified(email: str, purpose: str) -> bool:
        key = f"{OTPService.VERIFIED_PREFIX}{purpose}:{email}"
        val = await redis_client.get(key)
        if val:
            await redis_client.delete(key)
            return True
        return False

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

    RESEND_COUNT_PREFIX = "otp:resend_count:"
    RESEND_LOCK_PREFIX = "otp:resend_lock:"

    # ======================================================
    # Resend Limits & Cooldown
    # ======================================================

    @staticmethod
    async def check_resend_limit(email: str, purpose: str = "") -> None:
        """
        Check if the email has hit resend rate limit or lockout.
        Raises HTTPException(429) if locked or in cooldown.
        """
        from fastapi import HTTPException, status

        # Check 1: Check lockout key
        lock_key = f"{OTPService.RESEND_LOCK_PREFIX}{purpose}:{email}"
        lock_ttl = await redis_client.ttl(lock_key)

        if lock_ttl > 0:
            minutes = max(1, (lock_ttl + 59) // 60)
            if minutes > 1:
                detail = f"You have reached the maximum OTP resend limit. Please try again after {minutes} minutes."
            else:
                detail = "You have reached the maximum OTP resend limit. Please try again after 1 minute."
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=detail,
            )

        # Check 2: Check short cooldown key (60 seconds)
        resend_key = f"{OTPService.RESEND_PREFIX}{purpose}:{email}"
        cooldown_ttl = await redis_client.ttl(resend_key)
        if cooldown_ttl > 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {cooldown_ttl} seconds before requesting another OTP.",
            )

    @staticmethod
    async def record_resend(email: str, purpose: str = "") -> None:
        """
        Record an OTP resend action. Sets 60s cooldown and tracks resend count.
        If resend count >= MAX_OTP_RESEND_ATTEMPTS, sets lockout key for OTP_RESEND_LOCKOUT_SECONDS.
        """
        count_key = f"{OTPService.RESEND_COUNT_PREFIX}{purpose}:{email}"
        resend_key = f"{OTPService.RESEND_PREFIX}{purpose}:{email}"
        lock_key = f"{OTPService.RESEND_LOCK_PREFIX}{purpose}:{email}"

        resend_count = await redis_client.incr(count_key)
        if resend_count == 1:
            await redis_client.expire(count_key, settings.OTP_RESEND_LOCKOUT_SECONDS)

        await redis_client.setex(resend_key, 60, "1")

        if resend_count >= settings.MAX_OTP_RESEND_ATTEMPTS:
            await redis_client.setex(lock_key, settings.OTP_RESEND_LOCKOUT_SECONDS, "1")

    @staticmethod
    async def start_resend_cooldown(email: str):

        await redis_client.setex(
            f"{OTPService.RESEND_PREFIX}:{email}",
            60,
            "1",
        )

    @staticmethod
    async def can_resend(email: str) -> bool:

        value = await redis_client.get(
            f"{OTPService.RESEND_PREFIX}:{email}"
        )

        return value is None