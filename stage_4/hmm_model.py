"""
FILE: hmm_model.py

STAGE:
    Stage-4 Behavioral Phase Inference

PURPOSE:
    Gaussian Hidden Markov Model for behavioral phase inference.
    This module implements the HMM with fixed parameters for inferring
    behavioral phases from cognitive observation vectors.

HMM DESIGN:
    - 5 hidden states: BENIGN_BASELINE, EXPLORATORY, RECON, PREPARATION, EXECUTION
    - 8-dimensional continuous observations: [K, U, E, R, C, G, I, P]
    - Gaussian emissions with diagonal covariance
    - Conservative transition matrix (no skipping, slow escalation)

INPUTS:
    Cognitive observation vectors from Stage-3
    Per-user observation sequences

OUTPUTS:
    Phase probability distributions
    Most likely current state
    Log likelihood of observations

NOTE: No ML training happens here - only fixed-parameter HMM inference.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class HMMParameters:
    """Fixed HMM parameters for behavioral phase inference."""
    
    # Hidden states (ordered)
    STATES = [
        "BENIGN_BASELINE",
        "EXPLORATORY", 
        "RECON",
        "PREPARATION",
        "EXECUTION"
    ]
    
    # Initial state probabilities (π)
    INITIAL_PROBS = np.array([0.90, 0.10, 0.00, 0.00, 0.00])
    
    # Transition matrix (A) - conservative escalation
    TRANSITION_MATRIX = np.array([
        [0.95, 0.05, 0.00, 0.00, 0.00],  # S0 → [S0, S1, S2, S3, S4]
        [0.10, 0.85, 0.05, 0.00, 0.00],  # S1 → 
        [0.05, 0.10, 0.80, 0.05, 0.00],  # S2 →
        [0.00, 0.05, 0.10, 0.80, 0.05],  # S3 →
        [0.00, 0.00, 0.05, 0.10, 0.85]   # S4 →
    ])
    
    # Emission parameters (μ) - initial alignment with observations
    EMISSION_MEANS = np.array([
        # S0 (BENIGN_BASELINE)
        [0.02, 0.90, 0.03, 0.00, 0.45, 0.00, 0.45, 0.02],
        
        # S1 (EXPLORATORY)  
        [0.06, 0.80, 0.07, 0.00, 0.47, 0.00, 0.47, 0.07],
        
        # S2 (RECON) - trend: K↑, U↓, E↑, C↑, I↑, P↑
        [0.15, 0.60, 0.15, 0.05, 0.55, 0.05, 0.55, 0.15],
        
        # S3 (PREPARATION) - U very low, G rising, P high
        [0.25, 0.40, 0.25, 0.10, 0.65, 0.10, 0.65, 0.25],
        
        # S4 (EXECUTION) - R high, G high, I high
        [0.35, 0.20, 0.35, 0.20, 0.75, 0.20, 0.75, 0.35]
    ])
    
    # Emission covariance - diagonal, small values
    EMISSION_COVARIANCE = np.diag([0.01, 0.02, 0.01, 0.01, 0.02, 0.01, 0.02, 0.01])
    
    @classmethod
    def get_state_index(cls, state: str) -> int:
        """Get index of state in the ordered list."""
        return cls.STATES.index(state)
    
    @classmethod
    def get_state_name(cls, index: int) -> str:
        """Get state name from index."""
        return cls.STATES[index]


class GaussianHMM:
    """
    Gaussian Hidden Markov Model with fixed parameters.
    
    Implements online HMM inference for per-user behavioral phase tracking.
    """
    
    def __init__(self):
        """Initialize HMM with fixed parameters."""
        self.params = HMMParameters()
        
        # Cache for Gaussian PDF calculations
        self._sqrt_det_cov = np.sqrt(np.linalg.det(self.params.EMISSION_COVARIANCE))
        self._inv_cov = np.linalg.inv(self.params.EMISSION_COVARIANCE)
        
        logger.info(f"Initialized Gaussian HMM with {len(self.params.STATES)} states")
        logger.info(f"Emission covariance diagonal: {np.diag(self.params.EMISSION_COVARIANCE)}")
    
    def _gaussian_log_pdf(self, observation: np.ndarray, mean: np.ndarray) -> float:
        """
        Compute log probability density of multivariate Gaussian.
        
        Args:
            observation: 8D observation vector [K, U, E, R, C, G, I, P]
            mean: 8D mean vector for current state
            
        Returns:
            Log probability density
        """
        diff = observation - mean
        exponent = -0.5 * diff.T @ self._inv_cov @ diff
        log_pdf = exponent - 0.5 * np.log(self._sqrt_det_cov) - 4.0 * np.log(2 * np.pi)
        
        return log_pdf
    
    def compute_emission_log_probs(self, observation: np.ndarray) -> np.ndarray:
        """
        Compute log emission probabilities for all states.
        
        Args:
            observation: Current observation vector
            
        Returns:
            Array of log probabilities for each state
        """
        log_probs = np.zeros(len(self.params.STATES))
        
        for i, state_mean in enumerate(self.params.EMISSION_MEANS):
            log_probs[i] = self._gaussian_log_pdf(observation, state_mean)
        
        return log_probs
    
    def viterbi_path(self, observations: List[np.ndarray]) -> Tuple[List[int], float]:
        """
        Compute most likely state sequence using Viterbi algorithm.
        
        Args:
            observations: Sequence of observation vectors
            
        Returns:
            Tuple of (state_sequence, log_likelihood)
        """
        if not observations:
            return [], float('-inf')
        
        n_states = len(self.params.STATES)
        n_obs = len(observations)
        
        # Initialize DP tables
        viterbi = np.zeros((n_obs, n_states))
        backpointer = np.zeros((n_obs, n_states), dtype=int)
        
        # Initialize with first observation
        emission_log_probs = self.compute_emission_log_probs(observations[0])
        viterbi[0] = np.log(self.params.INITIAL_PROBS) + emission_log_probs
        
        # Forward pass
        for t in range(1, n_obs):
            emission_log_probs = self.compute_emission_log_probs(observations[t])
            
            for s in range(n_states):
                # Find best previous state
                best_prev_log_prob = float('-inf')
                best_prev_state = 0
                
                for prev_s in range(n_states):
                    log_prob = (viterbi[t-1, prev_s] + 
                               np.log(self.params.TRANSITION_MATRIX[prev_s, s]))
                    if log_prob > best_prev_log_prob:
                        best_prev_log_prob = log_prob
                        best_prev_state = prev_s
                
                viterbi[t, s] = best_prev_log_prob + emission_log_probs[s]
                backpointer[t, s] = best_prev_state
        
        # Termination - find best final state
        best_final_log_prob = np.max(viterbi[-1])
        best_final_state = np.argmax(viterbi[-1])
        
        # Backtrace to get path
        path = [best_final_state]
        for t in range(n_obs - 1, 0, -1):
            path.append(backpointer[t, path[-1]])
        
        path.reverse()
        return path, best_final_log_prob
    
    def forward_probabilities(self, observations: List[np.ndarray]) -> Tuple[np.ndarray, float]:
        """
        Compute forward probabilities and total log likelihood.
        
        Args:
            observations: Sequence of observation vectors
            
        Returns:
            Tuple of (final_alpha, log_likelihood)
        """
        if not observations:
            return np.log(self.params.INITIAL_PROBS), float('-inf')
        
        n_states = len(self.params.STATES)
        alpha = np.zeros((len(observations), n_states))
        
        # Initialize
        emission_log_probs = self.compute_emission_log_probs(observations[0])
        alpha[0] = np.log(self.params.INITIAL_PROBS) + emission_log_probs
        
        # Forward pass
        for t in range(1, len(observations)):
            emission_log_probs = self.compute_emission_log_probs(observations[t])
            
            for s in range(n_states):
                # Sum over all possible previous states
                log_sum = float('-inf')
                for prev_s in range(n_states):
                    log_prob = (alpha[t-1, prev_s] + 
                               np.log(self.params.TRANSITION_MATRIX[prev_s, s]))
                    log_sum = np.logaddexp(log_sum, log_prob)
                
                alpha[t, s] = log_sum + emission_log_probs[s]
        
        # Total log likelihood
        log_likelihood = np.logaddexp.reduce(alpha[-1])
        
        return alpha[-1], log_likelihood
    
    def infer_current_state(self, observations: List[np.ndarray]) -> Dict[str, float]:
        """
        Infer current state distribution from observations.
        
        Args:
            observations: Sequence of observation vectors for a user
            
        Returns:
            Dictionary mapping state names to probabilities
        """
        if not observations:
            # Return initial probabilities
            return {
                state: prob for state, prob in zip(self.params.STATES, self.params.INITIAL_PROBS)
            }
        
        # Get final forward probabilities
        final_probs, log_likelihood = self.forward_probabilities(observations)
        
        # Normalize to get probability distribution
        exp_probs = np.exp(final_probs - np.max(final_probs))
        normalized_probs = exp_probs / np.sum(exp_probs)
        
        return {
            state: prob for state, prob in zip(self.params.STATES, normalized_probs)
        }, log_likelihood
