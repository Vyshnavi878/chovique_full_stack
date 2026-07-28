import asyncio
import logging

import requests as requests_lib
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleService:

    @staticmethod
    async def verify_google_token(token: str) -> dict:
        """
        Verify Google ID Token and return user information.

        - Runs the blocking HTTP verification in a thread pool (asyncio.to_thread)
          so it never blocks the event loop.
        - Uses a requests.Session with an explicit timeout so a slow/unresponsive
          Google cert endpoint doesn't hang the server indefinitely.
        - asyncio.wait_for enforces a hard overall deadline (15 s).
        """

        def _verify() -> dict:
            # Explicit timeout on the underlying requests session so the thread
            # never waits forever for Google's JWKS/cert endpoint.
            session = requests_lib.Session()
            transport = google_requests.Request(session=session)
            return id_token.verify_oauth2_token(
                token,
                transport,
                settings.GOOGLE_CLIENT_ID,
                clock_skew_in_seconds=10,
            )

        try:
            user_info = await asyncio.wait_for(
                asyncio.to_thread(_verify),
                timeout=15.0,  # hard deadline — returns 400 instead of hanging
            )

            return {
                "google_id": user_info["sub"],
                "email": user_info["email"],
                "full_name": user_info.get("name"),
                "avatar_url": user_info.get("picture"),
                "email_verified": user_info.get("email_verified", False),
            }

        except asyncio.TimeoutError:
            logger.error("Google token verification timed out after 15 s")
            raise ValueError(
                "Google token verification timed out. Please try again."
            )
        except BaseException as e:
            # Catch BaseException (not just Exception) so asyncio.CancelledError
            # from request cancellation is also converted to a clean 400,
            # instead of propagating up and causing ERR_EMPTY_RESPONSE.
            logger.error("Google token verification failed: %s", str(e))
            raise ValueError(f"Invalid Google token: {e}") from e