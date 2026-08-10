"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Resolve this independently of the directory from which Uvicorn was started.
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "HCP Intelligence Platform"
    app_version: str = "1.0.0"
    debug: bool = False
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Groq API
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    # Google Gemini (used exclusively for final-profile validation)
    gemini_api_key: str = ""
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    gemini_judge_model: str = "gemini-flash-latest"

    # External APIs
    npi_registry_base_url: str = "https://npiregistry.cms.hhs.gov/api/"
    pubmed_base_url: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    clinical_trials_base_url: str = "https://clinicaltrials.gov/api/v2/"
    openfda_base_url: str = "https://api.fda.gov/"

    # HTTP client
    http_timeout_seconds: float = 30.0
    http_max_retries: int = 3

    # ML artifacts
    ml_models_dir: Path = Path("models")
    ml_default_model: str = "xgboost"

    # PDF output
    pdf_output_dir: Path = Path("output/pdfs")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def groq_configured(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
