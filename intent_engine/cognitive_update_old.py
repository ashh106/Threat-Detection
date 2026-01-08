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
    
    def _update_capability(self, state: CognitiveState, event: CanonicalEvent) -> float:
        """
        Update capability: C(t) increases slowly with success, privilege depth, and tool power.
        
        C(t+1) = α*C(t) + (1-α)*(w_success*success + w_priv*privilege_level + w_tool*tool_power)
        """
        # Estimate privilege level from object_type and action
        privilege_level = self._estimate_privilege_level(event.action, event.object_type)
        
        # Estimate tool power from action
        tool_power = self._estimate_tool_power(event.action)
        
        # Capability increment
        capability_increment = (
            self.config.capability_success_weight * (1.0 if event.success else 0.0) +
            self.config.capability_privilege_weight * privilege_level +
            self.config.capability_tool_weight * tool_power
        )
        
        # EMA update with slower decay (capability builds slowly)
        new_capability = (
            self.config.capability_decay * state.capability +
            (1 - self.config.capability_decay) * capability_increment
        )
        
        return max(0.0, new_capability)
    
    def _update_effort(self, state: CognitiveState, event: CanonicalEvent) -> float:
        """
        Update effort: E(t) increases with repeated, costly actions and time density.
        
        E(t+1) = α*E(t) + (1-α)*(w_cost*effort_cost + w_density*time_density + w_rep*repetition)
        """
        # Calculate time density (events per hour in recent window)
        time_density = self._calculate_time_density(state.user_id, event.timestamp)
        
        # Calculate repetition factor (same action/object combination)
        repetition_factor = self._calculate_repetition_factor(state.user_id, event)
        
        # Effort increment
        effort_increment = (
            self.config.effort_cost_weight * event.effort_cost +
            self.config.effort_time_density_weight * time_density +
            self.config.effort_repetition_weight * repetition_factor
        )
        
        # EMA update
        new_effort = (
            self.config.effort_decay * state.effort +
            (1 - self.config.effort_decay) * effort_increment
        )
        
        return max(0.0, new_effort)
    
    def _update_risk_tolerance(self, state: CognitiveState, event: CanonicalEvent) -> float:
        """
        Update risk tolerance: R(t) increases with high-risk actions that succeed or are retried.
        
        R(t+1) = α*R(t) + (1-α)*(w_risk*risk_cost + w_success*success_bonus + w_retry*retry_factor)
        """
        # Success bonus for high-risk actions
        success_bonus = 0.0
        if event.success and event.risk_cost > 0.5:
            success_bonus = self.config.risk_success_weight * event.risk_cost
        
        # Retry factor from failure patterns
        retry_factor = self._calculate_retry_factor(state.user_id, event)
        
        # Risk tolerance increment
        risk_increment = (
            self.config.risk_cost_weight * event.risk_cost +
            success_bonus +
            self.config.risk_retry_weight * retry_factor
        )
        
        # EMA update
        new_risk_tolerance = (
            self.config.risk_tolerance_decay * state.risk_tolerance +
            (1 - self.config.risk_tolerance_decay) * risk_increment
        )
        
        return max(0.0, new_risk_tolerance)
    
    def _update_uncertainty(self, state: CognitiveState, event: CanonicalEvent) -> float:
        """
        Update uncertainty: U(t) decreases as novelty drops and domains converge.
        
        U(t+1) = α*U(t) + (1-α)*(w_novelty*novelty + w_diversity*domain_diversity - w_time*time_regularity)
        """
        # Domain diversity (inverse of domain convergence)
        domain_diversity = self._calculate_domain_diversity(state.user_id)
        
        # Time regularity (regular patterns reduce uncertainty)
        time_regularity = self._calculate_time_regularity(state.user_id)
        
        # Uncertainty increment (higher values = more uncertainty)
        uncertainty_increment = (
            self.config.uncertainty_novelty_weight * event.novelty +
            self.config.uncertainty_domain_diversity_weight * domain_diversity -
            self.config.uncertainty_time_pattern_weight * time_regularity
        )
        
        # EMA update
        new_uncertainty = (
            self.config.uncertainty_decay * state.uncertainty +
            (1 - self.config.uncertainty_decay) * uncertainty_increment
        )
        
        return max(0.0, min(1.0, new_uncertainty))
    
    def _estimate_privilege_level(self, action: str, object_type: str) -> float:
        """Estimate privilege level from action and object type."""
        high_privilege_actions = {'delete', 'modify', 'admin', 'escalate', 'export'}
        medium_privilege_actions = {'access', 'read', 'write', 'execute'}
        
        if action.lower() in high_privilege_actions:
            return 0.8
        elif action.lower() in medium_privilege_actions:
            return 0.5
        else:
            return 0.2
    
    def _estimate_tool_power(self, action: str) -> float:
        """Estimate tool power from action type."""
        high_power_tools = {'script', 'automation', 'bulk', 'api', 'admin'}
        medium_power_tools = {'gui', 'manual', 'direct'}
        
        if any(tool in action.lower() for tool in high_power_tools):
            return 0.7
        elif any(tool in action.lower() for tool in medium_power_tools):
            return 0.4
        else:
            return 0.1
    
    def _calculate_time_density(self, user_id: str, current_time: float) -> float:
        """Calculate event density in recent time window."""
        if user_id not in self.user_event_times:
            return 0.0
        
        recent_times = [t for t in self.user_event_times[user_id] 
                       if current_time - t <= 3600]  # Last hour
        
        if len(recent_times) < 2:
            return 0.0
        
        # Events per hour, normalized to [0,1]
        events_per_hour = len(recent_times)
        normalized_density = min(1.0, events_per_hour / 100.0)  # 100 events/hour = max density
        
        return normalized_density
    
    def _calculate_repetition_factor(self, user_id: str, event: CanonicalEvent) -> float:
        """Calculate repetition factor for same action/object combination."""
        if user_id not in self.user_failure_patterns:
            return 0.0
        
        action_key = f"{event.action}:{event.object_type}"
        failure_count = self.user_failure_patterns[user_id].get(action_key, 0)
        
        # Normalize retry factor: 5+ failures = max repetition
        return min(1.0, failure_count / 5.0)
    
    def _calculate_retry_factor(self, user_id: str, event: CanonicalEvent) -> float:
        """Calculate retry factor from failure patterns."""
        if user_id not in self.user_failure_patterns:
            return 0.0
        
        action_key = f"{event.action}:{event.object_type}"
        failure_count = self.user_failure_patterns[user_id].get(action_key, 0)
        
        # Normalize retry factor: 5+ failures = max retry
        return min(1.0, failure_count / 5.0)
    
    def _calculate_domain_diversity(self, user_id: str) -> float:
        """Calculate domain diversity (inverse of convergence)."""
        if user_id not in self.user_domains:
            return 1.0  # Maximum uncertainty for new users
        
        domain_count = len(self.user_domains[user_id])
        
        # More domains = higher diversity = higher uncertainty
        # Normalize: 1 domain = 0 diversity, 10+ domains = max diversity
        diversity = min(1.0, (domain_count - 1) / 9.0)
        
        return diversity
    
    def _calculate_time_regularity(self, user_id: str) -> float:
        """Calculate time regularity (regular patterns reduce uncertainty)."""
        if user_id not in self.user_event_times:
            return 0.0
        
        times = self.user_event_times[user_id][-10:]  # Last 10 events
        if len(times) < 3:
            return 0.0
        
        # Calculate intervals
        intervals = [times[i] - times[i-1] for i in range(1, len(times))]
        
        # Regularity = 1 - coefficient of variation
        if len(intervals) < 2:
            return 1.0  # Perfectly regular
        
        mean_interval = sum(intervals) / len(intervals)
        if mean_interval == 0:
            return 1.0
        
        variance = sum((x - mean_interval) ** 2 for x in intervals) / len(intervals)
        std_dev = math.sqrt(variance)
        
        cv = std_dev / mean_interval if mean_interval > 0 else 0
        regularity = max(0.0, 1.0 - cv)
        
        return regularity
