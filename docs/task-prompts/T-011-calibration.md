# Task prompt: T-011 Calibration ratios with partial pooling and block bootstrap

> Prepared for: Member 2 · Date: 2026-11-14 · Based on main @ 7ecf30f
> Source of truth: docs/TASK_TRACKER.md row T-011 (assigned by the Lead's assignment PR #27; T-006 and T-004 are merged). This prompt adds no scope beyond it.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand): harmonize NASA FIRMS hotspot detections from several satellites (`docs/PROJECT_PLAN.md`). VIIRS sees more fire cell-days than MODIS, so each VIIRS witness must be converted to the Aqua-equivalent scale before witnesses are combined. The conversion is a ratio fitted on the years when the satellites overlap. T-006 produced the per-witness cell-month observations and T-004 the fire regions. T-011 fits the ratios; the holdout test (T-012) and the combination (T-013) come later.

## 2. Task objective
`data/products/calibration.parquet` (local, not committed), one row per stratum x witness x daynight x season, validating against `docs/DATA_CONTRACT.md` §5, with a ratio, its bootstrap uncertainty, the months used, the fit period and the pooling level. The proposed pooling design and the global and regional results are reported for the Lead's approval. `cells.parquet` is regenerated with the final `stratum_id` rule.

## 3. Assigned responsibility
- Task ID / priority: T-011 / P0
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-006 (merged), T-004 (merged)

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/SCIENTIFIC_METHODOLOGY.md` §4.3, `docs/DATA_CONTRACT.md` §1, §2 and §5, `docs/prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md` §11 and §12, `docs/VALIDATION_PLAN.md`, `docs/DATA_SOURCES.md` (T-004, T-006)
- Create/modify:
  - `docs/task-prompts/T-011-calibration.md` (this file)
  - `pipeline/calibration.py`
  - `pipeline/tests/test_calibration.py`
  - `docs/DATA_SOURCES.md` (the calibration design, results and proposals)
  - `docs/TASK_TRACKER.md` (row T-011 only)
- Not committed: everything under `data/products/` (`calibration.parquet`, regenerated `cells.parquet`)

## 5. Approved technologies
Python, NumPy, DuckDB, pyarrow, pytest, ruff (D-008). No new dependency.

## 6. Architecture and data contract
`calibration.parquet` (§5): `stratum_id`, `witness`, `daynight`, `season` (DJF, MAM, JJA, SON), `ratio` (multiplier to the Aqua-equivalent scale), `ratio_sd`, `n_overlap_months`, `fit_period`, `pooling_level` (LOCAL, REGION, GLOBAL). `cells.stratum_id` (§1) points to the stratum a cell belongs to.

## 7. Inputs
`data/products/cell_month_witness.parquet` and `data/products/cells.parquet` (T-006), `fire_region` from T-004.

## 8. Expected outputs
- `data/products/calibration.parquet` and the regenerated `data/products/cells.parquet` (new `stratum_id`).
- A report: global and regional ratios per witness x daynight x season, between-stratum variances, the distribution of pooling levels, months used and excluded.

## 9. Implementation requirements
1. Fit periods: S-NPP on 2012-01 to 2016-12 (2017 to 2021 is held out and never read); NOAA-20 on 2018-04 to 2021-12. Reference is Aqua.
2. Ratio = sum of Aqua `cell_days` over sum of witness `cell_days` over the fit months, per stratum x daynight x season (DJF, MAM, JJA, SON). `D` and `N` are fitted separately with their own ratios; `ALL` is informational (fitted on the `ALL` cell-days), the combination uses `D` and `N`.
3. Only complete months enter the fit: months where both Aqua and the witness had every day available (`days_available = days_in_month`); partial months are excluded and counted.
4. Partial pooling, proposals for the Lead's approval: local stratum = a 2.5 degree block within a fire region; shrink the log-ratio of a stratum toward its fire region, and that toward the global ratio, with precision weights (`1/variance` of the local estimate against `1/tau^2`, `tau^2` estimated from the spread between strata); `UNASSIGNED` fire-region cells pool directly to the global ratio (T-004 approval).
5. `pooling_level` is the level with the largest weight in the final estimate (LOCAL, REGION or GLOBAL).
6. Uncertainty: a monthly block bootstrap (resample fit months with replacement within each season, whole months so within-month dependence is kept); the whole procedure, including `tau^2`, is repeated per replicate; `ratio_sd` is the standard deviation of the final ratio across replicates. The seed is fixed.
7. Never fit per year; never look at the holdout years or at any validation case.
8. `n_overlap_months` = months of the fit period used for the row; `fit_period` = e.g. `2012-01/2016-12`.
9. Every stratum present in `cells.parquet` gets a row for every witness x daynight x season, also where there is no overlap data (then the ratio comes from the parent level and `n_overlap_months` is 0).

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify". Do not touch `api/` or `app/`.
- No secrets, no data files, no direct pushes to `main`, no self-merge.
- Do not compute the holdout evaluation (T-012), the combination (T-013) or any validation test. Do not present proposals as approved.

## 11. Acceptance criteria
`calibration` product; pooling levels reported.

## 12. Required tests
`python -m pytest pipeline/tests/test_calibration.py -q` on synthetic data with known ratios: recovery of a planted ratio per stratum; a sparse stratum shrinks to its region and a data-rich stratum stays local; `tau^2` is zero when strata do not differ; no month outside the fit period is used (planted outliers in the holdout years change nothing); partial months are excluded; the bootstrap is reproducible and its spread shrinks with more months; the contract validator accepts a good table and rejects a bad one. `ruff` passes on the files of this task. Then the run on the real products, with the report.

## 13. Documentation updates
`docs/TASK_TRACKER.md` row T-011; `docs/DATA_SOURCES.md`.

## 14. Git branch and PR instructions
- Branch: `science/T-011-calibration` created from the latest `main`
- First commit: this prompt file
- Open a DRAFT PR early; title "T-011: Calibration ratios with partial pooling and block bootstrap"; fill in `.github/pull_request_template.md`
- Never merge; wait for the Project Lead
- Commit with your own Git identity (D-020)

## 15. Out-of-scope or blocking issues
- The local block size (2.5 degrees), the shrinkage form, the `pooling_level` rule, the complete-months rule, the number of bootstrap replicates and the season definition need the Lead's approval (`MEMBER_2` prompt §11).
- The tracker shows T-011 as `TODO` until the Lead's assignment PR #27 is merged; work started on the Lead's go-ahead after T-006 merged. The Lead should confirm.
- The `stratum_id` rule is redefined here; the final rule is documented and `cells.parquet` regenerated, as the Lead asked on the T-006 PR.
