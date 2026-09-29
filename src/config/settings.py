"""
Settings and path configuration for Namma Pulse.
Single Canonical 5-Line Architecture (Purple, Green, Yellow, Pink, Blue).
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# Project root (two levels up from this file: src/config/settings.py)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Data directories
# ---------------------------------------------------------------------------
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REFERENCE_DIR = DATA_DIR / "reference"

INTERCHANGES_CSV = PROCESSED_DIR / "interchanges.csv"
STATIONS_CSV = PROCESSED_DIR / "stations.csv"
EDGES_CSV = PROCESSED_DIR / "edges.csv"

# ---------------------------------------------------------------------------
# Canonical Line Definitions & Status Metadata
# ---------------------------------------------------------------------------
ALL_LINES = ["Purple", "Green", "Yellow", "Pink", "Blue"]

DEFAULT_ACTIVE_LINES = {"Purple", "Green", "Yellow"}
DEFAULT_INACTIVE_LINES = {"Pink", "Blue"}

LINE_METADATA = {
    "Purple": {"status": "OPERATIONAL", "default_active": True},
    "Green":  {"status": "OPERATIONAL", "default_active": True},
    "Yellow": {"status": "OPERATIONAL", "default_active": True},
    "Pink":   {"status": "UNDER_CONSTRUCTION", "default_active": False},
    "Blue":   {"status": "UNDER_CONSTRUCTION", "default_active": False},
}

# Backwards compatibility constants
OPERATIONAL_LINES = ["Purple", "Green", "Yellow"]
EXCLUDED_LINES: list = []

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
