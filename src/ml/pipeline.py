"""
src/ml/pipeline.py

End-to-end training and evaluation pipeline for Namma Pulse ML models.
Orchestrates:
1. Loading 30-day synthetic dataset
2. Feature engineering once (fast execution)
3. Training Congestion LightGBM model
4. Training Travel Time LightGBM model
5. Training Delay Risk XGBoost model (if >= 500 positive examples)
6. Running SHAP explainability analysis
7. Persisting all artifacts in models/
"""
import logging
from typing import Dict, Any

from src.ml.models.congestion_model import CongestionModel
from src.ml.models.travel_time_model import TravelTimeModel
from src.ml.models.delay_risk_model import DelayRiskModel
from src.ml.explainability.shap_analysis import compute_shap_importance
from src.ml.features.congestion_features import build_congestion_features, load_raw_edge_data
from src.config.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)


def run_ml_pipeline() -> Dict[str, Any]:
    """Execute end-to-end training, evaluation, and artifact saving."""
    logger.info("Starting Phase 3 ML Pipeline execution...")

    # Load 30-day edge data and build feature matrix ONCE
    raw_df = load_raw_edge_data()
    logger.info("Pre-computing feature matrix...")
    processed_df, line_enc, edge_enc = build_congestion_features(raw_df, fit_encoders=True)

    # 1. Congestion Model
    logger.info("=== 1. Training Congestion Model ===")
    c_model = CongestionModel(random_state=42)
    c_metrics = c_model.fit(processed_df)

    # SHAP feature importance for congestion model
    try:
        sample_raw = processed_df.sample(n=min(100, len(processed_df)), random_state=42).copy()
        if hasattr(c_model, "hist_lookup") and c_model.hist_lookup is not None:
            sample_raw = sample_raw.merge(c_model.hist_lookup, on=["edge_id", "time_slot", "day_of_week"], how="left")
            sample_raw["hist_mean_congestion"] = sample_raw["hist_mean_congestion"].fillna(getattr(c_model, "global_hist_mean", 23.8))
        sample_df = sample_raw[c_model.features]
        shap_path = PROJECT_ROOT / "models" / "congestion" / "shap_importance.json"
        compute_shap_importance(c_model.model, sample_df, c_model.features, output_path=shap_path)
    except Exception as e:
        logger.warning("SHAP calculation skipped or encountered warning: %s", e)

    # 2. Travel Time Model
    logger.info("=== 2. Training Travel Time Model ===")
    t_model = TravelTimeModel(random_state=42)
    t_metrics = t_model.fit(processed_df)

    # 3. Delay Risk Model
    logger.info("=== 3. Training Delay Risk Model ===")
    d_model = DelayRiskModel(random_state=42)
    d_metrics = d_model.fit(processed_df)

    logger.info("ML Pipeline execution completed successfully.")
    return {
        "congestion": c_metrics,
        "travel_time": t_metrics,
        "delay_risk": d_metrics,
    }
