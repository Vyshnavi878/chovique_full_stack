import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
import httpx
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


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


def _send_sync_smtp(email: str, subject: str, html_body: str, port: int) -> None:
    """
    Send an email synchronously using Python's native smtplib socket implementation.
    This avoids uvloop/aiosmtplib event-loop bugs on Linux/Render.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    from_addr = settings.MAIL_FROM or settings.MAIL_USERNAME
    msg["From"] = from_addr
    msg["To"] = email
    msg.attach(MIMEText(html_body, "html"))

    timeout = getattr(settings, "MAIL_TIMEOUT", 10)
    server_host = settings.MAIL_SERVER

    if port == 465:
        with smtplib.SMTP_SSL(server_host, port, timeout=timeout) as server:
            if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.send_message(msg)
    else:
        with smtplib.SMTP(server_host, port, timeout=timeout) as server:
            server.ehlo()
            if getattr(settings, "MAIL_STARTTLS", True):
                server.starttls()
                server.ehlo()
            if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.send_message(msg)


async def _send_mail_dispatcher(
    email: str,
    subject: str,
    html_body: str,
    context_label: str,
    fallback_otp: str | None = None,
) -> bool:
    """
    Unified mail dispatcher:
    1. Attempts Resend HTTP REST API if RESEND_API_KEY is configured (HTTPS port 443).
    2. Dispatches native smtplib in a background thread to primary SMTP port (e.g. 587 or 465).
    3. Retries on fallback SMTP port (465 SSL or 587 STARTTLS) if primary fails.
    """
    # 1. Resend HTTPS REST API (Port 443, never blocked by cloud firewalls)
    resend_api_key = getattr(settings, "RESEND_API_KEY", None)
    if resend_api_key and resend_api_key.strip():
        try:
            from_email = settings.MAIL_FROM or "Chovique Chocolatier <onboarding@resend.dev>"
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {resend_api_key.strip()}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": from_email,
                        "to": [email],
                        "subject": subject,
                        "html": html_body,
                    },
                )
                if resp.is_success:
                    logger.info(f"{context_label} delivered successfully to {email} via Resend API")
                    return True
                else:
                    logger.warning(
                        f"Resend API returned {resp.status_code}: {resp.text}. Falling back to SMTP..."
                    )
        except Exception as resend_err:
            logger.warning(
                f"Resend API request failed for {email} ({resend_err}). Falling back to SMTP..."
            )

    # 2. Native SMTP via background thread (Primary Port)
    primary_port = settings.MAIL_PORT
    try:
        await asyncio.to_thread(_send_sync_smtp, email, subject, html_body, primary_port)
        logger.info(f"{context_label} delivered successfully to {email} via {settings.MAIL_SERVER}:{primary_port}")
        return True
    except Exception as primary_err:
        logger.warning(
            f"{context_label} delivery via {settings.MAIL_SERVER}:{primary_port} failed ({primary_err}). "
            f"Attempting fallback port..."
        )

    # 3. Native SMTP via background thread (Fallback Port 465 <-> 587)
    fallback_port = 465 if primary_port == 587 else (587 if primary_port == 465 else None)
    if fallback_port:
        try:
            await asyncio.to_thread(_send_sync_smtp, email, subject, html_body, fallback_port)
            logger.info(
                f"{context_label} delivered successfully to {email} via fallback {settings.MAIL_SERVER}:{fallback_port}"
            )
            return True
        except Exception as fallback_err:
            logger.error(
                f"{context_label} delivery via fallback {settings.MAIL_SERVER}:{fallback_port} failed ({fallback_err})."
            )

    logger.error(
        f"All email delivery attempts failed for {email}. "
        f"Please verify Render MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, and MAIL_PASSWORD environment variables."
    )

    if settings.DEBUG:
        if fallback_otp:
            print(f"\n==========================================")
            print(f"[DEV MODE - MAIL FAILED] {context_label} for {email}: {fallback_otp}")
            print(f"==========================================\n")
        return True

    return False


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
        success = await _send_mail_dispatcher(
            email=email,
            subject=subject,
            html_body=html,
            context_label="Registration OTP",
            fallback_otp=otp,
        )
        if not success and not settings.DEBUG:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to deliver verification email. Please verify SMTP configuration or try again later.",
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
        success = await _send_mail_dispatcher(
            email=email,
            subject=subject,
            html_body=html,
            context_label="Resend Registration OTP",
            fallback_otp=otp,
        )
        if not success and not settings.DEBUG:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to deliver verification email. Please verify SMTP configuration or try again later.",
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
        success = await _send_mail_dispatcher(
            email=email,
            subject=subject,
            html_body=html,
            context_label=label,
            fallback_otp=otp,
        )
        if not success and not settings.DEBUG:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to deliver password reset email. Please verify SMTP configuration or try again later.",
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
        success = await _send_mail_dispatcher(
            email=email,
            subject=subject,
            html_body=html,
            context_label="Update Password OTP",
            fallback_otp=otp,
        )
        if not success and not settings.DEBUG:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to deliver verification email. Please verify SMTP configuration or try again later.",
            )

    @staticmethod
    async def send_generic_email(
        email: str,
        subject: str,
        html_content: str,
    ) -> bool:
        """Send a transactional/notification email using existing infrastructure."""
        return await _send_mail_dispatcher(
            email=email,
            subject=subject,
            html_body=html_content,
            context_label="Notification Email",
        )