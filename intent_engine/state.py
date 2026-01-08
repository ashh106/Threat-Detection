"""
FILE: state.py

STAGE:
    Stage-3 Cognitive Intent Engine

PURPOSE:
    Core cognitive state representation with EMA-based temporal dynamics.
    This module implements the mathematical foundation for cognitive factor
    calculations using exponential moving averages derived from canonical events.

EQUATIONS IMPLEMENTED:
    - Knowledge: K(t+1) = (1-αK)K(t) + αK⋅sensitivity⋅(1-novelty)
    - Uncertainty: U(t+1) = (1-αU)U(t) + αU⋅novelty
    - Effort: E(t+1) = (1-αE)E(t) + αE⋅effort_cost
    - Risk tolerance: R(t+1) = (1-αR)R(t) + αR⋅risk_cost⋅1(success)
    - Persistence: P(t+1) = (1-αP)P(t) + αP⋅(1-novelty)
    - Capability: C(t) = σ(wK⋅K(t) + wE⋅E(t) + wP⋅P(t) - wU⋅U(t))
    - Intent strength: I(t) = σ(wK⋅K(t) + wE⋅E(t) + wR⋅R(t) + wP⋅P(t) - wU⋅U(t))

NOTE: No ML training happens here - only deterministic EMA calculations.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
import time
import json
import math


@dataclass
class CognitiveState:
    """
    Cognitive state vector with EMA-based temporal dynamics.
    
    All values are normalized to [0,1] and represent the user's
    current cognitive state regarding potential insider threats.
    """
    # Core cognitive factors (EMA-based)
    knowledge: float = 0.0      # K(t) - Knowledge of sensitive space
    uncertainty: float = 1.0    # U(t) - Uncertainty  
    effort: float = 0.0          # E(t) - Effort invested
    risk_tolerance: float = 0.0  # R(t) - Risk tolerance
    persistence: float = 0.0     # P(t) - Behavioral consistency (NEW)
    
    # Derived factors (computed, not stored)
    # capability: float = 0.0      # C(t) - Capability to act (derived)
    # intent_strength: float = 0.0 # I(t) - Intent strength (derived)
    
    # Metadata
    user_id: str = ""
    last_updated: float = field(default_factory=time.time)
    event_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            'knowledge': self.knowledge,
            'uncertainty': self.uncertainty,
            'effort': self.effort,
            'risk_tolerance': self.risk_tolerance,
            'persistence': self.persistence,
            'capability': self.compute_capability(),
            'intent_strength': self.compute_intent_strength(),
            'user_id': self.user_id,
            'last_updated': self.last_updated,
            'event_count': self.event_count
        }
    
    def compute_capability(self) -> float:
        """
        Compute derived capability factor.
        C(t) = σ(wK⋅K(t) + wE⋅E(t) + wP⋅P(t) - wU⋅U(t))
        """
        # Default weights (configurable)
        wK, wE, wP, wU = 0.3, 0.3, 0.2, 0.2
        
        # Linear combination
        linear = wK * self.knowledge + wE * self.effort + wP * self.persistence - wU * self.uncertainty
        
        # Sigmoid activation σ(x) = 1 / (1 + exp(-x))
        return 1.0 / (1.0 + math.exp(-linear))
    
    def compute_intent_strength(self) -> float:
        """
        Compute derived intent strength factor.
        I(t) = σ(wK⋅K(t) + wE⋅E(t) + wR⋅R(t) + wP⋅P(t) - wU⋅U(t))
        """
        # Default weights (configurable)
        wK, wE, wR, wP, wU = 0.25, 0.2, 0.2, 0.15, 0.2
        
        # Linear combination
        linear = wK * self.knowledge + wE * self.effort + wR * self.risk_tolerance + wP * self.persistence - wU * self.uncertainty
        
        # Sigmoid activation σ(x) = 1 / (1 + exp(-x))
        return 1.0 / (1.0 + math.exp(-linear))
    
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
    
    def normalize(self):
        """Ensure all values are within [0,1] range."""
        for field_name in ['knowledge', 'uncertainty', 'effort', 'risk_tolerance', 'persistence']:
            value = getattr(self, field_name)
            setattr(self, field_name, max(0.0, min(1.0, value)))
    
    def __str__(self) -> str:
        """String representation of cognitive state."""
        return (f"CognitiveState(user={self.user_id}, "
                f"K={self.knowledge:.3f}, U={self.uncertainty:.3f}, "
                f"E={self.effort:.3f}, R={self.risk_tolerance:.3f}, "
                f"P={self.persistence:.3f}, C={self.compute_capability():.3f}, "
                f"I={self.compute_intent_strength():.3f})")
