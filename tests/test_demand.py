"""
tests/test_demand.py

Unit tests for the Phase 2 synthetic demand generation engine.

Tests verify:
- Reproducibility (same seed → same output)
- Demand positivity
- Temporal patterns (peak > off-peak)
- Station coverage
- Congestion calculation correctness
- Seed behavior (different seeds → different outputs)
- No impossible percentages
- Weekend differs from weekday
- Event day creates localized surge
"""
import sys
from pathlib import Path
from datetime import date

import pytest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ---------------------------------------------------------------------------
# Temporal module tests
# ---------------------------------------------------------------------------

class TestTemporalCurves:
    def test_weekday_has_96_slots(self):
        from src.demand.temporal import weekday_curve
        curve = weekday_curve()
        assert len(curve) == 96

    def test_weekday_peak_greater_than_offpeak(self):
        from src.demand.temporal import weekday_curve
        curve = weekday_curve()
        # Slot 37 ≈ 09:15 (morning peak)
        # Slot 20 ≈ 05:00 (pre-service)
        assert curve[37] > curve[10]

    def test_weekday_service_closed_early_hours(self):
        from src.demand.temporal import weekday_curve, OPERATION_START_SLOT
        curve = weekday_curve()
        assert all(curve[s] == 0.0 for s in range(OPERATION_START_SLOT))

    def test_weekend_flatter_than_weekday(self):
        from src.demand.temporal import weekday_curve, weekend_curve
        wday = weekday_curve()
        wend = weekend_curve()
        # Weekend max should be less than weekday max (in absolute terms)
        # and peak should be later (morning peak slots lower for weekend)
        morning_peak_slot = 37  # 09:15
        assert wend[morning_peak_slot] < wday[morning_peak_slot]

    def test_holiday_lower_than_weekday(self):
        from src.demand.temporal import weekday_curve, holiday_curve
        wday = weekday_curve()
        hday = holiday_curve()
        # Holiday total demand should be substantially lower
        assert sum(hday) < sum(wday) * 0.9

    def test_event_curve_has_late_surge(self):
        from src.demand.temporal import event_curve, weekday_curve
        event = event_curve()
        wday = weekday_curve()
        # Evening slots 68..73 should be boosted relative to weekday
        evening_slots = range(68, 74)
        assert sum(event[s] for s in evening_slots) >= sum(wday[s] for s in evening_slots)

    def test_slot_labels(self):
        from src.demand.temporal import slot_label
        assert slot_label(0) == "00:00"
        assert slot_label(24) == "06:00"
        assert slot_label(34) == "08:30"
        assert slot_label(95) == "23:45"

    def test_is_peak_slot_morning(self):
        from src.demand.temporal import is_peak_slot
        assert is_peak_slot(34)  # 08:30
        assert is_peak_slot(38)  # 09:30
        assert not is_peak_slot(48)  # 12:00

    def test_is_peak_slot_evening(self):
        from src.demand.temporal import is_peak_slot
        assert is_peak_slot(72)  # 18:00
        assert is_peak_slot(78)  # 19:30


# ---------------------------------------------------------------------------
# Gravity model tests
# ---------------------------------------------------------------------------

class TestGravityModel:
    @pytest.fixture(scope="class")
    def graph_and_ids(self, request):
        from src.graph.metro_graph import build_metro_graph
        from src.graph import metro_graph as mg
        G = build_metro_graph()
        ids = list(mg._stations.keys())
        request.cls._G = G
        request.cls._ids = ids
        return G, ids

    def test_hop_distances_positive(self, graph_and_ids):
        from src.demand.gravity_model import compute_hop_distances
        G, ids = graph_and_ids
        distances = compute_hop_distances(G, ids[:10])
        assert all(v > 0 for v in distances.values())

    def test_gravity_demand_positive(self, graph_and_ids):
        from src.demand.gravity_model import (
            compute_hop_distances, compute_gravity_base_demand
        )
        G, ids = graph_and_ids
        distances = compute_hop_distances(G, ids)
        demand = compute_gravity_base_demand(ids, distances)
        assert all(v >= 0 for v in demand.values())

    def test_gravity_no_self_demand(self, graph_and_ids):
        from src.demand.gravity_model import (
            compute_hop_distances, compute_gravity_base_demand
        )
        G, ids = graph_and_ids
        distances = compute_hop_distances(G, ids)
        demand = compute_gravity_base_demand(ids, distances)
        assert all(o != d for (o, d) in demand.keys())

    def test_transit_hub_higher_demand(self, graph_and_ids):
        """Transit hubs should generate more demand than peripheral residential."""
        from src.demand.gravity_model import (
            compute_hop_distances, compute_gravity_base_demand
        )
        G, ids = graph_and_ids
        distances = compute_hop_distances(G, ids)
        demand = compute_gravity_base_demand(ids, distances)
        # Majestic Purple (PL22, transit_hub) sum > e.g. Channasandra (PL02, residential) sum
        majestic_total = sum(v for (o, d), v in demand.items() if o == "PL22")
        channasandra_total = sum(v for (o, d), v in demand.items() if o == "PL02")
        assert majestic_total > channasandra_total


# ---------------------------------------------------------------------------
# Congestion tests
# ---------------------------------------------------------------------------

class TestCongestion:
    def test_congestion_band_low(self):
        from src.demand.congestion import congestion_band
        assert congestion_band(30.0) == "LOW"

    def test_congestion_band_medium(self):
        from src.demand.congestion import congestion_band
        assert congestion_band(65.0) == "MEDIUM"

    def test_congestion_band_high(self):
        from src.demand.congestion import congestion_band
        assert congestion_band(90.0) == "HIGH"

    def test_congestion_band_critical(self):
        from src.demand.congestion import congestion_band
        assert congestion_band(120.0) == "CRITICAL"

    def test_slot_capacity_peak_gt_offpeak(self):
        from src.demand.congestion import slot_capacity
        peak_cap = slot_capacity(37)      # 09:15 — peak
        offpeak_cap = slot_capacity(50)   # 12:30 — off-peak
        assert peak_cap > offpeak_cap

    def test_edge_flow_positive(self):
        from src.demand.congestion import compute_edge_flows
        od = {("PL01", "PL05"): 100.0}
        paths = {("PL01", "PL05"): ["PL01", "PL02", "PL03", "PL04", "PL05"]}
        flows = compute_edge_flows(od, paths)
        assert len(flows) == 4
        assert all(v == 100.0 for v in flows.values())

    def test_congestion_pct_no_negative(self):
        from src.demand.congestion import compute_congestion_records
        recs = compute_congestion_records(
            {("PL01", "PL02"): 0.0}, slot=37, day_type="weekday",
            edge_id_map={("PL01", "PL02"): "E01"},
            edge_line_map={("PL01", "PL02"): "Purple"}
        )
        assert all(r["congestion_pct"] >= 0.0 for r in recs)


# ---------------------------------------------------------------------------
# Pipeline integration tests
# ---------------------------------------------------------------------------

class TestPipeline:
    @pytest.fixture(scope="class")
    def pipeline_output(self, request):
        """Run pipeline for 3 days (Mon/Sat/Sun) and return tables."""
        from src.demand.pipeline import DemandConfig, DemandPipeline
        cfg = DemandConfig(
            seed=42,
            start_date=date(2024, 1, 8),  # Monday
            num_days=3,
        )
        p = DemandPipeline(cfg)
        p.initialise()
        result = p.run(), p
        request.cls._pipeline_output = result
        return result

    def test_od_demand_rows_positive(self, pipeline_output):
        tables, _ = pipeline_output
        assert len(tables["od_demand"]) > 0
        assert all(r["demand"] >= 0 for r in tables["od_demand"])

    def test_all_tables_present(self, pipeline_output):
        tables, _ = pipeline_output
        assert "od_demand" in tables
        assert "edge_load" in tables
        assert "congestion" in tables
        assert "delay_events" in tables
        assert "station_demand" in tables

    def test_data_type_label_synthetic(self, pipeline_output):
        tables, _ = pipeline_output
        for table_name, rows in tables.items():
            for row in rows[:5]:
                assert row.get("data_type") == "SYNTHETIC", (
                    f"Row in {table_name} missing SYNTHETIC label"
                )

    def test_all_station_ids_in_demand(self, pipeline_output):
        from src.graph import metro_graph as mg
        tables, _ = pipeline_output
        station_ids_in_data = {r["station_id"] for r in tables["station_demand"]}
        all_ids = set(mg._stations.keys())
        assert all_ids == station_ids_in_data

    def test_no_impossible_congestion(self, pipeline_output):
        tables, _ = pipeline_output
        for row in tables["congestion"]:
            assert row["congestion_pct"] >= 0.0

    def test_peak_congestion_higher_than_offpeak(self, pipeline_output):
        from src.demand.temporal import is_peak_slot
        tables, _ = pipeline_output
        weekday_cong = [
            r for r in tables["congestion"] if r["day_type"] == "weekday"
        ]
        peak = [r["congestion_pct"] for r in weekday_cong if is_peak_slot(r["time_slot"])]
        offpeak = [r["congestion_pct"] for r in weekday_cong if not is_peak_slot(r["time_slot"])]
        if peak and offpeak:
            assert np.mean(peak) > np.mean(offpeak)

    def test_reproducibility(self):
        """Same seed → identical outputs."""
        from src.demand.pipeline import DemandConfig, DemandPipeline
        cfg = DemandConfig(seed=99, start_date=date(2024, 1, 8), num_days=1)
        p1 = DemandPipeline(cfg)
        p1.initialise()
        tables1 = p1.run()

        p2 = DemandPipeline(cfg)
        p2.initialise()
        tables2 = p2.run()

        # Check total demand is identical
        total1 = sum(r["demand"] for r in tables1["od_demand"])
        total2 = sum(r["demand"] for r in tables2["od_demand"])
        assert abs(total1 - total2) < 0.001

    def test_different_seeds_produce_different_outputs(self):
        """Different seeds → different outputs (noise is working)."""
        from src.demand.pipeline import DemandConfig, DemandPipeline
        cfg1 = DemandConfig(seed=1, start_date=date(2024, 1, 8), num_days=1)
        cfg2 = DemandConfig(seed=2, start_date=date(2024, 1, 8), num_days=1)
        p1 = DemandPipeline(cfg1)
        p1.initialise()
        t1 = p1.run()
        p2 = DemandPipeline(cfg2)
        p2.initialise()
        t2 = p2.run()
        total1 = sum(r["demand"] for r in t1["od_demand"])
        total2 = sum(r["demand"] for r in t2["od_demand"])
        # Must differ — proves noise is seed-dependent
        assert abs(total1 - total2) > 0.001

    def test_weekend_differs_from_weekday(self):
        """Weekend total demand should differ substantially from weekday."""
        from src.demand.pipeline import DemandConfig, DemandPipeline
        cfg = DemandConfig(seed=42, start_date=date(2024, 1, 8), num_days=7)
        p = DemandPipeline(cfg)
        p.initialise()
        tables = p.run()
        # Average weekday demand vs average weekend demand
        weekday_totals = [
            sum(r["demand"] for r in tables["od_demand"] if r["date"] == f"2024-01-0{d}")
            for d in [8, 9, 10]  # Mon, Tue, Wed
        ]
        weekend_totals = [
            sum(r["demand"] for r in tables["od_demand"] if r["date"] in ["2024-01-13", "2024-01-14"])
        ]
        assert weekday_totals and weekend_totals
        avg_weekday = np.mean(weekday_totals)
        total_weekend = weekend_totals[0]
        assert abs(avg_weekday - total_weekend) > avg_weekday * 0.05  # at least 5% different
