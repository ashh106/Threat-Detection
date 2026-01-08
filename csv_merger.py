#!/usr/bin/env python3

import csv
import json
import subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path.home() / "Downloads" / "r3.1"
TMP_FILE = BASE_DIR / "merged_unsorted.csv"
OUTPUT_FILE = BASE_DIR / "merged_events.csv"

EVENT_TYPE_MAP = {
    "logon.csv": "LOGON",
    "device.csv": "DEVICE",
    "http.csv": "HTTP",
    "email.csv": "EMAIL",
    "file.csv": "FILE"
}

FIELDNAMES = [
    "event_time",
    "event_type",
    "source_file",
    "user",
    "pc",
    "raw_payload"
]


def parse_time(value: str) -> str:
    # CERT r3 format: DD/MM/YYYY HH:MM:SS
    dt = datetime.strptime(value.strip(), "%d/%m/%Y %H:%M:%S")
    return dt.isoformat()


def stream_merge_csvs():
    print("[*] Streaming CSVs into unsorted merged file (memory-safe)...")

    with open(TMP_FILE, "w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=FIELDNAMES)
        writer.writeheader()

        for csv_name, event_type in EVENT_TYPE_MAP.items():
            file_path = BASE_DIR / csv_name
            if not file_path.exists():
                print(f"[WARN] Missing {csv_name}, skipping")
                continue

            print(f"    → Processing {csv_name}")

            with open(file_path, newline="", encoding="utf-8") as in_f:
                reader = csv.DictReader(in_f)
                for row in reader:
                    if "date" not in row:
                        continue

                    try:
                        event_time = parse_time(row["date"])
                    except Exception:
                        continue

                    writer.writerow({
                        "event_time": event_time,
                        "event_type": event_type,
                        "source_file": csv_name,
                        "user": row.get("user") or row.get("from") or "",
                        "pc": row.get("pc", ""),
                        "raw_payload": json.dumps(row, separators=(",", ":"))
                    })


def external_sort():
    print("[*] Sorting merged file by event_time using disk-based sort...")

    # sort by first column (event_time), keep header
    cmd = f"""
    (head -n 1 "{TMP_FILE}" && tail -n +2 "{TMP_FILE}" | sort -t, -k1,1) > "{OUTPUT_FILE}"
    """

    subprocess.run(cmd, shell=True, check=True)

    print("[OK] Sorting complete")


def main():
    stream_merge_csvs()
    external_sort()

    print(f"[DONE] Final merged CSV written to: {OUTPUT_FILE}")
    print("[INFO] You can now safely delete merged_unsorted.csv if desired")


if __name__ == "__main__":
    main()
