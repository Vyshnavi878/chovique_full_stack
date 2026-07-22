from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:


    def __init__(
        self,
        db: AsyncSession
    ):
        self.db = db



    # ==========================================================
    # Create Refresh Token
    # ==========================================================

    async def create(
        self,
        user_id: str,
        jti: str,
        hashed_token: str,
        expires_at: datetime,
        device_info: str | None = None,
    ) -> RefreshToken:


        token = RefreshToken(

            user_id=user_id,

            jti=jti,

            hashed_token=hashed_token,

            expires_at=expires_at,

            device_info=device_info,

        )


        self.db.add(token)


        await self.db.commit()


        await self.db.refresh(token)


        return token



    # ==========================================================
    # Get By JTI
    # ==========================================================

    async def get_by_jti(
        self,
        jti: str,
    ) -> RefreshToken | None:


        result = await self.db.execute(

            select(RefreshToken)
            .where(
                RefreshToken.jti == jti
            )

        )


        return result.scalar_one_or_none()



    # ==========================================================
    # Get User Sessions
    # ==========================================================

    async def get_user_sessions(
        self,
        user_id: str,
    ):


        result = await self.db.execute(

            select(RefreshToken)
            .where(

                RefreshToken.user_id == user_id,

                RefreshToken.revoked_at.is_(None),

            )

        )


        return result.scalars().all()



    # ==========================================================
    # Revoke Single Token
    # ==========================================================

    async def revoke(
        self,
        jti: str,
    ) -> None:


        await self.db.execute(

            update(RefreshToken)
            .where(
                RefreshToken.jti == jti
            )
            .values(

                revoked_at=datetime.now(
                    timezone.utc
                )

            )

        )


        await self.db.commit()



    # ==========================================================
    # Revoke All User Tokens
    # ==========================================================

    async def revoke_all_user_tokens(
        self,
        user_id: str,
    ) -> None:


        await self.db.execute(

            update(RefreshToken)
            .where(

                RefreshToken.user_id == user_id,

                RefreshToken.revoked_at.is_(None),

            )
            .values(

                revoked_at=datetime.now(
                    timezone.utc
                )

            )

        )


        await self.db.commit()



    # ==========================================================
    # Delete Expired Tokens
    # ==========================================================

    async def delete_expired(
        self
    ):


        await self.db.execute(

            delete(RefreshToken)
            .where(

                RefreshToken.expires_at
                <
                datetime.now(timezone.utc)

            )

        )


        await self.db.commit()