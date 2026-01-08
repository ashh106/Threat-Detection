"""
FILE: main.py

STAGE:
    Pipeline Entry Point

PURPOSE:
    Main entry point for HMM-based cognitive intent engine.
    This module provides the primary interface for running the intent analysis pipeline
    with HMM-based intent inference and Kafka integration.

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
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'intent_engine'))

from state import CognitiveState
from cognitive_update import CognitiveUpdater
from phase_hmm import PhaseInference
from consumer import CanonicalConsumer

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
    # Default weights from phase_hmm
    from phase_hmm import WEIGHTS
    
    return PipelineConfig(
        kafka_bootstrap_servers=args.kafka_servers,
        canonical_topic=args.canonical_topic,
        intent_topic=args.intent_topic,
        window_size_minutes=args.window_size,
        feature_weights=WEIGHTS.copy()
    )


def run_pipeline_mode(args):
    """Run the intent analysis pipeline in production mode."""
    logger.info("Starting pipeline in production mode")
    
    config = create_pipeline_config(args)
    pipeline = IntentAnalysisPipeline(config)
    
    try:
        # Start pipeline
        pipeline.start()
        logger.info("Pipeline is running. Press Ctrl+C to stop.")
        
        # Keep running until interrupted
        while True:
            time.sleep(60)
            
            # Print periodic statistics
            stats = pipeline.get_statistics()
            logger.info(f"Statistics: {stats['windows_processed']} windows processed, "
                       f"{stats['inferences_published']} inferences published")
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        pipeline.stop()
        logger.info("Pipeline stopped")


def run_simulation_mode(args):
    """Run the intent analysis pipeline in simulation mode."""
    logger.info("Starting pipeline in simulation mode")
    
    config = create_pipeline_config(args)
    pipeline = IntentAnalysisPipeline(config)
    
    try:
        # Start pipeline
        pipeline.start()
        
        # Run simulation
        simulator = IntentAnalysisSimulator(pipeline)
        simulator.run_simulation(
            duration_minutes=args.simulation_duration,
            events_per_minute=args.events_per_minute
        )
        
        # Keep running for a bit to see results
        logger.info("Simulation completed. Pipeline will continue running...")
        logger.info("Press Ctrl+C to stop")
        
        time.sleep(args.post_simulation_time)
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        pipeline.stop()
        logger.info("Pipeline stopped")


def run_demo_mode(args):
    """Run a quick demonstration of the intent inference system."""
    logger.info("Starting demonstration mode")
    
    config = create_pipeline_config(args)
    pipeline = IntentAnalysisPipeline(config)
    
    try:
        # Start pipeline
        pipeline.start()
        
        # Create simulator with demo parameters
        simulator = IntentAnalysisSimulator(pipeline)
        
        logger.info("=== INTENT INFERENCE DEMO ===")
        logger.info("This demo shows how intent progresses through stages:")
        logger.info("EXPLORE → LEARN → COLLECT → PREPARE → EXFIL")
        logger.info("")
        
        # Run a short simulation
        simulator.run_simulation(duration_minutes=3, events_per_minute=2)
        
        # Wait for processing
        time.sleep(5)
        
        # Show detailed results
        logger.info("\n=== DETAILED RESULTS ===")
        
        for user_id in ['alice_benign', 'bob_curious', 'charlie_malicious']:
            user_state = pipeline.get_user_intent_state(user_id)
            if user_state:
                beliefs = user_state.current_beliefs
                dominant = beliefs.get_dominant_intent()
                
                logger.info(f"\nUser: {user_id}")
                logger.info(f"  Dominant Intent: {dominant}")
                logger.info(f"  Transition Velocity: {user_state.transition_velocity:.3f}")
                logger.info(f"  Stability Score: {user_state.stability_score:.3f}")
                
                # Show probability distribution
                logger.info("  Intent Probabilities:")
                for state in INTENT_STATES:
                    prob = getattr(beliefs, f"{state.lower()}_prob")
                    logger.info(f"    {state}: {prob:.3f}")
        
        # Show overall statistics
        stats = pipeline.get_statistics()
        distribution = pipeline.get_intent_distribution()
        
        logger.info(f"\n=== OVERALL STATISTICS ===")
        logger.info(f"Windows Processed: {stats['windows_processed']}")
        logger.info(f"Inferences Published: {stats['inferences_published']}")
        logger.info(f"Intent Distribution: {distribution}")
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        pipeline.stop()
        logger.info("Demo completed")


def main():
    """Main entry point for the intent analysis system."""
    parser = argparse.ArgumentParser(
        description="HMM-based Cognitive Intent Engine for Insider Threat Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --mode demo                    # Run demonstration
  %(prog)s --mode simulation --duration 10 # Run 10-minute simulation
  %(prog)s --mode pipeline                 # Run production pipeline
        """
    )
    
    # Mode selection
    parser.add_argument(
        '--mode', 
        choices=['demo', 'simulation', 'pipeline'],
        default='demo',
        help='Running mode (default: demo)'
    )
    
    # Kafka configuration
    parser.add_argument(
        '--kafka-servers',
        default='localhost:9092',
        help='Kafka bootstrap servers (default: localhost:9092)'
    )
    
    parser.add_argument(
        '--canonical-topic',
        default='canonical-metadata',
        help='Kafka topic for canonical events (default: canonical-metadata)'
    )
    
    parser.add_argument(
        '--intent-topic',
        default='intent-inference',
        help='Kafka topic for intent results (default: intent-inference)'
    )
    
    # Pipeline configuration
    parser.add_argument(
        '--window-size',
        type=int,
        default=15,
        help='Time window size in minutes (default: 15)'
    )
    
    # Simulation parameters
    parser.add_argument(
        '--simulation-duration',
        type=int,
        default=5,
        help='Simulation duration in minutes (default: 5)'
    )
    
    parser.add_argument(
        '--events-per-minute',
        type=int,
        default=3,
        help='Events per minute in simulation (default: 3)'
    )
    
    parser.add_argument(
        '--post-simulation-time',
        type=int,
        default=30,
        help='Time to keep running after simulation (default: 30 seconds)'
    )
    
    # Logging
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Print startup banner
    logger.info("=" * 60)
    logger.info("HMM-based Cognitive Intent Engine")
    logger.info("=" * 60)
    logger.info(f"Mode: {args.mode}")
    logger.info(f"Kafka Servers: {args.kafka_servers}")
    logger.info(f"Canonical Topic: {args.canonical_topic}")
    logger.info(f"Intent Topic: {args.intent_topic}")
    logger.info(f"Window Size: {args.window_size} minutes")
    logger.info("=" * 60)
    
    # Run in requested mode
    try:
        if args.mode == 'demo':
            run_demo_mode(args)
        elif args.mode == 'simulation':
            run_simulation_mode(args)
        elif args.mode == 'pipeline':
            run_pipeline_mode(args)
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
