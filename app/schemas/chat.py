"""
Pydantic schemas for the Chovique AI Chatbot endpoint.

POST /api/v1/chat
  Request:  ChatRequest   { message, history? }
  Response: ChatResponse  { reply }
"""

from typing import Literal
from pydantic import BaseModel, Field


# Maximum allowed user message length (characters)
MAX_MESSAGE_LENGTH = 2000


class ChatMessage(BaseModel):
    """A single turn in the conversation history."""

    role: Literal["user", "assistant"] = Field(
        ...,
        description="Who sent this message: 'user' or 'assistant'.",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=MAX_MESSAGE_LENGTH,
        description="Text content of the message.",
    )


class ChatRequest(BaseModel):
    """
    Incoming chat request from the customer-facing widget.

    `history` contains previous turns so Gemini can understand
    follow-up questions within the same browser session.
    """

    message: str = Field(
        ...,
        min_length=1,
        max_length=MAX_MESSAGE_LENGTH,
        description="The customer's latest message.",
    )
    history: list[ChatMessage] = Field(
        default_factory=list,
        max_length=20,  # Cap at 20 turns to control token usage
        description="Previous conversation turns (oldest first).",
    )
    customer_name: str | None = Field(
        default=None,
        max_length=100,
        description="Optional customer name for personalized greetings.",
    )
    role: str | None = Field(
        default=None,
        max_length=50,
        description="Optional user role: 'customer', 'admin', 'superadmin', or 'guest'.",
    )


class ChatAction(BaseModel):
    """An interactive action button returned with the assistant's reply."""

    label: str = Field(..., description="User-facing button label (e.g. 'Explore Shop', 'Track Orders').")
    url: str = Field(..., description="Target route or URL (e.g. '/shop', '/dashboard?section=orders').")
    icon: str | None = Field(default=None, description="Optional icon identifier (e.g. 'shop', 'package', 'coins').")


class ChatResponse(BaseModel):
    """Response returned to the frontend chatbot widget."""

    reply: str = Field(..., description="Gemini's response to the customer.")
    actions: list[ChatAction] = Field(
        default_factory=list,
        description="Interactive action buttons to redirect the customer to specific pages/dashboards.",
    )

