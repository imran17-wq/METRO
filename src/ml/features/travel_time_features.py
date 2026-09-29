"""
src/ml/features/travel_time_features.py

Travel-time target generation and feature engineering.
Target formula (documented):
    travel_time_min = 2.5 + (2.5 * min(lag1_congestion_pct / 100, 1.5)) + delay_contrib

Target leakage policy:
    Current slot (T) congestion_pct is EXCLUDED from feature columns.
    Only prior-slot lag features and historical training averages are included.
"""
import logging
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
from sklearn.preprocessing import LabelEncoder

from src.config.settings import DATA_DIR
from src.ml.features.congestion_features import build_congestion_features
from src.ml.features.leakage_check import validate_features

logger = logging.getLogger(__name__)

TRAVEL_TIME_FEATURE_COLS = [
    "hour",
    "minute_bucket",
    "time_slot",
    "day_of_week",
    "is_weekend",
    "is_peak_slot",
    "line_enc",
    "edge_enc",
    "is_interchange_edge",
    "scheduled_time_min",
    "lag1_congestion_pct",
    "lag2_congestion_pct",
    "roll3_mean_congestion",
    "roll6_mean_congestion",
]


def load_delay_events_data(dataset_path: Optional[Path] = None) -> pd.DataFrame:
    """Load delay events dataset."""
    if dataset_path is None:
        expanded_path = DATA_DIR / "synthetic" / "delay_events_30d.csv"
        standard_path = DATA_DIR / "synthetic" / "delay_events.csv"
        dataset_path = expanded_path if expanded_path.exists() else standard_path

    if not dataset_path.exists():
        logger.warning("Delay events file not found at %s. Returning empty DataFrame.", dataset_path)
        return pd.DataFrame(columns=["date", "time_slot", "edge_id", "delay_min"])

    return pd.read_csv(dataset_path, parse_dates=["date"])


def build_travel_time_features(
    edge_df: Optional[pd.DataFrame] = None,
    delay_df: Optional[pd.DataFrame] = None,
    line_encoder: Optional[LabelEncoder] = None,
    edge_encoder: Optional[LabelEncoder] = None,
    fit_encoders: bool = True,
) -> Tuple[pd.DataFrame, LabelEncoder, LabelEncoder]:
    """
    Generate travel_time_min target and construct travel time feature matrix.

    Returns (processed_df, line_encoder, edge_encoder)
    """
    if edge_df is None or "lag1_congestion_pct" not in edge_df.columns:
        edge_processed_df, line_encoder, edge_encoder = build_congestion_features(
            edge_df,
            fit_encoders=fit_encoders,
            line_encoder=line_encoder,
            edge_encoder=edge_encoder,
        )
    else:
        edge_processed_df = edge_df.copy()

    if delay_df is None:
        delay_df = load_delay_events_data()

    df = edge_processed_df.copy()

    # Compute delay_contrib per (date, time_slot, edge_id)
    if not delay_df.empty:
        delay_agg = delay_df.groupby(["date", "time_slot", "edge_id"])["delay_min"].mean().reset_index()
        delay_agg.rename(columns={"delay_min": "delay_contrib"}, inplace=True)
        df = df.merge(delay_agg, on=["date", "time_slot", "edge_id"], how="left")
        df["delay_contrib"] = df["delay_contrib"].fillna(0.0)
    else:
        df["delay_contrib"] = 0.0

    # Constant base scheduled time for segment edges = 2.5 min (TRANSFER edges = 3.0 min)
    df["scheduled_time_min"] = df["line"].apply(lambda l: 3.0 if l == "TRANSFER" else 2.5)

    # Documented synthetic target generation formula using lag-1 congestion (T-1 slot):
    # travel_time_min = scheduled_time_min + (2.5 * min(lag1_congestion_pct / 100, 1.5)) + delay_contrib
    congestion_penalty = 2.5 * (df["lag1_congestion_pct"] / 100.0).clip(upper=1.5)
    df["travel_time_min"] = (df["scheduled_time_min"] + congestion_penalty + df["delay_contrib"]).round(2)

    # Ensure leakage validation passes on feature columns
    validate_features(TRAVEL_TIME_FEATURE_COLS)

    return df, line_encoder, edge_encoder
