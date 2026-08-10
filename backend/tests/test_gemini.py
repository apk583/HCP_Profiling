"""Tests for Gemini service model fallback."""

import httpx
import pytest

from app.config import Settings
from app.services.ai.gemini import GeminiService


def test_gemini_falls_back_when_configured_model_unavailable(httpx_mock):
    settings = Settings(
        gemini_api_key="test-key",
        gemini_judge_model="gemini-2.5-flash",
    )
    service = GeminiService(settings)

    httpx_mock.add_response(status_code=404, json={"error": {"message": "model unavailable"}})
    httpx_mock.add_response(
        json={
            "candidates": [
                {"content": {"parts": [{"text": '{"ok": true}'}]}}
            ]
        }
    )

    result = service.judge(system="Judge", user="Evaluate this")
    assert result == '{"ok": true}'
    assert len(httpx_mock.get_requests()) == 2


def test_gemini_raises_api_error_for_non_404(httpx_mock):
    settings = Settings(gemini_api_key="test-key", gemini_judge_model="gemini-flash-latest")
    service = GeminiService(settings)

    httpx_mock.add_response(status_code=401, json={"error": {"message": "API key not valid"}})

    with pytest.raises(RuntimeError, match="401"):
        service.judge(system="Judge", user="Evaluate this")
