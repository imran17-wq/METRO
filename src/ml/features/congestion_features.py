"""
src/ml/features/congestion_features.py

Feature engineering for edge x 15-minute congestion prediction model.
All features adhere strictly to KNOWN_BEFORE_PREDICTION rules.
"""
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

from src.config.settings import DATA_DIR, PROCESSED_DIR
from src.ml.features.leakage_check import validate_features

logger = logging.getLogger(__name__)

CONGESTION_FEATURE_COLS = [
    "hour",
    "minute_bucket",
    "time_slot",
    "day_of_week",
    "is_weekend",
    "is_peak_slot",
    "line_enc",
    "edge_enc",
    "is_interchange_edge",
    "capacity",
    "lag1_congestion_pct",
    "lag2_congestion_pct",
    "roll3_mean_congestion",
    "roll6_mean_congestion",
]


def load_raw_edge_data(dataset_path: Optional[Path] = None) -> pd.DataFrame:
    """Load raw edge dataset (30-day expanded if available, else 7-day)."""
    if dataset_path is None:
        expanded_path = DATA_DIR / "synthetic" / "edge_load_30d.csv"
        standard_path = DATA_DIR / "synthetic" / "edge_load.csv"
        dataset_path = expanded_path if expanded_path.exists() else standard_path

    logger.info("Loading edge load data from %s...", dataset_path)
    df = pd.read_csv(dataset_path, parse_dates=["date"])
    return df


def load_static_edge_metadata() -> pd.DataFrame:
    """Load static edge topology metadata from processed/edges.csv."""
    edges_csv = PROCESSED_DIR / "edges.csv"
    if not edges_csv.exists():
        raise FileNotFoundError(f"Static edges CSV not found at {edges_csv}")
    edges_df = pd.read_csv(edges_csv)
    # Mark transfer edges as interchange edges
    edges_df["is_interchange_edge"] = edges_df["line"].apply(lambda l: l == "TRANSFER")
    return edges_df


def build_congestion_features(
    df: Optional[pd.DataFrame] = None,
    line_encoder: Optional[LabelEncoder] = None,
    edge_encoder: Optional[LabelEncoder] = None,
    fit_encoders: bool = True,
) -> Tuple[pd.DataFrame, LabelEncoder, LabelEncoder]:
    """
    Process raw edge data and extract feature matrix X and target y.

    Returns (processed_df, line_encoder, edge_encoder)
    """
    if df is None:
        df = load_raw_edge_data()

    df = df.copy()

    # Filter out Pink and Blue edges if present (they have no synthetic history)
    df = df[~df["line"].isin(["Pink", "Blue"])].reset_index(drop=True)

    # Convert slot_start (e.g. "06:15") to hour and minute_bucket
    if "slot_start" in df.columns:
        hours = df["slot_start"].str.split(":").str[0].astype(int)
        minutes = df["slot_start"].str.split(":").str[1].astype(int)
        df["hour"] = hours
        df["minute_bucket"] = minutes
    else:
        df["hour"] = (df["time_slot"] * 15 // 60) % 24
        df["minute_bucket"] = (df["time_slot"] * 15) % 60

    # Temporal flags
    df["day_of_week"] = df["date"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].apply(lambda d: 1 if d >= 5 else 0)
    df["is_peak_slot"] = df["hour"].apply(lambda h: 1 if (8 <= h < 11 or 17 <= h < 21) else 0)

    # Sort deterministically for lag/rolling features
    df = df.sort_values(["edge_id", "date", "time_slot"]).reset_index(drop=True)

    # Groupby edge_id for lag & rolling features
    logger.info("Computing per-edge lag and rolling congestion features...")
    grouped = df.groupby("edge_id")["congestion_pct"]

    df["lag1_congestion_pct"] = grouped.shift(1)
    df["lag2_congestion_pct"] = grouped.shift(2)

    shifted = grouped.shift(1)
    df["roll3_mean_congestion"] = shifted.groupby(df["edge_id"]).rolling(3, min_periods=1).mean().reset_index(drop=True)
    df["roll6_mean_congestion"] = shifted.groupby(df["edge_id"]).rolling(6, min_periods=1).mean().reset_index(drop=True)

    # Fill initial NaNs resulting from shifts with overall mean or zero
    df["lag1_congestion_pct"] = df["lag1_congestion_pct"].fillna(df["congestion_pct"].mean())
    df["lag2_congestion_pct"] = df["lag2_congestion_pct"].fillna(df["lag1_congestion_pct"])
    df["roll3_mean_congestion"] = df["roll3_mean_congestion"].fillna(df["lag1_congestion_pct"])
    df["roll6_mean_congestion"] = df["roll6_mean_congestion"].fillna(df["roll3_mean_congestion"])

    # Load static edge metadata for capacity and interchange flag
    try:
        meta = load_static_edge_metadata()
        meta_dict = meta.set_index("edge_id")["is_interchange_edge"].to_dict()
        df["is_interchange_edge"] = df["edge_id"].map(meta_dict).fillna(0).astype(int)
    except Exception as e:
        logger.warning("Could not load static edge metadata (%s), defaulting is_interchange_edge", e)
        df["is_interchange_edge"] = (df["line"] == "TRANSFER").astype(int)

    # Encoders
    if fit_encoders:
        line_encoder = LabelEncoder()
        edge_encoder = LabelEncoder()
        df["line_enc"] = line_encoder.fit_transform(df["line"].astype(str))
        df["edge_enc"] = edge_encoder.fit_transform(df["edge_id"].astype(str))
    else:
        if line_encoder is None or edge_encoder is None:
            raise ValueError("Encoders must be provided when fit_encoders=False")
        df["line_enc"] = df["line"].astype(str).map(
            lambda x: line_encoder.transform([x])[0] if x in line_encoder.classes_ else -1
        )
        df["edge_enc"] = df["edge_id"].astype(str).map(
            lambda x: edge_encoder.transform([x])[0] if x in edge_encoder.classes_ else -1
        )

    # Run leakage check on feature columns
    validate_features(CONGESTION_FEATURE_COLS)

    return df, line_encoder, edge_encoder
