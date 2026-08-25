import asyncio
import logging
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_mail_config() -> ConnectionConfig:
    """
    Build FastMail ConnectionConfig dynamically.
    Auto-adjusts SSL/TLS vs STARTTLS based on port if standard defaults are provided,
    and applies a short timeout so requests never block.
    """
    port = settings.MAIL_PORT
    starttls = settings.MAIL_STARTTLS
    ssl_tls = settings.MAIL_SSL_TLS

    if port == 465:
        ssl_tls = True
        starttls = False
    elif port == 587:
        starttls = True
        ssl_tls = False

    return ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_PORT=port,
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
        conf = get_mail_config()
        fm = FastMail(conf)
        timeout_seconds = getattr(settings, "MAIL_TIMEOUT", 10)
        try:
            await asyncio.wait_for(fm.send_message(message), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.error(
                f"Registration OTP delivery timed out after {timeout_seconds}s for {email} connecting to {conf.MAIL_SERVER}:{conf.MAIL_PORT}."
            )
            if settings.DEBUG:
                print(f"\n==========================================")
                print(f"[DEV MODE - MAIL TIMEOUT] Registration OTP for {email}: {otp}")
                print(f"==========================================\n")
            else:
                raise RuntimeError(
                    f"Email service timed out connecting to {conf.MAIL_SERVER}:{conf.MAIL_PORT}. Please try again later."
                )
        except Exception as e:
            logger.error(f"Failed to send registration OTP email to {email} via {conf.MAIL_SERVER}:{conf.MAIL_PORT}: {e}")
            if settings.DEBUG:
                print(f"\n==========================================")
                print(f"[DEV MODE - MAIL FAILED] Registration OTP for {email}: {otp}")
                print(f"==========================================\n")
            else:
                raise e

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
        conf = get_mail_config()
        fm = FastMail(conf)
        timeout_seconds = getattr(settings, "MAIL_TIMEOUT", 10)
        try:
            await asyncio.wait_for(fm.send_message(message), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.error(
                f"Resend Registration OTP delivery timed out after {timeout_seconds}s for {email} connecting to {conf.MAIL_SERVER}:{conf.MAIL_PORT}."
            )
            if settings.DEBUG:
                print(f"\n==========================================")
                print(f"[DEV MODE - MAIL TIMEOUT] Resend Registration OTP for {email}: {otp}")
                print(f"==========================================\n")
            else:
                raise RuntimeError(
                    f"Email service timed out connecting to {conf.MAIL_SERVER}:{conf.MAIL_PORT}. Please try again later."
                )
        except Exception as e:
            logger.error(f"Failed to send resend registration OTP email to {email} via {conf.MAIL_SERVER}:{conf.MAIL_PORT}: {e}")
            if settings.DEBUG:
                print(f"\n==========================================")
                print(f"[DEV MODE - MAIL FAILED] Resend Registration OTP for {email}: {otp}")
                print(f"==========================================\n")
            else:
                raise e

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
        conf = get_mail_config()
        fm = FastMail(conf)
        timeout_seconds = getattr(settings, "MAIL_TIMEOUT", 10)
        try:
            await asyncio.wait_for(fm.send_message(message), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            label = "Resend Forgot" if is_resend else "Forgot"
            logger.error(
                f"{label} Password OTP delivery timed out after {timeout_seconds}s for {email} connecting to {conf.MAIL_SERVER}:{conf.MAIL_PORT}."
            )
            if settings.DEBUG:
                print(f"\n==========================================")
                print(f"[DEV MODE - MAIL TIMEOUT] {label} Password OTP for {email}: {otp}")
                print(f"==========================================\n")
            else:
                raise RuntimeError(
                    f"Email service timed out connecting to {conf.MAIL_SERVER}:{conf.MAIL_PORT}. Please try again later."
                )
        except Exception as e:
            label = "Resend Forgot" if is_resend else "Forgot"
            logger.error(f"Failed to send {label} Password OTP email to {email} via {conf.MAIL_SERVER}:{conf.MAIL_PORT}: {e}")
            if settings.DEBUG:
                print(f"\n==========================================")
                print(f"[DEV MODE - MAIL FAILED] {label} Password OTP for {email}: {otp}")
                print(f"==========================================\n")
            else:
                raise e

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
        conf = get_mail_config()
        fm = FastMail(conf)
        timeout_seconds = getattr(settings, "MAIL_TIMEOUT", 10)
        try:
            await asyncio.wait_for(fm.send_message(message), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            logger.error(
                f"Update Password OTP delivery timed out after {timeout_seconds}s for {email} connecting to {conf.MAIL_SERVER}:{conf.MAIL_PORT}."
            )
            if settings.DEBUG:
                print(f"\n==========================================")
                print(f"[DEV MODE - MAIL TIMEOUT] Update Password OTP for {email}: {otp}")
                print(f"==========================================\n")
            else:
                raise RuntimeError(
                    f"Email service timed out connecting to {conf.MAIL_SERVER}:{conf.MAIL_PORT}. Please try again later."
                )
        except Exception as e:
            logger.error(f"Failed to send Update Password OTP email to {email} via {conf.MAIL_SERVER}:{conf.MAIL_PORT}: {e}")
            if settings.DEBUG:
                print(f"\n==========================================")
                print(f"[DEV MODE - MAIL FAILED] Update Password OTP for {email}: {otp}")
                print(f"==========================================\n")
            else:
                raise e

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
        conf = get_mail_config()
        fm = FastMail(conf)
        timeout_seconds = getattr(settings, "MAIL_TIMEOUT", 10)
        try:
            await asyncio.wait_for(fm.send_message(message), timeout=timeout_seconds)
            logger.info(f"SMTP notification email sent successfully to {email} | Subject: {subject}")
            return True
        except asyncio.TimeoutError:
            logger.error(
                f"SMTP notification email delivery timed out after {timeout_seconds}s for {email} "
                f"connecting to {conf.MAIL_SERVER}:{conf.MAIL_PORT}. "
                f"Please verify SMTP host/port configuration (e.g. port 465 with SSL vs port 587 with STARTTLS) "
                f"and ensure outbound SMTP traffic is permitted."
            )
            return False
        except Exception as e:
            logger.error(
                f"SMTP notification email delivery failed for {email} via {conf.MAIL_SERVER}:{conf.MAIL_PORT}: {e}"
            )
            if settings.DEBUG:
                print(f"\n==========================================")
                print(f"[DEV MODE - SMTP FAILED] Email to {email} | Subject: {subject}")
                print(f"==========================================\n")
            return False