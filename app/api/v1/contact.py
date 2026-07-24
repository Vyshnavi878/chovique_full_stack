from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.contact import ContactMessageRequest, ContactMessageResponse
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/contact", tags=["Contact"])


@router.post(
    "",
    response_model=ContactMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit contact form message",
)
async def submit_contact(
    payload: ContactMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    service = CustomerService(db)
    return await service.submit_contact(payload)
