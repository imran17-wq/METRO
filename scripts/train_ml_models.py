#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/train_ml_models.py

CLI entry point to train and persist all Phase 3 ML models.
Run from project root:
    python scripts/train_ml_models.py
"""
import io
import json
import logging
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ml.pipeline import run_ml_pipeline
from src.config.settings import LOG_FORMAT, PROJECT_ROOT


def main():
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
    print("\n" + "=" * 60)
    print("  NAMMA PULSE -- ML PREDICTION LAYER TRAINING")
    print("=" * 60)
    print("  DATA_TYPE : SYNTHETIC")
    print("  Models    : Congestion (LGBM), Travel-Time (LGBM), Delay Risk (XGB)")
    print()

    results = run_ml_pipeline()

    print()
    print("  Training Summary Results")
    print("  " + "-" * 56)
    print("  1. Congestion Model (LightGBM):")
    c_res = results["congestion"]
    print(f"     Train Rows : {c_res['split_info']['total_rows']}")
    print(f"     Val MAE    : {c_res['val_metrics']['mae']:.2f}% | RMSE: {c_res['val_metrics']['rmse']:.2f}%")
    print(f"     Test MAE   : {c_res['test_metrics']['mae']:.2f}% (Baseline: {c_res['comparison']['baseline_mae']:.2f}%)")
    print(f"     Improvement: {c_res['comparison']['mae_improvement_pct']:+.1f}% MAE improvement over baseline")

    print()
    print("  2. Travel-Time Model (LightGBM):")
    t_res = results["travel_time"]
    print(f"     Test MAE   : {t_res['test_metrics']['mae']:.2f} min (Baseline: {t_res['comparison']['baseline_mae']:.2f} min)")
    print(f"     Improvement: {t_res['comparison']['mae_improvement_pct']:+.1f}% MAE improvement over baseline")

    print()
    print("  3. Delay Risk Model (XGBoost):")
    d_res = results["delay_risk"]
    if d_res.get("skipped"):
        print(f"     Status: SKIPPED -- {d_res['reason']}")
    else:
        print(f"     Test PR-AUC : {d_res['test_metrics']['pr_auc']:.4f}")
        print(f"     Test ROC-AUC: {d_res['test_metrics']['roc_auc']:.4f}")

    print()
    print("  [PASS] All model artifacts saved to models/")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
