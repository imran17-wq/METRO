"""
station_characteristics.py — Station type assignments for the demand model.

DATA PROVENANCE: ASSUMPTION
----------------------------
Station types and zone weights are hand-labeled based on general knowledge
of Bengaluru's urban geography.  They are NOT measured data.  They are NOT
from BMRCL surveys or travel-demand studies.

They are documented as modelling assumptions and are tunable.
The complete rationale is described in data_generation/README.md.

Station types
-------------
residential  : Primarily housing; high trip origin AM, high destination PM.
commercial   : Retail, markets, business districts; high destination all day.
IT           : IT corridors (Whitefield, Electronic City); high dest AM, origin PM.
educational  : Colleges; moderate uniform demand, slightly lower on weekends.
transit_hub  : Major interchange/terminal; high both directions, all day.
industrial   : Industrial areas (Peenya); shift-worker patterns.
mixed        : General mixed-use; moderate uniform demand.
"""
from __future__ import annotations

from typing import Dict, Tuple

# ---------------------------------------------------------------------------
# Station type weights
#
# Each type has (origin_weight_AM, destination_weight_AM,
#                origin_weight_PM, destination_weight_PM)
# These are relative multipliers applied to the base gravity demand.
# ---------------------------------------------------------------------------

STATION_TYPE_WEIGHTS: Dict[str, Tuple[float, float, float, float]] = {
    #                       orig_AM  dest_AM  orig_PM  dest_PM
    "residential":         (1.8,     0.3,     0.4,     1.7),
    "commercial":          (0.4,     1.4,     1.3,     0.5),
    "IT":                  (0.2,     2.0,     1.9,     0.2),
    "educational":         (0.9,     1.1,     0.9,     1.0),
    "transit_hub":         (1.0,     1.0,     1.0,     1.0),
    "industrial":          (1.5,     0.3,     0.3,     1.4),
    "mixed":               (0.9,     0.9,     0.9,     0.9),
}

# ---------------------------------------------------------------------------
# Station type assignments
#
# Keys are graph node IDs (e.g., "PL01").
# SOURCE: General knowledge of Bengaluru geography.  DOCUMENTED ASSUMPTION.
# ---------------------------------------------------------------------------

STATION_TYPES: Dict[str, str] = {
    # -----------------------------------------------------------------------
    # Purple Line
    # -----------------------------------------------------------------------
    "PL01": "IT",            # Whitefield (Kadugodi) — Whitefield IT corridor
    "PL02": "residential",   # Channasandra
    "PL03": "residential",   # Kadugodi Tree Park
    "PL04": "residential",   # Pattandur Agrahara
    "PL05": "mixed",         # Sri Sathya Sai Hospital — hospital vicinity
    "PL06": "residential",   # Nallurhalli
    "PL07": "IT",            # Kundalahalli — Whitefield tech corridor
    "PL08": "residential",   # Seetharam Palya
    "PL09": "residential",   # Hoodi
    "PL10": "residential",   # Garudacharapalya
    "PL11": "residential",   # Singayyanapalya
    "PL12": "transit_hub",   # KR Pura — near railway station
    "PL13": "residential",   # Benniganahalli
    "PL14": "transit_hub",   # Baiyappanahalli — eastern terminus, bus hub
    "PL15": "residential",   # Swami Vivekananda Road
    "PL16": "commercial",    # Indiranagar — café/retail district
    "PL17": "commercial",    # Trinity
    "PL18": "commercial",    # MG Road — CBD
    "PL19": "commercial",    # Cubbon Park — offices/government
    "PL20": "commercial",    # Vidhana Soudha — state legislature area
    "PL21": "educational",   # Central College
    "PL22": "transit_hub",   # Majestic (Purple) — largest interchange
    "PL23": "transit_hub",   # KSR City Railway Station — rail hub
    "PL24": "residential",   # Magadi Road
    "PL25": "residential",   # Hosahalli
    "PL26": "residential",   # Vijayanagar
    "PL27": "residential",   # Attiguppe
    "PL28": "residential",   # Deepanjali Nagar
    "PL29": "transit_hub",   # Mysuru Road — state highway bus hub
    "PL30": "residential",   # Nayandahalli
    "PL31": "educational",   # Jnanabharathi — university area
    "PL32": "residential",   # Rajarajeshwari Nagar
    "PL33": "residential",   # Pattanagere
    "PL34": "transit_hub",   # Kengeri Bus Terminal — major western bus hub
    "PL35": "residential",   # Kengeri
    "PL36": "transit_hub",   # Challaghatta — western terminus
    # -----------------------------------------------------------------------
    # Green Line
    # -----------------------------------------------------------------------
    "GL01": "transit_hub",   # Madavara — northern terminus
    "GL02": "residential",   # Chikkabidarakallu
    "GL03": "residential",   # Manjunathanagar
    "GL04": "residential",   # Nagasandra
    "GL05": "industrial",    # Dasarahalli — industrial belt
    "GL06": "mixed",         # Jalahalli
    "GL07": "industrial",    # Peenya Industry — Peenya industrial area
    "GL08": "industrial",    # Peenya
    "GL09": "mixed",         # Goraguntepalya
    "GL10": "transit_hub",   # Yeshwanthpur — railway junction
    "GL11": "industrial",    # Sandal Soap Factory
    "GL12": "residential",   # Mahalakshmi
    "GL13": "commercial",    # Rajajinagar — residential + commercial
    "GL14": "residential",   # Mahakavi Kuvempu Road
    "GL15": "residential",   # Srirampura
    "GL16": "commercial",    # Sampige Road (Mantri Square) — major mall
    "GL17": "transit_hub",   # Majestic (Green) — largest interchange
    "GL18": "commercial",    # Chickpete — wholesale market district
    "GL19": "commercial",    # KR Market — largest wholesale market
    "GL20": "educational",   # National College
    "GL21": "commercial",    # Lalbagh — tourist/park
    "GL22": "residential",   # South End Circle
    "GL23": "residential",   # Jayanagar — upper-middle residential
    "GL24": "transit_hub",   # RV Road (Green) — interchange
    "GL25": "residential",   # Banashankari
    "GL26": "residential",   # Jaya Prakash Nagar
    "GL27": "residential",   # Yelachenahalli
    "GL28": "residential",   # Konanakunte Cross
    "GL29": "residential",   # Doddakallasandra
    "GL30": "residential",   # Vajrahalli
    "GL31": "mixed",         # Thalaghattapura
    "GL32": "transit_hub",   # Silk Institute — southern terminus
    # -----------------------------------------------------------------------
    # Yellow Line
    # -----------------------------------------------------------------------
    "YL01": "transit_hub",   # RV Road (Yellow) — interchange
    "YL02": "residential",   # Ragigudda
    "YL03": "mixed",         # Jayadeva Hospital — hospital + residential
    "YL04": "commercial",    # BTM Layout — dense commercial
    "YL05": "commercial",    # Central Silk Board — office area
    "YL06": "residential",   # Bommanahalli
    "YL07": "residential",   # Hongasandra
    "YL08": "residential",   # Kudlu Gate
    "YL09": "residential",   # Singasandra
    "YL10": "residential",   # Hosa Road
    "YL11": "residential",   # Beratena Agrahara
    "YL12": "IT",            # Electronic City — major IT park
    "YL13": "IT",            # Infosys Foundation Konappana Agrahara
    "YL14": "residential",   # Huskur Road
    "YL15": "IT",            # Hebbagodi — IT/industrial
    "YL16": "IT",            # Bommasandra — IT/industrial terminus
}

# ---------------------------------------------------------------------------
# Event-day surge stations
#
# Stations near Chinnaswamy Stadium (IPL/cricket events):
# MG Road, Cubbon Park, Vidhana Soudha are within 1–2 km.
# SOURCE: General knowledge.  DOCUMENTED ASSUMPTION.
# ---------------------------------------------------------------------------

EVENT_SURGE_STATIONS: Dict[str, float] = {
    "PL18": 1.8,   # MG Road — nearest major interchange
    "PL19": 1.6,   # Cubbon Park
    "PL20": 1.4,   # Vidhana Soudha
    "PL17": 1.3,   # Trinity
    "PL22": 1.2,   # Majestic (Purple) — spill-over
    "GL17": 1.2,   # Majestic (Green)
}

# ---------------------------------------------------------------------------
# Base activity weights (used as gravity model node weights)
#
# Higher value = more trip-attractive in general.
# Calibrated so that high-activity stations (Majestic, IT hubs) generate
# substantially more demand than peripheral stations.
# SOURCE: ASSUMPTION — not from ridership surveys.
# ---------------------------------------------------------------------------

BASE_ACTIVITY_WEIGHTS: Dict[str, float] = {
    "transit_hub":  2.0,
    "commercial":   1.6,
    "IT":           1.5,
    "educational":  1.0,
    "mixed":        1.0,
    "residential":  0.8,
    "industrial":   0.7,
}
