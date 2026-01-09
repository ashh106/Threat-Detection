"""
FILE: inference.py

STAGE:
    Stage-4 Behavioral Phase Inference

PURPOSE:
    Online HMM inference for per-user behavioral phase detection.
    This module implements the core inference logic that processes
    cognitive observations and outputs phase probabilities.

INFERENCE DESIGN:
    - Online per-user HMM inference
    - Sliding window observation buffers
    - Viterbi for state sequences
    - Forward algorithm for probabilities
    - Conservative phase transitions

INPUTS:
    Cognitive observation vectors from Stage-3
    Per-user observation sequences from state store

OUTPUTS:
    Current phase probability distributions
    Most likely behavioral phases
    Log likelihoods for uncertainty estimation

NOTE: No ML training - only fixed-parameter HMM inference.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Any
import time
import logging

from .hmm_model import GaussianHMM
from .state_store import PerUserStateStore, UserState

logger = logging.getLogger(__name__)


class PhaseInference:
    """
    Online HMM-based phase inference engine.
    
    Processes per-user observation streams to infer behavioral phases
    using fixed-parameter Gaussian HMM with conservative transitions.
    """
    
    def __init__(self, user_timeout_seconds: int = 1800):
        """
        Initialize inference engine.
        
        Args:
            user_timeout_seconds: Seconds of inactivity before user expiry (default: 30 min)
        """
        self.hmm = GaussianHMM()
        self.state_store = PerUserStateStore(user_timeout_seconds)
        
        # Inference statistics
        self.total_inferences = 0
        self.start_time = time.time()
        
        logger.info("Initialized phase inference engine")
        logger.info(f"User timeout: {user_timeout_seconds} seconds")
    
    def process_observation(self, user_id: str, observation: List[float], 
                        timestamp: float) -> Optional[Dict[str, Any]]:
        """
        Process a single observation for a user.
        
        Args:
            user_id: User identifier
            observation: 8D cognitive observation vector [K, U, E, R, C, G, I, P]
            timestamp: Observation timestamp
            
        Returns:
            Inference result dict or None if insufficient data
        """
        # Convert to numpy array
        obs_array = np.array(observation, dtype=float)
        
        # Add to user state
        user_state = self.state_store.add_user_observation(user_id, obs_array, timestamp)
        
        # Need minimum observations for reliable inference
        if len(user_state.observation_buffer) < 3:
            logger.debug(f"User {user_id}: Insufficient observations ({len(user_state.observation_buffer)})")
            return None
        
        # Run HMM inference on user's observation sequence
        observations = user_state.get_observations()
        phase_probs, log_likelihood = self.hmm.infer_current_state(observations)
        
        # Get most likely phase
        current_phase = max(phase_probs, key=phase_probs.get)
        
        # Update user state
        user_state.update_phase(current_phase, log_likelihood)
        
        # Update statistics
        self.total_inferences += 1
        
        # Log inference result
        probs_str = ', '.join([f"{k}={v:.3f}" for k, v in phase_probs.items()])
        logger.info(f"User={user_id} | Phase={current_phase} | Probs=[{probs_str}] | LL={log_likelihood:.3f}")
        
        # Prepare output
        result = {
            "t": timestamp,
            "user": user_id,
            "state": current_phase,
            "state_probabilities": phase_probs,
            "log_likelihood": log_likelihood
        }
        
        return result
    
    def process_batch_observations(self, observations_batch: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process a batch of observations (for testing/catch-up).
        
        Args:
            observations_batch: List of observation messages from Stage-3
            
        Returns:
            List of inference results
        """
        results = []
        
        for obs_msg in observations_batch:
            user_id = obs_msg.get("user")
            observation = obs_msg.get("observation", [])
            timestamp = obs_msg.get("t", time.time())
            
            if not user_id or len(observation) != 8:
                logger.warning(f"Invalid observation message: {obs_msg}")
                continue
            
            result = self.process_observation(user_id, observation, timestamp)
            if result:
                results.append(result)
        
        return results
    
    def cleanup_expired_users(self) -> int:
        """
        Clean up expired user states.
        
        Returns:
            Number of users cleaned up
        """
        return self.state_store.cleanup_expired_users()
    
    def get_user_phase_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get phase history for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of history entries
            
        Returns:
            List of phase history entries
        """
        user_state = self.state_store.get_user_state(user_id)
        if not user_state:
            return []
        
        history = list(user_state.phase_history)
        return history[-limit:] if len(history) > limit else history
    
    def get_current_phases(self) -> Dict[str, str]:
        """
        Get current phase for all active users.
        
        Returns:
            Dictionary mapping user_id to current_phase
        """
        current_phases = {}
        
        for user_id, user_state in self.state_store.get_all_users().items():
            current_phases[user_id] = user_state.current_phase
        
        return current_phases
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get inference engine statistics.
        
        Returns:
            Statistics dictionary
        """
        runtime = time.time() - self.start_time
        store_stats = self.state_store.get_statistics()
        
        return {
            'runtime_seconds': runtime,
            'total_inferences': self.total_inferences,
            'inferences_per_second': self.total_inferences / max(runtime, 1),
            **store_stats
        }
