"""Tests for Gemini-backed LLM judge."""

import json

import httpx
import pytest

from app.config import Settings
from app.schemas.hcp import HCPProfile, NPIData
from app.services.ai.judge import SummaryJudge


@pytest.fixture
def gemini_settings():
    return Settings(
        gemini_api_key="test-key",
        gemini_base_url="https://generativelanguage.googleapis.com/v1beta",
        gemini_judge_model="gemini-flash-latest",
    )


def test_judge_uses_gemini_when_configured(gemini_settings, httpx_mock):
    judge_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "overall_score": 8.5,
                                    "groundedness": 8.0,
                                    "completeness": 9.0,
                                    "clarity": 8.5,
                                    "feedback": "Summary is well grounded.",
                                    "passed": True,
                                }
                            )
                        }
                    ]
                }
            }
        ]
    }
    httpx_mock.add_response(json=judge_response)

    judge = SummaryJudge(gemini_settings)
    profile = HCPProfile(npi="1234567890", identity=NPIData(npi="1234567890"))
    evaluation = judge.evaluate(profile, "Provider NPI 1234567890 summary.")

    assert evaluation.passed is True
    assert evaluation.overall_score == 8.5
    assert evaluation.judge_model == "gemini-flash-latest"
    assert len(httpx_mock.get_requests()) == 1
    request = httpx_mock.get_requests()[0]
    assert request.headers["x-goog-api-key"] == "test-key"
    assert "gemini-flash-latest:generateContent" in str(request.url)


def test_judge_heuristic_when_gemini_not_configured():
    judge = SummaryJudge(Settings(gemini_api_key=""))
    profile = HCPProfile(npi="1234567890", identity=NPIData(npi="1234567890"))
    evaluation = judge.evaluate(
        profile,
        "Provider NPI 1234567890 has a detailed profile summary.",
    )

    assert evaluation.judge_model == "Heuristic fallback"
    assert evaluation.overall_score > 0
