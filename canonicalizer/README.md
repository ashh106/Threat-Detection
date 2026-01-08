# Stage-2 Canonicalization

Stateless data processing layer that transforms raw security events into canonical format for downstream cognitive analysis.

## Purpose

The canonicalization stage provides:
- **Data standardization** across heterogeneous sources
- **Schema validation** and normalization
- **Kafka integration** for streaming pipeline
- **Stateless processing** (no cognitive logic)

## Components

### `canonical_conversion.py`
- Converts raw metadata to canonical format
- Handles schema validation and normalization
- Publishes to `canonical-metadata` topic

### `csv_to_kafka_streamer.py`
- Loads CSV data into Kafka pipeline
- Provides test data generation
- Streams to `raw-metadata` topic

### `kafka_integration.py`
- Kafka consumer/producer abstractions
- Data structure definitions
- Mock support for development

### `canonical_consumer.py`
- Canonical event consumer interface
- Event validation and basic filtering
- Feeds downstream cognitive engine

## Data Flow

```
Raw Sources → canonical-metadata → Cognitive Engine
```

## Key Characteristics

- **Stateless**: No user state maintained
- **Schema-driven**: Strict canonical format enforcement
- **High-throughput**: Optimized for streaming
- **Validation**: Data quality checks

## Integration Points

- **Input**: Raw security events from any source
- **Output**: Canonical events for intent engine
- **Configuration**: Kafka topics and schema definitions
