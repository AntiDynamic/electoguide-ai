"""Tests for chat, sessions, translation, and system endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app

client = TestClient(app)


# ── Health & Config ───────────────────────────────────────────────────────────


def test_health_check():
    r = client.get("/health")
    assert r.status_code == 200
    d = r.json()
    assert d["status"] == "healthy"
    assert "model" in d
    assert "version" in d


def test_config_endpoint():
    r = client.get("/api/config")
    assert r.status_code == 200
    d = r.json()
    assert "model" in d
    assert "version" in d


# ── Chat Tests ────────────────────────────────────────────────────────────────


def test_chat_empty_message_rejected():
    r = client.post("/api/chat", json={"message": ""})
    assert r.status_code == 422


def test_chat_message_too_long():
    r = client.post("/api/chat", json={"message": "x" * 2001})
    assert r.status_code == 422


@pytest.mark.parametrize(
    "persona", ["student", "first_voter", "researcher", "senior", "general"]
)
def test_chat_all_personas(persona):
    with patch(
        "routes.chat.generate_chat_response", new_callable=AsyncMock
    ) as mock_ai, patch(
        "routes.chat.extract_entities", new_callable=AsyncMock
    ) as mock_nl:
        mock_ai.return_value = f"Response for {persona}"
        mock_nl.return_value = []
        r = client.post(
            "/api/chat",
            json={"message": "How do I register to vote?", "persona": persona},
        )
        assert r.status_code == 200
        assert r.json()["persona"] == persona


def test_chat_invalid_persona_falls_back_to_general():
    with patch(
        "routes.chat.generate_chat_response", new_callable=AsyncMock
    ) as mock_ai, patch(
        "routes.chat.extract_entities", new_callable=AsyncMock
    ) as mock_nl:
        mock_ai.return_value = "Test response"
        mock_nl.return_value = []
        r = client.post(
            "/api/chat", json={"message": "What is an election?", "persona": "INVALID"}
        )
        assert r.status_code == 200
        assert r.json()["persona"] == "general"


def test_chat_returns_entities():
    with patch(
        "routes.chat.generate_chat_response", new_callable=AsyncMock
    ) as mock_ai, patch(
        "routes.chat.extract_entities", new_callable=AsyncMock
    ) as mock_nl:
        mock_ai.return_value = "India has a parliamentary system."
        mock_nl.return_value = ["India", "Parliament"]
        r = client.post(
            "/api/chat", json={"message": "Tell me about India's elections"}
        )
        assert r.status_code == 200
        assert "entities" in r.json()


def test_chat_with_history():
    with patch(
        "routes.chat.generate_chat_response", new_callable=AsyncMock
    ) as mock_ai, patch(
        "routes.chat.extract_entities", new_callable=AsyncMock
    ) as mock_nl:
        mock_ai.return_value = "Here is more info."
        mock_nl.return_value = []
        r = client.post(
            "/api/chat",
            json={
                "message": "Tell me more",
                "history": [
                    {"role": "user", "content": "What is voting?"},
                    {"role": "model", "content": "Voting is a right..."},
                ],
            },
        )
        assert r.status_code == 200


def test_chat_gemini_unavailable_returns_503():
    with patch(
        "routes.chat.generate_chat_response", new_callable=AsyncMock
    ) as mock_ai, patch(
        "routes.chat.extract_entities", new_callable=AsyncMock
    ) as mock_nl:
        mock_ai.side_effect = EnvironmentError("No API key")
        mock_nl.return_value = []
        r = client.post("/api/chat", json={"message": "What is an election?"})
        assert r.status_code == 503


# ── Sessions Tests ────────────────────────────────────────────────────────────


def test_create_session():
    with patch(
        "routes.sessions.fs.create_session", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = {
            "session_id": "test-uuid-1234-5678-abcd",
            "persona": "general",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
        r = client.post("/api/sessions", json={"persona": "general"})
        assert r.status_code == 200
        assert "session_id" in r.json()


def test_session_status():
    """Test standard session path fallback mapping."""
    r = client.get("/api/sessions/info")
    assert r.status_code == 200


def test_security_headers():
    """Test that security headers middleware injects correctly."""
    r = client.get("/health")
    assert r.status_code == 200
    assert (
        r.headers.get("Strict-Transport-Security")
        == "max-age=31536000; includeSubDomains"
    )
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("X-XSS-Protection") == "1; mode=block"


# ── Translation Tests ─────────────────────────────────────────────────────────


def test_translate_languages_list():
    r = client.get("/api/translate/languages")
    assert r.status_code == 200
    data = r.json()
    assert "languages" in data
    assert len(data["languages"]) >= 10


def test_translate_same_language_passthrough():
    with patch("routes.translate.translate_text", new_callable=AsyncMock) as mock_t:
        mock_t.return_value = {"translated_text": "Hello", "used_cloud": False}
        r = client.post(
            "/api/translate",
            json={"text": "Hello", "target_language": "en", "source_language": "en"},
        )
        assert r.status_code == 200


def test_translate_text_too_long():
    r = client.post(
        "/api/translate", json={"text": "x" * 10001, "target_language": "fr"}
    )
    assert r.status_code == 422


def test_translate_empty_text_rejected():
    r = client.post("/api/translate", json={"text": "", "target_language": "hi"})
    assert r.status_code == 422


# ── Quiz Tests ────────────────────────────────────────────────────────────────

MOCK_QUIZ = {
    "topic": "General Election Knowledge",
    "difficulty": "medium",
    "questions": [
        {
            "id": 1,
            "question": "?",
            "options": ["A", "B", "C", "D"],
            "correct": 0,
            "explanation": "Because.",
        }
    ],
}


def test_quiz_topics():
    r = client.get("/api/quiz/topics")
    assert r.status_code == 200
    assert len(r.json()["topics"]) > 0


def test_quiz_valid_request():
    with patch("routes.quiz.generate_quiz", new_callable=AsyncMock) as m:
        m.return_value = MOCK_QUIZ
        r = client.post(
            "/api/quiz", json={"topic": "general", "difficulty": "medium", "count": 5}
        )
        assert r.status_code == 200


def test_quiz_count_too_high():
    r = client.post("/api/quiz", json={"count": 20})
    assert r.status_code == 422


# ── Fact Check Tests ──────────────────────────────────────────────────────────


def test_factcheck_examples():
    r = client.get("/api/factcheck/examples")
    assert r.status_code == 200
    assert len(r.json()["examples"]) > 0


def test_factcheck_valid_claim():
    with patch("routes.factcheck.fact_check_claim", new_callable=AsyncMock) as m:
        m.return_value = {
            "verdict": "FALSE",
            "explanation": "...",
            "confidence": 90,
            "claim": "test",
            "sources_hint": "gov websites",
            "context": "ctx",
        }
        r = client.post(
            "/api/factcheck", json={"claim": "Dead people regularly vote in elections."}
        )
        assert r.status_code == 200
        assert r.json()["verdict"] in [
            "TRUE",
            "FALSE",
            "PARTIALLY TRUE",
            "MISLEADING",
            "UNVERIFIABLE",
        ]


def test_factcheck_claim_too_short():
    r = client.post("/api/factcheck", json={"claim": "No"})
    assert r.status_code == 422


# ── Countries Tests ───────────────────────────────────────────────────────────


def test_countries_list():
    r = client.get("/api/countries")
    assert r.status_code == 200
    assert len(r.json()["countries"]) >= 10


def test_get_country():
    with patch(
        "routes.countries.get_country_election_info", new_callable=AsyncMock
    ) as m:
        m.return_value = {"country": "India", "voting_age": 18, "key_steps": []}
        r = client.get("/api/countries/India")
        assert r.status_code == 200


# ── TTS Tests ─────────────────────────────────────────────────────────────────


def test_tts_status():
    r = client.get("/api/tts/status")
    assert r.status_code == 200


def test_tts_browser_fallback():
    with patch("routes.tts.synthesize_speech", new_callable=AsyncMock) as m:
        m.return_value = None
        r = client.post("/api/tts", json={"text": "Welcome to ElectoGuide AI!"})
        assert r.status_code == 200
        assert r.json()["use_browser_tts"] is True


def test_tts_text_too_long():
    r = client.post("/api/tts", json={"text": "x" * 5001})
    assert r.status_code == 422
