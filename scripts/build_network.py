#!/usr/bin/env python
"""
scripts/build_network.py

Entry-point script: builds the Bengaluru Metro graph from CSV data and
prints a summary.  Run from the project root:

    python scripts/build_network.py
"""
import logging
import sys
from pathlib import Path

# Make src importable when running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.settings import LOG_LEVEL, LOG_FORMAT
from src.graph.metro_graph import build_metro_graph

logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Building Namma Pulse metro graph …")
    G = build_metro_graph()

    print("\n" + "=" * 60)
    print("  NAMMA PULSE – Network Build Summary")
    print("=" * 60)
    print(f"  Graph name   : {G.graph['name']}")
    print(f"  Phase        : {G.graph['phase']}")
    print(f"  Lines        : {', '.join(G.graph['lines'])}")
    print(f"  Total nodes  : {G.number_of_nodes()}")
    print(f"  Total edges  : {G.number_of_edges()}")
    print("=" * 60)
    print("\nGraph built successfully. Run validate_network.py to validate.\n")


if __name__ == "__main__":
    main()
