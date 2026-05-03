"""
Translation Route  —  /api/translate
=======================================
Exposes Cloud Translation API to the frontend so users can translate
AI responses into their preferred language.
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from services.translate_service import (
    translate_text,
    detect_language,
    SUPPORTED_LANGUAGES,
)

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

VALID_CODES = {lang["code"] for lang in SUPPORTED_LANGUAGES}


class TranslateRequest(BaseModel):
    text:            str = Field(..., min_length=1, max_length=10_000)
    target_language: str = Field(..., max_length=10)
    source_language: str = Field(default="en", max_length=10)

    @field_validator("text")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()

    @field_validator("target_language", "source_language")
    @classmethod
    def validate_lang(cls, v: str) -> str:
        return v[:10].strip()


class DetectRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)


@router.post("/translate")
@limiter.limit("20/minute")
async def translate(request: Request, body: TranslateRequest) -> dict:
    """
    Translate text using Google Cloud Translation API.

    - **text**: Source text (max 10 000 chars)
    - **target_language**: BCP-47 language code (e.g. `hi`, `es`, `fr`)
    - **source_language**: Source language code (default: `en`)

    When Cloud Translation is unavailable, returns the original text with
    `used_cloud: false` so the frontend can degrade gracefully.
    """
    try:
        result = await translate_text(
            text=body.text,
            target_language=body.target_language,
            source_language=body.source_language,
        )
        return result
    except Exception as exc:
        logger.exception("Translation error: %s", exc)
        raise HTTPException(status_code=500, detail="Translation failed. Please try again.")


@router.post("/translate/detect")
@limiter.limit("20/minute")
async def detect(request: Request, body: DetectRequest) -> dict:
    """Detect the language of a text snippet."""
    return await detect_language(body.text)


@router.get("/translate/languages")
async def list_languages() -> dict:
    """Return the list of supported UI languages."""
    return {"languages": SUPPORTED_LANGUAGES}
