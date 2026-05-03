"""
Chat Route — /api/chat
========================
AI-powered conversational endpoint powered by Gemini.
Supports persona-based contextual responses.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from services.gemini_service import generate_chat_response

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

VALID_PERSONAS = {"student", "first_voter", "researcher", "senior", "general"}


class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|model)$")
    content: str = Field(..., min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: Optional[list[ChatMessage]] = Field(default=None, max_length=20)
    persona: str = Field(default="general")

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        return v.strip()

    @field_validator("persona")
    @classmethod
    def validate_persona(cls, v: str) -> str:
        if v not in VALID_PERSONAS:
            return "general"
        return v


class ChatResponse(BaseModel):
    response: str
    persona: str


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    """
    Send a message to the ElectoGuide AI assistant.

    - **message**: The user's question or message (max 2000 chars)
    - **history**: Optional conversation history for context (max 20 turns)
    - **persona**: One of `student`, `first_voter`, `researcher`, `senior`, `general`
    """
    try:
        history_dicts = (
            [{"role": m.role, "content": m.content} for m in body.history]
            if body.history
            else None
        )

        response_text = await generate_chat_response(
            message=body.message,
            history=history_dicts,
            persona=body.persona,
        )

        return ChatResponse(response=response_text, persona=body.persona)

    except EnvironmentError as exc:
        logger.error(f"Configuration error in /api/chat: {exc}")
        raise HTTPException(status_code=503, detail="AI service not configured. Please contact support.")
    except Exception as exc:
        logger.exception(f"Unexpected error in /api/chat: {exc}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again.")
