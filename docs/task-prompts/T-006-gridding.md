# Task prompt: T-006 Fine-grid cell-days to analysis cell-month, per witness and day/night

> Prepared for: Member 2 · Date: 2026-11-14 · Based on main @ a9ebc03
> Source of truth: docs/TASK_TRACKER.md row T-006 (assigned by the Lead's assignment PR #27; unblocked by D-009 locked at G1). This prompt adds no scope beyond it.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand): harmonize NASA FIRMS hotspot detections from several satellites (`docs/PROJECT_PLAN.md`). T-003 normalized the detections, T-004 gave every analysis cell a fire region, T-005 defined the filters and the static-source mask, and D-009 locked the grids: **analysis cells 0.5 degrees, fine cells 0.05 degrees**. T-006 turns the detections into the raw per-witness observations that calibration (T-011) and the combination (T-013) consume.

## 2. Task objective
Two real products under `data/products/` (local, not committed): `cells.parquet` (one row per analysis cell that has activity) and `cell_month_witness.parquet` (one row per cell x month x witness x day/night, for every month the witness operated, including months with zero cell-days), both validating against `docs/DATA_CONTRACT.md` v0.1.0. A G1 evidence table and the sensor-jump check are recorded in `docs/DATA_SOURCES.md`.

## 3. Assigned responsibility
- Task ID / priority: T-006 / P0
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-005 (merged), D-009 (locked 2026-11-14)

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/DATA_CONTRACT.md` §1 and §2, `docs/SCIENTIFIC_METHODOLOGY.md` §4.1 and §4.2, `docs/prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md` §8, §10, §12 and §S.3, `docs/DATA_SOURCES.md` (QA, mask, fire regions, country mapping), `docs/DECISION_LOG.md`
- Create/modify:
  - `docs/task-prompts/T-006-gridding.md` (this file)
  - `pipeline/gridding.py` (builds both products)
  - `pipeline/tests/test_gridding.py`
  - `pipeline/grid_test.py` and `pipeline/tests/test_grid_test.py` (the D-009 comparison, added at the Lead's request)
  - `docs/DATA_SOURCES.md` (G1 evidence table, availability rules, results)
  - `docs/TASK_TRACKER.md` (row T-006 only)
- Not committed: everything under `data/products/`

## 5. Approved technologies
Python and DuckDB (D-008), pyarrow, pytest, ruff. No new dependency.

## 6. Architecture and data contract
`DATA_CONTRACT.md` v0.1.0: `cells.parquet` (§1) and `cell_month_witness.parquet` (§2). Conventions: `cell_id` = `g050_r{row:04d}_c{col:04d}` (row from the south, column from -180; D-022 still proposed), cell bounds lower-inclusive, UTC months, `null` for unknown and `0` only for a real zero.

## 7. Inputs
- `data/interim/detections/` (T-003), `data/interim/qa/static_mask_fine0.05_share0.5_min10.parquet` (T-005, approved), `data/interim/fire_regions/fire_region_g050.parquet` (T-004), `pipeline/country_map.csv` (T-009).
- `data/raw/availability/missing_data_*.json` and `data_availability_*.csv` (T-002) for `days_available`.

## 8. Expected outputs
`data/products/cells.parquet` and `data/products/cell_month_witness.parquet`, a validation report (contract checks, integrity checks against the filtered detections), and the G1 evidence in `docs/DATA_SOURCES.md`.

## 9. Implementation requirements
1. Filters (approved): confidence MODIS 30 or more and VIIRS n or h; `type = 0` for SP rows; NRT rows have no `type`; the approved static mask (0.05 degree cells, share at least 0.5, at least 10 detections) is applied to every row, as in the D-009 test.
2. Cell-day key `(witness, daynight, fine cell, UTC date)`. A fine cell belongs to the analysis cell that holds its centre. Witnesses: Aqua `AQUA_MODIS`, Terra `TERRA_MODIS` (raw view only), `N` `SNPP_VIIRS`, `N20` `NOAA20_VIIRS`.
3. `daynight` rows `D` and `N` from the detections' own value, and `ALL` = D + N (contract).
4. `detections` counts the kept detections (informational). `frp_sum_mw` sums non-negative FRP only (negative FRP is treated as null, Lead decision on T-005).
5. Rows exist for every month the witness operated, with `cell_days = 0` where there are no kept detections; never a missing row for an operating month, never a row for a month before the witness operated. The record starts in 2002-07.
6. `days_available` from the FIRMS `missing_data` response and the witness's operating dates; `days_in_month` from the calendar; `data_level` SP, NRT or MIXED per witness-month.
7. `cells.parquet`: only cells with at least one kept detection. Country is the one with most detections in the cell (zip rows; API rows carry no country), continent from `pipeline/country_map.csv`, `fire_region` from T-004. The `stratum_id` rule is provisional (see §15).
8. Integrity: total `detections` in the product equals the number of kept detections; `cell_days` never exceeds the number of fine cells (100) times the days available.
9. G1 evidence: the raw combined record shows the expected jumps at 2012-01 (VIIRS) and 2018-04 (NOAA-20); the D-009 table is recorded.

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify". Do not touch `api/` or `app/`.
- No secrets, no data files, no direct pushes to `main`, no self-merge.
- No calibration, no harmonization (T-011, T-013). Do not look at validation cases (2015 Indonesia, the 2017 to 2021 holdout). Do not fill, interpolate or drop missing data.
- Nothing is removed from the normalized detections; filtered rows are not written back.

## 11. Acceptance criteria
`cell_month_witness` validates against the contract.

## 12. Required tests
`python -m pytest pipeline/tests -q` for the files of this task: cell-day counting (same cell and day once, day and night separate, `ALL` = D + N), the filters and the mask, the centre rule, zero rows for operating months, no rows before a witness operated, `days_available` and its gaps, `data_level`, negative FRP, `cells.parquet` attributes, and the contract validator on a small synthetic dataset with known answers. `ruff` passes on the files of this task. Then the full run on the real data with the integrity and contract checks reported.

## 13. Documentation updates
`docs/TASK_TRACKER.md` row T-006; `docs/DATA_SOURCES.md`.

## 14. Git branch and PR instructions
- Branch: `data/T-006-gridding` created from the latest `main`
- First commit: this prompt file
- Open a DRAFT PR early; title "T-006: Fine-grid cell-days to analysis cell-month"; fill in `.github/pull_request_template.md`
- Never merge; wait for the Project Lead
- Commit with your own Git identity (D-020)

## 15. Out-of-scope or blocking issues
- The tracker shows T-006 as `TODO` until the Lead's assignment PR #27 is merged; work started on the Lead's comment unblocking it. The Lead should confirm.
- The `stratum_id` rule belongs to calibration (T-011). A provisional rule (fire region and country) is used so `cells.parquet` is complete; T-011 may redefine it. Needs Lead approval.
- `ALL` follows the contract (`D + N`); the D-009 test used the union of day and night fine-cell-days. The difference is small and is reported.
- D-022 (`cell_id` format, product path rule) is still proposed; the products use the single-file names of the contract.
