"""
Configuration parameters for the cognitive intent engine.

This module contains all configurable parameters including
update weights, thresholds, and behavioral adaptation settings.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class IntentEngineConfig:
    """Configuration for cognitive intent engine."""
    
    # EMA smoothing parameters (decay rates)
    knowledge_decay: float = 0.95
    capability_decay: float = 0.98
    intent_decay: float = 0.90
    uncertainty_decay: float = 0.92
    risk_tolerance_decay: float = 0.93
    effort_decay: float = 0.94
    goal_proximity_decay: float = 0.96
    
    # Knowledge update weights
    knowledge_sensitivity_weight: float = 0.3
    knowledge_novelty_weight: float = -0.2  # Negative: low novelty increases knowledge
    knowledge_domain_weight: float = 0.1
    
    # Capability update weights
    capability_success_weight: float = 0.15
    capability_privilege_weight: float = 0.25
    capability_tool_weight: float = 0.1
    
    # Effort update weights
    effort_cost_weight: float = 0.2
    effort_time_density_weight: float = 0.15
    effort_repetition_weight: float = 0.1
    
    # Risk tolerance update weights
    risk_cost_weight: float = 0.3
    risk_success_weight: float = 0.2
    risk_retry_weight: float = 0.25
    
    # Uncertainty update weights
    uncertainty_novelty_weight: float = 0.3
    uncertainty_domain_diversity_weight: float = 0.2
    uncertainty_time_pattern_weight: float = 0.1
    
    # Goal proximity update weights (milestone-based)
    goal_staging_weight: float = 0.4
    goal_bulk_access_weight: float = 0.5
    goal_exfil_weight: float = 0.8
    goal_privilege_escalation_weight: float = 0.3
    
    # Intent calculation weights
    intent_effort_weight: float = 0.25
    intent_uncertainty_weight: float = 0.2  # Uses (1 - uncertainty)
    intent_knowledge_weight: float = 0.2
    intent_risk_weight: float = 0.15
    intent_capability_multiplier: float = 1.0
    intent_behavioral_prior_weight: float = 0.2
    
    # Alert thresholds
    alert_intent_threshold: float = 0.7
    alert_goal_threshold: float = 0.6
    alert_capability_threshold: float = 0.5
    alert_combined_threshold: float = 0.3  # I(t) * G(t) * C(t)
    
    # Behavioral adaptation parameters
    behavioral_deviation_weight: float = 0.3
    behavioral_peer_weight: float = 0.2
    behavioral_time_anomaly_weight: float = 0.25
    behavioral_frequency_weight: float = 0.25
    
    # Pattern detection thresholds
    pattern_learning_threshold: float = 0.4
    pattern_persistence_threshold: float = 0.5
    pattern_confidence_threshold: float = 0.6
    pattern_imminent_threshold: float = 0.8
    
    # State management
    max_history_entries: int = 50
    state_ttl_seconds: float = 86400 * 30  # 30 days
    
    # Simulation parameters
    simulation_time_step: float = 1.0  # seconds
    simulation_print_interval: int = 10  # events
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'IntentEngineConfig':
        """Create config from dictionary."""
        config = cls()
        for key, value in config_dict.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'knowledge_decay': self.knowledge_decay,
            'capability_decay': self.capability_decay,
            'intent_decay': self.intent_decay,
            'uncertainty_decay': self.uncertainty_decay,
            'risk_tolerance_decay': self.risk_tolerance_decay,
            'effort_decay': self.effort_decay,
            'goal_proximity_decay': self.goal_proximity_decay,
            'knowledge_sensitivity_weight': self.knowledge_sensitivity_weight,
            'knowledge_novelty_weight': self.knowledge_novelty_weight,
            'knowledge_domain_weight': self.knowledge_domain_weight,
            'capability_success_weight': self.capability_success_weight,
            'capability_privilege_weight': self.capability_privilege_weight,
            'capability_tool_weight': self.capability_tool_weight,
            'effort_cost_weight': self.effort_cost_weight,
            'effort_time_density_weight': self.effort_time_density_weight,
            'effort_repetition_weight': self.effort_repetition_weight,
            'risk_cost_weight': self.risk_cost_weight,
            'risk_success_weight': self.risk_success_weight,
            'risk_retry_weight': self.risk_retry_weight,
            'uncertainty_novelty_weight': self.uncertainty_novelty_weight,
            'uncertainty_domain_diversity_weight': self.uncertainty_domain_diversity_weight,
            'uncertainty_time_pattern_weight': self.uncertainty_time_pattern_weight,
            'goal_staging_weight': self.goal_staging_weight,
            'goal_bulk_access_weight': self.goal_bulk_access_weight,
            'goal_exfil_weight': self.goal_exfil_weight,
            'goal_privilege_escalation_weight': self.goal_privilege_escalation_weight,
            'intent_effort_weight': self.intent_effort_weight,
            'intent_uncertainty_weight': self.intent_uncertainty_weight,
            'intent_knowledge_weight': self.intent_knowledge_weight,
            'intent_risk_weight': self.intent_risk_weight,
            'intent_capability_multiplier': self.intent_capability_multiplier,
            'intent_behavioral_prior_weight': self.intent_behavioral_prior_weight,
            'alert_intent_threshold': self.alert_intent_threshold,
            'alert_goal_threshold': self.alert_goal_threshold,
            'alert_capability_threshold': self.alert_capability_threshold,
            'alert_combined_threshold': self.alert_combined_threshold,
            'behavioral_deviation_weight': self.behavioral_deviation_weight,
            'behavioral_peer_weight': self.behavioral_peer_weight,
            'behavioral_time_anomaly_weight': self.behavioral_time_anomaly_weight,
            'behavioral_frequency_weight': self.behavioral_frequency_weight,
            'pattern_learning_threshold': self.pattern_learning_threshold,
            'pattern_persistence_threshold': self.pattern_persistence_threshold,
            'pattern_confidence_threshold': self.pattern_confidence_threshold,
            'pattern_imminent_threshold': self.pattern_imminent_threshold,
            'max_history_entries': self.max_history_entries,
            'state_ttl_seconds': self.state_ttl_seconds,
            'simulation_time_step': self.simulation_time_step,
            'simulation_print_interval': self.simulation_print_interval
        }
    
    def validate(self) -> bool:
        """Validate configuration parameters."""
        # Check that all weights are in reasonable ranges
        for attr_name in dir(self):
            if attr_name.endswith('_weight') or attr_name.endswith('_decay'):
                value = getattr(self, attr_name)
                if not (0.0 <= value <= 1.0):
                    raise ValueError(f"Parameter {attr_name} must be in [0,1], got {value}")
        
        # Check thresholds
        for attr_name in dir(self):
            if attr_name.endswith('_threshold'):
                value = getattr(self, attr_name)
                if not (0.0 <= value <= 1.0):
                    raise ValueError(f"Threshold {attr_name} must be in [0,1], got {value}")
        
        return True


# Default configuration instance
DEFAULT_CONFIG = IntentEngineConfig()


def get_config(config_path: str = None) -> IntentEngineConfig:
    """
    Load configuration from file or return default.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        IntentEngineConfig instance
    """
    if config_path:
        import json
        with open(config_path, 'r') as f:
            config_dict = json.load(f)
        return IntentEngineConfig.from_dict(config_dict)
    
    return DEFAULT_CONFIG
