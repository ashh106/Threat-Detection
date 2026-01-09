# Stage-4 Behavioral Phase Inference

## Overview

Stage-4 implements a Gaussian Hidden Markov Model (HMM) for behavioral phase inference from cognitive observations produced by Stage-3.

## Architecture

```
Stage-3 (cognitive observations) → stage_3 topic → Stage-4 HMM inference → behavioral_phase topic → Stage-5
```

## Components

### Core Modules

- **hmm_model.py**: Fixed-parameter Gaussian HMM with 5 behavioral phases
- **state_store.py**: Per-user observation buffers and state management
- **inference.py**: Online HMM inference engine
- **consumer.py**: Kafka consumer for Stage-3 observations
- **producer.py**: Kafka producer for phase inference results
- **main.py**: Entry point and orchestration

### Behavioral Phases

1. **BENIGN_BASELINE** (S0): Normal activity, low risk
2. **EXPLORATORY** (S1): Information gathering, moderate novelty
3. **RECON** (S2): Data collection, escalating effort
4. **PREPARATION** (S3): Planning for execution, high focus
5. **EXECUTION** (S4): Active malicious behavior, high risk

## HMM Parameters

### Initial State Distribution
- BENIGN_BASELINE: 90%
- EXPLORATORY: 10%
- RECON: 0%
- PREPARATION: 0%
- EXECUTION: 0%

### Transition Matrix
Conservative escalation with no skipping states:
- High probability of staying in same state
- Low probability of escalation
- No direct jumps to EXECUTION

### Emission Parameters
Gaussian distributions aligned with cognitive patterns:
- **S0**: Low K/E/R, high U, low P
- **S1**: Moderate K/E, high U, low P
- **S2**: Increasing K/E/C/I/P, decreasing U
- **S3**: Low U, high G/P, moderate-high K/E/R
- **S4**: High K/E/R/C/I/P, very low U

## Key Features

### Per-User Separation
- Complete isolation of user observation streams
- Independent HMM inference per user
- No cross-user data contamination

### Online Inference
- Sliding window observation buffers (max 50 observations)
- Real-time Viterbi and forward algorithm updates
- Automatic user expiry after 1 hour inactivity

### Conservative Design
- Fixed parameters (no automatic training)
- Slow phase transitions
- Minimum 3 observations before inference
- Gaussian emissions with small variance

## Usage

```bash
# Activate Kafka environment
source ~/venvs/kafka-env/bin/activate

# Run Stage-4 HMM inference
cd /home/parth/projects/Insider_threat
python -m stage_4.main --mode hmm

# Custom parameters
python -m stage_4.main \
  --kafka-servers 127.0.0.1:9092 \
  --input-topic stage_3 \
  --output-topic behavioral_phase \
  --user-timeout 3600
```

## Input Schema (stage_3 topic)

```json
{
  "t": 1736228459.076,
  "user": "TDF0088",
  "observation": [0.42, 0.61, 0.19, 0.34, 0.28, 0.00, 0.31, 0.48],
  "features": ["K", "U", "E", "R", "C", "G", "I", "P"]
}
```

## Output Schema (behavioral_phase topic)

```json
{
  "t": 1736228459.076,
  "user": "TDF0088",
  "state": "EXPLORATORY",
  "state_probabilities": {
    "BENIGN_BASELINE": 0.05,
    "EXPLORATORY": 0.82,
    "RECON": 0.10,
    "PREPARATION": 0.02,
    "EXECUTION": 0.01
  },
  "log_likelihood": -12.34
}
```

## Logging

Per-inference logging:
```
User=TDF0088 | Phase=EXPLORATORY | Probs=[BENIGN_BASELINE=0.050, EXPLORATORY=0.820, RECON=0.100, PREPARATION=0.020, EXECUTION=0.010] | LL=-12.34
```

Periodic statistics:
```
Statistics: 1247 messages processed, 45 active users, 1247 total inferences
Inference rate: 0.832 inferences/second
```

## Constraints

- No ML training or parameter updates
- No alerting or intent scoring
- No modification of cognitive math
- Complete per-user separation
- Conservative phase transitions
- Fixed Gaussian emission parameters
