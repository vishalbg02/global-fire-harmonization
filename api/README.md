# API (`api/`)

Read-only FastAPI service for the Global Fire Harmonization project. It serves the contract v0.1.0 products (`docs/DATA_CONTRACT.md`) from Parquet and JSON files with DuckDB. Owner: Member 3 (D-015). Task: T-034.

**The API computes no science.** It selects, filters, joins and orders stored values. Conversions, baselines, probabilities and verdicts come from Member 2's products, and custom areas go through Member 2's `harmonize_area()` from `pipeline/harmonize.py` (see below).

## Prerequisites

- Python 3.12 to 3.14 (`docs/TECH_STACK.md` section 7). Use an explicit version when creating the environment, for example `python3.14`, not a bare `python3`, which may be newer than the approved range.

## Setup

```bash
cd api
python3.14 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

`requirements.txt` pins every package, including the test tools. `pyproject.toml` lists the direct dependencies, pinned to the approved stack (D-008; NumPy, pandas and PyArrow are there for `harmonize_area()`), and the pytest and ruff settings.

## Run

```bash
PRODUCTS_DIR=../data/fixtures/v0.1.0 .venv/bin/uvicorn fire_api.main:app --port 8000
```

Interactive documentation is at `http://127.0.0.1:8000/docs`.

`PRODUCTS_DIR` is the folder holding the products, one file per product: `cells.parquet`, `cell_month_harmonized.parquet`, `entity_month.parquet`, `metadata.json`, `validation_results.json`. It defaults to `data/products` (the real products, which are not in Git). For development, point it at the SYNTHETIC fixtures, `data/fixtures/v0.1.0`. It is read on every request and holds no secret.

## Endpoints

Responses are bare payloads (no envelope). Errors use FastAPI's default body, `{"detail": ...}`. The D-022 envelope and error format are not approved, so they are not used.

| Endpoint | Returns | Errors |
|---|---|---|
| `GET /api/meta` | `metadata.json` | 503 |
| `GET /api/entities?type=COUNTRY\|CONTINENT` | `[{entity_type, entity_id, entity_name, bbox: [W,S,E,N]}]` | 400, 503 |
| `GET /api/map?year=&month=&layer=verdict\|raw\|harmonized` | One record per analysis cell: bounds plus the cell's `cell_month_harmonized` fields | 400, 503 |
| `GET /api/series?entity_type=COUNTRY\|CONTINENT\|GLOBAL&entity_id=` | `entity_month` records ordered by year, month | 400, 404, 503 |
| `POST /api/series/custom` with `{"bbox": [W,S,E,N]}` | `entity_month`-shaped records from `harmonize_area()` | 422, 503 |
| `GET /api/evidence?entity_type=&entity_id=&year=&month=` | One `entity_month` record with `raw_by_witness` decoded into an object | 400, 404, 503 |
| `GET /api/anomalies?year=&month=&limit=` | Entities with an `ABOVE_NORMAL` or `BELOW_NORMAL` verdict, ordered by the larger of `p_above` and `p_below`, descending (default limit 20, maximum 500) | 400, 503 |
| `GET /api/export.csv?entity_type=&entity_id=` or `?bbox=W,S,E,N` | The monthly series of one preset area, or of a custom rectangle, as a CSV download (UTF-8 with a byte-order mark; `#` metadata lines, then one row per month; all five `raw_<witness>` columns; empty cell = missing, never 0; `Content-Disposition` carries the file name, prefixed `SYNTHETIC_` while the data are) | 400 (neither or both of preset and `bbox`, malformed `bbox`), 404, 422, 503 |
| `GET /api/validation` | `validation_results.json`, served as is | 503 |

Raw-only products (T-039 phase 1): with `method_version` ending in `-raw-only`, every harmonized field is `null` and every verdict is `CANNOT_DETERMINE`; the API serves them as stored. A missing product file gives `503` "Data are not available right now", never a fixture fallback (tested in `tests/test_missing_products.py`). On the full real set a `GET /api/map` month takes about 0.6 s and 28 MB; the series, evidence and export endpoints take about 0.02 s.

Status codes: `400` invalid parameters, `404` unknown entity or month, `422` invalid custom area, `503` products or the harmonization function unavailable (or a stored product that does not match the contract).  A custom series or `bbox` export answers `503` only when `harmonize_area()` cannot be imported or the products cannot be read.

Notes on the choices the contract leaves open (all confirmed by the Lead on PR #16):

- `type` and `entity_type` use the contract's uppercase values.
- `bbox` in `/api/entities` is derived from the bounds of the cells assigned to each country or continent. An entity with no cells has no derivable bbox and is not listed.
- `layer` is validated but every layer returns the same fields; the web app chooses how to colour them.
- Custom areas select the analysis cells whose **centre** lies inside the box (box edges inclusive). The cells are passed to `harmonize_area(cell_ids, months)` with the module's defaults (no `aqua_cutoff`, `phi` or `kappa` is passed, so the API never drifts from the method). `fire_api/custom.py` puts the repository's `pipeline/` on `sys.path` (nothing in `pipeline/` changes), binds the function to `PRODUCTS_DIR` and writes DuckDB spill files to the system temporary directory, not into the repository. The records are validated by the `EntityMonth` model and not altered. Until T-014 the verdict fields are `null` and the verdict is `CANNOT_DETERMINE`.
- Custom-area response time (local machine, real products, 2026-11-14): a country-sized box (about 107 cells) 3.2 to 3.5 s; a box of about 4,700 cells 3.8 s; the whole world (56,238 cells) 12.9 s; a CSV of the country-sized box 4.2 s. The function scans the 146.6 million-row `cell_month_witness` product on every call; no cache or size limit is in place (to be decided with the Lead).
- `null` is returned as `null` and a real zero as `0`. A stored value that violates the contract (for example an unknown verdict) is reported as `503`, never coerced.
- There is no CORS configuration. In development, the web app proxies `/api` to this server (Vite dev proxy).

## Test and lint

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
```

The tests build tiny SYNTHETIC products inside the test files (`tests/conftest.py`) and also run against `data/fixtures/v0.1.0` when it is present. Those fixtures are SYNTHETIC: not NASA observations, not results.

## Layout

```
api/
├── fire_api/
│   ├── main.py       FastAPI app, routes and error handlers
│   ├── models.py     Pydantic models mirroring the contract
│   ├── products.py   DuckDB and JSON readers (no science)
│   └── custom.py     imports Member 2's harmonize_area() and binds it to PRODUCTS_DIR
├── tests/            pytest tests (SYNTHETIC data)
├── pyproject.toml    direct dependencies, pytest and ruff settings
└── requirements.txt  fully pinned environment
```
