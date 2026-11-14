# Technology Stack: **PROPOSED (awaiting Project Lead approval)**

> **Status:** Recommendation only. Nothing has been installed or scaffolded.
> When the Project Lead approves (or amends) this, record the decision as D-008 in `DECISION_LOG.md` and change this header to **APPROVED**.

## 1. Requirements driving the choice

1. **About 36 hours, two separate implementation workstreams** (data/science in Python; app/UI). We need few moving parts and a contract-first hand-off.
2. **Global data volume [VERIFIED 2026-11-14]:**
   - 9.1 GB zipped, roughly 41 GB of CSV unzipped **[ESTIMATE]**, from 4.5× expansion measured on the 2020 archives.
   - Roughly 475 million detections **[ESTIMATE]**, from line length.
   - This must be aggregated on a laptop, so we need out-of-core processing.
3. **Small products, heavy precompute.** The app serves precomputed monthly grids and series. The only on-demand computation is custom-area aggregation.
4. **One implementation of the science.** Custom-area harmonization must use the *same* code as the batch pipeline. That argues for the API being in Python.
5. **Smooth rendering of tens of thousands of grid cells** worldwide, plus calendar heatmaps and line charts with uncertainty bands.
6. **No paid services.** The demo must work offline or locally, because the recorded video is the main judged artifact **[ASSUMPTION; check the 2026 judging guide]**.

## 2. Recommended stack at a glance

| Layer | Recommendation | Version at time of writing **[VERIFIED from registries 2026-11-14]** |
|---|---|---|
| Data processing | **Python + DuckDB** (SQL, out-of-core CSV→Parquet) | Python 3.12–3.14 (local: 3.14.5); duckdb 2.0.0 (abi3 wheels for cp312+) |
| Scientific computing | **NumPy, SciPy, pandas** (small aggregated tables), optional **statsmodels** | numpy 2.5.4, scipy 1.18.1, pandas 3.1.1, statsmodels 0.15.0 |
| Geospatial (one-off) | **GeoPandas + Shapely + pyogrio** for country polygons and cell attributes | geopandas 1.2.0, shapely 2.2.0, pyogrio 0.13.0 |
| Storage | **Parquet files** (pyarrow) as the data products; **no database server** | pyarrow 26.0.1 |
| API | **FastAPI + Uvicorn**, querying Parquet with DuckDB; **Pydantic** models = data contract | fastapi 0.162.7, uvicorn 0.54.0, pydantic 2.14.3 |
| HTTP client (FIRMS API) | **httpx** | 0.28.1 |
| Frontend | **React + Vite + TypeScript** (SPA) | react 19.3.1, vite 8.3.8; TypeScript at the version the Vite template pins |
| Map | **MapLibre GL JS + deck.gl** (grid layers); **Natural Earth** country boundaries; optional free basemap | maplibre-gl 6.18.0, deck.gl 9.4.1 |
| Custom-area drawing | **terra-draw** (rectangle in the MVP, polygon in P1) | 1.39.0 |
| Charts | **Apache ECharts** (calendar heatmap, line + uncertainty band) | echarts 6.1.0 |
| Data fetching | **TanStack Query** | 5.107.1 |
| Tests | **pytest** (science and contract), **ruff** (lint); **Vitest** (minimal UI tests) | pytest 9.2.0, ruff 0.17.5, vitest 5.1.0 (needs Node ≥22.12) |
| Node.js | **22 LTS or 24 LTS.** Local Node 20.20.2 is past end-of-life (April 2026) and too old for Vitest 5 | — |
| Python environment | **venv + pip with a pinned `requirements.txt`** (no extra tool to install). `uv` is optional | — |
| Collaboration | GitHub (private), feature branches + PRs, Lead reviews | — |
| Demo / deploy | **Local-first demo + recorded video.** Optional: frontend on a free static host, API on a free container host | — |

Versions are the latest on npm or PyPI as of 2026-11-14. Pin exact versions in lockfiles at setup time.

## 3. Area-by-area comparison

### 3.1 Scientific data processing

| | **DuckDB (recommended)** | Polars | pandas only |
|---|---|---|---|
| Advantages | Out-of-core SQL over CSV/Parquet; parallel; writes Parquet; the same engine is reused in the API; SQL is reviewable by the Lead | Very fast lazy/streaming DataFrame API; good Python ergonomics | Familiar to everyone |
| Disadvantages | SQL plus Python split; Python wheel is abi3 for cp312+ (fine on 3.14) | Streaming engine edge cases on very large joins; a second engine if the API uses DuckDB | **Cannot hold ~475M rows in memory**; slow |
| Learning curve | Low (SQL) | Medium | Low |
| Integration | Same engine in the pipeline and API | Separate from the API | — |
| Cost | Free | Free | Free |
| Fit | Best for "one big aggregation, then small tables" | Good alternative if Member 2 prefers DataFrames | Only for small post-aggregation tables |

pandas, NumPy and SciPy are used only *after* aggregation, when tables are small (cells × months).

### 3.2 Storage and database

| | **Parquet files + DuckDB (recommended)** | PostgreSQL + PostGIS | SQLite / SpatiaLite |
|---|---|---|---|
| Advantages | No server; files are the contract; columnar and compressed; easy to version and ship | Powerful spatial SQL; production-grade | Single file, simple |
| Disadvantages | Not suited to concurrent writes (we don't need them) | Server setup, hosting and migrations: hours we don't have | Slow for large analytic scans; weak columnar performance |
| Learning curve | Low | Medium–high | Low |
| Cost | Free | Free locally; hosted free tiers are limited | Free |
| Fit | Products are write-once, read-many | Overkill for the hackathon | Viable for small metadata only |

### 3.3 Backend / API

| | **FastAPI + DuckDB (recommended)** | No backend (static files + DuckDB-WASM in the browser) | Flask |
|---|---|---|---|
| Advantages | Python, so it **reuses Member 2's harmonization functions** for custom areas; Pydantic models enforce the contract; auto-generated OpenAPI docs | Simplest hosting; no server | Simple, familiar |
| Disadvantages | A process must run (local, or a free container host with cold starts) | Custom-area harmonization would need the science **re-implemented in JS**, or the per-cell math pushed into the browser; second implementation, divergence risk | No built-in validation/OpenAPI; more glue |
| Learning curve | Low–medium | Medium (WASM, range requests, CORS-capable hosting) | Low |
| Cost | Free locally | Free | Free |
| Fit | Best balance | Fallback for preset views only (see §4) | Acceptable, but FastAPI gives the contract for free |

### 3.4 Frontend framework

| | **React + Vite + TS (recommended)** | SvelteKit | Streamlit (Python-only) |
|---|---|---|---|
| Advantages | Largest ecosystem; first-class deck.gl/MapLibre/ECharts bindings; static build; fast dev server | Less boilerplate; fast | Member 2 could build the UI in Python; very fast for basic dashboards |
| Disadvantages | More boilerplate than Svelte | Smaller mapping/deck.gl ecosystem; fewer examples | Weak custom-area drawing, slow with tens of thousands of cells, limited polish |
| Learning curve | Low–medium if Member 3 knows React | Medium if new | Low |
| Cost | Free | Free | Free (Community Cloud hosting is public) |
| Fit | Best if Member 3 knows React | Choose only if Member 3 is a Svelte developer | **Emergency fallback** if Member 3 cannot use React |

Next.js was considered and rejected: server rendering adds complexity with no benefit for a data dashboard.

### 3.5 Mapping

| | **MapLibre GL JS + deck.gl (recommended)** | Leaflet | Mapbox GL JS |
|---|---|---|---|
| Advantages | Free, open-source, no token; WebGL; deck.gl renders 50k+ grid cells smoothly and handles picking/tooltips | Simplest API; huge plugin ecosystem | Polished; great docs |
| Disadvantages | Two libraries to integrate (the standard pattern, well documented) | Canvas/SVG rendering is slow for tens of thousands of polygons | Access token; usage-based pricing beyond the free tier |
| Learning curve | Medium | Low | Medium |
| Cost | Free | Free | Free tier, then paid |
| Fit | Global grids at interactive speed | Too slow for a global grid | Unnecessary vendor dependency |

**Basemap:** use Natural Earth admin-0 boundaries (public domain) drawn as our own vector layer on a plain background. That means no external tile dependency and full reliability. A free hosted basemap is optional polish; check its terms before use. CesiumJS (3D globe) was rejected as heavy, with no analytic benefit.

### 3.6 Charts

| | **ECharts (recommended)** | Observable Plot | Recharts |
|---|---|---|---|
| Advantages | Built-in heatmap/calendar; line + confidence-band patterns; good performance; rich tooltips | Very concise; excellent for cell heatmaps and bands | Idiomatic React |
| Disadvantages | Large bundle; imperative options object | Less interactive; manual tooltips | **No heatmap**; weaker for the calendar |
| Learning curve | Medium | Low–medium | Low |
| Fit | Covers the calendar, series and anomaly views with one library | Good alternative | Not suitable for the calendar |

### 3.7 Grid system (science-facing; see also D-009)

| | **Regular latitude/longitude grid (recommended)** | H3 hexagons | Equal-area grid (e.g. EASE) |
|---|---|---|---|
| Advantages | Standard in fire science (GFED, MODIS CMG); trivial to compute; cell areas known analytically; easy to explain | Near-equal area; attractive visuals; used by other teams | Equal area |
| Disadvantages | Cell area shrinks toward the poles, so we normalize by area | An extra library on both sides; harder to align with standard region masks | More complex; less familiar |
| Fit | Simplest and most defensible | Nice-to-have, not needed | Overkill |

### 3.8 Deployment and collaboration

| Option | Notes | Fit |
|---|---|---|
| **Local demo + recorded video (primary)** | Zero hosting risk | **Recommended primary** |
| Vercel (Hobby) or Netlify (free) for the static frontend | Free, non-commercial; works with private GitHub repos | Optional P1 |
| Hugging Face Spaces (Docker) or Render (free) for the API | Free tiers have cold starts and resource limits **[verify current limits]** | Optional P1 |
| GitHub Pages | **Not available for private repos on GitHub Free** (needs a paid plan) | Not suitable while private |
| GitHub Actions CI | Free minutes quota for private repos | Optional: one lint+test workflow added after approval |
| Branch protection | **Not available for private repos on GitHub Free**; "no direct pushes to `main`" is enforced by convention and review | Convention (see `CONTRIBUTING.md`) |

## 4. Integration plan

1. **The contract comes first.** `docs/DATA_CONTRACT.md` defines the Parquet and JSON products, plus API responses as Pydantic models.
2. Member 2 publishes **SYNTHETIC fixtures** (small, labelled, committed) by about H3, so Member 3 can build the whole UI before the real data exists.
3. Member 2's science lives in an importable Python package. The API imports its `harmonize_area()` function, so there is **one implementation**.
4. **Static fallback.** For the global map months, countries, continents and validation results, the API's responses are also exported as static JSON files. The frontend works without a running API for everything except custom areas.

## 5. Estimated implementation complexity

| Component | Owner | Complexity | Rough effort |
|---|---|---|---|
| Download + normalize + grid (global) | M2 | M–L | 6–8 h (mostly machine time) |
| Calibration + pooling + holdout | M2 | L | 5–6 h |
| Combination + verdicts + entity aggregation | M2 | M | 4 h |
| Validation suite | M2 (Lead reviews) | M | 4 h |
| API (6–8 read endpoints + custom area) | M3 (or M2; see D-015) | S–M | 3 h |
| Map + layers + area selection | M3 | M | 6 h |
| Calendar + witness chart + evidence panel | M3 | M | 6 h |
| Anomaly list + export + methods page | M3 | S | 3 h |
| Integration + polish | M3 + M2 | M | 4 h |

These are planning estimates **[ESTIMATE]**, not measurements.

## 6. Version and compatibility notes

- **Python:** 3.12, 3.13 and 3.14 are supported by all listed packages (DuckDB via its cp312 abi3 wheel). Every team member should use the same minor version.
- **Node:** 22.12+ or 24 LTS is required (Vitest 5 needs ≥22.12; Vite 8 needs ≥20.19 or ≥22.12). Upgrade the local Node 20.20.2.
- **TypeScript:** 7.0 (the new native compiler) is very recent. Use whatever version the Vite template pins; don't force the newest.
- **deck.gl + MapLibre:** use the documented interleaved/overlay integration. Pin both versions together.

## 7. Final approved stack

*Not yet approved.* To be completed by the Project Lead (D-008).
