"""
tests/test_ml_models.py

Unit tests for ML model training, persistence, loading, and predictions.
"""
import sys
from pathlib import Path

import pytest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ml.models.congestion_model import CongestionModel
from src.ml.models.travel_time_model import TravelTimeModel
from src.ml.models.delay_risk_model import DelayRiskModel
from src.ml.features.congestion_features import load_raw_edge_data


class TestCongestionModel:
    def test_fit_predict_save_load(self, tmp_path):
        raw_df = load_raw_edge_data()

        model = CongestionModel(n_estimators=20, random_state=42)
        metrics = model.fit(raw_df)

        assert "test_metrics" in metrics
        assert metrics["test_metrics"]["mae"] > 0

        # Predict on sample
        preds = model.predict_dataframe(raw_df.head(10))
        assert len(preds) == 10
        assert np.all(preds >= 0)

        # Save and reload
        save_dir = tmp_path / "congestion"
        model.save(save_dir)

        loaded_model = CongestionModel()
        loaded_model.load(save_dir)
        loaded_preds = loaded_model.predict_dataframe(raw_df.head(10))

        np.testing.assert_allclose(preds, loaded_preds, rtol=1e-5)


class TestTravelTimeModel:
    def test_fit_predict_save_load(self, tmp_path):
        raw_df = load_raw_edge_data()

        model = TravelTimeModel(n_estimators=20, random_state=42)
        metrics = model.fit(raw_df)

        assert "test_metrics" in metrics
        assert metrics["test_metrics"]["mae"] > 0

        preds = model.predict_dataframe(raw_df.head(10))
        assert len(preds) == 10
        assert np.all(preds >= 1.0)

        save_dir = tmp_path / "travel_time"
        model.save(save_dir)

        loaded_model = TravelTimeModel()
        loaded_model.load(save_dir)
        loaded_preds = loaded_model.predict_dataframe(raw_df.head(10))

        np.testing.assert_allclose(preds, loaded_preds, rtol=1e-5)


class TestDelayRiskModel:
    def test_fit_handles_insufficient_samples_gracefully(self, tmp_path):
        raw_df = load_raw_edge_data().head(100)  # small sample

        model = DelayRiskModel(random_state=42)
        metrics = model.fit(raw_df, min_positive_examples=500)

        assert metrics.get("skipped") is True
        assert "positive_examples_in_train" in metrics
