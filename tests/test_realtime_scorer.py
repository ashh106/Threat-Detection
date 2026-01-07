import pandas as pd
from src.distribution_builder import DistributionBuilder
from src.anomaly_scorer import RealTimeScorer


def test_realtime_scorer_smoke():
    builder = DistributionBuilder.load("models/distributions/baselines.pkl")
    rt = RealTimeScorer(builder)

    # Basic properties
    assert hasattr(rt, "alert_threshold")

    user = next(iter(builder.personal_distributions.keys()))
    event = {
        "user": user,
        "timestamp": pd.to_datetime("2020-01-01"),
        "features": {f: 0.0 for f in builder.feature_list},
    }

    res = rt.score_event(event)
    assert isinstance(res, dict)
    assert "anomaly_score" in res
    assert "severity" in res
    assert "alert" in res
