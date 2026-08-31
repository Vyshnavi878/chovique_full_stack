"""
Application configuration.

Loads environment variables from .env using Pydantic Settings.
"""

from functools import lru_cache
from typing import List

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # =====================================================
    # Application
    # =====================================================
    APP_NAME: str = "Chovique"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # =====================================================
    # API
    # =====================================================
    API_V1_PREFIX: str = "/api/v1"

    # =====================================================
    # PostgreSQL
    # =====================================================
    DATABASE_URL: str
    DB_ECHO: bool = False

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace(
                    "postgres://",
                    "postgresql+asyncpg://",
                    1,
                )

            if (
                v.startswith("postgresql://")
                and not v.startswith("postgresql+asyncpg://")
            ):
                return v.replace(
                    "postgresql://",
                    "postgresql+asyncpg://",
                    1,
                )

        return v

    # =====================================================
    # Redis
    # =====================================================
    REDIS_URL: str = ""

    # =====================================================
    # JWT
    # =====================================================
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # =====================================================
    # CORS
    # =====================================================
    ALLOWED_ORIGINS: List[str]

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, value):
        """
        Convert Render environment variable into a list.

        Example:
        http://localhost:5173,http://localhost:3000,https://example.vercel.app

        becomes:

        [
            "http://localhost:5173",
            "http://localhost:3000",
            "https://example.vercel.app"
        ]
        """

        if isinstance(value, str):

            value = value.strip()

            # Support JSON array:
            # ["https://example.vercel.app", "http://localhost:5173"]
            if value.startswith("[") and value.endswith("]"):
                import json

                origins = json.loads(value)

                return [
                    origin.strip().rstrip("/")
                    for origin in origins
                    if isinstance(origin, str) and origin.strip()
                ]

            # Support comma-separated values
            return [
                origin.strip().rstrip("/")
                for origin in value.split(",")
                if origin.strip()
            ]

        if isinstance(value, list):
            return [
                origin.strip().rstrip("/")
                for origin in value
                if isinstance(origin, str) and origin.strip()
            ]

        return value

    # =====================================================
    # SMTP
    # =====================================================
    MAIL_SERVER: str = ""
    MAIL_PORT: int = 587
    MAIL_USERNAME: str = ""
    MAIL_PASSWORD: str = ""
    MAIL_FROM: str = ""

    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    MAIL_TIMEOUT: int = 10

    @field_validator("MAIL_TIMEOUT", mode="before")
    @classmethod
    def parse_mail_timeout(cls, v):
        if v is None or v == "":
            return 10

        try:
            return int(v)
        except (ValueError, TypeError):
            return 10

    # =====================================================
    # OTP
    # =====================================================
    OTP_EXPIRE_SECONDS: int = 300
    MAX_OTP_ATTEMPTS: int = 3
    MAX_OTP_RESEND_ATTEMPTS: int = 3
    OTP_RESEND_LOCKOUT_SECONDS: int = 600

    @field_validator("OTP_EXPIRE_SECONDS", mode="before")
    @classmethod
    def parse_otp_expire_seconds(cls, v):
        if v is None or v == "":
            return 300

        try:
            val = int(v)
            return max(val, 300)
        except (ValueError, TypeError):
            return 300

    # =====================================================
    # Google OAuth
    # =====================================================
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # =====================================================
    # Razorpay
    # =====================================================
    RAZORPAY_KEY_ID: str = "rzp_test_placeholder"
    RAZORPAY_KEY_SECRET: str = "secret_placeholder"
    RAZORPAY_WEBHOOK_SECRET: str = "webhook_secret_placeholder"

    # =====================================================
    # Resend
    # =====================================================
    RESEND_API_KEY: str = ""

    # =====================================================
    # Cloudinary
    # =====================================================
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # =====================================================
    # Superadmin
    # =====================================================
    SUPERADMIN_EMAIL: str = Field(
        validation_alias=AliasChoices(
            "SUPERADMIN_EMAIL",
            "SUPER_ADMIN_EMAIL",
        )
    )

    SUPERADMIN_PASSWORD: str = Field(
        validation_alias=AliasChoices(
            "SUPERADMIN_PASSWORD",
            "SUPER_ADMIN_PASSWORD",
        )
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()