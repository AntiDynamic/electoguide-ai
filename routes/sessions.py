"""
Sessions Route  —  /api/sessions
===================================
CRUD endpoints for Firestore-backed chat sessions.
The session_id is returned on creation and stored in the browser (localStorage).
"""

import logging

from fastapi import APIRouter, HTTPException, Path, Request
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from services import firestore_service as fs
from services import cloud_logger

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

VALID_PERSONAS = {"student", "first_voter", "researcher", "senior", "general"}


class CreateSessionRequest(BaseModel):
    persona: str = Field(default="general")

    @field_validator("persona")
    @classmethod
    def validate_persona(cls, v: str) -> str:
        return v if v in VALID_PERSONAS else "general"


@router.post("/sessions")
@limiter.limit("10/minute")
async def create_session(request: Request, body: CreateSessionRequest) -> dict:
    """
    Create a new chat session backed by Cloud Firestore.

    Returns a `session_id` that the client stores in localStorage and
    passes with every subsequent `/api/chat` call.
    """
    session = await fs.create_session(persona=body.persona)
    cloud_logger.log_request("/api/sessions", method="POST", status_code=200)
    return {
        "session_id": session["session_id"],
        "persona": session["persona"],
        "created_at": session["created_at"],
        "firestore_enabled": fs.is_available(),
    }


@router.get("/sessions/info")
async def sessions_status() -> dict:
    """Check Firestore availability."""
    return {
        "firestore_available": fs.is_available(),
        "note": "Session history is persisted across page loads when Firestore is enabled.",
    }


@router.get("/sessions/{session_id}")
@limiter.limit("30/minute")
async def get_session(
    request: Request,
    session_id: str = Path(..., min_length=36, max_length=36),
) -> dict:
    """Retrieve a session by ID."""
    session = await fs.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


@router.patch("/sessions/{session_id}/persona")
@limiter.limit("20/minute")
async def update_persona(
    request: Request,
    body: CreateSessionRequest,
    session_id: str = Path(..., min_length=36, max_length=36),
) -> dict:
    """Update the persona for an existing session."""
    ok = await fs.update_persona(session_id, body.persona)
    if not ok:
        raise HTTPException(status_code=404, detail="Session not found or Firestore unavailable.")
    return {"session_id": session_id, "persona": body.persona, "updated": True}


@router.delete("/sessions/{session_id}")
@limiter.limit("10/minute")
async def delete_session(
    request: Request,
    session_id: str = Path(..., min_length=36, max_length=36),
) -> dict:
    """Delete a session and its history."""
    await fs.delete_session(session_id)
    return {"session_id": session_id, "deleted": True}
