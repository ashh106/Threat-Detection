"""
Training Pipeline (FINAL FIXED VERSION)

Email + Psychometric Insider Threat Detection
"""

import argparse
import logging
import yaml
from pathlib import Path
from datetime import datetime
import json

from src.data_loader import CERTDataLoader
from src.feature_engineering import BehavioralFeatureEngineer
from src.distribution_builder import DistributionBuilder
from src.anomaly_scorer import AnomalyScorer


# ------------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------------
def setup_logging(log_file: str):
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    # File handler uses UTF-8; ensure the console stream handler writes UTF-8
    import sys
    import io

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    stream_handler = logging.StreamHandler(
        stream=io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[file_handler, stream_handler],
    )


# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
def load_config(path: str) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


# ------------------------------------------------------------------
# TRAINING PIPELINE
# ------------------------------------------------------------------
def train(config: dict):
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("INSIDER THREAT DETECTION – TRAINING PIPELINE")
    logger.info("=" * 60)

    # --------------------------------------------------------------
    # STEP 1: LOAD DATA
    # --------------------------------------------------------------
    logger.info("[1/5] Loading raw data")

    loader = CERTDataLoader(config["data"]["raw_dir"])
    raw_data = loader.load_all()

    logger.info(f"Users loaded: {len(loader.get_user_list())}")

    # --------------------------------------------------------------
    # STEP 2: FEATURE ENGINEERING
    # --------------------------------------------------------------
    logger.info("[2/5] Feature engineering")

    engineer = BehavioralFeatureEngineer(
        aggregation_window=config["features"]["aggregation_window"]
    )

    features = engineer.create_unified_feature_matrix(raw_data)

    features_dir = Path(config["data"]["features_dir"])
    features_dir.mkdir(parents=True, exist_ok=True)

    features_path = features_dir / "behavioral_features.csv"
    features.to_csv(features_path, index=False)

    logger.info(f"Feature matrix saved -> {features_path}")
    logger.info(f"Shape: {features.shape}")

    # --------------------------------------------------------------
    # STEP 3: TRAIN / VALIDATION SPLIT
    # --------------------------------------------------------------
    logger.info("[3/5] Train / validation split")

    features = features.sort_values("date_only")
    split_idx = int(len(features) * 0.7)

    train_df = features.iloc[:split_idx]
    val_df = features.iloc[split_idx:]

    logger.info(f"Training samples: {len(train_df)}")
    logger.info(f"Validation samples: {len(val_df)}")

    # --------------------------------------------------------------
    # STEP 4: BUILD DISTRIBUTIONS (CORE TRAINING)
    # --------------------------------------------------------------
    logger.info("[4/5] Building behavioral baselines")

    # SAFE DEFAULT (can be overridden in config)
    min_obs = 10
    if "distributions" in config and "min_observations" in config["distributions"]:
        min_obs = int(config["distributions"]["min_observations"])

    builder = DistributionBuilder(min_observations=min_obs)

    # ✅ CORRECT METHOD NAMES
    builder.build_personal_distributions(train_df)

    if "psychometric" in raw_data:
        builder.build_peer_distributions(
            train_df,
            raw_data["psychometric"]
        )

    builder.build_temporal_distributions(train_df)

    logger.info(f"Personal models: {len(builder.personal_distributions)}")
    logger.info(f"Peer groups: {len(builder.peer_distributions)}")
    logger.info(f"Temporal buckets: {len(builder.temporal_distributions)}")

    # --------------------------------------------------------------
    # STEP 5: SAVE MODELS & METADATA
    # --------------------------------------------------------------
    logger.info("[5/5] Saving models")

    models_dir = Path(config["data"]["models_dir"])
    models_dir.mkdir(parents=True, exist_ok=True)

    model_path = models_dir / "baselines.pkl"
    builder.save(model_path)

    metadata = {
        "trained_at": datetime.now().isoformat(),
        "train_samples": len(train_df),
        "validation_samples": len(val_df),
        "users": len(builder.personal_distributions),
        "features": len(builder.feature_list),
        "peer_groups": len(builder.peer_distributions),
        "min_observations": min_obs,
    }

    with open(models_dir / "training_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Models saved -> {model_path}")

    # --------------------------------------------------------------
    # VALIDATION SCORING
    # --------------------------------------------------------------
    logger.info("Running validation scoring")

    scorer = AnomalyScorer(builder)
    val_scores = scorer.score_dataframe(val_df.head(1000))

    val_out = features_dir / "validation_results.csv"
    val_scores.to_csv(val_out, index=False)

    logger.info("Validation severity distribution:")
    logger.info(val_scores["severity"].value_counts().to_string())

    logger.info("=" * 60)
    logger.info("TRAINING COMPLETE")
    logger.info("=" * 60)
    logger.info("Next step: python inference.py")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Train insider threat model")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--log-file", default="logs/training.log")

    args = parser.parse_args()
    setup_logging(args.log_file)

    config = load_config(args.config)
    train(config)


if __name__ == "__main__":
    main()
