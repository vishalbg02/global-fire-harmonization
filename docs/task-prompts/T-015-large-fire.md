# Task prompt: T-015 Large-fire consistency check (diagnostic series per entity)

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main @ cd4a532
> Source of truth: `docs/TASK_TRACKER.md` row T-015 (on PR #61: "Diagnostic series per entity"), `docs/PROJECT_PLAN.md` F12 ("Large-fire consistency check, P1, diagnostic, not a correction"), `docs/SCIENTIFIC_METHODOLOGY.md` section 4.3 ("ratios assume the fire-size distribution within a stratum is stationary ... the P1 large-fire check is a diagnostic for it"), `docs/RISKS_AND_LIMITATIONS.md` S2. This prompt adds no scope beyond them.

## 1. Project context
The harmonized estimate counts fire-active fine cell-days (0.05 degree cell, at most once per day). The T-011 ratio Aqua over VIIRS is one number per stratum, day/night and season and assumes the fire-size distribution in a stratum is stationary. T-020b showed that the ratio rises with activity (saturation of the cell-day count). The docs name a "large-fire diagnostic" as the check for this assumption but do not define it.

## 2. Task objective
A diagnostic, not a correction, not a validation test and not a contract product: for each entity (country, fire region, world), witness and month, a series that shows how many detections and how much FRP fall on each fire-active cell-day. If large fires pile many detections into a cell-day, the cell-day count is blind to their size; a month whose index is far above the entity's usual level is a large-fire month in which the cell-day measure (and therefore a ratio fitted on typical months) is least reliable.

## 3. Assigned responsibility
- Task ID / priority: T-015 / P1 · Owner: Member 2 · Reviewer and merger: Member 1 · Dependencies: T-006 (merged)

## 4. Relevant files
- Read: `docs/validation/T-020b-saturation.md`, `pipeline/saturation.py` (built on, not repeated), `pipeline/calibration.py` (`FITS`), the products `cells`, `cell_month_witness`.
- Create: `docs/task-prompts/T-015-large-fire.md` (this file), `pipeline/large_fire.py`, `pipeline/tests/test_large_fire.py`, `docs/validation/T-015-large-fire.md` (report).
- Not committed: `data/interim/qa/T-015_large_fire_series.parquet` and `T-015_large_fire_summary.json`.

## 5. Approved technologies
Python, NumPy, pandas, DuckDB, pytest, ruff (D-008). No new dependency.

## 6. Architecture and data contract
No change. No product, no `validation_results.json` entry, no change to `api/` or `app/`.

## 7. Inputs
`data/products/cell_month_witness.parquet` (rows with `daynight = 'ALL'`, all four witnesses) and `cells.parquet` (country, fire region).

## 8. Expected outputs
The series file, the summary JSON, and the report with definition, headline findings and caveats.

## 9. Implementation requirements (fixed before any real run)
1. **Entities:** COUNTRY (`cells.country_iso3`; cells without a country are in no country), FIRE_REGION (`cells.fire_region`, including `UNASSIGNED`, reported as such), GLOBAL (all cells). Continents are not included.
2. **Aggregation:** per entity, year, month and witness, summed over the entity's analysis cells: `detections`, `cell_days`, `frp_sum_mw`, and `active_cells` (cells with `cell_days > 0`). Rows `daynight = 'ALL'` only (verified on the products: ALL cell-days equal day plus night cell-days, so a cell-day with both a day and a night detection counts twice there; this applies equally to all witnesses). All four witnesses, Terra included, because this is a diagnostic of the data, not of the estimate.
3. **Pile-up index** `S = detections / cell_days` (detections per fire-active cell-day; at least 1 by construction when cell_days > 0, except for the day/night double counting above). **Intensity** `F = frp_sum_mw / cell_days` (MW per cell-day). Both are ratios, so they do not depend on the days a witness was available.
4. **Cross-witness consistency** `S_rel = S_witness / S_Aqua` for the same entity and month, when both are judged (below).
5. **Judged:** a row is judged only if `cell_days >= 100` (MIN_CELL_DAYS); else `status = LOW_COUNT` and the index, flag and `S_rel` are empty (not filled, not interpolated). Months with no row stay absent.
6. **Reference level** per entity and witness: the median of `S` over the judged months of the reference period: S-NPP, Aqua and Terra 2012-01 to 2016-12 (the S-NPP calibration fit period of T-011); NOAA-20 2018-04 to 2021-12 (its fit period). At least 12 judged reference months are needed, else `status = NO_REFERENCE` and the index is empty. Same for `F`.
7. **Index** `S_index = S / reference S`, `F_index = F / reference F`.
8. **Flag** `LARGE_FIRE_HIGH` (descriptive, not PASS/FAIL, not a test) when the row is judged, has a reference and `S_index >= 1.5` (FLAG_FACTOR). The factor is a reading chosen now, before any result; it is never tuned on the result. A second view uses `S_index >= 2`; both are reported with their counts.
9. **Summaries in the report** (no thresholds beyond the above): per witness the global `S`, `F` by year and the OLS slope of global `S` on year over the witness's operating years; per entity type and witness the number and share of judged entity-months flagged; the 15 flagged entity-month-witness rows with the highest `S_index` among rows with `cell_days >= 1000`; the median `S_rel` for the VIIRS witnesses inside versus outside their reference period (drift of the cross-witness consistency), global and per fire region.
10. **Relation to T-020b** is described, not tested: the report says whether flagged months are months of high activity (median cell-days of flagged versus non-flagged rows), without rerunning the saturation analysis.
11. Heavy-job protocol: lock, DuckDB limits, temp directory removed at the end.

## 10. Constraints: do not modify
`harmonize.py`, `calibration.py`, `saturation.py` and every other module of earlier tasks; the products; thresholds of D-028; `api/`, `app/`. No secrets, no data files committed.

## 11. Acceptance criteria
The series exists for all entities and witnesses with the definition above; the report gives definition, findings, caveats; nothing is called PASS or FAIL.

## 12. Required tests
`python -m pytest pipeline/tests/test_large_fire.py -q` on SYNTHETIC data with known answers: S and F for planted counts; LOW_COUNT rows empty; reference median and index; flag at the factor (exactly 1.5 flags, just below does not); `S_rel`; NO_REFERENCE; the aggregation on a tiny synthetic product (a cell without country excluded from countries but in the world; daynight other than ALL ignored). `ruff` clean.

## 13. Documentation updates
`docs/validation/T-015-large-fire.md`. The tracker row T-015 only when PR #61 is on main.

## 14. Git
Branch `science/T-015-large-fire`; first commit this prompt; draft PR with the template; never merge.

## 15. Out-of-scope or blocking issues; readings for the Lead
- **[ASSUMPTION 1]** The docs do not define the diagnostic. I read it literally as "does the cell-day measure hide fire size": detections and FRP per cell-day, per entity, witness and month, against the entity's own reference level. A richer definition (per fire event, size distributions) needs fire clustering, which the products do not contain; not done.
- **[ASSUMPTION 2]** Thresholds (100 cell-days, 12 reference months, factors 1.5 and 2) are my reading, fixed before the run, descriptive only.
- **[ASSUMPTION 3]** The reference period is the calibration fit period, the period for which the ratio is "typical". A large-fire month outside it is where the ratio is applied outside its fit conditions.
- A diagnostic shown in the app (F12 is a feature) would need a new contract product or field; not built. See "Scope issues" in the PR.
