"""
FILE: consumer.py

STAGE:
    Stage-4 Behavioral Phase Inference

PURPOSE:
    Kafka consumer for Stage-3 cognitive observations.
    This module consumes observation vectors from Stage-3 and feeds
    them to the HMM inference engine for phase detection.

INPUT:
    Kafka topic: stage_3
    Message schema: {"t": ..., "user": ..., "observation": [...], "features": [...]}

OUTPUT:
    HMM inference results to behavioral_phase topic
    Message schema: {"t": ..., "user": ..., "state": ..., "state_probabilities": {...}, "log_likelihood": ...}

KAFKA INTEGRATION:
    IPv4-only bootstrap servers
    Consumer group: stage-4-hmm-inference
    Per-user message ordering guaranteed by Kafka key

NOTE: No phase inference logic here - only Kafka consumption and forwarding.
"""

import time
import threading
import logging
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .inference import PhaseInference
from .producer import PhaseProducer, ProducerConfig

# Kafka imports
try:
    from kafka import KafkaConsumer, KafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("Warning: kafka-python not installed. Using mock Kafka for testing.")

logger = logging.getLogger(__name__)


@dataclass
class ConsumerConfig:
    """Configuration for Stage-4 consumer."""
    bootstrap_servers: str = "127.0.0.1:9092"
    input_topic: str = "stage_3"
    output_topic: str = "behavioral_phase"
    consumer_group: str = "stage-4-hmm-inference"
    user_timeout_seconds: int = 1800  # 30 minutes
    poll_timeout_ms: int = 1000


class Stage4Consumer:
    """
    Kafka consumer for Stage-3 cognitive observations.
    
    Consumes observation vectors and forwards them to HMM inference
    engine for behavioral phase detection.
    """
    
    def __init__(self, config: ConsumerConfig):
        """Initialize consumer with configuration."""
        self.config = config
        self.running = False
        self.processed_count = 0
        
        # Core components
        self.inference_engine = PhaseInference(config.user_timeout_seconds)
        self.producer = PhaseProducer(config)
        
        # Kafka components
        self.consumer = None
        
        # Thread management
        self.consumer_thread = None
        
        # Cleanup timing
        self.last_cleanup_time = time.time()
    
    def _check_kafka_availability(self, max_retries: int = 3, backoff_seconds: int = 5) -> bool:
        """Check if Kafka is available before starting consumer."""
        for attempt in range(max_retries):
            try:
                test_consumer = KafkaConsumer(
                    bootstrap_servers=self.config.bootstrap_servers,
                    request_timeout_ms=5000
                )
                topics = test_consumer.topics()
                test_consumer.close()
                logger.info(f"Kafka is available. Topics: {list(topics)}")
                return True
            except Exception as e:
                logger.warning(f"Kafka not available (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(backoff_seconds)
        return False
    
    def _initialize_components(self):
        """Initialize Kafka consumer and producer."""
        if not KAFKA_AVAILABLE:
            raise RuntimeError("Kafka integration required for Stage-4 processing")
        
        if not self._check_kafka_availability():
            raise RuntimeError("Kafka availability check failed")
        
        try:
            # Initialize Kafka consumer
            self.consumer = KafkaConsumer(
                self.config.input_topic,
                bootstrap_servers=self.config.bootstrap_servers,
                group_id=self.config.consumer_group,
                auto_offset_reset='latest',
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                request_timeout_ms=40000,  # Must be larger than session timeout
                session_timeout_ms=30000,
                heartbeat_interval_ms=3000
            )
            
            # Initialize producer
            self.producer.config = ProducerConfig(
                bootstrap_servers=self.config.bootstrap_servers,
                output_topic=self.config.output_topic
            )
            self.producer.initialize()
            
            logger.info(f"Kafka consumer initialized for topic: {self.config.input_topic}")
            logger.info(f"Kafka producer initialized for topic: {self.config.output_topic}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kafka components: {e}")
            raise
    
    def _consume_observations(self):
        """Main observation consumption loop."""
        try:
            logger.info(f"Starting consumption from topic: {self.config.input_topic}")
            
            while self.running:
                try:
                    # Poll for messages
                    message_batch = self.consumer.poll(timeout_ms=self.config.poll_timeout_ms)
                    
                    if not message_batch:
                        continue
                    
                    # Process messages
                    for topic_partition, messages in message_batch.items():
                        for message in messages:
                            self._process_message(message)
                
                    # Periodic cleanup (time-based, not message-count based)
                    current_time = time.time()
                    if current_time - self.last_cleanup_time >= 60:  # 60 second interval
                        cleaned = self.inference_engine.cleanup_expired_users()
                        self.last_cleanup_time = current_time
                
                except Exception as e:
                    logger.error(f"Error in consumption loop: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Consumer loop error: {e}")
            raise
    
    def _process_message(self, message):
        """
        Process individual Kafka message.
        
        Args:
            message: Kafka message object
        """
        try:
            # Extract message data
            value = message.value
            key = message.key
            
            if not value or not isinstance(value, dict):
                logger.warning(f"Invalid message format: {value}")
                return
            
            user_id = value.get("user")
            observation = value.get("observation", [])
            timestamp = value.get("t", time.time())
            
            # Validate message format
            if not user_id or not isinstance(observation, list) or len(observation) != 8:
                logger.warning(f"Invalid observation message from user {user_id}: {value}")
                return
            
            # Forward to inference engine
            result = self.inference_engine.process_observation(user_id, observation, timestamp)
            
            if result:
                # Publish phase inference result
                self.producer.publish_phase_result(result)
                self.processed_count += 1
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def start_consuming(self):
        """Start consuming observations."""
        if self.running:
            logger.warning("Consumer is already running")
            return
        
        self.running = True
        
        try:
            self._initialize_components()
            
            # Start consumer thread
            self.consumer_thread = threading.Thread(
                target=self._consume_observations,
                name="Stage4Consumer",
                daemon=True
            )
            self.consumer_thread.start()
            
            logger.info("Stage-4 consumer started")
            
        except Exception as e:
            logger.error(f"Failed to start consumer: {e}")
            self.running = False
            raise
    
    def stop_consuming(self):
        """Stop consuming observations."""
        self.running = False
        
        if self.consumer_thread and self.consumer_thread.is_alive():
            self.consumer_thread.join(timeout=10.0)
        
        if self.consumer:
            self.consumer.close()
        
        if self.producer:
            self.producer.close()
        
        logger.info("Stage-4 consumer stopped")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get consumer and inference statistics."""
        inference_stats = self.inference_engine.get_statistics()
        
        return {
            'processed_messages': self.processed_count,
            'running': self.running,
            'input_topic': self.config.input_topic,
            'output_topic': self.config.output_topic,
            'active_users': inference_stats.get('active_users', 0),
            'total_inferences': inference_stats.get('total_inferences', 0),
            'inferences_per_second': inference_stats.get('inferences_per_second', 0.0)
        }
