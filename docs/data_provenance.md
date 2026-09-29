# Data Provenance

**Project:** Namma Pulse – Bengaluru Metro Intelligent Route & Congestion Management System  
**Phase:** 0 – Network Foundation  
**Document version:** 1.0  
**Date:** 2025

---

## Classification Legend

| Label | Meaning |
|-------|---------|
| **REAL** | Sourced directly from an official or authoritative published source |
| **DERIVED** | Computed or inferred from real data using a documented method |
| **APPROXIMATE** | Estimated; directionally correct but not precisely verified |
| **SYNTHETIC** | Programmatically generated; not observed in the real world |
| **PENDING** | Data element exists but provenance has not yet been confirmed |

---

## Data Elements

### Station Names

| Classification | REAL |
|---|---|
| **Source** | BMRCL official map PDF: `Metro_Map_2025_-_Bengaluru_City.pdf` (primary visual reference) |
| **Cross-references** | Wikipedia – Namma Metro article; bengalurumetro.in station pages; beegru.com station lists |
| **Notes** | Station names have been preserved as closely as possible to the official map. Where multiple sources disagreed on naming (e.g., sponsored prefixes like "Infosys Foundation Konappana Agrahara" or "Biocon Hebbagodi"), the most common authoritative form was used and the discrepancy flagged in `topology_issues.md`. |

---

### Station Sequence Numbers

| Classification | REAL / DERIVED |
|---|---|
| **Source** | BMRCL official map (visual sequence); Wikipedia; bengalurumetro.in |
| **Method** | Sequences were assigned by reading the physical order of stations on each line from terminus to terminus. Sequence 1 = terminus (east/north depending on line orientation). |
| **Notes** | No resequencing was performed. The sequence reflects the order as shown on the map. |

---

### Interchange Flags

| Classification | REAL |
|---|---|
| **Source** | Wikipedia – Namma Metro article; BMRCL official map |
| **Confirmed interchanges (Phase 0):** | |
| | **Nadaprabhu Kempegowda Station (Majestic)** – Purple ↔ Green |
| | **Rashtreeya Vidyalaya Road (RV Road)** – Green ↔ Yellow |
| **Notes** | Future interchanges (Jayadeva Hospital for Pink Line; Central Silk Board for Blue Line) are noted in station notes but are **not modelled** as operational interchanges in Phase 0. |

---

### Edge Connections (Station-to-Station)

| Classification | REAL |
|---|---|
| **Source** | BMRCL official map (physical track topology) |
| **Notes** | Edges represent consecutive station pairs on each line. Only physically confirmed consecutive connections from the map are included. No connections were invented. |

---

### Inter-Station Distance (`distance_km`)

| Classification | **NOT AVAILABLE** (Phase 0) |
|---|---|
| **Value in dataset** | `NA` |
| **Reason** | The PDF map does not provide precise inter-station distances. Published segment-level distance data was not available in a verified per-segment form for all three lines at the time of Phase 0 construction. |
| **Action required** | A future phase should source per-segment distances from BMRCL's official DPR (Detailed Project Report) or verified survey data and update `edges.csv`. |

---

### Scheduled Travel Time (`scheduled_time_min`)

| Classification | **NOT AVAILABLE** (Phase 0) |
|---|---|
| **Value in dataset** | `NA` |
| **Reason** | Per-segment scheduled times were not available in a verified tabular form. End-to-end travel times are publicly reported (Yellow Line: ~35 min for 19.15 km), but distributing this to individual segments without per-segment distances would introduce unacceptable imprecision. |
| **Action required** | A future phase should derive scheduled times from BMRCL timetable data or published speed profiles. Values must be clearly marked `DERIVED` or `APPROXIMATE` if estimated. |

---

### Transfer Edge Weight (`distance_km = 0.0`, `scheduled_time_min = 0.0`)

| Classification | APPROXIMATE |
|---|---|
| **Notes** | Interchange transfer edges are assigned 0.0 km and 0.0 min as a placeholder. In reality, a platform walk at Majestic or RV Road takes 3–8 minutes. A future phase should assign a realistic `congestion_penalty` to model this correctly. |

---

## What is NOT in Phase 0

The following data elements are **intentionally absent** in Phase 0. Their inclusion would require synthetic or unverified data:

- Passenger demand (synthetic – Phase 2)
- Congestion levels (derived from ML models – Phase 3+)
- Predicted travel times (ML output – Phase 3+)
- Disruption status (real-time feed – Phase 4+)
- Reliability scores (statistical – Phase 4+)
- Pink Line and Blue Line topology (under construction / excluded by design)

---

## Source PDF Reference

```
Filename : Metro_Map_2025_-_Bengaluru_City.pdf
Location : C:\Users\dudek\Downloads\Metro_Map_2025_-_Bengaluru_City.pdf
Publisher: BMRCL (Bangalore Metro Rail Corporation Limited)
Year     : 2025
Use      : Visual reference for station topology, naming, and line routing
Note     : PDF could not be machine-parsed directly. Data was extracted
           via visual inspection and cross-referenced with multiple
           secondary sources.
```
