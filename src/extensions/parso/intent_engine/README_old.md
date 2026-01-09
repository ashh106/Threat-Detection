# Cognitive Intent Engine for Insider Threat Detection

A state-based cognitive intent estimation system that infers user intent over time from canonical security events by maintaining per-user latent state vectors.

## Overview

This system implements a sophisticated approach to insider threat detection that goes beyond simple anomaly scoring. It models how users become dangerous through cognitive state evolution rather than just detecting strange events.

## Core Concepts

### Cognitive State Vector

For each user, the system maintains a 7-dimensional cognitive state vector (all values normalized to [0,1]):

- **K(t)** - Knowledge of sensitive space
- **C(t)** - Capability to act  
- **I(t)** - Intent strength (latent, inferred)
- **U(t)** - Uncertainty
- **R(t)** - Risk tolerance
- **E(t)** - Effort invested
- **G(t)** - Goal proximity

### Key Principles

1. **Intent is Inferred, Not Observed**: Intent is calculated from other cognitive factors using the formula:
   ```
   I(t+1) = f(E(t), 1 − U(t), K(t), R(t)) × C(t) × behavioral_prior
   ```

2. **Temporal Evolution**: Intent emerges from trajectories, not single events. The system tracks patterns like:
   - K↑, U↓, E↑ → learning → planning
   - E↑ after failure → persistence
   - R↑ with G↑ → malicious confidence

3. **Behavioral Priors**: External behavioral signals are used as priors/gating, not as intent labels.

## Architecture

```
intent_engine/
├── main.py                 # Simulation and testing
├── canonical_consumer.py   # Event processing and alerting
├── state_store.py         # Per-user state management
├── cognitive_state.py     # Cognitive state representation
├── intent_update.py       # State update equations
├── behavioral_adapter.py # Behavioral signal integration
├── config.py             # Configuration parameters
└── ml/
    ├── hmm.py            # Hidden Markov Model (stub)
    └── weight_fit.py     # Weight optimization (stub)
```

## Usage

### Basic Simulation

```python
from intent_engine.main import IntentEngineSimulator

# Create and run simulation
simulator = IntentEngineSimulator()
simulator.run_simulation(duration_minutes=5, print_interval=5)
```

### Processing Events

```python
from intent_engine import IntentEngineConfig, StateStore, BehavioralAdapter, IntentUpdater, CanonicalConsumer

# Initialize components
config = IntentEngineConfig()
state_store = StateStore(config)
behavioral_adapter = BehavioralAdapter(config)
intent_updater = IntentUpdater(config, behavioral_adapter)
consumer = CanonicalConsumer(config, state_store, behavioral_adapter, intent_updater)

# Process an event
event = {
    'timestamp': time.time(),
    'user_id': 'user123',
    'action': 'access',
    'object_type': 'file',
    'domain': 'finance',
    'success': True,
    'sensitivity': 0.8,
    'novelty': 0.2,
    'risk_cost': 0.3,
    'effort_cost': 0.4,
    'source': 'system'
}

alert = consumer.process_event(event)
if alert:
    print(f"Alert: {alert.description}")
```

## Alert Logic

Alerts trigger only when:
```
I(t) × G(t) × C(t) > threshold
```

This ensures that high intent alone doesn't trigger alerts - there must be both goal proximity and capability.

## Simulation Results

The system was tested with three user types:

1. **Alice (Benign)**: Normal activity patterns, low intent scores
2. **Bob (Curious)**: Explores but doesn't act maliciously, moderate intent
3. **Charlie (Malicious)**: Builds intent over time, escalating from reconnaissance to execution

Results show the malicious user (Charlie) developing higher intent (0.465) and goal proximity (0.311) compared to benign users, while the system maintains low false positives for normal behavior.

## Key Features

- **EMA Smoothing**: All state updates use exponential moving averages for stability
- **Pattern Detection**: Identifies specific malicious trajectories (learning_planning, persistence_after_failure, etc.)
- **Configurable Thresholds**: All parameters and thresholds are configurable
- **ML Integration**: Stubs provided for HMM-based state estimation and weight optimization
- **Real-time Processing**: Asynchronous event processing with alert callbacks
- **State Persistence**: Optional disk-based state storage

## Configuration

Key configurable parameters include:

- EMA decay rates for each cognitive factor
- Update weights for different event characteristics
- Alert thresholds for intent, goal proximity, and combined risk
- Behavioral signal integration weights

## Future Extensions

The ML stubs can be replaced with full implementations for:

- **HMM State Estimation**: Use Viterbi algorithm for better state inference
- **Weight Optimization**: Gradient descent or genetic algorithms for parameter tuning
- **Behavioral Model Integration**: Real-time behavioral analysis integration

## Installation

```bash
cd intent_engine
python -m main  # Run simulation
```

The system requires only standard Python libraries (no external dependencies for core functionality).
