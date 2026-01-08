"""
FILE: behavioral_adapter.py

STAGE:
    Stage-4 Behavioral Model

PURPOSE:
    Behavioral signal integration for intent inference enhancement.
    This module adapts behavioral signals into priors that influence
    intent inference without directly determining intent.

INPUTS:
    Cognitive states from intent engine stage.
    User intent states for behavioral analysis.

OUTPUTS:
    Behavioral priors for intent inference.
    Adapted behavioral signals for cognitive processing.

IMPORTANT:
    This file must not implement logic from other stages.
    Behavioral signal processing and adaptation only.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import time
import math

# Note: Config import should be updated when integration is needed
# from .config import IntentEngineConfig


@dataclass
class BehavioralSignals:
    """Behavioral model outputs for a user."""
    deviation_score: float = 0.0        # How much user deviates from their baseline
    peer_deviation: float = 0.0        # How much user deviates from peers
    time_anomaly: float = 0.0          # Temporal pattern anomaly
    access_frequency_zscore: float = 0.0  # Access frequency anomaly
    timestamp: float = 0.0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()


class BehavioralAdapter:
    """
    Adapts behavioral signals into intent priors.
    
    Behavioral signals are used as gating functions and priors,
    not as direct intent labels.
    """
    
    def __init__(self, config: IntentEngineConfig):
        self.config = config
        self.signal_history: Dict[str, list] = {}  # user_id -> list of signals
    
    def process_signals(self, user_id: str, signals: BehavioralSignals) -> Dict[str, float]:
        """
        Process behavioral signals and return intent priors.
        
        Args:
            user_id: User identifier
            signals: Behavioral signals from external model
            
        Returns:
            Dictionary of intent priors
        """
        # Store signals for trend analysis
        self._store_signals(user_id, signals)
        
        # Calculate priors using configurable weights
        priors = {
            'deviation_prior': self._calculate_deviation_prior(signals),
            'peer_prior': self._calculate_peer_prior(signals),
            'temporal_prior': self._calculate_temporal_prior(signals),
            'frequency_prior': self._calculate_frequency_prior(signals),
            'combined_prior': self._calculate_combined_prior(signals)
        }
        
        return priors
    
    def _store_signals(self, user_id: str, signals: BehavioralSignals):
        """Store signals for historical analysis."""
        if user_id not in self.signal_history:
            self.signal_history[user_id] = []
        
        self.signal_history[user_id].append(signals)
        
        # Keep only recent signals (last 100)
        if len(self.signal_history[user_id]) > 100:
            self.signal_history[user_id] = self.signal_history[user_id][-100:]
    
    def _calculate_deviation_prior(self, signals: BehavioralSignals) -> float:
        """
        Calculate deviation prior.
        
        Higher deviation increases intent prior, but with diminishing returns.
        """
        deviation = abs(signals.deviation_score)
        
        # Apply sigmoid function for smooth scaling
        # High deviation (>3) should map to high prior (~0.8)
        # Low deviation (<1) should map to low prior (~0.2)
        prior = 1 / (1 + math.exp(-0.5 * (deviation - 2)))
        
        return prior * self.config.behavioral_deviation_weight
    
    def _calculate_peer_prior(self, signals: BehavioralSignals) -> float:
        """
        Calculate peer deviation prior.
        
        Being significantly different from peers can indicate intent.
        """
        peer_dev = abs(signals.peer_deviation)
        
        # Peer deviation is less strong than personal deviation
        prior = 1 / (1 + math.exp(-0.3 * (peer_dev - 2.5)))
        
        return prior * self.config.behavioral_peer_weight
    
    def _calculate_temporal_prior(self, signals: BehavioralSignals) -> float:
        """
        Calculate temporal anomaly prior.
        
        Unusual timing can indicate malicious intent.
        """
        time_anomaly = abs(signals.time_anomaly)
        
        # Time anomalies are strong indicators
        prior = 1 / (1 + math.exp(-0.6 * (time_anomaly - 1.5)))
        
        return prior * self.config.behavioral_time_anomaly_weight
    
    def _calculate_frequency_prior(self, signals: BehavioralSignals) -> float:
        """
        Calculate frequency anomaly prior.
        
        Unusual access patterns can indicate intent.
        """
        freq_z = abs(signals.access_frequency_zscore)
        
        # Frequency anomalies are moderate indicators
        prior = 1 / (1 + math.exp(-0.4 * (freq_z - 2)))
        
        return prior * self.config.behavioral_frequency_weight
    
    def _calculate_combined_prior(self, signals: BehavioralSignals) -> float:
        """
        Calculate combined behavioral prior.
        
        Combines all signals using weighted sum.
        """
        deviation_prior = self._calculate_deviation_prior(signals)
        peer_prior = self._calculate_peer_prior(signals)
        temporal_prior = self._calculate_temporal_prior(signals)
        frequency_prior = self._calculate_frequency_prior(signals)
        
        # Weighted combination
        combined = (
            deviation_prior + peer_prior + temporal_prior + frequency_prior
        ) / self.config.behavioral_deviation_weight  # Normalize by total weight
        
        # Apply gating function: only high combined scores pass through
        gated_prior = self._gate_prior(combined)
        
        return gated_prior
    
    def _gate_prior(self, prior: float) -> float:
        """
        Gate the prior to prevent noise from triggering intent.
        
        Only priors above threshold significantly influence intent.
        """
        gate_threshold = 0.3  # Only priors > 0.3 have meaningful impact
        
        if prior < gate_threshold:
            return 0.0
        else:
            # Scale priors above threshold
            return (prior - gate_threshold) / (1.0 - gate_threshold)
    
    def get_signal_trend(self, user_id: str, window_size: int = 10) -> Dict[str, str]:
        """
        Analyze trends in behavioral signals.
        
        Args:
            user_id: User identifier
            window_size: Number of recent signals to analyze
            
        Returns:
            Dictionary describing signal trends
        """
        if user_id not in self.signal_history:
            return {'status': 'no_data'}
        
        signals = self.signal_history[user_id][-window_size:]
        if len(signals) < 3:
            return {'status': 'insufficient_data'}
        
        trends = {}
        
        # Calculate trends for each signal
        for signal_name in ['deviation_score', 'peer_deviation', 'time_anomaly', 'access_frequency_zscore']:
            values = [getattr(s, signal_name) for s in signals]
            trends[signal_name] = self._get_trend_direction(values)
        
        return {'status': 'analyzed', 'trends': trends}
    
    def _get_trend_direction(self, values: list) -> str:
        """Determine trend direction from values."""
        if len(values) < 2:
            return 'stable'
        
        # Simple linear trend
        diff = values[-1] - values[0]
        if abs(diff) < 0.1:
            return 'stable'
        elif diff > 0:
            return 'increasing'
        else:
            return 'decreasing'
    
    def is_signal_anomalous(self, signals: BehavioralSignals) -> bool:
        """
        Determine if signals indicate anomalous behavior.
        
        Used as a quick check before detailed processing.
        """
        # Quick anomaly check using thresholds
        anomaly_thresholds = {
            'deviation_score': 2.0,
            'peer_deviation': 2.5,
            'time_anomaly': 1.5,
            'access_frequency_zscore': 2.0
        }
        
        for signal_name, threshold in anomaly_thresholds.items():
            if abs(getattr(signals, signal_name)) > threshold:
                return True
        
        return False
    
    def get_behavioral_context(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive behavioral context for a user.
        
        Returns:
            Dictionary with behavioral context including priors and trends
        """
        if user_id not in self.signal_history or not self.signal_history[user_id]:
            return {
                'status': 'no_data',
                'priors': {k: 0.0 for k in ['deviation_prior', 'peer_prior', 'temporal_prior', 'frequency_prior', 'combined_prior']},
                'trends': {'status': 'no_data'},
                'is_anomalous': False
            }
        
        latest_signals = self.signal_history[user_id][-1]
        priors = self.process_signals(user_id, latest_signals)
        trends = self.get_signal_trend(user_id)
        is_anomalous = self.is_signal_anomalous(latest_signals)
        
        return {
            'status': 'available',
            'priors': priors,
            'trends': trends,
            'is_anomalous': is_anomalous,
            'signal_count': len(self.signal_history[user_id]),
            'last_updated': latest_signals.timestamp
        }
