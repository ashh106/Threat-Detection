#!/usr/bin/env python3

"""
FILE: csv_to_kafka_streamer.py

STAGE:
    Stage-2 Canonicalization

PURPOSE:
    Stateless CSV data streaming into Kafka for canonicalization.
    This module reads CSV files containing security event data and streams
    them to the raw-metadata topic for downstream processing.

INPUTS:
    CSV files with security event data
    Files containing raw security logs and metadata

OUTPUTS:
    Kafka topic: raw-metadata
    Raw security events for canonicalization pipeline.

IMPORTANT:
    This file must not implement logic from other stages.
    Data loading and streaming only - no cognitive analysis.
"""

import csv
import json
import uuid
import time
import random
from datetime import datetime, timezone
from pathlib import Path
from kafka import KafkaProducer
from kafka.errors import KafkaError


# ---------------------------
# Utilities
# ---------------------------

def parse_event_time(value: str) -> str:
    """
    event_time in merged CSV is already ISO-8601.
    Preserve it. Do NOT overwrite with now().
    """
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc).isoformat()
    except Exception:
        return value


def jitter_delay(base=0.2, variance=0.15):
    """
    Human / enterprise-like jitter.
    """
    return max(0.01, random.uniform(base - variance, base + variance))


# ---------------------------
# Streamer
# ---------------------------

class MergedCSVToKafkaStreamer:
    def __init__(self):
        self.bootstrap_servers = "localhost:9092"
        self.topic = "raw-metadata"

        self.data_file = Path.home() / "Downloads" / "r3.1" / "merged_events.csv"

        # Replay behavior
        self.base_delay = 0.25        # average delay between events
        self.pause_every = 300        # short pause every N events
        self.pause_duration = (2, 5)  # seconds (min, max)

        self.producer = None
        self.sent_count = 0

    # ---------------------------
    # Kafka
    # ---------------------------

    def setup_kafka_producer(self):
        self.producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8"),
            acks="all",
            linger_ms=50,
            batch_size=32768,
            retries=5,
        )
        print("✓ Kafka producer ready")

    # ---------------------------
    # Event mapping
    # ---------------------------

    def build_raw_metadata_event(self, row):
        return {
            "event_id": str(uuid.uuid4()),
            "event_time": parse_event_time(row["event_time"]),
            "event_type": row["event_type"],
            "user": row["user"],
            "pc": row["pc"],
            "source_file": row["source_file"],
            "raw_payload": json.loads(row["raw_payload"]),
            "ingest_time": datetime.now(timezone.utc).isoformat(),
        }

    # ---------------------------
    # Streaming
    # ---------------------------

    def stream(self):
        if not self.data_file.exists():
            raise RuntimeError("merged_events.csv not found")

        self.setup_kafka_producer()

        print(f"✓ Streaming from {self.data_file.name}")
        print("✓ Replay mode: sequential, human-paced\n")

        with self.data_file.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                event = self.build_raw_metadata_event(row)

                try:
                    self.producer.send(
                        self.topic,
                        key=event["user"] or "unknown",
                        value=event,
                    )
                except KafkaError as e:
                    print(f"✗ Kafka error: {e}")
                    continue

                self.sent_count += 1

                if self.sent_count % 50 == 0:
                    print(f"  → Sent {self.sent_count} events")

                # Micro-pause to simulate real operation
                if self.sent_count % self.pause_every == 0:
                    pause = random.uniform(*self.pause_duration)
                    print(f"  ⏸ Short operational pause ({pause:.1f}s)")
                    time.sleep(pause)
                else:
                    time.sleep(jitter_delay(self.base_delay))

        self.producer.flush()
        print(f"\n✓ Replay complete — total events sent: {self.sent_count}")

    # ---------------------------
    # Cleanup
    # ---------------------------

    def close(self):
        if self.producer:
            self.producer.close()
            print("✓ Kafka producer closed")


# ---------------------------
# Entry point
# ---------------------------

def main():
    print("Merged CSV → Kafka Raw Metadata Replay")
    print("=" * 50)

    streamer = MergedCSVToKafkaStreamer()
    try:
        streamer.stream()
    except KeyboardInterrupt:
        print("\n⚠ Interrupted by user")
    except Exception as e:
        print(f"✗ Fatal error: {e}")
    finally:
        streamer.close()


if __name__ == "__main__":
    main()
