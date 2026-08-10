"""ML model training and inference for HCP influence prediction."""

import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor

from app.config import Settings
from app.schemas.hcp import HCPProfile, MLFeatures, MLPrediction
from app.services.ml.features import FEATURE_NAMES, features_to_vector

logger = logging.getLogger(__name__)


def _generate_synthetic_dataset(n_samples: int = 500) -> pd.DataFrame:
    """Generate synthetic training data when no real labels exist."""
    rng = np.random.default_rng(42)
    data = {
        "publication_count": rng.integers(0, 50, n_samples),
        "first_author_count": rng.integers(0, 20, n_samples),
        "clinical_trial_count": rng.integers(0, 15, n_samples),
        "pi_trial_count": rng.integers(0, 8, n_samples),
        "collaborator_count": rng.integers(0, 150, n_samples),
        "unique_collaborator_count": rng.integers(0, 150, n_samples),
        "strongest_collaboration_count": rng.integers(0, 30, n_samples),
        "average_collaboration_strength": rng.uniform(0, 10, n_samples),
        "collaboration_network_density": rng.uniform(0, 1, n_samples),
        "recurring_collaborator_ratio": rng.uniform(0, 1, n_samples),
        "years_active": rng.integers(1, 40, n_samples),
        "adverse_event_reports": rng.integers(0, 20, n_samples),
    }
    df = pd.DataFrame(data)
    df["influence_score"] = (
        df["publication_count"] * 1.5
        + df["first_author_count"] * 2.0
        + df["clinical_trial_count"] * 3.0
        + df["pi_trial_count"] * 5.0
        + df["unique_collaborator_count"] * 0.25
        + df["strongest_collaboration_count"] * 1.2
        + df["average_collaboration_strength"] * 2.0
        + df["collaboration_network_density"] * 12.0
        + df["recurring_collaborator_ratio"] * 8.0
        + df["years_active"] * 0.5
    )
    df["influence_score"] = np.clip(df["influence_score"], 0, 100)
    return df


def _tier_from_score(score: float) -> str:
    if score >= 75:
        return "Tier 1 KOL"
    if score >= 50:
        return "Tier 2 KOL"
    if score >= 25:
        return "Emerging Influencer"
    return "Standard HCP"


class InfluencePredictor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.models_dir = settings.ml_models_dir
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._models: dict[str, object] = {}

    def train_all(self) -> dict[str, dict[str, float]]:
        df = _generate_synthetic_dataset()
        X = df[FEATURE_NAMES].values
        y = df["influence_score"].values
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        metrics: dict[str, dict[str, float]] = {}

        rf = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
        rf.fit(X_train, y_train)
        rf_pred = rf.predict(X_test)
        metrics["random_forest"] = {
            "mae": float(mean_absolute_error(y_test, rf_pred)),
            "r2": float(r2_score(y_test, rf_pred)),
        }
        joblib.dump(rf, self.models_dir / "random_forest.joblib")
        self._models["random_forest"] = rf

        xgb = XGBRegressor(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            n_jobs=-1,
        )
        xgb.fit(X_train, y_train)
        xgb_pred = xgb.predict(X_test)
        metrics["xgboost"] = {
            "mae": float(mean_absolute_error(y_test, xgb_pred)),
            "r2": float(r2_score(y_test, xgb_pred)),
        }
        joblib.dump(xgb, self.models_dir / "xgboost.joblib")
        self._models["xgboost"] = xgb

        logger.info("Model training complete: %s", metrics)
        return metrics

    def _load_model(self, name: str):
        if name in self._models:
            return self._models[name]
        path = self.models_dir / f"{name}.joblib"
        if not path.exists():
            logger.info("Model %s not found, training models...", name)
            self.train_all()
        model = joblib.load(path)
        if getattr(model, "n_features_in_", len(FEATURE_NAMES)) != len(FEATURE_NAMES):
            logger.info("Model %s uses retired features; retraining...", name)
            self.train_all()
            model = self._models[name]
        self._models[name] = model
        return model

    def predict(self, profile: HCPProfile) -> list[MLPrediction]:
        vector = np.array([features_to_vector(profile.features)])
        predictions: list[MLPrediction] = []

        for model_name in ("random_forest", "xgboost"):
            model = self._load_model(model_name)
            score = float(np.clip(model.predict(vector)[0], 0, 100))

            importance: dict[str, float] = {}
            if hasattr(model, "feature_importances_"):
                importance = dict(
                    zip(FEATURE_NAMES, [round(float(v), 4) for v in model.feature_importances_])
                )

            predictions.append(
                MLPrediction(
                    model_name=model_name,
                    influence_score=round(score, 2),
                    kol_tier=_tier_from_score(score),
                    confidence=0.85 if model_name == "xgboost" else 0.80,
                    feature_importance=importance,
                )
            )
        return predictions

    def get_best_prediction(self, profile: HCPProfile) -> MLPrediction:
        preds = self.predict(profile)
        default = self.settings.ml_default_model
        for p in preds:
            if p.model_name == default:
                return p
        return preds[0]
