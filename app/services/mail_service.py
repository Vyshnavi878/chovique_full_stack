from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.core.config import settings


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


class MailService:

    @staticmethod
    async def send_registration_otp(
        email: str,
        otp: str,
    ) -> None:

        message = MessageSchema(
            subject="Verify Your Email",
            recipients=[email],
            body=f"""
            <h2>Email Verification</h2>

            <p>Your OTP is:</p>

            <h1>{otp}</h1>

            <p>This OTP will expire in 5 minutes.</p>

            <p>If you didn't request this, please ignore this email.</p>
            """,
            subtype=MessageType.html,
        )

        fm = FastMail(conf)

        await fm.send_message(message)

    @staticmethod
    async def send_forgot_password_otp(
        email: str,
        otp: str,
    ) -> None:

        message = MessageSchema(
            subject="Reset Password OTP",
            recipients=[email],
            body=f"""
            <h2>Reset Password</h2>

            <p>Your OTP is:</p>

            <h1>{otp}</h1>

            <p>This OTP will expire in 5 minutes.</p>

            <p>If you didn't request this, please ignore this email.</p>
            """,
            subtype=MessageType.html,
        )

        fm = FastMail(conf)

        await fm.send_message(message)