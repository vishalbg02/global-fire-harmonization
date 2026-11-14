# Task prompt: T-025 Tests E1 (leave one region out) and S1 (sensitivity)

> Prepared for: Member 2 · Date: 2026-11-14 · Based on main @ 02cd07c
> Source of truth: docs/TASK_TRACKER.md row T-025. This prompt adds no scope beyond it.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand, global scope, `docs/PROJECT_PLAN.md`): hotspot detections of Aqua MODIS, S-NPP VIIRS and NOAA-20 VIIRS are put on the Aqua-equivalent scale (T-011 ratios), combined with an honest uncertainty (T-013), and judged against a baseline (T-014). The Witness Stand (`docs/VALIDATION_PLAN.md`) tests the method with criteria that were locked at Gate G1 (D-028) before any result existed. T-025 runs two of those tests: E1 asks whether the conversion generalizes to a fire region it never saw; S1 asks whether the conclusions depend on the baseline and on the confidence filter.

## 2. Task objective
Two validation tests are implemented, run on the final T-011 products, and recorded honestly. **E1:** for each of the 14 GFED fire regions R, the S-NPP calibration is fitted again without R (nothing of R in any fit input), R's 2017-2021 Aqua series is predicted from S-NPP converted as an unseen region would be, and the prediction is compared with the naive raw merge and with one global ratio, in the units of the T-012 holdout. **S1:** the verdicts of D-028 are recomputed with the Aqua-measured baseline (2003-2021) instead of the harmonized one (2003-2022) on the quantities that exist now; the parts that need T-014 products or a regridding without the confidence filter are written up as NOT_RUN with the code ready where possible.

## 3. Assigned responsibility
- Task ID / priority: T-025 / P1
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-011 (merged). T-012 and T-013 code is on main. The T-014 baseline products do not exist yet.

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/TEAM_WORKFLOW.md` §4, `docs/DECISION_LOG.md` D-005 and D-028, `docs/VALIDATION_PLAN.md`, `docs/SCIENTIFIC_METHODOLOGY.md` §4.3 to §4.6 and §7, `docs/DATA_SOURCES.md` (T-011, T-012, T-013), `docs/DATA_CONTRACT.md` §6, `pipeline/calibration.py`, `pipeline/harmonize.py`, `pipeline/holdout.py`, `data/products/*.parquet`
- Create/modify:
  - `docs/task-prompts/T-025-test-e1-s1.md` (this file)
  - `pipeline/validation_e1_s1.py`, `pipeline/tests/test_validation_e1_s1.py`
  - `docs/validation/T-025-results.md` (new file)
  - `docs/TASK_TRACKER.md` (row T-025 only)
- Not committed: everything under `data/interim/` (temporary fits in `data/interim/_e1_tmp`, reports and `T-025_validation_entries.json` in `data/interim/qa/`). The Lead integrates the entries into `data/products/validation_results.json`, `docs/VALIDATION_PLAN.md` and `docs/DATA_SOURCES.md`.

## 5. Approved technologies
Python, NumPy, pandas, DuckDB, pyarrow, pytest, ruff (D-008). Nothing is added.

## 6. Architecture and data contract
Component: validation (`docs/ARCHITECTURE.md`, Member 2). Inputs are the products `cells` and `cell_month_witness` of contract 0.1.1. Output shape: one entry per test in the `validation_results.json` shape (contract §6: test_id, family, title, case, criterion, threshold, measured, status, notes; status one of PASS, FAIL, INCONCLUSIVE, NOT_RUN). No contract change.

## 7. Inputs
`data/products/cells.parquet`, `data/products/cell_month_witness.parquet` (final T-011 products, Git LFS). No environment variables, no network.

## 8. Expected outputs
- `data/interim/qa/T-025_validation_entries.json`: entries E1, S1-BASELINE, S1-CONFIDENCE-FILTER and S1.
- `data/interim/qa/T-025_e1_report.json`, `T-025_s1_report.json`: all numbers.
- `docs/validation/T-025-results.md`: what was done, the table per region (ours, raw merge, global ratio, day and night), the verdict per test, honest failures, limitations, how to re-run.

## 9. Implementation requirements
1. **E1 fits.** For each region R in `cells.fire_region` except UNASSIGNED: remove R's cells from `cells.parquet` and from the cell-month table handed to `calibration.calibrate()`, restrict that table to Aqua and S-NPP and to years up to 2016, add one data-less phantom UNASSIGNED stratum (it pools to exactly the global ratio and its sd), fit with `calibration.calibrate()` unchanged (S-NPP fit period 2012-01 to 2016-12 only). Audit the files handed to the fit: no cell of R, no year after 2016. `calibration.py` and `harmonize.py` are not edited.
2. **E1 prediction.** R's strata take the phantom's ratio and ratio_sd (an unseen region). `harmonize.aggregate()` on R with these ratios gives the converted S-NPP series; units, actual values and error metrics are those of `holdout.py` (fire-region-months 2017-01 to 2021-12, complete months, at least 20 Aqua cell-days, day and night separately, day+night total). Predictions: ours (leave-one-out), raw (naive raw merge), glob (one global ratio per day/night and season, whole globe, as T-012) and gloo (the same global ratio fitted without R).
3. **E1 criterion (pre-registered here, before any result).** A region wins when the median absolute log error of ours is below that of raw in day and in night, each part counted only with at least 12 units. PASS: at least 11 of the 14 regions win. FAIL: even counting every not-evaluable region as a win the count is below 11. Otherwise INCONCLUSIVE. All 14 regions are reported with their numbers, losses included. The thresholds are not changed after the results.
4. **S1 baseline half.** Apply the verdict rules of D-028 (fixed order; probabilities from a Normal truncated at 0) to the harmonized estimate series of the 14 fire regions, Canada and the case boxes C1 to C6 of `docs/VALIDATION_PLAN.md` §2a, in 2012-01 to 2021-12, with (a) the harmonized baseline 2003-2022 and (b) the Aqua-measured baseline 2003-2021 (Aqua-only series from the same aggregation). The estimate judged is held fixed. PASS if the verdict is identical in every peak-window month of C1 to C6; any change is reported with its months. `compare_baselines()` takes entity_month-shaped frames so that it runs on T-014 products.
5. **S1 NOT_RUN parts.** Without the confidence filter: needs the raw archive regridded without the T-005 filter and the A1 and B1 tests it re-runs (not implemented): NOT_RUN. Cross-check of the verdict function against the T-014 verdict column: NOT_RUN until T-014 products exist (`crosscheck_with_t014()` is ready). The overall S1 entry is NOT_RUN while a half is missing.
6. No result is invented; missing data are reported as missing; synthetic fixtures are used only in tests and are labelled SYNTHETIC.

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify". In particular `pipeline/calibration.py`, `pipeline/harmonize.py`, `docs/DATA_SOURCES.md`, `docs/VALIDATION_PLAN.md` and `validation_results.json` are not edited.
- Do not touch `api/` and `app/`, or the other validation worktrees.
- No secrets, no raw or interim data files committed, no push, no PR, no self-merge.
- Do not mark a validation as passed unless it ran; no thresholds changed after the results.

## 11. Acceptance criteria
From the tracker ("Results recorded, pass or fail"), made measurable: (1) E1 ran for all 14 regions with its status and per-region numbers recorded; (2) S1 ran for the part that can run, NOT_RUN parts are stated with the reason; (3) entries in the contract §6 shape exist; (4) the results file lists every number and every failure; (5) tests and ruff pass.

## 12. Required tests
`python -m pytest pipeline/tests/test_validation_e1_s1.py -q -p no:cacheprovider` and `python -m ruff check pipeline/validation_e1_s1.py pipeline/tests/test_validation_e1_s1.py`, then the whole suite `python -m pytest pipeline/tests -q -p no:cacheprovider`. Tests on SYNTHETIC data with known answers: a planted world where leaving a region out changes its ratio and the metric detects it; the region is excluded from every fit input; no data from 2017 on in any fit; the 11-of-14 counting and the PASS/FAIL/INCONCLUSIVE logic; the verdict rules of D-028 by hand; the baselines by hand; reproducibility. Mutation checks: break a rule on purpose, confirm a test fails, restore.

## 13. Documentation updates
`docs/TASK_TRACKER.md` row T-025 (Status IN_REVIEW, Review PENDING). `docs/validation/T-025-results.md`. The Lead integrates the rest.

## 14. Git branch and PR instructions
- Branch: `science/T-025-test-e1-s1` created from the latest `main`
- First commit: this prompt file
- No push and no PR from this session; the Lead links the PR in the tracker
- Commit with the contributor's own Git identity; no AI names or attribution (D-020)

## 15. Out-of-scope or blocking issues
- The T-014 baseline products do not exist: the T-014-based S1 check is NOT_RUN.
- The confidence-filter sensitivity needs data outside `data/products/`: NOT_RUN.
- The Aqua-only series for S1 is built from the same aggregation as the harmonized one (`harmonize.records_from` on the Aqua rows). If the Lead wants the T-014 definition of the Aqua baseline instead, say so in the PR.
