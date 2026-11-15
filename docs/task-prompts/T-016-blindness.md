# Task prompt: T-016 "MODIS blindness" indicator (F13)

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main @ cd4a532
> Source of truth: `docs/PROJECT_PLAN.md` row F13 ("MODIS blindness" indicator, P1, "Falls out of the calibration step"); tracker row T-016 (PR #61): "Per-region value with caveat text".

## 1. Project context
VIIRS (375 m) detects more small fires than MODIS (about 1 km) (`docs/SCIENTIFIC_METHODOLOGY.md` section 2, `docs/RESEARCH_SUMMARY.md`). The T-011 calibration converts each VIIRS witness to the Aqua scale with a ratio Aqua over VIIRS that varies by region, day/night and season. The plan says the blindness indicator "falls out of the calibration step", but nowhere defines it more precisely. Hypothesis S15 (accepted as a hypothesis, not a fact) is that low night ratios in savanna and agricultural regions mean MODIS misses many small night fires there.

## 2. Task objective
Per fire region, one number that says how much more satellite-detected fire activity VIIRS records than Aqua, with an interval and caveat text, so the app could later show where MODIS-era records are likely to understate activity. A derived table and a report. Not a contract product, not a validation test.

## 3. Assigned responsibility
- Task ID / priority: T-016 / P1 (cut first if time is short, F13)
- Owner: Member 2 · Reviewer and merger: Member 1 · Dependency: T-011 (merged)

## 4. Relevant files and directories
- Read: `pipeline/calibration.py` (`monthly_sums`, `FITS`, `fit_months`, `SEASON_OF`, `load_cells`), `data/products/cells.parquet`, `cell_month_witness.parquet`, `calibration.parquet`, `docs/validation/T-020b-saturation.md`
- Create: this file, `pipeline/blindness.py`, `pipeline/tests/test_blindness.py`, `docs/validation/T-016-blindness.md`
- Not committed: `data/interim/blindness/` (the derived table)

## 5. Approved technologies
Python, NumPy, pandas, DuckDB, pytest, ruff. No new dependency.

## 6. Architecture and data contract
No contract change, no product, no change to T-011, T-013, T-014, API or app. If the app needs a field for this, it is described in the PR under Scope issues and not built.

## 7. Inputs
`cell_month_witness.parquet`, `cells.parquet` (cell to fire region), `calibration.parquet` (cross-check only). Fit periods only (S-NPP 2012-01 to 2016-12, NOAA-20 2018-04 to 2021-12, complete months of both witnesses, exactly as T-011). Held-out years and every validation case window are never used.

## 8. Expected outputs
- `data/interim/blindness/blindness_by_region.csv` (and `.json` with the run metadata).
- `docs/validation/T-016-blindness.md`: the table of numbers, the caveats, the reading.

## 9. Implementation requirements (fixed before any real run)
1. **Indicator (definition).** For a fire region R, witness V in {S-NPP, NOAA-20}, day or night, and a month set M (all fit months, or the fit months of one season):
   `B = (sum over M and the cells of R of VIIRS cell-days) / (sum of Aqua cell-days)`.
   It is the inverse of the T-011 ratio computed at fire-region level on the fit months: "VIIRS cell-days per Aqua cell-day". B above 1 means VIIRS records more fire-active cell-days than Aqua in that region; the "extra share" 1 - 1/B is also given (the share of VIIRS cell-days that Aqua has no counterpart for, as a sum, not cell by cell; negative when B is below 1). Units: dimensionless ratio of cell-days. Only complete months of both witnesses, as in `calibration.monthly_sums`.
2. **Uncertainty.** 90% interval (5th and 95th percentile) by a bootstrap over whole fit months (1,000 replicates, seed 20261115), within the month set. This is the sampling spread over months only. It does not include model error. The calibration `ratio_sd` (bootstrap spread of the pooled stratum ratio) is a different quantity; as a cross-check the table adds, for each region, witness, day/night and season, the inverse of the median T-011 stratum ratio of that region (`calib_inverse_median`) and the median `ratio_sd / ratio` of its strata (`calib_median_rel_sd`).
3. **Cannot determine.** B is given only if both the Aqua and the VIIRS sums are at least 100 cell-days and at least 6 months have both an Aqua and a VIIRS cell-day; otherwise the row is `CANNOT_DETERMINE` with the value empty. These thresholds are my choice, fixed now. A row is flagged `BURST` if one month holds more than half of the Aqua or the VIIRS cell-days of the month set (as in T-011); the value is still shown, with the flag.
4. **Regions.** The 14 GFED fire regions of `cells.fire_region`. `UNASSIGNED` is shown as a separate row marked "not a fire region".
5. **Caveat text** (stored in every row and in the report): this is not a fire count, not burned area and not a detection probability; B mixes the 375 m versus 1 km sensitivity with different overpass times (Aqua about 13:30 and 01:30; S-NPP about 13:30; NOAA-20 about 12:40), thresholds and cell-day saturation (T-020b confirmed that the Aqua/VIIRS ratio rises with activity, so B is lower in very active regions and months for that reason alone); it describes the fit periods only, not other years; the interval is month sampling only.
6. **Reading rule for the report.** The report says a region is "higher than the global value" only where its 90% interval lies entirely above the global B of the same witness, day/night and month set (and "lower" likewise). No causal claim ("MODIS misses X% of fires") is made; the S15 explanation stays a hypothesis.
7. **Sanity check.** The pooled global B per witness, day and night is shown, plus a check that the regional sums add up to the global sums.

## 10. Constraints: do not modify
Do not change `calibration.py`, `harmonize.py` or any earlier module, the products, the thresholds in D-028 or the validation plan; do not touch `api/` or `app/`. No secrets, no data files committed, no direct pushes to `main`.

## 11. Acceptance criteria
A per-region value (day and night, both witnesses, all-year and by season) with interval, status and caveat text, and a report that states what the number is not.

## 12. Required tests
`python -m pytest pipeline/tests/test_blindness.py -q` on SYNTHETIC data with known answers: a planted ratio recovers B; a region with too little data is `CANNOT_DETERMINE`; the interval covers the planted value and is reproducible with a fixed seed; the extra share formula; the burst flag; months outside the supplied set are not used; regional sums equal the global sum; the interval is wider with fewer months. `ruff` clean on the files of this task.

## 13. Documentation updates
`docs/validation/T-016-blindness.md`. The tracker row is updated only when PR #61 is on main.

## 14. Git branch and PR instructions
Branch `science/T-016-blindness` from the latest `main`; this file is the first commit; draft PR early; never merge; own Git identity, no AI attribution (D-020).

## 15. Out-of-scope or blocking issues
- **[ASSUMPTION] Definition.** The project documents only name the indicator and say it falls out of the calibration. I read it as the region-level VIIRS-to-Aqua cell-day ratio of the fit periods (item 9.1), the most literal and least interpretive reading. The Lead may prefer another form (for example 1 minus the ratio, or a seasonal-only or night-only indicator); the table carries B and the extra share, so any of these can be read off without a rerun.
- **[ASSUMPTION] Thresholds** of item 9.3 (100 cell-days, 6 months) are mine.
- **[ASSUMPTION] Scope of "region"**: GFED fire regions of `cells.fire_region`, not countries.
- If the app needs a contract field (per-region indicator), that is a contract change for the Lead (Scope issues in the PR). Nothing is built here.
