"""
src/ml/evaluation/baselines.py

Baseline models for comparison against ML models.
- Congestion Baseline: historical mean per (edge_id, time_slot, day_of_week) from training data.
- Travel Time Baseline: scheduled travel time (2.5 min segment / 3.0 min transfer).
"""
import logging
from typing import Dict, Tuple

import numpy as np
import pandas as pd

from src.ml.evaluation.metrics import regression_metrics

logger = logging.getLogger(__name__)


class CongestionHistoricalBaseline:
    """Predicts historical mean congestion per (edge_id, time_slot, day_of_week) from training data."""

    def __init__(self) -> None:
        self.lookup: Dict[Tuple[str, int, int], float] = {}
        self.global_mean: float = 0.0

    def fit(self, train_df: pd.DataFrame) -> None:
        self.global_mean = float(train_df["congestion_pct"].mean())
        grouped = train_df.groupby(["edge_id", "time_slot", "day_of_week"])["congestion_pct"].mean()
        self.lookup = grouped.to_dict()
        logger.info("Fitted CongestionHistoricalBaseline on %d groups (global mean=%.2f%%).",
                    len(self.lookup), self.global_mean)

    def predict(self, test_df: pd.DataFrame) -> np.ndarray:
        preds = []
        for _, row in test_df.iterrows():
            key = (row["edge_id"], int(row["time_slot"]), int(row["day_of_week"]))
            val = self.lookup.get(key, self.global_mean)
            preds.append(val)
        return np.array(preds)


class TravelTimeScheduledBaseline:
    """Predicts static scheduled travel time (2.5 min segment / 3.0 min transfer)."""

    def predict(self, test_df: pd.DataFrame) -> np.ndarray:
        if "scheduled_time_min" in test_df.columns:
            return test_df["scheduled_time_min"].to_numpy()
        return np.where(test_df["line"] == "TRANSFER", 3.0, 2.5)


def evaluate_baseline(
    baseline_obj,
    test_df: pd.DataFrame,
    target_col: str,
) -> Dict[str, float]:
    """Compute baseline metrics against ground truth target_col."""
    preds = baseline_obj.predict(test_df)
    y_true = test_df[target_col].to_numpy()
    metrics = regression_metrics(y_true, preds)
    return metrics
