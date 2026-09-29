"""
src/ml/evaluation/metrics.py

Evaluation metrics calculation module.
- Regression: MAE, RMSE, R2, improvement over baseline %
- Classification: PR-AUC, ROC-AUC, Precision, Recall, F1 (Accuracy is NOT reported)
"""
from typing import Dict

import numpy as np
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    precision_recall_curve,
    auc,
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
)


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate MAE, RMSE, R2 for regression models."""
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2": round(r2, 4),
    }


def compare_with_baseline(
    model_metrics: Dict[str, float],
    baseline_metrics: Dict[str, float],
) -> Dict[str, float]:
    """Calculate percentage improvement over baseline."""
    b_mae = baseline_metrics["mae"]
    m_mae = model_metrics["mae"]
    b_rmse = baseline_metrics["rmse"]
    m_rmse = model_metrics["rmse"]

    mae_imp = ((b_mae - m_mae) / b_mae) * 100.0 if b_mae > 0 else 0.0
    rmse_imp = ((b_rmse - m_rmse) / b_rmse) * 100.0 if b_rmse > 0 else 0.0

    return {
        "baseline_mae": b_mae,
        "model_mae": m_mae,
        "mae_improvement_pct": round(mae_imp, 2),
        "baseline_rmse": b_rmse,
        "model_rmse": m_rmse,
        "rmse_improvement_pct": round(rmse_imp, 2),
    }


def classification_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> Dict[str, float]:
    """Calculate PR-AUC, ROC-AUC, Precision, Recall, F1 for classification models."""
    y_pred = (y_prob >= threshold).astype(int)

    precision_vals, recall_vals, _ = precision_recall_curve(y_true, y_prob)
    pr_auc = float(auc(recall_vals, precision_vals))

    try:
        roc_auc = float(roc_auc_score(y_true, y_prob))
    except Exception:
        roc_auc = 0.5

    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    return {
        "pr_auc": round(pr_auc, 4),
        "roc_auc": round(roc_auc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
    }
