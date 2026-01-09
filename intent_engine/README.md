# Stage-3 Cognitive Intent Engine

Stateful cognitive analysis layer that infers user intent from canonical events using HMM-based probabilistic reasoning.

## Purpose

The cognitive intent engine provides:
- **Intent inference** using HMM-style phase tracking
- **State tracking** per user with EMA-based updates
- **Pattern recognition** for malicious progression
- **Explainable outputs** with confidence scores

## Components

### `state.py`
- Cognitive state vector representation
- User intent state tracking with EMA updates
- History and trajectory analysis

### `cognitive_update.py`
- EMA-based state update equations
- Intent calculation from cognitive factors
- Temporal smoothing and trend analysis

### `phase_hmm.py`
- HMM-style phase inference engine
- Forward-only state transitions
- Probabilistic reasoning with confidence scores

### `consumer.py`
- Pipeline orchestration and coordination
- Kafka integration for end-to-end flow
- Window aggregation and feature extraction

### `config.py`
- Configurable parameters and weights
- Threshold definitions
- System tuning options

### `state_store.py`
- Per-user state persistence
- Thread-safe state management
- History tracking and cleanup

## Data Flow

```
canonical-metadata → Window Aggregation → Feature Extraction → Phase Inference → cognitive-state
```

## Key Characteristics

- **Stateful**: Maintains user cognitive state over time
- **Probabilistic**: HMM-like reasoning with confidence
- **Temporal**: Intent evolution tracking and patterns
- **Explainable**: Clear probability distributions

## Integration Points

- **Input**: Canonical events from canonicalization stage
- **Output**: Cognitive state analysis for behavioral model
- **Configuration**: HMM parameters and feature weights

## Status

**Current Focus** - This stage contains the core cognitive intent inference logic and is ready for integration with canonicalization and behavioral model stages.
