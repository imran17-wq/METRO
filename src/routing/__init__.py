"""src/routing package — Phase 1 & Phase 4 routing engine."""
from src.routing.route import RouteResult, RouteSegment, DynamicRouteResult
from src.routing.routing_service import RoutingService
from src.routing.network_state_service import NetworkStateService
from src.routing.edge_cost import DynamicCostCalculator, RouteEdgeCost
from src.routing.candidate_generator import CandidateRouteGenerator
from src.routing.route_scorer import RouteScorer, RouteScore
from src.routing.dominance import ParetoFilter
from src.routing.explanation_generator import RouteExplanationGenerator

__all__ = [
    "RouteResult",
    "RouteSegment",
    "DynamicRouteResult",
    "RoutingService",
    "NetworkStateService",
    "DynamicCostCalculator",
    "RouteEdgeCost",
    "CandidateRouteGenerator",
    "RouteScorer",
    "RouteScore",
    "ParetoFilter",
    "RouteExplanationGenerator",
]
