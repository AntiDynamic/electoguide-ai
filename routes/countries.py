"""
Countries Route — /api/countries
===================================
Election system information for countries, powered by Gemini AI.
Includes voter journey generation.
"""

import logging
import re

from fastapi import APIRouter, HTTPException, Path, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from services.gemini_service import get_country_election_info, generate_voter_journey

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Featured countries displayed on the home page
FEATURED_COUNTRIES = [
    {"name": "United States",  "code": "us",  "emoji": "🇺🇸", "system": "Federal Republic"},
    {"name": "India",          "code": "in",  "emoji": "🇮🇳", "system": "Parliamentary Democracy"},
    {"name": "United Kingdom", "code": "gb",  "emoji": "🇬🇧", "system": "Constitutional Monarchy"},
    {"name": "Germany",        "code": "de",  "emoji": "🇩🇪", "system": "Federal Republic"},
    {"name": "France",         "code": "fr",  "emoji": "🇫🇷", "system": "Semi-Presidential"},
    {"name": "Canada",         "code": "ca",  "emoji": "🇨🇦", "system": "Parliamentary Democracy"},
    {"name": "Australia",      "code": "au",  "emoji": "🇦🇺", "system": "Federal Democracy"},
    {"name": "Brazil",         "code": "br",  "emoji": "🇧🇷", "system": "Federal Republic"},
    {"name": "Japan",          "code": "jp",  "emoji": "🇯🇵", "system": "Constitutional Monarchy"},
    {"name": "South Africa",   "code": "za",  "emoji": "🇿🇦", "system": "Constitutional Republic"},
    {"name": "New Zealand",    "code": "nz",  "emoji": "🇳🇿", "system": "Parliamentary Democracy"},
    {"name": "Sweden",         "code": "se",  "emoji": "🇸🇪", "system": "Constitutional Monarchy"},
]

VALID_PERSONAS = {"student", "first_voter", "researcher", "senior", "general"}


def _validate_country_name(country: str) -> str:
    """Sanitize country name input."""
    # Remove potentially harmful characters, allow letters, spaces, hyphens
    sanitized = re.sub(r"[^a-zA-Z\s\-]", "", country).strip()
    if len(sanitized) < 2 or len(sanitized) > 60:
        raise ValueError("Invalid country name")
    return sanitized


@router.get("/countries")
async def list_countries() -> dict:
    """Return the list of featured countries for the explorer."""
    return {"countries": FEATURED_COUNTRIES}


@router.get("/countries/{country}")
@limiter.limit("20/minute")
async def get_country(
    request: Request,
    country: str = Path(..., min_length=2, max_length=60),
) -> dict:
    """
    Get comprehensive election information for a specific country.

    - **country**: Country name (e.g. `United States`, `India`, `Germany`)
    """
    try:
        safe_country = _validate_country_name(country)
        result = await get_country_election_info(safe_country)
        return result

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except EnvironmentError as exc:
        logger.error(f"Config error in /api/countries/{country}: {exc}")
        raise HTTPException(status_code=503, detail="AI service not configured.")
    except Exception as exc:
        logger.exception(f"Unexpected error in /api/countries/{country}: {exc}")
        raise HTTPException(status_code=500, detail="Could not retrieve country information.")


@router.get("/countries/{country}/journey")
@limiter.limit("10/minute")
async def get_voter_journey(
    request: Request,
    country: str = Path(..., min_length=2, max_length=60),
    persona: str = Query(default="first_voter"),
) -> dict:
    """
    Get a personalized voter journey for a country.

    - **country**: Country name
    - **persona**: `student` | `first_voter` | `researcher` | `senior` | `general`
    """
    try:
        safe_country = _validate_country_name(country)
        safe_persona = persona if persona in VALID_PERSONAS else "first_voter"
        result = await generate_voter_journey(safe_country, safe_persona)
        return result

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except EnvironmentError as exc:
        logger.error(f"Config error in /api/countries/{country}/journey: {exc}")
        raise HTTPException(status_code=503, detail="AI service not configured.")
    except Exception as exc:
        logger.exception(f"Unexpected error in /api/countries/{country}/journey: {exc}")
        raise HTTPException(status_code=500, detail="Could not generate voter journey.")
