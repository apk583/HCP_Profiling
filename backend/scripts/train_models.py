"""CLI script to train ML models."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.services.ml.predictor import InfluencePredictor


def main():
    settings = get_settings()
    predictor = InfluencePredictor(settings)
    metrics = predictor.train_all()
    print("Training complete:")
    for model, scores in metrics.items():
        print(f"  {model}: MAE={scores['mae']:.3f}, R²={scores['r2']:.3f}")


if __name__ == "__main__":
    main()
