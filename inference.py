"""
Inference Pipeline (Aligned)

Runs anomaly detection using trained behavioral baselines.

Author: Behavioral Analytics Team
"""

import argparse
import logging
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

from src.data_loader import CERTDataLoader
from src.feature_engineering import BehavioralFeatureEngineer
from src.distribution_builder import DistributionBuilder
from src.anomaly_scorer import AnomalyScorer, RealTimeScorer
from src.visualizer import BehavioralVisualizer


# ------------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------------
def setup_logging(log_file: str):
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )


# ------------------------------------------------------------------
# LOAD MODELS
# ------------------------------------------------------------------
def load_models(model_path: str) -> DistributionBuilder:
    logger = logging.getLogger(__name__)
    logger.info(f"Loading trained baselines from {model_path}")
    return DistributionBuilder.load(model_path)


# ------------------------------------------------------------------
# BATCH INFERENCE
# ------------------------------------------------------------------
def batch_inference(
    input_path: str,
    model_path: str,
    output_dir: str,
    generate_visualizations: bool = True,
):
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("BATCH INFERENCE")
    logger.info("=" * 60)

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Load models
    builder = load_models(model_path)
    scorer = AnomalyScorer(builder)

    # Load data
    logger.info("Loading input data")

    if Path(input_path).is_dir():
        loader = CERTDataLoader(input_path)
        raw_data = loader.load_all()

        engineer = BehavioralFeatureEngineer("1D")
        features = engineer.create_unified_feature_matrix(raw_data)
    else:
        features = pd.read_csv(input_path)
        features["date_only"] = pd.to_datetime(features["date_only"])

    logger.info(f"Observations loaded: {len(features)}")

    # Score
    logger.info("Scoring observations")
    results = scorer.score_dataframe(features)

    # Save output
"""
Inference Pipeline (Aligned)

Runs anomaly detection using trained behavioral baselines.

Author: Behavioral Analytics Team
"""

import argparse
import logging
import json
from pathlib import Path
from datetime import datetime
import pandas as pd

from src.data_loader import CERTDataLoader
from src.feature_engineering import BehavioralFeatureEngineer
from src.distribution_builder import DistributionBuilder
from src.anomaly_scorer import AnomalyScorer, RealTimeScorer
from src.visualizer import BehavioralVisualizer


# ------------------------------------------------------------------
# LOGGING
# ------------------------------------------------------------------
def setup_logging(log_file: str):
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )


# ------------------------------------------------------------------
# LOAD MODELS
# ------------------------------------------------------------------
def load_models(model_path: str) -> DistributionBuilder:
    logger = logging.getLogger(__name__)
    logger.info(f"Loading trained baselines from {model_path}")
    return DistributionBuilder.load(model_path)


# ------------------------------------------------------------------
# BATCH INFERENCE
# ------------------------------------------------------------------
def batch_inference(
    input_path: str,
    model_path: str,
    output_dir: str,
    generate_visualizations: bool = True,
):
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("BATCH INFERENCE")
    logger.info("=" * 60)

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Load models
    builder = load_models(model_path)
    scorer = AnomalyScorer(builder)

    # Load data
    logger.info("Loading input data")

    if Path(input_path).is_dir():
        loader = CERTDataLoader(input_path)
        raw_data = loader.load_all()

        engineer = BehavioralFeatureEngineer("1D")
        features = engineer.create_unified_feature_matrix(raw_data)
    else:
        features = pd.read_csv(input_path)
        features["date_only"] = pd.to_datetime(features["date_only"])

    logger.info(f"Observations loaded: {len(features)}")

    # Score
    logger.info("Scoring observations")
    results = scorer.score_dataframe(features)

    # Save outputs
    results_path = Path(output_dir) / "anomaly_scores.csv"
    results.to_csv(results_path, index=False)

    alerts = results[results["severity"].isin(["HIGH", "CRITICAL"])]
    alerts_path = Path(output_dir) / "alerts.csv"
    alerts.to_csv(alerts_path, index=False)

    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_observations": len(results),
        "alerts": len(alerts),
        "severity_distribution": results["severity"].value_counts().to_dict(),
        "mean_anomaly_score": float(results["anomaly_score"].mean()),
    }

    with open(Path(output_dir) / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Results saved → {output_dir}")

    # Visualizations
    if generate_visualizations:
        viz = BehavioralVisualizer(builder)
        viz.create_dashboard(results, save_dir=f"{output_dir}/dashboard")

    logger.info("=" * 60)
    logger.info("INFERENCE COMPLETE")
    logger.info("=" * 60)


# ------------------------------------------------------------------
# REAL-TIME DEMO MODE
# ------------------------------------------------------------------
def realtime_inference(model_path: str, alert_threshold: float = 0.7):
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("REAL-TIME INFERENCE (DEMO)")
    logger.info("=" * 60)

    builder = load_models(model_path)
    scorer = RealTimeScorer(builder)
    scorer.alert_threshold = alert_threshold

    demo_event = {
        "user": "USER001",
        "timestamp": datetime.now(),
        "features": {
            "email_sent_count": 45,
            "unique_recipients_count": 38,
            "attachments_count": 10,
        },
    }

    result = scorer.score_event(demo_event)

    if result["alert"]:
        logger.warning(
            f"🚨 ALERT → {result['user']} | "
            f"Score={result['anomaly_score']:.2f} | "
            f"{result['severity']}"
        )
        logger.warning(result["explanation"])
    else:
        logger.info("No alert triggered")

    logger.info("Demo complete")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Run inference")
    parser.add_argument("--model", default="models/distributions/baselines.pkl")
    parser.add_argument("--input", help="CSV file or raw data directory")
    parser.add_argument("--output", default="results")
    parser.add_argument("--realtime", action="store_true")
    parser.add_argument("--no-viz", action="store_true")
    parser.add_argument("--log-file", default="logs/inference.log")

    args = parser.parse_args()
    setup_logging(args.log_file)

    if args.realtime:
        realtime_inference(args.model)
    else:
        if not args.input:
            raise ValueError("--input is required for batch mode")

        batch_inference(
            input_path=args.input,
            model_path=args.model,
            output_dir=args.output,
            generate_visualizations=not args.no_viz,
        )


if __name__ == "__main__":
    main()
