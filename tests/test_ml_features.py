"""
tests/test_ml_features.py

Unit tests for feature engineering, leakage prevention, and target generation.
"""
import sys
from pathlib import Path

import pytest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ml.features.leakage_check import LEAKAGE_REGISTRY, is_feature_safe, validate_features
from src.ml.features.congestion_features import CONGESTION_FEATURE_COLS, build_congestion_features
from src.ml.features.travel_time_features import TRAVEL_TIME_FEATURE_COLS, build_travel_time_features


class TestLeakageCheck:
    def test_safe_features_are_identified(self):
        assert is_feature_safe("hour")
        assert is_feature_safe("lag1_congestion_pct")
        assert is_feature_safe("is_weekend")

    def test_target_leakage_features_are_identified(self):
        assert not is_feature_safe("congestion_pct")
        assert not is_feature_safe("congestion_band")
        assert not is_feature_safe("flow_passengers")

    def test_validate_features_passes_on_safe_cols(self):
        validate_features(CONGESTION_FEATURE_COLS)
        validate_features(TRAVEL_TIME_FEATURE_COLS)

    def test_validate_features_raises_on_leakage(self):
        bad_features = ["hour", "lag1_congestion_pct", "congestion_pct"]
        with pytest.raises(ValueError, match="TARGET LEAKAGE DETECTED"):
            validate_features(bad_features)


class TestCongestionFeatures:
    def test_build_congestion_features(self):
        df, line_enc, edge_enc = build_congestion_features()
        assert not df.empty
        for col in CONGESTION_FEATURE_COLS:
            assert col in df.columns, f"Missing feature column: {col}"
        assert "congestion_pct" in df.columns
        assert df["lag1_congestion_pct"].isna().sum() == 0


class TestTravelTimeFeatures:
    def test_build_travel_time_features(self):
        df, line_enc, edge_enc = build_travel_time_features()
        assert not df.empty
        for col in TRAVEL_TIME_FEATURE_COLS:
            assert col in df.columns, f"Missing travel time feature: {col}"
        assert "travel_time_min" in df.columns
        assert (df["travel_time_min"] > 0).all()
        assert "congestion_pct" not in TRAVEL_TIME_FEATURE_COLS
