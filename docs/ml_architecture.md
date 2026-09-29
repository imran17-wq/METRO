# Phase 3 — Machine Learning Prediction Layer Architecture

**Namma Pulse v1.0** — Bengaluru Metro Intelligent Route & Congestion Management System

---

## 1. Executive Summary

Phase 3 introduces an explainable, tabular machine learning prediction layer built on top of the canonical 5-line network graph. The ML layer predicts:
1. **Edge-level congestion percentage** (15-minute time buckets) via LightGBM Regressor.
2. **Realistic travel time** per edge segment via LightGBM Regressor.
3. **Delay/disruption risk probability** per edge via XGBoost Classifier.

All training data is **SYNTHETIC** generated via gravity-model spatial distribution and temporal shaping. Data provenance metadata (`data_provenance = SYNTHETIC MODEL OUTPUT`) is attached to every prediction.

---

## 2. Dataset Specs & Chronological Splitting

### Training Dataset (`data/synthetic/*_30d.csv`)
- **Date Range**: 30 days (2024-01-01 to 2024-01-30)
- **Time Slots**: 24–89 (15-minute buckets from 06:00 to 22:15, 66 slots/day)
- **Granularity**: Edge × 15-minute time slot (83 active edges × 30 days × 66 slots = **164,340 rows**)
- **Active Lines**: Purple, Green, Yellow

### Chronological Splitting Strategy
To prevent temporal data leakage, the dataset is split strictly by date order without random shuffling:
- **Training Set**: Days 1–21 (70%, ~115,000 rows)
- **Validation Set**: Days 22–25 (13%, ~21,500 rows)
- **Test Set**: Days 26–30 (17%, ~27,800 rows)

---

## 3. Feature Leakage Prevention

Every feature is registered in `src/ml/features/leakage_check.py` and audited before training:

| Feature Name | Status | Rationale |
|--------------|--------|-----------|
| `hour` | `KNOWN_BEFORE_PREDICTION` | Derived from slot index |
| `minute_bucket` | `KNOWN_BEFORE_PREDICTION` | Derived from slot index |
| `time_slot` | `KNOWN_BEFORE_PREDICTION` | Derived from slot index |
| `day_of_week` | `KNOWN_BEFORE_PREDICTION` | Derived from date |
| `is_weekend` | `KNOWN_BEFORE_PREDICTION` | Derived from date |
| `is_peak_slot` | `KNOWN_BEFORE_PREDICTION` | AM/PM peak flag |
| `line_enc` | `KNOWN_BEFORE_PREDICTION` | Label-encoded static line |
| `edge_enc` | `KNOWN_BEFORE_PREDICTION` | Label-encoded static edge |
| `is_interchange_edge` | `KNOWN_BEFORE_PREDICTION` | Static graph metadata |
| `lag1_congestion_pct` | `KNOWN_BEFORE_PREDICTION` | T-1 slot congestion value |
| `lag2_congestion_pct` | `KNOWN_BEFORE_PREDICTION` | T-2 slot congestion value |
| `roll3_mean_congestion` | `KNOWN_BEFORE_PREDICTION` | Rolling 3-slot mean of past values |
| `roll6_mean_congestion` | `KNOWN_BEFORE_PREDICTION` | Rolling 6-slot mean of past values |
| `hist_mean_congestion` | `KNOWN_BEFORE_PREDICTION` | Computed **strictly from training set** |
| `congestion_pct` (T) | `TARGET_LEAKAGE_RISK` | **REJECTED** — target variable |
| `congestion_band` (T) | `TARGET_LEAKAGE_RISK` | **REJECTED** — derived from target |
| `flow_passengers` (T) | `TARGET_LEAKAGE_RISK` | **REJECTED** — used to calculate target |

---

## 4. Models & Targets

### A. Congestion Prediction Model
- **Target**: `congestion_pct` (continuous float, 0% to 150%+)
- **Algorithm**: LightGBM Regressor (`n_estimators=300, learning_rate=0.05, num_leaves=31`)
- **Baseline**: Historical average per (edge, time_slot, day_of_week) from training data
- **Primary Metric**: MAE, RMSE, % improvement over baseline

### B. Travel-Time Prediction Model
- **Target**: `travel_time_min` (generated target: `scheduled_time_min + 2.5 * min(lag1_congestion / 100, 1.5) + delay_contrib`)
- **Algorithm**: LightGBM Regressor
- **Baseline**: Static scheduled time (2.5 min segment / 3.0 min transfer)
- **Primary Metric**: MAE, RMSE, % improvement over baseline

### C. Delay Risk Model
- **Target**: `has_delay` (binary classification: 1 if delay event occurred on edge during slot, else 0)
- **Algorithm**: XGBoost Classifier (`scale_pos_weight` imbalance handling)
- **Metrics**: PR-AUC, ROC-AUC, Precision, Recall, F1 (Accuracy is NOT used)

---

## 5. NetworkStateBuilder & Pink/Blue Null Policy

The `NetworkStateBuilder` in `src/ml/network_state.py` attaches ML predictions to all 127 edges of the canonical 5-line NetworkX graph without rebuilding the graph.

- **Purple, Green, Yellow**: `active=true`, predictions populated, `data_provenance="SYNTHETIC MODEL OUTPUT"`.
- **Pink, Blue (Under Construction)**: `active=false`, `predicted_congestion_pct=null`, `predicted_travel_time_min=null`, `congestion_band=null`, `delay_risk_prob=null`, `data_provenance="NO_SYNTHETIC_DATA"`.

---

## 6. SHAP Explainability

SHAP (`shap.TreeExplainer`) is integrated to compute global feature importance and generate human-readable natural language explanations:

```
"Majestic (PL22) predicted HIGH congestion (72.3%) at 08:30 because:
 #1 hist_mean_congestion=68.1 (+9.2 SHAP impact)
 #2 lag1_congestion_pct=65.4 (+7.8 SHAP impact)
 #3 is_peak_slot=1 (+4.1 SHAP impact)"
```

Global feature importance rankings are saved to `models/congestion/shap_importance.json`.
