# Task prompt: T-090 Analytics compare and exact coverage

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main (HEAD at branch creation)
> Source of truth: the Lead's comment on PR #74 (new batch T-089, T-090, T-091), item T-090.

## Task
1. A "Compare with" area search inside the Analytics panel (reuse `ui/Combobox`), wired to the existing `compareArea` prop and kept in the link as `compare=`; an invalid value is ignored; only areas the series endpoint serves (countries, continents, the world).
2. **Exact coverage per country and continent.** Add `country_iso3` and `continent` columns to `GET /api/map/cells` (additive; values straight from `cells.parquet`; every old field and every other endpoint unchanged; documented in `api/README.md`; API test). The Lead approved the additive columns in the batch comment. The panel then counts the area's own cells instead of a bounding box; the world stays all cells; the "shown for the world only" message goes away when the exact figure exists and stays (as a clear message) if the columns are missing (an older API, or the offline copy). Extend `pipeline/analytics_check.py` so the figures for a country (Indonesia, India) and a continent (Asia) are reproduced from the products with 0 mismatches against the panel's own functions.

## Files
API: `api/fire_api/products.py`, `map_columns.py`, `api/tests/`, `api/README.md`. App: `app/src/api/client.ts` (+ a small decoder), `app/src/components/analytics/`, the link-state helper for `compare=`. Pipeline: `pipeline/analytics_check.py`, its Node bridge and tests. Not touched: other Member 3 components, products, thresholds, `GET /api/map`.

## Requirements
Values are the stored values; no number in the products changes. The map month payload is not made heavier (the area columns belong to the cell list, fetched once). Real data only, no fixture in production code.

## Git
Branch `frontend/T-090-analytics-compare-coverage` from the latest `main`; first commit: this prompt; PR with the template, the real-data statement and the note that the additive columns were approved by the Lead on #74; never merge; human identity, no AI attribution (D-020).
