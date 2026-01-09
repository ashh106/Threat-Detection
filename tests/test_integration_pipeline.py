import json
from pathlib import Path
from train import train
from src.anomaly_scorer import AnomalyScorer


def test_train_and_score(tmp_path):
    # Setup temp config using the repo fixtures created earlier
    cfg = {
        "data": {
            "raw_dir": "data/raw",
            "processed_dir": str(tmp_path / "processed"),
            "features_dir": str(tmp_path / "features"),
            "models_dir": str(tmp_path / "models"),
            "files": {"email": "email.csv", "psychometric": "psychometric.csv"}
        },
        "features": {"aggregation_window": "1D"},
    }

    Path(cfg["data"]["features_dir"]).mkdir(parents=True, exist_ok=True)
    Path(cfg["data"]["models_dir"]).mkdir(parents=True, exist_ok=True)

    # Ensure a minimal email.csv exists so training can run
    import pandas as pd
    email_df = pd.DataFrame({
        "user": ["user1"] * 12,
        "timestamp": pd.date_range("2020-01-01", periods=12, freq="D"),
        "from": ["user1@example.com"] * 12,
        "to": ["user2@example.com"] * 12,
        "size": [1024] * 12
    })
    Path("data/raw/email.csv").parent.mkdir(parents=True, exist_ok=True)
    email_df.to_csv("data/raw/email.csv", index=False)

    # Run training (should use small fixtures in data/raw)
    train(cfg)

    # Verify model file exists
    model_file = Path(cfg["data"]["models_dir"]) / "baselines.pkl"
    assert model_file.exists()

    # Load model and do a basic scoring operation
    from src.distribution_builder import DistributionBuilder

    builder = DistributionBuilder.load(str(model_file))
    scorer = AnomalyScorer(builder)

    # Create a fake event dataframe with a single row
    features = pd.DataFrame([{"user": list(builder.personal_distributions.keys())[0],
                              "date_only": pd.to_datetime("2020-01-01"),
                              "email_sent_count": 1.0}])

    out = scorer.score_dataframe(features)
    assert "anomaly_score" in out.columns
