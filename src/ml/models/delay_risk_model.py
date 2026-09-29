"""
src/ml/models/delay_risk_model.py

XGBoost binary classifier predicting probability of delay event occurrence.
Conditional training: requires >= 500 positive delay examples in training set.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from src.config.settings import PROJECT_ROOT
from src.ml.evaluation.metrics import classification_metrics
from src.ml.evaluation.splits import chronological_split
from src.ml.features.congestion_features import (
    CONGESTION_FEATURE_COLS,
    build_congestion_features,
)
from src.ml.features.leakage_check import validate_features
from src.ml.features.travel_time_features import load_delay_events_data

logger = logging.getLogger(__name__)

MODEL_DIR = PROJECT_ROOT / "models" / "delay_risk"


class DelayRiskModel:
    """XGBoost binary classifier for delay event risk estimation."""

    def __init__(self, random_state: int = 42) -> None:
        self.random_state = random_state
        self.model: Optional[XGBClassifier] = None
        self.features: List[str] = CONGESTION_FEATURE_COLS
        self.metrics: Dict[str, Any] = {}

    def fit(
        self,
        edge_df: Optional[pd.DataFrame] = None,
        delay_df: Optional[pd.DataFrame] = None,
        min_positive_examples: int = 500,
    ) -> Dict[str, Any]:
        """Train XGBoost classifier if positive delay examples >= min_positive_examples."""
        processed_df, line_enc, edge_enc = build_congestion_features(edge_df, fit_encoders=True)

        if delay_df is None:
            delay_df = load_delay_events_data()

        # Mark binary label has_delay = 1 if delay event exists for edge at date & slot
        if not delay_df.empty:
            delay_keys = set(
                zip(
                    delay_df["date"].dt.date if hasattr(delay_df["date"].dt, "date") else delay_df["date"],
                    delay_df["time_slot"].astype(int),
                    delay_df["edge_id"],
                )
            )
            processed_df["has_delay"] = processed_df.apply(
                lambda r: 1 if (r["date"].date() if hasattr(r["date"], "date") else r["date"], int(r["time_slot"]), r["edge_id"]) in delay_keys else 0,
                axis=1,
            )
        else:
            processed_df["has_delay"] = 0

        train_df, val_df, test_df, split_info = chronological_split(processed_df)
        pos_count = int(train_df["has_delay"].sum())

        if pos_count < min_positive_examples:
            msg = f"Skipped delay risk model: training set has only {pos_count} positive examples (< {min_positive_examples} required)."
            logger.warning(msg)
            self.metrics = {
                "model_name": "DelayRiskXGBoost",
                "skipped": True,
                "reason": msg,
                "positive_examples_in_train": pos_count,
            }
            self.save_metadata()
            return self.metrics

        validate_features(self.features)

        X_train, y_train = train_df[self.features], train_df["has_delay"]
        X_val, y_val = val_df[self.features], val_df["has_delay"]
        X_test, y_test = test_df[self.features], test_df["has_delay"]

        neg_count = len(y_train) - pos_count
        scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1.0

        self.model = XGBClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            scale_pos_weight=scale_pos_weight,
            random_state=self.random_state,
            eval_metric="logloss",
        )

        logger.info("Fitting XGBoost Delay Risk Model (%d pos / %d neg)...", pos_count, neg_count)
        self.model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )

        val_probs = self.model.predict_proba(X_val)[:, 1]
        test_probs = self.model.predict_proba(X_test)[:, 1]

        val_metrics = classification_metrics(y_val.to_numpy(), val_probs)
        test_metrics = classification_metrics(y_test.to_numpy(), test_probs)

        self.metrics = {
            "model_name": "DelayRiskXGBoost",
            "model_version": "1.0.0",
            "skipped": False,
            "training_date": datetime.now().isoformat(),
            "data_type": "SYNTHETIC",
            "algorithm": "XGBoost Classifier",
            "random_seed": self.random_state,
            "target": "has_delay",
            "features": self.features,
            "positive_examples_in_train": pos_count,
            "val_metrics": val_metrics,
            "test_metrics": test_metrics,
        }

        self.save()
        return self.metrics

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        """Predict delay probability for input DataFrame."""
        if self.model is None:
            # Model skipped or not fitted -- return zeros
            return np.zeros(len(df))

        processed_df, _, _ = build_congestion_features(df, fit_encoders=False)
        X = processed_df[self.features]
        return self.model.predict_proba(X)[:, 1]

    def save(self, model_dir: Path = MODEL_DIR) -> None:
        """Save model pickle and metadata."""
        model_dir.mkdir(parents=True, exist_ok=True)
        if self.model is not None:
            joblib.dump(self.model, model_dir / "model.pkl")

        with open(model_dir / "feature_schema.json", "w") as f:
            json.dump({"features": self.features, "target": "has_delay"}, f, indent=2)

        self.save_metadata(model_dir)

    def save_metadata(self, model_dir: Path = MODEL_DIR) -> None:
        model_dir.mkdir(parents=True, exist_ok=True)
        with open(model_dir / "metadata.json", "w") as f:
            json.dump(self.metrics, f, indent=2)

    def load(self, model_dir: Path = MODEL_DIR) -> None:
        """Load persisted model artifacts."""
        if (model_dir / "metadata.json").exists():
            with open(model_dir / "metadata.json") as f:
                self.metrics = json.load(f)

        if (model_dir / "model.pkl").exists():
            self.model = joblib.load(model_dir / "model.pkl")

        logger.info("Loaded DelayRiskModel from %s", model_dir)
