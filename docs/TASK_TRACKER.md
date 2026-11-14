# Task Tracker

Status: `TODO` · `IN_PROGRESS` · `BLOCKED` · `IN_REVIEW` · `DONE` · `CUT`.
Priority: **P0** = MVP · **P1** = important enhancement · **P2** = stretch.
H = hours after stack approval (H0). Update this file in the same PR as the work.

## Setup and governance

| ID | Task | Owner | Pri | Depends | Status | Acceptance criteria |
|---|---|---|---|---|---|---|
| T-000 | Planning docs + private repo created | Claude / M1 | P0 | — | DONE (2026-11-14) | Repo private; docs pushed; no secrets |
| T-0A | **Approve tech stack (D-008)** | M1 | P0 | T-000 | TODO | `TECH_STACK.md` marked APPROVED; D-008 logged |
| T-0B | **Approve data contract v0.1.0** | M1 | P0 | T-000 | TODO | D-016 logged; contract status APPROVED |
| T-0C | Add collaborators (Lead only) | M1 | P0 | T-000 | TODO | Both teammates have access |
| T-0D | Decide API owner (D-015) and repo directory layout | M1 | P0 | T-0A | TODO | Logged |

## Data and science (Member 2)

| ID | Task | Owner | Pri | Depends | Status | Acceptance criteria |
|---|---|---|---|---|---|---|
| T-001 | Download all global zips (MODIS 2002–2025, S-NPP 2012–2025, NOAA-20 2018–2025) | M2 | P0 | — (can start before T-0A) | TODO | All files present; sizes match `DATA_SOURCES.md`; snapshot date recorded |
| T-002 | Pull 2026 data via the area API (world, 5-day windows) for MODIS, S-NPP and NOAA-20; fetch `missing_data` and `data_availability` | M2 | P0 | MAP_KEY | TODO | Complete date coverage logged; retries recorded |
| T-003 | Unzip and normalize to the unified schema (Parquet) | M2 | P0 | T-001, T-0A | TODO | Row counts per sensor and year recorded |
| T-004 | Obtain a fire-region mask (GFED basis regions) or implement the UN-subregion fallback | M1 → M2 | P0 | — | TODO | Every analysis cell has a `fire_region` |
| T-005 | Filters + static-source mask + QA summary | M2 | P0 | T-003 | TODO | QA table; estimates in `DATA_SOURCES.md` replaced with measurements |
| T-006 | Fine-grid cell-days → analysis cell-month per witness × day/night | M2 | P0 | T-005, D-009 | TODO | `cell_month_witness` validates against the contract |
| T-007 | Investigate MODIS `version` values (6.2 / 6.03 / 61.03) | M2 | P1 | T-003 | TODO | Finding documented; any impact on the method logged |
| T-008 | Confirm Aqua and Terra 2026 availability via `data_availability` | M2 | P0 | MAP_KEY | TODO | Result in `DATA_SOURCES.md` |
| T-009 | FIRMS country name → ISO3 / continent mapping | M2 (M1 may help) | P0 | T-003 | TODO | 100% of country files mapped |
| T-010 | SYNTHETIC fixtures for all contract products | M2 | P0 | T-0B | TODO | Labelled synthetic; <5 MB; validate against the contract |
| T-011 | Calibration ratios with partial pooling + block bootstrap | M2 | P0 | T-006, T-004 | TODO | `calibration` product; pooling levels reported |
| T-012 | Holdout evaluation 2017–2021; Aqua drift diagnostic | M2 | P0 | T-011 | TODO | Scores and drift plot presented at R2 |
| T-013 | Witness combination + disagreement inflation; `harmonize_area()` | M2 | P0 | T-011 | TODO | Unit tests on synthetic data with known answers |
| T-014 | Baseline, probabilities, verdicts, reason codes; entity aggregation | M2 | P0 | T-013, D-010 | TODO | `cell_month_harmonized`, `entity_month`, `metadata.json` validate |
| T-015 | Large-fire consistency check | M2 | P1 | T-006 | TODO | Diagnostic series per entity |
| T-016 | "MODIS blindness" indicator | M2 | P1 | T-011 | TODO | Per-region value with caveat text |

## Validation (Member 2 implements; Member 1 defines and reviews)

| ID | Task | Owner | Pri | Depends | Status | Acceptance criteria |
|---|---|---|---|---|---|---|
| T-050 | Define case windows, bounding boxes, quiet months | M1 | P0 | — | TODO | Table in `VALIDATION_PLAN.md` |
| T-051 | **G1 lock**: grid, baseline, verdict and validation thresholds | M1 | P0 | T-006 | TODO | Logged as approved before any results |
| T-020 | Test A1 (two independent paths) | M2 | P0 | T-014, T-050 | TODO | Results recorded, pass or fail |
| T-021 | Test B1 (satellite-change steps) + B3 (known artifacts) | M2 | P0 | T-014 | TODO | Recorded |
| T-022 | Test D1 (coverage) + D2 (gaps) | M2 | P0 | T-012, T-014 | TODO | Recorded |
| T-023 | Test A2 (same fire, two eras) | M2 | P1 | T-014, T-050 | TODO | Recorded |
| T-024 | Tests B2, C1, CTRL | M2 | P1 | T-014 | TODO | Recorded |
| T-025 | Tests E1 (leave one region out) + S1 (sensitivity) | M2 | P1 | T-011 | TODO | Recorded |
| T-026 | Verify every number displayed in the app/demo against products | M2 + M1 | P0 | T-039 | TODO | Checklist signed off |

## Application (Member 3)

| ID | Task | Owner | Pri | Depends | Status | Acceptance criteria |
|---|---|---|---|---|---|---|
| T-030 | Environment setup per the approved stack; app skeleton | M3 | P0 | T-0A | TODO | Runs locally for M1 and M3 |
| T-031 | Global map: country layer + analysis-cell layer | M3 | P0 | T-030, T-010 | TODO | Selected month renders; tooltip per cell |
| T-032 | Calendar (years × months; % of normal / activity) | M3 | P0 | T-010 | TODO | Accessible ramps; legend; null shown as "no data" |
| T-033 | Raw vs harmonized toggle | M3 | P0 | T-032 | TODO | Switches calendar and map |
| T-034 | API skeleton serving fixtures (all endpoints) | M3 (D-015) | P0 | T-010 | TODO | Responses validate against the contract |
| T-035 | Country/continent selection + rectangle custom area | M3 | P0 | T-034 | TODO | Custom area returns a series via `harmonize_area()` |
| T-036 | Evidence panel (verdict, probability, reason codes in plain language) | M3 | P0 | T-034 | TODO | Every reason code has user-facing text approved by M1 |
| T-037 | Witness comparison chart + satellite timeline + outages | M3 | P0 | T-034 | TODO | Per-witness raw and converted series |
| T-038 | CSV export | M3 | P0 | T-034 | TODO | Header with method version, snapshot date, citation |
| T-039 | Real-data integration | M3 + M2 | P0 | T-014 | TODO | All views on real products |
| T-040 | Global anomaly list | M3 | P0 | T-034 | TODO | Ranked by probability; links to the entity |
| T-041 | Methods + validation results page | M3 | P0 | T-020+ | TODO | Shows PASS/FAIL/NOT_RUN faithfully |
| T-042 | Performance and accessibility pass | M3 | P1 | T-039 | TODO | Keyboard navigation; colour-blind-safe check |
| T-043 | Static fallback build; optional deploy | M3 | P1 | T-039 | TODO | Preset views work without the API |
| T-044 | Free-polygon custom area | M3 | P1 | T-035 | TODO | — |

## Demo and submission (Member 1)

| ID | Task | Owner | Pri | Depends | Status | Acceptance criteria |
|---|---|---|---|---|---|---|
| T-060 | Demo storyline (30 s cut + ~3 min) | M1 | P0 | — | TODO | Script in the repo |
| T-061 | Record the demo; English subtitles | M1 | P0 | T-039 | TODO | Uses real data only |
| T-062 | Space Apps project page with references | M1 | P0 | — | TODO | All sources cited |
| T-063 | Submit by H34 | M1 | P0 | T-061, T-062 | TODO | Confirmed on the site |
| T-064 | Decide repo visibility for judges (D-014) | M1 | P0 | — | TODO | Logged |
