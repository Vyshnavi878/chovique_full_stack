from google.auth.transport import requests
from google.oauth2 import id_token

from app.core.config import settings


class GoogleService:

    @staticmethod
    async def verify_google_token(token: str) -> dict:
        """
        Verify Google ID Token and return user information.
        """

        try:
            user_info = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )

            return {
                "google_id": user_info["sub"],
                "email": user_info["email"],
                "full_name": user_info.get("name"),
                "avatar_url": user_info.get("picture"),
                "email_verified": user_info.get(
                    "email_verified",
                    False,
                ),
            }

        except Exception:
            return None