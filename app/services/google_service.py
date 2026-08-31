import logging

from google.auth.transport import requests
from google.oauth2 import id_token

from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleService:

    @staticmethod
    async def verify_google_token(token: str) -> dict | None:
        """
        Verify Google ID Token against configured GOOGLE_CLIENT_ID and return user information.
        Rejects tokens if client ID is missing or audience/signature/expiration validation fails.
        """
        if not token:
            return None

        client_id = (settings.GOOGLE_CLIENT_ID or "").strip()
        if not client_id:
            logger.error("Google OAuth authentication attempted but GOOGLE_CLIENT_ID is not configured.")
            return None

        try:
            user_info = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                audience=client_id,
                clock_skew_in_seconds=10,
            )
            return {
                "google_id": user_info["sub"],
                "email": user_info["email"],
                "full_name": user_info.get("name") or user_info.get("email", "").split("@")[0],
                "avatar_url": user_info.get("picture"),
                "email_verified": user_info.get("email_verified", True),
            }
        except Exception as e:
            logger.warning("Google token verification failed: %s", str(e))
            return None