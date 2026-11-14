# Task prompt: T-020c v0.2 activity-dependent conversion (D-030, post-hoc after A1)

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main @ cdfa2d1
> Source of truth: docs/TASK_TRACKER.md row T-020c (PR #50) and the Lead's decision on PR #58 (comment of 2026-11-14): "build v0.2, time-boxed, with the adoption rule fixed now". This prompt adds no scope beyond it.

## 1. Project context
Many Witnesses converts each VIIRS witness to the Aqua-equivalent scale with one ratio per stratum, day/night and season (T-011), combines the witnesses (T-013) and judges each month against a 2003 to 2022 normal (T-014, D-028). Test A1 failed for method 0.1.0 (0 of 6 cases; D-029): in the big fire events the converted S-NPP estimate is below Aqua in the peak windows. T-020b confirmed by a pre-set rule that the Aqua/VIIRS ratio rises with activity, so a ratio fitted on typical months under-converts extreme months. This task builds the Lead's v0.2 answer and compares it with v0.1.

## 2. Task objective
A conversion v0.2 with an activity term, fitted on the calibration fit periods only, and a side-by-side comparison with v0.1 on the T-012 holdout, on D1 coverage and on the A1 gap, decided by the adoption rule below, which is recorded as D-030 PROPOSED **before** any v0.2 result exists. v0.2 products are written to `data/interim/v02/` only. Nothing in `data/products/` changes.

## 3. Assigned responsibility
- Task ID / priority: T-020c / P0
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (merged): T-011, T-012, T-013, T-014, T-020, T-020b, T-022
- **Decision deadline: 10:00 IST on 2026-11-15.** If v0.2 is not ready or fails any condition, v0.1 stays and the A1 FAIL is documented as a limitation.

## 4. Relevant files and directories
- Read: `docs/validation/T-020b-saturation.md`, `docs/validation/T-020-results.md`, `docs/validation/T-022-results.md`, `docs/DECISION_LOG.md` (D-005, D-028, D-029), `pipeline/calibration.py`, `pipeline/harmonize.py`, `pipeline/holdout.py`, `pipeline/saturation.py`, `pipeline/validation_a1.py`, `pipeline/validation_d.py`
- Create/modify:
  - `docs/task-prompts/T-020c-v02-conversion.md` (this file)
  - `pipeline/conversion_v02.py`, `pipeline/compare_v02.py` and their tests in `pipeline/tests/`
  - `pipeline/harmonize.py`: only an optional `factors` argument on `aggregate`, `fit_units`, `estimate_dispersion`; with `factors=None` the code and every result are unchanged (a test proves it)
  - `docs/DECISION_LOG.md` (D-030), `docs/validation/T-020c-v02.md` (report), `docs/RISKS_AND_LIMITATIONS.md` (the saturation finding), `docs/TASK_TRACKER.md` (row T-020c only)
- Not committed: everything under `data/interim/`.

## 5. Approved technologies
Python, NumPy, pandas, DuckDB, pytest, ruff (D-008). No new dependency.

## 6. Architecture and data contract
No contract change and no change to `data/products/`. v0.2 factors and comparison outputs live under `data/interim/v02/` (not committed); the small factor table is copied into the report.

## 7. Inputs
`cell_month_witness.parquet`, `cells.parquet`, `calibration.parquet` (v0.1, unchanged), `entity_month.parquet` for context only.

## 8. Expected outputs
`data/interim/v02/activity_factors.parquet` and `compare_report.json` (not committed); the report `docs/validation/T-020c-v02.md` with the factor table, the three adoption conditions side by side for v0.1 and v0.2, and the decision.

## 9. Implementation requirements (design fixed before any fit)
1. **Form (my choice, as the Lead allowed):** ratios by activity bin, pooled across strata. The v0.2 ratio of a stratum-month is `ratio_v01(stratum, witness, daynight, season) x f(witness, daynight, bin)`. The T-011 stratum ratios and their partial pooling stay; `f` is one global factor per witness, day/night and activity bin (full pooling across strata and regions at this level).
2. **Activity variable, known at estimation time:** the converted activity of the witness's own counts, `x = ratio_v01 x witness cell-days of the whole stratum-month / cells of the stratum` (Aqua-equivalent cell-days per analysis cell and month; Aqua is never used to bin). Bin edges as in T-020b: 0, 0.05, 0.15, 0.5, 1.5, 5, 15, 50, infinity. Binning on the witness's own count is the right conditional for prediction (E[Aqua | witness]); regression to the mean is shrinkage here, not bias.
3. **Fit (fit periods only, as `calibration.monthly_sums`):** units are stratum-months with witness cell-days above 0, day and night apart. `f(bin) = sum(Aqua) / sum(ratio_v01 x witness)` over the units of the bin, per witness and day/night. Bins with fewer than 50 units take the factor of the nearest bin that has 50 or more (no extrapolation). Factor uncertainty `f_sd`: 1,000 resamples of whole fit months (seed 20261115), standard deviation of `f`.
4. **Uncertainty:** `f_sd` is a shared error per witness, day/night and bin: strata in the same bin add fully correlated, `(sum cell_days x ratio x f_sd)^2`; the stratum ratio errors are scaled by `f`. Different bins and the stratum-ratio errors are treated as independent (limitation).
5. **Everything else as v0.1:** shared ratio errors, D-005 (Aqua night from 2024-05), D-028, the combination and the single day/night rule. **phi and kappa are re-estimated for v0.2 the same way on the fit periods** (`estimate_dispersion`, with the factors).
6. **Holdout (T-012 construction, unchanged):** 2017-01 to 2021-12, S-NPP against Aqua, Aqua >= 20 cell-days, regions and countries. The global-ratio baseline `glob` is unchanged.
7. **Adoption rule (pre-registered; Lead's wording).** Adopt v0.2 only if **all three** hold:
   1. Holdout median absolute log error of `ours` (day+night total, `T`) is **no worse than v0.1** (v0.2 <= v0.1, no tolerance) for **regions and countries**. The day and night parts are reported next to it; see §15.
   2. **D1 pooled 90% coverage stays within 80 to 97%** (the D1 definition of T-022: pooled day/night units of the 14 fire regions, with the v0.2 phi and kappa).
   3. **The A1 gap gets smaller in at least 3 of the 4 failed cases C3 to C6.** Gap = `|ln(S-NPP-only peak-window estimate / Aqua-only peak-window estimate)|`, the peak windows and boxes of `validation_a1.CASES`, both paths from `aggregate` as in T-020. Smaller means strictly smaller than v0.1.
8. **Labelling:** D-030 is a post-hoc improvement prompted by A1. A1 stays FAIL for v0.1 permanently; the v0.2 A1 numbers are reported as **not independent** (the cases motivated the change). v0.1 and v0.2 are shown side by side everywhere.
9. **Order:** write D-030 (PROPOSED, with this rule) and commit it before the first comparison run. No threshold, bin edge or rule changes after a result is seen; anything unexpected is reported as it is.
10. If the rule is not met or time runs out: v0.1 stays and the saturation finding goes into `docs/RISKS_AND_LIMITATIONS.md`.

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, data contract, D-028 thresholds, the validation plan or any earlier result. Do not touch `api/`, `app/` or `data/products/`.
- No secrets, no data files in Git, no direct pushes to `main`, no self-merge. No AI attribution (D-020).
- Building v0.2 products (`cell_month_harmonized`, `entity_month`) is **not** part of this task unless the Lead approves D-030.

## 11. Acceptance criteria
Holdout error no worse (regions and countries); D1 pooled 80 to 97%; A1 gap smaller in at least 3 of 4 failed cases; v0.1 kept visible. The report states adopt or keep v0.1 by the rule, with every number.

## 12. Required tests
`python -m pytest pipeline/tests -q` and `ruff check pipeline`. New tests on synthetic data with known answers: factors recover a planted ratio that rises with activity; a constant ratio gives factors near 1; bin assignment at the edges; small bins copy the nearest eligible bin; bootstrap reproducible; no month outside the fit periods; `aggregate(factors=None)` equals the earlier result exactly; with factors all 1 it equals v0.1; the factor error group adds fully correlated variance; the adoption rule on constructed inputs.

## 13. Documentation updates
`docs/DECISION_LOG.md` (D-030), `docs/validation/T-020c-v02.md`, `docs/RISKS_AND_LIMITATIONS.md`, row T-020c in `docs/TASK_TRACKER.md`.

## 14. Git branch and PR instructions
- Branch: `science/T-020c-v02-conversion` created from the latest `main`
- First commit: this prompt file; second commit: D-030 PROPOSED (before any comparison run)
- Open a PR; fill in `.github/pull_request_template.md`; never merge; wait for the Project Lead
- Commit with your own Git identity; no AI names or attribution (D-020)

## 15. Out-of-scope or blocking issues
- **Reading of "day+night" in condition 1:** I read it as the day+night total `T` of the T-012 report, the headline holdout metric. If the Lead means day **and** night each, the report gives both and the decision can be re-read; the stricter reading is shown too. The Lead may overrule in review, before the result, only.
- Time-box: decision by 10:00 IST. Building v0.2 products needs the Lead's approval of D-030.
