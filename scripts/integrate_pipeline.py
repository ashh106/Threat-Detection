"""Integration orchestrator for the combined pipeline.

Steps:
 - Train distributions using `train.train` (config.yaml)
 - Optionally run parso Stage-3 demo and Stage-4 demo (if requested)

This script is intended for local integration testing and quick demos (no Kafka required for demo modes).
"""
import argparse
import logging
import yaml
from pathlib import Path

from train import load_config, setup_logging, train
from src.extensions.parso import run_stage3_demo, run_stage4_demo


def main():
    parser = argparse.ArgumentParser(description="Integrate and run full pipeline (train + optional demos)")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--log-file", default="logs/integrate_pipeline.log")
    parser.add_argument("--stage3", action="store_true", help="Run Stage-3 demo after training")
    parser.add_argument("--stage4", action="store_true", help="Run Stage-4 demo after training")
    parser.add_argument("--relax", action="store_true", help="Relax distribution thresholds for demo runs (lower min_observations/min_peers)")

    args = parser.parse_args()
    setup_logging(args.log_file)
    config = load_config(args.config)

    # If requested, relax distribution thresholds to allow small-demo training runs
    if args.relax:
        import logging as _logging
        _logging.getLogger(__name__).info("Relaxing distribution thresholds for demo: setting min_observations=1 and peer_groups.min_peers=1")
        if "distributions" not in config:
            config["distributions"] = {}
        config["distributions"]["min_observations"] = 1
        if "peer_groups" not in config:
            config["peer_groups"] = {}
        config["peer_groups"]["min_peers"] = 1

    # Ensure required paths exist
    Path(config["data"]["raw_dir"]).mkdir(parents=True, exist_ok=True)
    Path(config["data"]["models_dir"]).mkdir(parents=True, exist_ok=True)

    logging.getLogger(__name__).info("Starting integrated pipeline: training phase")
    train(config)

    if args.stage3:
        logging.getLogger(__name__).info("Launching Stage-3 demo (parso)")
        try:
            run_stage3_demo()
        except Exception:
            logging.getLogger(__name__).exception("Stage-3 demo failed; continuing")

    if args.stage4:
        logging.getLogger(__name__).info("Launching Stage-4 demo (parso)")
        try:
            run_stage4_demo()
        except Exception:
            logging.getLogger(__name__).exception("Stage-4 demo failed; continuing")

    logging.getLogger(__name__).info("Integration run complete. See logs for details")


if __name__ == "__main__":
    main()
