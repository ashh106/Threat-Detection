"""
FILE: phase_hmm.py

STAGE:
    Stage-3 Cognitive Intent Engine

PURPOSE:
    HMM-style phase inference with forward-only transitions.
    This module implements probabilistic phase tracking that enforces
    semi-monotonic intent progression without requiring full ML training.

INPUTS:
    Updated cognitive state from cognitive_update stage.
    Per-user cognitive state with applied EMA updates.

OUTPUTS:
    Phase probability vector for each user.
    Intent phase probabilities with confidence scores.

STATE MANAGEMENT:
    Per-user phase belief tracking with transition enforcement.
    Forward-only state progression (EXPLORE → LEARN → COLLECT → PREPARE → EXFIL).

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
class UserPhaseState:
    """Per-user phase state tracking."""
    user_id: str
    current_beliefs: 'PhaseBelief'
    previous_beliefs: Optional['PhaseBelief']
    dominant_phase_history: deque
    last_update_time: float
    transition_velocity: float
    stability_score: float
    
    def __post_init__(self):
        if not hasattr(self, 'dominant_phase_history') or self.dominant_phase_history is None:
            self.dominant_phase_history = deque(maxlen=10)
        if self.last_update_time == 0.0:
            self.last_update_time = time.time()


@dataclass
class PhaseBelief:
    """Phase belief probabilities."""
    explore_prob: float = 0.8    # Start with explore bias
    learn_prob: float = 0.2
    collect_prob: float = 0.0
    prepare_prob: float = 0.0
    exfil_prob: float = 0.0
    
    def get_dominant_phase(self) -> str:
        """Get phase with highest probability."""
        probs = {
            "EXPLORE": self.explore_prob,
            "LEARN": self.learn_prob,
            "COLLECT": self.collect_prob,
            "PREPARE": self.prepare_prob,
            "EXFIL": self.exfil_prob
        }
        return max(probs, key=probs.get)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'explore_prob': self.explore_prob,
            'learn_prob': self.learn_prob,
            'collect_prob': self.collect_prob,
            'prepare_prob': self.prepare_prob,
            'exfil_prob': self.exfil_prob
        }


class PhaseInference:
    """
    HMM-style phase inference engine with forward-only transitions.
    
    Maintains per-user phase belief: P(phase_state | history)
    Enforces allowed transitions only.
    """
    
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or WEIGHTS.copy()
        
        # Per-user phase state tracking
        self.user_states: Dict[str, UserPhaseState] = {}
        
        # Emission likelihood parameters (heuristic)
        self.emission_params = self._initialize_emission_params()
        
        # Transition parameters
        self.transition_params = self._initialize_transition_params()
    
    def _initialize_emission_params(self) -> Dict[str, Dict[str, float]]:
        """
        Initialize heuristic emission likelihood parameters.
        
        Maps intent phases to expected feature patterns.
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
                'focus': 1.0,         # Maximum focus
                'entropy': 0.1         # Minimum entropy
            }
        }
    
    def _initialize_transition_params(self) -> Dict[str, Dict[str, float]]:
        """
        Initialize transition parameters.
        
        Higher values for staying in same phase, lower for progression.
        """
        return {
            "EXPLORE": {"EXPLORE": 0.7, "LEARN": 0.3},
            "LEARN": {"LEARN": 0.6, "COLLECT": 0.4},
            "COLLECT": {"COLLECT": 0.5, "PREPARE": 0.5},
            "PREPARE": {"PREPARE": 0.4, "EXFIL": 0.6},
            "EXFIL": {"EXFIL": 1.0}
        }
    
    def infer_phase(self, user_id: str, cognitive_state) -> PhaseBelief:
        """
        Infer intent phase from cognitive state using HMM-like reasoning.
        
        Args:
            user_id: User identifier
            cognitive_state: Current cognitive state vector
            
        Returns:
            Updated phase belief probabilities
        """
        # Get or create user state
        user_state = self._get_or_create_user_state(user_id)
        
        # Calculate emission likelihoods based on cognitive state
        emission_likelihoods = self._calculate_emission_likelihoods(cognitive_state)
        
        # Update beliefs using HMM forward algorithm
        new_beliefs = self._update_beliefs(user_state.current_beliefs, emission_likelihoods)
        
        # Calculate transition velocity and stability
        transition_velocity = self._calculate_transition_velocity(
            user_state.current_beliefs, new_beliefs
        )
        stability_score = self._calculate_stability(user_state)
        
        # Update user state
        user_state.previous_beliefs = user_state.current_beliefs
        user_state.current_beliefs = new_beliefs
        user_state.last_update_time = time.time()
        user_state.transition_velocity = transition_velocity
        user_state.stability_score = stability_score
        
        # Track dominant phase history
        dominant_phase = new_beliefs.get_dominant_phase()
        user_state.dominant_phase_history.append(dominant_phase)
        
        return new_beliefs
    
    def _get_or_create_user_state(self, user_id: str) -> UserPhaseState:
        """Get existing user state or create new one."""
        if user_id not in self.user_states:
            # Initialize with explore bias
            initial_beliefs = PhaseBelief()
            self.user_states[user_id] = UserPhaseState(
                user_id=user_id,
                current_beliefs=initial_beliefs,
                previous_beliefs=None,
                dominant_phase_history=deque(maxlen=10),
                last_update_time=time.time(),
                transition_velocity=0.0,
                stability_score=0.0
            )
        
        return self.user_states[user_id]
    
    def _calculate_emission_likelihoods(self, cognitive_state) -> Dict[str, float]:
        """
        Calculate emission likelihoods for each intent phase.
        
        Uses Gaussian-like similarity between observed features and expected patterns.
        """
        likelihoods = {}
        
        # Extract features from cognitive state
        features = {
            'novelty': 1.0 - cognitive_state.uncertainty,  # Inverted uncertainty
            'sensitivity': cognitive_state.knowledge,          # Knowledge as proxy
            'effort': cognitive_state.effort,              # Direct effort
            'focus': 1.0 - cognitive_state.uncertainty,  # Low uncertainty = high focus
            'entropy': 1.0 - cognitive_state.knowledge   # High knowledge = low entropy
        }
        
        for phase in INTENT_STATES:
            expected_params = self.emission_params[phase]
            
            # Calculate similarity as product of feature similarities
            similarity = 1.0
            for feature_name, observed_value in features.items():
                expected_value = expected_params[feature_name]
                
                # Gaussian-like similarity
                diff = abs(observed_value - expected_value)
                feature_similarity = math.exp(-diff * diff / 0.1)  # σ = 0.316
                similarity *= feature_similarity
            
            likelihoods[phase] = similarity
        
        # Normalize
        total = sum(likelihoods.values())
        if total > 0:
            likelihoods = {k: v/total for k, v in likelihoods.items()}
        
        return likelihoods
    
    def _update_beliefs(self, previous_beliefs: PhaseBelief, 
                       emission_likelihoods: Dict[str, float]) -> PhaseBelief:
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
        
        for current_phase in INTENT_STATES:
            # Sum over all possible previous states
            probability = 0.0
            
            for prev_phase in INTENT_STATES:
                if prev_phase in ALLOWED_TRANSITIONS and current_phase in ALLOWED_TRANSITIONS[prev_phase]:
                    # Transition probability
                    trans_prob = self.transition_params[prev_phase].get(current_phase, 0.0)
                    
                    # Previous belief * transition * emission
                    prob = prev_probs[prev_phase] * trans_prob * emission_likelihoods[current_phase]
                    probability += prob
            
            new_probs[current_phase] = probability
        
        # Normalize
        total = sum(new_probs.values())
        if total > 0:
            new_probs = {k: v/total for k, v in new_probs.items()}
        
        return PhaseBelief(
            explore_prob=new_probs.get("EXPLORE", 0.0),
            learn_prob=new_probs.get("LEARN", 0.0),
            collect_prob=new_probs.get("COLLECT", 0.0),
            prepare_prob=new_probs.get("PREPARE", 0.0),
            exfil_prob=new_probs.get("EXFIL", 0.0)
        )
    
    def _calculate_transition_velocity(self, previous_beliefs: PhaseBelief, 
                                 new_beliefs: PhaseBelief) -> float:
        """
        Calculate velocity of phase change.
        
        Higher velocity = rapid phase progression.
        """
        prev_dict = previous_beliefs.to_dict()
        new_dict = new_beliefs.to_dict()
        
        # Calculate L2 distance between belief vectors
        velocity = 0.0
        for phase in INTENT_STATES:
            prev_val = prev_dict.get(f"{phase.lower()}_prob", 0.0)
            new_val = new_dict.get(f"{phase.lower()}_prob", 0.0)
            velocity += (new_val - prev_val) ** 2
        
        return math.sqrt(velocity)
    
    def _calculate_stability(self, user_state: UserPhaseState) -> float:
        """
        Calculate stability of phase progression.
        
        Higher stability = consistent progression, lower = noisy changes.
        """
        if len(user_state.dominant_phase_history) < 3:
            return 0.0
        
        # Check for monotonic progression
        history = list(user_state.dominant_phase_history)
        phase_order = {phase: i for i, phase in enumerate(INTENT_STATES)}
        
        monotonic_count = 0
        for i in range(1, len(history)):
            prev_phase = history[i-1]
            curr_phase = history[i]
            
            prev_order = phase_order.get(prev_phase, -1)
            curr_order = phase_order.get(curr_phase, -1)
            
            if prev_order <= curr_order:  # Forward or same
                monotonic_count += 1
        
        stability = monotonic_count / (len(history) - 1)
        return stability
    
    def get_user_state(self, user_id: str) -> Optional[UserPhaseState]:
        """Get current phase state for a user."""
        return self.user_states.get(user_id)
    
    def reset_user_state(self, user_id: str):
        """Reset phase state for a user."""
        if user_id in self.user_states:
            del self.user_states[user_id]
    
    def get_all_user_states(self) -> Dict[str, UserPhaseState]:
        """Get all user states."""
        return self.user_states.copy()
