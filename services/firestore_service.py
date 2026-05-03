"""
Google Cloud Firestore Service
================================
Stores and retrieves user chat sessions so conversations persist across
page reloads. Each session is identified by a UUID stored in the client.

Gracefully disabled when GCP credentials are unavailable.
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

_firestore_client = None
_FIRESTORE_AVAILABLE: Optional[bool] = None


def _get_client():
    """Lazily initialise and cache the Firestore async client."""
    global _firestore_client, _FIRESTORE_AVAILABLE
    if _FIRESTORE_AVAILABLE is False:
        return None
    if _firestore_client is not None:
        return _firestore_client
    try:
        from google.cloud import firestore as fs
        project = os.getenv("GCP_PROJECT_ID", "promptwars-495214")
        _firestore_client = fs.AsyncClient(project=project)
        _FIRESTORE_AVAILABLE = True
        logger.info("✅ Firestore client initialised (project=%s)", project)
        return _firestore_client
    except Exception as exc:
        _FIRESTORE_AVAILABLE = False
        logger.warning("⚠️  Firestore unavailable — sessions will be in-memory only: %s", exc)
        return None


def is_available() -> bool:
    _get_client()
    return _FIRESTORE_AVAILABLE is True


# ── Session Management ────────────────────────────────────────────────────────

async def create_session(persona: str = "general") -> dict[str, Any]:
    """Create a new chat session and persist it to Firestore."""
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    session = {
        "session_id": session_id,
        "persona": persona,
        "history": [],
        "created_at": now,
        "updated_at": now,
        "message_count": 0,
    }

    client = _get_client()
    if client:
        try:
            await client.collection("sessions").document(session_id).set(session)
            logger.debug("Firestore: created session %s", session_id)
        except Exception as exc:
            logger.error("Firestore: create_session failed: %s", exc)

    return session


async def get_session(session_id: str) -> Optional[dict[str, Any]]:
    """Retrieve a session from Firestore."""
    client = _get_client()
    if not client:
        return None
    try:
        doc = await client.collection("sessions").document(session_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception as exc:
        logger.error("Firestore: get_session(%s) failed: %s", session_id, exc)
        return None


async def append_message(session_id: str, role: str, content: str) -> bool:
    """Append a message to a session's history in Firestore."""
    client = _get_client()
    if not client:
        return False
    try:
        from google.cloud import firestore as fs
        ref = client.collection("sessions").document(session_id)
        await ref.update({
            "history": fs.ArrayUnion([{"role": role, "content": content}]),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "message_count": fs.Increment(1),
        })
        return True
    except Exception as exc:
        logger.error("Firestore: append_message(%s) failed: %s", session_id, exc)
        return False


async def update_persona(session_id: str, persona: str) -> bool:
    """Update the persona for an existing session."""
    client = _get_client()
    if not client:
        return False
    try:
        await client.collection("sessions").document(session_id).update({
            "persona": persona,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        return True
    except Exception as exc:
        logger.error("Firestore: update_persona(%s) failed: %s", session_id, exc)
        return False


async def delete_session(session_id: str) -> bool:
    """Delete a session from Firestore."""
    client = _get_client()
    if not client:
        return False
    try:
        await client.collection("sessions").document(session_id).delete()
        return True
    except Exception as exc:
        logger.error("Firestore: delete_session(%s) failed: %s", session_id, exc)
        return False
