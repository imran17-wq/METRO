"""
src/simulation/impact_analysis.py

ImpactAnalyzer — Calculates before (baseline) vs after (disrupted) route deltas
and journey metrics for Phase 5 Disruption Simulation.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.routing.routing_service import (
    RoutingService,
    StationNotFoundError,
    InactiveLineError,
    NoRouteError,
    SameStationError,
)
from src.routing.route import RouteResult

logger = logging.getLogger(__name__)


class ImpactAnalyzer:
    """
    Calculates journey impact metrics by comparing baseline routes against disrupted routes.
    """

    @staticmethod
    def compare_route_impact(
        origin_name: str,
        destination_name: str,
        routing_service: RoutingService,
        network_state_service: Any,
        profile: str = "BALANCED",
        scenario_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compare baseline (un-disrupted) route with disrupted route for a single OD pair.

        Returns dict containing:
          - baseline_route
          - disrupted_route
          - travel_time_change_min
          - travel_time_change_pct
          - congestion_change_pct
          - transfer_change
          - route_changed
          - unreachable
          - recommendation
          - provenance
        """
        # 1. Calculate baseline route (using un-disrupted base state)
        # Backup overlay if active
        overlay_backup = dict(network_state_service.overlay_dict)
        network_state_service.clear_disruption_overlay()

        try:
            baseline_dyn = routing_service.dynamic_route(
                origin_name, destination_name, network_state_service, profile=profile
            )
            baseline_rec = baseline_dyn.recommended
        except Exception as exc:
            # Restore overlay
            network_state_service.apply_disruption_overlay(overlay_backup)
            raise exc

        # 2. Restore disruption overlay to evaluate disrupted route
        network_state_service.apply_disruption_overlay(overlay_backup)

        disrupted_rec: Optional[RouteResult] = None
        unreachable = False
        error_message: Optional[str] = None

        try:
            disrupted_dyn = routing_service.dynamic_route(
                origin_name, destination_name, network_state_service, profile=profile
            )
            disrupted_rec = disrupted_dyn.recommended
        except (NoRouteError, InactiveLineError) as exc:
            unreachable = True
            error_message = str(exc)
        except Exception as exc:
            unreachable = True
            error_message = str(exc)

        # 3. Calculate deltas
        base_tt = baseline_rec.predicted_travel_time or baseline_rec.total_time_min
        base_cg = baseline_rec.predicted_congestion or 15.0
        base_tf = baseline_rec.transfer_count or baseline_rec.interchange_count

        if unreachable or disrupted_rec is None:
            return {
                "origin": origin_name,
                "destination": destination_name,
                "profile": profile,
                "scenario_id": scenario_id,
                "unreachable": True,
                "error_detail": error_message,
                "baseline_route": baseline_rec.to_dict(),
                "disrupted_route": None,
                "travel_time_change_min": None,
                "travel_time_change_pct": None,
                "congestion_change_pct": None,
                "transfer_change": None,
                "route_changed": True,
                "recommendation": f"Route between '{origin_name}' and '{destination_name}' is UNREACHABLE during this disruption scenario.",
                "data_provenance": {
                    "topology": "STATIC_TOPOLOGY_REAL_SOURCE_NETWORK",
                    "scenario": "SIMULATED_SCENARIO",
                    "impact": "DERIVED_SIMULATION_OUTPUT",
                },
            }

        dis_tt = disrupted_rec.predicted_travel_time or disrupted_rec.total_time_min
        dis_cg = disrupted_rec.predicted_congestion or 15.0
        dis_tf = disrupted_rec.transfer_count or disrupted_rec.interchange_count

        time_delta = round(dis_tt - base_tt, 2)
        time_delta_pct = round((time_delta / base_tt) * 100.0, 1) if base_tt > 0 else 0.0
        cong_delta = round(dis_cg - base_cg, 2)
        transfer_delta = dis_tf - base_tf

        route_changed = (
            baseline_rec.station_ids != disrupted_rec.station_ids
        )

        # Build recommendation narrative
        if route_changed:
            if time_delta > 0:
                rec_text = (
                    f"Rerouted around disruption: +{time_delta:.1f} min (+{time_delta_pct:.1f}%), "
                    f"{'same transfers' if transfer_delta == 0 else f'{transfer_delta:+d} transfer(s)'}."
                )
            else:
                rec_text = f"Rerouted to alternative route with equivalent travel time ({dis_tt:.1f} min)."
        else:
            if time_delta > 0:
                rec_text = f"Same route traversed with delay: +{time_delta:.1f} min (+{time_delta_pct:.1f}%)."
            else:
                rec_text = "Route unaffected by current disruption scenario."

        return {
            "origin": origin_name,
            "destination": destination_name,
            "profile": profile,
            "scenario_id": scenario_id,
            "unreachable": False,
            "baseline_route": baseline_rec.to_dict(),
            "disrupted_route": disrupted_rec.to_dict(),
            "baseline_time_min": base_tt,
            "disrupted_time_min": dis_tt,
            "travel_time_change_min": time_delta,
            "travel_time_change_pct": time_delta_pct,
            "baseline_congestion_pct": base_cg,
            "disrupted_congestion_pct": dis_cg,
            "congestion_change_pct": cong_delta,
            "baseline_transfers": base_tf,
            "disrupted_transfers": dis_tf,
            "transfer_change": transfer_delta,
            "route_changed": route_changed,
            "recommendation": rec_text,
            "data_provenance": {
                "topology": "STATIC_TOPOLOGY_REAL_SOURCE_NETWORK",
                "scenario": "SIMULATED_SCENARIO",
                "impact": "DERIVED_SIMULATION_OUTPUT",
            },
        }
