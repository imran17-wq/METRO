"""
src/simulation/resilience.py

ResilienceEvaluator — Evaluates network-wide resilience metrics, OD sampling,
and targeted cascading demand redistribution for Phase 5 Disruption Simulation.

DESIGN RULES
------------
1. Uses a deterministic representative sample of OD station pairs (default 50,
   max 500) generated with fixed seed 42.
2. Cascading demand redistribution is targeted ONLY on alternative route edges
   receiving rerouted passengers from affected journeys. No global congestion inflating.
3. Computes documented composite Resilience Score (0 to 100).
4. All outputs include data_provenance = DERIVED_SIMULATION_OUTPUT.
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from src.config.simulation_settings import (
    DEFAULT_OD_SAMPLE_SIZE,
    MAX_OD_SAMPLE_SIZE,
    RANDOM_SEED,
    RESILIENCE_SCORE_WEIGHTS,
    SIMULATION_PROVENANCE,
    REROUTE_CONGESTION_INCREMENT_PER_PAIR,
)
from src.routing.routing_service import RoutingService, NoRouteError, InactiveLineError
from src.simulation.scenario import Scenario

logger = logging.getLogger(__name__)


@dataclass
class ODMetric:
    origin: str
    destination: str
    baseline_time: float
    disrupted_time: Optional[float]
    time_delta: Optional[float]
    time_delta_pct: Optional[float]
    baseline_transfers: int
    disrupted_transfers: Optional[int]
    transfer_delta: Optional[int]
    route_changed: bool
    unreachable: bool
    disrupted: bool                    # True if baseline route affected by disruption


@dataclass
class ResilienceMetrics:
    scenario_id: str
    scenario_name: str
    sample_size: int
    seed: int

    # Metric summary
    route_availability_pct: float     # % reachable pairs (0 to 100)
    avg_travel_time_impact_pct: float # Mean % time increase on reachable pairs
    unreachable_od_rate_pct: float   # % unreachable pairs (0 to 100)
    rerouting_success_rate_pct: float # % disrupted pairs successfully rerouted
    avg_transfer_change: float        # Mean change in transfer count
    resilience_score: float           # Composite score 0 to 100

    # Counts
    reachable_count: int
    unreachable_count: int
    disrupted_count: int
    rerouted_count: int

    # Cascading congestion edges receiving rerouted load
    cascading_congestion_edges: List[Dict[str, Any]]

    data_provenance: Dict[str, str] = field(
        default_factory=lambda: dict(SIMULATION_PROVENANCE)
    )

    def to_dict(self) -> dict:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "sample_size": self.sample_size,
            "seed": self.seed,
            "route_availability_pct": round(self.route_availability_pct, 1),
            "avg_travel_time_impact_pct": round(self.avg_travel_time_impact_pct, 1),
            "unreachable_od_rate_pct": round(self.unreachable_od_rate_pct, 1),
            "rerouting_success_rate_pct": round(self.rerouting_success_rate_pct, 1),
            "avg_transfer_change": round(self.avg_transfer_change, 2),
            "resilience_score": round(self.resilience_score, 1),
            "reachable_count": self.reachable_count,
            "unreachable_count": self.unreachable_count,
            "disrupted_count": self.disrupted_count,
            "rerouted_count": self.rerouted_count,
            "cascading_congestion_edges": self.cascading_congestion_edges,
            "data_provenance": self.data_provenance,
        }


class ResilienceEvaluator:
    """
    Evaluates network-level resilience metrics and calculates targeted demand redistribution.
    """

    def __init__(self, routing_service: RoutingService) -> None:
        self.routing_service = routing_service

    def get_representative_od_sample(
        self,
        sample_size: int = DEFAULT_OD_SAMPLE_SIZE,
        seed: int = RANDOM_SEED,
    ) -> List[Tuple[str, str]]:
        """
        Generate a deterministic sample of origin-destination station name pairs.
        Filter to active operational lines to ensure valid baseline routes.
        """
        from src.graph.metro_graph import get_active_lines
        actives = get_active_lines()

        n = min(max(1, sample_size), MAX_OD_SAMPLE_SIZE)
        stations = self.routing_service.all_stations()

        names = [
            s["name"] for s in stations
            if any(l in actives for l in s.get("lines", []))
        ]
        if not names:
            names = [s["name"] for s in stations]

        rng = random.Random(seed)
        sample: List[Tuple[str, str]] = []
        seen: set = set()

        attempts = 0
        max_attempts = n * 100
        while len(sample) < n and attempts < max_attempts:
            attempts += 1
            o = rng.choice(names)
            d = rng.choice(names)
            if o != d and (o, d) not in seen:
                seen.add((o, d))
                sample.append((o, d))

        return sample


    def evaluate_resilience(
        self,
        network_state_service: Any,
        scenario: Scenario,
        sample_size: int = DEFAULT_OD_SAMPLE_SIZE,
        seed: int = RANDOM_SEED,
        profile: str = "BALANCED",
    ) -> ResilienceMetrics:
        """
        Evaluate full scenario resilience metrics across representative OD sample.

        Steps
        -----
        1. Generate deterministic OD sample.
        2. Evaluate baseline route for each OD pair (un-disrupted).
        3. Evaluate disrupted route for each OD pair (with scenario overlay).
        4. Perform Targeted Cascading Demand Redistribution onto alternative edges used by rerouted journeys.
        5. Compute composite Resilience Score and metric summary.
        """
        od_pairs = self.get_representative_od_sample(sample_size=sample_size, seed=seed)

        # ── Step 1: Baseline Route Evaluation ──────────────────────────────
        overlay_backup = dict(network_state_service.overlay_dict)
        network_state_service.clear_disruption_overlay()

        baseline_results: Dict[Tuple[str, str], Optional[Any]] = {}
        for o, d in od_pairs:
            try:
                res = self.routing_service.dynamic_route(o, d, network_state_service, profile=profile)
                baseline_results[(o, d)] = res.recommended
            except Exception:
                baseline_results[(o, d)] = None

        # ── Step 2: Disrupted Route Evaluation ────────────────────────────
        network_state_service.apply_disruption_overlay(overlay_backup)

        od_metrics: List[ODMetric] = []
        rerouted_edge_load: Dict[str, int] = {}  # edge_id -> rerouted journey count

        for o, d in od_pairs:
            base_rec = baseline_results.get((o, d))
            if base_rec is None:
                continue

            base_tt = base_rec.predicted_travel_time or base_rec.total_time_min
            base_tf = base_rec.transfer_count or base_rec.interchange_count

            try:
                dis_dyn = self.routing_service.dynamic_route(o, d, network_state_service, profile=profile)
                dis_rec = dis_dyn.recommended

                dis_tt = dis_rec.predicted_travel_time or dis_rec.total_time_min
                dis_tf = dis_rec.transfer_count or dis_rec.interchange_count

                t_delta = round(dis_tt - base_tt, 2)
                t_delta_pct = round((t_delta / base_tt) * 100.0, 1) if base_tt > 0 else 0.0
                tf_delta = dis_tf - base_tf
                route_changed = (base_rec.station_ids != dis_rec.station_ids)

                is_disrupted = route_changed or (t_delta > 0.5)

                # Record alternative edges for targeted demand redistribution
                if route_changed:
                    for seg in dis_rec.segments:
                        for idx in range(len(seg.station_ids) - 1):
                            u_nid = seg.station_ids[idx]
                            v_nid = seg.station_ids[idx + 1]
                            edge_key = f"{u_nid}_{v_nid}"
                            rerouted_edge_load[edge_key] = rerouted_edge_load.get(edge_key, 0) + 1

                od_metrics.append(ODMetric(
                    origin=o,
                    destination=d,
                    baseline_time=base_tt,
                    disrupted_time=dis_tt,
                    time_delta=t_delta,
                    time_delta_pct=t_delta_pct,
                    baseline_transfers=base_tf,
                    disrupted_transfers=dis_tf,
                    transfer_delta=tf_delta,
                    route_changed=route_changed,
                    unreachable=False,
                    disrupted=is_disrupted,
                ))

            except (NoRouteError, InactiveLineError):
                od_metrics.append(ODMetric(
                    origin=o,
                    destination=d,
                    baseline_time=base_tt,
                    disrupted_time=None,
                    time_delta=None,
                    time_delta_pct=None,
                    baseline_transfers=base_tf,
                    disrupted_transfers=None,
                    transfer_delta=None,
                    route_changed=True,
                    unreachable=True,
                    disrupted=True,
                ))
            except Exception:
                od_metrics.append(ODMetric(
                    origin=o,
                    destination=d,
                    baseline_time=base_tt,
                    disrupted_time=None,
                    time_delta=None,
                    time_delta_pct=None,
                    baseline_transfers=base_tf,
                    disrupted_transfers=None,
                    transfer_delta=None,
                    route_changed=True,
                    unreachable=True,
                    disrupted=True,
                ))

        # ── Step 3: Targeted Cascading Congestion Redistribution ────────────
        cascading_edges: List[Dict[str, Any]] = []
        for e_key, load in rerouted_edge_load.items():
            inc_cong = round(load * REROUTE_CONGESTION_INCREMENT_PER_PAIR, 2)
            cascading_edges.append({
                "edge": e_key,
                "rerouted_passengers_load": load,
                "derived_congestion_increase_pct": inc_cong,
                "data_provenance": "DERIVED_SIMULATION_OUTPUT",
            })
        cascading_edges.sort(key=lambda x: x["rerouted_passengers_load"], reverse=True)

        # ── Step 4: Metric Aggregation ──────────────────────────────────────
        total = len(od_metrics)
        if total == 0:
            return _empty_resilience_metrics(scenario.id, scenario.name, sample_size, seed)

        unreachable_cnt = sum(1 for m in od_metrics if m.unreachable)
        reachable_cnt = total - unreachable_cnt
        disrupted_cnt = sum(1 for m in od_metrics if m.disrupted)
        rerouted_cnt = sum(1 for m in od_metrics if m.disrupted and not m.unreachable and m.route_changed)

        route_avail_pct = (reachable_cnt / total) * 100.0
        unreachable_rate_pct = (unreachable_cnt / total) * 100.0

        reroute_success_pct = (
            (rerouted_cnt / disrupted_cnt * 100.0) if disrupted_cnt > 0 else 100.0
        )

        valid_time_pcts = [m.time_delta_pct for m in od_metrics if m.time_delta_pct is not None]
        avg_tt_impact_pct = (sum(valid_time_pcts) / len(valid_time_pcts)) if valid_time_pcts else 0.0

        valid_tf_deltas = [m.transfer_delta for m in od_metrics if m.transfer_delta is not None]
        avg_tf_change = (sum(valid_tf_deltas) / len(valid_tf_deltas)) if valid_tf_deltas else 0.0

        # ── Step 5: Composite Resilience Score Formula (0 to 100) ───────────
        # Formula:
        #   S_avail = route_avail_pct
        #   S_time  = max(0, 100 - avg_tt_impact_pct * 2)
        #   S_unreach = max(0, 100 - unreachable_rate_pct * 3)
        #   S_reroute = reroute_success_pct
        #
        # score = w_avail * S_avail + w_time * S_time + w_unreach * S_unreach + w_reroute * S_reroute

        w = RESILIENCE_SCORE_WEIGHTS
        s_avail = route_avail_pct
        s_time = max(0.0, 100.0 - (avg_tt_impact_pct * 2.0))
        s_unreach = max(0.0, 100.0 - (unreachable_rate_pct * 3.0))
        s_reroute = reroute_success_pct

        composite_score = (
            w["route_availability"] * s_avail
            + w["travel_time_impact"] * s_time
            + w["unreachable_rate"] * s_unreach
            + w["rerouting_success"] * s_reroute
        )

        return ResilienceMetrics(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            sample_size=total,
            seed=seed,
            route_availability_pct=route_avail_pct,
            avg_travel_time_impact_pct=avg_tt_impact_pct,
            unreachable_od_rate_pct=unreachable_rate_pct,
            rerouting_success_rate_pct=reroute_success_pct,
            avg_transfer_change=avg_tf_change,
            resilience_score=composite_score,
            reachable_count=reachable_cnt,
            unreachable_count=unreachable_cnt,
            disrupted_count=disrupted_cnt,
            rerouted_count=rerouted_cnt,
            cascading_congestion_edges=cascading_edges[:10],  # top 10 impacted edges
        )


def _empty_resilience_metrics(sc_id: str, sc_name: str, sample_size: int, seed: int) -> ResilienceMetrics:
    return ResilienceMetrics(
        scenario_id=sc_id,
        scenario_name=sc_name,
        sample_size=sample_size,
        seed=seed,
        route_availability_pct=100.0,
        avg_travel_time_impact_pct=0.0,
        unreachable_od_rate_pct=0.0,
        rerouting_success_rate_pct=100.0,
        avg_transfer_change=0.0,
        resilience_score=100.0,
        reachable_count=0,
        unreachable_count=0,
        disrupted_count=0,
        rerouted_count=0,
        cascading_congestion_edges=[],
    )
