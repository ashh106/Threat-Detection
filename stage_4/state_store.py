"""
FILE: state_store.py

STAGE:
    Stage-4 Behavioral Phase Inference

PURPOSE:
    Per-user state management for HMM inference.
    This module maintains observation buffers, phase histories,
    and handles user state expiry for inactive users.

INPUTS:
    New cognitive observations from Stage-3
    User activity timestamps

OUTPUTS:
    Per-user observation buffers
    Phase inference results
    User expiry management

STATE MANAGEMENT:
    Complete per-user separation
    Rolling observation windows
    Automatic cleanup of inactive users

NOTE: No cross-user data sharing - each user has isolated state.
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class UserState:
    """Per-user HMM inference state."""
    user_id: str
    observation_buffer: deque = field(default_factory=lambda: deque(maxlen=50))  # Rolling window
    last_seen_wall_clock: float = field(default_factory=time.time)  # Wall-clock time for expiry
    current_phase: str = "BENIGN_BASELINE"
    phase_history: deque = field(default_factory=lambda: deque(maxlen=20))
    inference_count: int = 0
    
    def add_observation(self, observation: np.ndarray, event_timestamp: float):
        """Add new observation to user's buffer."""
        self.observation_buffer.append(observation)
        self.last_seen_wall_clock = time.time()  # Use wall-clock time for expiry
    
    def get_observations(self) -> List[np.ndarray]:
        """Get observations as list."""
        return list(self.observation_buffer)
    
    def is_expired(self, timeout_seconds: int = 1800) -> bool:  # 30 minutes default
        """Check if user state has expired (no recent activity)."""
        return (time.time() - self.last_seen_wall_clock) > timeout_seconds
    
    def update_phase(self, phase: str, log_likelihood: float):
        """Update current phase and history."""
        self.current_phase = phase
        self.phase_history.append({
            'phase': phase,
            'timestamp': time.time(),
            'log_likelihood': log_likelihood
        })
        self.inference_count += 1


class PerUserStateStore:
    """
    Per-user state store with automatic expiry management.
    
    Maintains complete separation between users while providing
    efficient access and cleanup of inactive user states.
    """
    
    def __init__(self, user_timeout_seconds: int = 1800, cleanup_interval: int = 60):
        """
        Initialize state store.
        
        Args:
            user_timeout_seconds: Seconds of inactivity before expiry (default: 30 min)
            cleanup_interval: Seconds between cleanup runs (default: 60 sec)
        """
        self.users: Dict[str, UserState] = {}
        self.user_timeout_seconds = user_timeout_seconds
        self.cleanup_interval = cleanup_interval
        self.last_cleanup_time = time.time()
        
        logger.info(f"Initialized per-user state store with {user_timeout_seconds}s timeout, {cleanup_interval}s cleanup interval")
    
    def add_user_observation(self, user_id: str, observation: np.ndarray, 
                          timestamp: float) -> UserState:
        """
        Add observation for a user, creating state if needed.
        
        Args:
            user_id: User identifier
            observation: 8D cognitive observation vector
            timestamp: Observation timestamp
            
        Returns:
            UserState object for the user
        """
        if user_id not in self.users:
            self.users[user_id] = UserState(user_id=user_id)
            logger.debug(f"Created new state for user {user_id}")
        
        user_state = self.users[user_id]
        user_state.add_observation(observation, timestamp)
        
        return user_state
    
    def get_user_state(self, user_id: str) -> Optional[UserState]:
        """
        Get current state for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            UserState object or None if user doesn't exist
        """
        return self.users.get(user_id)
    
    def cleanup_expired_users(self) -> int:
        """
        Remove expired user states to prevent memory leaks.
        Runs only on cleanup interval to reduce log spam.
        
        Returns:
            Number of users cleaned up
        """
        current_time = time.time()
        
        # Check if cleanup interval has passed
        if current_time - self.last_cleanup_time < self.cleanup_interval:
            return 0
        
        expired_users = []
        
        for user_id, user_state in self.users.items():
            if user_state.is_expired(self.user_timeout_seconds):
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.users[user_id]
            logger.debug(f"Cleaned up expired user state: {user_id}")
        
        # Update cleanup time
        self.last_cleanup_time = current_time
        
        if expired_users:
            logger.info(f"Cleaned up {len(expired_users)} expired user states")
        
        return len(expired_users)
    
    def get_all_users(self) -> Dict[str, UserState]:
        """Get all active user states."""
        return self.users.copy()
    
    def get_user_count(self) -> int:
        """Get number of active users."""
        return len(self.users)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the state store."""
        phase_counts = {}
        total_observations = 0
        
        for user_state in self.users.values():
            # Count phases
            phase = user_state.current_phase
            phase_counts[phase] = phase_counts.get(phase, 0) + 1
            
            # Count observations
            total_observations += len(user_state.observation_buffer)
        
        return {
            'active_users': len(self.users),
            'total_observations': total_observations,
            'phase_distribution': phase_counts,
            'average_observations_per_user': total_observations / max(len(self.users), 1)
        }
