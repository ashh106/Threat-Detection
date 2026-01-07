"""
Inference Pipeline (Final, Aligned)

Runs batch and real-time anomaly detection using trained
behavioral baselines.

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
    # File handler with utf-8 encoding and a stream handler that writes UTF-8 to the console
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
# LOAD MODEL
# ------------------------------------------------------------------
def load_model(model_path: str) -> DistributionBuilder:
    logger = logging.getLogger(__name__)
    logger.info(f"Loading trained baselines -> {model_path}")
    return DistributionBuilder.load(model_path)


# ------------------------------------------------------------------
# LOAD INPUT DATA
# ------------------------------------------------------------------
def load_input_data(input_path: str) -> pd.DataFrame:
    logger = logging.getLogger(__name__)

    if Path(input_path).is_dir():
        logger.info("Loading raw CERT data directory")
        loader = CERTDataLoader(input_path)
        raw_data = loader.load_all()

        engineer = BehavioralFeatureEngineer("1D")
        features = engineer.create_unified_feature_matrix(raw_data)
    else:
        logger.info("Loading feature CSV")
        features = pd.read_csv(input_path)

        if "date" in features.columns:
            features["date"] = pd.to_datetime(features["date"])
        elif "date_only" in features.columns:
            features["date_only"] = pd.to_datetime(features["date_only"])

    logger.info(
        f"Loaded {len(features)} observations | "
        f"Users: {features['user'].nunique()}"
    )

    return features


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

    # Load model
    builder = load_model(model_path)
    scorer = AnomalyScorer(builder)

    # Load data
    features = load_input_data(input_path)

    # Score
    logger.info("Scoring observations")
    results = scorer.score_dataframe(features)

    # ------------------------------------------------------------------
    # SAVE RESULTS
    # ------------------------------------------------------------------
    results_path = Path(output_dir) / "all_anomaly_scores.csv"
    results.to_csv(results_path, index=False)

    alerts = results[results["severity"].isin(["HIGH", "CRITICAL"])]
    alerts_path = Path(output_dir) / "high_priority_alerts.csv"
    alerts.to_csv(alerts_path, index=False)

    # Summary
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_observations": len(results),
        "unique_users": int(results["user"].nunique()),
        "high_risk_alerts": int(len(alerts)),
        "severity_distribution": results["severity"].value_counts().to_dict(),
        "mean_anomaly_score": float(results["anomaly_score"].mean()),
        "max_anomaly_score": float(results["anomaly_score"].max()),
        "top_user": (
            results.loc[results["anomaly_score"].idxmax(), "user"]
            if len(results) > 0
            else None
        ),
    }

    with open(Path(output_dir) / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Results saved -> {output_dir}")

    # ------------------------------------------------------------------
    # VISUALIZATION
    # ------------------------------------------------------------------
    if generate_visualizations:
        logger.info("Generating visualizations")
        viz = BehavioralVisualizer(builder)
        viz.create_dashboard(results, save_dir=f"{output_dir}/dashboard")

    logger.info("=" * 60)
    logger.info("BATCH INFERENCE COMPLETE")
    logger.info("=" * 60)


# ------------------------------------------------------------------
# REAL-TIME DEMO MODE
# ------------------------------------------------------------------
def realtime_inference(model_path: str, alert_threshold: float = 0.7):
    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("REAL-TIME INFERENCE (DEMO MODE)")
    logger.info("=" * 60)

    builder = load_model(model_path)
    scorer = RealTimeScorer(builder)
    scorer.alert_threshold = alert_threshold

    demo_event = {
        "user": "USER001",
        "timestamp": datetime.now(),
        "features": {
            "email_sent_count": 45,
            "unique_recipients_count": 38,
            "after_hours_email_count": 12,
        },
    }

    result = scorer.score_event(demo_event)

    if result["alert"]:
        logger.warning(
            f"ALERT -> {result['user']} | "
            f"Score={result['anomaly_score']:.2f} | "
            f"{result['severity']}"
        )
        logger.warning(result["explanation"])
    else:
        logger.info("No alert triggered")

    logger.info("Real-time demo complete")


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Behavioral Anomaly Inference")
    parser.add_argument("--model", default="models/distributions/baselines.pkl")
    parser.add_argument("--input", help="Feature CSV or raw data directory")
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
            raise ValueError("--input is required for batch inference")

        batch_inference(
            input_path=args.input,
            model_path=args.model,
            output_dir=args.output,
            generate_visualizations=not args.no_viz,
        )


if __name__ == "__main__":
    main()
