"""
Distribution Builder Module

Builds statistical baselines for behavioral anomaly detection.
This is UNSUPERVISED "training".

Author: Behavioral Analytics Team
"""

import pandas as pd
import numpy as np
import pickle
import logging
from typing import Dict

logger = logging.getLogger(__name__)


# ============================================================
# SINGLE FEATURE DISTRIBUTION
# ============================================================

class BehavioralDistribution:
    """
    Stores statistical baseline for one feature.
    """

    def __init__(self, feature_name: str, values: np.ndarray):
        self.feature_name = feature_name
        self.values = values[~np.isnan(values)]

        self.n_samples = len(self.values)

        self.mean = float(np.mean(self.values))
        self.std = float(np.std(self.values)) if self.n_samples > 1 else 0.0

        self.median = float(np.median(self.values))
        self.min_value = float(np.min(self.values))
        self.max_value = float(np.max(self.values))

        # Percentiles for temporal scoring
        self.percentiles = {
            p: float(np.percentile(self.values, p))
            for p in [5, 25, 50, 75, 95]
        }

    def score(self, value: float) -> Dict:
        """
        Score a value against this distribution.
        """
        if self.std == 0:
            z = 0.0
        else:
            z = (value - self.mean) / self.std

        percentile = sum(value > v for v in self.values) / len(self.values) * 100

        return {
            "z_score": float(z),
            "percentile": float(percentile)
        }


# ============================================================
# DISTRIBUTION BUILDER
# ============================================================

class DistributionBuilder:
    """
    Builds personal and temporal behavioral baselines.
    """

    def __init__(self, min_observations: int = 10):
        self.min_observations = min_observations

        self.personal_distributions: Dict[str, Dict[str, BehavioralDistribution]] = {}
        self.temporal_distributions: Dict[int, Dict[str, BehavioralDistribution]] = {}

        self.feature_list = []

    # --------------------------------------------------------
    # PERSONAL BASELINES
    # --------------------------------------------------------
    def build_personal_distributions(self, df: pd.DataFrame):
        logger.info("Building personal distributions...")

        feature_cols = [
            c for c in df.columns
            if c not in ["user", "date_only", "day_of_week", "is_weekend", "hour_of_day"]
            and np.issubdtype(df[c].dtype, np.number)
        ]

        self.feature_list = feature_cols

        for user, user_df in df.groupby("user"):
            self.personal_distributions[user] = {}

            for feature in feature_cols:
                values = user_df[feature].values

                if len(values) >= self.min_observations:
                    self.personal_distributions[user][feature] = BehavioralDistribution(
                        feature, values
                    )

        logger.info(f"✓ Built personal baselines for {len(self.personal_distributions)} users")
        return self.personal_distributions

    # --------------------------------------------------------
    # TEMPORAL BASELINES (hour-of-day)
    # --------------------------------------------------------
    def build_temporal_distributions(self, df: pd.DataFrame):
        logger.info("Building temporal distributions...")

        if "hour_of_day" not in df.columns:
            df = df.copy()
            df["hour_of_day"] = pd.to_datetime(df["date_only"]).dt.hour

        feature_cols = self.feature_list

        for hour, hour_df in df.groupby("hour_of_day"):
            self.temporal_distributions[hour] = {}

            for feature in feature_cols:
                values = hour_df[feature].values

                if len(values) >= self.min_observations:
                    self.temporal_distributions[hour][feature] = BehavioralDistribution(
                        feature, values
                    )

        logger.info(f"✓ Built temporal baselines for {len(self.temporal_distributions)} hours")
        return self.temporal_distributions

    # --------------------------------------------------------
    # SAVE / LOAD
    # --------------------------------------------------------
    def save(self, path: str):
        with open(path, "wb") as f:
            pickle.dump(self, f)
        logger.info(f"Saved distributions to {path}")

    @staticmethod
    def load(path: str):
        with open(path, "rb") as f:
            return pickle.load(f)
