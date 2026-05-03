"""
Text-to-Speech Route — /api/tts
==================================
Attempts Google Cloud TTS; returns metadata for browser fallback if unavailable.
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from services.tts_service import is_tts_available, synthesize_speech

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    language_code: str = Field(default="en-US", max_length=10)
    speaking_rate: float = Field(default=1.0, ge=0.25, le=4.0)

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        return v.strip()

    @field_validator("language_code")
    @classmethod
    def validate_language(cls, v: str) -> str:
        # Basic sanitization — allow only BCP-47 format
        import re

        if not re.match(r"^[a-zA-Z]{2,3}(-[a-zA-Z0-9]{2,4})?$", v):
            return "en-US"
        return v


@router.post("/tts")
@limiter.limit("20/minute")
async def text_to_speech(request: Request, body: TTSRequest) -> dict:
    """
    Convert text to speech.

    If Google Cloud TTS credentials are configured, returns base64-encoded MP3 audio.
    Otherwise, returns `use_browser_tts: true` so the client falls back to Web Speech API.

    - **text**: Text to speak (max 5000 chars)
    - **language_code**: BCP-47 language code (default: en-US)
    - **speaking_rate**: Speed multiplier 0.25–4.0 (default: 1.0)
    """
    try:
        audio_b64 = await synthesize_speech(
            text=body.text,
            language_code=body.language_code,
            speaking_rate=body.speaking_rate,
        )

        if audio_b64:
            return {
                "use_browser_tts": False,
                "audio_base64": audio_b64,
                "format": "mp3",
                "language_code": body.language_code,
            }
        else:
            # Graceful degradation — client handles via Web Speech API
            return {
                "use_browser_tts": True,
                "text": body.text,
                "language_code": body.language_code,
                "speaking_rate": body.speaking_rate,
            }

    except Exception as exc:
        logger.exception(f"Unexpected error in /api/tts: {exc}")
        # Always degrade gracefully — TTS should never block the app
        return {
            "use_browser_tts": True,
            "text": body.text,
            "language_code": body.language_code,
            "speaking_rate": body.speaking_rate,
        }


@router.get("/tts/status")
async def tts_status() -> dict:
    """Check whether Google Cloud TTS is available."""
    return {
        "cloud_tts_available": is_tts_available(),
        "fallback": "Web Speech API (browser-native)",
    }
