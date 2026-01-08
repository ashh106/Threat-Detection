"""
FILE: state.py

STAGE:
    Stage-3 Cognitive Intent Engine

PURPOSE:
    Stateful cognitive state representation for intent inference.
    This module defines the core cognitive state vector that tracks
    user intent components over time for the intent engine.

INPUTS:
    Canonical events from canonicalization stage.
    Processed security events for cognitive analysis.

OUTPUTS:
    Cognitive state vectors.
    User intent state for behavioral analysis and ML processing.

IMPORTANT:
    This file must not implement logic from other stages.
    State data structures and basic operations only.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import time
import json


@dataclass
class CognitiveState:
    """
    Cognitive state vector for intent inference.
    
    All values are normalized to [0,1] and represent the user's
    current cognitive state regarding potential insider threats.
    """
    # Core cognitive factors
    knowledge: float = 0.0      # K(t) - Knowledge of sensitive space
    capability: float = 0.0    # C(t) - Capability to act
    intent: float = 0.0        # I(t) - Intent strength (latent, inferred)
    uncertainty: float = 1.0   # U(t) - Uncertainty
    risk_tolerance: float = 0.0 # R(t) - Risk tolerance
    effort: float = 0.0        # E(t) - Effort invested
    goal_proximity: float = 0.0 # G(t) - Goal proximity
    
    # Metadata
    user_id: str = ""
    last_updated: float = field(default_factory=time.time)
    event_count: int = 0
    
    # History for trajectory analysis (keep last N updates)
    update_history: list = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            'knowledge': self.knowledge,
            'capability': self.capability,
            'intent': self.intent,
            'uncertainty': self.uncertainty,
            'risk_tolerance': self.risk_tolerance,
            'effort': self.effort,
            'goal_proximity': self.goal_proximity,
            'user_id': self.user_id,
            'last_updated': self.last_updated,
            'event_count': self.event_count
        }
    
    def to_json(self) -> str:
        """Convert state to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CognitiveState':
        """Create state from dictionary."""
        state = cls()
        for key, value in data.items():
            if hasattr(state, key):
                setattr(state, key, value)
        return state
    
    def update_history_entry(self, event_type: str, update_type: str):
        """Add entry to update history for trajectory analysis."""
        entry = {
            'timestamp': time.time(),
            'event_type': event_type,
            'update_type': update_type,
            'state_snapshot': self.to_dict()
        }
        self.update_history.append(entry)
        
        # Keep only last 50 entries to prevent memory bloat
        if len(self.update_history) > 50:
            self.update_history = self.update_history[-50:]
    
    def get_trajectory_pattern(self) -> Dict[str, str]:
        """
        Analyze recent trajectory to identify patterns.
        
        Returns:
            Dictionary describing detected patterns
        """
        if len(self.update_history) < 3:
            return {'pattern': 'insufficient_data'}
        
        recent = self.update_history[-3:]
        
        # Extract trends for key factors
        k_trend = self._get_trend([h['state_snapshot']['knowledge'] for h in recent])
        u_trend = self._get_trend([h['state_snapshot']['uncertainty'] for h in recent])
        e_trend = self._get_trend([h['state_snapshot']['effort'] for h in recent])
        r_trend = self._get_trend([h['state_snapshot']['risk_tolerance'] for h in recent])
        g_trend = self._get_trend([h['state_snapshot']['goal_proximity'] for h in recent])
        
        patterns = []
        
        # Pattern detection based on trajectories
        if k_trend == 'increasing' and u_trend == 'decreasing' and e_trend == 'increasing':
            patterns.append('learning_planning')
        
        if e_trend == 'increasing' and any('failure' in h.get('event_type', '') for h in recent):
            patterns.append('persistence_after_failure')
        
        if r_trend == 'increasing' and g_trend == 'increasing':
            patterns.append('malicious_confidence')
        
        if g_trend == 'increasing' and len([h for h in recent[-2:] if h['state_snapshot']['goal_proximity'] > 0.7]) >= 2:
            patterns.append('imminent_risk')
        
        return {
            'pattern': patterns[0] if patterns else 'normal',
            'trends': {
                'knowledge': k_trend,
                'uncertainty': u_trend,
                'effort': e_trend,
                'risk_tolerance': r_trend,
                'goal_proximity': g_trend
            }
        }
    
    def _get_trend(self, values: list) -> str:
        """Determine trend direction from a list of values."""
        if len(values) < 2:
            return 'stable'
        
        # Simple linear trend detection
        diff = values[-1] - values[0]
        if abs(diff) < 0.05:
            return 'stable'
        elif diff > 0:
            return 'increasing'
        else:
            return 'decreasing'
    
    def normalize(self):
        """Ensure all values are within [0,1] range."""
        for field_name in ['knowledge', 'capability', 'intent', 'uncertainty', 
                          'risk_tolerance', 'effort', 'goal_proximity']:
            value = getattr(self, field_name)
            setattr(self, field_name, max(0.0, min(1.0, value)))
    
    def __str__(self) -> str:
        """String representation of cognitive state."""
        return (f"CognitiveState(user={self.user_id}, "
                f"K={self.knowledge:.3f}, C={self.capability:.3f}, "
                f"I={self.intent:.3f}, U={self.uncertainty:.3f}, "
                f"R={self.risk_tolerance:.3f}, E={self.effort:.3f}, "
                f"G={self.goal_proximity:.3f})")
