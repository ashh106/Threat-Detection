"""Adapter/wrapper for the parso integration components.
Provides simple functions to run Stage-3 demo and Stage-4 demo programmatically.
"""
from types import SimpleNamespace
import logging

logger = logging.getLogger(__name__)


def run_stage3_demo(kafka_servers: str = "127.0.0.1:9092", canonical_topic: str = "canonical-metadata", intent_topic: str = "stage_3", window_size: int = 15):
    """Run the Stage-3 (intent engine) demo flow for a short duration.
    This uses the CLI functions in `pipeline/main.py`.
    """
    try:
        # Import here to avoid startup-time side-effects if module isn't used
        from pipeline.main import run_demo_mode

        args = SimpleNamespace(
            mode="consumer",
            kafka_servers=kafka_servers,
            canonical_topic=canonical_topic,
            intent_topic=intent_topic,
            window_size=window_size
        )

        logger.info("Starting Stage-3 demo via parso pipeline wrapper")
        run_demo_mode(args)
    except Exception as e:
        logger.exception("Stage-3 demo failed: %s", e)
        raise


def run_stage4_demo(kafka_servers: str = "127.0.0.1:9092", input_topic: str = "stage_3", output_topic: str = "behavioral_phase"):
    """Run the Stage-4 HMM demo flow using `stage_4/main.py` internals."""
    try:
        from stage_4.main import run_stage4_mode

        args = SimpleNamespace(
            mode="hmm",
            kafka_servers=kafka_servers,
            input_topic=input_topic,
            output_topic=output_topic,
            user_timeout=3600,
            poll_timeout=1000
        )

        logger.info("Starting Stage-4 demo via parso stage_4 wrapper")
        run_stage4_mode(args)
    except Exception as e:
        logger.exception("Stage-4 demo failed: %s", e)
        raise
