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
| `POST /api/series/custom` with `{"bbox": [W,S,E,N]}` or `{"polygon": [[lon,lat], ...]}` (exactly one) | `entity_month`-shaped records from `harmonize_area()` | 422, 503 |
| `POST /api/export.csv` with the same body | The monthly series of a custom rectangle or polygon as a CSV download (same file layout as the `GET`; the `#` header names the area `CUSTOM polygon (N points)` or `CUSTOM bbox W,S,E,N`; the file name is safe and prefixed `SYNTHETIC_` while the data are) | 422, 503 |
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
- Free polygons (T-044): `POST /api/series/custom` and `POST /api/export.csv` take either `{"bbox": [W,S,E,N]}` or `{"polygon": [[lon, lat], ...]}`, never both and never neither (`422`: "Give either bbox or polygon, not both and not neither."). The polygon is one outer ring; the first point is not repeated (the API closes it). **Which cells belong:** a grid cell belongs when its **centre** (`lon_c`, `lat_c` in `cells.parquet`) lies inside the polygon, the boundary included, by the even-odd (ray-casting) rule written in `fire_api/polygon.py` (plain Python with an exact-fraction fallback near edges; no geometry library). The polygon's bounding box is applied in SQL first, then the centres are tested in Python. Consequences: a cell the polygon covers 60% but whose centre is outside is left out, and a cell covered 40% whose centre is inside is included; a small polygon may contain no centre (`422` "No analysis cells have their centre inside this area.", the rectangle's message). **Limits (each a `422` with its own message):** 3 to 100 different points ("A polygon can have at most 100 corner points."; "A polygon needs at least 3 different corner points."); every coordinate finite and inside the world box (-180 <= lon <= 180, -90 <= lat <= 90); no repeated point, so the first point is not repeated at the end; non-zero area; no antimeridian crossing, defined as: no side may span more than 180 degrees of longitude and the bounding box needs west < east (as for the rectangle); no self-intersection: any two sides that meet other than consecutive sides at their shared corner (crossing, touching, repeated or collinear overlapping sides) are rejected. Two polygons (or a polygon and a rectangle) that select the same cells share one cached answer (same key as the rectangle). Not an API contract of the products; a request shape only.
- Custom-area response time (local machine, real products, 2026-11-14; the machine was shared, so repeat the measurement before quoting): first request, a country-sized box (bbox `-58.5,-35,-53,-30`, 107 cells) about 3.2 to 5 s, the whole world (56,238 cells) about 13 s; repeat of the same area 0.02 s (country) and 0.07 to 0.13 s (world, mostly hashing 56,238 cell ids). Where the first request goes: the DuckDB scan and aggregation of the 146.6 million-row `cell_month_witness` product (about 2.7 s for the box, 13 s for the world) and the pandas per-month record building in `harmonize_area()` (about 1.4 to 2 s, independent of size); importing `harmonize` (numpy, pandas) about 0.6 s once per process; pydantic validation and JSON are under 10 ms.
- Custom-area cache (`fire_api/custom.py`, per process, in memory): the validated list a request returns is kept in a bounded LRU of **32 entries** (a series is about 300 records, a few hundred kB). The key is: the resolved products directory, a SHA-256 digest and the count of the sorted distinct cell ids, the modified time (ns) and size of `cells.parquet`, `cell_month_witness.parquet` and `calibration.parquet` (the three files `harmonize_area()` reads), and `harmonize.METHOD_VERSION` read on each call. A replaced or touched product, a different cell set or a new method version therefore never serves an old answer; the old entry just ages out. Only successful results are stored (a 503, a missing product or a contract violation is recomputed on the next call); concurrent identical requests compute once; the CSV export shares the cache. The cache is not shared between worker processes and is empty after a restart (each worker pays the first request once). If a product file cannot be inspected the call is not cached. Not part of the key: `harmonize` constants (`PHI`, `KAPPA`, `AQUA_FROM`) that change without a `METHOD_VERSION` change; restart the server after such an edit.
- Compression: responses of 1000 bytes or more are gzip-compressed (`GZipMiddleware`, level 6) when the client sends `Accept-Encoding: gzip`. Map month 2026-10 (56,238 cells), `layer=raw` or `layer=verdict`: 28.7 MB plain, 0.66 MB gzipped (0.61 MB at level 9), about 1.0 s total either way on localhost (compression costs about 0.13 s; on a real network the transfer saved is far larger).
- `null` is returned as `null` and a real zero as `0`. A stored value that violates the contract (for example an unknown verdict) is reported as `503`, never coerced.
- There is no CORS configuration. In development, the web app proxies `/api` to this server (Vite dev proxy).

## Static export (offline copy, T-043)

`fire_api/static_export.py` writes the preset views as static JSON, so the app can run with no API:

```bash
cd api
PRODUCTS_DIR=../data/products .venv/bin/python -m fire_api.static_export --out ../app/public/data
```

Every file is the API's own answer: the endpoints are called in-process through the FastAPI test client, so there is one implementation and nothing is computed. It writes `meta.json`, `validation.json`, `entities-COUNTRY.json`, `entities-CONTINENT.json`, `series/<TYPE>-<ID>.json` for every country, continent and the world, `anomalies/<YYYY-MM>.json` and `map/<YYYY-MM>.json` for every month, the CSV of every preset area under `export/` (made with the real export code, with the file names it chose), a shared `cells.json` and a `manifest.json` (export time, `synthetic`, versions, data snapshot, months, file names).

- **The map files are columnar.** The API's full map response is about 28 MB for a month; a month file holds one column per field (a column that is the same everywhere is stored once, a repeated value through a small table), and the cell ids and bounds are written once in `cells.json`. Decoding gives back exactly the API's records (tested for several months, including an outage, a witness-disagreement, a MIXED and an NRT month).
- **Two copies, two commands** (the Lead's decision on #53; sizes measured on the real T-014 products, 293 months, 2002-07 to 2026-11):
  - **Demo laptop: the full copy** (every month, full fields), made on the demo machine. About 1,650 MB raw, **474 MB gzipped** (map months 462 MB, everything else 11.5 MB), about 17 minutes. It is a local folder, never uploaded.
    ```bash
    PRODUCTS_DIR=../data/products .venv/bin/python -m fire_api.static_export --out ../app/public/data --overwrite
    ```
  - **A web host: the 24-month copy**, with the map for the latest 24 months only (the calendar, series, evidence and CSVs stay complete for every month). **225 MB raw, 55.3 MB gzipped** (map 43.7 MB, series 5.8 MB, CSVs 5.0 MB, the rest 0.8 MB: the anomaly list of every month is always included), generated in 85 s on a quiet machine.
    ```bash
    PRODUCTS_DIR=../data/products .venv/bin/python -m fire_api.static_export --out ../app/public/data --latest-months 24 --overwrite
    ```
  Stored values are never rounded or dropped to make a copy smaller. The app reads the months that have a map from the manifest (see `app/README.md`).
- **One products directory per export.** The `synthetic` flag is passed through. A non-empty output directory is refused unless `--overwrite` is given, and then only a directory that holds this script's `manifest.json` is cleared. `--latest-months N` makes a quick partial copy.
- **Not committed.** `app/public/data/` is ignored; regenerate it. Sizes and generation time of the real export are in the T-043 pull request.

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
