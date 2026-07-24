from typing import Optional
from pydantic import BaseModel, ConfigDict


class FAQBase(BaseModel):
    question: str
    answer: str
    category: str = "General"
    sort_order: int = 0


class FAQCreate(FAQBase):
    pass


class FAQResponse(FAQBase):
    id: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
