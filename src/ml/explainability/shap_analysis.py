"""
src/ml/explainability/shap_analysis.py

SHAP TreeExplainer analysis for LightGBM models.
Computes global feature importance and generates natural language explanations.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.config.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)


def compute_shap_importance(
    model: Any,
    X_sample: pd.DataFrame,
    feature_names: List[str],
    output_path: Optional[Path] = None,
) -> Dict[str, float]:
    """
    Compute mean absolute SHAP values per feature across a sample DataFrame.

    Returns dict mapping feature_name -> mean_abs_shap_val sorted descending.
    """
    import shap

    logger.info("Computing SHAP TreeExplainer values for %d sample rows...", len(X_sample))
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)

    if isinstance(shap_values, list):
        shap_values = shap_values[0]

    mean_abs_shap = np.mean(np.abs(shap_values), axis=0)

    importance_dict = {
        name: round(float(val), 4)
        for name, val in sorted(zip(feature_names, mean_abs_shap), key=lambda x: x[1], reverse=True)
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(importance_dict, f, indent=2)
        logger.info("Saved SHAP feature importance to %s", output_path)

    return importance_dict


def generate_sample_explanation(
    model: Any,
    row_df: pd.DataFrame,
    feature_names: List[str],
    entity_name: str = "Majestic",
    predicted_val: float = 72.3,
    congestion_band: str = "HIGH",
    slot_start: str = "08:30",
) -> str:
    """
    Generate natural-language explanation derived directly from row SHAP values.
    """
    import shap

    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(row_df[feature_names])

    if isinstance(shap_vals, list):
        shap_vals = shap_vals[0]

    row_shap = shap_vals[0]
    row_feats = row_df[feature_names].iloc[0]

    # Rank features by absolute impact for this specific prediction
    impacts = sorted(
        zip(feature_names, row_feats, row_shap),
        key=lambda x: abs(x[2]),
        reverse=True,
    )

    top_drivers = []
    for name, val, impact in impacts[:3]:
        sign = "+" if impact >= 0 else ""
        top_drivers.append(f"  # {name}={val} ({sign}{impact:.1f}% SHAP impact)")

    explanation = (
        f"{entity_name} is predicted to have {congestion_band} congestion ({predicted_val:.1f}%) at {slot_start} because:\n"
        + "\n".join(top_drivers)
    )
    return explanation
