# Task Tracker

The process is defined in [`TEAM_WORKFLOW.md`](TEAM_WORKFLOW.md).

**Who edits what:**
- Only the **Project Lead** assigns tasks (sets Owner, Branch, `ASSIGNED`) and records `MERGED` / `REJECTED`.
- A teammate's PR edits **only its own task row** (Status → `IN_PROGRESS` / `IN_REVIEW`, PR link).

**Legend:**
- **Status:** `TODO` · `ASSIGNED` · `IN_PROGRESS` · `IN_REVIEW` · `CHANGES_REQUESTED` · `MERGED` · `BLOCKED` · `REJECTED` · `CUT` · `DONE` (decision/governance tasks only)
- **Review:** `—` · `PENDING` · `CHANGES_REQUESTED` · `APPROVED` · `REJECTED`
- **Priority:** **P0** = MVP · **P1** = enhancement · **P2** = stretch
- **H** = hours after stack approval

> **Stack (D-008) and data contract v0.1.0 (D-016) approved on 2026-11-14 at 12:26 IST (H0).** No implementation task is assigned yet. **Layout (T-0D) approved:** `pipeline/` (Member 2), `api/` and `app/` (Member 3). **Member 3 owns the API (D-015).** Every task is now assignable once its dependencies are merged. Branch names below are the planned names; the Lead confirms them at assignment.
>
> **Workstream prompts:** Member 2 → [`prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md`](prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md) · Member 3 → [`prompts/MEMBER_3_APPLICATION_PROMPT.md`](prompts/MEMBER_3_APPLICATION_PROMPT.md). For each assigned task, the teammate's session still writes a task prompt in `task-prompts/`.

## Setup and governance

| ID | Task | Owner | Pri | Depends | Branch | PR | Status | Review | Acceptance criteria |
|---|---|---|---|---|---|---|---|---|---|
| T-000 | Planning docs + private repo created | M1 | P0 | — | `main` (bootstrap) | — | MERGED (2026-11-14) | n/a (bootstrap) | Repo private; docs pushed; no secrets |
| T-0E | Team workflow docs (TEAM_WORKFLOW, PR template, push guard) | M1 | P0 | T-000 | `docs/team-workflow` | [#2](https://github.com/vishalbg02/global-fire-harmonization/pull/2) (supersedes #1) | MERGED (2026-11-14, merge commit cc940ba) | — (Lead-authored PR; GitHub does not allow self-approval) | Lead approves the workflow (D-017) |
| T-0A | **Approve tech stack (D-008)** | M1 | P0 | T-000 | — | — | DONE (approved 2026-11-14 12:26 IST) | — | `TECH_STACK.md` marked APPROVED; D-008 logged |
| T-0B | **Approve data contract v0.1.0 (D-016)** | M1 | P0 | T-000 | — | — | DONE (approved 2026-11-14) | — | Contract status APPROVED |
| T-0C | Add collaborators (Lead only) | M1 | P0 | T-000 | — | — | TODO | — | Both teammates have access |
| T-0D | Decide API owner (D-015) and repo directory layout | M1 | P0 | T-0A | — | — | DONE (approved 2026-11-14: pipeline/, api/, app/; API owner M3) | — | Logged |
| T-0F | Decide technical protection of `main` (D-019) | M1 | P1 | — | — | — | TODO | — | Logged; any settings change made by the Lead |
| T-0G | Teammate workstream prompts (Member 2, Member 3) + stale-status fixes | M1 | P0 | T-0E | `docs/T-0G-teammate-prompts` | [#3](https://github.com/vishalbg02/global-fire-harmonization/pull/3) | MERGED (2026-11-14, PR #3) | — (Lead-authored PR) | Lead approves both prompts; prompts consistent with DATA_CONTRACT v0.1.0 |
| T-0H | Record D-008 and D-016 approvals across docs and prompts | M1 | P0 | T-0G | `docs/T-0H-record-approvals` | *(see PR list)* | IN_REVIEW | PENDING | Approvals reflected consistently on `main` |

## Data and science (Member 2)

| ID | Task | Owner | Pri | Depends | Branch | PR | Status | Review | Acceptance criteria |
|---|---|---|---|---|---|---|---|---|---|
| T-001 | Download all global zips (MODIS 2002–2025, S-NPP 2012–2025, NOAA-20 2018–2025) | M2 | P0 | — (stack-independent) | `data/T-001-download-zips` | — | TODO | — | All files present; sizes match `DATA_SOURCES.md`; snapshot recorded in `data/README.md` |
| T-002 | Pull 2026 data via the area API (world, 5-day windows) for MODIS, S-NPP, NOAA-20; fetch `missing_data` and `data_availability` | M2 | P0 | MAP_KEY | `data/T-002-api-2026` | — | TODO | — | Complete date coverage logged; retries recorded |
| T-003 | Unzip and normalize to the unified schema (Parquet) | M2 | P0 | T-001, T-0A, T-0D | `data/T-003-normalize` | — | TODO | — | Row counts per sensor and year recorded |
| T-004 | Fire-region mask (GFED basis regions) or UN-subregion fallback | M1 → M2 | P0 | — | `science/T-004-region-mask` | — | TODO | — | Every analysis cell has a `fire_region` |
| T-005 | Filters + static-source mask + QA summary | M2 | P0 | T-003 | `data/T-005-filters-qa` | — | TODO | — | QA table; estimates in `DATA_SOURCES.md` replaced with measurements |
| T-006 | Fine-grid cell-days → analysis cell-month per witness × day/night | M2 | P0 | T-005, D-009 | `data/T-006-gridding` | — | TODO | — | `cell_month_witness` validates against the contract |
| T-007 | Investigate MODIS `version` values (6.2 / 6.03 / 61.03) | M2 | P1 | T-003 | `data/T-007-modis-version` | — | TODO | — | Finding documented; any method impact logged |
| T-008 | Confirm Aqua/Terra 2026 availability via `data_availability` | M2 | P0 | MAP_KEY | `data/T-008-availability` | — | TODO | — | Result in `DATA_SOURCES.md` |
| T-009 | FIRMS country name → ISO3 / continent mapping | M2 | P0 | T-003 | `data/T-009-country-mapping` | — | TODO | — | 100% of country files mapped |
| T-010 | SYNTHETIC fixtures for all contract products | M2 | P0 | T-0B | `data/T-010-fixtures` | — | TODO | — | Labelled synthetic; <5 MB; validate against the contract |
| T-011 | Calibration ratios with partial pooling + block bootstrap | M2 | P0 | T-006, T-004 | `science/T-011-calibration` | — | TODO | — | `calibration` product; pooling levels reported |
| T-012 | Holdout evaluation 2017–2021; Aqua drift diagnostic | M2 | P0 | T-011 | `science/T-012-holdout-drift` | — | TODO | — | Scores and drift plot presented at R2 |
| T-013 | Witness combination + disagreement inflation; `harmonize_area()` | M2 | P0 | T-011 | `science/T-013-combination` | — | TODO | — | Unit tests on synthetic data with known answers |
| T-014 | Baseline, probabilities, verdicts, reason codes; entity aggregation | M2 | P0 | T-013, D-010 | `science/T-014-verdicts` | — | TODO | — | `cell_month_harmonized`, `entity_month`, `metadata.json` validate |
| T-015 | Large-fire consistency check | M2 | P1 | T-006 | `science/T-015-large-fire` | — | TODO | — | Diagnostic series per entity |
| T-016 | "MODIS blindness" indicator | M2 | P1 | T-011 | `science/T-016-blindness` | — | TODO | — | Per-region value with caveat text |

## Validation (Member 2 implements; Member 1 defines and reviews)

| ID | Task | Owner | Pri | Depends | Branch | PR | Status | Review | Acceptance criteria |
|---|---|---|---|---|---|---|---|---|---|
| T-050 | Define case windows, bounding boxes, quiet months | M1 | P0 | — | `docs/T-050-validation-cases` | — | TODO | — | Table in `VALIDATION_PLAN.md` |
| T-051 | **G1 lock**: grid, baseline, verdict and validation thresholds | M1 | P0 | T-006 | `docs/T-051-g1-lock` | — | TODO | — | Logged as approved before any results |
| T-020 | Test A1 (two independent paths) | M2 | P0 | T-014, T-050 | `science/T-020-test-a1` | — | TODO | — | Results recorded, pass or fail |
| T-021 | Tests B1 (satellite-change steps) + B3 (known artifacts) | M2 | P0 | T-014 | `science/T-021-test-b` | — | TODO | — | Recorded |
| T-022 | Tests D1 (coverage) + D2 (gaps) | M2 | P0 | T-012, T-014 | `science/T-022-test-d` | — | TODO | — | Recorded |
| T-023 | Test A2 (same fire, two eras) | M2 | P1 | T-014, T-050 | `science/T-023-test-a2` | — | TODO | — | Recorded |
| T-024 | Tests B2, C1, CTRL | M2 | P1 | T-014 | `science/T-024-test-b2-c1-ctrl` | — | TODO | — | Recorded |
| T-025 | Tests E1 (leave one region out) + S1 (sensitivity) | M2 | P1 | T-011 | `science/T-025-test-e1-s1` | — | TODO | — | Recorded |
| T-026 | Verify every number displayed in the app/demo against products | M2 + M1 | P0 | T-039 | `science/T-026-number-check` | — | TODO | — | Checklist signed off |

## Application and API (Member 3)

| ID | Task | Owner | Pri | Depends | Branch | PR | Status | Review | Acceptance criteria |
|---|---|---|---|---|---|---|---|---|---|
| T-030 | Environment setup per the approved stack; app skeleton | M3 | P0 | T-0A, T-0D | `Swastik` (accepted for this task only) | [#5](https://github.com/vishalbg02/global-fire-harmonization/pull/5) | ASSIGNED (2026-11-14) | — | Runs locally for M1 and M3 |
| T-031 | Global map: country layer + analysis-cell layer | M3 | P0 | T-030, T-010 | `frontend/T-031-global-map` | — | TODO | — | Selected month renders; tooltip per cell |
| T-032 | Calendar (years × months; % of normal / activity) | M3 | P0 | T-010 | `frontend/T-032-calendar` | — | TODO | — | Accessible ramps; legend; null shown as "no data" |
| T-033 | Raw vs harmonized toggle | M3 | P0 | T-032 | `frontend/T-033-toggle` | — | TODO | — | Switches calendar and map |
| T-034 | API skeleton serving fixtures (all endpoints) | M3 | P0 | T-010, T-0D | `api/T-034-api-skeleton` | — | TODO | — | Responses validate against the contract |
| T-035 | Country/continent selection + rectangle custom area | M3 | P0 | T-034 | `frontend/T-035-area-selection` | — | TODO | — | Custom area returns a series via `harmonize_area()` |
| T-036 | Evidence panel (verdict, probability, reason codes in plain language) | M3 | P0 | T-034 | `frontend/T-036-evidence-panel` | — | TODO | — | Every reason code has user-facing text approved by M1 |
| T-037 | Witness comparison chart + satellite timeline + outages | M3 | P0 | T-034 | `frontend/T-037-witness-chart` | — | TODO | — | Per-witness raw and converted series |
| T-038 | CSV export | M3 | P0 | T-034 | `api/T-038-csv-export` | — | TODO | — | Header with method version, snapshot date, citation |
| T-039 | Real-data integration | M3 + M2 | P0 | T-014 | `frontend/T-039-real-data` | — | TODO | — | All views on real products |
| T-040 | Global anomaly list | M3 | P0 | T-034 | `frontend/T-040-anomaly-list` | — | TODO | — | Ranked by probability; links to the entity |
| T-041 | Methods + validation results page | M3 | P0 | T-020+ | `frontend/T-041-methods-page` | — | TODO | — | Shows PASS/FAIL/NOT_RUN faithfully |
| T-042 | Performance and accessibility pass | M3 | P1 | T-039 | `frontend/T-042-perf-a11y` | — | TODO | — | Keyboard navigation; colour-blind-safe check |
| T-043 | Static fallback build; optional deploy | M3 | P1 | T-039 | `frontend/T-043-static-build` | — | TODO | — | Preset views work without the API |
| T-044 | Free-polygon custom area | M3 | P1 | T-035 | `frontend/T-044-polygon` | — | TODO | — | — |

## Demo and submission (Member 1)

| ID | Task | Owner | Pri | Depends | Branch | PR | Status | Review | Acceptance criteria |
|---|---|---|---|---|---|---|---|---|---|
| T-060 | Demo storyline (30 s cut + ~3 min) | M1 | P0 | — | `docs/T-060-demo-script` | — | TODO | — | Script in the repo |
| T-061 | Record the demo; English subtitles | M1 | P0 | T-039 | — (outside the repo) | — | TODO | — | Uses real data only |
| T-062 | Space Apps project page with references | M1 | P0 | — | — (outside the repo) | — | TODO | — | All sources cited |
| T-063 | Submit by H34 | M1 | P0 | T-061, T-062 | — | — | TODO | — | Confirmed on the site |
| T-064 | Decide repo visibility for judges (D-014) | M1 | P0 | — | — | — | TODO | — | Logged |
