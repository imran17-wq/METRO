"""
src/config/routing_weights.py

Configurable routing weights and profile definitions for Phase 4 Intelligent
Dynamic Rerouting.

All weight constants live here — nothing is hard-coded in routing logic.

NORMALIZATION APPROACH
----------------------
Components are placed on compatible minute-equivalent scales before weighting:

  travel_time_score   = predicted_travel_time_min
      → already in minutes; natural scale

  congestion_score    = (predicted_congestion_pct / 100.0) * CONGESTION_SCALE_MIN
      → at 100% congestion → CONGESTION_SCALE_MIN minute penalty (default 5.0)
      → at 0% congestion  → 0.0 minute penalty

  delay_score         = delay_risk_prob * DELAY_SCALE_MIN
      → at probability 1.0 → DELAY_SCALE_MIN minute penalty (default 10.0)
      → at probability 0.0 → 0.0 minute penalty

  transfer_score      = transfer_count * TRANSFER_BASE_MIN
      → each transfer adds TRANSFER_BASE_MIN minutes (default 3.0) before
        profile weighting

Profile weight multipliers are then applied to each component:
  total_cost = (w_t * travel_time_score
              + w_c * congestion_score
              + w_d * delay_score
              + w_r * transfer_score)

This ensures all terms are in compatible (minute-equivalent) units before
any profile weight is applied.
"""
from __future__ import annotations

from typing import Dict

# ---------------------------------------------------------------------------
# Normalization Scale Factors
# ---------------------------------------------------------------------------

#: At 100% congestion the penalty equals this many minutes.
CONGESTION_SCALE_MIN: float = 5.0

#: At delay_risk_prob = 1.0 the penalty equals this many minutes.
DELAY_SCALE_MIN: float = 10.0

#: Base transfer penalty in minutes (before profile weight multiplier).
TRANSFER_BASE_MIN: float = 3.0

# ---------------------------------------------------------------------------
# K — number of candidate routes to generate
# ---------------------------------------------------------------------------
K_CANDIDATES: int = 5

# ---------------------------------------------------------------------------
# Default weights (used as BALANCED baseline)
# ---------------------------------------------------------------------------
ROUTING_WEIGHTS: Dict[str, float] = {
    "travel_time": 1.0,
    "congestion":  0.25,
    "delay_risk":  0.20,
    "transfer":    2.0,
}

# ---------------------------------------------------------------------------
# Route Profile Weight Tables
# ---------------------------------------------------------------------------
# Each profile is a dict of multipliers applied to the normalized components.
# Higher values → that component matters more → routes minimising it are preferred.

ROUTE_PROFILES: Dict[str, Dict[str, float]] = {
    "FASTEST": {
        "travel_time": 2.5,
        "congestion":  0.05,
        "delay_risk":  0.05,
        "transfer":    0.3,
    },
    "BALANCED": {
        "travel_time": 1.0,
        "congestion":  0.25,
        "delay_risk":  0.20,
        "transfer":    2.0,
    },
    "LEAST_CONGESTED": {
        "travel_time": 0.8,
        "congestion":  2.5,
        "delay_risk":  0.5,
        "transfer":    1.0,
    },
    "MOST_RELIABLE": {
        "travel_time": 0.8,
        "congestion":  0.5,
        "delay_risk":  3.0,
        "transfer":    1.0,
    },
    "FEWEST_TRANSFERS": {
        "travel_time": 0.8,
        "congestion":  0.1,
        "delay_risk":  0.1,
        "transfer":    6.0,
    },
}

VALID_PROFILES = frozenset(ROUTE_PROFILES.keys())
DEFAULT_PROFILE = "BALANCED"

# ---------------------------------------------------------------------------
# Fallback baselines (used when ML predictions are unavailable)
# ---------------------------------------------------------------------------

#: Fallback congestion percentage when no ML prediction is available.
FALLBACK_CONGESTION_PCT: float = 15.0

#: Fallback delay risk probability when no ML prediction is available.
FALLBACK_DELAY_RISK: float = 0.02

#: Fallback segment travel time in minutes when no ML prediction is available.
FALLBACK_SEGMENT_TIME_MIN: float = 2.5

#: Fallback transfer time in minutes.
FALLBACK_TRANSFER_TIME_MIN: float = 3.0
