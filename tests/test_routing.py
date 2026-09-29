"""
tests/test_routing.py
Unit tests for routing engine on single canonical 5-line graph with line state filtering.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.graph.metro_graph import build_metro_graph
from src.routing.dijkstra_router import find_dijkstra_route
from src.routing.astar_router import find_astar_route
from src.routing.routing_service import (
    RoutingService,
    StationNotFoundError,
    SameStationError,
    InactiveLineError,
    NoRouteError,
)
from src.config.settings import DEFAULT_ACTIVE_LINES


@pytest.fixture(scope="module")
def graph_and_stations():
    G = build_metro_graph()
    from src.graph import metro_graph as mg
    return G, dict(mg._stations)


@pytest.fixture(scope="function")
def service():
    svc = RoutingService()
    svc.initialise()
    svc.set_active_lines(set(DEFAULT_ACTIVE_LINES))
    yield svc
    svc.set_active_lines(set(DEFAULT_ACTIVE_LINES))


class TestNormalRoutingActiveLines:
    def test_purple_indiranagar_to_mgroad(self, service):
        result = service.route("Indiranagar", "MG Road", "dijkstra")
        assert result is not None
        assert "Indiranagar" in result.origin
        assert "MG Road" in result.destination
        assert result.interchange_count == 0

    def test_green_madavara_to_nagasandra(self, service):
        result = service.route("Madavara", "Nagasandra", "dijkstra")
        assert result is not None
        assert result.interchange_count == 0

    def test_cross_line_purple_to_green(self, service):
        result = service.route("Whitefield (Kadugodi)", "Silk Institute", "dijkstra")
        assert result is not None
        assert result.interchange_count == 1
        assert any("Majestic" in x for x in result.interchange_stations)


class TestInactiveLineExclusionAndActivation:
    def test_inactive_pink_line_raises_inactive_error(self, service):
        # Kalena Agrahara is on Pink line (inactive by default)
        with pytest.raises((InactiveLineError, NoRouteError)) as exc_info:
            service.route("Kalena Agrahara", "MG Road", "dijkstra")
        assert "inactive" in str(exc_info.value).lower() or "under construction" in str(exc_info.value).lower()

    def test_inactive_blue_line_raises_inactive_error(self, service):
        # KIA Airport is on Blue line (inactive by default)
        with pytest.raises((InactiveLineError, NoRouteError)) as exc_info:
            service.route("KIA Airport", "Indiranagar", "dijkstra")
        assert "inactive" in str(exc_info.value).lower() or "under construction" in str(exc_info.value).lower()

    def test_activating_pink_line_makes_it_routable(self, service):
        # Before activation: fails
        with pytest.raises((InactiveLineError, NoRouteError)):
            service.route("Kalena Agrahara", "MG Road", "dijkstra")

        # Activate Pink Line dynamically (no graph rebuild)
        service.activate_line("Pink")

        # After activation: succeeds!
        result = service.route("Kalena Agrahara", "MG Road", "dijkstra")
        assert result is not None
        assert "Pink" in result.lines

    def test_activating_blue_line_makes_it_routable(self, service):
        service.activate_line("Blue")
        result = service.route("KIA Airport", "KR Pura", "dijkstra")
        assert result is not None
        assert "Blue" in result.lines

    def test_deactivating_line_removes_route_eligibility(self, service):
        # Deactivate Yellow line
        service.deactivate_line("Yellow")

        # RV Road to Bommasandra requires Yellow line
        with pytest.raises((InactiveLineError, NoRouteError)):
            service.route("Rashtreeya Vidyalaya Road (RV Road)", "Bommasandra", "dijkstra")

    def test_transfer_requires_both_lines_active(self, service):
        # Activating ONLY Blue line without Pink line
        service.set_active_lines({"Purple", "Green", "Yellow", "Blue"})

        # Jayadeva Hospital connects Yellow (Active) and Pink (Inactive)
        # Attempting a route from Jayadeva (Yellow) to Hulimavu (Pink) must fail because Pink side of transfer is inactive!
        with pytest.raises((InactiveLineError, NoRouteError)):
            service.route("Jayadeva Hospital", "Hulimavu", "dijkstra")


class TestAStarMatchesDijkstra:
    def test_astar_respects_line_state(self, service):
        d = service.route("Indiranagar", "MG Road", "dijkstra")
        a = service.route("Indiranagar", "MG Road", "astar")
        assert d.total_time_min == pytest.approx(a.total_time_min, rel=1e-6)

        with pytest.raises((InactiveLineError, NoRouteError)):
            service.route("Kalena Agrahara", "MG Road", "astar")
