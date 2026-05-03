"""
Google Cloud Text-to-Speech Service
=====================================
Converts text to speech using Google Cloud TTS.
Falls back gracefully when credentials are unavailable.
"""

import logging
import os
from base64 import b64encode
from typing import Optional

logger = logging.getLogger(__name__)

_TTS_AVAILABLE: Optional[bool] = None


def is_tts_available() -> bool:
    """Check if Google Cloud TTS credentials are available."""
    global _TTS_AVAILABLE
    if _TTS_AVAILABLE is not None:
        return _TTS_AVAILABLE
    try:
        from google.cloud import texttospeech  # noqa: F401
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        _TTS_AVAILABLE = bool(creds_path and os.path.exists(creds_path))
    except ImportError:
        _TTS_AVAILABLE = False
    return _TTS_AVAILABLE


async def synthesize_speech(
    text: str,
    language_code: str = "en-US",
    voice_name: str = "en-US-Neural2-F",
    speaking_rate: float = 1.0,
) -> Optional[str]:
    """
    Synthesize speech from text using Google Cloud TTS.

    Returns:
        Base64-encoded MP3 audio string, or None if unavailable.
    """
    if not is_tts_available():
        logger.debug("Cloud TTS unavailable — client should use browser Web Speech API")
        return None

    try:
        from google.cloud import texttospeech

        client = texttospeech.TextToSpeechAsyncClient()

        synthesis_input = texttospeech.SynthesisInput(text=text[:5000])  # Limit length

        voice = texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=0.0,
        )

        response = await client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        audio_b64 = b64encode(response.audio_content).decode("utf-8")
        logger.info(f"Cloud TTS synthesized {len(text)} chars → {len(audio_b64)} B64 chars")
        return audio_b64

    except Exception as exc:
        logger.error(f"Cloud TTS synthesis failed: {exc}")
        return None
