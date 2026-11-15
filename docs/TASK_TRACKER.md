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

> **Stack (D-008) and data contract v0.1.0 (D-016) approved on 2026-11-14 at 12:26 IST (H0).** Implementation tasks are assigned in the table below. **Layout (T-0D) approved:** `pipeline/` (Member 2), `api/` and `app/` (Member 3). **Member 3 owns the API (D-015).** Every task is now assignable once its dependencies are merged. Branch names below are the planned names; the Lead confirms them at assignment.
>
> **Workstream prompts:** Member 2 → [`prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md`](prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md) · Member 3 → [`prompts/MEMBER_3_APPLICATION_PROMPT.md`](prompts/MEMBER_3_APPLICATION_PROMPT.md). For each assigned task, the teammate's session still writes a task prompt in `task-prompts/`.

## Setup and governance

| ID | Task | Owner | Pri | Depends | Branch | PR | Status | Review | Acceptance criteria |
|---|---|---|---|---|---|---|---|---|---|
| T-000 | Planning docs + private repo created | M1 | P0 | — | `main` (bootstrap) | — | MERGED (2026-11-14) | n/a (bootstrap) | Repo private; docs pushed; no secrets |
| T-0E | Team workflow docs (TEAM_WORKFLOW, PR template, push guard) | M1 | P0 | T-000 | `docs/team-workflow` | [#2](https://github.com/vishalbg02/global-fire-harmonization/pull/2) (supersedes #1) | MERGED (2026-11-14, merge commit cc940ba) | — (Lead-authored PR; GitHub does not allow self-approval) | Lead approves the workflow (D-017) |
| T-0A | **Approve tech stack (D-008)** | M1 | P0 | T-000 | — | — | DONE (approved 2026-11-14 12:26 IST) | — | `TECH_STACK.md` marked APPROVED; D-008 logged |
| T-0B | **Approve data contract v0.1.0 (D-016)** | M1 | P0 | T-000 | — | — | DONE (approved 2026-11-14) | — | Contract status APPROVED |
| T-0C | Add collaborators (Lead only) | M1 | P0 | T-000 | — | — | DONE (2026-11-14; Member 2 and Member 3 have access) | — | Both teammates have access |
| T-0D | Decide API owner (D-015) and repo directory layout | M1 | P0 | T-0A | — | — | DONE (approved 2026-11-14: pipeline/, api/, app/; API owner M3) | — | Logged |
| T-0F | Decide technical protection of `main` (D-019) | M1 | P1 | — | — | — | TODO | — | Logged; any settings change made by the Lead |
| T-0G | Teammate workstream prompts (Member 2, Member 3) + stale-status fixes | M1 | P0 | T-0E | `docs/T-0G-teammate-prompts` | [#3](https://github.com/vishalbg02/global-fire-harmonization/pull/3) | MERGED (2026-11-14, PR #3) | — (Lead-authored PR) | Lead approves both prompts; prompts consistent with DATA_CONTRACT v0.1.0 |
| T-0H | Record D-008 and D-016 approvals across docs and prompts | M1 | P0 | T-0G | `docs/T-0H-record-approvals` | [#4](https://github.com/vishalbg02/global-fire-harmonization/pull/4) | MERGED (2026-11-14) | APPROVED | Approvals reflected consistently on `main` |

## Data and science (Member 2)

| ID | Task | Owner | Pri | Depends | Branch | PR | Status | Review | Acceptance criteria |
|---|---|---|---|---|---|---|---|---|---|
| T-001 | Download all global zips (MODIS 2002–2025, S-NPP 2012–2025, NOAA-20 2018–2025) | M2 | P0 | — (stack-independent) | `data/T-001-download-zips` | [#7](https://github.com/vishalbg02/global-fire-harmonization/pull/7) | MERGED (2026-11-14) | APPROVED | All files present; sizes match `DATA_SOURCES.md`; snapshot recorded in `data/README.md` |
| T-002 | Pull 2026 data via the area API (world, 5-day windows) for MODIS, S-NPP, NOAA-20; fetch `missing_data` and `data_availability` | M2 | P0 | MAP_KEY | `data/T-002-api-2026` | [#9](https://github.com/vishalbg02/global-fire-harmonization/pull/9) | MERGED (2026-11-14) | APPROVED | Complete date coverage logged; retries recorded |
| T-003 | Unzip and normalize to the unified schema (Parquet) | M2 | P0 | T-001, T-0A, T-0D | `data/T-003-normalize` | [#17](https://github.com/vishalbg02/global-fire-harmonization/pull/17) | MERGED (2026-11-14) | APPROVED | Row counts per sensor and year recorded |
| T-004 | Fire-region mask (GFED basis regions) or UN-subregion fallback | M2 | P0 | — | `science/T-004-region-mask` | [#29](https://github.com/vishalbg02/global-fire-harmonization/pull/29) | MERGED (2026-11-14) | APPROVED | Every analysis cell has a `fire_region` |
| T-005 | Filters + static-source mask + QA summary | M2 | P0 | T-003 | `data/T-005-filters-qa` | [#25](https://github.com/vishalbg02/global-fire-harmonization/pull/25) | MERGED (2026-11-14) | APPROVED | QA table; estimates in `DATA_SOURCES.md` replaced with measurements |
| T-006 | Fine-grid cell-days → analysis cell-month per witness × day/night | M2 | P0 | T-005, D-009 | `data/T-006-gridding` | [#34](https://github.com/vishalbg02/global-fire-harmonization/pull/34) | MERGED (2026-11-14) | APPROVED | `cell_month_witness` validates against the contract |
| T-007 | Investigate MODIS `version` values (6.2 / 6.03 / 61.03) | M2 | P1 | T-003 | `data/T-007-modis-version` | [#31](https://github.com/vishalbg02/global-fire-harmonization/pull/31) | MERGED (2026-11-14) | APPROVED | Finding documented; any method impact logged |
| T-008 | Confirm Aqua/Terra 2026 availability via `data_availability` | M2 | P0 | MAP_KEY | `data/T-008-availability` | [#10](https://github.com/vishalbg02/global-fire-harmonization/pull/10) | MERGED (2026-11-14) | APPROVED | Result in `DATA_SOURCES.md` |
| T-009 | FIRMS country name → ISO3 / continent mapping | M2 | P0 | T-003 | `data/T-009-country-mapping` | [#21](https://github.com/vishalbg02/global-fire-harmonization/pull/21) | MERGED (2026-11-14) | APPROVED | 100% of country files mapped |
| T-010 | SYNTHETIC fixtures for all contract products | M2 | P0 | T-0B | `data/T-010-fixtures` | [#15](https://github.com/vishalbg02/global-fire-harmonization/pull/15) | MERGED (2026-11-14) | APPROVED | Labelled synthetic; <5 MB; validate against the contract |
| T-011 | Calibration ratios with partial pooling + block bootstrap | M2 | P0 | T-006, T-004 | `science/T-011-calibration` | [#36](https://github.com/vishalbg02/global-fire-harmonization/pull/36) | MERGED (2026-11-14) | APPROVED | `calibration` product; pooling levels reported |
| T-012 | Holdout evaluation 2017–2021; Aqua drift diagnostic | M2 | P0 | T-011 | `science/T-012-holdout-drift` | [#45](https://github.com/vishalbg02/global-fire-harmonization/pull/45) | MERGED (2026-11-14) | APPROVED | Scores and drift plot presented at R2 |
| T-013 | Witness combination + disagreement inflation; `harmonize_area()` | M2 | P0 | T-011 | `science/T-013-combination` | [#43](https://github.com/vishalbg02/global-fire-harmonization/pull/43) | MERGED (2026-11-14) | APPROVED | Unit tests on synthetic data with known answers |
| T-014 | Baseline, probabilities, verdicts, reason codes; entity aggregation | M2 | P0 | T-013, D-010 | `science/T-014-verdicts` | [#52](https://github.com/vishalbg02/global-fire-harmonization/pull/52) | MERGED (2026-11-15) | APPROVED | `cell_month_harmonized`, `entity_month`, `metadata.json` validate |
| T-014a | Raw-only `cell_month_harmonized`, `entity_month` and `metadata.json` for the app (D-026) | M2 | P0 | T-006, T-009 | `science/T-014a-raw-only-products` | [#40](https://github.com/vishalbg02/global-fire-harmonization/pull/40) | MERGED (2026-11-14) | APPROVED | Contract 0.1.1 raw-only shape; every harmonized field null; `NOT_HARMONIZED`; totals reconcile |
| T-015 | Large-fire consistency check | M2 | P1 | T-006 | `science/T-015-large-fire` | [#66](https://github.com/vishalbg02/global-fire-harmonization/pull/66) | MERGED (2026-11-15; #66) | APPROVED | Diagnostic series per entity |
| T-016 | "MODIS blindness" indicator | M2 | P1 | T-011 | `science/T-016-blindness` | [#65](https://github.com/vishalbg02/global-fire-harmonization/pull/65) | MERGED (2026-11-15; #65) | APPROVED | Per-region value with caveat text |

## Validation (Member 2 implements; Member 1 defines and reviews)

| ID | Task | Owner | Pri | Depends | Branch | PR | Status | Review | Acceptance criteria |
|---|---|---|---|---|---|---|---|---|---|
| T-050 | Define case windows, bounding boxes, quiet months | M1 | P0 | — | `docs/T-050-validation-cases` | [#51](https://github.com/vishalbg02/global-fire-harmonization/pull/51) | MERGED (2026-11-14) | APPROVED | Table in `VALIDATION_PLAN.md` |
| T-051 | **G1 lock**: grid, baseline, verdict and validation thresholds | M1 | P0 | T-006 | `docs/T-051-g1-lock` | [#51](https://github.com/vishalbg02/global-fire-harmonization/pull/51) | MERGED (2026-11-14) | APPROVED | Logged as approved before any results |
| T-020 | Test A1 (two independent paths) | M2 | P0 | T-014, T-050 | `science/T-020-test-a1` | [#55](https://github.com/vishalbg02/global-fire-harmonization/pull/55) | MERGED (2026-11-15) | APPROVED | Results recorded, pass or fail |
| T-020b | Extreme-month diagnostic after A1 FAIL (cell-day saturation) | M2 | P0 | T-020, T-011 | `science/T-020b-extreme-months` | [#58](https://github.com/vishalbg02/global-fire-harmonization/pull/58) | MERGED (2026-11-15) | APPROVED | Fit periods only; ratio by activity bin with intervals; decision by a pre-set rule |
| T-020c | v0.2 activity-dependent conversion (D-030, post-hoc after A1): build, compare with v0.1, adopt only by the pre-registered rule | M2 | P0 | T-020b | `science/T-020c-v02-conversion` | [#64](https://github.com/vishalbg02/global-fire-harmonization/pull/64) | MERGED (2026-11-15; rule not met, D-030 NOT ADOPTED, v0.1 stays) | APPROVED | Holdout error no worse (regions and countries); D1 pooled 80–97%; A1 gap smaller in ≥3 of 4 failed cases; v0.1 kept visible |
| T-021 | Tests B1 (satellite-change steps) + B3 (known artifacts) | M2 | P0 | T-014 | `science/T-021-test-b` | [#54](https://github.com/vishalbg02/global-fire-harmonization/pull/54) | MERGED (2026-11-15) | APPROVED | Recorded |
| T-022 | Tests D1 (coverage) + D2 (gaps) | M2 | P0 | T-012, T-014 | `science/T-022-test-d` | [#56](https://github.com/vishalbg02/global-fire-harmonization/pull/56) | MERGED (2026-11-15) | APPROVED | Recorded |
| T-023 | Test A2 (same fire, two eras) | M2 | P1 | T-014, T-050 | `science/T-023-test-a2` | [#68](https://github.com/vishalbg02/global-fire-harmonization/pull/68) | MERGED (2026-11-15; #68) | APPROVED | Recorded |
| T-024 | Tests B2, C1, CTRL | M2 | P1 | T-014 | `science/T-024-test-b2-c1-ctrl` | [#69](https://github.com/vishalbg02/global-fire-harmonization/pull/69) | MERGED (2026-11-15; #69) | APPROVED | Recorded |
| T-025 | Tests E1 (leave one region out) + S1 (sensitivity) | M2 | P1 | T-011 | `science/T-025-test-e1-s1` | [#57](https://github.com/vishalbg02/global-fire-harmonization/pull/57) | MERGED (2026-11-15) | APPROVED | Recorded |
| T-025b | Test S1, confidence-filter half: regrid without the T-005 confidence filter, re-run A1 and B1, record the outcome | M2 | P1 | T-025, T-006 | `science/T-025b-s1-confidence` | [#67](https://github.com/vishalbg02/global-fire-harmonization/pull/67) | MERGED (2026-11-15; #67) | APPROVED | S1-CONFIDENCE-FILTER recorded (PASS, FAIL or INCONCLUSIVE); S1 overall updated |
| T-027 | Validation integration: write every real test status into `validation_results.json` and `VALIDATION_PLAN.md` §4 | M2 | P0 | T-020, T-021, T-022, T-025 | `science/T-027-validation-integration` | [#70](https://github.com/vishalbg02/global-fire-harmonization/pull/70) | MERGED (2026-11-15; #70) | APPROVED | Every test entry with its real status (PASS, FAIL, INCONCLUSIVE, NOT_RUN), D1 per-region and night entries, A1 family FAIL; contract check passes; methods page shows them |
| T-026 | Verify every number displayed in the app/demo against products | M2 + M1 | P0 | T-039 | `science/T-026-number-check` | [#71](https://github.com/vishalbg02/global-fire-harmonization/pull/71) | MERGED (2026-11-15; #71, signed off by the Lead) | APPROVED | Checklist signed off |

## Application and API (Member 3)

| ID | Task | Owner | Pri | Depends | Branch | PR | Status | Review | Acceptance criteria |
|---|---|---|---|---|---|---|---|---|---|
| T-030 | Environment setup per the approved stack; app skeleton | M3 | P0 | T-0A, T-0D | `Swastik` (accepted for this task only) | [#5](https://github.com/vishalbg02/global-fire-harmonization/pull/5) | MERGED (2026-11-14) | APPROVED | Runs locally for M1 and M3 |
| T-031 | Global map: country layer + analysis-cell layer | M3 | P0 | T-030, T-010 | `frontend/T-031-global-map` | [#14](https://github.com/vishalbg02/global-fire-harmonization/pull/14) | MERGED (2026-11-14) | APPROVED | Selected month renders; tooltip per cell |
| T-032 | Calendar (years × months; % of normal / activity) | M3 | P0 | T-010 | `frontend/T-032-calendar` | [#20](https://github.com/vishalbg02/global-fire-harmonization/pull/20) | MERGED (2026-11-14) | APPROVED | Accessible ramps; legend; null shown as "no data" |
| T-033 | Raw vs harmonized toggle | M3 | P0 | T-032 | `frontend/T-033-toggle` | [#24](https://github.com/vishalbg02/global-fire-harmonization/pull/24) | MERGED (2026-11-14) | APPROVED | Switches calendar and map |
| T-034 | API skeleton serving fixtures (all endpoints) | M3 | P0 | T-010, T-0D | `api/T-034-api-skeleton` | [#16](https://github.com/vishalbg02/global-fire-harmonization/pull/16) | MERGED (2026-11-14) | APPROVED | Responses validate against the contract |
| T-035 | Country/continent selection + rectangle custom area | M3 | P0 | T-034 | `frontend/T-035-area-selection` | [#30](https://github.com/vishalbg02/global-fire-harmonization/pull/30) | MERGED (2026-11-14) | APPROVED | Custom area returns a series via `harmonize_area()` |
| T-036 | Evidence panel (verdict, probability, reason codes in plain language) | M3 | P0 | T-034 | `frontend/T-036-evidence-panel` | [#28](https://github.com/vishalbg02/global-fire-harmonization/pull/28) | MERGED (2026-11-14) | APPROVED | Every reason code has user-facing text approved by M1 |
| T-037 | Witness comparison chart + satellite timeline + outages | M3 | P0 | T-034 | `frontend/T-037-witness-chart` | [#33](https://github.com/vishalbg02/global-fire-harmonization/pull/33) | MERGED (2026-11-14) | APPROVED | Per-witness raw and converted series |
| T-038 | CSV export | M3 | P0 | T-034 | `api/T-038-csv-export` | [#37](https://github.com/vishalbg02/global-fire-harmonization/pull/37) | MERGED (2026-11-14) | APPROVED | Header with method version, snapshot date, citation |
| T-039 | Real-data integration | M3 + M2 | P0 | T-014 | `frontend/T-039-real-data` | [#39](https://github.com/vishalbg02/global-fire-harmonization/pull/39), [#46](https://github.com/vishalbg02/global-fire-harmonization/pull/46), [#47](https://github.com/vishalbg02/global-fire-harmonization/pull/47), [#62](https://github.com/vishalbg02/global-fire-harmonization/pull/62), [#72](https://github.com/vishalbg02/global-fire-harmonization/pull/72) | MERGED (2026-11-15; phase 1 #39, #46, #47; phase 2 #62; item 7 #72) | APPROVED | All views on real products |
| T-040 | Global anomaly list | M3 | P0 | T-034 | `frontend/T-040-anomaly-list` | [#35](https://github.com/vishalbg02/global-fire-harmonization/pull/35) | MERGED (2026-11-14) | APPROVED | Ranked by probability; links to the entity |
| T-041 | Methods + validation results page | M3 | P0 | T-020+ | `frontend/T-041-methods-page` | [#48](https://github.com/vishalbg02/global-fire-harmonization/pull/48) | MERGED (2026-11-15) | APPROVED | Shows PASS/FAIL/NOT_RUN faithfully |
| T-042 | Performance and accessibility pass | M3 | P1 | T-039 | `frontend/T-042-perf-a11y` | [#49](https://github.com/vishalbg02/global-fire-harmonization/pull/49), [#60](https://github.com/vishalbg02/global-fire-harmonization/pull/60) | MERGED (2026-11-15) | APPROVED | Keyboard navigation; colour-blind-safe check |
| T-043 | Static fallback build; optional deploy | M3 | P1 | T-039 | `frontend/T-043-static-build` | [#53](https://github.com/vishalbg02/global-fire-harmonization/pull/53) | MERGED (2026-11-15) | APPROVED | Preset views work without the API |
| T-044 | Free-polygon custom area | M3 | P1 | T-035 | `frontend/T-044-polygon` | [#63](https://github.com/vishalbg02/global-fire-harmonization/pull/63) | MERGED (2026-11-15; #63) | APPROVED | — |
| T-070 | **UI: design system and layout.** Header with name and one-line purpose; CSS design tokens (colour, type scale, spacing); consistent buttons and inputs; map as the hero with a right panel whose top shows the selected area's summary; controls grouped in one toolbar; calendar, evidence and chart reorganised so the key verdict is above the fold. Post a mock (screenshot) for the Lead's approval (T-080) before the full build | M3 | P0 | T-039 | `frontend/T-070-design-system` | [#78](https://github.com/vishalbg02/global-fire-harmonization/pull/78) | MERGED (2026-11-15; #78; follow-ups toolbar and India outline in #95, ready) | APPROVED | Screenshots at 1440x900, 1280x720 (projector) and 375; nothing that was shown is lost; tests, lint, build pass |
| T-071 | **UI: map experience.** Open on the latest determinable month (2026-10, not the all-grey 2026-11); page scroll never zooms the map (zoom with Ctrl/Cmd + scroll or the buttons, with a hint); legend on the map; lighter cell outlines; `NO_DETECTED_ACTIVITY` clearly different from `BELOW_NORMAL` (colour-blind safe, icon kept); loading state; clicked cell info stays pinned | M3 | P0 | T-070 | `frontend/T-071-map-ux` | [#80](https://github.com/vishalbg02/global-fire-harmonization/pull/80) | MERGED (2026-11-15; #80) | APPROVED | Before/after screenshots; display only, no product value changes |
| T-072 | **UI: summary card and featured stories.** Above-the-fold card for the selected area and month (verdict, probability, % of normal, 90% interval, a 12-month sparkline, reason text); featured quick-picks with captions from T-079 (Indonesia 2015-09, Australia 2019-12 country, Canada 2023-08, Brazil 2019-08, World 2026-10); a short dismissible "How to read this" for first-time users | M3 | P0 | T-070, T-079 | `frontend/T-072-summary-stories` | [#82](https://github.com/vishalbg02/global-fire-harmonization/pull/82) | MERGED (2026-11-15; #82, with the Analytics tab and the T-070 follow-ups) | APPROVED | A judge understands the main verdict without scrolling; screenshots |
| T-073 | **Performance: map payload and month switching.** `/api/map` is about 3.1 MB per month even gzipped (measured 2026-11-15); reduce it (only the fields each layer needs; transport precision consistent with `docs/NUMBER_INVENTORY.md`), cache and prefetch adjacent months; no contract change without the Lead's approval | M3 | P1 | T-070 | `perf/T-073-map-payload` | [#81](https://github.com/vishalbg02/global-fire-harmonization/pull/81) | MERGED (2026-11-15; #81) | APPROVED | Payload and switch time measured before and after; T-026 checker still 0 mismatches |
| T-074 | **UI: responsive, accessibility and offline copy.** Phone 375 (the month label is cut off today), tablet, keyboard-only path, visible focus, WCAG AA contrast, automated accessibility check (axe or Lighthouse a11y >= 95); regenerate the offline copy after the UI work and test it in the browser | M3 | P0 | T-070, T-071, T-072 | `frontend/T-074-responsive-a11y` | [#83](https://github.com/vishalbg02/global-fire-harmonization/pull/83) | MERGED (2026-11-15; #83) | APPROVED | Scores and screenshots in the PR; offline copy opens and works |
| T-084 | **Map: realistic Earth (D-032).** NASA GIBS Blue Marble shaded-relief basemap; optional Aqua MODIS true-colour "satellite view" for a day of the selected month (date on the map); Globe / Flat switch (MapLibre globe) if the deck.gl cells render correctly on it; cells semi-transparent over the imagery; GIBS credit and link on the map; offline copy falls back to the plain background with a note | M3 | P0 | T-070, T-071 | `frontend/T-084-earth-imagery` | [#89](https://github.com/vishalbg02/global-fire-harmonization/pull/89) | MERGED (2026-11-15; #89) | APPROVED | Screenshots flat and globe at 1440x900, 1280x720 and 375; GIF of rotate, zoom, select; tile URLs recorded in `DATA_SOURCES.md`; no product value changes |

## Demo and submission (Member 1)

| ID | Task | Owner | Pri | Depends | Branch | PR | Status | Review | Acceptance criteria |
|---|---|---|---|---|---|---|---|---|---|
| T-060 | Demo storyline (30 s cut + ~3 min) | M1 | P0 | — | `docs/T-060-demo-script` | — | TODO | — | Script in the repo |
| T-061 | Record the demo; English subtitles | M1 | P0 | T-039 | — (outside the repo) | — | TODO | — | Uses real data only |
| T-062 | Space Apps project page with references | M1 | P0 | — | — (outside the repo) | — | TODO | — | All sources cited |
| T-063 | Submit by H34 | M1 | P0 | T-061, T-062 | — | — | TODO | — | Confirmed on the site |
| T-064 | Decide repo visibility for judges (D-014) | M1 | P0 | — | — | — | TODO | — | Logged |
