"""Groq API client wrapper."""

import logging

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


class GroqService:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def is_configured(self) -> bool:
        return self.settings.groq_configured

    def chat(self, model: str, system: str, user: str, temperature: float = 0.3) -> str:
        if not self.is_configured:
            raise RuntimeError("Groq is not configured. Set GROQ_API_KEY.")
        endpoint = "https://api.groq.com/openai/v1/chat/completions"
        response = httpx.post(
            endpoint,
            headers={"Authorization": f"Bearer {self.settings.groq_api_key}"},
            json={
                "model": model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": temperature,
            },
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"] or ""
