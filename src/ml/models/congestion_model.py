"""
src/ml/models/congestion_model.py

LightGBM regression model for edge x 15-min congestion percentage prediction.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

from src.config.settings import PROJECT_ROOT
from src.ml.evaluation.baselines import CongestionHistoricalBaseline, evaluate_baseline
from src.ml.evaluation.metrics import compare_with_baseline, regression_metrics
from src.ml.evaluation.splits import chronological_split
from src.ml.features.congestion_features import (
    CONGESTION_FEATURE_COLS,
    build_congestion_features,
)
from src.ml.features.leakage_check import validate_features

logger = logging.getLogger(__name__)

MODEL_DIR = PROJECT_ROOT / "models" / "congestion"


class CongestionModel:
    """LightGBM Regressor for predicting continuous edge congestion percentage."""

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
        self.features: List[str] = CONGESTION_FEATURE_COLS + ["hist_mean_congestion"]
        self.metrics: Dict[str, Any] = {}

    def fit(self, df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Train LightGBM model with chronological validation and save artifacts."""
        processed_df, self.line_encoder, self.edge_encoder = build_congestion_features(df, fit_encoders=True)

        train_df, val_df, test_df, split_info = chronological_split(processed_df)

        self.hist_lookup = train_df.groupby(["edge_id", "time_slot", "day_of_week"])["hist_mean_congestion"].first().reset_index()
        self.global_hist_mean = float(train_df["congestion_pct"].mean())

        validate_features(self.features)

        X_train, y_train = train_df[self.features], train_df["congestion_pct"]
        X_val, y_val = val_df[self.features], val_df["congestion_pct"]
        X_test, y_test = test_df[self.features], test_df["congestion_pct"]

        # Baseline evaluation
        baseline = CongestionHistoricalBaseline()
        baseline.fit(train_df)
        baseline_val_metrics = evaluate_baseline(baseline, val_df, "congestion_pct")
        baseline_test_metrics = evaluate_baseline(baseline, test_df, "congestion_pct")

        # Train LightGBM model
        self.model = lgb.LGBMRegressor(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            num_leaves=self.num_leaves,
            random_state=self.random_state,
            n_jobs=-1,
            verbosity=-1,
        )

        logger.info("Fitting LightGBM Congestion Model on %d training rows...", len(X_train))
        self.model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(50, verbose=False)],
        )

        # Model predictions
        val_preds = self.model.predict(X_val)
        test_preds = self.model.predict(X_test)

        val_metrics = regression_metrics(y_val.to_numpy(), val_preds)
        test_metrics = regression_metrics(y_test.to_numpy(), test_preds)

        comparison = compare_with_baseline(test_metrics, baseline_test_metrics)

        # Check for suspicious near-zero MAE (leakage indicator)
        if test_metrics["mae"] < 0.5:
            logger.warning("WARNING: Test MAE is %.4f (<0.5%%) -- check for feature leakage!", test_metrics["mae"])

        self.metrics = {
            "model_name": "CongestionLightGBM",
            "model_version": "1.0.0",
            "training_date": datetime.now().isoformat(),
            "data_type": "SYNTHETIC",
            "algorithm": "LightGBM Regressor",
            "random_seed": self.random_state,
            "target": "congestion_pct",
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
        """Predict congestion percentage for an input DataFrame."""
        if self.model is None:
            raise RuntimeError("Model is not fitted or loaded.")

        processed_df, _, _ = build_congestion_features(
            df,
            line_encoder=self.line_encoder,
            edge_encoder=self.edge_encoder,
            fit_encoders=False,
        )
        if "hist_mean_congestion" not in processed_df.columns:
            if hasattr(self, "hist_lookup") and self.hist_lookup is not None:
                processed_df = processed_df.merge(self.hist_lookup, on=["edge_id", "time_slot", "day_of_week"], how="left")
            else:
                processed_df["hist_mean_congestion"] = getattr(self, "global_hist_mean", 23.8)
            processed_df["hist_mean_congestion"] = processed_df["hist_mean_congestion"].fillna(getattr(self, "global_hist_mean", 23.8))

        X = processed_df[self.features]
        preds = self.model.predict(X)
        return np.clip(preds, 0.0, 200.0)

    def save(self, model_dir: Path = MODEL_DIR) -> None:
        """Save model pickle, encoders, feature schema, and metadata."""
        model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, model_dir / "model.pkl")
        joblib.dump(self.line_encoder, model_dir / "line_encoder.pkl")
        joblib.dump(self.edge_encoder, model_dir / "edge_encoder.pkl")
        if hasattr(self, "hist_lookup"):
            joblib.dump(self.hist_lookup, model_dir / "hist_lookup.pkl")
            joblib.dump(getattr(self, "global_hist_mean", 23.8), model_dir / "global_hist_mean.pkl")

        with open(model_dir / "feature_schema.json", "w") as f:
            json.dump({"features": self.features, "target": "congestion_pct"}, f, indent=2)

        with open(model_dir / "metadata.json", "w") as f:
            json.dump(self.metrics, f, indent=2)

        logger.info("Saved CongestionModel artifacts to %s", model_dir)

    def load(self, model_dir: Path = MODEL_DIR) -> None:
        """Load persisted model artifacts."""
        if not (model_dir / "model.pkl").exists():
            raise FileNotFoundError(f"Model artifact not found at {model_dir / 'model.pkl'}")

        self.model = joblib.load(model_dir / "model.pkl")
        self.line_encoder = joblib.load(model_dir / "line_encoder.pkl")
        self.edge_encoder = joblib.load(model_dir / "edge_encoder.pkl")
        if (model_dir / "hist_lookup.pkl").exists():
            self.hist_lookup = joblib.load(model_dir / "hist_lookup.pkl")
        if (model_dir / "global_hist_mean.pkl").exists():
            self.global_hist_mean = joblib.load(model_dir / "global_hist_mean.pkl")

        if (model_dir / "metadata.json").exists():
            with open(model_dir / "metadata.json") as f:
                self.metrics = json.load(f)

        logger.info("Loaded CongestionModel from %s", model_dir)
