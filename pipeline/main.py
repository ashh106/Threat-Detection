"""
FILE: main.py

STAGE:
    Pipeline Entry Point

PURPOSE:
    Main entry point for cognitive intent engine.
    This module provides the primary interface for running the intent analysis pipeline
    with cognitive state updates and phase inference.

INPUTS:
    Command line arguments and configuration.
    Runtime parameters for pipeline execution.

OUTPUTS:
    Pipeline execution and monitoring.
    Intent analysis system operation.

IMPORTANT:
    This file coordinates all stages but implements minimal logic.
    Pipeline orchestration and configuration management only.
"""

import time
import argparse
import logging
from typing import Dict, Any
from dataclasses import dataclass

# Import Stage-3 components
from src.extensions.parso.intent_engine.state import CognitiveState
from src.extensions.parso.intent_engine.cognitive_update import CognitiveUpdater
from src.extensions.parso.intent_engine.consumer import CanonicalConsumer
from src.extensions.parso.intent_engine.config import IntentEngineConfig
# Use PhaseInference implementation from intent_engine (disabled HMM is default)
from src.extensions.parso.intent_engine.phase_hmm_disabled import PhaseInference

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Pipeline configuration."""
    kafka_bootstrap_servers: str
    canonical_topic: str
    intent_topic: str
    window_size_minutes: int
    feature_weights: Dict[str, float]


def create_pipeline_config(args) -> PipelineConfig:
    """Create pipeline configuration from command line arguments."""
    # Default feature weights for observation producer
    default_weights = {
        'novelty': 0.2,
        'sensitivity': 0.35,
        'effort': 0.25,
        'focus': 0.1,
        'entropy': 0.1
    }
    
    return PipelineConfig(
        kafka_bootstrap_servers=args.kafka_servers,
        canonical_topic=args.canonical_topic,
        intent_topic=args.intent_topic,
        window_size_minutes=args.window_size,
        feature_weights=default_weights.copy()
    )


def run_demo_mode(args):
    """Run a demonstration of the cognitive intent engine."""
    logger.info("Starting cognitive intent engine demonstration")
    
    try:
        # Create configuration
        config = IntentEngineConfig()
        
        # Initialize components
        cognitive_updater = CognitiveUpdater(config)
        phase_inference = PhaseInference()
        consumer = CanonicalConsumer(
            bootstrap_servers=args.kafka_servers,
            input_topic=args.canonical_topic,
            output_topic=args.intent_topic
        )
        
        # Initialize consumer components (mock for demo)
        consumer.cognitive_updater = cognitive_updater
        consumer.phase_inference = phase_inference
        
        logger.info("=== COGNITIVE INTENT ENGINE DEMO ===")
        logger.info("This demo shows cognitive state updates and phase inference")
        logger.info("Processing mock events for 30 seconds...")
        
        # Start consumer
        consumer.start_consuming()
        
        # Run for demonstration period
        time.sleep(30)
        
        # Stop consumer
        consumer.stop_consuming()
        
        # Show statistics
        stats = consumer.get_statistics()
        logger.info(f"Demo completed. Processed {stats['processed_events']} events")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


def run_consumer_mode(args):
    """Run cognitive observation producer in real consumer mode."""
    logger.info("Starting Stage-3 cognitive observation producer")
    logger.info("Mock/demo events are explicitly disabled")
    
    try:
        # Create configuration
        config = IntentEngineConfig()
        
        # Initialize consumer (no phase inference)
        consumer = CanonicalConsumer(
            bootstrap_servers=args.kafka_servers,
            input_topic=args.canonical_topic,
            output_topic=args.intent_topic
        )
        
        logger.info("=== STAGE-3 COGNITIVE OBSERVATION PRODUCER ===")
        logger.info("Consuming real canonical events from canonical-metadata")
        logger.info(f"Input topic: {args.canonical_topic}")
        logger.info(f"Output topic: {args.intent_topic}")
        
        # Start consumer
        consumer.start_consuming()
        
        # Keep running until interrupted
        logger.info("Stage-3 consumer is running. Press Ctrl+C to stop.")
        
        while True:
            time.sleep(60)
            
            # Print periodic statistics with validation data
            stats = consumer.get_statistics()
            logger.info(f"Statistics: {stats['processed_events']} events processed, {stats['active_users']} active users")
            
            # Log validation statistics periodically
            if 'cognitive_factors' in stats:
                factors = stats['cognitive_factors']
                logger.info(f"Cognitive Factors - K: μ={factors['knowledge']['mean']:.3f}, σ²={factors['knowledge']['variance']:.3f} | "
                           f"U: μ={factors['uncertainty']['mean']:.3f}, σ²={factors['uncertainty']['variance']:.3f} | "
                           f"E: μ={factors['effort']['mean']:.3f}, σ²={factors['effort']['variance']:.3f} | "
                           f"R: μ={factors['risk_tolerance']['mean']:.3f}, σ²={factors['risk_tolerance']['variance']:.3f} | "
                           f"P: μ={factors['persistence']['mean']:.3f}, σ²={factors['persistence']['variance']:.3f}")
            
            if 'example_observation' in stats:
                obs = stats['example_observation']
                obs_str = ', '.join([f"{val:.3f}" for val in obs['observation']])
                logger.info(f"Example User {obs['user']}: Observation=[{obs_str}] ({obs['event_count']} events)")
            
    except Exception as e:
        logger.error(f"Consumer failed: {e}")
        raise
    finally:
        consumer.stop_consuming()
        logger.info("Stage-3 consumer stopped")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cognitive Intent Engine - Stage-3 Pipeline"
    )
    
    parser.add_argument(
        '--mode',
        choices=['consumer'],
        default='consumer',
        help='Stage-3 cognitive intent engine mode'
    )
    
    parser.add_argument(
        '--kafka-servers',
        default='127.0.0.1:9092',
        help='Kafka bootstrap servers (IPv4 only)'
    )
    
    parser.add_argument(
        '--canonical-topic',
        default='canonical-metadata',
        help='Canonical events input topic'
    )
    
    parser.add_argument(
        '--intent-topic',
        default='stage_3',
        help='Stage-3 cognitive output topic'
    )
    
    parser.add_argument(
        '--window-size',
        type=int,
        default=15,
        help='Window size in minutes'
    )
    
    args = parser.parse_args()
    
    # Print configuration
    logger.info("=" * 60)
    logger.info("STAGE-3 COGNITIVE INTENT ENGINE")
    logger.info("=" * 60)
    logger.info(f"Kafka Servers: {args.kafka_servers}")
    logger.info(f"Input Topic: {args.canonical_topic}")
    logger.info(f"Output Topic: {args.intent_topic}")
    logger.info(f"Window Size: {args.window_size} minutes")
    logger.info("=" * 60)
    
    # Run Stage-3 cognitive intent engine
    if args.mode == 'consumer':
        run_consumer_mode(args)
    else:
        logger.error(f"Unknown mode: {args.mode}")
        logger.error("Only 'consumer' mode is supported. Demo mode is disabled.")


if __name__ == "__main__":
    main()
