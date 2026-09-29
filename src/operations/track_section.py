"""
track_section.py — Operational Track Section Layer for Namma Pulse OCC.

Models two directional tracks (UP and DOWN) as distinct operational movement sections.
Enforces max 1 train per section, safe entry rules, and section blocking without changing graph topology.

Data Provenance Tag: SIMULATED OPERATIONS
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class TrackSection:
    section_id: str
    line: str
    direction: str  # "UP" or "DOWN"
    from_station: str
    to_station: str
    occupied_by: Optional[str] = None
    reserved_by: Optional[str] = None
    blocked: bool = False
    block_reason: Optional[str] = None
    data_provenance: str = "SIMULATED OPERATIONS"

    @property
    def is_free(self) -> bool:
        return not self.blocked and self.occupied_by is None

    def to_dict(self) -> Dict:
        status = "BLOCKED" if self.blocked else ("OCCUPIED" if self.occupied_by else "FREE")
        return {
            "section_id": self.section_id,
            "line": self.line,
            "direction": self.direction,
            "from_station": self.from_station,
            "to_station": self.to_station,
            "status": status,
            "occupied_by": self.occupied_by,
            "reserved_by": self.reserved_by,
            "blocked": self.blocked,
            "block_reason": self.block_reason,
            "data_provenance": self.data_provenance,
        }


class SectionManager:
    """
    Manages operational track section occupancies and directional movement rules.
    """

    def __init__(self, station_data_by_line: Dict[str, List[str]]):
        self.sections: Dict[str, TrackSection] = {}
        self.build_sections(station_data_by_line)

    def build_sections(self, station_data_by_line: Dict[str, List[str]]):
        self.sections.clear()
        for line, stations in station_data_by_line.items():
            if len(stations) < 2:
                continue

            # UP direction (index 0 -> index N-1)
            for i in range(len(stations) - 1):
                from_st, to_st = stations[i], stations[i + 1]
                sec_id = f"{line.upper()}_UP_{from_st.upper()}_{to_st.upper()}"
                self.sections[sec_id] = TrackSection(
                    section_id=sec_id,
                    line=line,
                    direction="UP",
                    from_station=from_st,
                    to_station=to_st,
                )

            # DOWN direction (index N-1 -> index 0)
            rev_stations = list(reversed(stations))
            for i in range(len(rev_stations) - 1):
                from_st, to_st = rev_stations[i], rev_stations[i + 1]
                sec_id = f"{line.upper()}_DOWN_{from_st.upper()}_{to_st.upper()}"
                self.sections[sec_id] = TrackSection(
                    section_id=sec_id,
                    line=line,
                    direction="DOWN",
                    from_station=from_st,
                    to_station=to_st,
                )

    def get_section(self, section_id: str) -> Optional[TrackSection]:
        return self.sections.get(section_id)

    def get_section_for_stations(self, line: str, direction: str, from_st: str, to_st: str) -> Optional[TrackSection]:
        sec_id = f"{line.upper()}_{direction.upper()}_{from_st.upper()}_{to_st.upper()}"
        return self.sections.get(sec_id)

    def can_enter_section(self, section_id: str, train_id: str) -> bool:
        sec = self.get_section(section_id)
        if not sec:
            return False
        if sec.blocked:
            return False
        if sec.occupied_by is not None and sec.occupied_by != train_id:
            return False
        if sec.reserved_by is not None and sec.reserved_by != train_id:
            return False
        return True

    def occupy_section(self, section_id: str, train_id: str) -> bool:
        sec = self.get_section(section_id)
        if not sec or not self.can_enter_section(section_id, train_id):
            return False
        sec.occupied_by = train_id
        sec.reserved_by = None
        return True

    def release_section(self, section_id: str, train_id: str):
        sec = self.get_section(section_id)
        if sec and sec.occupied_by == train_id:
            sec.occupied_by = None

    def block_section(self, section_id: str, reason: str = "Disruption"):
        sec = self.get_section(section_id)
        if sec:
            sec.blocked = True
            sec.block_reason = reason

    def unblock_section(self, section_id: str):
        sec = self.get_section(section_id)
        if sec:
            sec.blocked = False
            sec.block_reason = None

    def clear_all_occupancies(self):
        for sec in self.sections.values():
            sec.occupied_by = None
            sec.reserved_by = None

    def get_all_sections_list(self) -> List[Dict]:
        return [sec.to_dict() for sec in self.sections.values()]
