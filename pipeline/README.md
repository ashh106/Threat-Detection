# Pipeline Entry Point

Main orchestration and configuration for the entire insider threat detection pipeline.

## Purpose

The pipeline stage provides:
- **System entry point** for all pipeline stages
- **Configuration management** across components
- **Mode selection** (demo, simulation, production)
- **Monitoring** and statistics collection

## Components

### `main.py`
- Command line interface and argument parsing
- Pipeline configuration and initialization
- Mode-specific execution (demo/simulation/production)
- Error handling and logging

## Data Flow

```
CLI Arguments → Pipeline Configuration → Stage Orchestration → System Execution
```

## Key Characteristics

- **Orchestration**: Coordinates all pipeline stages
- **Configuration**: Centralized parameter management
- **Modes**: Multiple execution modes for different use cases
- **Monitoring**: System health and performance tracking

## Integration Points

- **Input**: Command line arguments and config files
- **Output**: Coordinated pipeline execution
- **Configuration**: All stage parameters and Kafka settings

## Usage Examples

```bash
# Demo mode with default settings
python -m pipeline.main --mode demo

# Simulation mode with custom parameters
python -m pipeline.main --mode simulation --duration 10 --events-per-minute 5

# Production mode with Kafka configuration
python -m pipeline.main --mode pipeline --kafka-servers localhost:9092
```
