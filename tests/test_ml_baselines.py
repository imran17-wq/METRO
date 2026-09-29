"""
tests/test_ml_baselines.py

Unit tests for baseline models (Historical Mean and Scheduled Travel Time).
"""
import sys
from pathlib import Path

import pytest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ml.evaluation.baselines import CongestionHistoricalBaseline, TravelTimeScheduledBaseline, evaluate_baseline
from src.ml.evaluation.splits import chronological_split
from src.ml.features.congestion_features import load_raw_edge_data, build_congestion_features
from src.ml.features.travel_time_features import build_travel_time_features


class TestBaselines:
    def test_congestion_historical_baseline(self):
        raw_df = load_raw_edge_data()
        processed_df, _, _ = build_congestion_features(raw_df)
        train_df, val_df, test_df, _ = chronological_split(processed_df)

        baseline = CongestionHistoricalBaseline()
        baseline.fit(train_df)
        preds = baseline.predict(test_df)

        assert len(preds) == len(test_df)
        assert np.all(preds > 0)

        metrics = evaluate_baseline(baseline, test_df, "congestion_pct")
        assert "mae" in metrics
        assert "rmse" in metrics
        assert metrics["mae"] > 0

    def test_travel_time_scheduled_baseline(self):
        df, _, _ = build_travel_time_features()
        train_df, val_df, test_df, _ = chronological_split(df)

        baseline = TravelTimeScheduledBaseline()
        preds = baseline.predict(test_df)

        assert len(preds) == len(test_df)
        assert np.all(preds >= 2.5)

        metrics = evaluate_baseline(baseline, test_df, "travel_time_min")
        assert "mae" in metrics
        assert metrics["mae"] > 0
