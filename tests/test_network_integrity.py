"""
tests/test_network_integrity.py
Higher-level network integrity tests for canonical 5-line connectivity, paths, and interchange topology.
"""
import sys
from pathlib import Path

import pytest
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.graph.metro_graph import build_metro_graph, get_station, get_line_stations
from src.graph import metro_graph as mg


@pytest.fixture(scope="module")
def G():
    return build_metro_graph()


class TestConnectivity:
    def test_graph_connected(self, G):
        assert nx.is_connected(G), "Graph is not fully connected."

    def test_single_component(self, G):
        components = list(nx.connected_components(G))
        assert len(components) == 1, (
            f"Expected 1 component, found {len(components)}: "
            f"sizes {[len(c) for c in components]}"
        )

    def test_path_exists_whitefield_to_silk_institute(self, G):
        assert nx.has_path(G, "PL01", "GL32"), "No path from Whitefield to Silk Institute."

    def test_path_exists_whitefield_to_bommasandra(self, G):
        assert nx.has_path(G, "PL01", "YL16"), "No path from Whitefield to Bommasandra."

    def test_path_exists_madavara_to_bommasandra(self, G):
        assert nx.has_path(G, "GL01", "YL16")

    def test_no_isolated_nodes(self, G):
        isolated = list(nx.isolates(G))
        assert not isolated, f"Isolated nodes: {isolated}"

    def test_cross_line_path_kia_airport_to_silk_institute(self, G):
        assert nx.has_path(G, "BL01", "GL32")


class TestInterchangeTopology:
    def test_majestic_connects_purple_and_green(self, G):
        assert G.has_edge("PL22", "GL17") or G.has_edge("GL17", "PL22")

    def test_rv_road_connects_green_and_yellow(self, G):
        assert G.has_edge("GL24", "YL01") or G.has_edge("YL01", "GL24")

    def test_majestic_transfer_edge_metadata(self, G):
        data = dict(G["PL22"]["GL17"]) if G.has_edge("PL22", "GL17") else dict(G["GL17"]["PL22"])
        assert data["line"] == "TRANSFER"
        assert data["distance_km"] == 0.0

    def test_rv_road_transfer_edge_metadata(self, G):
        data = dict(G["GL24"]["YL01"]) if G.has_edge("GL24", "YL01") else dict(G["YL01"]["GL24"])
        assert data["line"] == "TRANSFER"
        assert data["distance_km"] == 0.0

    def test_all_interchange_transfers_exist(self, G):
        assert G.has_edge("YL03", "PK05") or G.has_edge("PK05", "YL03")
        assert G.has_edge("YL05", "BL23") or G.has_edge("BL23", "YL05")
        assert G.has_edge("PL18", "PK11") or G.has_edge("PK11", "PL18")
        assert G.has_edge("PL12", "BL12") or G.has_edge("BL12", "PL12")
        assert G.has_edge("PK18", "BL06") or G.has_edge("BL06", "PK18")


class TestStructuralProperties:
    def test_no_self_loops(self, G):
        loops = list(nx.selfloop_edges(G))
        assert not loops, f"Self-loops detected: {loops}"

    def test_line_edge_counts(self, G):
        counts = {"Purple": 0, "Green": 0, "Yellow": 0, "Pink": 0, "Blue": 0}
        for _, _, data in G.edges(data=True):
            line = data.get("line")
            if line in counts:
                counts[line] += 1
        assert counts["Purple"] == 35
        assert counts["Green"]  == 31
        assert counts["Yellow"] == 15
        assert counts["Pink"]   == 17
        assert counts["Blue"]   == 22
