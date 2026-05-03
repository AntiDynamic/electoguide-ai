"""
Fact-Check Route — /api/factcheck
====================================
AI-powered election myth vs. fact checker.
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from services.gemini_service import fact_check_claim

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Pre-loaded myth examples to showcase on the frontend
EXAMPLE_MYTHS = [
    "You need a photo ID to vote in every country.",
    "Election results are always decided on election night.",
    "Online voting is widely used in most democracies.",
    "Convicted felons can never vote again.",
    "The candidate with the most votes always wins the election.",
    "Voting machines are easily hacked during elections.",
    "Dead people regularly vote in elections.",
    "If you miss voter registration, you can still vote on Election Day anywhere.",
]


class FactCheckRequest(BaseModel):
    claim: str = Field(..., min_length=10, max_length=500)

    @field_validator("claim")
    @classmethod
    def sanitize_claim(cls, v: str) -> str:
        return v.strip()


@router.post("/factcheck")
@limiter.limit("20/minute")
async def fact_check(request: Request, body: FactCheckRequest) -> dict:
    """
    Fact-check an election-related claim using Gemini AI.

    - **claim**: The claim to verify (10–500 characters)

    Returns a verdict (TRUE / FALSE / PARTIALLY TRUE / MISLEADING / UNVERIFIABLE),
    an explanation, confidence score, and source hints.
    """
    try:
        result = await fact_check_claim(body.claim)
        return result

    except EnvironmentError as exc:
        logger.error(f"Config error in /api/factcheck: {exc}")
        raise HTTPException(status_code=503, detail="AI service not configured.")
    except ValueError as exc:
        logger.error(f"Parse error in /api/factcheck: {exc}")
        raise HTTPException(
            status_code=502, detail="Could not parse AI response. Please retry."
        )
    except Exception as exc:
        logger.exception(f"Unexpected error in /api/factcheck: {exc}")
        raise HTTPException(
            status_code=500, detail="Fact-check failed. Please try again."
        )


@router.get("/factcheck/examples")
async def get_examples() -> dict:
    """Return example myth claims for the frontend."""
    return {"examples": EXAMPLE_MYTHS}
