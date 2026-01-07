# Changelog

## [Unreleased] - 2026-01-06

### Fixed
- Normalize psychometric trait column names to full names (`openness`, `conscientiousness`, `extraversion`, `agreeableness`, `neuroticism`) in `src/data_loader.py` so downstream feature engineering doesn't raise KeyError. 🔧
- Implemented `RealTimeScorer` in `src/anomaly_scorer.py` and exposed `score_event` for simple real-time scoring use. 🔧
- Removed Unicode characters from log/print messages and made logging handlers UTF-8 aware to prevent Windows console encoding errors. 🔧

### Added
- Unit tests for psychometric normalization and real-time scorer (`tests/test_psychometric.py`, `tests/test_realtime_scorer.py`). ✅
- Notebook demo cell demonstrating psychometric columns and `RealTimeScorer` usage (`notebooks/01_getting_started.ipynb`). 📓

### Notes
- Training and inference completed successfully locally after fixes. If you use CI, consider adding the test run (`pytest`) to the pipeline.
