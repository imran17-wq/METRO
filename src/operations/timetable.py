"""
timetable.py — Synthetic Operational Timetable Generator for Namma Pulse OCC.

Generates reproducible train schedules for active operational lines (Purple, Green, Yellow, Pink, Blue).
Pink and Blue lines remain INACTIVE (0 scheduled passenger services) by default,
and generate SCENARIO_SYNTHETIC_DEMAND when activated via Scenario Controller.
"""
import random
from dataclasses import dataclass, field
from typing import Dict, List, Set

from src.config.settings import DEFAULT_ACTIVE_LINES, ALL_LINES
from src.operations.train import Train


@dataclass
class TrainSchedule:
    train_id: str
    line: str
    direction: str
    origin_station: str
    destination_station: str
    station_sequence: List[str]
    departure_sec: int
    arrivals_sec: Dict[str, int]
    departures_sec: Dict[str, int]
    demand_provenance: str = "SYNTHETIC"


class TimetableGenerator:
    """
    Generates synthetic timetable schedules for Namma Pulse OCC.
    Uses canonical network topology station sequences.
    """

    DEFAULT_SEGMENT_TIME_SEC = 150  # 2.5 min per segment
    DEFAULT_DWELL_TIME_SEC = 30     # 30s station dwell

    def __init__(self, station_data_by_line: Dict[str, List[str]], seed: int = 42):
        """
        :param station_data_by_line: Map of line_name -> list of station_names ordered by sequence
        """
        self.station_data_by_line = station_data_by_line
        self.seed = seed
        self._rng = random.Random(seed)

    def generate_timetable(
        self,
        active_lines: Set[str] = None,
        start_time_sec: int = 28800,  # 08:00:00 AM
        end_time_sec: int = 34200,    # 09:30:00 AM
        headway_sec: int = 360,       # 6 min dispatch frequency
    ) -> List[TrainSchedule]:
        if active_lines is None:
            active_lines = set(DEFAULT_ACTIVE_LINES)

        schedules: List[TrainSchedule] = []

        # Operational lines: schedule all active lines present in station data
        lines_to_schedule = [
            line for line in ALL_LINES
            if line in active_lines and line in self.station_data_by_line
        ]

        train_counter = 1

        for line in lines_to_schedule:
            seq = self.station_data_by_line[line]
            if len(seq) < 2:
                continue

            rev_seq = list(reversed(seq))
            demand_prov = "SCENARIO_SYNTHETIC_DEMAND" if line in ("Pink", "Blue") else "SYNTHETIC"

            # Dispatch trains from start_time_sec to end_time_sec
            dispatch_time = start_time_sec
            while dispatch_time <= end_time_sec:
                # 1. Forward direction (e.g. UP)
                t_id_fwd = f"{line[0]}L-{train_counter:03d}"
                fwd_sched = self._build_schedule_for_train(
                    train_id=t_id_fwd,
                    line=line,
                    direction="UP",
                    sequence=seq,
                    departure_sec=dispatch_time,
                    demand_provenance=demand_prov,
                )
                schedules.append(fwd_sched)
                train_counter += 1

                # 2. Return direction (e.g. DOWN)
                t_id_rev = f"{line[0]}L-{train_counter:03d}"
                rev_sched = self._build_schedule_for_train(
                    train_id=t_id_rev,
                    line=line,
                    direction="DOWN",
                    sequence=rev_seq,
                    departure_sec=dispatch_time,
                    demand_provenance=demand_prov,
                )
                schedules.append(rev_sched)
                train_counter += 1

                dispatch_time += headway_sec

        return schedules

    def create_train_instances(
        self,
        active_lines: Set[str] = None,
        start_time_sec: int = 28800,
        end_time_sec: int = 34200,
        headway_sec: int = 360,
    ) -> List[Train]:
        schedules = self.generate_timetable(
            active_lines=active_lines,
            start_time_sec=start_time_sec,
            end_time_sec=end_time_sec,
            headway_sec=headway_sec,
        )

        trains: List[Train] = []
        for sched in schedules:
            t = Train(
                train_id=sched.train_id,
                line=sched.line,
                direction=sched.direction,
                origin_station=sched.origin_station,
                destination_station=sched.destination_station,
                station_sequence=sched.station_sequence,
                scheduled_departure_sec=sched.departure_sec,
                scheduled_arrivals_sec=sched.arrivals_sec,
                scheduled_departures_sec=sched.departures_sec,
            )
            trains.append(t)

        return trains

    def _build_schedule_for_train(
        self,
        train_id: str,
        line: str,
        direction: str,
        sequence: List[str],
        departure_sec: int,
        demand_provenance: str = "SYNTHETIC",
    ) -> TrainSchedule:
        arrivals: Dict[str, int] = {}
        departures: Dict[str, int] = {}

        curr_time = departure_sec
        departures[sequence[0]] = curr_time

        for i in range(len(sequence) - 1):
            curr_st = sequence[i]
            next_st = sequence[i + 1]

            # Segment running time
            curr_time += self.DEFAULT_SEGMENT_TIME_SEC
            arrivals[next_st] = curr_time

            # Dwell time if not last station
            if i + 1 < len(sequence) - 1:
                curr_time += self.DEFAULT_DWELL_TIME_SEC
                departures[next_st] = curr_time

        return TrainSchedule(
            train_id=train_id,
            line=line,
            direction=direction,
            origin_station=sequence[0],
            destination_station=sequence[-1],
            station_sequence=sequence,
            departure_sec=departure_sec,
            arrivals_sec=arrivals,
            departures_sec=departures,
            demand_provenance=demand_provenance,
        )
