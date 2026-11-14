# Task prompt: T-035 follow-up, wire `harmonize_area()` into custom areas

> Prepared for: Member 3 · Date: 2026-11-14 · Based on main @ 1b4b252
> Source of truth: the Lead's comments on PR #38 and PR #46 (2026-11-14): "a separate small follow-up PR for the custom-area wiring (branch e.g. `frontend/T-035-harmonize-area`). Import `harmonize_area()` from `pipeline/harmonize.py` in `api/fire_api/custom.py` for both the rectangle and the T-044 polygon path, with tests against real products, and a measured response time for one country-sized box. Verdict fields stay `null` until T-014." This prompt adds no scope beyond it; the tracker is not edited.

## 1. Objective

`POST /api/series/custom` and `GET /api/export.csv?bbox=` return the real harmonized series of the chosen rectangle (from `harmonize_area()`, `0.1.0-combined-no-baseline`) instead of `503`. The API never reimplements the science (D-015, DATA_CONTRACT §8). T-044 (polygon) will call the same function; this PR does not build the polygon UI.

## 2. In scope

- `api/fire_api/custom.py`: `load_harmonize_area()` imports `harmonize_area` from `pipeline/harmonize.py` and binds it to the API's `PRODUCTS_DIR`; `503` remains only when the import or the products fail.
- `api/tests/`: tests against the real products in `data/products/` (skipped with a clear reason when the files are only Git LFS pointers), plus the existing synthetic tests unchanged.
- A measured response time for one country-sized box, in the PR description.
- `api/README.md` and `docs/RISKS_AND_LIMITATIONS.md` (T13 no longer applies once wired).
- The dependencies the function needs (see open question 1).

## 3. Out of scope

- The polygon UI and point-in-polygon cell rule (T-044).
- Any change in `pipeline/`, `data/`, the contract or the method. Verdict and baseline fields stay `null`.

## 4. Open questions, with defaults

1. **Dependencies.** `harmonize.py` imports NumPy, pandas and (through `calibration.py`) PyArrow, which the API environment does not have. Default: add them to `api/pyproject.toml` and `api/requirements.txt` at the versions already approved in `docs/TECH_STACK.md` §7 (numpy 2.5.4, pandas 3.1.1, pyarrow 26.0.1), after checking they install on Python 3.14. No other package.
2. **Import path.** `pipeline/` is not a package and `harmonize.py` does `import calibration`. Default: `custom.py` adds the repository's `pipeline/` directory (found from the file's own location) to `sys.path` and imports `harmonize`, with no change to `pipeline/`.
3. **Where it reads and writes.** `harmonize_area()` defaults to `data/products` and writes DuckDB spill files to `data/interim/_duckdb_tmp`. Default: pass `Paths(products=PRODUCTS_DIR, tmp=<system temp dir>)` so the API honours `PRODUCTS_DIR` and writes nothing into the repository.
4. **Call.** `harmonize_area(cell_ids, months=None)` for every month, no `aqua_cutoff` (the value comes from T-012), default `phi`/`kappa`, `entity_id="CUSTOM"`. The returned records are validated by the existing `EntityMonth` model and not altered.
5. **Large areas.** Default: measure first (a country-sized box and the whole world) and report; add a size limit or a cache only if the numbers need it, and ask before choosing the limit.
6. **Tests without the files.** Default: real-product tests are skipped with a clear reason when `data/products/*.parquet` are LFS pointers, so a clone without `git lfs pull` still passes.

## 5. Acceptance

- A rectangle over a real country returns series records that validate against the contract, with `entity_type = CUSTOM` and null verdict and baseline fields.
- The cell counts match `cells_with_centre_in`; the empty-area `422`, invalid-bbox `422` and the export `400`s are unchanged.
- ruff, pytest and the app checks pass; real numbers (response time, row counts) go in the PR description.
