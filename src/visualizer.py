"""
Visualization Module
(Aligned with Psychometric + Email Insider-Threat Pipeline)

Provides visual tools for:
1. Behavioral baseline understanding
2. Anomaly timelines
3. Severity distribution
4. User vs peer-cluster comparison

Author: Behavioral Analytics Team
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging
from typing import Optional
from datetime import datetime
from pathlib import Path

from distribution_builder import DistributionBuilder


logger = logging.getLogger(__name__)
plt.rcParams["figure.figsize"] = (12, 6)


class BehavioralVisualizer:
    """Visual analytics for behavioral anomaly detection."""

    def __init__(self, builder: DistributionBuilder):
        self.builder = builder
        logger.info("BehavioralVisualizer initialized")

    # ------------------------------------------------------------------
    # PERSONAL DISTRIBUTION SUMMARY
    # ------------------------------------------------------------------
    def plot_personal_distribution(
        self, user: str, feature: str, save_path: Optional[str] = None
    ):
        if user not in self.builder.personal:
            logger.warning(f"No personal baseline for {user}")
            return

        dist = self.builder.personal[user].get(feature)
        if not dist:
            logger.warning(f"No distribution for {feature}")
            return

        fig, ax = plt.subplots()

        # Gaussian visualization
        if dist.distribution_type == "gaussian":
            x = np.linspace(
                dist.percentile_values[5],
                dist.percentile_values[99],
                500,
            )
            y = (
                1
                / (dist.std * np.sqrt(2 * np.pi))
                * np.exp(-0.5 * ((x - dist.mean) / dist.std) ** 2)
            )
            ax.plot(x, y, label="Baseline (Gaussian)", linewidth=2)
            ax.axvline(dist.mean, linestyle="--", label="Mean")

        # Percentiles
        for p, v in dist.percentile_values.items():
            if p in [5, 50, 95]:
                ax.axvline(v, linestyle=":", label=f"{p}th percentile")

        ax.set_title(f"Personal Baseline: {user} – {feature}")
        ax.set_xlabel(feature)
        ax.set_ylabel("Density")
        ax.legend()
        ax.grid(alpha=0.3)

        self._save_or_show(save_path)
        plt.close()

    # ------------------------------------------------------------------
    # USER vs PEER CLUSTER
    # ------------------------------------------------------------------
    def plot_user_vs_peer_cluster(
        self,
        user: str,
        cluster: int,
        feature: str,
        save_path: Optional[str] = None,
    ):
        if user not in self.builder.personal:
            return
        if cluster not in self.builder.peer:
            return

        u_dist = self.builder.personal[user].get(feature)
        p_dist = self.builder.peer[cluster].get(feature)

        if not u_dist or not p_dist:
            return

        fig, ax = plt.subplots()

        ax.axvline(u_dist.mean, color="blue", label="User Mean", linewidth=2)
        ax.axvline(p_dist.mean, color="green", label="Peer Mean", linewidth=2)

        ax.axvspan(
            p_dist.mean - p_dist.std,
            p_dist.mean + p_dist.std,
            alpha=0.2,
            color="green",
            label="Peer ±1σ",
        )

        ax.set_title(f"User vs Peer Cluster – {feature}")
        ax.legend()
        ax.grid(alpha=0.3)

        self._save_or_show(save_path)
        plt.close()

    # ------------------------------------------------------------------
    # ANOMALY TIMELINE
    # ------------------------------------------------------------------
    def plot_anomaly_timeline(
        self,
        scored_df: pd.DataFrame,
        user: Optional[str] = None,
        save_path: Optional[str] = None,
    ):
        df = scored_df.copy()
        if user:
            df = df[df["user"] == user]
            title = f"Anomaly Timeline – {user}"
        else:
            title = "Anomaly Timeline (All Users)"

        if df.empty:
            return

        df = df.sort_values("date")

        fig, ax = plt.subplots()
        ax.plot(df["date"], df["anomaly_score"], marker="o", alpha=0.6)
        ax.axhline(0.7, color="red", linestyle="--", label="Alert Threshold")

        ax.set_title(title)
        ax.set_ylabel("Anomaly Score")
        ax.set_xlabel("Date")
        ax.legend()
        ax.grid(alpha=0.3)

        self._save_or_show(save_path)
        plt.close()

    # ------------------------------------------------------------------
    # SEVERITY DISTRIBUTION
    # ------------------------------------------------------------------
    def plot_severity_distribution(
        self, scored_df: pd.DataFrame, save_path: Optional[str] = None
    ):
        counts = scored_df["severity"].value_counts().sort_index()

        fig, ax = plt.subplots()
        counts.plot(kind="bar", ax=ax, color="tomato")

        ax.set_title("Anomaly Severity Distribution")
        ax.set_ylabel("Count")
        ax.grid(axis="y", alpha=0.3)

        self._save_or_show(save_path)
        plt.close()

    # ------------------------------------------------------------------
    # DASHBOARD
    # ------------------------------------------------------------------
    def create_dashboard(
        self, scored_df: pd.DataFrame, save_dir: str = "reports/dashboard"
    ):
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        self.plot_anomaly_timeline(
            scored_df, save_path=save_dir / "timeline.png"
        )
        self.plot_severity_distribution(
            scored_df, save_path=save_dir / "severity.png"
        )

        self._create_html_report(scored_df, save_dir)

        logger.info(f"Dashboard created → {save_dir}")

    # ------------------------------------------------------------------
    # HTML REPORT
    # ------------------------------------------------------------------
    def _create_html_report(self, df: pd.DataFrame, save_dir: Path):
        html = f"""
        <html>
        <head><title>Insider Threat Report</title></head>
        <body style="font-family:Arial">
        <h1>Insider Threat Detection Report</h1>
        <p>Generated: {datetime.now()}</p>

        <h3>Summary</h3>
        <ul>
          <li>Total observations: {len(df)}</li>
          <li>Anomalies detected: {(df['severity'] != 'NORMAL').sum()}</li>
          <li>Users analyzed: {df['user'].nunique()}</li>
        </ul>

        <h3>Anomaly Timeline</h3>
        <img src="timeline.png" width="800">

        <h3>Severity Distribution</h3>
        <img src="severity.png" width="600">
        </body>
        </html>
        """

        with open(save_dir / "report.html", "w") as f:
            f.write(html)

    @staticmethod
    def _save_or_show(save_path):
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
        else:
            plt.show()
