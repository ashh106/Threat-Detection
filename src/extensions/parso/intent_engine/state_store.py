"""
State store for managing per-user cognitive states.

This module provides storage and retrieval of cognitive states
with support for persistence and cleanup.
"""

import time
import json
import threading
from typing import Dict, Any, Optional, List
from pathlib import Path

from .cognitive_state import CognitiveState
from .config import IntentEngineConfig


class StateStore:
    """
    Manages cognitive states for multiple users.
    
    Provides thread-safe access to per-user states with optional
    persistence to disk and automatic cleanup of expired states.
    """
    
    def __init__(self, config: IntentEngineConfig, persistence_path: Optional[str] = None):
        self.config = config
        self.persistence_path = persistence_path
        self._states: Dict[str, CognitiveState] = {}
        self._lock = threading.RLock()
        
        # Load existing states if persistence is enabled
        if self.persistence_path:
            self._load_states()
    
    def get_state(self, user_id: str) -> CognitiveState:
        """
        Get cognitive state for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            CognitiveState for the user (creates new if doesn't exist)
        """
        with self._lock:
            if user_id not in self._states:
                self._states[user_id] = CognitiveState(user_id=user_id)
            
            return self._states[user_id]
    
    def update_state(self, state: CognitiveState) -> CognitiveState:
        """
        Update cognitive state for a user.
        
        Args:
            state: Updated cognitive state
            
        Returns:
            The stored cognitive state
        """
        with self._lock:
            self._states[state.user_id] = state
            
            # Persist if enabled
            if self.persistence_path:
                self._save_state(state)
            
            return state
    
    def delete_state(self, user_id: str) -> bool:
        """
        Delete cognitive state for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if state was deleted, False if didn't exist
        """
        with self._lock:
            if user_id in self._states:
                del self._states[user_id]
                
                # Remove from persistence if enabled
                if self.persistence_path:
                    self._delete_persisted_state(user_id)
                
                return True
            
            return False
    
    def get_all_states(self) -> Dict[str, CognitiveState]:
        """
        Get all cognitive states.
        
        Returns:
            Dictionary mapping user_id to CognitiveState
        """
        with self._lock:
            return self._states.copy()
    
    def get_active_users(self, max_age_seconds: float = 3600) -> List[str]:
        """
        Get list of active users (recent activity).
        
        Args:
            max_age_seconds: Maximum age in seconds to consider active
            
        Returns:
            List of active user IDs
        """
        with self._lock:
            current_time = time.time()
            active_users = []
            
            for user_id, state in self._states.items():
                if current_time - state.last_updated <= max_age_seconds:
                    active_users.append(user_id)
            
            return active_users
    
    def cleanup_expired_states(self) -> int:
        """
        Remove expired states based on TTL.
        
        Returns:
            Number of states removed
        """
        with self._lock:
            current_time = time.time()
            expired_users = []
            
            for user_id, state in self._states.items():
                if current_time - state.last_updated > self.config.state_ttl_seconds:
                    expired_users.append(user_id)
            
            for user_id in expired_users:
                del self._states[user_id]
                
                # Remove from persistence if enabled
                if self.persistence_path:
                    self._delete_persisted_state(user_id)
            
            return len(expired_users)
    
    def get_high_risk_users(self, intent_threshold: float = 0.7, 
                          goal_threshold: float = 0.6) -> List[Dict[str, Any]]:
        """
        Get users with high intent and goal proximity.
        
        Args:
            intent_threshold: Minimum intent score
            goal_threshold: Minimum goal proximity score
            
        Returns:
            List of high-risk user information
        """
        with self._lock:
            high_risk_users = []
            
            for user_id, state in self._states.items():
                if state.intent >= intent_threshold and state.goal_proximity >= goal_threshold:
                    high_risk_users.append({
                        'user_id': user_id,
                        'intent': state.intent,
                        'goal_proximity': state.goal_proximity,
                        'capability': state.capability,
                        'risk_score': state.intent * state.goal_proximity * state.capability,
                        'last_updated': state.last_updated,
                        'event_count': state.event_count
                    })
            
            # Sort by risk score (descending)
            high_risk_users.sort(key=lambda x: x['risk_score'], reverse=True)
            
            return high_risk_users
    
    def get_user_trajectory(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get trajectory analysis for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Trajectory analysis or None if user doesn't exist
        """
        with self._lock:
            if user_id not in self._states:
                return None
            
            state = self._states[user_id]
            pattern = state.get_trajectory_pattern()
            
            return {
                'user_id': user_id,
                'current_state': state.to_dict(),
                'pattern': pattern,
                'event_count': state.event_count,
                'last_updated': state.last_updated
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored states.
        
        Returns:
            Dictionary with state statistics
        """
        with self._lock:
            total_users = len(self._states)
            active_users = len(self.get_active_users())
            
            if total_users == 0:
                return {
                    'total_users': 0,
                    'active_users': 0,
                    'avg_intent': 0.0,
                    'avg_goal_proximity': 0.0,
                    'high_risk_count': 0
                }
            
            # Calculate averages
            total_intent = sum(state.intent for state in self._states.values())
            total_goal_proximity = sum(state.goal_proximity for state in self._states.values())
            
            avg_intent = total_intent / total_users
            avg_goal_proximity = total_goal_proximity / total_users
            
            # Count high-risk users
            high_risk_count = len(self.get_high_risk_users())
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'avg_intent': avg_intent,
                'avg_goal_proximity': avg_goal_proximity,
                'high_risk_count': high_risk_count
            }
    
    def _load_states(self):
        """Load states from persistence file."""
        if not self.persistence_path:
            return
        
        try:
            persistence_file = Path(self.persistence_path)
            if not persistence_file.exists():
                return
            
            with open(persistence_file, 'r') as f:
                data = json.load(f)
            
            for user_id, state_data in data.items():
                state = CognitiveState.from_dict(state_data)
                self._states[user_id] = state
                
        except Exception as e:
            print(f"Warning: Failed to load states from {self.persistence_path}: {e}")
    
    def _save_state(self, state: CognitiveState):
        """Save a single state to persistence."""
        if not self.persistence_path:
            return
        
        try:
            persistence_file = Path(self.persistence_path)
            
            # Load existing data
            data = {}
            if persistence_file.exists():
                with open(persistence_file, 'r') as f:
                    data = json.load(f)
            
            # Update with new state
            data[state.user_id] = state.to_dict()
            
            # Save back
            with open(persistence_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"Warning: Failed to save state for {state.user_id}: {e}")
    
    def _delete_persisted_state(self, user_id: str):
        """Delete a state from persistence."""
        if not self.persistence_path:
            return
        
        try:
            persistence_file = Path(self.persistence_path)
            if not persistence_file.exists():
                return
            
            with open(persistence_file, 'r') as f:
                data = json.load(f)
            
            if user_id in data:
                del data[user_id]
                
                with open(persistence_file, 'w') as f:
                    json.dump(data, f, indent=2)
                    
        except Exception as e:
            print(f"Warning: Failed to delete persisted state for {user_id}: {e}")
    
    def export_states(self, output_path: str):
        """
        Export all states to a file.
        
        Args:
            output_path: Path to export file
        """
        with self._lock:
            data = {}
            for user_id, state in self._states.items():
                data[user_id] = state.to_dict()
            
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
    
    def import_states(self, input_path: str, merge: bool = True):
        """
        Import states from a file.
        
        Args:
            input_path: Path to import file
            merge: If True, merge with existing states; if False, replace all
        """
        with self._lock:
            with open(input_path, 'r') as f:
                data = json.load(f)
            
            if not merge:
                self._states.clear()
            
            for user_id, state_data in data.items():
                state = CognitiveState.from_dict(state_data)
                self._states[user_id] = state
