"""
Data Loader Module for CERT Insider Threat Dataset
(Email + Psychometric Data)

Author: Behavioral Analytics Team
"""

import pandas as pd
from pathlib import Path
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class CERTDataLoader:
    """
    Loads and preprocesses CERT Insider Threat dataset files.

    Supported sources:
    - email.csv
    - psychometric.csv
    """

    def __init__(self, raw_data_dir: str):
        self.raw_data_dir = Path(raw_data_dir)
        self.data: Dict[str, pd.DataFrame] = {}

        if not self.raw_data_dir.exists():
            raise FileNotFoundError(f"Raw data directory not found: {raw_data_dir}")

        logger.info(f"Initialized CERTDataLoader with raw_data_dir={raw_data_dir}")

    # ------------------------------------------------------------------
    # EMAIL DATA
    # ------------------------------------------------------------------
    def load_email_data(self, filename: str = "email.csv") -> pd.DataFrame:
        logger.info("Loading email data...")
        filepath = self.raw_data_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Email file not found: {filepath}")

        df = pd.read_csv(filepath)

        # Normalize column names
        df.columns = [c.strip().lower() for c in df.columns]

        # ---- USER COLUMN RESOLUTION ----
        if "user" not in df.columns:
            if "user_id" in df.columns:
                df.rename(columns={"user_id": "user"}, inplace=True)
            elif "employee_name" in df.columns:
                df.rename(columns={"employee_name": "user"}, inplace=True)
            else:
                raise KeyError(f"No user column found in email data: {df.columns.tolist()}")

        # ---- DATE COLUMN RESOLUTION ----
        if "date" not in df.columns:
            if "timestamp" in df.columns:
                df["date"] = pd.to_datetime(df["timestamp"], errors="coerce")
            else:
                raise KeyError(f"No date/timestamp column found: {df.columns.tolist()}")
        else:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

        df = df.dropna(subset=["user", "date"])

        # ---- RECIPIENT HANDLING ----
        if "to" in df.columns:
            df["to"] = df["to"].fillna("")
            df["recipient_count"] = df["to"].apply(
                lambda x: len([r for r in str(x).split(";") if r.strip()])
            )
        else:
            df["recipient_count"] = 0

        # ---- EXTERNAL RECIPIENT FLAG ----
        def _extract_domain(addr):
            if pd.isna(addr) or not addr:
                return ""
            s = str(addr)
            if "@" in s:
                return s.split("@")[-1].lower()
            return ""

        if "from" in df.columns:
            df["sender_domain"] = df["from"].apply(_extract_domain)
        else:
            df["sender_domain"] = ""

        def _has_external(row):
            sender = row["sender_domain"]
            for col in ("to", "cc", "bcc"):
                if col in row and pd.notna(row[col]) and row[col] != "":
                    recips = [r.strip() for r in str(row[col]).split(";") if r.strip()]
                    for r in recips:
                        if "@" in r:
                            rdom = r.split("@")[-1].lower()
                            if not sender or rdom != sender:
                                return 1
            return 0

        df["has_external_recipient"] = df.apply(_has_external, axis=1)

        # ---- SIZE HANDLING ----
        if "size" in df.columns:
            df["size"] = df["size"].fillna(0)
            df["size_kb"] = df["size"] / 1024
        else:
            df["size_kb"] = 0.0

        # ---- TIME FEATURES ----
        df["hour"] = df["date"].dt.hour
        df["day_of_week"] = df["date"].dt.dayofweek
        df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
        df["is_after_hours"] = ((df["hour"] < 6) | (df["hour"] >= 18)).astype(int)

        self.data["email"] = df
        logger.info(f"Loaded {len(df):,} email records")
        return df

    # ------------------------------------------------------------------
    # PSYCHOMETRIC DATA
    # ------------------------------------------------------------------
    def load_psychometric_data(self, filename: str = "psychometric.csv") -> pd.DataFrame:
        logger.info("Loading psychometric data...")
        filepath = self.raw_data_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Psychometric file not found: {filepath}")

        df = pd.read_csv(filepath)

        # Normalize column names
        df.columns = [c.strip().lower() for c in df.columns]

        # ---- USER COLUMN RESOLUTION ----
        if "user" not in df.columns:
            if "user_id" in df.columns:
                df.rename(columns={"user_id": "user"}, inplace=True)
            elif "employee_name" in df.columns:
                df.rename(columns={"employee_name": "user"}, inplace=True)
            else:
                raise KeyError(
                    f"No user identifier column found in psychometric data. "
                    f"Columns: {df.columns.tolist()}"
                )

        # ---- BIG FIVE TRAITS (normalize to full trait names expected downstream) ----
        trait_map = {
            "o": "openness",
            "c": "conscientiousness",
            "e": "extraversion",
            "a": "agreeableness",
            "n": "neuroticism",
            "openness": "openness",
            "conscientiousness": "conscientiousness",
            "extraversion": "extraversion",
            "agreeableness": "agreeableness",
            "neuroticism": "neuroticism",
        }

        # Rename any short or long form trait columns to the full trait names
        df.rename(columns={k: v for k, v in trait_map.items() if k in df.columns}, inplace=True)

        required_traits = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
        available_traits = [t for t in required_traits if t in df.columns]

        if not available_traits:
            raise KeyError(
                f"No Big Five traits found after normalization. Columns: {df.columns.tolist()}"
            )

        df = df.dropna(subset=["user"])

        self.data["psychometric"] = df
        logger.info(f"Loaded psychometric data for {len(df):,} users")
        return df

    # ------------------------------------------------------------------
    # LOAD ALL
    # ------------------------------------------------------------------
    def load_all(self) -> Dict[str, pd.DataFrame]:
        logger.info("Loading all available CERT data...")

        self.load_email_data()
        self.load_psychometric_data()

        return self.data

    # ------------------------------------------------------------------
    # SUMMARY HELPERS
    # ------------------------------------------------------------------
    def get_user_list(self):
        users = set()
        for df in self.data.values():
            if "user" in df.columns:
                users.update(df["user"].unique())
        return sorted(users)

    def get_date_range(self):
        dates = []
        if "email" in self.data:
            dates.extend(self.data["email"]["date"].dropna().tolist())
        return (min(dates), max(dates)) if dates else (None, None)

    def get_data_summary(self):
        rows = []
        for k, df in self.data.items():
            rows.append({
                "source": k,
                "rows": len(df),
                "columns": list(df.columns)
            })
        return pd.DataFrame(rows)
