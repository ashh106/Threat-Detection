"""
STAGE 3 — Cognitive Observation Producer

This file consumes canonical events from Kafka,
updates per-user cognitive state using EMA dynamics,
and emits HMM-ready observation vectors to Kafka topic `stage_3`.

Phase inference is handled by Stage-4 HMM.
This stage produces ONLY cognitive observation vectors.

Mock/demo events are explicitly disabled.
"""

import time
import threading
import logging
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from state import CognitiveState
from cognitive_update import CognitiveUpdater, CanonicalEvent
from config import IntentEngineConfig

# Kafka imports
try:
    from kafka import KafkaConsumer, KafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("Warning: kafka-python not installed. Using mock Kafka for testing.")


def cognitive_update(state, event):
    """
    Minimal cognitive state update.
    Deterministic, no ML, no history explosion.
    """
    if state is None:
        state = {
            "event_count": 0,
            "risk_sum": 0.0,
            "effort_sum": 0.0,
            "novelty_sum": 0.0,
            "last_ts": None,
        }

    state["event_count"] += 1
    state["risk_sum"] += float(event.get("risk_cost", 0.0))
    state["effort_sum"] += float(event.get("effort_cost", 0.0))
    state["novelty_sum"] += float(event.get("novelty", 0.0))
    state["last_ts"] = event.get("t")

    return state

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class CognitiveOutput:
    """Cognitive state output for Kafka publishing."""
    user_id: str
    timestamp: float
    cognitive_state: Dict[str, Any]
    phase_probabilities: Dict[str, float]
    dominant_phase: str
    transition_velocity: float
    confidence_score: float


class CanonicalConsumer:
    """
    Kafka consumer for canonical events with real cognitive processing.
    
    Consumes canonical events from canonical-metadata topic,
    updates cognitive states, performs phase inference,
    and publishes results to stage_3 topic.
    """
    
    def __init__(self, bootstrap_servers: str = "127.0.0.1:9092",
                 input_topic: str = "canonical-metadata",
                 output_topic: str = "stage_3"):
        self.bootstrap_servers = bootstrap_servers
        self.input_topic = input_topic
        self.output_topic = output_topic
        
        # Initialize core components
        self.config = IntentEngineConfig()
        self.cognitive_updater = CognitiveUpdater(self.config)
        
        # Per-user cognitive state storage
        self.user_states: Dict[str, CognitiveState] = {}
        
        # Kafka components
        self.consumer = None
        self.producer = None
        
        # Event processing
        self.running = False
        self.processed_count = 0
        
        # Thread management
        self.consumer_thread = None
    
    def start_consuming(self):
        """Start consuming canonical events and processing."""
        if self.running:
            logger.warning("Consumer is already running")
            return
        
        self.running = True
        logger.info(f"Starting canonical event consumer")
        logger.info(f"Input topic: {self.input_topic}")
        logger.info(f"Output topic: {self.output_topic}")
        
        # Start consumer thread
        self.consumer_thread = threading.Thread(
            target=self._consume_events,
            name="CanonicalConsumer",
            daemon=True
        )
        self.consumer_thread.start()
        
        logger.info("Canonical consumer started")
    
    def stop_consuming(self):
        """Stop consuming events."""
        self.running = False
        
        if self.consumer_thread and self.consumer_thread.is_alive():
            self.consumer_thread.join(timeout=5.0)
        
        if self.producer:
            self.producer.flush()
            self.producer.close()
        
        logger.info("Canonical consumer stopped")
    
    def _consume_events(self):
        """
        Main event consumption loop.
        
        Consumes canonical events, updates cognitive states,
        and publishes HMM-ready observation vectors.
        """
        try:
            # Initialize Kafka components (placeholder for now)
            self._initialize_components()
            
            # Main consumption loop
            while self.running:
                try:
                    # Consume canonical event
                    event = self._consume_canonical_event()
                    if event:
                        # Process event through cognitive pipeline
                        self._process_canonical_event(event)
                        self.processed_count += 1
                        
                except Exception as e:
                    logger.error(f"Error processing event: {e}")
                    
        except Exception as e:
            logger.error(f"Consumer thread error: {e}")
    
    def _check_kafka_availability(self, max_retries: int = 3, backoff_seconds: int = 5) -> bool:
        """
        Pre-flight Kafka availability check with retry and backoff.
        
        Returns True if Kafka is available, False otherwise.
        """
        import time
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Checking Kafka availability (attempt {attempt + 1}/{max_retries})...")
                
                # Try to fetch metadata
                test_consumer = KafkaConsumer(
                    bootstrap_servers=self.bootstrap_servers,
                    request_timeout_ms=5000,
                    api_version=(0, 10, 1)
                )
                
                # Force metadata fetch
                topics = test_consumer.topics()
                test_consumer.close()
                
                logger.info(f"Kafka is available. Topics: {list(topics)}")
                return True
                
            except Exception as e:
                logger.warning(f"Kafka not available (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {backoff_seconds} seconds...")
                    time.sleep(backoff_seconds)
                else:
                    logger.error("Kafka is not available after all retries")
                    return False
        
        return False
    
    def _initialize_components(self):
        """
        Initialize real Kafka components for cognitive engine.
        
        Mock/demo events are explicitly disabled.
        """
        logger.info("Initializing real Kafka components...")
        
        if not KAFKA_AVAILABLE:
            logger.error("kafka-python not installed. Install kafka-python for real processing.")
            raise RuntimeError("Kafka integration required for Stage-3 processing")
        
        # Pre-flight Kafka availability check
        if not self._check_kafka_availability():
            logger.error("Kafka is not available. Exiting.")
            raise RuntimeError("Kafka availability check failed")
        
        try:
            # Initialize real Kafka consumer with IPv4 and consumer group
            self.consumer = KafkaConsumer(
                self.input_topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id="stage-3-cognitive-engine",
                auto_offset_reset='latest',  # Don't reset to 0 every run
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                request_timeout_ms=40000,  # Must be larger than session timeout
                session_timeout_ms=30000,
                heartbeat_interval_ms=3000
            )
            
            # Initialize real Kafka producer
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                request_timeout_ms=10000,
                acks='all',
                retries=3
            )
            
            logger.info(f"Connected to Kafka: {self.bootstrap_servers}")
            logger.info(f"Consuming from: {self.input_topic}")
            logger.info(f"Publishing to: {self.output_topic}")
            logger.info("Consumer group: stage-3-cognitive-engine")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kafka components: {e}")
            raise
    
    def _consume_canonical_event(self):
        """
        Consume a single canonical event from real Kafka.
        
        Mock/demo events are explicitly disabled.
        """
        if not KAFKA_AVAILABLE:
            raise RuntimeError("Kafka required for real canonical event consumption")
        
        # Consume from real Kafka with timeout
        try:
            message_pack = self.consumer.poll(timeout_ms=1000)
            if message_pack:
                for topic_partition, messages in message_pack.items():
                    for message in messages:
                        return message.value
        except Exception as e:
            logger.error(f"Error consuming from Kafka: {e}")
        
        return None
    
    def _process_canonical_event(self, event: Dict[str, Any]):
        """
        Process canonical event through real cognitive pipeline.
        
        Updates cognitive state and performs phase inference.
        Canonical schema: t, user, action, object_type, object_id, domain, success, 
                     sensitivity, novelty, risk_cost, effort_cost, source, raw_event_id
        """
        try:
            # Canonical schema normalization - handle both user_id and user fields
            user_id = event.get("user_id") or event.get("user")
            if not user_id:
                logger.error(f"Missing user identifier in canonical event: {event}")
                return  # Skip malformed event, continue processing
            
            # Log real canonical event at DEBUG level
            logger.debug(f"Canonical event received: user={user_id}, action={event.get('action')}, "
                       f"novelty={event.get('novelty'):.3f}, "
                       f"sensitivity={event.get('sensitivity'):.3f}, "
                       f"effort_cost={event.get('effort_cost'):.3f}, "
                       f"risk_cost={event.get('risk_cost'):.3f}")
            
            # Get or create user cognitive state
            if user_id not in self.user_states:
                self.user_states[user_id] = CognitiveState(user_id=user_id)
            
            # Convert to canonical event format for cognitive updater
            canonical_event = CanonicalEvent(
                timestamp=event.get('t', event.get('timestamp', time.time())),
                user_id=user_id,
                action=event.get('action', ''),
                object_type=event.get('object_type', ''),
                domain=event.get('domain', ''),
                success=event.get('success', True),
                sensitivity=event.get('sensitivity', 0.0),
                novelty=event.get('novelty', 0.0),
                risk_cost=event.get('risk_cost', 0.0),
                effort_cost=event.get('effort_cost', 0.0),
                source=event.get('source', 'kafka')
            )
            
            # Update cognitive state using real EMA equations
            updated_state = self.cognitive_updater.update_state(
                self.user_states[user_id], canonical_event
            )
            self.user_states[user_id] = updated_state
            
            # Build HMM-ready observation vector
            observation_vector = [
                updated_state.knowledge,      # K
                updated_state.uncertainty,    # U
                updated_state.effort,         # E
                updated_state.risk_tolerance,  # R
                updated_state.compute_capability(),  # C
                0.0,                        # G (goal proximity - placeholder)
                updated_state.compute_intent_strength(),  # I
                updated_state.persistence      # P
            ]
            
            # Prepare Stage-3 observation output
            stage_3_output = {
                "t": event.get('t', event.get('timestamp', time.time())),
                "user": user_id,
                "observation": observation_vector,
                "features": ["K", "U", "E", "R", "C", "G", "I", "P"]
            }
            
            # Publish to stage_3 topic
            self._publish_stage_3_output(stage_3_output)
            
            # Observation-based logging (no phase inference)
            logger.info(f"Processed: user={user_id} | "
                       f"Observation=[K={updated_state.knowledge:.2f}, "
                       f"U={updated_state.uncertainty:.2f}, "
                       f"E={updated_state.effort:.2f}, "
                       f"R={updated_state.risk_tolerance:.2f}, "
                       f"C={updated_state.compute_capability():.2f}, "
                       f"G=0.00, "
                       f"I={updated_state.compute_intent_strength():.2f}, "
                       f"P={updated_state.persistence:.2f}]")
            
            self.processed_count += 1
            
        except Exception as e:
            logger.error(f"Error processing canonical event: {e}")
            # Continue processing other events, don't crash consumer
    
    def _publish_stage_3_output(self, output: Dict[str, Any]):
        """Publish Stage-3 cognitive output to Kafka topic stage_3."""
        try:
            if self.producer:
                self.producer.send(
                    topic=self.output_topic,
                    value=output,
                    key=output['user'].encode('utf-8')
                )
                self.producer.flush()
        except Exception as e:
            logger.error(f"Error publishing to stage_3 topic: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get consumer statistics."""
        stats = {
            'processed_events': self.processed_count,
            'running': self.running,
            'input_topic': self.input_topic,
            'output_topic': self.output_topic,
            'active_users': len(self.user_states)
        }
        
        # Add validation statistics if we have users
        if self.user_states:
            # Calculate mean and variance of cognitive factors
            factors = ['knowledge', 'uncertainty', 'effort', 'risk_tolerance', 'persistence']
            factor_stats = {}
            
            for factor in factors:
                values = [getattr(state, factor) for state in self.user_states.values()]
                if values:
                    mean_val = sum(values) / len(values)
                    variance = sum((x - mean_val) ** 2 for x in values) / len(values)
                    factor_stats[factor] = {'mean': mean_val, 'variance': variance}
            
            stats['cognitive_factors'] = factor_stats
            
            # Example observation for one user
            if self.user_states:
                example_user = list(self.user_states.keys())[0]
                example_state = self.user_states[example_user]
                stats['example_observation'] = {
                    'user': example_user,
                    'observation': [
                        example_state.knowledge,
                        example_state.uncertainty,
                        example_state.effort,
                        example_state.risk_tolerance,
                        example_state.compute_capability(),
                        0.0,  # G (goal proximity placeholder)
                        example_state.compute_intent_strength(),
                        example_state.persistence
                    ],
                    'features': ["K", "U", "E", "R", "C", "G", "I", "P"],
                    'event_count': example_state.event_count
                }
        
        return stats
