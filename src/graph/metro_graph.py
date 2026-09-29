"""
Core metro graph builder and query API for Namma Pulse.
Single Canonical 5-Line Graph Architecture (Purple, Green, Yellow, Pink, Blue).
Line active/inactive states are managed dynamically without rebuilding the graph.
"""
from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import networkx as nx

from src.graph.station_model import Station
from src.graph.edge_model import Edge
from src.config.settings import (
    DATA_DIR,
    ALL_LINES,
    DEFAULT_ACTIVE_LINES,
    LINE_METADATA,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------
_graph: Optional[nx.Graph] = None
_stations: Dict[str, Station] = {}          # station_id → Station
_name_index: Dict[str, List[str]] = {}      # canonical_name → [station_ids]
_line_index: Dict[str, List[str]] = {}      # line → [station_ids]
_interchange_ids: List[str] = []            # station_ids that are interchanges
_active_lines: Set[str] = set(DEFAULT_ACTIVE_LINES)  # Dynamic active line state


# ---------------------------------------------------------------------------
# Dynamic Line State Management (No graph rebuild required)
# ---------------------------------------------------------------------------

def get_active_lines() -> Set[str]:
    return set(_active_lines)


def set_active_lines(lines: Set[str]) -> None:
    global _active_lines
    _active_lines = set(lines)
    logger.info("Active lines set to: %s", sorted(list(_active_lines)))


def activate_line(line: str) -> None:
    global _active_lines
    if line in ALL_LINES:
        _active_lines.add(line)
        logger.info("Line activated: %s", line)


def deactivate_line(line: str) -> None:
    global _active_lines
    _active_lines.discard(line)
    logger.info("Line deactivated: %s", line)


# ---------------------------------------------------------------------------
# CSV loaders
# ---------------------------------------------------------------------------

def _load_stations(csv_path: Path) -> List[Station]:
    stations: List[Station] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            line = row["line"].strip()
            is_interchange = row["is_interchange"].strip().lower() == "true"
            interchange_lines = (
                [ln.strip() for ln in row["interchange_lines"].split("|")]
                if row["interchange_lines"].strip()
                else []
            )
            s = Station(
                station_id=row["station_id"].strip(),
                station_name=row["station_name"].strip(),
                line=line,
                sequence=int(row["sequence"].strip()),
                is_interchange=is_interchange,
                interchange_lines=interchange_lines,
                notes=row.get("notes", "").strip(),
            )
            stations.append(s)
    return stations


def _load_edges(csv_path: Path) -> List[Edge]:
    edges: List[Edge] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dist_raw = row.get("distance_km", "NA").strip()
            time_raw = row.get("scheduled_time_min", "NA").strip()
            e = Edge(
                edge_id=row["edge_id"].strip(),
                from_station_id=row["from_station_id"].strip(),
                to_station_id=row["to_station_id"].strip(),
                from_station_name=row["from_station_name"].strip(),
                to_station_name=row["to_station_name"].strip(),
                line=row["line"].strip(),
                sequence=int(row["sequence"].strip()),
                distance_km=float(dist_raw) if dist_raw not in ("NA", "", "None") else None,
                scheduled_time_min=float(time_raw) if time_raw not in ("NA", "", "None") else None,
                notes=row.get("notes", "").strip(),
            )
            edges.append(e)
    return edges


# ---------------------------------------------------------------------------
# Interchange cross-edges
# ---------------------------------------------------------------------------

def _add_interchange_edges(G: nx.Graph, stations: List[Station]) -> None:
    """Add platform transfer edges for shared physical station names."""
    name_to_ids: Dict[str, List[str]] = {}
    for s in stations:
        name_to_ids.setdefault(s.canonical_name, []).append(s.station_id)

    transfer_count = 0
    for name, ids in name_to_ids.items():
        if len(ids) > 1:
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    a, b = ids[i], ids[j]
                    if not G.has_edge(a, b):
                        G.add_edge(
                            a, b,
                            edge_id=f"XFER_{a}_{b}",
                            line="TRANSFER",
                            sequence=0,
                            distance_km=0.0,
                            scheduled_time_min=3.0,
                            predicted_travel_time=None,
                            congestion_penalty=None,
                            disruption_status=None,
                            reliability_score=None,
                            notes=f"Platform transfer: {name}",
                        )
                        transfer_count += 1
    logger.debug("Added %d interchange transfer edges.", transfer_count)


# ---------------------------------------------------------------------------
# Public Graph Builder (ONE Canonical 5-Line Graph)
# ---------------------------------------------------------------------------

def build_metro_graph(
    stations_csv: Optional[Path] = None,
    edges_csv: Optional[Path] = None,
) -> nx.Graph:
    """Build the single canonical 5-line NetworkX graph."""
    global _graph, _stations, _name_index, _line_index, _interchange_ids

    stations_csv = stations_csv or DATA_DIR / "processed" / "stations.csv"
    edges_csv = edges_csv or DATA_DIR / "processed" / "edges.csv"

    stations = _load_stations(stations_csv)
    edges = _load_edges(edges_csv)

    G = nx.Graph()
    G.graph["name"] = "Namma Pulse — Canonical Bengaluru Metro Graph"
    G.graph["lines"] = list(ALL_LINES)

    _stations = {}
    _name_index = {}
    _line_index = {}
    _interchange_ids = []

    # Add nodes with status metadata
    for s in stations:
        meta = LINE_METADATA.get(s.line, {"status": "OPERATIONAL", "default_active": True})
        G.add_node(
            s.station_id,
            station_name=s.station_name,
            line=s.line,
            sequence=s.sequence,
            is_interchange=s.is_interchange,
            interchange_lines=s.interchange_lines,
            line_status=meta["status"],
            notes=s.notes,
        )
        _stations[s.station_id] = s
        _name_index.setdefault(s.canonical_name, []).append(s.station_id)
        _line_index.setdefault(s.line, []).append(s.station_id)
        if s.is_interchange:
            _interchange_ids.append(s.station_id)

    # Add line edges
    for e in edges:
        G.add_edge(e.from_station_id, e.to_station_id, **e.to_dict())

    # Add interchange transfer edges
    _add_interchange_edges(G, stations)

    _graph = G
    logger.info(
        "Canonical 5-line graph built: %d nodes, %d edges.",
        G.number_of_nodes(),
        G.number_of_edges(),
    )
    return G


def _require_graph() -> nx.Graph:
    if _graph is None:
        build_metro_graph()
    return _graph  # type: ignore


def get_station(station_name: str) -> Optional[List[Station]]:
    _require_graph()
    hits = _name_index.get(station_name.strip())
    if hits:
        return [_stations[sid] for sid in hits]
    lower_query = station_name.strip().lower()
    for name, ids in _name_index.items():
        if name.lower() == lower_query:
            return [_stations[sid] for sid in ids]
    return None


def get_neighbors(station_name: str) -> Optional[List[Station]]:
    G = _require_graph()
    records = get_station(station_name)
    if not records:
        return None
    neighbour_ids: set = set()
    for s in records:
        neighbour_ids.update(G.neighbors(s.station_id))
    return [_stations[sid] for sid in neighbour_ids]


def get_line_stations(line: str) -> Optional[List[Station]]:
    _require_graph()
    ids = _line_index.get(line)
    if ids is None:
        return None
    return sorted([_stations[sid] for sid in ids], key=lambda s: s.sequence)


def get_interchanges() -> List[Station]:
    _require_graph()
    return [_stations[sid] for sid in _interchange_ids]


def get_edge_data(
    from_station_name: str,
    to_station_name: str,
) -> Optional[Dict[str, Any]]:
    G = _require_graph()
    from_records = get_station(from_station_name)
    to_records = get_station(to_station_name)
    if not from_records or not to_records:
        return None
    for f in from_records:
        for t in to_records:
            if G.has_edge(f.station_id, t.station_id):
                return dict(G[f.station_id][t.station_id])
    return None


def validate_graph() -> Dict[str, Any]:
    from src.graph.validation import run_all_checks
    return run_all_checks(_require_graph(), _stations, _name_index, _line_index)
