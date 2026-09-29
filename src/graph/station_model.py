"""
Station model for the Namma Pulse metro graph.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Station:
    """
    Represents a single metro station node in the network graph.

    Attributes
    ----------
    station_id : str
        Unique station identifier (e.g., 'PL01', 'GL17').
    station_name : str
        Official station name as per BMRCL / map source.
    line : str
        The metro line this record belongs to ('Purple', 'Green', 'Yellow').
        Interchange stations appear once per line they serve.
    sequence : int
        Position of this station within its line (1-indexed, terminus = 1).
    is_interchange : bool
        True if this station connects two or more operational lines.
    interchange_lines : List[str]
        List of line names this station serves when is_interchange is True.
    notes : str
        Free-text notes (naming caveats, source flags, etc.).
    """

    station_id: str
    station_name: str
    line: str
    sequence: int
    is_interchange: bool = False
    interchange_lines: List[str] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self) -> None:
        if self.is_interchange and not self.interchange_lines:
            raise ValueError(
                f"Station '{self.station_id}' is marked as interchange "
                "but has no interchange_lines defined."
            )
    @property
    def canonical_name(self) -> str:
        """Return the station name, normalised to title-case stripped form."""
        return self.station_name.strip()

    def __repr__(self) -> str:
        interchange_flag = " [INTERCHANGE]" if self.is_interchange else ""
        return (
            f"<Station {self.station_id}: {self.station_name} "
            f"({self.line} seq={self.sequence}){interchange_flag}>"
        )
