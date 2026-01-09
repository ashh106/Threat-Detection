"""
FILE: producer.py

STAGE:
    Stage-4 Behavioral Phase Inference

PURPOSE:
    Kafka producer for behavioral phase inference results.
    This module publishes HMM phase inference results to the
    behavioral_phase topic for downstream stages.

INPUT:
    HMM inference results from inference engine
    Schema: {"t": ..., "user": ..., "state": ..., "state_probabilities": {...}, "log_likelihood": ...}

OUTPUT:
    Kafka topic: behavioral_phase
    Message format: Same as input (passed through)

KAFKA INTEGRATION:
    IPv4-only bootstrap servers
    Message key: user_id (for per-user ordering)
    Acks: all (reliable delivery)
    Retries: 3 (fault tolerance)

NOTE: No message transformation - only reliable publishing.
"""

import time
import threading
import logging
import json
from typing import Dict, Any
from dataclasses import dataclass

# Kafka imports
try:
    from kafka import KafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("Warning: kafka-python not installed. Using mock Kafka for testing.")

logger = logging.getLogger(__name__)


@dataclass
class ProducerConfig:
    """Configuration for Stage-4 producer."""
    bootstrap_servers: str = "127.0.0.1:9092"
    output_topic: str = "behavioral_phase"
    client_id: str = "stage-4-hmm-producer"


class PhaseProducer:
    """
    Kafka producer for behavioral phase inference results.
    
    Publishes HMM phase inference results to behavioral_phase topic
    with reliable delivery and proper message keying.
    """
    
    def __init__(self, config: ProducerConfig):
        """Initialize producer with configuration."""
        self.config = config
        self.producer = None
        self.publish_count = 0
        self.error_count = 0
    
    def initialize(self):
        """Initialize Kafka producer."""
        if not KAFKA_AVAILABLE:
            raise RuntimeError("Kafka integration required for Stage-4 processing")
        
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.config.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                client_id=self.config.client_id,
                acks='all',
                retries=3,
                request_timeout_ms=10000,
                batch_size=16384,
                linger_ms=10
            )
            
            logger.info(f"Kafka producer initialized for topic: {self.config.output_topic}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            raise
    
    def publish_phase_result(self, result: Dict[str, Any]):
        """
        Publish phase inference result to Kafka.
        
        Args:
            result: HMM inference result dictionary
        """
        if not self.producer:
            logger.error("Producer not initialized")
            return
        
        try:
            # Extract user_id for message key
            user_id = result.get("user", "")
            
            # Send message with user_id as key for ordering
            future = self.producer.send(
                topic=self.config.output_topic,
                value=result,
                key=user_id
            )
            
            # Block briefly to ensure delivery
            record_metadata = future.get(timeout=5.0)
            
            self.publish_count += 1
            
            # Debug logging for first few messages
            if self.publish_count <= 5:
                logger.debug(f"Published phase result for user {user_id}: {result.get('state')}")
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Failed to publish phase result: {e}")
    
    def flush(self):
        """Force flush of any buffered messages."""
        if self.producer:
            self.producer.flush()
            logger.debug("Flushed producer buffers")
    
    def close(self):
        """Close producer and clean up resources."""
        if self.producer:
            try:
                self.producer.flush()
                self.producer.close()
                logger.info("Kafka producer closed")
            except Exception as e:
                logger.error(f"Error closing producer: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get producer statistics."""
        return {
            'published_messages': self.publish_count,
            'error_count': self.error_count,
            'success_rate': (self.publish_count / max(self.publish_count + self.error_count, 1)) * 100,
            'output_topic': self.config.output_topic
        }
