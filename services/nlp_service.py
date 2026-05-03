"""
Google Cloud Natural Language API Service
==========================================
Analyses user messages to extract named entities (countries, organisations,
election-related terms). These entities are injected into the Gemini system
prompt to improve response relevance.

Gracefully disabled when GCP credentials are unavailable.
"""

import logging
import os
from typing import Optional

from async_lru import alru_cache

logger = logging.getLogger(__name__)

_NL_AVAILABLE: Optional[bool] = None

# Entity types we care about for election context
RELEVANT_TYPES = {"LOCATION", "ORGANIZATION", "PERSON", "EVENT", "WORK_OF_ART", "OTHER"}


def _is_available() -> bool:
    global _NL_AVAILABLE
    if _NL_AVAILABLE is not None:
        return _NL_AVAILABLE
    try:
        from google.cloud import language_v1  # noqa: F401

        creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
        _NL_AVAILABLE = bool(creds and os.path.exists(creds))
    except ImportError:
        _NL_AVAILABLE = False
    if not _NL_AVAILABLE:
        logger.info("Cloud NL API unavailable — entity extraction disabled.")
    return _NL_AVAILABLE


@alru_cache(maxsize=100)
async def extract_entities(text: str) -> list[str]:
    """
    Extract meaningful entities (locations, orgs, events) from user text. using Cloud Natural Language API.

    Returns:
        List of entity name strings (e.g. ["United States", "Electoral College"]).
        Returns empty list if the API is unavailable.
    """
    if not _is_available():
        return []

    try:
        from google.cloud import language_v1
        import asyncio

        client = language_v1.LanguageServiceAsyncClient()
        document = language_v1.Document(
            content=text[:1000],  # API limit guard
            type_=language_v1.Document.Type.PLAIN_TEXT,
        )

        response = await client.analyze_entities(
            request={
                "document": document,
                "encoding_type": language_v1.EncodingType.UTF8,
            }
        )

        entities = [
            entity.name
            for entity in response.entities
            if language_v1.Entity.Type(entity.type_).name in RELEVANT_TYPES
            and entity.salience > 0.05  # Only notable entities
        ]

        logger.debug("NL API extracted entities: %s", entities)
        return entities[:10]  # Cap at 10 entities

    except Exception as exc:
        logger.error("Cloud NL API entity extraction failed: %s", exc)
        return []


async def analyse_sentiment(text: str) -> dict:
    """
    Analyse the sentiment of user text.

    Returns:
        {"score": float, "magnitude": float} or empty dict on failure.
    """
    if not _is_available():
        return {}

    try:
        from google.cloud import language_v1

        client = language_v1.LanguageServiceAsyncClient()
        document = language_v1.Document(
            content=text[:1000],
            type_=language_v1.Document.Type.PLAIN_TEXT,
        )
        response = await client.analyze_sentiment(request={"document": document})
        return {
            "score": response.document_sentiment.score,
            "magnitude": response.document_sentiment.magnitude,
        }
    except Exception as exc:
        logger.error("Cloud NL sentiment analysis failed: %s", exc)
        return {}
