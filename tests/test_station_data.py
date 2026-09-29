"""
tests/test_station_data.py
Unit tests for the integrity of the stations.csv dataset (supporting 5 lines).
"""
import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config.settings import PROCESSED_DIR

STATIONS_CSV = PROCESSED_DIR / "stations.csv"


@pytest.fixture(scope="module")
def station_rows():
    with open(STATIONS_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


class TestStationCSV:
    def test_file_exists(self):
        assert STATIONS_CSV.exists(), f"stations.csv not found at {STATIONS_CSV}"

    def test_has_rows(self, station_rows):
        assert len(station_rows) > 0

    def test_required_columns(self, station_rows):
        required = {
            "station_id", "station_name", "line",
            "sequence", "is_interchange",
        }
        actual = set(station_rows[0].keys())
        missing = required - actual
        assert not missing, f"Missing columns: {missing}"

    def test_station_ids_unique(self, station_rows):
        ids = [r["station_id"] for r in station_rows]
        assert len(ids) == len(set(ids)), "Duplicate station_ids found."

    def test_station_ids_not_empty(self, station_rows):
        for r in station_rows:
            assert r["station_id"].strip(), "Empty station_id found."

    def test_station_names_not_empty(self, station_rows):
        for r in station_rows:
            assert r["station_name"].strip(), f"Empty station_name for ID {r['station_id']}"

    def test_line_values_valid(self, station_rows):
        valid_lines = {"Purple", "Green", "Yellow", "Pink", "Blue"}
        for r in station_rows:
            assert r["line"].strip() in valid_lines, f"Unknown line '{r['line']}' for station {r['station_id']}"

    def test_sequence_values_positive_integers(self, station_rows):
        for r in station_rows:
            seq = r["sequence"].strip()
            assert seq.isdigit() and int(seq) >= 1, f"Invalid sequence '{seq}' for {r['station_id']}"

    def test_is_interchange_boolean(self, station_rows):
        for r in station_rows:
            assert r["is_interchange"].strip().lower() in ("true", "false"), f"Invalid is_interchange for {r['station_id']}"

    def test_purple_line_count(self, station_rows):
        assert sum(1 for r in station_rows if r["line"] == "Purple") == 36

    def test_green_line_count(self, station_rows):
        assert sum(1 for r in station_rows if r["line"] == "Green") == 32

    def test_yellow_line_count(self, station_rows):
        assert sum(1 for r in station_rows if r["line"] == "Yellow") == 16

    def test_pink_line_count(self, station_rows):
        assert sum(1 for r in station_rows if r["line"] == "Pink") == 18

    def test_blue_line_count(self, station_rows):
        assert sum(1 for r in station_rows if r["line"] == "Blue") == 23

    def test_interchange_stations_have_interchange_lines(self, station_rows):
        for r in station_rows:
            if r["is_interchange"].strip().lower() == "true":
                assert r["interchange_lines"].strip(), f"Interchange station {r['station_id']} has no interchange_lines."
