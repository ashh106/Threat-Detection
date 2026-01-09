"""
FILE: kafka_integration.py

STAGE:
    Stage-2 Canonicalization

PURPOSE:
    Kafka consumer and producer functionality for canonical event processing.
    This module provides the Kafka integration layer for consuming canonical events
    and publishing intent inference results.

INPUTS:
    Kafka topic: canonical-metadata
    Canonical security events from canonicalization stage.

OUTPUTS:
    Kafka topic: intent-inference
    Intent inference results for downstream consumption.

IMPORTANT:
    This file must not implement logic from other stages.
    Kafka messaging and data structure definitions only.
"""

import json
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import threading
import logging

try:
    from kafka import KafkaConsumer, KafkaProducer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("Warning: kafka-python not installed. Using mock Kafka for testing.")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class CanonicalEvent:
    """Canonical event from Kafka topic."""
    user: str
    timestamp: float
    action: str
    object_type: str
    sensitivity: float
    novelty: float
    effort: float
    risk: float
    success: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WindowSummary:
    """Aggregated metrics for a user time window."""
    user_id: str
    window_start: float
    window_end: float
    aggregated_metrics: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ObservationVector:
    """Feature vector for intent inference."""
    novelty_score: float
    sensitivity_pressure: float
    effort_escalation: float
    focus_score: float
    access_entropy: float
    time_compression: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class IntentBelief:
    """HMM-based intent belief probabilities."""
    explore_prob: float
    learn_prob: float
    collect_prob: float
    prepare_prob: float
    exfil_prob: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def get_dominant_intent(self) -> str:
        """Get the intent state with highest probability."""
        probs = {
            "EXPLORE": self.explore_prob,
            "LEARN": self.learn_prob,
            "COLLECT": self.collect_prob,
            "PREPARE": self.prepare_prob,
            "EXFIL": self.exfil_prob
        }
        return max(probs, key=probs.get)


@dataclass
class IntentInferenceResult:
    """Final intent inference result for publishing."""
    user_id: str
    window: Dict[str, float]  # window_start, window_end
    dominant_intent: str
    intent_probabilities: Dict[str, float]
    transition_velocity: float
    confidence_score: float
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MockKafkaConsumer:
    """Mock Kafka consumer for testing without real Kafka."""
    
    def __init__(self, *args, **kwargs):
        self.messages = deque()
        self.closed = False
    
    def add_test_event(self, event_data: Dict[str, Any]):
        """Add test event for mock Kafka."""
        if not KAFKA_AVAILABLE:
            self.messages.append(event_data)
            # Immediately process the message in mock mode
            # This simulates real-time consumption
            import threading
            def process_message():
                try:
                    # Create a mock message and process it immediately
                    message = MockMessage(event_data)
                    self._process_single_message(message)
                except Exception as e:
                    print(f"Error processing mock message: {e}")
            
            # Process in separate thread to simulate async behavior
            threading.Thread(target=process_message, daemon=True).start()
    
    def _process_single_message(self, message):
        """Process a single message (used by mock consumer)."""
        # This would normally be handled by the consumer's iteration logic
        # For mock, we need to manually trigger the processing
        pass
    
    def __iter__(self):
        return self
    
    def __next__(self):
        if self.closed or not self.messages:
            raise StopIteration
        
        message = self.messages.popleft()
        return MockMessage(message)
    
    def close(self):
        self.closed = True


class MockMessage:
    """Mock Kafka message."""
    
    def __init__(self, value: Dict[str, Any]):
        self.value = value


class MockKafkaProducer:
    """Mock Kafka producer for testing without real Kafka."""
    
    def __init__(self, *args, **kwargs):
        self.sent_messages = []
    
    def send(self, topic: str, value: Dict[str, Any]):
        """Mock send - store message for testing."""
        self.sent_messages.append({
            'topic': topic,
            'value': value,
            'timestamp': time.time()
        })
    
    def flush(self):
        pass
    
    def close(self):
        pass


class CanonicalEventConsumer:
    """Kafka consumer for canonical events with time window aggregation."""
    
    def __init__(self, bootstrap_servers: str = "localhost:9092", 
                 topic: str = "canonical-metadata",
                 window_size_minutes: int = 15):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.window_size_minutes = window_size_minutes
        
        # Event buffers per user
        self.user_buffers: Dict[str, List[CanonicalEvent]] = defaultdict(list)
        self.processed_windows: Dict[str, List[WindowSummary]] = defaultdict(list)
        
        # Initialize Kafka consumer
        if KAFKA_AVAILABLE:
            self.consumer = KafkaConsumer(
                topic,
                bootstrap_servers=bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True
            )
        else:
            self.consumer = MockKafkaConsumer()
            logger.warning("Using mock Kafka consumer")
        
        self.running = False
        self.window_callbacks: List[Callable[[WindowSummary], None]] = []
    
    def add_window_callback(self, callback: Callable[[WindowSummary], None]):
        """Add callback for processed windows."""
        self.window_callbacks.append(callback)
    
    def start_consuming(self):
        """Start consuming messages from Kafka."""
        self.running = True
        logger.info(f"Started consuming from topic: {self.topic}")
        
        try:
            for message in self.consumer:
                if not self.running:
                    break
                
                # Parse canonical event
                event_data = message.value
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
                
                # Add to user buffer
                self.user_buffers[event.user].append(event)
                
                # Process windows for this user
                self._process_user_windows(event.user)
                
        except Exception as e:
            logger.error(f"Error consuming messages: {e}")
        finally:
            self.consumer.close()
    
    def _process_user_windows(self, user_id: str):
        """Process time windows for a specific user."""
        events = self.user_buffers[user_id]
        if not events:
            return
        
        # Sort events by timestamp
        events.sort(key=lambda x: x.timestamp)
        
        # Find the latest event time
        latest_time = events[-1].timestamp
        window_start = latest_time - (self.window_size_minutes * 60)
        
        # Get events in the current window
        window_events = [
            e for e in events 
            if e.timestamp >= window_start and e.timestamp <= latest_time
        ]
        
        if len(window_events) >= 2:  # Need at least 2 events for meaningful aggregation
            # Create window summary
            window_summary = self._create_window_summary(
                user_id, window_start, latest_time, window_events
            )
            
            # Store and notify callbacks
            self.processed_windows[user_id].append(window_summary)
            
            for callback in self.window_callbacks:
                callback(window_summary)
            
            # Clean old events (keep events from last 2 windows)
            cutoff_time = latest_time - (2 * self.window_size_minutes * 60)
            self.user_buffers[user_id] = [
                e for e in events if e.timestamp >= cutoff_time
            ]
    
    def _create_window_summary(self, user_id: str, window_start: float, 
                              window_end: float, events: List[CanonicalEvent]) -> WindowSummary:
        """Create aggregated metrics for a time window."""
        if not events:
            return WindowSummary(
                user_id=user_id,
                window_start=window_start,
                window_end=window_end,
                aggregated_metrics={}
            )
        
        # Basic aggregations
        avg_sensitivity = sum(e.sensitivity for e in events) / len(events)
        avg_novelty = sum(e.novelty for e in events) / len(events)
        avg_effort = sum(e.effort for e in events) / len(events)
        avg_risk = sum(e.risk for e in events) / len(events)
        success_rate = sum(1 for e in events if e.success) / len(events)
        
        # Sensitivity trend (compare first half to second half)
        mid_point = len(events) // 2
        first_half_sensitivity = sum(e.sensitivity for e in events[:mid_point]) / max(1, mid_point)
        second_half_sensitivity = sum(e.sensitivity for e in events[mid_point:]) / max(1, len(events) - mid_point)
        sensitivity_trend = "↑" if second_half_sensitivity > first_half_sensitivity else "↓"
        
        # Novelty decay (how much novelty decreases over time)
        if len(events) >= 2:
            first_novelty = events[0].novelty
            last_novelty = events[-1].novelty
            novelty_decay = max(0, first_novelty - last_novelty)
        else:
            novelty_decay = 0.0
        
        # Effort escalation (increase in effort over time)
        if len(events) >= 2:
            first_effort = events[0].effort
            last_effort = events[-1].effort
            effort_escalation = max(0, last_effort - first_effort)
        else:
            effort_escalation = 0.0
        
        # Focus score (entropy of accessed objects)
        object_counts = {}
        for event in events:
            object_counts[event.object_type] = object_counts.get(event.object_type, 0) + 1
        
        # Calculate entropy
        total_events = len(events)
        entropy = -sum((count/total_events) * math.log2(count/total_events) 
                      for count in object_counts.values())
        focus_score = 1.0 - (entropy / math.log2(len(object_counts))) if len(object_counts) > 1 else 1.0
        
        # Time compression (events per minute)
        window_duration_minutes = (window_end - window_start) / 60
        time_compression = len(events) / max(1, window_duration_minutes)
        
        aggregated_metrics = {
            'event_count': len(events),
            'avg_sensitivity': avg_sensitivity,
            'sensitivity_trend': sensitivity_trend,
            'avg_novelty': avg_novelty,
            'novelty_decay': novelty_decay,
            'avg_effort': avg_effort,
            'effort_escalation': effort_escalation,
            'avg_risk': avg_risk,
            'success_rate': success_rate,
            'focus_score': focus_score,
            'access_entropy': entropy,
            'time_compression': time_compression,
            'unique_objects': len(object_counts)
        }
        
        return WindowSummary(
            user_id=user_id,
            window_start=window_start,
            window_end=window_end,
            aggregated_metrics=aggregated_metrics
        )
    
    def stop(self):
        """Stop consuming messages."""
        self.running = False
        if hasattr(self.consumer, 'close'):
            self.consumer.close()
    
    def add_test_event(self, event_data: Dict[str, Any]):
        """Add test event for mock Kafka."""
        if not KAFKA_AVAILABLE:
            self.consumer.add_message(event_data)


class IntentInferencePublisher:
    """Kafka producer for publishing intent inference results."""
    
    def __init__(self, bootstrap_servers: str = "localhost:9092",
                 topic: str = "intent-inference"):
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        
        # Initialize Kafka producer
        if KAFKA_AVAILABLE:
            self.producer = KafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
        else:
            self.producer = MockKafkaProducer()
            logger.warning("Using mock Kafka producer")
    
    def publish_inference(self, result: IntentInferenceResult):
        """Publish intent inference result to Kafka."""
        try:
            self.producer.send(self.topic, result.to_dict())
            logger.debug(f"Published inference for user {result.user_id}: {result.dominant_intent}")
        except Exception as e:
            logger.error(f"Error publishing inference: {e}")
    
    def flush(self):
        """Flush pending messages."""
        if hasattr(self.producer, 'flush'):
            self.producer.flush()
    
    def close(self):
        """Close the producer."""
        if hasattr(self.producer, 'close'):
            self.producer.close()


import math  # Import math for entropy calculations
