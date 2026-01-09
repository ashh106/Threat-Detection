"""Adapter/wrapper for the parso integration components.
Provides simple functions to run Stage-3 demo and Stage-4 demo programmatically.
"""
from types import SimpleNamespace
import logging

logger = logging.getLogger(__name__)


def run_stage3_demo(kafka_servers: str = "127.0.0.1:9092", canonical_topic: str = "canonical-metadata", intent_topic: str = "stage_3", window_size: int = 15, demo: bool = True):
    """Run the Stage-3 (intent engine) demo flow for a short duration.
    If demo=True, run a lightweight in-process simulation that does not require Kafka.
    """
    try:
        if demo:
            # Lightweight in-process demo using the CanonicalConsumer processing logic
            import os
            import sys

            # Ensure the parso intent_engine directory is on sys.path so its internal imports resolve
            pkg_dir = os.path.join(os.path.dirname(__file__), "intent_engine")
            if pkg_dir not in sys.path:
                sys.path.insert(0, pkg_dir)

            from src.extensions.parso.intent_engine.consumer import CanonicalConsumer

            consumer = CanonicalConsumer(bootstrap_servers=kafka_servers,
                                         input_topic=canonical_topic,
                                         output_topic=intent_topic)

            # Generate synthetic canonical events for two users
            now = __import__("time").time()
            events = []
            users = ["demo_user_1", "demo_user_2"]
            actions = ["login", "open_email", "edit_doc", "send_email"]

            for i in range(10):
                evt = {
                    "t": now + i,
                    "user": users[i % len(users)],
                    "action": actions[i % len(actions)],
                    "object_type": "email",
                    "domain": "corp",
                    "success": True,
                    "sensitivity": float(i % 3) * 0.1,
                    "novelty": float((i % 5)) * 0.05,
                    "risk_cost": float((i % 4)) * 0.2,
                    "effort_cost": float((i % 3)) * 0.1,
                    "source": "demo"
                }
                events.append(evt)

            logger.info("Starting Stage-3 in-process demo: processing synthetic canonical events")
            for e in events:
                consumer._process_canonical_event(e)

            stats = consumer.get_statistics()
            logger.info("Stage-3 demo completed")
            return stats

        else:
            # Fallback to CLI demo mode (may require Kafka)
            from pipeline.main import run_demo_mode

            args = SimpleNamespace(
                mode="consumer",
                kafka_servers=kafka_servers,
                canonical_topic=canonical_topic,
                intent_topic=intent_topic,
                window_size=window_size
            )

            logger.info("Starting Stage-3 demo via parso pipeline wrapper (CLI)")
            run_demo_mode(args)
    except Exception as e:
        logger.exception("Stage-3 demo failed: %s", e)
        raise


def run_stage4_demo(kafka_servers: str = "127.0.0.1:9092", input_topic: str = "stage_3", output_topic: str = "behavioral_phase", demo: bool = True):
    """Run the Stage-4 HMM demo flow.
    If demo=True, run an in-process PhaseInference over synthetic Stage-3 observations.
    """
    try:
        if demo:
            from stage_4.inference import PhaseInference

            engine = PhaseInference(user_timeout_seconds=3600)

            # Create synthetic Stage-3 observation messages
            now = __import__("time").time()
            observations = []
            users = ["demo_user_1", "demo_user_2"]

            # Ensure each user has at least 4 observations so inference occurs
            for u in users:
                for i in range(5):
                    obs = [
                        0.1 * (i + 1),  # K
                        0.05 * (i % 4),  # U
                        0.2 * ((i + 1) % 3),  # E
                        0.1 * (i % 2),  # R
                        0.05 * (i % 5),  # C
                        0.0,             # G
                        0.02 * (i + 1),  # I
                        0.01 * (i % 3)   # P
                    ]
                    observations.append({
                        "t": now + i,
                        "user": u,
                        "observation": obs
                    })

            logger.info("Starting Stage-4 in-process demo: running PhaseInference on synthetic observations")
            results = engine.process_batch_observations(observations)
            stats = engine.get_statistics()
            logger.info("Stage-4 demo completed: %d inferences", len(results))
            return {"results": results, "stats": stats}

        else:
            from stage_4.main import run_stage4_mode

            args = SimpleNamespace(
                mode="hmm",
                kafka_servers=kafka_servers,
                input_topic=input_topic,
                output_topic=output_topic,
                user_timeout=3600,
                poll_timeout=1000
            )

            logger.info("Starting Stage-4 demo via parso stage_4 wrapper (CLI)")
            run_stage4_mode(args)
    except Exception as e:
        logger.exception("Stage-4 demo failed: %s", e)
        raise
