"""
FILE: cognitive_update.py

STAGE:
    Stage-3 Cognitive Intent Engine

PURPOSE:
    EMA-based cognitive state update equations for intent inference.
    This module implements the mathematical foundation for cognitive factor
    calculations using exponential moving averages derived from canonical events.

EQUATIONS IMPLEMENTED:
    - Knowledge: K(t+1) = (1-αK)K(t) + αK⋅sensitivity⋅(1-novelty)
    - Uncertainty: U(t+1) = (1-αU)U(t) + αU⋅novelty
    - Effort: E(t+1) = (1-αE)E(t) + αE⋅effort_cost
    - Risk tolerance: R(t+1) = (1-αR)R(t) + αR⋅risk_cost⋅1(success)
    - Persistence: P(t+1) = (1-αP)P(t) + αP⋅(1-novelty)

NOTE: No ML training happens here - only deterministic EMA calculations.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, Set
import time
import math

from state import CognitiveState
from config import IntentEngineConfig


@dataclass
class CanonicalEvent:
    """Canonical security event."""
    timestamp: float
    user_id: str
    action: str
    object_type: str
    domain: str
    success: bool
    sensitivity: float  # 0-1
    novelty: float      # 0-1
    risk_cost: float    # 0-1
    effort_cost: float  # 0-1
    source: str


class CognitiveUpdater:
    """
    EMA-based cognitive state updater with correct mathematical implementation.
    
    Implements explicit EMA update equations for each cognitive factor.
    """
    
    def __init__(self, config: IntentEngineConfig):
        self.config = config
        
        # EMA decay rates (configurable constants)
        self.alpha_K = 0.1  # Knowledge learning rate
        self.alpha_U = 0.15  # Uncertainty adaptation rate
        self.alpha_E = 0.2  # Effort accumulation rate
        self.alpha_R = 0.1  # Risk tolerance adaptation rate
        self.alpha_P = 0.05  # Persistence accumulation rate (slow decay)
    
    def update_state(self, state: CognitiveState, event: CanonicalEvent) -> CognitiveState:
        """
        Update cognitive state using EMA-based equations.
        
        Args:
            state: Current cognitive state
            event: Canonical event to process
            
        Returns:
            Updated cognitive state
        """
        # Apply EMA updates for each factor
        state.knowledge = self._update_knowledge(state, event)
        state.uncertainty = self._update_uncertainty(state, event)
        state.effort = self._update_effort(state, event)
        state.risk_tolerance = self._update_risk_tolerance(state, event)
        state.persistence = self._update_persistence(state, event)
        
        # Update metadata
        state.last_updated = event.timestamp
        state.event_count += 1
        
        # Normalize all values to [0,1]
        state.normalize()
        
        return state
    
    def _update_knowledge(self, state: CognitiveState, event: CanonicalEvent) -> float:
        """
        Update knowledge using EMA: K(t+1) = (1-αK)K(t) + αK⋅sensitivity⋅(1-novelty)
        
        Knowledge increases with high sensitivity, low novelty actions.
        """
        # ΔK(e) = sensitivity ⋅ (1 - novelty)
        delta_K = event.sensitivity * (1.0 - event.novelty)
        
        # EMA update: K(t+1) = (1-αK)K(t) + αK⋅ΔK(e)
        return (1.0 - self.alpha_K) * state.knowledge + self.alpha_K * delta_K
    
    def _update_uncertainty(self, state: CognitiveState, event: CanonicalEvent) -> float:
        """
        Update uncertainty using EMA: U(t+1) = (1-αU)U(t) + αU⋅novelty
        
        Uncertainty increases with novel actions.
        """
        # ΔU(e) = novelty
        delta_U = event.novelty
        
        # EMA update: U(t+1) = (1-αU)U(t) + αU⋅ΔU(e)
        return (1.0 - self.alpha_U) * state.uncertainty + self.alpha_U * delta_U
    
    def _update_effort(self, state: CognitiveState, event: CanonicalEvent) -> float:
        """
        Update effort using EMA: E(t+1) = (1-αE)E(t) + αE⋅effort_cost
        
        Effort accumulates based on effort_cost of actions.
        """
        # ΔE(e) = effort_cost
        delta_E = event.effort_cost
        
        # EMA update: E(t+1) = (1-αE)E(t) + αE⋅ΔE(e)
        return (1.0 - self.alpha_E) * state.effort + self.alpha_E * delta_E
    
    def _update_risk_tolerance(self, state: CognitiveState, event: CanonicalEvent) -> float:
        """
        Update risk tolerance using EMA: R(t+1) = (1-αR)R(t) + αR⋅risk_cost⋅1(success)
        
        Risk tolerance increases with successful risky actions.
        """
        # ΔR(e) = risk_cost ⋅ 1(success)
        delta_R = event.risk_cost * (1.0 if event.success else 0.0)
        
        # EMA update: R(t+1) = (1-αR)R(t) + αR⋅ΔR(e)
        return (1.0 - self.alpha_R) * state.risk_tolerance + self.alpha_R * delta_R
    
    def _update_persistence(self, state: CognitiveState, event: CanonicalEvent) -> float:
        """
        Update persistence using EMA: P(t+1) = (1-αP)P(t) + αP⋅(1-novelty)
        
        Persistence increases with non-novel, repeated actions.
        Decays slowly (low αP) and is bounded [0,1].
        """
        # ΔP(e) = (1 - novelty)
        delta_P = 1.0 - event.novelty
        
        # EMA update: P(t+1) = (1-αP)P(t) + αP⋅ΔP(e)
        return (1.0 - self.alpha_P) * state.persistence + self.alpha_P * delta_P