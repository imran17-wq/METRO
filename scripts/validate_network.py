#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/validate_network.py

Run all structural validation checks on the metro graph and emit a
formatted report.  Exits with code 0 on full PASS, 1 on any FAIL.

Run from the project root:

    python scripts/validate_network.py
"""
import io
import logging
import sys
from pathlib import Path

# Force UTF-8 output on Windows terminals that default to cp1252
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.settings import LOG_LEVEL, LOG_FORMAT
from src.graph.metro_graph import build_metro_graph, validate_graph

logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)

# Check labels for display
DISPLAY_NAMES = {
    "self_loops":                "No self-loops",
    "all_edges_valid":           "All edges reference valid stations",
    "no_duplicate_station_ids":  "No duplicate station IDs",
    "sequence_ordering":         "Sequence ordering within lines",
    "all_lines_present":         "All operational lines present",
    "interchange_stations":      "Interchange stations correct",
    "graph_connected":           "Graph fully connected",
    "bidirectional_traversal":   "Bidirectional traversal",
    "no_impossible_connections": "No impossible cross-line connections",
}


def main() -> None:
    logger.info("Building graph ...")
    build_metro_graph()

    logger.info("Running validation checks ...")
    report = validate_graph()
    summary = report.pop("_summary")

    sep = "=" * 60
    print(f"\n{sep}")
    print("  NAMMA PULSE -- NETWORK VALIDATION REPORT")
    print(sep)
    print(f"  Total stations  : {summary['total_nodes']}")
    print(f"  Total edges     : {summary['total_edges']}")
    print(f"  Purple Line     : {summary['purple_stations']} stations")
    print(f"  Green Line      : {summary['green_stations']} stations")
    print(f"  Yellow Line     : {summary['yellow_stations']} stations")
    print(f"  Interchange pts : {summary['interchange_locations']}")
    for name in sorted(summary["interchange_names"]):
        print(f"    * {name}")
    print()
    print("  Checks:")
    print("  " + "-" * 56)

    all_pass = True
    for key, result in report.items():
        label = DISPLAY_NAMES.get(key, key)
        status = result["status"]
        icon = "PASS" if status == "PASS" else "FAIL"
        print(f"  [{icon}] {label:<45} {status}")
        if status != "PASS":
            all_pass = False
            print(f"         --> {result['detail']}")

    print()
    overall = "PASS" if all_pass else "FAIL"
    print(f"  [{'PASS' if all_pass else 'FAIL'}] OVERALL: {overall}")
    print(sep + "\n")

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
