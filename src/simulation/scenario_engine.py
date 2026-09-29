"""
src/simulation/scenario_engine.py

ScenarioEngine — Manages disruption overlay activation, state modification,
and exact state restoration/recovery for Phase 5 Disruption Simulation.

IMPORTANT
---------
The canonical NetworkX graph topology is NEVER modified or rebuilt.
Disruptions modify per-edge network state attributes via dynamic overlay dicts
managed inside NetworkStateService.
Deactivating a scenario restores the exact base network state.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set

from src.simulation.disruption import Disruption, DisruptionType, Severity
from src.simulation.scenario import Scenario, SCENARIO_LIBRARY, get_scenario

logger = logging.getLogger(__name__)


class ScenarioEngine:
    """
    Orchestrates disruption scenario loading, activation overlays, and recovery state restoration.
    """

    def __init__(self) -> None:
        self._active_scenario: Optional[Scenario] = None
        self._overlay_dict: Dict[str, Dict[str, Any]] = {}

    @property
    def active_scenario(self) -> Optional[Scenario]:
        return self._active_scenario

    @property
    def is_scenario_active(self) -> bool:
        return self._active_scenario is not None

    @property
    def is_active(self) -> bool:
        return self._active_scenario is not None

    @property
    def affected_edges(self) -> Set[str]:
        return set(self._overlay_dict.keys())


    def list_available_scenarios(self) -> List[Dict[str, Any]]:
        """Return list of dicts for all available scenarios in library."""
        return [sc.to_dict() for sc in SCENARIO_LIBRARY.values()]

    def get_scenario_details(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        sc = get_scenario(scenario_id)
        return sc.to_dict() if sc else None

    def activate_scenario(
        self,
        scenario_id_or_obj: Any,
        network_state_service: Any,
        routing_service: Optional[Any] = None,
        operations_engine: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Activate a scenario from the Scenario Library or a custom Scenario object.

        Atomically updates active lines, timetable services, demand profile,
        and disruption overlays.
        """
        if isinstance(scenario_id_or_obj, Scenario):
            sc = scenario_id_or_obj
        else:
            sc = get_scenario(scenario_id_or_obj)

        if sc is None:
            raise ValueError(f"Unknown scenario ID: '{scenario_id_or_obj}'.")

        # Mandatory Correction 4: Zero active lines rejection
        target_lines = sc.active_lines if sc.active_lines is not None else ["Purple", "Green", "Yellow"]
        if not target_lines or len(target_lines) == 0:
            raise ValueError("At least one metro line must remain active in the simulation.")

        # Deactivate any currently active scenario first to prevent cumulative pollution
        if self._active_scenario is not None:
            self.deactivate_scenario(
                network_state_service=network_state_service,
                routing_service=routing_service,
                operations_engine=operations_engine,
            )

        logger.info("Activating disruption scenario: %s (%s)", sc.name, sc.id)

        # 1. Update RoutingService line eligibility
        active_lines_set = set(target_lines)
        if routing_service is not None:
            routing_service.set_active_lines(active_lines_set)

        # 2. Update OperationsEngine simulated train timetable & headway
        if operations_engine is not None:
            operations_engine.set_active_lines(active_lines_set, headway_sec=sc.headway_sec)

        # 3. Refresh NetworkStateService for new active lines
        try:
            network_state_service.refresh(
                date_str=network_state_service.last_date or "2024-01-08",
                time_slot=network_state_service.last_time_slot if network_state_service.last_time_slot is not None else 36,
                active_lines=active_lines_set,
            )
        except Exception as e:
            logger.warning("NetworkState refresh warning during scenario activation: %s", e)

        # 4. Build edge overlay dict from scenario disruptions
        overlay: Dict[str, Dict[str, Any]] = {}
        edge_index = network_state_service.edge_index

        for edge_id, state in edge_index.items():
            line = state.get("line", "")
            u = state.get("from_id", "")
            v = state.get("to_id", "")

            # Evaluate each disruption in the scenario against this edge
            for d in sc.disruptions:
                is_affected = False
                is_closure = (sc.severity == Severity.CRITICAL or d.type in (
                    DisruptionType.STATION_CLOSURE,
                    DisruptionType.LINE_CLOSURE,
                    DisruptionType.EDGE_CLOSURE,
                    DisruptionType.INTERCHANGE_CLOSURE,
                ))

                if d.type == DisruptionType.LINE_CLOSURE:
                    if line in d.affected_lines:
                        is_affected = True

                elif d.type == DisruptionType.EDGE_CLOSURE:
                    if edge_id in d.affected_edges or f"{u}_{v}" in d.affected_edges:
                        is_affected = True

                elif d.type == DisruptionType.INTERCHANGE_CLOSURE:
                    if line == "TRANSFER":
                        for st_target in d.affected_stations:
                            if st_target in (u, v, state.get("from_name"), state.get("to_name")):
                                is_affected = True

                elif d.type == DisruptionType.STATION_CLOSURE:
                    for st in d.affected_stations:
                        if st in (u, v):
                            is_affected = True

                elif d.type in (DisruptionType.SEVERE_DELAY, DisruptionType.CONGESTION_SURGE, DisruptionType.DEMAND_SURGE):
                    for st in d.affected_stations:
                        if st in (u, v):
                            is_affected = True
                    if edge_id in d.affected_edges:
                        is_affected = True

                if is_affected:
                    base_active = state.get("active", True)
                    effective_active = False if is_closure else base_active

                    base_tt = state.get("predicted_travel_time_min") or state.get("scheduled_time_min", 2.5)
                    eff_tt = round(base_tt * d.delay_multiplier, 2) if base_tt else base_tt

                    base_cong = state.get("predicted_congestion_pct") or 15.0
                    mult = d.congestion_multiplier * d.demand_multiplier * sc.demand_multiplier
                    eff_cong = round(min(95.0, base_cong * mult), 2)

                    overlay[edge_id] = {
                        "active": effective_active,
                        "predicted_travel_time_min": eff_tt,
                        "predicted_congestion_pct": eff_cong,
                        "disruption_applied": d.id,
                        "disruption_type": d.type.value if hasattr(d.type, "value") else str(d.type),
                        "data_provenance": "SIMULATED_SCENARIO",
                    }

        # Apply global scenario demand multiplier to non-disrupted edges if demand_multiplier != 1.0
        if sc.demand_multiplier != 1.0:
            for edge_id, state in edge_index.items():
                if edge_id not in overlay and state.get("active", False):
                    base_cong = state.get("predicted_congestion_pct") or 15.0
                    eff_cong = round(min(95.0, base_cong * sc.demand_multiplier), 2)
                    overlay[edge_id] = {
                        "active": True,
                        "predicted_travel_time_min": state.get("predicted_travel_time_min"),
                        "predicted_congestion_pct": eff_cong,
                        "disruption_applied": f"{sc.id}_demand_surge",
                        "disruption_type": "DEMAND_SURGE",
                        "data_provenance": "SIMULATED_SCENARIO",
                    }

        # Store active scenario and apply overlay to NetworkStateService
        sc.active = True
        self._active_scenario = sc
        self._overlay_dict = overlay
        network_state_service.apply_disruption_overlay(overlay)

        if operations_engine is not None:
            operations_engine.update_disruption_state(sc, self.affected_edges)

        logger.info(
            "Scenario '%s' activated: %d active lines, %d edges affected.",
            sc.name, len(active_lines_set), len(overlay)
        )

        return {
            "scenario_id": sc.id,
            "name": sc.name,
            "severity": sc.severity.value if hasattr(sc.severity, "value") else str(sc.severity),
            "active_lines": sorted(list(active_lines_set)),
            "affected_edge_count": len(overlay),
            "status": "ACTIVE",
            "provenance": "SIMULATED SCENARIO",
        }

    def deactivate_scenario(
        self,
        network_state_service: Any,
        routing_service: Optional[Any] = None,
        operations_engine: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Deactivate active scenario and restore exact base operational state.
        """
        sc_id = self._active_scenario.id if self._active_scenario else "UNKNOWN"
        sc_name = self._active_scenario.name if self._active_scenario else "UNKNOWN"

        if self._active_scenario is not None:
            self._active_scenario.active = False
            self._active_scenario = None

        self._overlay_dict = {}

        # 1. Restore base active lines (Purple, Green, Yellow)
        base_lines = {"Purple", "Green", "Yellow"}
        if routing_service is not None:
            routing_service.set_active_lines(base_lines)

        if operations_engine is not None:
            operations_engine.set_active_lines(base_lines, headway_sec=360)
            operations_engine.clock.reset()
            operations_engine.update_disruption_state(None, set())

        # 2. Clear overlay in NetworkStateService & refresh
        network_state_service.clear_disruption_overlay()
        try:
            network_state_service.refresh(
                date_str=network_state_service.last_date or "2024-01-08",
                time_slot=network_state_service.last_time_slot if network_state_service.last_time_slot is not None else 36,
                active_lines=base_lines,
            )
        except Exception as e:
            logger.warning("NetworkState refresh warning during scenario deactivation: %s", e)

        logger.info("Scenario '%s' deactivated. Base network state restored.", sc_name)

        return {
            "scenario_id": sc_id,
            "name": sc_name,
            "status": "DEACTIVATED",
            "state_restored": True,
        }

    def get_simulation_state(self) -> Dict[str, Any]:
        """Return current simulation active state metadata."""
        if self._active_scenario is None:
            return {
                "active_scenario": None,
                "is_active": False,
                "affected_edge_count": 0,
                "provenance": "STATIC_TOPOLOGY_REAL_SOURCE_NETWORK",
            }
        return {
            "active_scenario": self._active_scenario.to_dict(),
            "is_active": True,
            "affected_edge_count": len(self._overlay_dict),
            "provenance": "SIMULATED SCENARIO",
        }
