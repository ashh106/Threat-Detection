"""
FILE: phase_hmm.py

STAGE:
    Stage-3 Cognitive Intent Engine

PURPOSE:
    HMM-based intent inference with deterministic feature extraction.
    This module implements the core intent inference logic using HMM-like 
    probabilistic reasoning without requiring full ML training.

INPUTS:
    Window summaries from cognitive update stage.
    Aggregated canonical event features for intent analysis.

OUTPUTS:
    Intent inference results.
    Probabilistic intent state predictions with confidence scores.

IMPORTANT:
    This file must not implement logic from other stages.
    HMM inference algorithms and state transitions only.
"""

import math
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict, deque
import time

# Note: Kafka integration import should be updated when integration is needed
# from .kafka_integration import WindowSummary, ObservationVector, IntentBelief, IntentInferenceResult


# Intent states definition (MANDATORY)
INTENT_STATES = [
    "EXPLORE",
    "LEARN", 
    "COLLECT",
    "PREPARE",
    "EXFIL"
]

# Allowed transitions (forward-only, semi-monotonic)
ALLOWED_TRANSITIONS = {
    "EXPLORE": ["EXPLORE", "LEARN"],
    "LEARN": ["LEARN", "COLLECT"],
    "COLLECT": ["COLLECT", "PREPARE"],
    "PREPARE": ["PREPARE", "EXFIL"],
    "EXFIL": ["EXFIL"]  # Terminal state
}

# Feature weights (configurable)
WEIGHTS = {
    'novelty': 0.2,
    'sensitivity': 0.35,
    'effort': 0.25,
    'focus': 0.1,
    'entropy': 0.1
}


@dataclass
class UserIntentState:
    """Per-user intent state tracking."""
    user_id: str
    current_beliefs: IntentBelief
    previous_beliefs: Optional[IntentBelief]
    dominant_intent_history: deque
    last_update_time: float
    transition_velocity: float
    stability_score: float
    
    def __post_init__(self):
        if not hasattr(self, 'dominant_intent_history') or self.dominant_intent_history is None:
            self.dominant_intent_history = deque(maxlen=10)
        if self.last_update_time == 0:
            self.last_update_time = time.time()


class CognitiveFeatureExtractor:
    """Extracts cognitive features from window summaries."""
    
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or WEIGHTS
    
    def extract_features(self, window_summary: WindowSummary) -> ObservationVector:
        """
        Convert window summary into intent evidence features.
        
        Purely deterministic calculations - no ML yet.
        """
        metrics = window_summary.aggregated_metrics
        
        # Novelty score (inverted - low novelty means learning)
        novelty_score = 1.0 - metrics.get('avg_novelty', 0.5)
        
        # Sensitivity pressure (high avg sensitivity + upward trend)
        sensitivity_pressure = metrics.get('avg_sensitivity', 0.0)
        if metrics.get('sensitivity_trend') == '↑':
            sensitivity_pressure *= 1.2  # Boost for upward trend
        sensitivity_pressure = min(1.0, sensitivity_pressure)
        
        # Effort escalation (normalized escalation)
        effort_escalation = min(1.0, metrics.get('effort_escalation', 0.0) * 2)
        
        # Focus score (already normalized)
        focus_score = metrics.get('focus_score', 0.0)
        
        # Access entropy (normalized)
        access_entropy = min(1.0, metrics.get('access_entropy', 0.0) / 3.0)
        
        # Time compression (normalized - high compression = intense activity)
        time_compression = min(1.0, metrics.get('time_compression', 0.0) / 10.0)
        
        return ObservationVector(
            novelty_score=novelty_score,
            sensitivity_pressure=sensitivity_pressure,
            effort_escalation=effort_escalation,
            focus_score=focus_score,
            access_entropy=access_entropy,
            time_compression=time_compression
        )
    
    def apply_weights(self, features: ObservationVector) -> Dict[str, float]:
        """Apply configurable weights to features."""
        weighted_features = {
            'novelty': features.novelty_score * self.weights['novelty'],
            'sensitivity': features.sensitivity_pressure * self.weights['sensitivity'],
            'effort': features.effort_escalation * self.weights['effort'],
            'focus': features.focus_score * self.weights['focus'],
            'entropy': features.access_entropy * self.weights['entropy']
        }
        return weighted_features


class HMMIntentInference:
    """
    HMM-like probabilistic reasoning engine for intent inference.
    
    Maintains per-user intent belief: P(intent_state | history)
    Enforces allowed transitions only.
    """
    
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or WEIGHTS
        self.feature_extractor = CognitiveFeatureExtractor(weights)
        
        # Per-user state tracking
        self.user_states: Dict[str, UserIntentState] = {}
        
        # Emission likelihood parameters (heuristic)
        self.emission_params = self._initialize_emission_params()
        
        # Transition parameters
        self.transition_params = self._initialize_transition_params()
    
    def _initialize_emission_params(self) -> Dict[str, Dict[str, float]]:
        """
        Initialize heuristic emission likelihood parameters.
        
        Maps intent states to expected feature patterns.
        """
        return {
            "EXPLORE": {
                'novelty': 0.8,      # High novelty
                'sensitivity': 0.3,   # Low sensitivity
                'effort': 0.2,        # Low effort
                'focus': 0.3,         # Low focus (broad exploration)
                'entropy': 0.7         # High entropy (diverse access)
            },
            "LEARN": {
                'novelty': 0.4,       # Medium novelty (decreasing)
                'sensitivity': 0.5,    # Medium sensitivity
                'effort': 0.4,        # Medium effort
                'focus': 0.5,         # Medium focus
                'entropy': 0.5         # Medium entropy
            },
            "COLLECT": {
                'novelty': 0.2,       # Low novelty (repetition)
                'sensitivity': 0.7,    # High sensitivity
                'effort': 0.6,        # High effort
                'focus': 0.7,         # High focus
                'entropy': 0.3         # Low entropy (targeted access)
            },
            "PREPARE": {
                'novelty': 0.1,       # Very low novelty
                'sensitivity': 0.8,    # Very high sensitivity
                'effort': 0.8,        # Very high effort
                'focus': 0.9,         # Very high focus
                'entropy': 0.2         # Very low entropy
            },
            "EXFIL": {
                'novelty': 0.1,       # Very low novelty
                'sensitivity': 0.9,    # Maximum sensitivity
                'effort': 0.9,         # Maximum effort
                'focus': 1.0,          # Maximum focus
                'entropy': 0.1         # Minimum entropy
            }
        }
    
    def _initialize_transition_params(self) -> Dict[str, Dict[str, float]]:
        """
        Initialize transition parameters.
        
        Higher values for staying in same state, lower for progression.
        """
        return {
            "EXPLORE": {"EXPLORE": 0.7, "LEARN": 0.3},
            "LEARN": {"LEARN": 0.6, "COLLECT": 0.4},
            "COLLECT": {"COLLECT": 0.5, "PREPARE": 0.5},
            "PREPARE": {"PREPARE": 0.4, "EXFIL": 0.6},
            "EXFIL": {"EXFIL": 1.0}
        }
    
    def infer_intent(self, window_summary: WindowSummary) -> IntentInferenceResult:
        """
        Infer intent from window summary using HMM-like reasoning.
        
        Args:
            window_summary: Aggregated window metrics
            
        Returns:
            Intent inference result with probabilities and metadata
        """
        user_id = window_summary.user_id
        
        # Extract and weight features
        features = self.feature_extractor.extract_features(window_summary)
        weighted_features = self.feature_extractor.apply_weights(features)
        
        # Get or create user state
        user_state = self._get_or_create_user_state(user_id)
        
        # Calculate emission likelihoods
        emission_likelihoods = self._calculate_emission_likelihoods(weighted_features)
        
        # Update beliefs using HMM forward algorithm
        new_beliefs = self._update_beliefs(user_state.current_beliefs, emission_likelihoods)
        
        # Calculate transition velocity and stability
        transition_velocity = self._calculate_transition_velocity(user_state.current_beliefs, new_beliefs)
        stability_score = self._calculate_stability(user_state)
        
        # Update user state
        user_state.previous_beliefs = user_state.current_beliefs
        user_state.current_beliefs = new_beliefs
        user_state.last_update_time = time.time()
        user_state.transition_velocity = transition_velocity
        user_state.stability_score = stability_score
        
        # Track dominant intent history
        dominant_intent = new_beliefs.get_dominant_intent()
        user_state.dominant_intent_history.append(dominant_intent)
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(new_beliefs, stability_score)
        
        # Create result
        result = IntentInferenceResult(
            user_id=user_id,
            window={
                'window_start': window_summary.window_start,
                'window_end': window_summary.window_end
            },
            dominant_intent=dominant_intent,
            intent_probabilities=new_beliefs.to_dict(),
            transition_velocity=transition_velocity,
            confidence_score=confidence_score
        )
        
        return result
    
    def _get_or_create_user_state(self, user_id: str) -> UserIntentState:
        """Get existing user state or create new one."""
        if user_id not in self.user_states:
            # Initialize with uniform beliefs
            initial_beliefs = IntentBelief(
                explore_prob=0.8,    # Start with explore bias
                learn_prob=0.2,
                collect_prob=0.0,
                prepare_prob=0.0,
                exfil_prob=0.0
            )
            
            self.user_states[user_id] = UserIntentState(
                user_id=user_id,
                current_beliefs=initial_beliefs,
                previous_beliefs=None,
                dominant_intent_history=deque(maxlen=10),
                last_update_time=time.time(),
                transition_velocity=0.0,
                stability_score=0.0
            )
        
        return self.user_states[user_id]
    
    def _calculate_emission_likelihoods(self, weighted_features: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate emission likelihoods for each intent state.
        
        Uses Gaussian-like similarity between observed features and expected patterns.
        """
        likelihoods = {}
        
        for intent_state in INTENT_STATES:
            expected_params = self.emission_params[intent_state]
            
            # Calculate similarity as product of feature similarities
            similarity = 1.0
            for feature_name, observed_value in weighted_features.items():
                expected_value = expected_params[feature_name]
                
                # Gaussian-like similarity
                diff = abs(observed_value - expected_value)
                feature_similarity = math.exp(-diff * diff / 0.1)  # σ = 0.316
                similarity *= feature_similarity
            
            likelihoods[intent_state] = similarity
        
        # Normalize
        total = sum(likelihoods.values())
        if total > 0:
            likelihoods = {k: v/total for k, v in likelihoods.items()}
        
        return likelihoods
    
    def _update_beliefs(self, previous_beliefs: IntentBelief, 
                       emission_likelihoods: Dict[str, float]) -> IntentBelief:
        """
        Update beliefs using HMM forward algorithm.
        
        Enforces allowed transitions only.
        """
        # Get previous beliefs as dict
        prev_probs = {
            "EXPLORE": previous_beliefs.explore_prob,
            "LEARN": previous_beliefs.learn_prob,
            "COLLECT": previous_beliefs.collect_prob,
            "PREPARE": previous_beliefs.prepare_prob,
            "EXFIL": previous_beliefs.exfil_prob
        }
        
        # Calculate new beliefs
        new_probs = {}
        
        for current_state in INTENT_STATES:
            # Sum over all possible previous states
            probability = 0.0
            
            for prev_state in INTENT_STATES:
                if prev_state in ALLOWED_TRANSITIONS and current_state in ALLOWED_TRANSITIONS[prev_state]:
                    # Transition probability
                    trans_prob = self.transition_params[prev_state].get(current_state, 0.0)
                    
                    # Previous belief * transition * emission
                    prob = prev_probs[prev_state] * trans_prob * emission_likelihoods[current_state]
                    probability += prob
            
            new_probs[current_state] = probability
        
        # Normalize
        total = sum(new_probs.values())
        if total > 0:
            new_probs = {k: v/total for k, v in new_probs.items()}
        
        return IntentBelief(
            explore_prob=new_probs["EXPLORE"],
            learn_prob=new_probs["LEARN"],
            collect_prob=new_probs["COLLECT"],
            prepare_prob=new_probs["PREPARE"],
            exfil_prob=new_probs["EXFIL"]
        )
    
    def _calculate_transition_velocity(self, previous_beliefs: IntentBelief, 
                                   new_beliefs: IntentBelief) -> float:
        """
        Calculate velocity of intent change.
        
        Higher velocity = rapid intent progression.
        """
        prev_dict = previous_beliefs.to_dict() if previous_beliefs else {}
        new_dict = new_beliefs.to_dict()
        
        # Calculate L2 distance between belief vectors
        velocity = 0.0
        for state in INTENT_STATES:
            prev_val = prev_dict.get(f"{state.lower()}_prob", 0.0)
            new_val = new_dict.get(f"{state.lower()}_prob", 0.0)
            velocity += (new_val - prev_val) ** 2
        
        return math.sqrt(velocity)
    
    def _calculate_stability(self, user_state: UserIntentState) -> float:
        """
        Calculate stability of intent progression.
        
        Higher stability = consistent progression, lower = noisy changes.
        """
        if len(user_state.dominant_intent_history) < 3:
            return 0.0
        
        # Check for monotonic progression
        history = list(user_state.dominant_intent_history)
        state_order = {state: i for i, state in enumerate(INTENT_STATES)}
        
        monotonic_count = 0
        for i in range(1, len(history)):
            prev_order = state_order.get(history[i-1], -1)
            curr_order = state_order.get(history[i], -1)
            
            if prev_order <= curr_order:  # Forward or same
                monotonic_count += 1
        
        stability = monotonic_count / (len(history) - 1)
        return stability
    
    def _calculate_confidence_score(self, beliefs: IntentBelief, stability: float) -> float:
        """
        Calculate confidence in the inference.
        
        Higher confidence = clear dominant intent + stable progression.
        """
        # Get dominant probability
        probs = beliefs.to_dict()
        max_prob = max(probs.values())
        
        # Calculate entropy (lower entropy = higher confidence)
        entropy = -sum(p * math.log2(p) for p in probs.values() if p > 0)
        max_entropy = math.log2(len(INTENT_STATES))
        normalized_entropy = entropy / max_entropy
        
        # Combine factors
        confidence = max_prob * (1.0 - normalized_entropy) * (0.5 + 0.5 * stability)
        return confidence
    
    def get_user_state(self, user_id: str) -> Optional[UserIntentState]:
        """Get current intent state for a user."""
        return self.user_states.get(user_id)
    
    def reset_user_state(self, user_id: str):
        """Reset intent state for a user."""
        if user_id in self.user_states:
            del self.user_states[user_id]
