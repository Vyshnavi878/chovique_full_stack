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

    timeout = min(getattr(settings, "MAIL_TIMEOUT", 3), 3)
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
    context_label: str = "Notification",
    fallback_otp: str | None = None,
) -> bool:
    """
    Unified mail dispatcher:
    1. If fallback_otp is provided, log it clearly for dev/monitoring/backup access.
    2. Attempts Resend HTTP REST API if RESEND_API_KEY is configured (HTTPS port 443).
    3. Dispatches native smtplib in a background thread to primary SMTP port (e.g. 587 or 465).
    4. Retries on fallback SMTP port (465 SSL or 587 STARTTLS) if primary fails.
    5. Gracefully handles cloud network blocks (e.g. Render blocking SMTP ports) so the user flow is preserved.
    """
    if fallback_otp:
        logger.info("[OTP BACKUP] %s OTP for %s: %s", context_label, email, fallback_otp)

    logger.info("%s email: sending to %s", context_label, email)

    # 1. Resend HTTPS REST API (Port 443, never blocked by cloud firewalls)
    resend_api_key = getattr(settings, "RESEND_API_KEY", None)
    if resend_api_key and resend_api_key.strip():
        try:
            from_email = settings.MAIL_FROM or "Chovique Chocolatier <onboarding@resend.dev>"
            async with httpx.AsyncClient(timeout=4.0) as client:
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
                    logger.info("%s email: sent successfully to %s via Resend API", context_label, email)
                    return True
                else:
                    logger.warning(
                        "Resend API returned %s for %s email to %s. Falling back to SMTP...",
                        resp.status_code,
                        context_label,
                        email,
                    )
        except Exception as resend_err:
            logger.warning(
                "Resend API request failed for %s email to %s (%s). Falling back to SMTP...",
                context_label,
                email,
                resend_err,
            )

    # 2. Native SMTP via background thread (Auto-prioritize port 465 for Gmail on cloud hosts)
    if "gmail.com" in settings.MAIL_SERVER.lower():
        ports_to_try = [465, 587] if settings.MAIL_PORT in [465, 587] else [settings.MAIL_PORT, 465]
    else:
        primary_port = settings.MAIL_PORT
        fallback_port = 465 if primary_port == 587 else (587 if primary_port == 465 else None)
        ports_to_try = [primary_port] + ([fallback_port] if fallback_port else [])

    last_error: Optional[Exception] = None
    for port in ports_to_try:
        try:
            await asyncio.to_thread(_send_sync_smtp, email, subject, html_body, port)
            logger.info("%s email: sent successfully to %s via %s:%d", context_label, email, settings.MAIL_SERVER, port)
            return True
        except Exception as err:
            last_error = err
            logger.debug("%s email attempt on %s:%d failed: %s", context_label, settings.MAIL_SERVER, port, err)

    safe_error_str = str(last_error) if last_error else "Network unreachable or SMTP credentials unconfigured"
    logger.error("%s email failed for %s: %s", context_label, email, safe_error_str)

    if settings.DEBUG:
        if fallback_otp:
            print(f"\n==========================================")
            print(f"[DEV MODE - OTP] {context_label} for {email}: {fallback_otp}")
            print(f"==========================================\n")

    # Return True so customer actions / registration flows are not aborted when host blocks raw SMTP ports
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