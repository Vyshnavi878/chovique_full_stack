import asyncio
import logging
from fastapi import HTTPException, status
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_mail_config(port: int | None = None) -> ConnectionConfig:
    """
    Build FastMail ConnectionConfig dynamically.
    Auto-adjusts SSL/TLS vs STARTTLS based on port if standard defaults are provided,
    and applies a short timeout so requests never block.
    """
    actual_port = port or settings.MAIL_PORT
    starttls = settings.MAIL_STARTTLS
    ssl_tls = settings.MAIL_SSL_TLS

    if actual_port == 465:
        ssl_tls = True
        starttls = False
    elif actual_port == 587:
        starttls = True
        ssl_tls = False

    return ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_PORT=actual_port,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_STARTTLS=starttls,
        MAIL_SSL_TLS=ssl_tls,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
        TIMEOUT=getattr(settings, "MAIL_TIMEOUT", 10),
    )


def _otp_expiry_minutes() -> int:
    """Return OTP validity in whole minutes."""
    return settings.OTP_EXPIRE_SECONDS // 60


def _build_otp_html(name: str, otp: str, heading: str, body_text: str, footer_note: str) -> str:
    """Render a consistent OTP email HTML body."""
    expiry_minutes = _otp_expiry_minutes()
    app_name = settings.APP_NAME
    return f"""
    <p>Hi <strong>{name}</strong>,</p>

    <p>{body_text}</p>

    <h2 style="letter-spacing: 6px; font-size: 2rem;">{otp}</h2>

    <p>This OTP is valid for <strong>{expiry_minutes} minutes</strong>. Please do not share this OTP with anyone.</p>

    <p>{footer_note}</p>

    <p>Thanks,<br/><strong>{app_name} Team</strong></p>
    """


async def _send_mail_with_fallback(
    message: MessageSchema,
    email: str,
    context_label: str,
    fallback_otp: str | None = None,
) -> None:
    """
    Attempt to send email via primary configured port (e.g. 587).
    If that fails or times out (e.g. Render port 587 restriction),
    automatically attempts fallback port (e.g. 465 with SSL/TLS).
    """
    timeout_seconds = getattr(settings, "MAIL_TIMEOUT", 10)
    primary_port = settings.MAIL_PORT

    # Attempt 1: primary port
    primary_conf = get_mail_config(primary_port)
    fm = FastMail(primary_conf)
    try:
        await asyncio.wait_for(fm.send_message(message), timeout=timeout_seconds)
        logger.info(f"{context_label} sent successfully to {email} via {primary_conf.MAIL_SERVER}:{primary_port}")
        return
    except Exception as primary_err:
        logger.warning(
            f"{context_label} attempt on {primary_conf.MAIL_SERVER}:{primary_port} failed ({primary_err}). "
            f"Attempting fallback port..."
        )

    # Attempt 2: fallback port (465 SSL if 587, or 587 STARTTLS if 465)
    fallback_port = 465 if primary_port == 587 else (587 if primary_port == 465 else None)
    if fallback_port:
        try:
            fallback_conf = get_mail_config(fallback_port)
            fm_fallback = FastMail(fallback_conf)
            await asyncio.wait_for(fm_fallback.send_message(message), timeout=timeout_seconds)
            logger.info(f"{context_label} sent successfully to {email} via fallback {fallback_conf.MAIL_SERVER}:{fallback_port}")
            return
        except Exception as fallback_err:
            logger.error(
                f"{context_label} fallback on {primary_conf.MAIL_SERVER}:{fallback_port} failed ({fallback_err})."
            )

    # If all attempts fail
    logger.error(
        f"All SMTP delivery attempts failed for {email} via {primary_conf.MAIL_SERVER}:{primary_port}. "
        f"Please verify Render MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, and MAIL_PASSWORD environment variables."
    )

    if settings.DEBUG:
        if fallback_otp:
            print(f"\n==========================================")
            print(f"[DEV MODE - MAIL FAILED] {context_label} for {email}: {fallback_otp}")
            print(f"==========================================\n")
        return

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Unable to deliver verification email. Please verify SMTP configuration or try again later.",
    )


class MailService:

    @staticmethod
    async def send_registration_otp(
        email: str,
        otp: str,
        name: str = "",
    ) -> None:
        """Send OTP for new account email verification."""
        display_name = name.strip() or email.split("@")[0]
        subject = "Verify Your Email Address"
        html = _build_otp_html(
            name=display_name,
            otp=otp,
            heading="Email Verification",
            body_text="Your OTP for verifying your email address is:",
            footer_note="If you did not request this OTP, please ignore this email.",
        )
        message = MessageSchema(
            subject=subject,
            recipients=[email],
            body=html,
            subtype=MessageType.html,
        )
        await _send_mail_with_fallback(
            message=message,
            email=email,
            context_label="Registration OTP",
            fallback_otp=otp,
        )

    @staticmethod
    async def send_resend_registration_otp(
        email: str,
        otp: str,
        name: str = "",
    ) -> None:
        """Send a new OTP when the user requests a resend during registration."""
        display_name = name.strip() or email.split("@")[0]
        subject = "Your New Verification OTP"
        html = _build_otp_html(
            name=display_name,
            otp=otp,
            heading="Resend Verification OTP",
            body_text="Here is your new verification OTP:",
            footer_note="If you did not request this OTP, please ignore this email.",
        )
        message = MessageSchema(
            subject=subject,
            recipients=[email],
            body=html,
            subtype=MessageType.html,
        )
        await _send_mail_with_fallback(
            message=message,
            email=email,
            context_label="Resend Registration OTP",
            fallback_otp=otp,
        )

    @staticmethod
    async def send_forgot_password_otp(
        email: str,
        otp: str,
        name: str = "",
        is_resend: bool = False,
    ) -> None:
        """Send OTP for password reset. Set is_resend=True for resend requests."""
        display_name = name.strip() or email.split("@")[0]

        if is_resend:
            subject = "Your New Password Reset OTP"
            body_text = "Here is your new OTP to reset your password:"
        else:
            subject = "Reset Your Password"
            body_text = "Your OTP to reset your password is:"

        html = _build_otp_html(
            name=display_name,
            otp=otp,
            heading="Password Reset OTP",
            body_text=body_text,
            footer_note="If you did not request a password reset, please ignore this email.",
        )
        message = MessageSchema(
            subject=subject,
            recipients=[email],
            body=html,
            subtype=MessageType.html,
        )
        label = "Resend Forgot Password OTP" if is_resend else "Forgot Password OTP"
        await _send_mail_with_fallback(
            message=message,
            email=email,
            context_label=label,
            fallback_otp=otp,
        )

    @staticmethod
    async def send_update_password_otp(
        email: str,
        otp: str,
        name: str = "",
    ) -> None:
        """Send OTP for authenticated password update."""
        display_name = name.strip() or email.split("@")[0]
        subject = "Update Your Password"
        body_text = "Your OTP to update your password is:"

        html = _build_otp_html(
            name=display_name,
            otp=otp,
            heading="Update Password OTP",
            body_text=body_text,
            footer_note="If you did not request a password update, please secure your account.",
        )
        message = MessageSchema(
            subject=subject,
            recipients=[email],
            body=html,
            subtype=MessageType.html,
        )
        await _send_mail_with_fallback(
            message=message,
            email=email,
            context_label="Update Password OTP",
            fallback_otp=otp,
        )

    @staticmethod
    async def send_generic_email(
        email: str,
        subject: str,
        html_content: str,
    ) -> bool:
        """Send a transactional/notification email using existing SMTP configuration."""
        message = MessageSchema(
            subject=subject,
            recipients=[email],
            body=html_content,
            subtype=MessageType.html,
        )
        timeout_seconds = getattr(settings, "MAIL_TIMEOUT", 10)
        primary_port = settings.MAIL_PORT

        # 1. Primary port
        primary_conf = get_mail_config(primary_port)
        fm = FastMail(primary_conf)
        try:
            await asyncio.wait_for(fm.send_message(message), timeout=timeout_seconds)
            logger.info(f"SMTP notification email sent successfully to {email} | Subject: {subject}")
            return True
        except Exception as primary_err:
            logger.warning(
                f"SMTP notification failed on {primary_conf.MAIL_SERVER}:{primary_port} ({primary_err}). "
                f"Attempting fallback port..."
            )

        # 2. Fallback port
        fallback_port = 465 if primary_port == 587 else (587 if primary_port == 465 else None)
        if fallback_port:
            try:
                fallback_conf = get_mail_config(fallback_port)
                fm_fallback = FastMail(fallback_conf)
                await asyncio.wait_for(fm_fallback.send_message(message), timeout=timeout_seconds)
                logger.info(f"SMTP notification sent successfully to {email} via fallback port {fallback_port}")
                return True
            except Exception as fallback_err:
                logger.error(
                    f"SMTP notification fallback failed on {primary_conf.MAIL_SERVER}:{fallback_port} for {email}: {fallback_err}"
                )

        if settings.DEBUG:
            print(f"\n==========================================")
            print(f"[DEV MODE - SMTP FAILED] Email to {email} | Subject: {subject}")
            print(f"==========================================\n")
        return False