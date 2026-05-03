"""
Chat Route  —  POST /api/chat
================================
AI-powered conversational endpoint.
• Gemini 1.5 Flash for response generation
• Cloud NL API for entity extraction (enriches AI context)
• Firestore for optional session persistence
• Cloud Logging for structured request telemetry
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from services.gemini_service import generate_chat_response
from services.nlp_service import extract_entities
from services.firestore_service import append_message, get_session
from services import cloud_logger

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

VALID_PERSONAS = {"student", "first_voter", "researcher", "senior", "general"}


# ── Request / Response models ─────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  = Field(..., pattern="^(user|model)$")
    content: str = Field(..., min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message:    str                        = Field(..., min_length=1, max_length=2000)
    history:    Optional[list[ChatMessage]] = Field(default=None, max_length=20)
    persona:    str                        = Field(default="general")
    session_id: Optional[str]              = Field(default=None, max_length=64)

    @field_validator("message")
    @classmethod
    def sanitize(cls, v: str) -> str:
        return v.strip()

    @field_validator("persona")
    @classmethod
    def validate_persona(cls, v: str) -> str:
        return v if v in VALID_PERSONAS else "general"


class ChatResponse(BaseModel):
    response:   str
    persona:    str
    session_id: Optional[str] = None
    entities:   list[str]     = []


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
@limiter.limit("30/minute")
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    """
    Send a message and receive an AI-generated election education response.

    - **message**: Your question (max 2 000 chars)
    - **history**: Optional prior conversation turns (max 20)
    - **persona**: `student` | `first_voter` | `researcher` | `senior` | `general`
    - **session_id**: Optional Firestore session ID for persistent history
    """
    t0 = time.monotonic()

    # ── Resolve conversation history ─────────────────────────────────────────
    history_dicts: list[dict] = []
    if body.session_id:
        session = await get_session(body.session_id)
        if session:
            history_dicts = session.get("history", [])[-10:]
    elif body.history:
        history_dicts = [{"role": m.role, "content": m.content} for m in body.history]

    # ── Cloud NL API — extract entities to enrich Gemini context ────────────
    entities: list[str] = []
    try:
        entities = await extract_entities(body.message)
    except Exception:
        pass  # Non-critical; continue without entities

    # ── Generate response via Gemini ─────────────────────────────────────────
    try:
        response_text = await generate_chat_response(
            message=body.message,
            history=history_dicts,
            persona=body.persona,
            entities=entities,
        )
    except EnvironmentError as exc:
        logger.error("Configuration error: %s", exc)
        raise HTTPException(status_code=503, detail="AI service not configured. Contact support.")
    except Exception as exc:
        logger.exception("Unexpected error in /api/chat: %s", exc)
        raise HTTPException(status_code=500, detail="An error occurred. Please try again.")

    # ── Persist to Firestore ─────────────────────────────────────────────────
    if body.session_id:
        await append_message(body.session_id, "user", body.message)
        await append_message(body.session_id, "model", response_text)

    # ── Structured log ───────────────────────────────────────────────────────
    cloud_logger.log_request(
        endpoint="/api/chat",
        status_code=200,
        persona=body.persona,
        session_id=body.session_id,
        duration_ms=(time.monotonic() - t0) * 1000,
        extra={"entities_found": len(entities)},
    )

    return ChatResponse(
        response=response_text,
        persona=body.persona,
        session_id=body.session_id,
        entities=entities,
    )
