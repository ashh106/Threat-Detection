"""
Feature Engineering Module for Behavioral Analytics
(Current: Email + Psychometric Data Only)

Raw logs → Aggregated features per (user, time_window)

Author: Behavioral Analytics Team
"""

import pandas as pd
import numpy as np
from typing import Dict
import logging

logger = logging.getLogger(__name__)


class BehavioralFeatureEngineer:
    """
    Engineers behavioral features from CERT email activity
    and psychometric traits.
    """

    def __init__(self, aggregation_window: str = "1D"):
        self.aggregation_window = aggregation_window
        logger.info(f"FeatureEngineer initialized (window={aggregation_window})")

    # ------------------------------------------------------------------
    # EMAIL FEATURES
    # ------------------------------------------------------------------
    def engineer_email_features(self, email_df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate email activity into behavioral features.

        Returns:
            DataFrame indexed by (user, date)
        """
        logger.info("Engineering email features...")

        df = email_df.copy()
        df["date_only"] = df["date"].dt.floor(self.aggregation_window)

        grouped = df.groupby(["user", "date_only"])

        features = {
            "email_sent_count": grouped.size(),
            "unique_recipients_count": grouped["recipient_count"].sum(),
            "external_recipient_ratio": grouped["has_external_recipient"].mean(),
            "after_hours_email_count": grouped["is_after_hours"].sum(),
            "avg_email_size_kb": grouped["size_kb"].mean(),
        }

        feature_df = pd.DataFrame(features).fillna(0)

        logger.info(
            f"Created {feature_df.shape[1]} email features for {len(feature_df):,} user-days"
        )
        return feature_df

    # ------------------------------------------------------------------
    # PSYCHOMETRIC FEATURES
    # ------------------------------------------------------------------
    def engineer_psychometric_features(self, psycho_df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare psychometric features (static per user).

        Returns:
            DataFrame indexed by user
        """
        logger.info("Processing psychometric features...")

        df = psycho_df.copy()

        traits = [
            "openness",
            "conscientiousness",
            "extraversion",
            "agreeableness",
            "neuroticism",
        ]

        # Z-score normalization
        for col in traits:
            df[col] = (df[col] - df[col].mean()) / df[col].std()

        df = df.set_index("user")[traits]

        logger.info(f"Prepared psychometric features for {len(df):,} users")
        return df

    # ------------------------------------------------------------------
    # UNIFIED FEATURE MATRIX
    # ------------------------------------------------------------------
    def create_unified_feature_matrix(
        self, data: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """
        Combine behavioral (email) and psychometric features.

        Returns:
            Unified DataFrame indexed by (user, date)
        """
        logger.info("Creating unified feature matrix...")

        if "email" not in data or data["email"].empty:
            raise ValueError("Email data is required for feature engineering")

        email_features = self.engineer_email_features(data["email"])
        unified = email_features.copy()

        # Join psychometric traits (static per user)
        if "psychometric" in data and not data["psychometric"].empty:
            psycho_features = self.engineer_psychometric_features(
                data["psychometric"]
            )
            unified = unified.join(psycho_features, on="user")

        unified = unified.reset_index()

        # Temporal context
        unified["day_of_week"] = unified["date_only"].dt.dayofweek
        unified["is_weekend"] = unified["day_of_week"].isin([5, 6]).astype(int)

        logger.info(
            f"Unified matrix shape: {unified.shape[0]:,} rows × {unified.shape[1]} features"
        )
        return unified

    # ------------------------------------------------------------------
    # ROLLING FEATURES
    # ------------------------------------------------------------------
    def add_rolling_features(self, feature_df: pd.DataFrame, window: int = 7) -> pd.DataFrame:
        """
        Add rolling mean/std features per user.

        Args:
            window: rolling window size (days)

        Returns:
            DataFrame with rolling features
        """
        logger.info(f"Adding {window}-day rolling features...")

        df = feature_df.sort_values(["user", "date_only"]).copy()

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        exclude = ["day_of_week", "is_weekend"]
        numeric_cols = [c for c in numeric_cols if c not in exclude]

        for col in numeric_cols:
            df[f"{col}_rolling_mean_{window}d"] = df.groupby("user")[col].transform(
                lambda x: x.rolling(window, min_periods=1).mean()
            )
            df[f"{col}_rolling_std_{window}d"] = df.groupby("user")[col].transform(
                lambda x: x.rolling(window, min_periods=1).std()
            )

        logger.info(f"Added {len(numeric_cols) * 2} rolling features")
        return df


# ------------------------------------------------------------------
# TEST RUN
# ------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    from src.data_loader import CERTDataLoader

    loader = CERTDataLoader("data/raw")
    data = loader.load_all()

    engineer = BehavioralFeatureEngineer(aggregation_window="1D")
    features = engineer.create_unified_feature_matrix(data)
    features = engineer.add_rolling_features(features, window=7)

    print("\nFEATURE MATRIX SUMMARY")
    print(features.head())
    print(f"\nTotal rows: {len(features):,}")
    print(f"Total features: {features.shape[1]}")

    features.to_csv("data/features/behavioral_features.csv", index=False)
    print("\nSaved → data/features/behavioral_features.csv")
