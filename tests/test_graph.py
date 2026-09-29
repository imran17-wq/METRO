"""
tests/test_graph.py
Unit tests for the single canonical 5-line graph construction, line status metadata,
and dynamic line activation/deactivation without graph rebuilding.
"""
import sys
from pathlib import Path

import pytest
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.graph.metro_graph import (
    build_metro_graph,
    get_station,
    get_neighbors,
    get_line_stations,
    get_interchanges,
    get_edge_data,
    validate_graph,
    get_active_lines,
    set_active_lines,
    activate_line,
    deactivate_line,
)
from src.config.settings import ALL_LINES, DEFAULT_ACTIVE_LINES, DEFAULT_INACTIVE_LINES


@pytest.fixture(scope="module")
def G():
    return build_metro_graph()


class TestCanonicalGraphCreation:
    def test_graph_is_networkx_graph(self, G):
        assert isinstance(G, nx.Graph)

    def test_graph_is_undirected(self, G):
        assert not isinstance(G, nx.DiGraph)

    def test_graph_has_nodes_and_edges(self, G):
        assert G.number_of_nodes() > 0
        assert G.number_of_edges() > 0

    def test_all_five_lines_present_in_graph(self, G):
        lines = G.graph["lines"]
        for expected in ("Purple", "Green", "Yellow", "Pink", "Blue"):
            assert expected in lines

    def test_default_line_activity_states(self, G):
        active = get_active_lines()
        assert active == DEFAULT_ACTIVE_LINES
        assert "Purple" in active
        assert "Green" in active
        assert "Yellow" in active
        assert "Pink" not in active
        assert "Blue" not in active

    def test_line_status_metadata_on_nodes(self, G):
        pink_records = get_line_stations("Pink")
        assert pink_records is not None
        for s in pink_records:
            node_data = G.nodes[s.station_id]
            assert node_data["line_status"] == "UNDER_CONSTRUCTION"

        purple_records = get_line_stations("Purple")
        assert purple_records is not None
        for s in purple_records:
            node_data = G.nodes[s.station_id]
            assert node_data["line_status"] == "OPERATIONAL"


class TestTopologyPersistenceOnStateChange:
    def test_activating_line_does_not_rebuild_graph(self, G):
        initial_nodes = G.number_of_nodes()
        initial_edges = G.number_of_edges()
        initial_graph_id = id(G)

        activate_line("Pink")
        assert "Pink" in get_active_lines()

        # Graph object identity and structure must remain identical
        assert G.number_of_nodes() == initial_nodes
        assert G.number_of_edges() == initial_edges
        assert id(G) == initial_graph_id

        # Reset back to default
        deactivate_line("Pink")
        assert "Pink" not in get_active_lines()

    def test_deactivating_line_does_not_rebuild_graph(self, G):
        initial_nodes = G.number_of_nodes()
        initial_edges = G.number_of_edges()

        deactivate_line("Yellow")
        assert "Yellow" not in get_active_lines()
        assert G.number_of_nodes() == initial_nodes
        assert G.number_of_edges() == initial_edges

        # Restore default active lines
        set_active_lines(DEFAULT_ACTIVE_LINES)


class TestStationAndEdgeLookups:
    def test_get_existing_station(self, G):
        result = get_station("Indiranagar")
        assert result is not None
        assert len(result) == 1
        assert result[0].line == "Purple"

    def test_get_interchange_station(self, G):
        result = get_station("Nadaprabhu Kempegowda Station (Majestic)")
        assert result is not None
        assert len(result) == 2
        lines = {s.line for s in result}
        assert lines == {"Purple", "Green"}

    def test_get_edge_existing(self, G):
        data = get_edge_data("Indiranagar", "Trinity")
        assert data is not None
        assert data["line"] == "Purple"

    def test_interchange_has_transfer_edge(self, G):
        assert G.has_edge("PL22", "GL17") or G.has_edge("GL17", "PL22")
        data = dict(G["PL22"]["GL17"]) if G.has_edge("PL22", "GL17") else dict(G["GL17"]["PL22"])
        assert data["line"] == "TRANSFER"


class TestValidation:
    def test_validate_graph_passes(self, G):
        report = validate_graph()
        summary = report["_summary"]
        assert summary["overall"] == "PASS"
