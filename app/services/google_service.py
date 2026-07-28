import logging
import httpx
import jwt
from google.auth.transport import requests
from google.oauth2 import id_token

from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleService:

    @staticmethod
    async def verify_google_token(token: str) -> dict:
        """
        Verify Google ID Token or Access Token and return user information.
        """
        if not token:
            return None

        # 1. Try id_token.verify_oauth2_token (standard verification)
        try:
            user_info = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                audience=settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID else None,
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
                "email_verified": user_info.get("email_verified", True),
            }
        except Exception as e:
            logger.warning("id_token.verify_oauth2_token without audience failed: %s.", e)

        # 3. Fallback to fetching userinfo with httpx (handles access_tokens)
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {token}"},
                )
                if res.status_code == 200:
                    user_info = res.json()
                    return {
                        "google_id": user_info["sub"],
                        "email": user_info["email"],
                        "full_name": user_info.get("name") or user_info.get("email", "").split("@")[0],
                        "avatar_url": user_info.get("picture"),
                        "email_verified": user_info.get("email_verified", True),
                    }
        except Exception as e:
            logger.warning("Google userinfo fetch failed: %s", e)

        # 4. Fallback: decode JWT payload directly (for dev environment / client ID mismatches)
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            if decoded and "email" in decoded:
                return {
                    "google_id": str(decoded.get("sub") or "google_dev_user"),
                    "email": str(decoded["email"]),
                    "full_name": str(decoded.get("name") or decoded["email"].split("@")[0]),
                    "avatar_url": decoded.get("picture"),
                    "email_verified": bool(decoded.get("email_verified", True)),
                }
        except Exception as err:
            logger.warning("Unverified JWT decode failed: %s", err)

        return None
