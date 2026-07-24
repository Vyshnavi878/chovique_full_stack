from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ticket import SupportTicket


class TicketRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_tickets(self, customer_id: str) -> list[SupportTicket]:
        result = await self.db.execute(
            select(SupportTicket)
            .where(SupportTicket.customer_id == customer_id)
            .order_by(SupportTicket.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, ticket_id: str) -> SupportTicket | None:
        result = await self.db.execute(
            select(SupportTicket).where(SupportTicket.id == ticket_id)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> SupportTicket:
        ticket = SupportTicket(**kwargs)
        self.db.add(ticket)
        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    async def update_feedback(self, ticket_id: str, feedback: str) -> SupportTicket | None:
        await self.db.execute(
            update(SupportTicket)
            .where(SupportTicket.id == ticket_id)
            .values(customer_resolution_feedback=feedback)
        )
        await self.db.commit()
        return await self.get_by_id(ticket_id)
