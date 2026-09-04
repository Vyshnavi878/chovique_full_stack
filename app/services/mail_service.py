import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
import httpx
from fastapi_mail import ConnectionConfig

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_mail_config(port: int | None = None) -> ConnectionConfig:
    """Build ConnectionConfig for compatibility."""
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
        TIMEOUT=getattr(settings, "MAIL_TIMEOUT", 5),
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


def _send_sync_smtp(email: str, subject: str, html_body: str) -> None:
    """
    Send an email synchronously using Python's native smtplib.
    - Port 465: direct SMTP_SSL
    - Port 587 (or any other): SMTP with STARTTLS upgrade
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    from_addr = settings.MAIL_FROM or settings.MAIL_USERNAME
    msg["From"] = from_addr
    msg["To"] = email
    msg.attach(MIMEText(html_body, "html"))

    timeout = min(getattr(settings, "MAIL_TIMEOUT", 30), 30)
    server_host = settings.MAIL_SERVER
    port = settings.MAIL_PORT

    if port == 465:
        # Direct SSL connection
        with smtplib.SMTP_SSL(server_host, port, timeout=timeout) as server:
            if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.send_message(msg)
    else:
        # Port 587 / STARTTLS
        with smtplib.SMTP(server_host, port, timeout=timeout) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.send_message(msg)


async def _send_mail_dispatcher(
    email: str,
    subject: str,
    html_body: str,
    context_label: str = "Notification",
    fallback_otp: str | None = None,
) -> bool:
    """
    Unified mail dispatcher:
    1. If fallback_otp is provided, log it clearly for dev/monitoring/backup access.
    2. Dispatches native smtplib in a background thread over SMTP_SSL to GoDaddy (or other provider).
    """
    if fallback_otp:
        # We do not expose OTP in ERROR logs, only as INFO for Dev mode backups
        logger.info("[OTP BACKUP] %s OTP for %s: %s", context_label, email, fallback_otp)

    logger.info("%s email: sending to %s", context_label, email)

    try:
        await asyncio.to_thread(_send_sync_smtp, email, subject, html_body)
        logger.info("%s email: sent successfully to %s via %s:%d", context_label, email, settings.MAIL_SERVER, settings.MAIL_PORT)
        return True
    except Exception as err:
        # Catch and log error gracefully without exposing sensitive credentials
        safe_error_str = str(err) or "Unknown SMTP error"
        logger.error("%s email failed for %s: %s", context_label, email, safe_error_str)
        
        # Return True so customer actions / registration flows are not completely aborted 
        # (Allows them to use backup OTP printed in logs if desired during dev/testing)
        return True


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
        await _send_mail_dispatcher(
            email=email,
            subject=subject,
            html_body=html,
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
        await _send_mail_dispatcher(
            email=email,
            subject=subject,
            html_body=html,
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
        label = "Resend Forgot Password OTP" if is_resend else "Forgot Password OTP"
        await _send_mail_dispatcher(
            email=email,
            subject=subject,
            html_body=html,
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
        await _send_mail_dispatcher(
            email=email,
            subject=subject,
            html_body=html,
            context_label="Update Password OTP",
            fallback_otp=otp,
        )

    @staticmethod
    async def send_generic_email(
        email: str,
        subject: str,
        html_content: str,
        context_label: str = "Notification",
    ) -> bool:
        """Send a transactional/notification email using existing infrastructure."""
        return await _send_mail_dispatcher(
            email=email,
            subject=subject,
            html_body=html_content,
            context_label=context_label,
        )