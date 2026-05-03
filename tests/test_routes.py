"""Tests for quiz, factcheck, TTS, and countries endpoints."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app

client = TestClient(app)

# ── Quiz Tests ─────────────────────────────────────────────────────────────────

MOCK_QUIZ = {
    "topic": "General Election Knowledge",
    "difficulty": "medium",
    "questions": [
        {
            "id": 1,
            "question": "What is the minimum voting age in most democracies?",
            "options": ["16", "17", "18", "21"],
            "correct": 2,
            "explanation": "Most democracies set the voting age at 18."
        }
    ]
}


def test_quiz_topics_endpoint():
    response = client.get("/api/quiz/topics")
    assert response.status_code == 200
    assert "topics" in response.json()
    assert len(response.json()["topics"]) > 0


def test_quiz_valid_request():
    with patch("routes.quiz.generate_quiz", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = MOCK_QUIZ
        response = client.post("/api/quiz", json={"topic": "general", "difficulty": "medium", "count": 5})
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data


def test_quiz_count_out_of_range():
    response = client.post("/api/quiz", json={"topic": "general", "difficulty": "medium", "count": 20})
    assert response.status_code == 422


def test_quiz_invalid_difficulty_defaults():
    with patch("routes.quiz.generate_quiz", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = MOCK_QUIZ
        response = client.post("/api/quiz", json={"topic": "general", "difficulty": "impossible", "count": 3})
        assert response.status_code == 200  # defaults to medium


# ── Fact-Check Tests ──────────────────────────────────────────────────────────

MOCK_FACTCHECK = {
    "claim": "You need ID to vote everywhere",
    "verdict": "FALSE",
    "explanation": "ID requirements vary widely by country.",
    "confidence": 90,
    "sources_hint": "Government election websites",
    "context": "Some countries require ID, others use voter rolls."
}


def test_factcheck_examples_endpoint():
    response = client.get("/api/factcheck/examples")
    assert response.status_code == 200
    assert "examples" in response.json()
    assert len(response.json()["examples"]) > 0


def test_factcheck_valid_claim():
    with patch("routes.factcheck.fact_check_claim", new_callable=AsyncMock) as mock_fc:
        mock_fc.return_value = MOCK_FACTCHECK
        response = client.post("/api/factcheck", json={"claim": "You need a photo ID to vote in every country."})
        assert response.status_code == 200
        data = response.json()
        assert "verdict" in data
        assert data["verdict"] in ["TRUE", "FALSE", "PARTIALLY TRUE", "MISLEADING", "UNVERIFIABLE"]


def test_factcheck_claim_too_short():
    response = client.post("/api/factcheck", json={"claim": "No"})
    assert response.status_code == 422


def test_factcheck_claim_too_long():
    response = client.post("/api/factcheck", json={"claim": "x" * 501})
    assert response.status_code == 422


# ── Countries Tests ───────────────────────────────────────────────────────────

MOCK_COUNTRY = {
    "country": "India",
    "flag_emoji": "🇮🇳",
    "system_type": "Federal Parliamentary Republic",
    "electoral_system": "First Past the Post",
    "voting_age": 18,
    "election_frequency_years": 5,
    "registration_required": True,
    "compulsory_voting": False,
    "key_steps": ["Register on voter rolls", "Receive voter ID card", "Visit polling booth"],
    "timeline": [{"phase": "Election Day", "timing": "Day 0", "description": "Cast your vote"}],
    "unique_features": ["World's largest democracy", "Electronic Voting Machines (EVMs)"],
    "fun_fact": "India conducts the world's largest elections."
}


def test_countries_list():
    response = client.get("/api/countries")
    assert response.status_code == 200
    data = response.json()
    assert "countries" in data
    assert len(data["countries"]) >= 10


def test_get_country_info():
    with patch("routes.countries.get_country_election_info", new_callable=AsyncMock) as mock_ci:
        mock_ci.return_value = MOCK_COUNTRY
        response = client.get("/api/countries/India")
        assert response.status_code == 200
        data = response.json()
        assert "voting_age" in data


def test_get_country_invalid_name():
    response = client.get("/api/countries/A")  # Too short
    assert response.status_code in [400, 422]


# ── TTS Tests ─────────────────────────────────────────────────────────────────

def test_tts_status():
    response = client.get("/api/tts/status")
    assert response.status_code == 200
    data = response.json()
    assert "cloud_tts_available" in data
    assert "fallback" in data


def test_tts_browser_fallback():
    """When Cloud TTS is unavailable, should return browser fallback instruction."""
    with patch("routes.tts.synthesize_speech", new_callable=AsyncMock) as mock_tts:
        mock_tts.return_value = None  # Simulate unavailable
        response = client.post("/api/tts", json={"text": "Welcome to ElectoGuide AI!"})
        assert response.status_code == 200
        data = response.json()
        assert data["use_browser_tts"] is True
        assert "text" in data


def test_tts_text_too_long():
    response = client.post("/api/tts", json={"text": "x" * 5001})
    assert response.status_code == 422


def test_tts_invalid_speaking_rate():
    response = client.post("/api/tts", json={"text": "Hello", "speaking_rate": 10.0})
    assert response.status_code == 422


# ── Health & Config Tests ─────────────────────────────────────────────────────

def test_app_config_endpoint():
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "model" in data
    assert "version" in data
