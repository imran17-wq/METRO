"""
simulation_clock.py — Deterministic Simulation Clock for Namma Pulse OCC.

Manages simulated operations time, play/pause/reset controls, and speed multipliers (1x, 2x, 5x, 10x).
"""
import time
from typing import Dict


class SimulationClock:
    """
    Deterministic OCC Simulation Clock.
    Operates on simulated time in seconds from midnight.
    """

    DEFAULT_START_SEC = 28800  # 08:00:00 AM

    def __init__(self, start_sec: int = DEFAULT_START_SEC):
        self.start_sec = start_sec
        self.current_time_sec = float(start_sec)
        self.is_running = False
        self.speed_multiplier = 1.0
        self.last_tick_wall_time = time.time()

    def play(self):
        self.is_running = True
        self.last_tick_wall_time = time.time()

    def pause(self):
        self.is_running = False

    def reset(self):
        self.current_time_sec = float(self.start_sec)
        self.is_running = False
        self.speed_multiplier = 1.0
        self.last_tick_wall_time = time.time()

    def set_speed(self, speed: float):
        if speed in (1.0, 2.0, 5.0, 10.0):
            self.speed_multiplier = speed

    def tick(self, elapsed_seconds: float = None) -> int:
        """
        Advances simulation clock by elapsed_seconds * speed_multiplier (if specified)
        or wall-clock time elapsed since last tick (if elapsed_seconds is None).
        Returns current simulated time in seconds from midnight.
        """
        now = time.time()
        wall_elapsed = now - self.last_tick_wall_time
        self.last_tick_wall_time = now

        if self.is_running:
            if elapsed_seconds is not None and elapsed_seconds > 0:
                advance = elapsed_seconds * self.speed_multiplier
            else:
                advance = max(0.0, wall_elapsed) * self.speed_multiplier
            self.current_time_sec += advance

        return int(round(self.current_time_sec))

    def formatted_time(self) -> str:
        curr_int = int(round(self.current_time_sec))
        h = (curr_int // 3600) % 24
        m = (curr_int % 3600) // 60
        s = curr_int % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def to_dict(self) -> Dict:
        return {
            "current_time_sec": int(round(self.current_time_sec)),
            "formatted_time": self.formatted_time(),
            "is_running": self.is_running,
            "speed_multiplier": self.speed_multiplier,
            "data_provenance": "SIMULATED OPERATIONS",
        }

