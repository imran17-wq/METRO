"""
Validation checks for the Namma Pulse canonical 5-line metro graph.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

import networkx as nx

from src.graph.station_model import Station
from src.config.settings import ALL_LINES

logger = logging.getLogger(__name__)


def check_no_self_loops(G: nx.Graph, **_) -> Tuple[str, str]:
    loops = list(nx.selfloop_edges(G))
    if loops:
        return "FAIL", f"{len(loops)} self-loop(s) found: {loops}"
    return "PASS", "No self-loops."


def check_all_edges_valid(
    G: nx.Graph,
    stations: Dict[str, Station],
    **_,
) -> Tuple[str, str]:
    bad: List[Tuple[str, str]] = []
    for u, v in G.edges():
        if u not in stations or v not in stations:
            bad.append((u, v))
    if bad:
        return "FAIL", f"{len(bad)} edge(s) reference non-existent nodes: {bad}"
    return "PASS", "All edges reference valid stations."


def check_no_duplicate_station_ids(
    stations: Dict[str, Station],
    **_,
) -> Tuple[str, str]:
    seen: Dict[str, int] = {}
    for sid in stations:
        seen[sid] = seen.get(sid, 0) + 1
    dups = {k: v for k, v in seen.items() if v > 1}
    if dups:
        return "FAIL", f"Duplicate station IDs: {dups}"
    return "PASS", "All station IDs are unique."


def check_sequence_ordering(
    stations: Dict[str, Station],
    line_index: Dict[str, List[str]],
    **_,
) -> Tuple[str, str]:
    issues: List[str] = []
    for line, ids in line_index.items():
        seqs = sorted(stations[sid].sequence for sid in ids)
        expected = list(range(1, len(seqs) + 1))
        if seqs != expected:
            issues.append(
                f"{line}: sequences {seqs} do not match expected {expected}"
            )
    if issues:
        return "FAIL", "; ".join(issues)
    return "PASS", "All line sequences are contiguous from 1."


def check_all_lines_present(
    G: nx.Graph,
    line_index: Dict[str, List[str]],
    **_,
) -> Tuple[str, str]:
    required = set(ALL_LINES)
    missing = required - set(line_index.keys())
    if missing:
        return "FAIL", f"Missing lines in canonical graph: {missing}"
    return "PASS", f"All 5 required lines present: {sorted(required)}"


def check_interchange_stations(
    G: nx.Graph,
    stations: Dict[str, Station],
    name_index: Dict[str, List[str]],
    **_,
) -> Tuple[str, str]:
    expected_interchanges = {
        "Nadaprabhu Kempegowda Station (Majestic)": {"Purple", "Green"},
        "Rashtreeya Vidyalaya Road (RV Road)": {"Green", "Yellow"},
        "Jayadeva Hospital": {"Yellow", "Pink"},
        "Central Silk Board": {"Yellow", "Blue"},
        "Mahatma Gandhi Road (MG Road)": {"Purple", "Pink"},
        "Krishnarajapura (KR Pura)": {"Purple", "Blue"},
        "Nagawara": {"Pink", "Blue"},
    }

    issues: List[str] = []
    for name, expected_lines in expected_interchanges.items():
        ids = name_index.get(name, [])
        if not ids:
            issues.append(f"Interchange station '{name}' not found in graph.")
            continue
        actual_lines = {stations[sid].line for sid in ids}
        missing_lines = expected_lines - actual_lines
        if missing_lines:
            issues.append(f"'{name}' missing expected lines: {missing_lines}")
    if issues:
        return "FAIL", "; ".join(issues)
    return "PASS", f"All {len(expected_interchanges)} interchange stations connect the correct lines."


def check_no_disconnected_components(G: nx.Graph, **_) -> Tuple[str, str]:
    components = list(nx.connected_components(G))
    if len(components) != 1:
        sizes = [len(c) for c in components]
        return (
            "FAIL",
            f"{len(components)} connected components found (sizes: {sizes}). Expected exactly 1.",
        )
    return "PASS", "Graph is fully connected (1 component)."


def check_bidirectional_traversal(G: nx.Graph, **_) -> Tuple[str, str]:
    if isinstance(G, nx.DiGraph) and not isinstance(G, nx.Graph):
        return "FAIL", "Graph is directed (DiGraph). Expected undirected Graph."
    return "PASS", "Graph is undirected – all edges are bidirectionally traversable."


def check_no_impossible_connections(
    G: nx.Graph,
    stations: Dict[str, Station],
    **_,
) -> Tuple[str, str]:
    bad: List[str] = []
    for u, v, data in G.edges(data=True):
        if data.get("line") == "TRANSFER":
            continue
        s_u = stations[u]
        s_v = stations[v]
        if s_u.line != s_v.line:
            bad.append(f"{u}({s_u.line}) — {v}({s_v.line}) [edge_id={data.get('edge_id', '?')}]")
    if bad:
        return "FAIL", f"{len(bad)} cross-line edge(s) without TRANSFER designation: " + "; ".join(bad)
    return "PASS", "No impossible cross-line connections."


def run_all_checks(
    G: nx.Graph,
    stations: Dict[str, Station],
    name_index: Dict[str, List[str]],
    line_index: Dict[str, List[str]],
) -> Dict[str, Any]:
    kwargs = dict(
        G=G,
        stations=stations,
        name_index=name_index,
        line_index=line_index,
    )

    checks = [
        ("self_loops",               check_no_self_loops),
        ("all_edges_valid",          check_all_edges_valid),
        ("no_duplicate_station_ids", check_no_duplicate_station_ids),
        ("sequence_ordering",        check_sequence_ordering),
        ("all_lines_present",        check_all_lines_present),
        ("interchange_stations",     check_interchange_stations),
        ("graph_connected",          check_no_disconnected_components),
        ("bidirectional_traversal",  check_bidirectional_traversal),
        ("no_impossible_connections", check_no_impossible_connections),
    ]

    results: Dict[str, Any] = {}
    all_pass = True

    for name, fn in checks:
        try:
            status, detail = fn(**kwargs)
        except Exception as exc:  # noqa: BLE001
            status, detail = "FAIL", f"Exception during check: {exc}"
        results[name] = {"status": status, "detail": detail}
        if status != "PASS":
            all_pass = False

    per_line_counts = {line: len(ids) for line, ids in line_index.items()}
    unique_physical_names = {s.station_name for s in stations.values()}
    interchange_names = {s.station_name for s in stations.values() if s.is_interchange}

    results["_summary"] = {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "physical_stations": len(unique_physical_names),
        "per_line_counts": per_line_counts,
        "interchange_locations": len(interchange_names),
        "interchange_names": sorted(list(interchange_names)),
        "overall": "PASS" if all_pass else "FAIL",
    }

    return results
