"""
FILE: consumer.py

STAGE:
    Stage-3 Cognitive Intent Engine

PURPOSE:
    Intent analysis pipeline orchestrator with Kafka integration.
    This module ties together all components of intent analysis pipeline:
    Kafka consumption, window aggregation, feature extraction, HMM inference, and publishing.

INPUTS:
    Canonical events from canonicalization stage.
    Processed security events for cognitive analysis.

OUTPUTS:
    Intent inference results to Kafka.
    Cognitive intent analysis for downstream consumption.

IMPORTANT:
    This file must not implement logic from other stages.
    Pipeline orchestration and coordination only.
"""

import time
import threading
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .kafka_integration import (
    CanonicalEventConsumer, IntentInferencePublisher, 
    WindowSummary, IntentInferenceResult, CanonicalEvent, KAFKA_AVAILABLE
)
from .hmm_intent_inference import HMMIntentInference, INTENT_STATES, WEIGHTS
from .config import IntentEngineConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the intent analysis pipeline."""
    kafka_bootstrap_servers: str = "localhost:9092"
    canonical_topic: str = "canonical-metadata"
    intent_topic: str = "intent-inference"
    window_size_minutes: int = 15
    processing_interval_seconds: float = 30.0
    feature_weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.feature_weights is None:
            self.feature_weights = WEIGHTS.copy()


class IntentAnalysisPipeline:
    """
    Main orchestrator for the intent analysis pipeline.
    
    Coordinates:
    1. Kafka consumption of canonical events
    2. Time window aggregation
    3. Feature extraction and weighting
    4. HMM-based intent inference
    5. Publishing results to Kafka
    """
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.running = False
        
        # Initialize components
        self.consumer = CanonicalEventConsumer(
            bootstrap_servers=config.kafka_bootstrap_servers,
            topic=config.canonical_topic,
            window_size_minutes=config.window_size_minutes
        )
        
        self.publisher = IntentInferencePublisher(
            bootstrap_servers=config.kafka_bootstrap_servers,
            topic=config.intent_topic
        )
        
        self.intent_inference = HMMIntentInference(
            weights=config.feature_weights
        )
        
        # Statistics tracking
        self.stats = {
            'windows_processed': 0,
            'inferences_published': 0,
            'processing_errors': 0,
            'start_time': None
        }
        
        # Setup window processing callback
        self.consumer.add_window_callback(self._process_window)
        
        # Thread management
        self.consumer_thread = None
    
    def start(self):
        """Start the intent analysis pipeline."""
        if self.running:
            logger.warning("Pipeline is already running")
            return
        
        self.running = True
        self.stats['start_time'] = time.time()
        
        logger.info("Starting Intent Analysis Pipeline")
        logger.info(f"Consuming from: {self.config.canonical_topic}")
        logger.info(f"Publishing to: {self.config.intent_topic}")
        logger.info(f"Window size: {self.config.window_size_minutes} minutes")
        
        # Start consumer in separate thread
        self.consumer_thread = threading.Thread(
            target=self._run_consumer,
            name="KafkaConsumer",
            daemon=True
        )
        self.consumer_thread.start()
        
        logger.info("Pipeline started successfully")
    
    def stop(self):
        """Stop the intent analysis pipeline."""
        if not self.running:
            return
        
        logger.info("Stopping Intent Analysis Pipeline...")
        
        self.running = False
        self.consumer.stop()
        
        # Wait for consumer thread to finish
        if self.consumer_thread and self.consumer_thread.is_alive():
            self.consumer_thread.join(timeout=10.0)
        
        # Flush and close publisher
        self.publisher.flush()
        self.publisher.close()
        
        logger.info("Pipeline stopped")
    
    def _run_consumer(self):
        """Run the Kafka consumer."""
        try:
            self.consumer.start_consuming()
        except Exception as e:
            logger.error(f"Consumer thread error: {e}")
            self.stats['processing_errors'] += 1
    
    def _process_window(self, window_summary: WindowSummary):
        """
        Process a window summary through the inference pipeline.
        
        This is the core pipeline logic:
        Window Summary → Feature Extraction → HMM Inference → Publishing
        """
        try:
            logger.debug(f"Processing window for user {window_summary.user_id}")
            
            # Stage 4: Feature extraction and weighting (handled inside HMM inference)
            # Stage 5: HMM-based intent inference
            inference_result = self.intent_inference.infer_intent(window_summary)
            
            # Stage 6: Intent trajectory tracking (handled inside HMM inference)
            
            # Publish result
            self.publisher.publish_inference(inference_result)
            
            # Update statistics
            self.stats['windows_processed'] += 1
            self.stats['inferences_published'] += 1
            
            logger.info(f"Published inference for {window_summary.user_id}: "
                       f"{inference_result.dominant_intent} "
                       f"(confidence: {inference_result.confidence_score:.3f})")
            
        except Exception as e:
            logger.error(f"Error processing window for {window_summary.user_id}: {e}")
            self.stats['processing_errors'] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        stats = self.stats.copy()
        
        if stats['start_time']:
            stats['uptime_seconds'] = time.time() - stats['start_time']
            stats['windows_per_minute'] = stats['windows_processed'] / max(1, stats['uptime_seconds'] / 60)
        
        return stats
    
    def get_user_intent_state(self, user_id: str):
        """Get current intent state for a specific user."""
        return self.intent_inference.get_user_state(user_id)
    
    def add_test_event(self, event_data: Dict[str, Any]):
        """Add a test event for development/testing."""
        if not KAFKA_AVAILABLE:
            # For mock mode, directly process the event
            self._process_test_event(event_data)
        else:
            self.consumer.add_test_event(event_data)
    
    def _process_test_event(self, event_data: Dict[str, Any]):
        """Process a test event directly in mock mode."""
        try:
            # Parse canonical event
            event = CanonicalEvent(
                user=event_data['user'],
                timestamp=float(event_data['timestamp']),
                action=event_data['action'],
                object_type=event_data['object_type'],
                sensitivity=float(event_data['sensitivity']),
                novelty=float(event_data['novelty']),
                effort=float(event_data['effort']),
                risk=float(event_data['risk']),
                success=bool(event_data['success'])
            )
            
            # Add to user buffer and process windows
            self.consumer.user_buffers[event.user].append(event)
            self.consumer._process_user_windows(event.user)
            
        except Exception as e:
            logger.error(f"Error processing test event: {e}")
            self.stats['processing_errors'] += 1
    
    def get_intent_distribution(self) -> Dict[str, int]:
        """Get distribution of dominant intents across all users."""
        distribution = {state: 0 for state in INTENT_STATES}
        
        user_states = self.intent_inference.user_states
        for user_state in user_states.values():
            dominant = user_state.current_beliefs.get_dominant_intent()
            distribution[dominant] += 1
        
        return distribution


class IntentAnalysisSimulator:
    """
    Simulator for testing the intent analysis pipeline.
    
    Generates synthetic canonical events that demonstrate
    benign → malicious intent progression.
    """
    
    def __init__(self, pipeline: IntentAnalysisPipeline):
        self.pipeline = pipeline
        self.simulation_time = 0.0
        self.user_profiles = self._create_user_profiles()
    
    def _create_user_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Create user profiles for simulation."""
        return {
            'alice_benign': {
                'intent_progression': ['EXPLORE'],
                'event_frequency': 0.3,
                'base_sensitivity': 0.2,
                'base_novelty': 0.6
            },
            'bob_curious': {
                'intent_progression': ['EXPLORE', 'LEARN'],
                'event_frequency': 0.5,
                'base_sensitivity': 0.4,
                'base_novelty': 0.5
            },
            'charlie_malicious': {
                'intent_progression': ['EXPLORE', 'LEARN', 'COLLECT', 'PREPARE', 'EXFIL'],
                'event_frequency': 0.4,
                'base_sensitivity': 0.3,
                'base_novelty': 0.7
            }
        }
    
    def run_simulation(self, duration_minutes: int = 10, events_per_minute: int = 5):
        """Run simulation with synthetic events."""
        logger.info(f"Starting simulation for {duration_minutes} minutes")
        logger.info(f"Target rate: {events_per_minute} events/minute")
        
        start_time = time.time()
        next_event_time = start_time
        
        while time.time() - start_time < duration_minutes * 60:
            current_time = time.time()
            
            # Generate events at the specified rate
            if current_time >= next_event_time:
                # Generate one event per cycle, rotating through users
                user_ids = list(self.user_profiles.keys())
                user_index = int((current_time - start_time) / (60.0 / events_per_minute)) % len(user_ids)
                user_id = user_ids[user_index]
                profile = self.user_profiles[user_id]
                
                event = self._generate_synthetic_event(user_id, profile, current_time - start_time)
                self.pipeline.add_test_event(event)
                
                # Schedule next event
                next_event_time = current_time + (60.0 / events_per_minute)
            
            time.sleep(0.1)  # Small delay to prevent overwhelming
        
        logger.info("Simulation completed")
        self._log_simulation_summary()
    
    def _generate_synthetic_event(self, user_id: str, profile: Dict[str, Any], elapsed_time: float) -> Dict[str, Any]:
        """Generate a synthetic canonical event."""
        # Determine current intent stage based on elapsed time
        progression = profile['intent_progression']
        stage_index = min(int(elapsed_time / 120), len(progression) - 1)  # Change stage every 2 minutes
        current_stage = progression[stage_index]
        
        # Generate event based on current stage
        event_params = self._get_stage_parameters(current_stage, profile)
        
        return {
            'user': user_id,
            'timestamp': time.time(),
            'action': event_params['action'],
            'object_type': event_params['object_type'],
            'sensitivity': event_params['sensitivity'],
            'novelty': event_params['novelty'],
            'effort': event_params['effort'],
            'risk': event_params['risk'],
            'success': event_params['success']
        }
    
    def _get_stage_parameters(self, stage: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Get event parameters based on intent stage."""
        import random
        
        if stage == "EXPLORE":
            return {
                'action': random.choice(['access', 'read', 'browse']),
                'object_type': random.choice(['file', 'directory', 'network']),
                'sensitivity': profile['base_sensitivity'] + random.uniform(-0.1, 0.2),
                'novelty': profile['base_novelty'] + random.uniform(-0.1, 0.2),
                'effort': random.uniform(0.1, 0.3),
                'risk': random.uniform(0.1, 0.3),
                'success': random.random() < 0.8
            }
        
        elif stage == "LEARN":
            return {
                'action': random.choice(['access', 'read', 'search']),
                'object_type': random.choice(['database', 'config', 'system']),
                'sensitivity': profile['base_sensitivity'] + random.uniform(0.2, 0.4),
                'novelty': profile['base_novelty'] - random.uniform(0.1, 0.3),
                'effort': random.uniform(0.3, 0.5),
                'risk': random.uniform(0.3, 0.5),
                'success': random.random() < 0.85
            }
        
        elif stage == "COLLECT":
            return {
                'action': random.choice(['copy', 'collect', 'stage']),
                'object_type': random.choice(['database', 'sensitive_file', 'log']),
                'sensitivity': profile['base_sensitivity'] + random.uniform(0.4, 0.6),
                'novelty': profile['base_novelty'] - random.uniform(0.3, 0.5),
                'effort': random.uniform(0.5, 0.7),
                'risk': random.uniform(0.5, 0.7),
                'success': random.random() < 0.9
            }
        
        elif stage == "PREPARE":
            return {
                'action': random.choice(['prepare', 'package', 'compress']),
                'object_type': random.choice(['archive', 'backup', 'staging_area']),
                'sensitivity': profile['base_sensitivity'] + random.uniform(0.6, 0.8),
                'novelty': profile['base_novelty'] - random.uniform(0.4, 0.6),
                'effort': random.uniform(0.7, 0.9),
                'risk': random.uniform(0.7, 0.9),
                'success': random.random() < 0.95
            }
        
        elif stage == "EXFIL":
            return {
                'action': random.choice(['export', 'transfer', 'upload']),
                'object_type': random.choice(['archive', 'encrypted_file', 'external']),
                'sensitivity': profile['base_sensitivity'] + random.uniform(0.8, 1.0),
                'novelty': profile['base_novelty'] - random.uniform(0.5, 0.7),
                'effort': random.uniform(0.8, 1.0),
                'risk': random.uniform(0.8, 1.0),
                'success': random.random() < 0.98
            }
        
        else:
            return self._get_stage_parameters("EXPLORE", profile)
    
    def _log_simulation_summary(self):
        """Log simulation summary with intent progression."""
        logger.info("=== SIMULATION SUMMARY ===")
        
        for user_id in self.user_profiles.keys():
            user_state = self.pipeline.get_user_intent_state(user_id)
            if user_state:
                beliefs = user_state.current_beliefs
                dominant = beliefs.get_dominant_intent()
                confidence = self.pipeline.intent_inference._calculate_confidence_score(
                    beliefs, user_state.stability_score
                )
                
                logger.info(f"User {user_id}:")
                logger.info(f"  Dominant Intent: {dominant}")
                logger.info(f"  Confidence: {confidence:.3f}")
                logger.info(f"  Transition Velocity: {user_state.transition_velocity:.3f}")
                logger.info(f"  Stability: {user_state.stability_score:.3f}")
                
                # Show probability distribution
                probs = beliefs.to_dict()
                logger.info(f"  Probabilities: {probs}")
        
        # Show overall distribution
        distribution = self.pipeline.get_intent_distribution()
        logger.info(f"Overall Intent Distribution: {distribution}")
        
        # Show pipeline stats
        stats = self.pipeline.get_statistics()
        logger.info(f"Pipeline Statistics: {stats}")


def main():
    """Main function to run the intent analysis pipeline."""
    # Configuration
    config = PipelineConfig(
        kafka_bootstrap_servers="localhost:9092",
        canonical_topic="canonical-metadata",
        intent_topic="intent-inference",
        window_size_minutes=15
    )
    
    # Create pipeline
    pipeline = IntentAnalysisPipeline(config)
    
    try:
        # Start pipeline
        pipeline.start()
        
        # Run simulation
        simulator = IntentAnalysisSimulator(pipeline)
        simulator.run_simulation(duration_minutes=5, events_per_minute=3)
        
        # Keep running for a bit to see results
        logger.info("Pipeline running... Press Ctrl+C to stop")
        time.sleep(30)
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        # Stop pipeline
        pipeline.stop()
        
        # Final statistics
        stats = pipeline.get_statistics()
        logger.info(f"Final Statistics: {stats}")


if __name__ == "__main__":
    main()
