"""
tests/test_ml_network_state.py

Unit tests for NetworkStateBuilder and Pink/Blue null prediction enforcement.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ml.network_state import NetworkStateBuilder, compute_congestion_band


class TestNetworkStateBuilder:
    def test_build_state_structure_and_pink_blue_nulls(self):
        builder = NetworkStateBuilder()
        states = builder.build_state(date_str="2024-01-08", time_slot=36)

        assert len(states) == 127  # Total edges in canonical 5-line graph

        pink_blue_states = [s for s in states if s["line"] in ["Pink", "Blue"]]
        purple_green_yellow_states = [s for s in states if s["line"] in ["Purple", "Green", "Yellow"]]

        assert len(pink_blue_states) == 39  # 17 Pink + 22 Blue
        assert len(purple_green_yellow_states) == 81

        # Enforce User Correction 2: Pink and Blue MUST have null predictions
        for s in pink_blue_states:
            assert s["active"] is False
            assert s["predicted_congestion_pct"] is None
            assert s["predicted_travel_time_min"] is None
            assert s["congestion_band"] is None
            assert s["delay_risk_prob"] is None
            assert s["data_provenance"] == "NO_SYNTHETIC_DATA"

        # Operational lines MUST have active status and synthetic output provenance
        for s in purple_green_yellow_states:
            assert s["active"] is True
            assert s["data_provenance"] == "SYNTHETIC MODEL OUTPUT"

    def test_compute_congestion_band(self):
        assert compute_congestion_band(None) is None
        assert compute_congestion_band(10.0) == "LOW"
        assert compute_congestion_band(35.0) == "MEDIUM"
        assert compute_congestion_band(65.0) == "HIGH"
        assert compute_congestion_band(90.0) == "CRITICAL"
