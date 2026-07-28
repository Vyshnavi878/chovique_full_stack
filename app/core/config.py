"""
Application configuration.

Loads environment variables from .env using Pydantic Settings.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
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
    APP_NAME: str
    APP_VERSION: str
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

    # =====================================================
    # Redis
    # =====================================================
    REDIS_URL: str

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
    ALLOWED_ORIGINS: List[str] | str

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, str):
            if value.startswith("[") and value.endswith("]"):
                import json
                return json.loads(value)
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    # =====================================================
    # SMTP
    # =====================================================
    MAIL_SERVER: str
    MAIL_PORT: int
    MAIL_USERNAME: str
    MAIL_PASSWORD: str
    MAIL_FROM: str

    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False

    OTP_EXPIRE_SECONDS: int = 300
    MAX_OTP_ATTEMPTS: int = 3

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
    # Resend Email
    # =====================================================
    RESEND_API_KEY: str = ""

    # =====================================================
    # Cloudinary
    # =====================================================
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()