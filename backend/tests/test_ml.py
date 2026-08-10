"""Tests for ML predictor."""

from app.config import Settings
from app.schemas.hcp import HCPProfile, MLFeatures, NPIData
from app.services.ml.predictor import InfluencePredictor, _tier_from_score


def test_tier_classification():
    assert _tier_from_score(80) == "Tier 1 KOL"
    assert _tier_from_score(55) == "Tier 2 KOL"
    assert _tier_from_score(30) == "Emerging Influencer"
    assert _tier_from_score(10) == "Standard HCP"


def test_predictor_training_and_inference(tmp_path):
    settings = Settings(ml_models_dir=tmp_path)
    predictor = InfluencePredictor(settings)
    metrics = predictor.train_all()
    assert "random_forest" in metrics
    assert "xgboost" in metrics

    profile = HCPProfile(
        npi="1234567890",
        identity=NPIData(npi="1234567890"),
        features=MLFeatures(
            publication_count=10,
            clinical_trial_count=3,
            collaborator_count=12,
            unique_collaborator_count=12,
            strongest_collaboration_count=4,
            average_collaboration_strength=1.5,
            collaboration_network_density=0.2,
            recurring_collaborator_ratio=0.25,
            years_active=15,
        ),
    )
    predictions = predictor.predict(profile)
    assert len(predictions) == 2
    for p in predictions:
        assert 0 <= p.influence_score <= 100
        assert p.kol_tier
