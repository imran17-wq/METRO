"""
pipeline.py — Orchestrator for the Phase 2 synthetic demand generation pipeline.

DATA PROVENANCE: SYNTHETIC
--------------------------
All output files produced by this pipeline are SYNTHETIC.
Every file contains DATA_TYPE = SYNTHETIC in its metadata rows.

Pipeline steps
--------------
1. Load the Phase 0 metro graph.
2. Build station and edge lookup tables.
3. Pre-compute all-pairs shortest paths (hop-based).
4. Pre-compute gravity-model base demand matrix.
5. For each date in the configured range:
   a. Determine day_type (weekday/weekend/holiday/event).
   b. For each 15-min time slot:
      i. Scale demand by temporal curve + directional weights + noise.
      ii. Apply event surge if applicable.
      iii. Compute edge flows from OD routing.
      iv. Compute congestion from flows.
      v. Generate delay events.
      vi. Accumulate station arrival/departure records.
6. Write all output files to data/synthetic/.

Usage
-----
From project root:

    python scripts/generate_data.py --seed 42 --days 7
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import networkx as nx

from src.graph.metro_graph import build_metro_graph, _stations as _station_registry
from src.demand.temporal import (
    SLOTS_PER_DAY,
    slot_label,
    get_temporal_curve,
    is_peak_slot,
    DayType,
)
from src.demand.gravity_model import (
    compute_hop_distances,
    compute_gravity_base_demand,
    scale_demand_by_time,
    apply_event_surge,
    DECAY_ALPHA,
    DECAY_BETA,
    DAILY_DEMAND_SCALE,
)
from src.demand.congestion import (
    compute_edge_flows,
    compute_congestion_records,
    compute_station_congestion,
    slot_capacity,
)
from src.demand.delay_generator import generate_delay_events
from src.demand.station_characteristics import EVENT_SURGE_STATIONS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class DemandConfig:
    """All tunable parameters for the demand generation pipeline."""

    # Reproducibility
    seed: int = 42

    # Date range
    start_date: date = field(default_factory=lambda: date(2024, 1, 8))  # Mon
    num_days: int = 7

    # Calendar overrides (ISO format strings → day_type)
    holiday_dates: List[str] = field(default_factory=list)
    event_dates: List[str] = field(default_factory=list)

    # Gravity model
    decay_alpha: float = DECAY_ALPHA
    decay_beta: float = DECAY_BETA
    demand_scale: float = DAILY_DEMAND_SCALE

    # Noise
    noise_std: float = 0.10   # ±10% stochastic per slot

    # Output
    output_dir: Path = Path("data/synthetic")

    # Sanity check thresholds
    min_peak_ratio: float = 1.5    # peak demand must be >= 1.5× off-peak mean


# ---------------------------------------------------------------------------
# Pre-computation helpers
# ---------------------------------------------------------------------------

def _build_edge_maps(
    G: nx.Graph,
) -> Tuple[Dict, Dict, set]:
    """
    Build two lookup dicts for edge_id and line, keyed on canonical edge tuples.

    Returns (edge_id_map, edge_line_map, interchange_edge_set)
    """
    edge_id_map: Dict[Tuple[str, str], str] = {}
    edge_line_map: Dict[Tuple[str, str], str] = {}
    interchange_edges: set = set()

    for u, v, data in G.edges(data=True):
        key = (u, v) if u < v else (v, u)
        edge_id_map[key] = data.get("edge_id", f"E_{u}_{v}")
        line = data.get("line", "Unknown")
        edge_line_map[key] = line
        if line == "TRANSFER":
            interchange_edges.add(key)

    return edge_id_map, edge_line_map, interchange_edges


def _precompute_all_paths(
    G: nx.Graph, station_ids: List[str]
) -> Dict[Tuple[str, str], List[str]]:
    """Pre-compute all-pairs shortest paths for flow assignment."""
    logger.info("Pre-computing all-pairs shortest paths for %d nodes...", len(station_ids))
    raw = dict(nx.all_pairs_shortest_path(G))
    paths: Dict[Tuple[str, str], List[str]] = {}
    node_set = set(station_ids)
    for u, target_map in raw.items():
        if u not in node_set:
            continue
        for v, path in target_map.items():
            if v in node_set and u != v:
                paths[(u, v)] = path
    logger.info("Pre-computed %d paths.", len(paths))
    return paths


def _get_day_type(d: date, config: DemandConfig) -> DayType:
    iso = d.isoformat()
    if iso in config.event_dates:
        return "event"
    if iso in config.holiday_dates:
        return "holiday"
    if d.weekday() >= 5:  # Saturday=5, Sunday=6
        return "weekend"
    return "weekday"


# ---------------------------------------------------------------------------
# CSV output helpers
# ---------------------------------------------------------------------------

SYNTHETIC_META = {
    "DATA_TYPE": "SYNTHETIC",
    "METHODOLOGY": "Gravity model + temporal shaping. NOT real ridership data.",
    "PROJECT": "Namma Pulse v1.0",
}


def _write_csv(path: Path, rows: List[Dict], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Wrote %d rows to %s", len(rows), path)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

class DemandPipeline:
    """Orchestrates the full synthetic demand generation."""

    def __init__(self, config: Optional[DemandConfig] = None) -> None:
        self.config = config or DemandConfig()
        self.rng = np.random.default_rng(self.config.seed)
        self.G: Optional[nx.Graph] = None
        self.station_ids: List[str] = []
        self.stations: Dict = {}
        self.hop_distances: Dict = {}
        self.all_paths: Dict = {}
        self.base_demand: Dict = {}
        self.edge_id_map: Dict = {}
        self.edge_line_map: Dict = {}
        self.interchange_edges: set = set()
        self.station_line_map: Dict[str, str] = {}

    def initialise(self) -> None:
        """Load graph and pre-compute expensive structures."""
        logger.info("Initialising demand pipeline (seed=%d)...", self.config.seed)
        self.G = build_metro_graph()

        from src.graph import metro_graph as mg
        self.stations = dict(mg._stations)
        self.station_ids = list(self.stations.keys())
        self.station_line_map = {sid: s.line for sid, s in self.stations.items()}

        self.hop_distances = compute_hop_distances(self.G, self.station_ids)
        self.all_paths = _precompute_all_paths(self.G, self.station_ids)
        self.edge_id_map, self.edge_line_map, self.interchange_edges = (
            _build_edge_maps(self.G)
        )
        self.base_demand = compute_gravity_base_demand(
            self.station_ids,
            self.hop_distances,
            decay_alpha=self.config.decay_alpha,
            decay_beta=self.config.decay_beta,
            scale=self.config.demand_scale,
        )
        logger.info("Pipeline initialised. Ready to generate data.")

    def _get_time_factors(self, slot: int, day_type: DayType):
        """Return (origin_wf, dest_wf) for directional time scaling."""
        from src.demand.temporal import slot_to_hour
        h = slot_to_hour(slot)
        # AM peak: origins strong, destinations strong for work/IT
        if 8.0 <= h < 10.5:
            return 1.0, 0.8
        # Evening peak: destinations strong for home, origins strong from work
        if 17.5 <= h < 20.5:
            return 0.8, 1.0
        return 0.6, 0.6

    def run(self) -> Dict[str, List[Dict]]:
        """
        Run the full pipeline for the configured date range.

        Returns a dict of output table names → list of row dicts.
        """
        cfg = self.config
        od_rows: List[Dict] = []
        edge_rows: List[Dict] = []
        congestion_rows: List[Dict] = []
        delay_rows: List[Dict] = []
        station_demand_rows: List[Dict] = []

        for day_idx in range(cfg.num_days):
            current_date = cfg.start_date + timedelta(days=day_idx)
            day_type = _get_day_type(current_date, cfg)
            date_str = current_date.isoformat()
            temporal_curve = get_temporal_curve(day_type)

            logger.info(
                "Generating data for %s (%s)...", date_str, day_type
            )

            # Daily accumulators for station demand
            station_arrivals: Dict[str, float] = {sid: 0.0 for sid in self.station_ids}
            station_departures: Dict[str, float] = {sid: 0.0 for sid in self.station_ids}

            for slot in range(SLOTS_PER_DAY):
                tf = temporal_curve[slot]
                if tf == 0.0:
                    continue  # Service not running

                slot_str = slot_label(slot)
                orig_wf, dest_wf = self._get_time_factors(slot, day_type)

                slot_od = scale_demand_by_time(
                    self.base_demand,
                    time_factor=tf,
                    origin_weight_factor=orig_wf,
                    dest_weight_factor=dest_wf,
                    station_ids=self.station_ids,
                    noise_rng=self.rng,
                    noise_std=cfg.noise_std,
                )

                if day_type == "event":
                    slot_od = apply_event_surge(slot_od)

                # OD rows
                for (o, d), demand in slot_od.items():
                    if demand < 0.5:
                        continue
                    od_rows.append({
                        "date": date_str,
                        "time_slot": slot,
                        "slot_start": slot_str,
                        "origin_id": o,
                        "origin_name": self.stations[o].station_name,
                        "destination_id": d,
                        "destination_name": self.stations[d].station_name,
                        "demand": round(demand, 1),
                        "day_type": day_type,
                        "data_type": "SYNTHETIC",
                    })
                    # Accumulate station departures/arrivals
                    station_departures[o] = station_departures.get(o, 0.0) + demand
                    station_arrivals[d] = station_arrivals.get(d, 0.0) + demand

                # Edge flows
                edge_flow = compute_edge_flows(slot_od, self.all_paths)

                # Congestion records
                cong_recs = compute_congestion_records(
                    edge_flow, slot, day_type,
                    self.edge_id_map, self.edge_line_map
                )
                for rec in cong_recs:
                    edge_rows.append({
                        "date": date_str,
                        "time_slot": slot,
                        "slot_start": slot_str,
                        "edge_id": rec["edge_id"],
                        "from_id": rec["from_id"],
                        "to_id": rec["to_id"],
                        "line": rec["line"],
                        "flow_passengers": rec["flow_passengers"],
                        "capacity": rec["capacity"],
                        "congestion_pct": rec["congestion_pct"],
                        "congestion_band": rec["congestion_band"],
                        "day_type": day_type,
                        "data_type": "SYNTHETIC",
                    })

                # Station-level congestion
                station_cong = compute_station_congestion(
                    cong_recs, self.station_ids, self.station_line_map
                )
                for sc in station_cong:
                    congestion_rows.append({
                        "date": date_str,
                        "time_slot": slot,
                        "slot_start": slot_str,
                        "station_id": sc["station_id"],
                        "station_name": self.stations[sc["station_id"]].station_name,
                        "line": sc["line"],
                        "congestion_pct": sc["congestion_pct"],
                        "congestion_band": sc["congestion_band"],
                        "day_type": day_type,
                        "data_type": "SYNTHETIC",
                    })

                # Delay events
                delay_events = generate_delay_events(
                    cong_recs, slot, day_type, self.interchange_edges, self.rng
                )
                for ev in delay_events:
                    delay_rows.append({
                        "date": date_str,
                        "time_slot": slot,
                        "slot_start": slot_str,
                        "edge_id": ev["edge_id"],
                        "from_id": ev["from_id"],
                        "to_id": ev["to_id"],
                        "line": ev["line"],
                        "delay_min": ev["delay_min"],
                        "cause": ev["cause"],
                        "congestion_band": ev["congestion_band"],
                        "is_interchange_edge": ev["is_interchange_edge"],
                        "day_type": day_type,
                        "data_type": "SYNTHETIC",
                    })

            # Station demand daily summary rows
            for sid in self.station_ids:
                station_demand_rows.append({
                    "date": date_str,
                    "station_id": sid,
                    "station_name": self.stations[sid].station_name,
                    "line": self.station_line_map[sid],
                    "total_arrivals": round(station_arrivals[sid], 0),
                    "total_departures": round(station_departures[sid], 0),
                    "net_flow": round(station_arrivals[sid] - station_departures[sid], 0),
                    "day_type": day_type,
                    "data_type": "SYNTHETIC",
                })

        return {
            "od_demand": od_rows,
            "edge_load": edge_rows,
            "congestion": congestion_rows,
            "delay_events": delay_rows,
            "station_demand": station_demand_rows,
        }

    def write_outputs(self, tables: Dict[str, List[Dict]]) -> None:
        """Write all output tables to CSV files in the configured output directory."""
        out = self.config.output_dir

        _write_csv(
            out / "od_demand.csv",
            tables["od_demand"],
            ["date", "time_slot", "slot_start", "origin_id", "origin_name",
             "destination_id", "destination_name", "demand", "day_type", "data_type"],
        )
        _write_csv(
            out / "edge_load.csv",
            tables["edge_load"],
            ["date", "time_slot", "slot_start", "edge_id", "from_id", "to_id",
             "line", "flow_passengers", "capacity", "congestion_pct",
             "congestion_band", "day_type", "data_type"],
        )
        _write_csv(
            out / "congestion.csv",
            tables["congestion"],
            ["date", "time_slot", "slot_start", "station_id", "station_name",
             "line", "congestion_pct", "congestion_band", "day_type", "data_type"],
        )
        _write_csv(
            out / "delay_events.csv",
            tables["delay_events"],
            ["date", "time_slot", "slot_start", "edge_id", "from_id", "to_id",
             "line", "delay_min", "cause", "congestion_band",
             "is_interchange_edge", "day_type", "data_type"],
        )
        _write_csv(
            out / "station_demand.csv",
            tables["station_demand"],
            ["date", "station_id", "station_name", "line",
             "total_arrivals", "total_departures", "net_flow", "day_type", "data_type"],
        )

    def generate_summary(self, tables: Dict[str, List[Dict]]) -> Dict:
        """Generate summary statistics for validation."""
        od = tables["od_demand"]
        cong = tables["congestion"]
        edge = tables["edge_load"]

        total_demand = sum(r["demand"] for r in od)
        station_daily = {}
        for r in tables["station_demand"]:
            key = r["station_id"]
            station_daily.setdefault(key, []).append(r["total_arrivals"])

        peak_congestions = [
            r["congestion_pct"] for r in cong
            if is_peak_slot(r["time_slot"])
        ]
        offpeak_congestions = [
            r["congestion_pct"] for r in cong
            if not is_peak_slot(r["time_slot"])
        ]

        weekday_total = sum(
            r["demand"] for r in od if r["day_type"] == "weekday"
        )
        weekend_total = sum(
            r["demand"] for r in od if r["day_type"] == "weekend"
        )

        busiest = sorted(
            station_daily.items(),
            key=lambda x: sum(x[1]),
            reverse=True,
        )[:5]

        return {
            "total_synthetic_passengers": round(total_demand),
            "num_od_rows": len(od),
            "num_edge_rows": len(edge),
            "num_congestion_rows": len(cong),
            "num_delay_events": len(tables["delay_events"]),
            "avg_peak_congestion_pct": round(float(np.mean(peak_congestions)), 2)
            if peak_congestions else 0.0,
            "avg_offpeak_congestion_pct": round(float(np.mean(offpeak_congestions)), 2)
            if offpeak_congestions else 0.0,
            "max_congestion_pct": round(float(np.max(peak_congestions)), 2)
            if peak_congestions else 0.0,
            "weekday_total": round(weekday_total),
            "weekend_total": round(weekend_total),
            "top_5_busiest_stations": [
                {"station_id": sid, "total_arrivals": int(sum(vals))}
                for sid, vals in busiest
            ],
        }
