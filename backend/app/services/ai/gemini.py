"""Google Gemini client used for final-profile quality validation."""

import logging

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

# Fallbacks for accounts where pinned model IDs are unavailable to new users.
JUDGE_MODEL_FALLBACKS = ("gemini-flash-latest", "gemini-3.5-flash", "gemini-2.5-flash-lite")


class GeminiService:
    """Client for Gemini's native GenerateContent API."""

    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def is_configured(self) -> bool:
        return self.settings.gemini_configured

    def judge(self, system: str, user: str) -> str:
        if not self.is_configured:
            raise RuntimeError("Gemini is not configured. Set GEMINI_API_KEY.")

        models = self._candidate_models()
        last_error: Exception | None = None

        for model in models:
            try:
                return self._generate(model, system, user)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                if exc.response.status_code == 404:
                    logger.warning("Gemini model unavailable for this account: %s", model)
                    continue
                raise self._http_error(exc) from exc
            except Exception as exc:
                last_error = exc
                raise

        raise RuntimeError(
            f"No Gemini judge model available. Tried: {', '.join(models)}. "
            f"Last error: {last_error}"
        )

    def _candidate_models(self) -> tuple[str, ...]:
        configured = self.settings.gemini_judge_model.strip()
        models: list[str] = [configured] if configured else []
        for model in JUDGE_MODEL_FALLBACKS:
            if model not in models:
                models.append(model)
        return tuple(models)

    def _generate(self, model: str, system: str, user: str) -> str:
        response = httpx.post(
            f"{self.settings.gemini_base_url.rstrip('/')}/models/{model}:generateContent",
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.settings.gemini_api_key,
            },
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {
                    "temperature": 0,
                    "responseMimeType": "application/json",
                },
            },
            timeout=60.0,
        )
        response.raise_for_status()
        candidates = response.json().get("candidates", [])
        if not candidates:
            raise ValueError("Gemini returned no candidate response")
        parts = candidates[0].get("content", {}).get("parts", [])
        content = "".join(part.get("text", "") for part in parts)
        if not content:
            raise ValueError("Gemini returned an empty response")
        return content

    @staticmethod
    def _http_error(exc: httpx.HTTPStatusError) -> RuntimeError:
        detail = exc.response.text[:300]
        try:
            detail = exc.response.json().get("error", {}).get("message", detail)
        except Exception:
            pass
        return RuntimeError(f"Gemini API error ({exc.response.status_code}): {detail}")
