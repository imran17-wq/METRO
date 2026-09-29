"""
temporal.py — Time-of-day demand profiles for the synthetic demand generator.

DATA PROVENANCE: SYNTHETIC (generative, not fabricated-as-real)
---------------------------------------------------------------
The demand curves are modelled using a mixture-of-Gaussians approximation.

Calibration anchors (documented assumptions):
- Two weekday peaks: morning 08:30–10:00, evening 18:00–20:00.
- Weekend curve: later single peak ~11:00–13:00, flatter.
- Holiday: approximately 40–60% of normal weekday demand.
- Off-peak trough: ~15–25% of peak demand.

These are consistent with general urban-metro patterns reported for Bengaluru
Metro 2025 (BMRCL annual reports, media coverage of overcrowding on
Purple/Green lines at peak hours).  The exact shape is a modelling choice,
not a measured fact.

All values are documented here so the methodology is transparent to reviewers.
"""
from __future__ import annotations

import numpy as np
from typing import Literal, Sequence

# ---------------------------------------------------------------------------
# Slot definitions
# ---------------------------------------------------------------------------

SLOTS_PER_DAY: int = 96          # 24h / 15min
SLOT_MINUTES: int = 15

# First metro service ~06:00, last ~22:00 (approximate BMRCL operating hours).
# Slots 0..23 = 00:00..05:45 — near zero (service not running)
# Slots 24..95 = 06:00..23:45

OPERATION_START_SLOT: int = 24   # 06:00
OPERATION_END_SLOT: int = 89     # 22:15 (last full slot before closing)


def slot_to_hour(slot: int) -> float:
    """Convert a slot index (0..95) to hours since midnight."""
    return slot * SLOT_MINUTES / 60.0


def hour_to_slot(hour: float) -> int:
    """Convert hours since midnight to slot index (clamped to 0..95)."""
    return max(0, min(SLOTS_PER_DAY - 1, int(hour * 60 / SLOT_MINUTES)))


# ---------------------------------------------------------------------------
# Temporal multiplier curves
# ---------------------------------------------------------------------------

def _gaussian(x: np.ndarray, mu: float, sigma: float, amplitude: float) -> np.ndarray:
    return amplitude * np.exp(-0.5 * ((x - mu) / sigma) ** 2)


def weekday_curve() -> np.ndarray:
    """
    96-element array of relative demand multipliers for a typical weekday.

    Two peaks:
    - Morning: centred at 09:15 (slot 37), σ ≈ 40 min (σ ≈ 2.7 slots)
    - Evening: centred at 19:00 (slot 76), σ ≈ 50 min (σ ≈ 3.3 slots)
    Off-peak baseline: 0.18
    Service-closed hours: 0.0
    """
    slots = np.arange(SLOTS_PER_DAY, dtype=float)
    hours = slot_to_hour(slots)

    curve = np.full(SLOTS_PER_DAY, 0.18)   # baseline off-peak

    # Morning peak centred at 09:15
    curve += _gaussian(hours, mu=9.25,  sigma=0.6, amplitude=0.82)
    # Evening peak centred at 19:00
    curve += _gaussian(hours, mu=19.0,  sigma=0.75, amplitude=0.68)
    # Midday minor bump
    curve += _gaussian(hours, mu=13.0,  sigma=0.5,  amplitude=0.12)

    # Service-closed slots
    curve[:OPERATION_START_SLOT] = 0.0
    curve[OPERATION_END_SLOT + 1:] = 0.0

    # Normalise so peak ≈ 1.0
    peak = curve.max()
    if peak > 0:
        curve /= peak

    return curve


def weekend_curve() -> np.ndarray:
    """
    Weekend profile: later, flatter, single midday peak.

    - Peak at 12:30 (slot 50), broader σ ≈ 80 min
    - Off-peak baseline: 0.20
    - Evening mild bump at 17:30
    """
    slots = np.arange(SLOTS_PER_DAY, dtype=float)
    hours = slot_to_hour(slots)

    curve = np.full(SLOTS_PER_DAY, 0.20)
    curve += _gaussian(hours, mu=12.5, sigma=1.3, amplitude=0.55)
    curve += _gaussian(hours, mu=17.5, sigma=0.8, amplitude=0.25)

    curve[:OPERATION_START_SLOT] = 0.0
    curve[OPERATION_END_SLOT + 1:] = 0.0

    peak = curve.max()
    if peak > 0:
        curve /= peak

    return curve


def holiday_curve() -> np.ndarray:
    """
    Holiday profile: 40–55% of normal weekday demand, weekend-like shape.
    """
    return weekend_curve() * 0.47


def event_curve(surge_slots: Sequence[int] = (68, 69, 70, 71, 72, 73)) -> np.ndarray:
    """
    Event-day curve for affected stations.
    Has an additional surge in evening slots (e.g., 17:00–18:30 = slots 68–73).
    Applied ONLY to EVENT_SURGE_STATIONS via multiplicative factor.
    The base curve is the weekday curve.
    """
    base = weekday_curve().copy()
    for s in surge_slots:
        if 0 <= s < SLOTS_PER_DAY:
            base[s] = min(1.0, base[s] + 0.35)
    peak = base.max()
    if peak > 0:
        base /= peak
    return base


# ---------------------------------------------------------------------------
# Day-type resolver
# ---------------------------------------------------------------------------

DayType = Literal["weekday", "weekend", "holiday", "event"]


def get_temporal_curve(day_type: DayType) -> np.ndarray:
    """Return the 96-slot demand multiplier array for the given day type."""
    if day_type == "weekday":
        return weekday_curve()
    elif day_type == "weekend":
        return weekend_curve()
    elif day_type == "holiday":
        return holiday_curve()
    elif day_type == "event":
        return event_curve()
    else:
        raise ValueError(f"Unknown day_type: '{day_type}'.")


# ---------------------------------------------------------------------------
# Slot metadata helpers
# ---------------------------------------------------------------------------

def slot_label(slot: int) -> str:
    """Return 'HH:MM' string for a slot index."""
    hour = (slot * SLOT_MINUTES) // 60
    minute = (slot * SLOT_MINUTES) % 60
    return f"{hour:02d}:{minute:02d}"


def is_peak_slot(slot: int, day_type: DayType = "weekday") -> bool:
    """Return True if the slot falls within a peak period."""
    hour = slot_to_hour(slot)
    if day_type in ("weekday", "event"):
        return (8.0 <= hour <= 10.25) or (17.75 <= hour <= 20.25)
    elif day_type == "weekend":
        return 11.0 <= hour <= 14.0
    return False
