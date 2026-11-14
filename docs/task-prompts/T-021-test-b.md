# Task prompt: T-021 Tests B1 (satellite-change steps) and B3 (known artifacts)

> Prepared for: Member 2 · Date: 2026-11-14 · Based on main @ 02cd07c
> Source of truth: docs/TASK_TRACKER.md row T-021. This prompt adds no scope beyond it.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand): harmonize NASA FIRMS hotspot detections from Aqua, S-NPP and NOAA-20 onto one Aqua-equivalent scale, with honest uncertainty and pre-registered validation tests whose failures are published (`docs/PROJECT_PLAN.md`, `docs/VALIDATION_PLAN.md`). T-011 fitted the ratios, T-013 combines the witnesses, T-012 measured the Aqua drift (D-005). T-021 runs two of the Witness Stand tests: B1 (no step in the harmonized series where a satellite enters the record) and B3 (the known real artifacts are visible and handled as stated).

## 2. Task objective
A tested harness `pipeline/validation_b.py` that evaluates B1 and B3 with the thresholds locked at G1 (D-028, `docs/VALIDATION_PLAN.md` section 3), on `entity_month`-shaped frames (`docs/DATA_CONTRACT.md` section 4); the parts that need only estimates run on the real products now; the parts that need the verdicts of T-014 are coded, tested on synthetic data, and recorded as `NOT_RUN`. Results in `docs/validation/T-021-results.md` and in contract-section-6 entries in `data/interim/qa/T-021_validation_entries.json` (not committed).

## 3. Assigned responsibility
- Task ID / priority: T-021 / P0
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-014 per the tracker. T-014 is not finished; the Lead approved building the harness now (verdict-dependent parts `NOT_RUN`, estimate-only parts run for real).

## 4. Relevant files and directories
- Read: `CLAUDE.md`, `docs/TEAM_WORKFLOW.md` section 4, `docs/DECISION_LOG.md` D-005 and D-028, `docs/VALIDATION_PLAN.md` (B1, B3, section 2a, the NOT_RUN table), `docs/SCIENTIFIC_METHODOLOGY.md` sections 4 and 7, `docs/DATA_SOURCES.md` (T-011, T-013, T-012 sections, satellite dates), `docs/DATA_CONTRACT.md` sections 3, 4, 6, `pipeline/harmonize.py`, `pipeline/aqua_drift.py`, `pipeline/holdout.py`, `data/products/*.parquet`
- Create/modify:
  - `docs/task-prompts/T-021-test-b.md` (this file)
  - `pipeline/validation_b.py`, `pipeline/tests/test_validation_b.py`
  - `docs/validation/T-021-results.md` (new)
  - `docs/TASK_TRACKER.md` (row T-021 only)
- Not committed: `data/interim/qa/T-021_validation_entries.json` and anything else under `data/` except products through Git LFS (D-027)

## 5. Approved technologies
Python, NumPy, pandas, DuckDB, pyarrow, pytest, ruff (D-008, `docs/TECH_STACK.md`). No new dependency.

## 6. Architecture and data contract
Shared science stays in `pipeline/harmonize.py` (`aggregate`, `records_from`, `harmonize_area`); this task only reads its output. Input shape: `entity_month` (contract 0.1.1 section 4: `estimate`, `sd`, `ci90_*`, `pct_of_normal`, `p_above`, `p_below`, `verdict`, `reason_codes`, `witnesses_used`, `n_witnesses`, `raw_combined_cell_days`, `raw_by_witness`, `method_version`). Output entries follow section 6 (`test_id`, `family`, `title`, `case`, `criterion`, `threshold`, `measured`, `status`, `notes`). No contract change.

## 7. Inputs
`data/products/cells.parquet`, `cell_month_witness.parquet`, `calibration.parquet` (real, Git LFS); `entity_month.parquet` once T-014 has produced it (today it is the raw-only product, `method_version` `0.1.0-raw-only`, which carries no verdict logic and is detected as such). No environment variables.

## 8. Expected outputs
Python API: `step_ratio`, `evaluate_b1`, `b1_status`, `drift_series`/`evaluate_b3_drift`, `incomplete_witness_months`, `evaluate_outage_estimates`, `evaluate_outage_verdicts`, `family_status`, `entries_from`. Report and JSON entries as in section 2. Statuses are exactly `PASS`, `FAIL`, `INCONCLUSIVE`, `NOT_RUN`.

## 9. Implementation requirements
1. **B1 statistic (VALIDATION_PLAN B1):** per fire region and date d in {2012-01, 2018-04}: `q(window) = sum X / sum A` over the usable months of the window; step = `q(12 months from d) / q(12 months before d)`. A = the Aqua-only series (Aqua cell-days, Aqua ratio 1), X = the harmonized estimate (and, for the raw reference, `raw_combined_cell_days`). Usable month: an estimate exists and Aqua was used. **PASS** at a date when the harmonized step is within +-10% of 1 in at least 80% of the regions with sufficient data. The raw step must be "clearly present" first; otherwise the date is INCONCLUSIVE.
2. **Chosen before any result, because the plan leaves them open [ASSUMPTION]:** sufficient data = at least 10 usable months in each window and at least 60 Aqua cell-days in each window (D-028 step 4: 5 per month); fire regions = the 14 pipeline regions, not `UNASSIGNED`/`NONE`; "clearly present" = the raw step lies outside +-10% of 1 in at least 50% of the sufficient regions; fewer than 5 sufficient regions gives INCONCLUSIVE; windows are the 12 calendar months from the date (including it) and the 12 before it; the C8 box (cells with centre in 20, -20, 35, -8) is reported as a supplementary row, outside the family fraction.
3. **B3, three parts:** (a) drift: the pre-registered T-012 detector (`aqua_drift.detect`, unchanged settings) on the global monthly Aqua / converted-VIIRS ratio; PASS when it fires for both VIIRS witnesses in the same day/night part with a negative slope and an onset in 2021-01 or later, and the onsets are reported; chosen with knowledge of the T-012 result, so a PASS confirms T-012 and is not independent; (b) outages, estimates: every month with no complete witness has no estimate (100%), and an incomplete witness-month is never in `witnesses_used`; (c) outages, verdicts: months with no complete witness are 100% `CANNOT_DETERMINE` with `OUTAGE` (D-028 step 1): `NOT_RUN` while the product is raw-only. The S-NPP end (2026-11-02) is described against the monthly availability, as a supplementary check without a plan criterion.
4. Thresholds and criteria come only from the plan and D-028 and are never changed after seeing results; a failure is published with its numbers.
5. Nothing is interpolated or filled; months without an estimate stay missing.
6. Deterministic (fixed seed from `aqua_drift`), no network.

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside section 4 "Create/modify" (in particular not `docs/DATA_SOURCES.md`, `docs/VALIDATION_PLAN.md`, `pipeline/harmonize.py`, `pipeline/calibration.py` or any product).
- Do not touch the other workstream directories (`api/`, `app/`).
- No secrets, no raw or interim data files, no direct pushes to main, no self-merge.
- Do not mark unverified scientific claims as validated; a part that did not run is `NOT_RUN`.

## 11. Acceptance criteria
Tracker: "Recorded". Made measurable: B1 and B3 each have a status per plan criterion with the measured numbers, the code is tested and ruff-clean, the verdict parts run with one command once T-014 exists, and the results file states what ran and what did not.

## 12. Required tests
`python -m pytest pipeline/tests/test_validation_b.py -q -p no:cacheprovider` (planted step detected, flat series not; window logic; status logic; outage months have no estimate; verdict check; reproducible); `python -m ruff check pipeline/validation_b.py pipeline/tests/test_validation_b.py`; the full suite `python -m pytest pipeline/tests -q -p no:cacheprovider`. Mutation check: break a rule on purpose, see a test fail, restore.

## 13. Documentation updates
`docs/validation/T-021-results.md` (new) and the row T-021 in `docs/TASK_TRACKER.md` (status IN_REVIEW, review PENDING). Needed changes elsewhere are listed in the final report for the Lead (`docs/VALIDATION_PLAN.md` section 4 table).

## 14. Git branch and PR instructions
- Branch: `science/T-021-test-b` created from the latest `main`
- First commit: this prompt file
- No push and no PR from this session (the Lead integrates)
- Commit with the human contributor's Git identity; no AI names or attribution (D-020)

## 15. Out-of-scope or blocking issues
- T-014 (baseline, probabilities, verdicts) is not merged: the verdict-dependent parts are `NOT_RUN`.
- The plan does not define "regions with sufficient data", "clearly present" or "visible" numerically: section 9.2 and 9.3 record the conservative choices; the Lead may replace them (a change needs a `DECISION_LOG.md` entry).
