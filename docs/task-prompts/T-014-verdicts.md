# Task prompt: T-014 Baseline, probabilities, verdicts, reason codes; entity aggregation (real products)

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main @ 02cd07c
> Source of truth: docs/TASK_TRACKER.md row T-014 (assigned by the Lead's assignment PR #50) and `docs/DECISION_LOG.md` D-028 (G1 lock, approved 2026-11-14, closes D-010). This prompt adds no scope beyond them.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand): harmonize NASA FIRMS hotspot detections from several satellites (`docs/PROJECT_PLAN.md`). T-011 calibrated the witnesses, T-013 combines them with an honest uncertainty (`harmonize.py`: `phi` and `kappa`, shared ratio errors, day and night combined separately, the Aqua night cutoff of D-005), and T-012 evaluated the method out of sample. T-014 turns the combined estimates into the products the app shows: a baseline for the same calendar month, probabilities, a verdict and reason codes for every cell, country, continent and the world. Until now Member 3 has had raw-only products (T-014a); T-014 replaces them.

## 2. Task objective
Real `cell_month_harmonized.parquet` and `entity_month.parquet` (contract 0.1.1 sections 3 and 4) with estimates, intervals, baselines, probabilities, verdicts and reason codes (no `-raw-only`), and a real `metadata.json`, committed through Git LFS (D-027) with checksums; validated with `contract_check.py` in real mode; and a summary: share of determinable verdicts by level, verdict counts, Indonesia 2015 and one quiet control country.

## 3. Assigned responsibility
- Task ID / priority: T-014 / P0
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-013 (merged), D-010 closed by D-028 (merged)

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/DECISION_LOG.md` D-028 and D-005, `docs/SCIENTIFIC_METHODOLOGY.md` §4.4 to §4.6, `docs/DATA_CONTRACT.md` §3, §4, §7 and the 0.1.1 additions, `docs/DATA_SOURCES.md` (T-011, T-013, T-012), `pipeline/harmonize.py`, `pipeline/contract_check.py`, `pipeline/raw_only.py`
- Create/modify:
  - `docs/task-prompts/T-014-verdicts.md` (this file)
  - `pipeline/verdicts.py`, `pipeline/tests/test_verdicts.py`
  - `pipeline/harmonize.py` (only one added output column, `e_pooled`, for the `POOLED_CALIBRATION` rule; behaviour unchanged)
  - `data/products/cell_month_harmonized.parquet`, `entity_month.parquet` (LFS), `metadata.json`, `validation_results.json`
  - `docs/DATA_SOURCES.md` (the T-014 section; the all-country shares requested on #27), `docs/TASK_TRACKER.md` (row T-014 only)

## 5. Approved technologies
Python, NumPy, pandas, DuckDB, pyarrow, pytest, ruff (D-008). `scipy` is in the approved stack but is not installed here and is not needed: the normal distribution function uses `math.erf`.

## 6. Architecture and data contract
Outputs exactly as `DATA_CONTRACT.md` 0.1.1 §3 and §4 (enumerations include `NOT_HARMONIZED`, which these rows do not carry). `method_version` `0.1.0`. `contract_version` `0.1.1`.

## 7. Inputs
`cell_month_witness.parquet`, `cells.parquet`, `calibration.parquet` (final T-011 products, D-025 mask); `pipeline/country_map.csv` (country names).

## 8. Expected outputs
- The two tables and `metadata.json` / `validation_results.json` (`tests: []`; no test has run), committed through Git LFS with SHA-256 checksums posted in the PR.
- A summary: verdict counts and the share of determinable verdicts for cells, countries, continents and the world; Indonesia 2015; one quiet control country; the all-country shares of `S` from `python pipeline/harmonize.py` (requested by the Lead on #27).

## 9. Implementation requirements (D-028, locked)
1. **Estimate** per cell and per entity (countries, continents, the world) and month: the T-013 combination, vectorised; it must equal `harmonize.records_from` (tested).
2. **Baseline:** the same calendar month, years 2003 to 2022, empirical p25, p50, p75 with linear interpolation over the years that have an estimate; fewer than 15 of the 20 years: no baseline.
3. **Probabilities:** the estimate is Normal(estimate, sd) truncated at 0; `p_above` = P(X > p75), `p_below` = P(X < p25), `p_within` = 1 - both.
4. **Verdicts, in this order:** (1) no estimate: `CANNOT_DETERMINE` + `OUTAGE`; (2) fewer than 15 baseline years: `CANNOT_DETERMINE` + `INSUFFICIENT_BASELINE`; (3) estimate 0 and baseline p75 at most 1: `NO_DETECTED_ACTIVITY`; (4) baseline p50 below 5: `CANNOT_DETERMINE` + `INSUFFICIENT_BASELINE`; (5) `p_above` at least 0.8: `ABOVE_NORMAL`; (6) `p_below` at least 0.8: `BELOW_NORMAL`; (7) `p_within` at least 0.8: `WITHIN_NORMAL`; (8) otherwise `CANNOT_DETERMINE` + `WIDE_INTERVAL`.
5. **Caveat codes** (added, never change the verdict): `PROVISIONAL_NRT`, `SINGLE_WITNESS`, `WITNESS_DISAGREEMENT` (S above 2), `AQUA_DRIFT_ERA` (from T-013); `POOLED_CALIBRATION` (more than 50% of the converted cell-days of the witnesses that count use a `REGION` or `GLOBAL` ratio); `DIURNAL_CAVEAT` (India and the cells with centres in 29.5 to 32.5 N, 73.8 to 77.5 E, October and November, from 2020); `INSUFFICIENT_OVERLAP` is not used.
6. `pct_of_normal` = estimate / baseline median x 100 (null without a baseline or with median 0). All baseline fields are null together.
7. **Contract conflict, handled and reported (not changed silently):** the contract checker forbids `NO_DETECTED_ACTIVITY` where any witness (Terra included) detected something. Step 3 therefore also requires the raw combined cell-days to be 0; a row with an estimate of 0 but raw detections goes to step 4 (`INSUFFICIENT_BASELINE`). This is a refinement of D-028 step 3 for the Lead to confirm; the number of rows concerned is reported.
8. Products are written by `python pipeline/verdicts.py`; the contract check runs on every row group; the data snapshot dates come from the previous `metadata.json` when there is no raw folder.

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, scientific methodology, data contract or any threshold of D-028. Do not touch `api/` or `app/`.
- No secrets; products only through Git LFS; no direct pushes to `main`; no self-merge.
- Do not run or record any validation test (T-020 and later); do not present proposals as approved.

## 11. Acceptance criteria
`cell_month_harmonized`, `entity_month` and `metadata.json` validate against the contract in real mode (the tracker's criterion).

## 12. Required tests
`python -m pytest pipeline/tests/test_verdicts.py -q`: the probabilities against a numeric integration; the baseline by hand (missing years, calendar months, years outside 2003 to 2022 ignored); every row of the verdict table by hand, with the boundaries (15 years, p50 of 5, p75 of 1, the 0.8 level); the caveat codes (diurnal box, pooled share, alphabetical order); the vectorised combination equals `records_from` on random inputs (including the cutoff, incomplete months and Terra); a small end-to-end world whose products pass the contract check. Mutation checks on the rules. `ruff` passes on the files of this task. Then the real run, with the summary.

## 13. Documentation updates
`docs/TASK_TRACKER.md` row T-014; `docs/DATA_SOURCES.md` (T-014 section, the all-country shares).

## 14. Git branch and PR instructions
- Branch: `science/T-014-verdicts` created from the latest `main`
- First commit: this prompt file
- Open a DRAFT PR early; fill in `.github/pull_request_template.md`
- Never merge; wait for the Project Lead
- Commit with your own Git identity (D-020)

## 15. Out-of-scope or blocking issues
- The refinement of step 3 (item 7) needs the Lead's confirmation.
- The all-country shares of `S` are re-run in this PR, as requested on #27.
- Validation tests that use these products (A1, B1, B3, D1, D2, E1, S1) are separate tasks.
