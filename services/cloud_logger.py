"""
Google Cloud Logging Service
==============================
Structured logging client for Cloud Run / Cloud Logging.
Falls back to standard Python logging when credentials are unavailable.
"""

import logging
import os
from typing import Any

_logger = logging.getLogger(__name__)
_cloud_client = None
_CLOUD_LOG_AVAILABLE: bool | None = None
_LOG_NAME = "electoguide-ai"


def _get_cloud_logger():
    """Lazily initialise the Cloud Logging client."""
    global _cloud_client, _CLOUD_LOG_AVAILABLE
    if _CLOUD_LOG_AVAILABLE is not None:
        return _cloud_client

    try:
        import google.cloud.logging as gcl

        project = os.getenv("GCP_PROJECT_ID", "promptwars-495214")
        client = gcl.Client(project=project)
        _cloud_client = client.logger(_LOG_NAME)
        _CLOUD_LOG_AVAILABLE = True
        _logger.info("✅ Cloud Logging client initialised")
    except Exception as exc:
        _CLOUD_LOG_AVAILABLE = False
        _logger.info("Cloud Logging unavailable, using local logging: %s", exc)

    return _cloud_client


def log_request(
    endpoint: str,
    method: str = "POST",
    status_code: int = 200,
    persona: str | None = None,
    session_id: str | None = None,
    duration_ms: float | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """
    Emit a structured log entry for an API request.
    Uses Cloud Logging when available, otherwise falls back to stdlib logging.
    """
    payload: dict[str, Any] = {
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "service": "electoguide-ai",
    }
    if persona:
        payload["persona"] = persona
    if session_id:
        payload["session_id"] = session_id
    if duration_ms is not None:
        payload["duration_ms"] = round(duration_ms, 2)
    if extra:
        payload.update(extra)

    cloud = _get_cloud_logger()
    if cloud:
        try:
            severity = (
                "ERROR"
                if status_code >= 500
                else "WARNING" if status_code >= 400 else "INFO"
            )
            cloud.log_struct(payload, severity=severity)
            return
        except Exception as exc:
            _logger.debug("Cloud Logging write failed: %s", exc)

    # Stdlib fallback as structured JSON
    import json

    _logger.info(
        "API %s %s → %d | %s", method, endpoint, status_code, json.dumps(payload)
    )
