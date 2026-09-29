"""
tests/test_ml_splits.py

Unit tests for chronological date-based splitting and training-only historical feature calculation.
"""
import sys
from pathlib import Path

import pytest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ml.evaluation.splits import chronological_split
from src.ml.features.congestion_features import load_raw_edge_data, build_congestion_features


class TestChronologicalSplits:
    def test_chronological_split_date_ordering(self):
        raw_df = load_raw_edge_data()
        processed_df, _, _ = build_congestion_features(raw_df)
        train_df, val_df, test_df, split_info = chronological_split(processed_df)

        assert not train_df.empty
        assert not val_df.empty
        assert not test_df.empty

        train_max_date = train_df["date"].max()
        val_min_date = val_df["date"].min()
        val_max_date = val_df["date"].max()
        test_min_date = test_df["date"].min()

        assert train_max_date < val_min_date, "Validation dates overlap with or precede training dates"
        assert val_max_date < test_min_date, "Test dates overlap with or precede validation dates"

    def test_no_date_overlap_across_splits(self):
        raw_df = load_raw_edge_data()
        processed_df, _, _ = build_congestion_features(raw_df)
        train_df, val_df, test_df, _ = chronological_split(processed_df)

        train_dates = set(train_df["date"].dt.date if hasattr(train_df["date"].dt, "date") else train_df["date"])
        val_dates = set(val_df["date"].dt.date if hasattr(val_df["date"].dt, "date") else val_df["date"])
        test_dates = set(test_df["date"].dt.date if hasattr(test_df["date"].dt, "date") else test_df["date"])

        assert not (train_dates & val_dates), "Train and Val dates overlap"
        assert not (train_dates & test_dates), "Train and Test dates overlap"
        assert not (val_dates & test_dates), "Val and Test dates overlap"

    def test_hist_mean_feature_created(self):
        raw_df = load_raw_edge_data()
        processed_df, _, _ = build_congestion_features(raw_df)
        train_df, val_df, test_df, _ = chronological_split(processed_df)

        assert "hist_mean_congestion" in train_df.columns
        assert "hist_mean_congestion" in val_df.columns
        assert "hist_mean_congestion" in test_df.columns
        assert train_df["hist_mean_congestion"].isna().sum() == 0
