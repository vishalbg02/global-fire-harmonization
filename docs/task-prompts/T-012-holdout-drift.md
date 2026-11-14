# Task prompt: T-012 Holdout evaluation 2017-2021 and Aqua drift diagnostic

> Prepared for: Member 2 · Date: 2026-11-14 · Based on science/T-013-combination @ b902596 (PR #43, not yet merged)
> Source of truth: docs/TASK_TRACKER.md row T-012 and the Lead's kick-off notes on PR #27 (comment of 2026-11-14 14:42). This prompt adds no scope beyond them.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand): harmonize NASA FIRMS hotspot detections from several satellites (`docs/PROJECT_PLAN.md`). T-011 fitted the ratios that convert S-NPP and NOAA-20 to the Aqua-equivalent scale on 2012-2016 and 2018-2021; T-013 combines the converted witnesses with an honest uncertainty. T-012 answers two questions before any verdict is built: how well do the conversions predict Aqua out of sample (2017-2021, which the calibration never read), and when does Aqua start to drift, so that the drift cutoff of D-005 can be proposed.

## 2. Task objective
(a) A holdout evaluation: predict Aqua cell-days in 2017-2021 from converted S-NPP with the T-011 ratios, report the error by fire region x day/night against the two baselines of `docs/VALIDATION_PLAN.md` (the naive raw merge and one global ratio), and the coverage of the 90% intervals of T-013 (the input to test D1). (b) An Aqua drift diagnostic: the monthly Aqua / converted-VIIRS ratio, globally and by region, day and night separately, 2012 to 2026; an onset estimated with a method **pre-registered below**; a **proposed** `aqua_cutoff` with its evidence. A short table and a drift plot.

## 3. Assigned responsibility
- Task ID / priority: T-012 / P0
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-011 (merged). The coverage needs the final variance of T-013 (PR #43, reworked and awaiting review); this branch is created from the T-013 branch, so its first commits are T-013's until #43 merges.

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/SCIENTIFIC_METHODOLOGY.md` §3 and §4.3 to §4.5, `docs/VALIDATION_PLAN.md`, `docs/DECISION_LOG.md` D-005, `docs/DATA_SOURCES.md` (T-006, T-011, T-013), `pipeline/calibration.py`, `pipeline/harmonize.py`
- Create/modify:
  - `docs/task-prompts/T-012-holdout-drift.md` (this file)
  - `pipeline/holdout.py`, `pipeline/tests/test_holdout.py`
  - `pipeline/aqua_drift.py`, `pipeline/tests/test_aqua_drift.py`
  - `docs/DATA_SOURCES.md` (results, the proposal)
  - `docs/figures/aqua_drift.png` (small, normal Git)
  - `docs/TASK_TRACKER.md` (row T-012 only)
- Not committed: everything under `data/interim/` and any product under `data/products/` (products, if any, go through Git LFS, D-027)

## 5. Approved technologies
Python, NumPy, pandas, DuckDB, pyarrow, matplotlib for the figure (check that it is installed; it is the only plotting dependency and needs the Lead's approval if it must be added), pytest, ruff (D-008).

## 6. Architecture and data contract
No contract change, no new product. Results go to `data/interim/qa/*.json` and `docs/DATA_SOURCES.md`.

## 7. Inputs
`data/products/cell_month_witness.parquet`, `cells.parquet`, `calibration.parquet` (final T-011 products, D-025 mask); `pipeline/harmonize.py` (T-013: `aggregate`, `records_from`, `PHI`).

## 8. Expected outputs
- A holdout report: by fire region x day/night, the median of predicted / actual Aqua, its 5th and 95th percentile, and the bias by year, for our method and the two baselines; the coverage of the 90% intervals (overall and by region and day/night).
- A drift report: monthly series and the change-point result, the proposed `aqua_cutoff`, and `docs/figures/aqua_drift.png`.

## 9. Implementation requirements
1. **Holdout.** Units: country-months and fire-region-months (and cell-block-months if useful) in 2017-01 to 2021-12 where Aqua and S-NPP both have a complete month. Prediction: the converted S-NPP estimate (T-013 aggregation, D and N separately) against the Aqua cell-days. **Baselines:** (a) the naive raw merge, i.e. S-NPP raw cell-days as the prediction; (b) one global ratio per day/night (and season) applied to S-NPP raw cell-days. Report the median absolute log error and the median and 5th/95th percentile of predicted / actual, with units of at least 20 Aqua cell-days so that the ratio is stable; state the threshold and give a sensitivity to 5 and 100.
2. **Coverage.** The share of actual Aqua values inside the 90% interval of the prediction (the converted S-NPP estimate with the T-013 variance including `phi` and shared ratio errors, plus the counting variance of the Aqua value itself). Target 80% to 97% (test D1); report it honestly whatever it is. Do not tune any parameter to the result.
3. **Drift series.** For each month from 2012-01 to the last complete month, `R(t) = Aqua / converted VIIRS` (sum over the globe and per fire region; D and N separately), from S-NPP and from NOAA-20 separately (NOAA-20 from 2018-04). Complete witness-months only. Use the T-011 ratios as they are; nothing in T-011 is re-fitted.
4. **Pre-registered change-point method (fixed here, before any result is seen).** On `y(t) = log R(t)` of the **global day series from S-NPP** (primary; S-NPP ended 2026-11-02, so its last complete month is 2026-10): fit a model that is flat up to a break month `b` and linear afterwards (continuous at `b`), by least squares over candidate months `b` from 2018-01 to 2025-06. The onset estimate is the `b` with the smallest residual sum of squares. Its 90% interval is the 5th to 95th percentile of `b` over 1,000 moving-block bootstrap replicates of the residuals (blocks of 6 months, fixed seed). The slope after `b` is reported with its bootstrap interval; **drift is called detected only if that slope interval excludes 0 and the break model beats the no-break (flat) model by BIC.** The same is repeated, as confirmation and not as selection, for the night series, for the NOAA-20 series (from 2018-04) and for each fire region.
5. **Proposal.** The proposed `aqua_cutoff` is the primary onset estimate (month), shown with its interval and the confirmation results. If the diagnostic does not detect drift, say so and propose no cutoff. The proposal is for the Lead's approval (D-005); nothing is applied.
6. **Figure.** One PNG, `docs/figures/aqua_drift.png`: the global monthly `R(t)` (day and night, S-NPP and NOAA-20), the fitted model and the onset with its interval. Small file, readable with light and dark backgrounds, axes and units labelled.
7. **No tuning.** No validation case (Indonesia 2015 and others) is used to choose anything. The held-out S-NPP years are used here for evaluation only and nowhere to refit.

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, scientific methodology or data contract. Do not touch `pipeline/calibration.py` or `pipeline/harmonize.py` (report any needed change instead); do not touch `api/` or `app/`.
- No secrets, no data files in Git except LFS products, no direct pushes to `main`, no self-merge.
- Do not compute baselines or verdicts (T-014), the other validation tests (T-020 and later), or a combination of witnesses. Do not apply the drift cutoff and do not present the proposal as approved.

## 11. Acceptance criteria
Scores and drift plot presented at R2 (the tracker's criterion): the holdout table against both baselines, the coverage, the drift result with the proposed cutoff and its evidence, all with the numbers and the honest failures.

## 12. Required tests
`python -m pytest pipeline/tests/test_holdout.py pipeline/tests/test_aqua_drift.py -q` on synthetic data with known answers: the holdout recovers a planted error and ranks the method above the baselines on synthetic data where it should win and does not hide a case where it does not; the coverage is counted correctly on planted intervals; no calibration input from 2017-2021 is used to fit anything; the drift method finds a planted break month and slope within tolerance, finds none in a flat series, and the BIC and slope criteria behave as specified; the bootstrap is reproducible. `ruff` passes on the files of this task. Then the runs on the real products, with the report.

## 13. Documentation updates
`docs/TASK_TRACKER.md` row T-012; `docs/DATA_SOURCES.md` (the holdout table, the coverage, the drift result and the proposal); `docs/RISKS_AND_LIMITATIONS.md` if a limitation is found.

## 14. Git branch and PR instructions
- Branch: `science/T-012-holdout-drift` created from `science/T-013-combination` (PR #43 not merged yet); rebase onto `main` after #43 merges
- First commit: this prompt file
- Open a DRAFT PR early; fill in `.github/pull_request_template.md`
- Never merge; wait for the Project Lead
- Commit with your own Git identity (D-020)

## 15. Out-of-scope or blocking issues
- The coverage uses the T-013 variance, which is in review (#43). If the Lead changes it, the coverage is re-run.
- `matplotlib` must already be installed; otherwise the Lead decides.
- The calibration ratios were fitted on 2012-2016 and 2018-2021: the S-NPP holdout (2017-2021) is out of sample, but the NOAA-20 series is in sample, so it is a consistency check only.
- Test D1 itself (the recorded test result) belongs to T-022; here the coverage is the input.
