# Topology Issues Log

**Project:** Namma Pulse – Phase 0  
**Purpose:** Record ambiguities, naming discrepancies, and unresolved questions identified during network construction. These must be verified against the source PDF before Phase 1.

---

## Issue Format

Each issue is recorded as:

- **Issue ID:** Unique reference
- **Category:** Naming | Sequence | Interchange | Coverage | Data Gap
- **Affected Station/Edge:** The specific node(s) or edge(s) involved
- **Reason:** Why this is flagged
- **Resolution Status:** `UNRESOLVED` | `RESOLVED` | `PENDING_PDF_REVIEW`
- **Proposed Resolution:** Suggested action

---

## ISSUE-001 — Sponsored Station Names (Yellow Line)

- **Category:** Naming
- **Affected Stations:** YL13, YL15, YL16
- **Reason:** Multiple sources use different name forms:
  - YL13: "Infosys Foundation Konappana Agrahara" vs "Konappana Agrahara"
  - YL15: "Hebbagodi" vs "Biocon Hebbagodi"
  - YL16: "Bommasandra" vs "Delta Electronics Bommasandra"
  
  Sponsored prefixes (Infosys Foundation, Biocon, Delta Electronics) are commercial arrangements that may change. The 2025 PDF map may use either form.

- **Resolution Status:** `PENDING_PDF_REVIEW`
- **Proposed Resolution:** Confirm against the PDF. Store the map-canonical name as `station_name` and record the sponsored form in `notes`.

---

## ISSUE-002 — Purple Line Station Count Discrepancy

- **Category:** Coverage
- **Affected:** Purple Line overall
- **Reason:** Some sources report 37 stations; others 36. The discrepancy may relate to whether the Baiyappanahalli satellite station or a staging facility is counted separately.
- **Resolution Status:** `UNRESOLVED`
- **Proposed Resolution:** Count stations visually on the PDF. The current dataset uses 36 stations (matching the most commonly cited station-by-station lists). If the PDF shows 37, identify and add the missing station.

---

## ISSUE-003 — Green Line Station Count Discrepancy

- **Category:** Coverage
- **Affected:** Green Line overall
- **Reason:** Some sources list 32 stations, one source cited "33". This may include a planned but not-yet-opened extension.
- **Resolution Status:** `UNRESOLVED`
- **Proposed Resolution:** Verify against the 2025 PDF. Current dataset uses 32 stations.

---

## ISSUE-004 — "Mahakavi Kuvempu Road" Naming Variant

- **Category:** Naming
- **Affected Station:** GL14
- **Reason:** Some sources list this as "Kuvempu Road" without the "Mahakavi" prefix.
- **Resolution Status:** `PENDING_PDF_REVIEW`
- **Proposed Resolution:** Use the name exactly as shown on the PDF legend.

---

## ISSUE-005 — Transfer Walk Time at Interchange Stations

- **Category:** Data Gap
- **Affected Edges:** XFER_PL22_GL17 (Majestic), XFER_GL24_YL01 (RV Road)
- **Reason:** Transfer edges currently have `scheduled_time_min = 0.0`. Actual platform-to-platform walk times at Majestic are estimated at 5–8 minutes; at RV Road 3–5 minutes. These values are unverified from official sources.
- **Resolution Status:** `UNRESOLVED`
- **Proposed Resolution:** Source official BMRCL interchange walk times or measure from published journey planners. Update in Phase 1 as `APPROXIMATE` values.

---

## ISSUE-006 — Jayadeva Hospital Future Interchange

- **Category:** Interchange
- **Affected Station:** YL03 (Jayadeva Hospital)
- **Reason:** Jayadeva Hospital is listed as a future interchange with the Pink Line, which is not yet operational. It is correctly NOT flagged as `is_interchange=True` in Phase 0. However, the note referencing the future Pink Line interchange may need updating once Pink Line opens.
- **Resolution Status:** `RESOLVED` (deferred correctly to Phase 0 scope)
- **Proposed Resolution:** No action in Phase 0. Flag for update in Phase 1 when Pink Line becomes operational.

---

## ISSUE-007 — Central Silk Board Future Interchange

- **Category:** Interchange
- **Affected Station:** YL05 (Central Silk Board)
- **Reason:** Central Silk Board is a planned interchange with the Blue Line, not yet operational.
- **Resolution Status:** `RESOLVED` (deferred correctly to Phase 0 scope)
- **Proposed Resolution:** No action in Phase 0. Flag for update when Blue Line becomes operational.

---

## ISSUE-008 — Inter-Station Distances Not Available

- **Category:** Data Gap
- **Affected:** All edges (`distance_km = NA`)
- **Reason:** The PDF map does not label per-segment distances. The total line lengths are known (Purple ~43.5 km / 36 stations; Green ~33.5 km / 32 stations; Yellow 19.15 km / 16 stations) but individual segment distances are not confirmed from authoritative per-segment sources.
- **Resolution Status:** `UNRESOLVED`
- **Proposed Resolution:** Source per-segment distances from BMRCL's Detailed Project Report (DPR) documents or station-level survey data. Do not distribute total line length equally across segments — urban metro geometries are non-uniform.

---

## ISSUE-009 — Scheduled Time Per Segment Not Available

- **Category:** Data Gap
- **Affected:** All edges (`scheduled_time_min = NA`)
- **Reason:** Published timetable data does not appear to be publicly available in per-segment form. End-to-end times are known but per-segment derivation without distance data would introduce synthetic error.
- **Resolution Status:** `UNRESOLVED`
- **Proposed Resolution:** Source from BMRCL timetables or derive from GTFS feed if available.

---

## Summary

| Status | Count |
|--------|-------|
| RESOLVED | 2 |
| PENDING_PDF_REVIEW | 2 |
| UNRESOLVED | 5 |

**Action required before Phase 1:** Manually verify ISSUE-001 through ISSUE-004 against the source PDF. Issues 008 and 009 block the use of real travel-time routing but do not block Phase 0 graph validation.
