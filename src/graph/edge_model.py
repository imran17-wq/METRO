"""
Edge model for the Namma Pulse metro graph.
"""
from dataclasses import dataclass, field
from typing import Optional


SENTINEL = object()  # sentinel for "not provided" (distinct from None)


@dataclass
class Edge:
    """
    Represents a directed connection between two consecutive metro stations.

    The graph is undirected (bidirectional traversal is the default), so each
    Edge represents a physical track segment; the graph engine stores it in
    both directions automatically via NetworkX undirected graph conventions.

    Attributes
    ----------
    edge_id : str
        Unique edge identifier (e.g., 'PL_E01').
    from_station_id : str
        Station ID of the source station.
    to_station_id : str
        Station ID of the destination station.
    from_station_name : str
        Human-readable source station name.
    to_station_name : str
        Human-readable destination station name.
    line : str
        Metro line this edge belongs to.
    sequence : int
        Edge position within the line (1 = first segment from terminus).
    distance_km : Optional[float]
        Inter-station distance in km. None if unavailable from source.
    scheduled_time_min : Optional[float]
        Scheduled travel time in minutes. None if unavailable from source.
        This field is designed to be replaced later with predicted_travel_time.
    notes : str
        Free-text notes (data provenance caveats, etc.).

    Future extensibility
    --------------------
    The following fields are intentionally reserved and will be added
    in later phases without touching the graph engine:
        - predicted_travel_time : float
        - congestion_penalty : float
        - disruption_status : str
        - reliability_score : float
    """

    edge_id: str
    from_station_id: str
    to_station_id: str
    from_station_name: str
    to_station_name: str
    line: str
    sequence: int
    distance_km: Optional[float] = None
    scheduled_time_min: Optional[float] = None
    notes: str = ""

    def to_dict(self) -> dict:
        """Return edge metadata as a plain dict for NetworkX storage."""
        return {
            "edge_id": self.edge_id,
            "line": self.line,
            "sequence": self.sequence,
            "distance_km": self.distance_km,
            "scheduled_time_min": self.scheduled_time_min,
            "notes": self.notes,
            # Reserved slots for future phases – set to None now so
            # downstream code can always key-check without AttributeError:
            "predicted_travel_time": None,
            "congestion_penalty": None,
            "disruption_status": None,
            "reliability_score": None,
        }

    def __repr__(self) -> str:
        dist = f"{self.distance_km} km" if self.distance_km is not None else "dist=NA"
        time = (
            f"{self.scheduled_time_min} min"
            if self.scheduled_time_min is not None
            else "time=NA"
        )
        return (
            f"<Edge {self.edge_id}: {self.from_station_name} → "
            f"{self.to_station_name} [{self.line}] {dist} {time}>"
        )
