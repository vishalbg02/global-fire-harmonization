# Task prompt: T-020 Validation test A1 (real anomaly preserved, two independent paths)

> Prepared for: Member 2 · Date: 2026-11-14 · Based on main @ 02cd07c
> Source of truth: docs/TASK_TRACKER.md row T-020, docs/VALIDATION_PLAN.md §2a and §3 (test A1), D-028. This prompt adds no scope beyond them.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand): harmonize NASA FIRMS hotspot detections from Aqua MODIS, S-NPP VIIRS and NOAA-20 VIIRS onto one Aqua-equivalent scale, with an honest uncertainty and a verdict against a 2003-2022 baseline (`docs/PROJECT_PLAN.md`). T-011 fitted the conversion ratios, T-013 combines the witnesses (`harmonize_area()`), T-014 (in progress, Lead) builds the baseline, probabilities and verdicts. The Witness Stand is the set of validation tests of `docs/VALIDATION_PLAN.md`. T-020 is test A1: a real, extreme fire season must be seen with the same direction and timing whether it is measured by Aqua alone or by converted S-NPP alone.

## 2. Task objective
A harness that, for a case window, computes two independent paths from `pipeline/harmonize.py` (the Aqua-only path, with S-NPP and NOAA-20 excluded, and the S-NPP-only path, with Aqua and NOAA-20 excluded), builds a D-028 baseline per path, computes `pct_of_normal` per month, and applies the A1 criterion exactly as written (same direction above or below normal; peak month within ±1; 90% intervals overlap). The comparison function takes two `entity_month`-shaped DataFrames, so that it can be re-run unchanged on the T-014 products. The harness is run on case C1 (Sumatra + Kalimantan, Sep-Oct 2015) and the result is recorded in the contract §6 test shape, clearly labelled provisional until T-014 products exist.

## 3. Assigned responsibility
- Task ID / priority: T-020 / P0
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-013 (merged), T-050 (merged). T-014 is NOT merged: the baseline used here is a stand-in built in this module, to be replaced by the T-014 products.

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/TEAM_WORKFLOW.md` §4, `docs/DECISION_LOG.md` D-005 and D-028, `docs/VALIDATION_PLAN.md` §2, §2a, §3, `docs/DATA_CONTRACT.md` §4 and §6, `docs/DATA_SOURCES.md` (T-011, T-013, T-012), `pipeline/harmonize.py`, `data/products/*.parquet`
- Create/modify:
  - `docs/task-prompts/T-020-test-a1.md` (this file)
  - `pipeline/validation_a1.py`, `pipeline/tests/test_validation_a1.py`
  - `docs/validation/T-020-results.md` (new)
  - `docs/TASK_TRACKER.md` (row T-020 only)
- Not committed: `data/interim/qa/T-020_validation_entries.json` (git-ignored); nothing under `data/`.

## 5. Approved technologies
Python, NumPy, pandas, DuckDB, pyarrow, pytest, ruff (D-008). No new dependency.

## 6. Architecture and data contract
No contract change, no new product. Inputs and outputs of the comparison use the `entity_month` field names of `docs/DATA_CONTRACT.md` §4 (`year`, `month`, `estimate`, `sd`, `ci90_low`, `ci90_high`, `baseline_median`, `baseline_p25`, `baseline_p75`, `pct_of_normal`). The recorded entry follows the test shape of §6 (contract_version 0.1.1).

## 7. Inputs
`data/products/cell_month_witness.parquet`, `cells.parquet`, `calibration.parquet`; `pipeline/harmonize.py` (`aggregate`, `records_from`, `WITNESSES`). Case C1 from `docs/VALIDATION_PLAN.md` §2a: box 95, -6, 119, 4 (W, S, E, N); analysis window 2015-06 to 2015-12; peak window 2015-09 to 2015-10.

## 8. Expected outputs
- `pipeline/validation_a1.py`: path restriction by filtering the `aggregate()` table to one witness before `records_from`; the D-028 baseline; `pct_of_normal`; `compare_paths()` (A1 criterion on two `entity_month`-shaped frames); `build_case_frames()` (the thin function that builds the two frames from the data); a command-line run that writes the entry.
- `data/interim/qa/T-020_validation_entries.json` (git-ignored) in the contract §6 shape.
- `docs/validation/T-020-results.md`: what was done, tables for the two paths, the status, the caveats, what is provisional, the exact re-run command.

## 9. Implementation requirements
1. **Paths.** Aqua-only: only `AQUA_MODIS` rows of `aggregate()`. S-NPP-only: only `SNPP_VIIRS` rows. NOAA-20 and Terra enter neither path. `harmonize.py` is not edited.
2. **Baseline (D-028).** Per path and calendar month: years 2003-2022, empirical p25/p50/p75 with linear interpolation, over the years that have an estimate; fewer than 15 of the 20 years gives no baseline; a baseline median below 5 Aqua-equivalent cell-days gives no baseline (step 4 of D-028). The baseline is built from the path's own estimates. The uncertainty of the percentiles is not propagated (D-028). The S-NPP-only path has at most 11 baseline years (2012-2022), so under D-028 it has no baseline; this is recorded as an [ASSUMPTION] with the exploratory variants below, never as a threshold change.
3. **pct_of_normal** = estimate / baseline median × 100; its 90% interval uses the estimate's interval over the same median.
4. **Criterion (verbatim from the plan, thresholds locked).** Direction of a path: the direction of its peak window (estimate summed over the peak window against the summed p75 and p25: ABOVE, BELOW or WITHIN). PASS needs both ABOVE or both BELOW, peak months (the month of the largest `pct_of_normal` in the analysis window) at most 1 month apart, and the 90% intervals of the peak-window `pct_of_normal` overlapping. FAIL if a path has a baseline and a defined peak window and any condition fails. INCONCLUSIVE if a path has no baseline or an incomplete peak window, or if both paths are WITHIN (no anomaly to preserve). Nothing is tuned on the case.
5. **Status.** The formal status stays `NOT_RUN` in the recorded entry until the test is re-run on the T-014 products; the computed result with the stand-in baseline is recorded as `provisional_status` inside `measured`.
6. **Honesty.** Shared fires (both paths see the same fires), the short S-NPP baseline, and Aqua being itself an estimate are stated in the notes. Label claims [VERIFIED], [ASSUMPTION], [HYPOTHESIS], [OPEN].

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, scientific methodology, data contract or validation thresholds. Do not edit `pipeline/harmonize.py`, `docs/DATA_SOURCES.md`, `docs/VALIDATION_PLAN.md` or any product (report any needed change instead).
- Do not edit files outside §4 "Create/modify". Do not touch `api/` or `app/`.
- No secrets, no data files in Git, no direct pushes to `main`, no self-merge.
- Do not mark a validation as passed unless it actually ran; the stand-in result is provisional.

## 11. Acceptance criteria
Results recorded, pass or fail (tracker): the harness, its tests, the C1 run with the numbers for both paths, the status computed under the stated reading, and an explicit list of what is provisional until T-014.

## 12. Required tests
`python -m pytest pipeline/tests/test_validation_a1.py -q -p no:cacheprovider` on synthetic data with known answers: direction (same, opposite, within), peak month at the ±1 boundary and beyond, interval overlap at the boundary, status PASS/FAIL/INCONCLUSIVE, the witness restriction removing the other witnesses, the baseline by hand (empirical percentiles; fewer than 15 years gives none), reproducibility. A mutation check (break a rule, see a test fail, restore). `python -m ruff check` on the two files passes. Then the full suite `python -m pytest pipeline/tests -q -p no:cacheprovider`.

## 13. Documentation updates
`docs/TASK_TRACKER.md` row T-020 (Status IN_REVIEW, Review PENDING; PR stays an em dash); `docs/validation/T-020-results.md` (new).

## 14. Git branch and PR instructions
- Branch: `science/T-020-test-a1` created from the latest `main`
- First commit: this prompt file
- The Lead opens the PR (this work does not push); title "T-020: Test A1 (two independent paths)"
- Never merge; wait for the Project Lead
- Commit with your own Git identity; no AI names or attribution in commits, PR text or branch names (D-020)

## 15. Out-of-scope or blocking issues
- T-014 products (real baseline, `pct_of_normal`, verdicts) do not exist yet: the run here is provisional and must be repeated on them.
- The plan does not say how the S-NPP-only path gets a baseline before 2012. Reading used: D-028 literally (fewer than 15 years gives no baseline), with two exploratory variants reported separately; the Lead decides the intended reading.
- A1 covers C1 to C6 and a family pass of 5 of 6; this task runs C1 (the case named in the task). The harness takes the case as data, so C2 to C6 need no new code.
