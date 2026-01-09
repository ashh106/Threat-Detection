"""Create minimal fixtures for unit tests.
Generates:
- data/raw/psychometric.csv
- models/distributions/baselines.pkl
"""
from pathlib import Path
import pandas as pd
from src.distribution_builder import DistributionBuilder

Path("data/raw").mkdir(parents=True, exist_ok=True)
Path("models/distributions").mkdir(parents=True, exist_ok=True)

# Create psychometric.csv
psy = pd.DataFrame({
    "user": ["user1", "user2"],
    "openness": [0.1, 0.2],
    "conscientiousness": [0.2, 0.3],
    "extraversion": [0.3, 0.4],
    "agreeableness": [0.4, 0.5],
    "neuroticism": [0.5, 0.6],
})
psy.to_csv("data/raw/psychometric.csv", index=False)

# Build minimal distributions
# Create a small behavioral DataFrame
import pandas as pd
import numpy as np

df = pd.DataFrame({
    "user": ["user1"] * 5 + ["user2"] * 5,
    "date": pd.to_datetime(["2020-01-01"] * 5 + ["2020-01-02"] * 5),
    "date_only": pd.to_datetime(["2020-01-01"] * 5 + ["2020-01-02"] * 5),
    "email_sent_count": [1, 2, 3, 4, 5, 2, 2, 3, 1, 0],
    "unique_recipients_count": [1, 0, 2, 1, 3, 1, 1, 0, 0, 1],
    "openness": [0.1, 0.2, 0.15, 0.18, 0.12, 0.2, 0.22, 0.19, 0.18, 0.17],
})

builder = DistributionBuilder(min_observations=1)
builder.build_personal_distributions(df)
# Also set a feature_list so RealTimeScorer has features
builder.feature_list = ["email_sent_count", "unique_recipients_count", "openness"]

builder.save("models/distributions/baselines.pkl")

print("Test fixtures created: data/raw/psychometric.csv, models/distributions/baselines.pkl")