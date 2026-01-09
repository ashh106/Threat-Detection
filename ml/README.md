# Offline ML Training

Machine learning training and optimization modules for enhancing the cognitive intent engine.

## Purpose

The offline ML stage provides:
- **HMM training** for better state estimation
- **Weight optimization** for parameter tuning
- **Bayesian optimization** for model improvement
- **Model persistence** for production deployment

## Components

### `hmm.py`
- Hidden Markov Model training
- State estimation from historical data
- Viterbi and Baum-Welch algorithms

### `weight_fit.py`
- ML-based weight optimization
- Gradient descent and genetic algorithms
- Cross-validation and model selection

### `hmm_train.ipynb`
- Interactive HMM training notebook
- Data visualization and analysis
- Model evaluation and tuning

### `bayesian_weight_fit.ipynb`
- Bayesian optimization notebook
- Parameter uncertainty analysis
- Model comparison and selection

## Data Flow

```
Historical Data → ML Training → Optimized Models → Production Deployment
```

## Key Characteristics

- **Offline only**: No runtime imports allowed
- **Training-focused**: Model development and evaluation
- **Experimentation**: Interactive notebooks for research
- **Persistence**: Model saving and loading

## Integration Points

- **Input**: Historical cognitive state data
- **Output**: Trained models and optimized parameters
- **Deployment**: Model files for runtime integration

## Usage

These modules are **not imported by runtime code**. They are used for:
- Offline training on historical data
- Model experimentation and development
- Parameter optimization and tuning
- Production model deployment
