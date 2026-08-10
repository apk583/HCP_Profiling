"""Quick Gemini connectivity check."""

import httpx
from dotenv import dotenv_values

from app.config import Settings
from app.services.ai.gemini import GeminiService

cfg = dotenv_values(".env")
settings = Settings(
    gemini_api_key=cfg.get("GEMINI_API_KEY", ""),
    gemini_base_url=cfg.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"),
    gemini_judge_model=cfg.get("GEMINI_JUDGE_MODEL", "gemini-flash-latest"),
)

service = GeminiService(settings)
result = service.judge(
    system='Return JSON only: {"ok": true}',
    user="Connectivity test",
)
print("success:", result[:120])
