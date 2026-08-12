from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.address import CustomerAddress


class AddressRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_addresses(self, user_id: str) -> list[CustomerAddress]:
        result = await self.db.execute(
            select(CustomerAddress)
            .where(CustomerAddress.user_id == user_id)
            .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, address_id: str) -> CustomerAddress | None:
        result = await self.db.execute(
            select(CustomerAddress).where(CustomerAddress.id == address_id)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> CustomerAddress:
        if kwargs.get("is_default"):
            # Unset default on existing user addresses
            await self.db.execute(
                update(CustomerAddress)
                .where(CustomerAddress.user_id == kwargs["user_id"])
                .values(is_default=False)
            )

        address = CustomerAddress(**kwargs)
        self.db.add(address)
        await self.db.commit()
        await self.db.refresh(address)
        return address

    async def delete(self, address_id: str, user_id: str) -> bool:
        result = await self.db.execute(
            delete(CustomerAddress)
            .where(CustomerAddress.id == address_id, CustomerAddress.user_id == user_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def update(self, address_id: str, user_id: str, **kwargs) -> CustomerAddress | None:
        address = await self.get_by_id(address_id)
        if not address or str(address.user_id) != str(user_id):
            return None

        if kwargs.get("is_default"):
            # Unset default on existing user addresses
            await self.db.execute(
                update(CustomerAddress)
                .where(CustomerAddress.user_id == user_id)
                .values(is_default=False)
            )

        for k, v in kwargs.items():
            if hasattr(address, k) and v is not None:
                setattr(address, k, v)

        await self.db.commit()
        await self.db.refresh(address)
        return address

    async def set_default(self, address_id: str, user_id: str) -> CustomerAddress | None:
        # Clear default flag on all addresses for this user
        await self.db.execute(
            update(CustomerAddress)
            .where(CustomerAddress.user_id == user_id)
            .values(is_default=False)
        )
        # Set default on targeted address
        await self.db.execute(
            update(CustomerAddress)
            .where(CustomerAddress.id == address_id, CustomerAddress.user_id == user_id)
            .values(is_default=True)
        )
        await self.db.commit()
        return await self.get_by_id(address_id)
