"""Health check endpoint."""

from datetime import datetime

from fastapi import APIRouter

from app.config import get_settings
from app.schemas.hcp import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        azure_configured=settings.azure_configured,
        gemini_configured=settings.gemini_configured,
        timestamp=datetime.utcnow(),
    )
