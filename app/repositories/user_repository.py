from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==========================================================
    # Create User
    # ==========================================================

    async def create(self, **kwargs) -> User:
        user = User(**kwargs)

        self.db.add(user)

        await self.db.commit()

        await self.db.refresh(user)

        return user

    # ==========================================================
    # Get By Email
    # ==========================================================

    async def get_by_email(self, email: str) -> User | None:

        result = await self.db.execute(
            select(User).where(User.email == email)
        )

        return result.scalar_one_or_none()

    # ==========================================================
    # Get By ID
    # ==========================================================

    async def get_by_id(self, user_id: str) -> User | None:

        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )

        return result.scalar_one_or_none()

    # ==========================================================
    # Get By Google ID
    # ==========================================================

    async def get_by_google_id(
        self,
        google_id: str,
    ) -> User | None:

        result = await self.db.execute(
            select(User).where(User.google_id == google_id)
        )

        return result.scalar_one_or_none()

    # ==========================================================
    # Verify Email
    # ==========================================================

    async def verify_email(
        self,
        user_id: str,
    ) -> None:

        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_email_verified=True)
        )

        await self.db.commit()

    # ==========================================================
    # Update Password
    # ==========================================================

    async def update_password(
        self,
        user_id: str,
        hashed_password: str,
    ) -> None:

        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(hashed_password=hashed_password)
        )

        await self.db.commit()

    # ==========================================================
    # Update Google ID
    # ==========================================================

    async def update_google_id(
        self,
        user_id: str,
        google_id: str,
    ) -> None:

        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(google_id=google_id)
        )

        await self.db.commit()

    async def update_google_data(
        self,
        user_id: str,
        google_id: str,
        avatar_url: str | None = None,
    ) -> None:

        values = {"google_id": google_id}
        if avatar_url is not None:
            values["avatar_url"] = avatar_url

        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(**values)
        )

        await self.db.commit()

    # ==========================================================
    # Update Last Login
    # ==========================================================

    async def update_last_login(
        self,
        user_id: str,
        last_login_at,
    ) -> None:

        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=last_login_at)
        )

        await self.db.commit()

    # ==========================================================
    # Deactivate User
    # ==========================================================

    async def deactivate(
        self,
        user_id: str,
    ) -> None:

        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_active=False)
        )

        await self.db.commit()

    # ==========================================================
    # Update Profile
    # ==========================================================

    async def update_profile(
        self,
        user_id: str,
        **kwargs,
    ) -> User | None:

        if kwargs:
            await self.db.execute(
                update(User)
                .where(User.id == user_id)
                .values(**kwargs)
            )
            await self.db.commit()

        return await self.get_by_id(user_id)

    # ==========================================================
    # Count Customers
    # ==========================================================

    async def count_customers(self) -> int:
        from sqlalchemy import select, func
        result = await self.db.execute(
            select(func.count(User.id)).where(User.role == "customer")
        )
        return result.scalar_one_or_none() or 0