import numpy as np
from src.data_loader import CERTDataLoader
from src.feature_engineering import BehavioralFeatureEngineer


def test_psychometric_columns_and_zscore():
    loader = CERTDataLoader("data/raw")
    df = loader.load_psychometric_data()

    # Ensure full trait names exist
    expected = [
        "openness",
        "conscientiousness",
        "extraversion",
        "agreeableness",
        "neuroticism",
    ]
    for col in expected:
        assert col in df.columns

    engineer = BehavioralFeatureEngineer("1D")
    psycho = engineer.engineer_psychometric_features(df)

    # Z-scored columns should be numeric and have mean approximately 0 and non-zero std
    for col in expected:
        assert col in psycho.columns
        vals = psycho[col].dropna().values
        assert vals.dtype.kind in "f"
        assert abs(np.mean(vals)) < 0.2  # reasonable tolerance for sample
        assert np.std(vals) > 0.0
