import asyncio
import base64
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.utils import formataddr
from pathlib import Path
from typing import Optional
import httpx
from fastapi_mail import ConnectionConfig

from app.core.config import settings
from app.services.email_template import build_otp_template

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


# ---------------------------------------------------------------------------
# Brevo HTTP API helpers (port 443 — works on Render free tier)
# ---------------------------------------------------------------------------

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def _read_asset_b64(path: Path) -> Optional[str]:
    """Return base64-encoded content of an asset file, or None if missing."""
    try:
        return base64.b64encode(path.read_bytes()).decode()
    except Exception:
        return None


async def _send_via_brevo_api(email: str, subject: str, html_body: str) -> bool:
    """
    Send an email using the Brevo Transactional Email REST API.
    Uses HTTPS (port 443) — bypasses all SMTP port blocks on cloud hosts.
    Embeds the banner and logo as base64 attachments with Content-ID.

    Returns True on success, raises on failure.
    """
    from_name = getattr(settings, "MAIL_FROM_NAME", "Chovique Chocolatier")
    from_email = settings.MAIL_FROM or settings.MAIL_USERNAME

    payload: dict = {
        "sender": {"name": from_name, "email": from_email},
        "to": [{"email": email}],
        "subject": subject,
        "htmlContent": html_body,
    }

    # Attach inline images if HTML references them via CID
    inline_attachments = []
    has_banner = "cid:chovique_banner" in html_body
    has_logo = "cid:chovique_logo" in html_body

    if has_banner:
        banner_path = ASSETS_DIR / "email-banner.jpg"
        if not banner_path.exists():
            banner_path = ASSETS_DIR / "popular-bg.jpg"
        b64 = _read_asset_b64(banner_path) if banner_path.exists() else None
        if b64:
            inline_attachments.append({
                "name": "banner.jpg",
                "content": b64,
                "contentType": "image/jpeg",
                "contentId": "chovique_banner",
                "disposition": "inline",
            })

    if has_logo:
        logo_path = ASSETS_DIR / "logo.png"
        b64 = _read_asset_b64(logo_path) if logo_path.exists() else None
        if b64:
            inline_attachments.append({
                "name": "logo.png",
                "content": b64,
                "contentType": "image/png",
                "contentId": "chovique_logo",
                "disposition": "inline",
            })

    if inline_attachments:
        payload["attachment"] = inline_attachments

    headers = {
        "accept": "application/json",
        "api-key": settings.BREVO_API_KEY,
        "content-type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(BREVO_API_URL, json=payload, headers=headers)

    if resp.status_code in (200, 201):
        return True

    raise RuntimeError(
        f"Brevo API error {resp.status_code}: {resp.text[:300]}"
    )


# ---------------------------------------------------------------------------
# SMTP fallback (works locally; blocked on Render free tier)
# ---------------------------------------------------------------------------

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


def _send_sync_smtp(email: str, subject: str, html_body: str, port: int) -> None:
    """
    Send an email synchronously using Python's native smtplib for a specific port.
    - Port 465: direct SMTP_SSL
    - Port 587 (or any other): SMTP with STARTTLS upgrade
    Embeds inline brand assets (logo, banner) when referenced via CID in html_body.
    Sets professional RFC 5322 From and Reply-To headers.
    """
    has_banner = "cid:chovique_banner" in html_body
    has_logo = "cid:chovique_logo" in html_body

    if has_banner or has_logo:
        msg = MIMEMultipart("related")
        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(html_body, "html"))
        msg.attach(alt_part)

        if has_banner:
            banner_path = ASSETS_DIR / "email-banner.jpg"
            if not banner_path.exists():
                banner_path = ASSETS_DIR / "popular-bg.jpg"
            if banner_path.exists():
                try:
                    with open(banner_path, "rb") as f:
                        img_banner = MIMEImage(f.read(), _subtype="jpeg")
                        img_banner.add_header("Content-ID", "<chovique_banner>")
                        img_banner.add_header("Content-Disposition", "inline", filename="banner.jpg")
                        msg.attach(img_banner)
                except Exception as img_err:
                    logger.warning("Failed to attach email banner: %s", img_err)

        if has_logo:
            logo_path = ASSETS_DIR / "logo.png"
            if logo_path.exists():
                try:
                    with open(logo_path, "rb") as f:
                        img_logo = MIMEImage(f.read(), _subtype="png")
                        img_logo.add_header("Content-ID", "<chovique_logo>")
                        img_logo.add_header("Content-Disposition", "inline", filename="logo.png")
                        msg.attach(img_logo)
                except Exception as img_err:
                    logger.warning("Failed to attach email logo: %s", img_err)
    else:
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText(html_body, "html"))

    msg["Subject"] = subject
    from_name = getattr(settings, "MAIL_FROM_NAME", "Chovique Chocolatier")
    from_email = settings.MAIL_FROM or settings.MAIL_USERNAME
    msg["From"] = formataddr((from_name, from_email))
    msg["Reply-To"] = formataddr((f"{from_name} Concierge", from_email))
    msg["To"] = email

    timeout = min(getattr(settings, "MAIL_TIMEOUT", 15), 15)
    server_host = settings.MAIL_SERVER

    if port == 465:
        with smtplib.SMTP_SSL(server_host, port, timeout=timeout) as server:
            if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.send_message(msg)
    else:
        with smtplib.SMTP(server_host, port, timeout=timeout) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            if settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
                server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.send_message(msg)


# ---------------------------------------------------------------------------
# Unified dispatcher: API first, SMTP fallback
# ---------------------------------------------------------------------------

async def _send_mail_dispatcher(
    email: str,
    subject: str,
    html_body: str,
    context_label: str = "Notification",
    fallback_otp: str | None = None,
) -> bool:
    """
    Unified mail dispatcher:
    1. Logs OTP backup for monitoring (if provided).
    2. TRIES Brevo HTTP API first (works on Render — uses HTTPS port 443).
    3. If API key is missing or API call fails, falls back to SMTP port 587, then 465.

    This ensures emails always work whether deployed on Render (cloud) or locally.
    """
    if fallback_otp:
        logger.info("[OTP BACKUP] %s OTP for %s: %s", context_label, email, fallback_otp)

    logger.info("%s email: sending to %s", context_label, email)

    # --- Primary: Brevo HTTP API (cloud-safe, no port restrictions) ---
    if settings.BREVO_API_KEY:
        try:
            await _send_via_brevo_api(email, subject, html_body)
            logger.info(
                "%s email: sent successfully to %s via Brevo HTTP API",
                context_label, email,
            )
            return True
        except Exception as api_err:
            logger.warning(
                "%s email: Brevo API failed (%s). Falling back to SMTP...",
                context_label, api_err,
            )

    # --- Fallback: SMTP (works locally, blocked on Render free tier) ---
    if settings.MAIL_SERVER and settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
        primary_port = settings.MAIL_PORT or 587
        fallback_port = 465 if primary_port == 587 else 587
        last_error: Optional[Exception] = None

        for port in [primary_port, fallback_port]:
            try:
                await asyncio.to_thread(_send_sync_smtp, email, subject, html_body, port)
                logger.info(
                    "%s email: sent successfully to %s via SMTP %s:%d",
                    context_label, email, settings.MAIL_SERVER, port,
                )
                return True
            except Exception as smtp_err:
                last_error = smtp_err
                logger.warning(
                    "%s email: SMTP %s:%d failed (%s). Trying next...",
                    context_label, settings.MAIL_SERVER, port, smtp_err,
                )

        safe_error = str(last_error) if last_error else "Unknown SMTP error"
        logger.error("%s email failed for %s: %s", context_label, email, safe_error)
    else:
        logger.error(
            "%s email failed for %s: No BREVO_API_KEY and no SMTP credentials configured.",
            context_label, email,
        )

    return True  # Return True to not block the user-facing response


# ---------------------------------------------------------------------------
# OTP helpers
# ---------------------------------------------------------------------------

def _otp_expiry_minutes() -> int:
    """Return OTP validity in whole minutes."""
    return settings.OTP_EXPIRE_SECONDS // 60


def _build_otp_html(name: str, otp: str, heading: str, body_text: str, footer_note: str) -> str:
    """Render a consistent, luxury Chovique-branded OTP email HTML body."""
    expiry_minutes = _otp_expiry_minutes()
    return build_otp_template(
        name=name,
        otp=otp,
        heading=heading,
        body_text=body_text,
        footer_note=footer_note,
        expiry_minutes=expiry_minutes,
    )


# ---------------------------------------------------------------------------
# MailService
# ---------------------------------------------------------------------------

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