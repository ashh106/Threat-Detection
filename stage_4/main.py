"""
FILE: main.py

STAGE:
    Stage-4 Behavioral Phase Inference

PURPOSE:
    Main entry point for Stage-4 HMM-based behavioral phase inference.
    This module orchestrates the consumption of Stage-3 observations,
    HMM inference, and publication of phase results.

INPUT:
    Kafka topic: stage_3 (cognitive observations)
    Message schema: {"t": ..., "user": ..., "observation": [...], "features": [...]}

OUTPUT:
    Kafka topic: behavioral_phase (phase inference results)
    Message schema: {"t": ..., "user": ..., "state": ..., "state_probabilities": {...}, "log_likelihood": ...}

ARCHITECTURE:
    - Per-user HMM inference with complete separation
    - Fixed-parameter Gaussian HMM (no training)
    - Conservative phase transitions
    - Automatic user state expiry

NOTE: No alerting, intent scoring, or ML training - pure HMM inference.
"""

import argparse
import logging
import time
import signal
import sys
from typing import Dict, Any

from .consumer import Stage4Consumer, ConsumerConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_consumer_config(args) -> ConsumerConfig:
    """Create consumer configuration from command line arguments."""
    return ConsumerConfig(
        bootstrap_servers=args.kafka_servers,
        input_topic=args.input_topic,
        output_topic=args.output_topic,
        user_timeout_seconds=args.user_timeout,
        poll_timeout_ms=args.poll_timeout
    )


def run_stage4_mode(args):
    """Run Stage-4 HMM inference mode."""
    logger.info("Starting Stage-4 Behavioral Phase Inference")
    logger.info("HMM-based phase inference from Stage-3 cognitive observations")
    
    try:
        # Create configuration
        config = create_consumer_config(args)
        
        # Initialize consumer
        consumer = Stage4Consumer(config)
        
        logger.info("=== STAGE-4 HMM INFERENCE ENGINE ===")
        logger.info(f"Input topic: {config.input_topic}")
        logger.info(f"Output topic: {config.output_topic}")
        logger.info(f"User timeout: {config.user_timeout_seconds} seconds")
        
        # Start consumer
        consumer.start_consuming()
        
        # Keep running until interrupted
        logger.info("Stage-4 HMM inference is running. Press Ctrl+C to stop.")
        
        while True:
            time.sleep(60)  # Statistics interval
            
            # Print periodic statistics
            stats = consumer.get_statistics()
            logger.info(f"Statistics: {stats['processed_messages']} messages processed, "
                       f"{stats['active_users']} active users, "
                       f"{stats['total_inferences']} total inferences")
            
            # Log inference rate
            if stats['inferences_per_second'] > 0:
                logger.info(f"Inference rate: {stats['inferences_per_second']:.3f} inferences/second")
    
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Stage-4 failed: {e}")
        raise
    finally:
        consumer.stop_consuming()
        logger.info("Stage-4 HMM inference stopped")


def signal_handler(signum, frame):
    """Handle interrupt signals gracefully."""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Stage-4 Behavioral Phase Inference Engine"
    )
    
    parser.add_argument(
        '--mode',
        choices=['hmm'],
        default='hmm',
        help='Stage-4 HMM inference mode'
    )
    
    parser.add_argument(
        '--kafka-servers',
        default='127.0.0.1:9092',
        help='Kafka bootstrap servers (IPv4 only)'
    )
    
    parser.add_argument(
        '--input-topic',
        default='stage_3',
        help='Input Kafka topic for cognitive observations'
    )
    
    parser.add_argument(
        '--output-topic',
        default='behavioral_phase',
        help='Output Kafka topic for phase inference results'
    )
    
    parser.add_argument(
        '--user-timeout',
        type=int,
        default=3600,
        help='User inactivity timeout in seconds (default: 3600)'
    )
    
    parser.add_argument(
        '--poll-timeout',
        type=int,
        default=1000,
        help='Kafka poll timeout in milliseconds (default: 1000)'
    )
    
    args = parser.parse_args()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run Stage-4
    if args.mode == 'hmm':
        run_stage4_mode(args)
    else:
        logger.error(f"Unknown mode: {args.mode}")
        sys.exit(1)


if __name__ == "__main__":
    main()
