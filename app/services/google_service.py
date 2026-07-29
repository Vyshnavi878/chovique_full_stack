import asyncio
import logging

from google.auth.transport import requests
from google.oauth2 import id_token

from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleService:

    @staticmethod
    async def verify_google_token(token: str) -> dict:
        """
        Verify Google ID Token and return user information.
        """
        if not token:
            return None

        try:
            user_info = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )
            return {
                "google_id": user_info["sub"],
                "email": user_info["email"],
                "full_name": user_info.get("name") or user_info.get("email", "").split("@")[0],
                "avatar_url": user_info.get("picture"),
                "email_verified": user_info.get("email_verified", True),
            }
        except Exception as e:
            logger.warning("id_token.verify_oauth2_token with audience failed: %s. Trying without audience.", e)

        # 2. Try verify_oauth2_token without audience constraint
        try:
            user_info = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                audience=None,
            )
            return {
                "google_id": user_info["sub"],
                "email": user_info["email"],
                "full_name": user_info.get("name") or user_info.get("email", "").split("@")[0],
                "avatar_url": user_info.get("picture"),
                "email_verified": user_info.get(
                    "email_verified",
                    False,
                ),
            }

        except Exception as e:
            logger.error("Google token verification failed: %s", str(e))
            return None