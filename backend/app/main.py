"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, hcp
from app.config import get_settings
from app.logging_config import setup_logging
from app.services.ml.predictor import InfluencePredictor


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.debug)
    predictor = InfluencePredictor(settings)
    rf_path = settings.ml_models_dir / "random_forest.joblib"
    if not rf_path.exists():
        predictor.train_all()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-Powered Healthcare Professional Intelligence Platform",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(hcp.router, prefix=settings.api_prefix)

    return app


app = create_app()
