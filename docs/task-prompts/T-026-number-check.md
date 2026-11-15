# Task prompt: T-026 Verify every number displayed in the app and the demo against the products

> Prepared for: Member 2 (with Member 1 for the sign-off) · Date: 2026-11-15 · Based on `origin/frontend/T-039-real-verdicts` @ ce0e155 (PR #62, the app of T-039 phase 2, not yet merged; this branch is cut from it and says so in the PR)
> Source of truth: docs/TASK_TRACKER.md row T-026 (PR #61), the Lead's instruction on #61 ("Final, with me: T-026, checking every number in the app and the demo script against the products, after T-039 phase 2 and the v0.2 decision"; v0.2 is not adopted, D-030 closed) and the inventory `docs/NUMBER_INVENTORY.md` written by Member 3 for this task. This prompt adds no scope beyond them. T-026 never changes the app, the API or a product.

## 1. Project context
Judges will read numbers off the app and the demo. Every number there must be a stored product value, or a documented formatting of one, and never a wrong or invented value. The app shows stored values from the API and formats them (whole percentages, one decimal, "more than 99%"); `docs/NUMBER_INVENTORY.md` lists every displayed number, its source column and its format. T-026 checks that list against the products.

## 2. Task objective
A reproducible checker that, for a fixed list of views and for every row of the products, confirms (a) that the API serves exactly the stored value, (b) that the app's own formatting code shows what the inventory says it shows, (c) that the three numbers the app computes itself (rank, "N of M in neither ranking", test-status counts) are right, (d) that the CSV and the methods page match the products and the documents they cite. The result is a report with every check and every mismatch, and an unchecked sign-off list for the Lead.

## 3. Assigned responsibility
- Task ID / priority: T-026 / P0 · Owner: Member 2 + Member 1 (sign-off) · Reviewer and merger: Member 1
- Dependencies: T-039 phase 2 (PR #62). If #62 changes after this PR is opened, re-run the checker (one command) and update the report.

## 4. Relevant files and directories
- Read: `docs/NUMBER_INVENTORY.md`, `app/src/components/map/format.ts`, `components/anomalies/rankings.ts`, `components/methods/validationFormat.ts`, `components/calendar/{text,grid,scales}.ts`, `components/witness/series.ts`, `state/bbox.ts`, `app/src/content/methods.ts`, `api/fire_api/*.py`, `api/README.md`, the products in `data/products/`, `docs/DATA_CONTRACT.md`, `docs/validation/*`.
- Create/modify: `docs/task-prompts/T-026-number-check.md` (this file), `pipeline/number_check.py`, `pipeline/number_check_app.mjs` (a node script that calls the app's own TypeScript helpers; read-only use of `app/`), `pipeline/tests/test_number_check.py`, `docs/validation/T-026-number-check.md` (the report), nothing else.
- Not committed: everything under `data/interim/`.

## 5. Approved technologies
Python, pandas, DuckDB, pytest, ruff, FastAPI's TestClient (already in `api/requirements.txt`), Node 22 (the app's own runtime; the helpers are imported as TypeScript with Node's built-in type stripping). No new dependency; no `npm install` is needed for the helpers used.

## 6. Architecture and data contract
No change. The checker reads the API in process (`fire_api.main:app` with `PRODUCTS_DIR=data/products`) through the TestClient, so it checks the code that serves the app, not a copy.

## 7. Inputs
`data/products/{cells,cell_month_harmonized,entity_month}.parquet`, `metadata.json`, `validation_results.json` (the file of the branch; the T-027 file of PR #70 is also read from its branch for the methods-page tally), the app and API of the branch.

## 8. Expected outputs
`data/interim/qa/T-026_number_check.json` (not committed) and `docs/validation/T-026-number-check.md`: per check class the number of values checked, the number that match, and every mismatch with view, field, stored value, displayed value and class.

## 9. Implementation requirements (fixed before any result)
1. **Views.** Fixed: the demo scenes of T-050 and the default scenes of the task prompt of T-039 phase 2: Indonesia (country IDN) 2015-09 and 2015-10; Brazil (BRA) 2019-08; Canada (CAN) 2023-07; the world (GLOBAL) for the latest month in `metadata.json`; the continents for 2015-09; the anomaly lists of 2015-09, 2023-08 and the latest month; the calendar and the satellite series of IDN; the CSV export of IDN; one analysis cell inside Indonesia (the cell of the largest `estimate` in 2015-09); the methods page.
2. **Check A, API against products.** For each view the answer of the endpoint equals the stored rows: every numeric field exactly (float equality after a JSON round trip: the same double), every null a null, never 0; `raw_by_witness` decoded equals the stored JSON; map answers hold one record per cell with the stored fields; the series are ordered by month; the anomaly answer equals the stored rows with an ABOVE or BELOW verdict, in the documented order (larger of `p_above` and `p_below`, then `abs(ln(pct_of_normal / 100))`, then `entity_id`), recomputed independently from `entity_month`.
3. **Check B, formatting.** For **every** row of `entity_month` and every non-null number of `cell_month_harmonized` (all rows): the app's real functions `formatProbability`, `formatPctOfNormal`, `formatEstimate`, `verdictProbability` (`components/map/format.ts`), `pctText` and `probabilityText` (`rankings.ts`) are called through node on the stored values and compared with the string the inventory rule gives, computed independently in Python by the rule of the inventory (whole numbers rounded as JavaScript does, half up; one decimal as JavaScript `toFixed`; the probability wording thresholds 0.995 and 0.005). A Python port that differs from JavaScript on a half is itself a finding to understand, not to hide.
4. **Check C, what the app computes.** `rankAnomalies` keeps the API order and splits above and below; `notRankedCount(M, rankings)` equals M minus the entries of the two rankings for each tab and month; `countStatuses` (`validationFormat.ts`) equals a tally of `validation_results.json` for the file of the branch and for the T-027 file; the rank shown is `index + 1`.
5. **Check D, the CSV.** For the export of IDN: the header rows, the 25 contract columns plus the five `raw_*` columns, one row per stored month, every number equals the stored value (repr precision), null is an empty cell, no 0 where the product is null.
6. **Check E, hand-written text of the methods page.** The numbers written in `app/src/content/methods.ts` that the inventory lists (baseline 2003 to 2022 and 15 years, probability threshold 0.8, phi 2.25 and 2.47, kappa 0.0084 and 0.0164, grid 0.5 and 0.05 degrees, D1 coverage 0.818 and 0.811, the shares of judgeable months 29.6%, 52.7% and 34.1%, and any other number in the text) are compared with the document or the product each cites; the shares are recomputed from the products. Where a document and a product disagree, both are reported.
7. **Classes of result.** MATCH; DEFECT (a displayed or served number differs from the product); DOC (hand-written text differs from its source); NOTE (a limit to know about, for example colour clamps or ECharts default tooltip numbers, which this check cannot read; those are listed for a browser pass).
8. **No fixing.** A defect is reported to the Lead and Member 3. T-026 changes no file of `app/`, `api/` or `data/products/`.
9. **Tolerances.** None for stored values (exact). Percentages displayed are compared as strings.
10. **Sign-off.** The report ends with a checklist of the inventory rows for the Lead to tick; this task does not tick it.

## 10. Constraints: do not modify
- Do not change `app/`, `api/`, the contract, the methodology, the products or any earlier report. Do not touch Member 3's branch.
- No secrets, no interim data in Git, no direct pushes to `main`, no self-merge. No AI attribution (D-020).
- Heavy reads (the full `cell_month_harmonized`) take the heavy-job lock (`mkdir data/interim/.heavy_lock`) and DuckDB limits (`memory_limit` 5 GB, `max_temp_directory_size` 20 GiB).

## 11. Acceptance criteria
Every row of the inventory has its check result; the report lists every mismatch and every note; the checker reproduces with one command; the sign-off list is left for the Lead.

## 12. Required tests
`python -m pytest pipeline/tests/test_number_check.py -q` on SYNTHETIC data: the JavaScript rounding emulation (half up, negative values, .5 boundaries) and `toFixed`; the probability thresholds at 0.995, 0.994999, 0.005, 0.0050001; the anomaly-order recomputation on a planted list with ties, nulls and non-positive `pct_of_normal`; the comparison reports a planted wrong number as a DEFECT and a null shown as 0 as a DEFECT; the CSV check catches a changed cell. `ruff` clean on the new files.

## 13. Documentation updates
`docs/validation/T-026-number-check.md`; the tracker row T-026 once PR #61 is on `main`.

## 14. Git branch and PR instructions
- Branch: `science/T-026-number-check`, cut from `origin/frontend/T-039-real-verdicts` (PR #62) because the app is not on `main` yet; the PR says so and the Lead can have it rebased once #62 is merged.
- First commit: this prompt. Open a PR with the template; never merge.

## 15. Out-of-scope or blocking issues
- The Lead asked to start against the branch of #62; if #62 changes, the checker is re-run.
- Numbers a browser draws (ECharts axis and hover numbers, colour scales) cannot be read by this checker; they are listed as NOTE for a browser pass with the Lead.
- The demo script (T-060) does not exist yet; the demo scenes of T-050 stand in for it and the report says so.
