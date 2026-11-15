# Task prompt: T-025b Test S1, confidence-filter half

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main @ cd4a532
> Source of truth: docs/TASK_TRACKER.md row T-025b (on PR #61). This prompt adds no scope beyond it.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand, `docs/PROJECT_PLAN.md`). Hotspot detections of Aqua MODIS, S-NPP VIIRS and NOAA-20 VIIRS are put on the Aqua-equivalent scale (T-011 ratios), combined (T-013) and judged (T-014). The Witness Stand (`docs/VALIDATION_PLAN.md`) tests this with criteria locked at G1 (D-028). S1 (sensitivity) is: "Re-run A1 and B1 without the confidence filter, and with the Aqua-measured baseline (2003-2021); conclusions unchanged (report any that change)". T-025 ran the baseline half (S1-BASELINE, FAIL by its strict rule) and recorded the confidence-filter half as NOT_RUN (`docs/validation/T-025-results.md` section 5): the products hold filtered data only, and A1 and B1 did not exist yet. They exist now (T-020, T-021).

## 2. Task objective
Run the confidence-filter half of S1 if it is feasible within a bounded effort: regrid the detections without the T-005 confidence filter, for the cells and months that A1 and B1 need only, into a private directory; re-run the A1 (C1 to C6) and B1 (2012-01, 2018-04) logic of T-020 and T-021 on that table; compare the conclusions with the filtered ones by a rule fixed here before the run. Otherwise record exactly why not (status NOT_RUN with the blocker).

## 3. Assigned responsibility
- Task ID / priority: T-025b / P1, priority 7 "if time". Owner: Member 2. Reviewer and merger: Member 1.
- Dependencies: T-025 (PR #57), T-006 (merged), T-020 (PR #55), T-021 (PR #54). The A1 and B1 modules are on main (`validation_a1.py`, `validation_b.py`).

## 4. Relevant files and directories
- Read: `CLAUDE.md`, `docs/TEAM_WORKFLOW.md` section 4, `docs/VALIDATION_PLAN.md` (S1, A1, B1, 2a), `docs/DECISION_LOG.md` D-005, D-028, D-029, `docs/validation/T-025-results.md`, `T-020-results.md`, `T-021-results.md`, `pipeline/gridding.py`, `pipeline/qa_filters.py`, `pipeline/harmonize.py`, `pipeline/validation_a1.py`, `pipeline/validation_b.py`, `pipeline/validation_e1_s1.py`.
- Create: this file; `pipeline/validation_s1_confidence.py`; `pipeline/tests/test_validation_s1_confidence.py`; `docs/validation/T-025b-results.md`.
- Not committed: everything under `data/interim/` (private tables in `data/interim/T-025b/`, entries `data/interim/qa/T-025b_validation_entries.json`, reports `T-025b_report.json`).
- Not edited: every module of an earlier task. `data/products/` is only read.

## 5. Approved technologies
Python, NumPy, pandas, DuckDB, pyarrow, pytest, ruff (D-008). Nothing is added.

## 6. Architecture and data contract
Validation component (Member 2). Output entries in the contract section 6 shape. No contract change. The private table has the shape of `cell_month_witness` and is read through `harmonize.Paths(products=<private dir>)`; nothing is written to `data/products/`.

## 7. Feasibility check (done BEFORE any run; facts read from disk and code)
1. **Data present [VERIFIED].** The normalized detections (`data/interim/detections/sensor=*/year=*/detections.parquet`, 6.3 GB, every sensor-year 2002 to 2026) are on disk, with `confidence_class` (LOW / NOMINAL / HIGH), `type`, `data_level`, `daynight` and `frp_mw` kept per row; nothing was dropped at normalization. The static mask (`static_mask_plus_night_sources.parquet`) is on disk. The raw zips are also reachable through `data/raw`. Nothing is gone.
2. **The filter is one line [VERIFIED by reading `gridding.kept_sql`].** The T-006 kept set is: confidence in NOMINAL/HIGH, SP rows of type 0 (NRT rows have no type), and not in the static mask. "Without the confidence filter" removes only the first condition; the type filter and the mask stay (S1 varies the confidence filter only). LOW is a large share of VIIRS (about 10% of S-NPP and NOAA-20 detections in 2019) and a small share of MODIS (about 5%).
3. **Scope of the regridding.** A1 needs, for each case box, the cells of the box (centre in the box, as `validation_a1.box_cells`) in the analysis window months plus the same calendar months of 2003-2022 (the baseline). B1 needs every fire-region cell for 2011-01 to 2012-12 and 2017-04 to 2019-03. The union is a few hundred months at most and a bounded set of cells; the regridding is done per year, in the T-006 way (fine 0.05 degree cell-days, then analysis 0.5 degree cell-month), only for those months and cells.
4. **Cost [estimate].** `gridding.build` over all 24 years takes 10 to 20 minutes; the restricted run scans the same files with a month filter, so about the same or less, in memory-bounded DuckDB (5 GB, per year). No heavy join with the 179 MB product beyond a filtered skeleton. Well below the "few hours" limit, so the task is feasible and is run. Free disk was 83 GB (needs 40 GB).
5. **Not touching products [VERIFIED by design].** The private directory `data/interim/T-025b/{filtered,unfiltered}/` each hold `cells.parquet` and `calibration.parquet` (copies of the product files) and a restricted `cell_month_witness.parquet`. The harness code is pointed at them by `harmonize.Paths(products=...)`.
6. **Validity gate (control).** The restricted table is built twice with the same code: with the confidence filter (control) and without. The control must reproduce the product `cell_month_witness` exactly (cell_days and detections equal in every row of the selection; `frp_sum_mw` equal to 1e-6 relative). If it does not, the regridding is not trusted and the status is NOT_RUN (blocker: the control did not reproduce the product). The "filtered" side of the comparison is the product itself restricted to the selection.

## 8. Expected outputs
- `data/interim/qa/T-025b_validation_entries.json` with entry `S1-CONFIDENCE-FILTER` (PASS, FAIL, INCONCLUSIVE or NOT_RUN), contract section 6 shape, plus `T-025b_report.json` with every number.
- `docs/validation/T-025b-results.md`.

## 9. Implementation requirements and the decision rule (fixed here, before any real run)
1. **Selection.** A1 selection: for each case C1 to C6 (`validation_a1.CASES`), the cells of its box in `cells.parquet` and the months `analysis window union (calendar months of the window x 2003..2022)`, exactly the months `validation_a1.build_case_frames` aggregates. B1 selection: every cell with a fire region (and NONE), months 2011-01..2012-12 and 2017-04..2019-03 (12 months before and after each date). Rows of the private table: every selected cell x every operated witness-month x D / N (and ALL = D + N), with `days_available`, `days_in_month` and `data_level` taken from the product row (they do not depend on the filter).
2. **Regridding.** As `gridding.observe_year` / `write_year`: kept detections, fine cell (floor((lat+90)/0.05), floor((lon wrapped+180)/0.05)), fine cell-days (distinct fine cell and date per witness and day/night), analysis cell = fine // 10, `cell_days`, `detections`, `frp_sum_mw` (non-negative FRP) per analysis cell-month, zero where nothing is detected. Only the confidence condition differs between the two builds.
3. **Calibration is not refitted [ASSUMPTION].** The T-011 ratios (v0.1 product `calibration.parquet`) stay as they are; the filter is varied in the numerators (the cell-days that are converted) only. Refitting the ratios without the filter would be a different test (a changed calibration, not a sensitivity of the conclusions), and the plan does not ask for it. Consequence: VIIRS counts rise by the LOW detections but are multiplied by ratios fitted on filtered counts, so a shift upwards is expected by construction; the test asks whether the conclusions survive it.
4. **Cells [ASSUMPTION].** The cell set is that of the product `cells.parquet`. A cell whose only detections are low confidence is not in it and is not added (it has no stratum or fire region; the calibration is not refitted). The number of unfiltered detections that fall in such cells inside the selection is reported.
5. **Re-run of A1.** `validation_a1.build_case_frames(case, Paths(products=dir))`, `entry_for` and `family_entry`, unchanged, for both tables. The official reading per case is `FORMAL_READING` (C1 own baseline, C2 to C6 shared Aqua baseline). The filtered side is also compared with the stored T-020 statuses (data/interim/qa/T-020_validation_entries.json) as a check.
6. **Re-run of B1.** As `validation_b.run`: fire-region entities, `harmonize.aggregate` over the selected months, `records_from`, `evaluate_b1`, `b1_status` for each of the two dates, for both tables. The raw step is taken from the table itself (so it also changes, as raw cell-days change).
7. **Peak-window verdicts (the S1 rule of T-025).** For the six case boxes the harmonized series (`records_from` on the box) is judged with `validation_e1_s1.verdict_for` against its own baseline of the same calendar month 2003-2022 (`baselines`, as `compare_baselines` for the harmonized baseline), for each month of the case peak window (`validation_e1_s1.CASES`), for both tables.
8. **Rule.** S1-CONFIDENCE-FILTER is:
   - **PASS** if all of the following are unchanged between the filtered and the unfiltered run: (a) the official A1 status of each of C1 to C6 (six comparisons); (b) the A1 family status; (c) the B1 status at 2012-01 and at 2018-04 (two comparisons); (d) the verdict of every peak-window month of C1 to C6 (13 months). A status that is INCONCLUSIVE in both runs counts as unchanged.
   - **FAIL** if any of (a) to (d) changes. Every change is reported with its numbers (it is a failure of "conclusions unchanged"; nothing is excused as borderline, as in S1-BASELINE).
   - **INCONCLUSIVE** if a part cannot be computed in one of the two runs (an exception or a missing table), but nothing computable changed.
   - **NOT_RUN** if the control (section 7.6) fails or the regridding cannot be done; the exact blocker is the notes.
   Not part of the rule, reported as context: how far each case's S-NPP-only and NOAA-20 estimates move (ratio unfiltered / filtered), the B1 harmonized and raw steps, the dropped detections in cells outside the product cell set.
9. **S1 overall.** S1 = S1-BASELINE and S1-CONFIDENCE-FILTER. S1 is PASS only if both halves PASS; FAIL if either FAILs; otherwise INCONCLUSIVE or NOT_RUN as the halves are. This is reported in the results file; the integration into `validation_results.json` is T-027's.
10. No result is invented; missing data stay missing; synthetic fixtures only in tests, labelled SYNTHETIC.

## 10. Constraints: do not modify
Tech stack, architecture, methodology, data contract, thresholds (D-028, plan section 3) and any earlier module. No writes under `data/products/`. No raw or interim data committed. No push to main, no merge, no approval, no AI attribution (D-020).

## 11. Acceptance criteria
(1) The feasibility finding is written; (2) the control reproduces the product, or the blocker is stated; (3) the rule above is applied exactly as written and every change is listed; (4) entries in contract section 6 shape; (5) tests and ruff pass.

## 12. Required tests
`python -m pytest pipeline/tests/test_validation_s1_confidence.py -q -p no:cacheprovider`; `python -m ruff check pipeline/validation_s1_confidence.py pipeline/tests/test_validation_s1_confidence.py`; then the whole suite. SYNTHETIC tests with known answers: the regridding of a tiny planted detection set with and without the confidence condition (known cell-days, zero fill, ALL = D + N, wrap of longitude, mask applied, type filter kept); the control equality check detects a planted difference; the comparison rule (PASS / FAIL / INCONCLUSIVE / NOT_RUN) on hand-made statuses; the S1 overall combination. Mutation check: drop the type filter or the mask from the regridding, confirm a test fails, restore.

## 13. Documentation updates
`docs/validation/T-025b-results.md`. The tracker row T-025b only once PR #61 is on main (otherwise the Lead updates it; stated in the PR).

## 14. Git branch and PR instructions
Branch `science/T-025b-s1-confidence` from the latest main; first commit this prompt; a draft PR early; no merge. Commit with the contributor's own identity; no AI names or attribution.

## 15. Open points and [ASSUMPTION]s for the Lead
1. The ratios of T-011 are not refitted (9.3). 2. The cell set is the product's (9.4). 3. The strict rule (a)-(d): any single change is a FAIL, as for S1-BASELINE. 4. "Without the confidence filter" removes the confidence condition only; the type filter and the D-025 static mask stay. 5. The comparison is on the v0.1 products on main. If the Lead adopts v0.2 (T-020c) the same command re-runs on the new products. 6. S1-BASELINE (T-025) is not repeated.
