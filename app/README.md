# Web app (`app/`)

Frontend for the Global Fire Harmonization project (working name: *Many Witnesses*). Owner: Member 3. Task: T-030 (setup and skeleton).

**Status:** the global map (T-031) and the historical calendar (T-032: years by months, % of normal or activity, with a table view) are built. A shared Raw / Harmonized control (T-033) switches the map and the calendar between the stored raw count and the harmonized estimate on one colour scale. An evidence panel (T-036) explains the verdict for the selected area and month, or for a selected map cell, in plain language. The area picker (T-035) chooses the world, a country, a continent or a custom rectangle (typed, or drawn on the map), and the selection is kept in the link. The witness comparison chart (T-037) shows the area's whole monthly history: the harmonized line and its band, the baseline band and median, the raw combined line, a line per satellite, a static satellite timeline, and outage/drift/provisional marks, with an accessible table view. A CSV download (T-038) in the area picker saves the shown area's monthly series from `GET /api/export.csv`. A global anomaly overview (T-040) ranks, for the selected month, the countries (or continents) that are most likely above and most likely below normal, outlines the listed countries on the map, and selects an area when its entry is clicked. The app will talk only to the API or the static JSON export, never to Parquet files directly (`docs/ARCHITECTURE.md`).

## Prerequisites

- Node.js 22.12+ or 24 LTS (`docs/TECH_STACK.md` §7). Node 20 is end-of-life and too old for Vitest 5.
- npm (installed with Node).

## Commands

Run all commands from this `app/` directory.

| Command | What it does |
|---|---|
| `npm ci` | Install the exact versions from `package-lock.json` |
| `npm run dev` | Start the dev server (Vite prints the local URL) |
| `npm run build` | Type-check (strict TypeScript), then build to `dist/` |
| `npm run typecheck` | Type-check only |
| `npm test` | Run the Vitest tests once |
| `npm run lint` | Run the template's default linter (Oxlint) |
| `npm run preview` | Serve the built `dist/` locally |

## Running against the API

The web app reads data from the API in `api/` (see `api/README.md`). In development, Vite proxies `/api` to `http://127.0.0.1:8000`, so no CORS configuration is needed and `VITE_API_BASE_URL` can stay empty. With the SYNTHETIC fixtures:

```bash
cd ../api && PRODUCTS_DIR=../data/fixtures/v0.1.0 .venv/bin/uvicorn fire_api.main:app --port 8000
```

```bash
npm run dev
```

Open the address Vite prints (use `localhost`). While `metadata.synthetic` is `true` the app shows the "SYNTHETIC DATA" banner. Without a running API the country layer still works and the other views report that data are not available.

## Links

The address bar always holds the selection, so a link reproduces the view. Query parameters (all optional, defaults left out): `area` (`COUNTRY:IDN`, `CONTINENT:AS`, `GLOBAL`, or `CUSTOM:west,south,east,north`), `month` (`2015-09`), `source` (`raw` or `harmonized`), `map` (`verdict` or `activity`) and `value` (`pct` or `activity`). Unknown or malformed values are ignored. Raw with % of normal, or raw with the verdict map, cannot be selected together.

## Raw-only data

When `metadata.method_version` ends in `-raw-only` (real raw counts, no harmonization yet, T-039 phase 1) the app shows a "Raw data only, harmonization in progress" note, forces the raw / activity views, disables Harmonized, Verdict and % of normal with the reason written out, and shows "Not available yet" in the evidence panel, the anomaly list and the chart. The SYNTHETIC banner follows `metadata.synthetic` only. Real products are never mixed with fixtures.

## Custom areas

A custom rectangle is sent to `POST /api/series/custom`; the API returns the series, and the calendar and evidence panel show it. Until Member 2's `harmonize_area()` is delivered, the API answers `503` and the app shows that message. Boxes must have west less than east (boxes that cross the antimeridian are not supported) and south less than north. A rectangle can also be drawn on the map with two clicks (terra-draw with `terra-draw-maplibre-gl-adapter`, D-024); drawing needs a pointer, so the typed fields are the keyboard route.

## Configuration

- `VITE_API_BASE_URL`: base URL of the API (for example `http://localhost:8000`). Optional; it holds no secret. Without a reachable API the map still shows the country layer and reports that data are not available. Contract v0.1.0 defines no response envelope, so the client expects the bare payload of `GET /api/meta` and `GET /api/map`.

## Country boundaries

`public/geo/ne_110m_admin_0_countries.geojson` is Natural Earth admin-0 countries at 1:110m (public domain), file `geojson/ne_110m_admin_0_countries.geojson` from the `nvkelso/natural-earth-vector` repository at tag `v5.1.2`, 838,726 bytes, 177 features, unmodified. The app takes each country's ISO 3166-1 alpha-3 code from `ISO_A3_EH`, because `ISO_A3` is `-99` for Norway and France. Three features (Northern Cyprus, Somaliland, Kosovo) have no ISO code in this file; they are drawn but cannot be selected, and no code is invented for them.

## Stack (approved, D-008)

React 19, Vite 8, TypeScript (strict), MapLibre GL JS 6, deck.gl 9 (installed as the individual modules `@deck.gl/core`, `@deck.gl/layers`, `@deck.gl/react` and `@deck.gl/maplibre`, not the `deck.gl` meta-package, which pulls in unused ArcGIS and Vaadin packages), terra-draw, Apache ECharts 6, TanStack Query, Vitest. The map, drawing and chart libraries are installed but not used yet. Exact versions are pinned in `package-lock.json`.

## Folder map

```
app/
├── index.html              page entry
├── src/
│   ├── main.tsx            app root; mounts the TanStack Query provider
│   ├── App.tsx             map page: wires selection, data queries and components
│   ├── index.css           styles and visible focus
│   ├── api/                contract types and parsers (contract.ts), typed client (client.ts)
│   ├── state/              selection state (selection.ts), month list (months.ts)
│   ├── content/            verdict presentation, reason texts (approved), witness names, wording
│   ├── components/map/     map, legend, month and layer selectors, tooltip, colour scale
│   ├── components/calendar/ calendar grid, ECharts heatmap, table view, legend, scales, tooltip text
│   ├── components/evidence/ evidence panel: verdict, numbers, satellites, raw contributions, reasons
│   ├── components/area/    area picker, custom-area form, country search, shared series query
│   ├── components/witness/ witness comparison chart, satellite timeline, table view, outage/drift marking
│   ├── components/export/  Download CSV button (T-038): request, file name, error states
│   ├── components/anomalies/ anomaly overview: two rankings, Countries/Continents tabs, ranking logic
│   ├── state/              selection, months, box checks (bbox.ts), link encoding (urlState.ts)
│   ├── components/common/  synthetic banner, loading/error/empty states, error boundary, Raw / Harmonized control
│   └── **/*.test.ts(x)     Vitest tests (mock data inside test files is SYNTHETIC)
├── public/geo/             Natural Earth country boundaries
└── package.json            scripts and dependencies
```

Folders for later views are added when the task that needs them starts.

## Pointer for the root README (proposed, awaiting Lead approval)

The root `README.md` "Setup" section is not edited in this task. Proposed line for it:

> Web app: see [`app/README.md`](app/README.md) for install, run, build and test commands.

## Rules for this folder

- Components consume only the documented data contract (`docs/DATA_CONTRACT.md`).
- No science in the app: no conversions, baselines, probabilities or verdicts.
- Never commit `node_modules/`, `dist/`, secrets or data products.
