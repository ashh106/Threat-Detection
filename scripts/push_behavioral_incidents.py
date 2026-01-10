import os
import sys
import logging
from pathlib import Path

import pandas as pd
import requests


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Push high/critical behavioral alerts into the Flask backend Incident DB.

    Preferred CSV: results/high_priority_alerts.csv produced by inference.py
    Fallback CSV:  results/anomaly_scores.csv (filtered to HIGH/CRITICAL)
    Backend:       http://localhost:8000/api/incidents
    """
    repo_root = Path(__file__).resolve().parents[1]
    results_dir = repo_root / "results"

    primary_csv = results_dir / "high_priority_alerts.csv"
    fallback_csv = results_dir / "anomaly_scores.csv"

    use_severity_filter = False

    if primary_csv.exists():
        csv_path = primary_csv
        logger.info("Using %s as alerts source", csv_path)
    elif fallback_csv.exists():
        csv_path = fallback_csv
        use_severity_filter = True
        logger.info(
            "high_priority_alerts.csv not found; using %s and filtering to HIGH/CRITICAL",
            csv_path,
        )
    else:
        logger.error(
            "No alerts CSV found. Expected %s or %s. Run inference.py first.",
            primary_csv,
            fallback_csv,
        )
        sys.exit(1)

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        logger.exception("Failed to read %s: %s", csv_path, e)
        sys.exit(1)

    if use_severity_filter:
        if "severity" in df.columns:
            filtered = df[df["severity"].isin(["HIGH", "CRITICAL"])]
            if filtered.empty:
                if "anomaly_score" in df.columns:
                    # Fallback: use top-N highest anomaly scores for demo purposes
                    df = df.sort_values("anomaly_score", ascending=False).head(10)
                    logger.info(
                        "No HIGH/CRITICAL alerts found in %s after filtering; "
                        "using top %d rows by anomaly_score instead.",
                        csv_path,
                        len(df),
                    )
                else:
                    logger.info(
                        "No HIGH/CRITICAL alerts and no 'anomaly_score' column in %s; "
                        "nothing to push.",
                        csv_path,
                    )
                    return
            else:
                df = filtered
        else:
            logger.warning(
                "Fallback CSV %s has no 'severity' column; pushing all rows as incidents.",
                csv_path,
            )

    if df.empty:
        logger.info("No alerts found in %s", csv_path)
        return

    backend_url = os.environ.get("BACKEND_URL", "http://localhost:8000")
    endpoint = backend_url.rstrip("/") + "/api/incidents"

    created = 0
    for _, row in df.iterrows():
        user = row.get("user", "UNKNOWN")
        severity = row.get("severity", "UNKNOWN")
        score = float(row.get("anomaly_score", 0.0))

        # date column may be "date_only" or "date"
        date_val = row.get("date_only", row.get("date", ""))

        title = f"Behavioral Anomaly: {user} [{severity}]"
        details = (
            f"User={user}, Date={date_val}, "
            f"Score={score:.2f}, Severity={severity}"
        )

        payload = {
            "title": title,
            "details": details,
            "confidence": score,
        }

        try:
            r = requests.post(endpoint, json=payload, timeout=5)
            r.raise_for_status()
            created += 1
        except Exception as e:
            logger.warning("Failed to POST incident for user %s: %s", user, e)

    logger.info("Created %d incidents via %s", created, endpoint)


if __name__ == "__main__":
    main()
