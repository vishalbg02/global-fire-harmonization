# Task prompt: T-020b Diagnostic: does the Aqua/VIIRS ratio rise with activity (cell-day saturation)?

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main @ 9367b68
> Source of truth: the Lead's decision on PR #55 (comment of 2026-11-14 19:14): "Next, as a time-boxed diagnostic (decision by about 06:00 IST): is it cell-day saturation?" in a separate branch and PR. This prompt adds no scope beyond it.

## 1. Project context
Test A1 (T-020) failed for method 0.1.0: in the four big fire events C3 to C6 the converted S-NPP estimate is below Aqua in every peak window (S-NPP over Aqua 0.58 to 0.80) although direction and peak month agree. The Lead decided that the problem is bias, not variance. A possible cause is **cell-day saturation**: a 0.05 degree fine cell counts at most once per day, so in very active areas both sensors saturate, and the Aqua over VIIRS ratio should **rise** with activity, whereas the T-011 ratio is one value per stratum, day/night and season, fitted mostly on typical months.

## 2. Task objective
A diagnostic that bins stratum-months of the **calibration fit periods only** by activity level and reports the Aqua/VIIRS ratio per bin, by witness and day/night, with bootstrap intervals; and a decision, by a rule fixed here before any result is seen, whether saturation is confirmed. If it is confirmed, a **proposal** for a v0.2 conversion is outlined (not built in this PR).

## 3. Assigned responsibility
- Task ID / priority: T-020b (a diagnostic named by the Lead on #55) / P0
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies: T-011 (merged)

## 4. Relevant files and directories
- Read: `docs/DATA_SOURCES.md` (T-011, T-012), `docs/validation/T-020-results.md` (PR #55), `pipeline/calibration.py` (`monthly_sums`, `FITS`, strata)
- Create/modify: `docs/task-prompts/T-020b-extreme-months.md` (this file), `pipeline/saturation.py`, `pipeline/tests/test_saturation.py`, `docs/validation/T-020b-saturation.md` (the report)
- Not committed: everything under `data/interim/`

## 5. Approved technologies
Python, NumPy, pandas, DuckDB, pytest, ruff (D-008). No new dependency.

## 6. Architecture and data contract
No contract change, no product, no change to T-011, T-013 or T-014.

## 7. Inputs
`cell_month_witness.parquet`, `cells.parquet` (final T-011 products).

## 8. Expected outputs
`data/interim/qa/saturation_report.json` (not committed) and the report `docs/validation/T-020b-saturation.md`: the ratio per activity bin, by witness and day/night, for each binning, with 90% bootstrap intervals; the slope; the decision by the rule below; what a v0.2 would be if confirmed.

## 9. Implementation requirements (fixed before any result)
1. **Data:** only months of the fit periods (S-NPP 2012-01 to 2016-12, complete months; NOAA-20 2018-04 to 2021-12, complete months), exactly as T-011 (`calibration.monthly_sums`). Never S-NPP 2017 to 2021 and never the A1 case windows or any validation case. Unit: a stratum-month (2.5 degree block in a fire region), day and night separately. Activity is measured per analysis cell (divide by the number of cells of the stratum).
2. **Three binnings** of the unit, with the same fixed bin edges in cell-days per cell and month: 0 to 0.05, 0.05 to 0.15, 0.15 to 0.5, 0.5 to 1.5, 1.5 to 5, 5 to 15, 15 to 50, 50 and above.
   - (a) **Aqua activity** of the month (the Lead's suggestion; biased by regression to the mean, because the numerator defines the bin);
   - (b) **symmetric proxy**: the mean of the Aqua cell-days and of the VIIRS cell-days times the stratum-wide fit ratio of that witness and day/night (less biased);
   - (c) **typical activity** of the stratum: the median over the fit months of its Aqua cell-days per cell (independent of the month's own noise).
3. **Ratio per bin:** sum of Aqua over sum of the witness over the units in the bin (as in T-011). 90% interval by a month block bootstrap: whole fit months are resampled with replacement (1,000 replicates, fixed seed). Bins with fewer than 50 units are shown but not used in the slope.
4. **Slope:** the ordinary least-squares slope of log(ratio) on log(mean activity of the bin) over the eligible bins, with its bootstrap interval (the whole slope is recomputed per replicate).
5. **Decision rule (fixed now):** saturation is **confirmed** if, in at least two of the three binnings, the slope is positive with a 90% interval that excludes 0 in at least three of the four combinations (S-NPP day, S-NPP night, NOAA-20 day, NOAA-20 night). Otherwise it is **not confirmed**. Binning (a) alone never decides, because of its bias.
6. If confirmed: outline the v0.2 conversion (for example log(Aqua) = a + b log(VIIRS) per stratum with pooling, or ratios by activity bin, fitted on the fit periods only) and what must be reported (holdout errors against v0.1, D1 coverage, A1 under v0.2, labelled as a post-hoc improvement prompted by A1). Do not build it here.

## 10. Constraints: do not modify
- Do not change T-011, T-013 or T-014, the thresholds of D-028 or the validation plan. Do not touch `api/` or `app/`.
- No secrets, no data files, no direct pushes to `main`, no self-merge.

## 11. Acceptance criteria
The report shows the ratio against activity for each binning, witness and day/night, the decision by the rule above, and what follows.

## 12. Required tests
`python -m pytest pipeline/tests/test_saturation.py -q` on synthetic data with known answers: a planted ratio that rises with activity gives a positive slope with an interval excluding 0; a constant ratio gives a slope near 0 and is not confirmed; bin assignment at the edges; the bootstrap is reproducible; no month outside the fit periods is used; the decision rule. `ruff` passes on the files of this task. Then the real run.

## 13. Documentation updates
`docs/validation/T-020b-saturation.md` (the report).

## 14. Git branch and PR instructions
- Branch: `science/T-020b-extreme-months` created from the latest `main`
- First commit: this prompt file
- Open a PR; fill in `.github/pull_request_template.md`
- Never merge; wait for the Project Lead
- Commit with your own Git identity (D-020)

## 15. Out-of-scope or blocking issues
- If saturation is confirmed, the v0.2 conversion is a new decision for the Lead; it is a post-hoc improvement prompted by A1 and cannot make A1 a clean pass.
- This PR does not change PR #55 (A1 stays FAIL for v0.1).
