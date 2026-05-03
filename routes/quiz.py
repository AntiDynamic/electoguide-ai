"""
Quiz Route — /api/quiz
========================
AI-generated adaptive quiz questions about election topics.
"""

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address

from services.gemini_service import generate_quiz

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

VALID_DIFFICULTIES = {"easy", "medium", "hard"}
QUIZ_TOPICS = {
    "voter_registration": "Voter Registration Process",
    "ballot_types": "Types of Ballots",
    "electoral_systems": "Electoral Systems Around the World",
    "election_timeline": "Election Timeline and Deadlines",
    "civic_rights": "Civic Rights and Responsibilities",
    "election_officials": "Election Officials and Their Roles",
    "election_security": "Election Security and Integrity",
    "general": "General Election Knowledge",
}


class QuizRequest(BaseModel):
    topic: str = Field(default="general", max_length=100)
    difficulty: str = Field(default="medium")
    count: int = Field(default=5, ge=3, le=10)

    @field_validator("topic")
    @classmethod
    def sanitize_topic(cls, v: str) -> str:
        return v.strip()

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        if v not in VALID_DIFFICULTIES:
            return "medium"
        return v


@router.post("/quiz")
@limiter.limit("15/minute")
async def create_quiz(request: Request, body: QuizRequest) -> dict:
    """
    Generate an adaptive quiz about election topics.

    - **topic**: Quiz topic (e.g. voter_registration, electoral_systems, general)
    - **difficulty**: `easy` | `medium` | `hard`
    - **count**: Number of questions (3–10)
    """
    try:
        # Map slug to full topic name if applicable
        topic_label = QUIZ_TOPICS.get(body.topic, body.topic)

        result = await generate_quiz(
            topic=topic_label,
            difficulty=body.difficulty,
            count=body.count,
        )
        return result

    except EnvironmentError as exc:
        logger.error(f"Config error in /api/quiz: {exc}")
        raise HTTPException(status_code=503, detail="AI service not configured.")
    except ValueError as exc:
        logger.error(f"Parse error in /api/quiz: {exc}")
        raise HTTPException(status_code=502, detail="Could not parse AI response. Please retry.")
    except Exception as exc:
        logger.exception(f"Unexpected error in /api/quiz: {exc}")
        raise HTTPException(status_code=500, detail="Quiz generation failed. Please try again.")


@router.get("/quiz/topics")
async def list_topics() -> dict:
    """Return available quiz topic slugs and their display names."""
    return {"topics": [{"slug": k, "label": v} for k, v in QUIZ_TOPICS.items()]}
