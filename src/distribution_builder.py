"""
Distribution Builder Module

Builds statistical behavioral baselines for insider-threat detection.
UNSUPERVISED – no labels, no ML training loops.

Baselines:
1. Personal (per user)
2. Peer (psychometric clusters)
3. Temporal (day-of-week)

Author: Behavioral Analytics Team
"""

import pandas as pd
import numpy as np
import pickle
import logging
from typing import Dict
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

EPSILON = 1e-6


# ============================================================
# SINGLE FEATURE DISTRIBUTION
# ============================================================

class BehavioralDistribution:
    """
    Stores statistical baseline for one behavioral feature.
    """

    def __init__(self, feature_name: str, values: np.ndarray):
        self.feature_name = feature_name
        self.values = values[~np.isnan(values)]
        self.n_samples = len(self.values)

        self.mean = float(np.mean(self.values))
        self.std = float(np.std(self.values)) if self.n_samples > 1 else EPSILON
        if self.std == 0:
            self.std = EPSILON

        self.percentiles = {
            p: float(np.percentile(self.values, p))
            for p in [5, 25, 50, 75, 95]
        }

    def score(self, value: float) -> Dict:
        """
        Score a value against this distribution.
        """
        z = (value - self.mean) / self.std
        percentile = np.mean(self.values <= value) * 100

        return {
            "z_score": float(z),
            "percentile": float(percentile)
        }


# ============================================================
# DISTRIBUTION BUILDER
# ============================================================

class DistributionBuilder:
    """
    Builds personal, peer, and temporal behavioral distributions.
    """

    def __init__(self, n_clusters: int = 5, min_observations: int = 10):
        self.n_clusters = n_clusters
        self.min_observations = min_observations

        self.personal_distributions: Dict[str, Dict[str, BehavioralDistribution]] = {}
        self.peer_distributions: Dict[int, Dict[str, BehavioralDistribution]] = {}
        self.temporal_distributions: Dict[int, Dict[str, BehavioralDistribution]] = {}

        self.user_to_cluster: Dict[str, int] = {}
        self.feature_list = []
        self.kmeans_model = None

    # --------------------------------------------------------
    # PERSONAL DISTRIBUTIONS
    # --------------------------------------------------------
    def build_personal_distributions(self, df: pd.DataFrame):
        logger.info("Building personal distributions...")

        feature_cols = [
            c for c in df.columns
            if c not in ["user", "date", "date_only", "day_of_week", "is_weekend"]
            and np.issubdtype(df[c].dtype, np.number)
        ]

        self.feature_list = feature_cols

        for user, user_df in df.groupby("user"):
            if len(user_df) < self.min_observations:
                continue

            self.personal_distributions[user] = {}

            for feature in feature_cols:
                values = user_df[feature].values
                if len(values) >= self.min_observations:
                    self.personal_distributions[user][feature] = BehavioralDistribution(
                        feature, values
                    )

        logger.info(f"Built personal baselines for {len(self.personal_distributions)} users")

    # --------------------------------------------------------
    # PEER DISTRIBUTIONS (Psychometric)
    # --------------------------------------------------------
    def build_peer_distributions(self, behavioral_df: pd.DataFrame, psychometric_df: pd.DataFrame):
        logger.info("Building peer distributions using psychometric clustering...")

        user_col = "user" if "user" in psychometric_df.columns else "user_id"
        # Accept either short codes (O,C,E,A,N) or full names (openness, conscientiousness, extraversion, agreeableness, neuroticism)
        possible_short = ["O", "C", "E", "A", "N"]
        possible_full = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]

        if all(c in psychometric_df.columns for c in possible_short):
            trait_cols = possible_short
        elif all(c in psychometric_df.columns for c in possible_full):
            trait_cols = possible_full
        else:
            # try to use any overlap
            trait_cols = [c for c in possible_short + possible_full if c in psychometric_df.columns]

        if not trait_cols:
            logger.warning("No psychometric traits found. Skipping peer distributions.")
            return

        cluster_df = psychometric_df[[user_col] + trait_cols].dropna()

        scaler = StandardScaler()
        X = scaler.fit_transform(cluster_df[trait_cols])

        self.kmeans_model = KMeans(
            n_clusters=min(self.n_clusters, len(cluster_df)),
            random_state=42,
            n_init=10
        )
        labels = self.kmeans_model.fit_predict(X)

        self.user_to_cluster = dict(zip(cluster_df[user_col], labels))

        behavioral_df = behavioral_df.copy()
        behavioral_df["cluster"] = behavioral_df["user"].map(self.user_to_cluster)
        behavioral_df.dropna(subset=["cluster"], inplace=True)

        for cluster_id, cluster_df in behavioral_df.groupby("cluster"):
            if len(cluster_df) < self.min_observations:
                continue

            self.peer_distributions[int(cluster_id)] = {}

            for feature in self.feature_list:
                values = cluster_df[feature].values
                if len(values) >= self.min_observations:
                    self.peer_distributions[int(cluster_id)][feature] = BehavioralDistribution(
                        feature, values
                    )

        logger.info(f"Built peer baselines for {len(self.peer_distributions)} clusters")

    # --------------------------------------------------------
    # TEMPORAL DISTRIBUTIONS (Day-of-week)
    # --------------------------------------------------------
    def build_temporal_distributions(self, df: pd.DataFrame):
        logger.info("Building temporal (day-of-week) distributions...")

        df = df.copy()
        if "day_of_week" not in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df["day_of_week"] = df["date"].dt.dayofweek

        for day, day_df in df.groupby("day_of_week"):
            if len(day_df) < self.min_observations:
                continue

            self.temporal_distributions[int(day)] = {}

            for feature in self.feature_list:
                values = day_df[feature].values
                if len(values) >= self.min_observations:
                    self.temporal_distributions[int(day)][feature] = BehavioralDistribution(
                        feature, values
                    )

        logger.info(f"Built temporal baselines for {len(self.temporal_distributions)} days")

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
