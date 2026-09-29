"""
src/ml/models/travel_time_model.py

LightGBM regression model for edge x 15-min travel time prediction.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

from src.config.settings import PROJECT_ROOT
from src.ml.evaluation.baselines import TravelTimeScheduledBaseline, evaluate_baseline
from src.ml.evaluation.metrics import compare_with_baseline, regression_metrics
from src.ml.evaluation.splits import chronological_split
from src.ml.features.leakage_check import validate_features
from src.ml.features.travel_time_features import (
    TRAVEL_TIME_FEATURE_COLS,
    build_travel_time_features,
)

logger = logging.getLogger(__name__)

MODEL_DIR = PROJECT_ROOT / "models" / "travel_time"


class TravelTimeModel:
    """LightGBM Regressor for predicting realistic travel time per edge segment."""

    def __init__(
        self,
        n_estimators: int = 300,
        learning_rate: float = 0.05,
        num_leaves: int = 31,
        random_state: int = 42,
    ) -> None:
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.random_state = random_state

        self.model: Optional[lgb.LGBMRegressor] = None
        self.line_encoder: Optional[LabelEncoder] = None
        self.edge_encoder: Optional[LabelEncoder] = None
        self.features: List[str] = TRAVEL_TIME_FEATURE_COLS
        self.metrics: Dict[str, Any] = {}

    def fit(self, edge_df: Optional[pd.DataFrame] = None, delay_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Train LightGBM travel time model with chronological validation."""
        processed_df, self.line_encoder, self.edge_encoder = build_travel_time_features(
            edge_df, delay_df, fit_encoders=True
        )

        train_df, val_df, test_df, split_info = chronological_split(processed_df)

        validate_features(self.features)

        X_train, y_train = train_df[self.features], train_df["travel_time_min"]
        X_val, y_val = val_df[self.features], val_df["travel_time_min"]
        X_test, y_test = test_df[self.features], test_df["travel_time_min"]

        # Baseline evaluation (scheduled_time_min)
        baseline = TravelTimeScheduledBaseline()
        baseline_val_metrics = evaluate_baseline(baseline, val_df, "travel_time_min")
        baseline_test_metrics = evaluate_baseline(baseline, test_df, "travel_time_min")

        # Train LightGBM model
        self.model = lgb.LGBMRegressor(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            num_leaves=self.num_leaves,
            random_state=self.random_state,
            n_jobs=-1,
            verbosity=-1,
        )

        logger.info("Fitting LightGBM Travel Time Model on %d training rows...", len(X_train))
        self.model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(50, verbose=False)],
        )

        val_preds = self.model.predict(X_val)
        test_preds = self.model.predict(X_test)

        val_metrics = regression_metrics(y_val.to_numpy(), val_preds)
        test_metrics = regression_metrics(y_test.to_numpy(), test_preds)

        comparison = compare_with_baseline(test_metrics, baseline_test_metrics)

        self.metrics = {
            "model_name": "TravelTimeLightGBM",
            "model_version": "1.0.0",
            "training_date": datetime.now().isoformat(),
            "data_type": "SYNTHETIC",
            "algorithm": "LightGBM Regressor",
            "random_seed": self.random_state,
            "target": "travel_time_min",
            "features": self.features,
            "validation_method": "Chronological Split (70/15/15)",
            "split_info": split_info,
            "val_metrics": val_metrics,
            "test_metrics": test_metrics,
            "baseline_test_metrics": baseline_test_metrics,
            "comparison": comparison,
        }

        self.save()
        return self.metrics

    def predict_dataframe(self, df: pd.DataFrame) -> np.ndarray:
        """Predict travel time in minutes for input DataFrame."""
        if self.model is None:
            raise RuntimeError("Model is not fitted or loaded.")

        processed_df, _, _ = build_travel_time_features(
            df,
            line_encoder=self.line_encoder,
            edge_encoder=self.edge_encoder,
            fit_encoders=False,
        )
        X = processed_df[self.features]
        preds = self.model.predict(X)
        return np.clip(preds, 1.0, 60.0)

    def save(self, model_dir: Path = MODEL_DIR) -> None:
        """Save model pickle, encoders, and metadata."""
        model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, model_dir / "model.pkl")
        joblib.dump(self.line_encoder, model_dir / "line_encoder.pkl")
        joblib.dump(self.edge_encoder, model_dir / "edge_encoder.pkl")

        with open(model_dir / "feature_schema.json", "w") as f:
            json.dump({"features": self.features, "target": "travel_time_min"}, f, indent=2)

        with open(model_dir / "metadata.json", "w") as f:
            json.dump(self.metrics, f, indent=2)

        logger.info("Saved TravelTimeModel artifacts to %s", model_dir)

    def load(self, model_dir: Path = MODEL_DIR) -> None:
        """Load persisted model artifacts."""
        if not (model_dir / "model.pkl").exists():
            raise FileNotFoundError(f"Model artifact not found at {model_dir / 'model.pkl'}")

        self.model = joblib.load(model_dir / "model.pkl")
        self.line_encoder = joblib.load(model_dir / "line_encoder.pkl")
        self.edge_encoder = joblib.load(model_dir / "edge_encoder.pkl")

        if (model_dir / "metadata.json").exists():
            with open(model_dir / "metadata.json") as f:
                self.metrics = json.load(f)

        logger.info("Loaded TravelTimeModel from %s", model_dir)
