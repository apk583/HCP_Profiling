"""Feature vector extraction for ML models."""

from app.schemas.hcp import MLFeatures

FEATURE_NAMES = [
    "publication_count",
    "first_author_count",
    "clinical_trial_count",
    "pi_trial_count",
    "collaborator_count",
    "unique_collaborator_count",
    "strongest_collaboration_count",
    "average_collaboration_strength",
    "collaboration_network_density",
    "recurring_collaborator_ratio",
    "years_active",
    "adverse_event_reports",
]


def features_to_vector(features: MLFeatures) -> list[float]:
    return [float(getattr(features, name)) for name in FEATURE_NAMES]


def vector_to_dict(vector: list[float]) -> dict[str, float]:
    return dict(zip(FEATURE_NAMES, vector))
