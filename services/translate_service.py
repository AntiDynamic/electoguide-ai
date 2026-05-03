"""
Google Cloud Translation Service
====================================
Translates text using the Cloud Translation API v2.
Gracefully falls back (returns original text) when unavailable.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_TRANSLATE_AVAILABLE: Optional[bool] = None

# Supported language codes and display names shown in the UI
SUPPORTED_LANGUAGES: list[dict[str, str]] = [
    {"code": "en", "name": "English"},
    {"code": "hi", "name": "Hindi"},
    {"code": "es", "name": "Español"},
    {"code": "fr", "name": "Français"},
    {"code": "de", "name": "Deutsch"},
    {"code": "pt", "name": "Português"},
    {"code": "ar", "name": "Arabic"},
    {"code": "zh", "name": "中文"},
    {"code": "ja", "name": "日本語"},
    {"code": "ko", "name": "한국어"},
    {"code": "ru", "name": "Русский"},
    {"code": "sw", "name": "Swahili"},
]


def _is_available() -> bool:
    global _TRANSLATE_AVAILABLE
    if _TRANSLATE_AVAILABLE is not None:
        return _TRANSLATE_AVAILABLE
    try:
        from google.cloud import translate_v2  # noqa: F401

        creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        _TRANSLATE_AVAILABLE = bool(creds and os.path.exists(creds))
    except ImportError:
        _TRANSLATE_AVAILABLE = False
    if not _TRANSLATE_AVAILABLE:
        logger.info("Cloud Translation API unavailable — text will not be translated.")
    return _TRANSLATE_AVAILABLE


async def translate_text(
    text: str, target_language: str, source_language: str = "en"
) -> dict:
    """
    Translate text to the target language.

    Returns:
        {"translated_text": ..., "source_language": ..., "target_language": ..., "used_cloud": bool}
    """
    if target_language == source_language or target_language == "en":
        return {
            "translated_text": text,
            "source_language": source_language,
            "target_language": target_language,
            "used_cloud": False,
        }

    if not _is_available():
        return {
            "translated_text": text,
            "source_language": source_language,
            "target_language": target_language,
            "used_cloud": False,
            "note": "Translation service unavailable; showing original text.",
        }

    try:
        from google.cloud import translate_v2 as translate
        import asyncio

        client = translate.Client()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: client.translate(
                text, target_language=target_language, source_language=source_language
            ),
        )
        return {
            "translated_text": result["translatedText"],
            "source_language": result.get("detectedSourceLanguage", source_language),
            "target_language": target_language,
            "used_cloud": True,
        }
    except Exception as exc:
        logger.error("Cloud Translate failed: %s", exc)
        return {
            "translated_text": text,
            "source_language": source_language,
            "target_language": target_language,
            "used_cloud": False,
            "error": str(exc),
        }


async def detect_language(text: str) -> dict:
    """Detect the language of a text snippet."""
    if not _is_available():
        return {"language": "en", "confidence": 1.0, "used_cloud": False}
    try:
        from google.cloud import translate_v2 as translate
        import asyncio

        client = translate.Client()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: client.detect_language(text))
        return {
            "language": result["language"],
            "confidence": result.get("confidence", 1.0),
            "used_cloud": True,
        }
    except Exception as exc:
        logger.error("Language detection failed: %s", exc)
        return {"language": "en", "confidence": 1.0, "used_cloud": False}
