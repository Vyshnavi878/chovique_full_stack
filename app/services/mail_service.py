import logging
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.core.config import settings

logger = logging.getLogger(__name__)

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
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
        fm = FastMail(conf)
        try:
            await fm.send_message(message)
        except Exception as e:
            logger.error(f"Failed to send registration OTP email to {email}: {e}")
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
        fm = FastMail(conf)
        try:
            await fm.send_message(message)
        except Exception as e:
            logger.error(f"Failed to send resend registration OTP email to {email}: {e}")
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
        fm = FastMail(conf)
        try:
            await fm.send_message(message)
        except Exception as e:
            label = "Resend Forgot" if is_resend else "Forgot"
            logger.error(f"Failed to send {label} Password OTP email to {email}: {e}")
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
        fm = FastMail(conf)
        try:
            await fm.send_message(message)
        except Exception as e:
            logger.error(f"Failed to send Update Password OTP email to {email}: {e}")
            if settings.DEBUG:
                print(f"\n==========================================")
                print(f"[DEV MODE - MAIL FAILED] Update Password OTP for {email}: {otp}")
                print(f"==========================================\n")
            else:
                raise e