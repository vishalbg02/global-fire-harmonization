# Task prompt: T-039 Real-data integration (phase 1: real cells and raw counts)

> Prepared for: Member 3 · Date: 2026-11-14 · Based on main @ aa79228
> Source of truth: docs/TASK_TRACKER.md row T-039 and the Lead's kick-off comment on PR #38. This prompt adds no scope beyond them.
> **Assignment status:** the Lead assigns T-039 (with T-041 to T-044) in PR #38 and asks for **phase 1 now**: real cells and raw counts (T-006 is merged). Harmonized fields follow after T-014 (phase 2, a later PR). The Lead marks the tracker row; this task does not edit it (see §13).

## 1. Project context

The team is building a global web platform for the NASA Space Apps Challenge 2026, "Harmonization of MODIS and VIIRS Hot Spots" (Many Witnesses + Witness Stand, global scope, D-002/D-003). Member 2's pipeline produces monthly products; Member 3 builds the API and web app around them. Until now the API served only the SYNTHETIC fixtures (`data/fixtures/v0.1.0`). Member 2's merged T-006 now yields real `cells.parquet` and `cell_month_witness.parquet`, and T-011 yields `calibration.parquet`. No harmonized product (T-014) exists yet. T-039 phase 1 makes the app show what is really there and nothing else.

## 2. Task objective

When phase 1 is done, with `PRODUCTS_DIR` pointing at the real products the app shows: the real 0.5° grid; **raw** values on the map and in the calendar (sum of `cell_days` over the witnesses that operated); and per-witness raw contributions and outages in the evidence panel and witness chart. Everything that needs harmonization (estimate, interval, baseline, % of normal, probabilities, verdicts) is shown as "not available yet" and is empty, never taken from fixtures and never mixed with real values. The SYNTHETIC banner disappears only for views that are fully real; partial views say so plainly.

## 3. Assigned responsibility

- Task ID / priority: T-039 / P0 (phase 1)
- Owner: Member 3 (Application Development & UI), with Member 2 for the products
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies: T-006 (merged: real cells and witness counts), T-034 (merged). T-014 (harmonized product) is needed only for phase 2.

## 4. Relevant files and directories

- Read: `CLAUDE.md`, `docs/TASK_TRACKER.md`, `docs/TEAM_WORKFLOW.md`, `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACT.md` (§1, §2, §4, §7), `docs/TECH_STACK.md` (§7), `docs/DECISION_LOG.md`, `docs/prompts/MEMBER_3_APPLICATION_PROMPT.md`, `data/README.md`, `api/README.md`, `app/README.md`
- Create/modify (nothing else; see §15 for items awaiting the Lead):
  - `api/fire_api/products.py` and `main.py`: raw-only mode when the harmonized products are absent
  - `api/tests/`: tests for the raw-only and the missing-product states
  - `api/README.md`
  - `app/src/`: "not available yet" and partial-data states in the map, calendar, evidence panel, witness chart, anomaly list and banner, with tests
  - `app/README.md`
  - `docs/RISKS_AND_LIMITATIONS.md` (any limitation found)
  - `docs/task-prompts/T-039-real-data.md` (this file)
- Nothing is added under `data/` except what is already ignored; the real products stay local (about 180 MB), never in Git.

## 5. Approved technologies

From `docs/TECH_STACK.md` §7 (D-008): FastAPI, DuckDB, Pydantic, React, Vite, TypeScript, MapLibre, deck.gl, ECharts, TanStack Query, Vitest, pytest, ruff. No new package is needed.

## 6. Architecture and data contract

- Components: API and web app (`docs/ARCHITECTURE.md` §2). The app talks only to the API.
- Contract `0.1.0` (D-016) is not changed. Real products present now (checked locally against Member 2's SHA256SUMS, all three hashes match):
  - `cells.parquet`: 56,238 rows, columns as in contract §1 (927 cells have a null country; 226 distinct country codes and 7 continent codes).
  - `cell_month_witness.parquet`: 146,612,466 rows, columns as in contract §2. Witnesses Aqua, Terra, S-NPP and NOAA-20 (no NOAA-21); `daynight` is `D`, `N` and `ALL`; `data_level` `SP` through 2026-08 and `NRT` from 2026-08 to 2026-11; no duplicate keys; `days_available` between 2 and 31.
  - `calibration.parquet`: 96,384 rows. Not used in phase 1 (it feeds harmonization).
- Not present yet: `cell_month_harmonized.parquet`, `entity_month.parquet`, `metadata.json`, `validation_results.json`.
- Raw values are computed in the API only from stored columns: `raw_combined_cell_days` is the sum of `cell_days` (`daynight = ALL`) over the witnesses that have a row for that cell and month, and `raw_by_witness` is the same per witness (contract §3, §4). This is addition, not science.

## 7. Inputs

- `cells.parquet`, `cell_month_witness.parquet`, `calibration.parquet` and `SHA256SUMS.txt` from Member 2 (received 2026-11-14; hashes verified). A fourth file, `cells_T006_backup.parquet`, is not in the manifest and is not used.
- The Lead's kick-off comment on PR #38.
- Test data: tiny `SYNTHETIC` products built inside test files only. Nothing in `data/fixtures/` is edited.

## 8. Expected outputs

1. API in raw-only mode (no harmonized products): `GET /api/map` returns every cell for the month with `raw_combined_cell_days`, and every harmonized field empty; the series, evidence and CSV export for a country, continent or the world are summed from the cells' raw values (see §15, items 2 to 4).
2. API states that never crash on a missing product: documented `503` (or an explicit empty list) for each endpoint that needs a missing product, each with a test.
3. App: raw map and raw calendar from real values; the harmonized / verdict map and the harmonized calendar show "not available yet" with an explanation; the evidence panel shows the raw contributions and says the verdict is not available yet; the witness chart shows the raw lines and outages and no harmonized line or band; the anomaly list says none can be computed yet.
4. A clear label on every partial view, and the SYNTHETIC banner only while any product shown is synthetic (see §15, item 1).
5. No fixture value ever appears next to a real value.

## 9. Implementation requirements

1. **No science.** Only sums of stored columns. No estimates, baselines, ratios, probabilities or verdicts are computed; "not available" is shown, not approximated.
2. **No mixing.** Real and fixture products are never combined: the API reads one products directory, and a missing product is an empty or `503` state, never a fallback to fixtures.
3. **Contract fidelity.** Missing harmonized fields are `null`, never `0`. Types and enums are unchanged.
4. **Wording.** "Satellite-detected fire activity", never "number of fires". Raw counts jump when satellites join or leave; the existing raw note stays.
5. **Accessibility:** WCAG 2.1 AA contrast, visible focus, no information by colour alone.
6. TypeScript strict, ruff-clean Python, type hints.

## 10. Constraints: do not modify

- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not touch `pipeline/` or `data/` (except placing the ignored local products).
- Do not commit any product or Parquet file.
- Do not build T-041 to T-044 here.
- No secrets, no `.env` files, no direct pushes to `main`, no self-merge.
- No AI tool names or attribution in commits, PR text, branch names, code comments or metadata (D-020).
- Do not mark anything validated that has not run.

## 11. Acceptance criteria

From the tracker: **"All views on real products."** For phase 1, made measurable:

1. With the real products, the map shows the real grid and raw values; the raw calendar for a country, a continent and the world shows real values; the witness chart shows real per-witness lines and outages.
2. Every view that needs a harmonized value shows "not available yet", never a fixture or a zero.
3. Each API endpoint with a missing product returns its documented state (tested).
4. Real values in the app agree with the Parquet files for sampled cells and areas (checked by independent queries and reported).
5. The banner and labels are right for partial data.
6. `pytest`, `ruff` in `api/`; `npm ci`, `npm run build`, `npm test`, `npm run lint`, `npm run typecheck` in `app/` pass.

## 12. Required tests

- pytest: raw-only `/api/map` (sums, nulls, a month with one witness, a month with none); series sums by country, continent and world; each endpoint with a missing product; no fixture value leaks.
- Vitest: "not available yet" states and the partial-data label; banner rule.
- Manual (reported honestly): the app against the real products for a month with all witnesses and a month with one; sampled cells and areas checked against the Parquet files; response times for `/api/map` on the full file; screenshots with the correct banner and labels.

## 13. Documentation updates

- `docs/TASK_TRACKER.md`: not edited (the Lead marks it).
- `api/README.md`, `app/README.md`: raw-only mode and the new states.
- `docs/RISKS_AND_LIMITATIONS.md`: limitations found.
- `docs/HANDOFF.md`, `docs/PROGRESS_LOG.md`: a PR note asking the Lead to update them.

## 14. Git branch and PR instructions

- Branch: `frontend/T-039-real-data`, created from the latest `main`.
- First commit: this prompt file.
- Open a DRAFT PR early; title "T-039: Real-data integration (phase 1)"; fill in `.github/pull_request_template.md` with the real summary, changed files and results.
- Mark Ready for review only when §11 and §12 are satisfied.
- Never merge; wait for the Project Lead.
- Commit with your own Git identity; no AI names or attribution (D-020).

## 15. Out-of-scope or blocking issues

Open questions for the Lead. None is decided here. Suggested defaults are what I will do if the Lead does not answer.

1. **Assignment and tracker.** PR #38 assigns T-039. I will start on the strength of the Lead's PR text and not edit the tracker.
2. **`metadata.json` for the real set.** The API needs `/api/meta` (versions, `synthetic`, `provisional_months`, snapshot dates, citation) and the app reads it for the banner. None exists for the real products. Default: Member 2 supplies it with `synthetic: false`; until then I use a local file outside Git for development only. I will not invent its contents in the repo. Who writes it, and which `method_version` does a raw-only set carry?
3. **How "harmonized not available" is represented.** The contract has no flag for it, and I may not change the contract. Default: harmonized fields `null`, `verdict` `CANNOT_DETERMINE`, empty `reason_codes`, and the app labels the missing harmonized values from a missing-product signal. The signal must come from somewhere: (a) a new optional field in `/api/meta` (for example `products_available`), which needs the Lead's approval of a contract addition (D-016/D-022), or (b) the app infers it from every `estimate` being `null`. Which? I prefer (a) as less fragile.
4. **Series, evidence and export in raw-only mode.** `entity_month.parquet` does not exist. Default: the API computes the entity's monthly series on the fly from the cells (grouped by `country_iso3`, `continent`, or all cells for the world), with `raw_combined_cell_days`, `raw_by_witness` (JSON string), `witnesses_used`, `n_witnesses`, `n_cells`, `data_level` and every harmonized field `null`. This uses only sums. Confirm, or should Member 2 deliver `entity_month` with raw-only values instead?
5. **Entity names.** `cells.parquet` has only ISO codes. Default: `entity_name` is the ISO 3166-1 alpha-3 code or the continent code until Member 2 supplies names; the app already shows the Natural Earth name for a clicked country and I would use it where it exists. Confirm, or who supplies a name table?
6. **Cells with no country (927).** Default: they appear on the map and in the world total, but in no country or continent total, as the products define. Confirm.
7. **`data_level` and provisional months.** Months from 2026-08 are `NRT` for some witnesses. Default: a month is provisional if any witness row in it is `NRT`, derived from the stored `data_level`, and reported through `/api/meta` `provisional_months`. Is deriving this in the API acceptable, or should `metadata.json` carry it?
8. **Outages.** The witness chart marks outages. Default: from `days_available < days_in_month` summed per witness for the entity, shown as the outage mark with the days missing. Confirm that this is the intended use of `days_available`.
9. **Per-request cost.** On the full 147M-row file a one-month query took about 0.05 s locally; series for the world scan the whole file. Default: measure and report; add a cache or a precomputed local table only if a request is too slow (and not commit it). Acceptable?
10. **Where the real files live.** Default: `data/products/` (already ignored by Git), copied from Member 2's team-drive files, with `PRODUCTS_DIR=data/products`. Confirm.
11. **Phase 2.** Default: harmonized fields, baselines and verdicts are a separate PR after T-014, on this same task row. Confirm that phase 1 is merged on its own and the row is not marked MERGED until phase 2.
