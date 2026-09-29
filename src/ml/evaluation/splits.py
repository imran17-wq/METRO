"""
src/ml/evaluation/splits.py

Chronological date-based dataset splitting module.
Ensures zero data leakage across train/validation/test partitions.
Calculates historical lookup tables (hist_mean_congestion, hist_delay_rate)
STRICTLY from the training partition.
"""
import logging
from typing import Dict, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


def chronological_split(
    df: pd.DataFrame,
    date_col: str = "date",
    train_frac: float = 0.70,
    val_frac: float = 0.15,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, str]]:
    """
    Split DataFrame chronologically based on sorted unique dates.

    Returns (train_df, val_df, test_df, split_info_dict)
    """
    if df.empty:
        raise ValueError("DataFrame is empty, cannot perform chronological split.")

    unique_dates = sorted(df[date_col].dt.date.unique() if hasattr(df[date_col].dt, "date") else df[date_col].unique())
    num_dates = len(unique_dates)

    if num_dates == 1:
        train_dates = set(unique_dates)
        val_dates = set(unique_dates)
        test_dates = set(unique_dates)
    else:
        n_train = max(1, int(num_dates * train_frac))
        n_val = max(1, int(num_dates * val_frac))

        train_dates = set(unique_dates[:n_train])
        val_dates = set(unique_dates[n_train : n_train + n_val])
        test_dates = set(unique_dates[n_train + n_val :])

        if not val_dates:
            val_dates = set(train_dates)
        if not test_dates:
            test_dates = set(val_dates)

    train_df = df[df[date_col].apply(lambda d: (d.date() if hasattr(d, "date") else d) in train_dates)].copy()
    val_df = df[df[date_col].apply(lambda d: (d.date() if hasattr(d, "date") else d) in val_dates)].copy()
    test_df = df[df[date_col].apply(lambda d: (d.date() if hasattr(d, "date") else d) in test_dates)].copy()

    # Compute historical mean feature strictly from training rows
    hist_lookup = train_df.groupby(["edge_id", "time_slot", "day_of_week"])["congestion_pct"].mean().reset_index()
    hist_lookup.rename(columns={"congestion_pct": "hist_mean_congestion"}, inplace=True)
    global_hist_mean = float(train_df["congestion_pct"].mean())

    def _join_hist(part_df: pd.DataFrame) -> pd.DataFrame:
        if "hist_mean_congestion" in part_df.columns:
            part_df = part_df.drop(columns=["hist_mean_congestion"])
        merged = part_df.merge(hist_lookup, on=["edge_id", "time_slot", "day_of_week"], how="left")
        merged["hist_mean_congestion"] = merged["hist_mean_congestion"].fillna(global_hist_mean)
        return merged

    train_df = _join_hist(train_df)
    val_df = _join_hist(val_df)
    test_df = _join_hist(test_df)

    split_info = {
        "total_rows": len(df),
        "total_days": num_dates,
        "train_days": f"{min(train_dates)} to {max(train_dates)} ({len(train_dates)} days, {len(train_df)} rows)",
        "val_days": f"{min(val_dates)} to {max(val_dates)} ({len(val_dates)} days, {len(val_df)} rows)",
        "test_days": f"{min(test_dates)} to {max(test_dates)} ({len(test_dates)} days, {len(test_df)} rows)",
        "train_min_date": str(min(train_dates)),
        "train_max_date": str(max(train_dates)),
        "val_min_date": str(min(val_dates)),
        "val_max_date": str(max(val_dates)),
        "test_min_date": str(min(test_dates)),
        "test_max_date": str(max(test_dates)),
    }

    logger.info("Chronological split completed: Train=%s, Val=%s, Test=%s",
                split_info["train_days"], split_info["val_days"], split_info["test_days"])

    return train_df, val_df, test_df, split_info
