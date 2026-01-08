#!/usr/bin/env python3
"""
FILE: canonical_conversion.py

STAGE:
    Stage-2 Canonicalization

PURPOSE:
    Stateless conversion of raw security metadata into canonical format.
    Produces weak but structured cognitive priors for downstream intent inference.

INPUT:
    Kafka topic: raw-metadata

OUTPUT:
    Kafka topic: canonical-metadata

IMPORTANT GUARANTEES:
    - Stateless (no memory, no history)
    - Deterministic (same input → same output)
    - No ML, no aggregation
    - Safe priors only (never strong conclusions)
"""

import json
import time
from datetime import datetime, timezone
from kafka import KafkaConsumer, KafkaProducer


# -------------------------------------------------
# Kafka Configuration
# -------------------------------------------------

BOOTSTRAP_SERVERS = "localhost:9092"
RAW_TOPIC = "raw-metadata"
CANONICAL_TOPIC = "canonical-metadata"
GROUP_ID = "canonicalizer-group"


# -------------------------------------------------
# Utilities
# -------------------------------------------------

def iso_to_epoch(ts):
    try:
        return int(
            datetime.fromisoformat(ts.replace("Z", "+00:00"))
            .astimezone(timezone.utc)
            .timestamp()
        )
    except Exception:
        return int(time.time())


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


# -------------------------------------------------
# Canonicalization (STATELESS + SAFE PRIORS)
# -------------------------------------------------

def canonicalize(raw):
    """
    Convert a raw metadata event into canonical form.

    This function:
    - uses ONLY fields present in the raw event
    - assigns weak cognitive priors
    - never uses history or learned values
    """

    user = raw.get("user")
    if not user:
        return None

    action = raw.get("event_type")
    source = raw.get("source_file")
    pc = raw.get("pc")
    payload = raw.get("raw_payload", {})

    # -------------------------
    # Success (binary where possible)
    # -------------------------
    if action == "LOGON":
        success = True
    else:
        success = None

    # -------------------------
    # Sensitivity (surface-based)
    # -------------------------
    if action == "LOGON":
        sensitivity = 0.2

    elif action == "HTTP":
        url = payload.get("url", "").lower()
        if any(k in url for k in ["google", "youtube", "wikipedia"]):
            sensitivity = 0.25
        else:
            sensitivity = 0.4

    else:
        sensitivity = 0.3

    # -------------------------
    # Effort cost (intentionality proxy)
    # -------------------------
    if action == "LOGON":
        effort_cost = 0.1
    elif action == "HTTP":
        effort_cost = 0.15
    else:
        effort_cost = 0.2

    # -------------------------
    # Novelty (neutral prior ONLY)
    # -------------------------
    novelty = 0.5

    # -------------------------
    # Risk cost (derived, not arbitrary)
    # -------------------------
    risk_cost = clamp(0.6 * sensitivity + 0.4 * effort_cost)

    # -------------------------
    # Confidence (data quality)
    # -------------------------
    if success is True:
        confidence = 0.9
    elif success is False:
        confidence = 0.7
    else:
        confidence = 0.6

    # -------------------------
    # Canonical Event
    # -------------------------
    return {
        "t": iso_to_epoch(raw.get("event_time")),
        "user": user,
        "action": action,
        "object_type": action,
        "object_id": pc,
        "success": success,
        "source": source,
        "raw_event_id": raw.get("event_id"),

        # ---- Cognitive priors (weak, stateless) ----
        "sensitivity": sensitivity,
        "effort_cost": effort_cost,
        "risk_cost": risk_cost,
        "novelty": novelty,
        "confidence": confidence,
    }


# -------------------------------------------------
# Kafka Pipeline
# -------------------------------------------------

def main():
    consumer = KafkaConsumer(
        RAW_TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_deserializer=lambda v: json.loads(v.decode()),
        group_id=GROUP_ID,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        max_poll_records=500,
    )

    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode(),
        linger_ms=10,
        batch_size=65536,
    )

    print("Stage-2 Canonicalizer started.")
    print("Processing existing data and waiting for new events...")

    processed = 0
    last_report = time.time()

    try:
        for msg in consumer:
            canonical_event = canonicalize(msg.value)

            if canonical_event:
                producer.send(CANONICAL_TOPIC, canonical_event)
                processed += 1

            if time.time() - last_report > 10:
                print(f"Canonicalizer running | Events processed: {processed}")
                last_report = time.time()

    except KeyboardInterrupt:
        print("\nShutdown requested.")

    finally:
        producer.flush()
        print(f"Canonicalizer stopped | Total events processed: {processed}")


if __name__ == "__main__":
    main()
