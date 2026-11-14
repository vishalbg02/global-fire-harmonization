# Web app (`app/`)

Frontend for the Global Fire Harmonization project (working name: *Many Witnesses*). Owner: Member 3. Task: T-030 (setup and skeleton).

**Status:** the global map (T-031) and the historical calendar (T-032: years by months, % of normal or activity, with a table view) are built. A shared Raw / Harmonized control (T-033) switches the map and the calendar between the stored raw count and the harmonized estimate on one colour scale. An evidence panel (T-036) explains the verdict for the selected area and month, or for a selected map cell, in plain language. The witness charts are added by a later task. The app will talk only to the API or the static JSON export, never to Parquet files directly (`docs/ARCHITECTURE.md`).

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
