"""Tests for the chat endpoint."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data


def test_chat_invalid_empty_message():
    response = client.post("/api/chat", json={"message": ""})
    assert response.status_code == 422


def test_chat_message_too_long():
    response = client.post("/api/chat", json={"message": "x" * 2001})
    assert response.status_code == 422


def test_chat_invalid_persona_defaults_to_general():
    with patch("routes.chat.generate_chat_response", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Test response"
        response = client.post(
            "/api/chat",
            json={"message": "What is an election?", "persona": "INVALID"}
        )
        assert response.status_code == 200
        assert response.json()["persona"] == "general"


@pytest.mark.parametrize("persona", ["student", "first_voter", "researcher", "senior", "general"])
def test_chat_valid_personas(persona):
    with patch("routes.chat.generate_chat_response", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = f"Response for {persona}"
        response = client.post(
            "/api/chat",
            json={"message": "How do I register to vote?", "persona": persona}
        )
        assert response.status_code == 200
        assert response.json()["persona"] == persona


def test_chat_with_history():
    with patch("routes.chat.generate_chat_response", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = "Here is more info about voting."
        response = client.post("/api/chat", json={
            "message": "Tell me more",
            "persona": "general",
            "history": [
                {"role": "user", "content": "What is voting?"},
                {"role": "model", "content": "Voting is a civic right..."}
            ]
        })
        assert response.status_code == 200
        assert "response" in response.json()


def test_chat_service_error_returns_503():
    with patch("routes.chat.generate_chat_response", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = EnvironmentError("No API key")
        response = client.post("/api/chat", json={"message": "What is an election?"})
        assert response.status_code == 503
