"""
Anomaly Scoring Module
(Aligned with Psychometric + Email CERT Pipeline)

Scores observations against:
1. Personal baselines
2. Peer (psychometric cluster) baselines
3. Temporal (day-of-week) baselines

Author: Behavioral Analytics Team
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, Optional
from datetime import datetime

from src.distribution_builder import DistributionBuilder

logger = logging.getLogger(__name__)


class AnomalyScorer:
    """Scores behavioral observations against learned baselines."""

    def __init__(
        self,
        builder: DistributionBuilder,
        fusion_weights: Optional[Dict[str, float]] = None,
        alert_threshold: float = 0.7,
    ):
        self.builder = builder
        self.alert_threshold = alert_threshold

        if fusion_weights is None:
            fusion_weights = {
                "personal": 0.6,
                "peer": 0.25,
                "temporal": 0.15,
            }

        total = sum(fusion_weights.values())
        self.weights = {k: v / total for k, v in fusion_weights.items()}

        logger.info("AnomalyScorer initialized")

    # ------------------------------------------------------------------
    # CORE SCORING
    # ------------------------------------------------------------------
    def score_observation(
        self,
        user: str,
        timestamp: datetime,
        features: Dict[str, float],
        peer_cluster: Optional[int] = None,
    ) -> Dict:
        """Score a single (user, timestamp, feature-vector) observation."""

        dow = timestamp.weekday()

        personal = self._score_personal(user, features)
        peer = self._score_peer(peer_cluster, features)
        temporal = self._score_temporal(dow, features)

        feature_scores = {}
        flagged = []

        for feature, value in features.items():
            p = personal.get(feature, {})
            r = peer.get(feature, {})
            t = temporal.get(feature, {})

            p_norm = self._normalize_z(p.get("z_score"))
            r_norm = self._normalize_z(r.get("z_score"))
            t_norm = (t.get("percentile", 50) or 50) / 100.0

            score = (
                self.weights["personal"] * p_norm
                + self.weights["peer"] * r_norm
                + self.weights["temporal"] * t_norm
            )

            feature_scores[feature] = {
                "value": value,
                "score": score,
                "personal_z": p.get("z_score"),
                "peer_z": r.get("z_score"),
                "temporal_percentile": t.get("percentile"),
            }

            if score >= self.alert_threshold:
                flagged.append(feature)

        # Overall score = mean of top-k features
        if feature_scores:
            top_k = sorted(
                [v["score"] for v in feature_scores.values()],
                reverse=True
            )[: min(5, len(feature_scores))]
            overall = float(np.mean(top_k))
        else:
            overall = 0.0

        return {
            "user": user,
            "timestamp": timestamp,
            "anomaly_score": overall,
            "severity": self._severity(overall),
            "flagged_features": flagged,
            "feature_scores": feature_scores,
            "explanation": self._explain(flagged, feature_scores),
            "alert": overall >= self.alert_threshold,
        }

    # ------------------------------------------------------------------
    # BATCH SCORING
    # ------------------------------------------------------------------
    def score_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Score an entire feature dataframe."""

        logger.info(f"Scoring {len(df):,} observations...")
        results = []

        for _, row in df.iterrows():
            features = {
                f: row[f]
                for f in self.builder.feature_list
                if f in row
            }

            res = self.score_observation(
                user=row["user"],
                timestamp=row["date_only"],
                features=features,
                peer_cluster=row.get("cluster"),
            )

            results.append({
                "user": row["user"],
                "date": row["date_only"],
                "anomaly_score": res["anomaly_score"],
                "severity": res["severity"],
                "flagged_count": len(res["flagged_features"]),
                "top_feature": res["flagged_features"][0]
                if res["flagged_features"] else None,
                "explanation": res["explanation"],
            })

        return pd.DataFrame(results)

    # ------------------------------------------------------------------
    # BASELINE SCORING HELPERS
    # ------------------------------------------------------------------
    def _score_personal(self, user: str, features: Dict[str, float]) -> Dict:
        scores = {}
        dists = self.builder.personal_distributions.get(user, {})
        for f, v in features.items():
            if f in dists:
                scores[f] = dists[f].score(v)
        return scores

    def _score_peer(self, cluster: Optional[int], features: Dict[str, float]) -> Dict:
        if cluster is None:
            return {}
        dists = self.builder.peer_distributions.get(cluster, {})
        scores = {}
        for f, v in features.items():
            if f in dists:
                scores[f] = dists[f].score(v)
        return scores

    def _score_temporal(self, dow: int, features: Dict[str, float]) -> Dict:
        dists = self.builder.temporal_distributions.get(dow, {})
        scores = {}
        for f, v in features.items():
            if f in dists:
                scores[f] = dists[f].score(v)
        return scores

    # ------------------------------------------------------------------
    # UTILITIES
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_z(z: Optional[float]) -> float:
        if z is None:
            return 0.5
        return float(1 / (1 + np.exp(-z / 1.5)))

    @staticmethod
    def _severity(score: float) -> str:
        if score < 0.3:
            return "NORMAL"
        elif score < 0.5:
            return "LOW"
        elif score < 0.7:
            return "MEDIUM"
        elif score < 0.9:
            return "HIGH"
        else:
            return "CRITICAL"

    @staticmethod
    def _explain(flagged, feature_scores) -> str:
        if not flagged:
            return "No significant behavioral deviations detected."

        explanations = []
        for f in flagged[:3]:
            info = feature_scores[f]
            if info["personal_z"] is not None and abs(info["personal_z"]) > 3:
                explanations.append(
                    f"{f} deviates strongly from user's baseline "
                    f"({info['personal_z']:.1f}σ)"
                )
            elif (
                info["temporal_percentile"] is not None
                and info["temporal_percentile"] > 95
            ):
                explanations.append(
                    f"{f} is rare for this day "
                    f"({info['temporal_percentile']:.0f}th percentile)"
                )

        return "; ".join(explanations)


# ------------------------------------------------------------------
# TEST RUN
# ------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    builder = DistributionBuilder.load(
        "models/distributions/baseline_distributions.pkl"
    )

    df = pd.read_csv("data/features/behavioral_features.csv")
    df["date_only"] = pd.to_datetime(df["date_only"])

    scorer = AnomalyScorer(builder)
    results = scorer.score_dataframe(df.head(200))

    print("\nANOMALY SUMMARY")
    print(results["severity"].value_counts())

    results.to_csv("data/results/anomaly_scores.csv", index=False)
    print("Saved → data/results/anomaly_scores.csv")
