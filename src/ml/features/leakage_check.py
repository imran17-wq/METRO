"""
src/ml/features/leakage_check.py

Target leakage registry and verification module.
Documents every feature as KNOWN_BEFORE_PREDICTION or TARGET_LEAKAGE_RISK.
The training pipeline rejects any feature marked as TARGET_LEAKAGE_RISK.
"""
from typing import Dict, List, Tuple

LEAKAGE_REGISTRY: Dict[str, Tuple[str, str]] = {
    # ── SAFE FEATURES (KNOWN_BEFORE_PREDICTION) ─────────────────────────────
    "hour": ("KNOWN_BEFORE_PREDICTION", "Derived from timestamp hour (0-23)"),
    "minute_bucket": ("KNOWN_BEFORE_PREDICTION", "Derived from timestamp slot (0, 15, 30, 45)"),
    "time_slot": ("KNOWN_BEFORE_PREDICTION", "15-minute slot index (24-89)"),
    "day_of_week": ("KNOWN_BEFORE_PREDICTION", "Day of week (0=Mon .. 6=Sun)"),
    "is_weekend": ("KNOWN_BEFORE_PREDICTION", "Binary indicator derived from date"),
    "is_peak_slot": ("KNOWN_BEFORE_PREDICTION", "Binary indicator derived from hour (AM/PM peak)"),
    "line_enc": ("KNOWN_BEFORE_PREDICTION", "Label-encoded line name"),
    "edge_enc": ("KNOWN_BEFORE_PREDICTION", "Label-encoded edge ID"),
    "station_enc": ("KNOWN_BEFORE_PREDICTION", "Label-encoded station ID"),
    "is_interchange_edge": ("KNOWN_BEFORE_PREDICTION", "Static edge metadata from graph topology"),
    "capacity": ("KNOWN_BEFORE_PREDICTION", "Static edge capacity metadata"),
    "lag1_congestion_pct": ("KNOWN_BEFORE_PREDICTION", "Previous slot (T-1) congestion value"),
    "lag2_congestion_pct": ("KNOWN_BEFORE_PREDICTION", "Two slots prior (T-2) congestion value"),
    "roll3_mean_congestion": ("KNOWN_BEFORE_PREDICTION", "Rolling 3-slot mean of past congestion values"),
    "roll6_mean_congestion": ("KNOWN_BEFORE_PREDICTION", "Rolling 6-slot mean of past congestion values"),
    "hist_mean_congestion": ("KNOWN_BEFORE_PREDICTION", "Historical average computed from training set only"),
    "hist_delay_rate": ("KNOWN_BEFORE_PREDICTION", "Historical delay event rate from training set only"),
    "scheduled_time_min": ("KNOWN_BEFORE_PREDICTION", "Base scheduled travel time (2.5 min for segment edges)"),

    # ── TARGET LEAKAGE FEATURES (REJECTED) ───────────────────────────────────
    "congestion_pct": ("TARGET_LEAKAGE_RISK", "Target variable itself (congestion percentage at time T)"),
    "congestion_band": ("TARGET_LEAKAGE_RISK", "Directly derived from target variable at time T"),
    "flow_passengers": ("TARGET_LEAKAGE_RISK", "Passenger flow at time T (used to compute congestion_pct)"),
    "delay_min": ("TARGET_LEAKAGE_RISK", "Future delay duration at time T"),
    "has_delay": ("TARGET_LEAKAGE_RISK", "Future delay occurrence at time T"),
    "travel_time_min": ("TARGET_LEAKAGE_RISK", "Target variable for travel time model"),
}


def is_feature_safe(feature_name: str) -> bool:
    """Return True if feature is KNOWN_BEFORE_PREDICTION."""
    info = LEAKAGE_REGISTRY.get(feature_name)
    if not info:
        # Unknown feature -- raise warning or treat cautiously
        return False
    return info[0] == "KNOWN_BEFORE_PREDICTION"


def validate_features(feature_names: List[str]) -> None:
    """
    Validate that no feature in feature_names is marked as TARGET_LEAKAGE_RISK.
    Raises ValueError with detailed reasoning if leakage is detected.
    """
    leakage_found = []
    for f in feature_names:
        info = LEAKAGE_REGISTRY.get(f)
        if info and info[0] == "TARGET_LEAKAGE_RISK":
            leakage_found.append((f, info[1]))

    if leakage_found:
        details = "\n".join([f"  - '{name}': {reason}" for name, reason in leakage_found])
        raise ValueError(
            f"TARGET LEAKAGE DETECTED! The following features cannot be used during training:\n{details}"
        )


def get_safe_features() -> List[str]:
    """Return a list of all safe feature names."""
    return [name for name, (status, _) in LEAKAGE_REGISTRY.items() if status == "KNOWN_BEFORE_PREDICTION"]
