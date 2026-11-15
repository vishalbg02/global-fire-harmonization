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

The address bar always holds the selection, so a link reproduces the view. Query parameters (all optional, defaults left out): `area` (`COUNTRY:IDN`, `CONTINENT:AS`, `GLOBAL`, `CUSTOM:west,south,east,north`, or `POLY:lon,lat;lon,lat;...`), `month` (`2015-09`), `source` (`raw` or `harmonized`), `map` (`verdict` or `activity`) and `value` (`pct` or `activity`). Unknown or malformed values are ignored. Raw with % of normal, or raw with the verdict map, cannot be selected together.

**Map experience (T-071).** *Opening month:* with no `month` in the link, the app opens on the latest month of the world series (`GET /api/series?entity_type=GLOBAL&entity_id=GLOBAL`) whose record has an estimate and no `OUTAGE` reason code (`state/initialMonth.ts`), or on the latest month if none qualifies; on the real products that is 2026-10, not the all-grey 2026-11. *Scrolling:* MapLibre cooperative gestures, so the page scrolls over the map; zoom with Ctrl or Cmd + scroll, the +/- buttons or the keyboard, and two fingers move the map on touch; a hint sits on the map. *Legend:* on the map at the bottom left (collapsible, collapsed on narrow maps). *Outlines:* the cell stroke is thin and light (alpha 35), none below zoom 3 and growing to 1 px; the selected cell keeps its blue outline and "no data" its dark one. *Colour:* "No detected activity" is a pale sand (`[245, 225, 185]`, quiet on purpose: it covers about 65% of the land) with the open circle icon. *Loading:* a status pill on the map while the month's cells load. *Pinned card:* clicking a cell opens a card on the map with the cell details and the full reason sentences; it stays until it is closed (button or Esc), another cell is clicked or the selection moves elsewhere; the hover tooltip stays for quick reading.

## Methods and validation page (T-041)

A "Methods and validation" link in the header opens a page (`?page=methods`, kept in the link; no router library). It holds the method in plain language (`src/content/methods.ts`, drafted from the approved decisions and `docs/DATA_SOURCES.md`, each statement labelled APPROVED, PROPOSED, VERIFIED, LIMITATION, OPEN or NOT_BUILT_YET, with its source), what each verdict and reason code means (from the approved reason texts), the D-009 grid evidence, the validation results exactly as `GET /api/validation` serves them, a separate "Planned tests (not run yet)" list that has no status and is never part of the results, and the FIRMS acknowledgement (from `/api/meta`), the seven dataset DOIs and the references. Results are shown in file order, each status as text plus an icon; FAIL and INCONCLUSIVE are drawn with a heavier border than PASS; an empty list says no test has been run yet. Each reason code in the evidence panel links to its entry on the page.

## Performance and accessibility (T-042)

- **Code splitting:** the map (MapLibre, deck.gl, the draw tool) and the two charts (ECharts) load when first needed. The first-load chunk went from 2,816.61 kB (about 794 kB gzipped) to 314 kB (about 92 kB gzipped). Every chunk is under 500 kB except `maplibre-gl` (1.06 MB, one library) and its own worker (519 kB), which load only with the map; the build warning limit is set to 1,100 kB for that reason (`vite.config.ts`).
- **Keyboard:** a skip link goes to the controls; focus is visible; the map canvas has a name and takes the arrow keys to pan and plus and minus to zoom. MapLibre has no cell-by-cell keyboard selection, so the keyboard routes to a place are the country search, the typed custom box, the calendar table view and the anomaly list. This is a known limit, not built here.
- **Colour vision:** `src/content/colorVision.ts` simulates protanopia, deuteranopia and tritanopia (Machado, Oliveira and Fernandes 2009) and its tests check every ramp and colour set (threshold CIEDE2000 10, chosen for this project, not a standard). The raw-combined line is near black because it was too close to the baseline grey. Pairs that still fall below the threshold are pinned in the tests with the cue that separates them (icon, dash pattern or width).
- **Contrast:** `src/content/contrast.test.ts` reads the tokens in `src/index.css` and checks WCAG 2.1 AA text contrast. The app has one (light) theme.
- **Loading:** a custom area shows "Computing this area… A new area can take several seconds." while it computes.

## Offline copy of the preset views (T-043)

The app can run from static files written by `api/fire_api/static_export.py` (see `api/README.md`), with no API:

- **Static-only build** (no API calls at all): `VITE_STATIC_ONLY=1 npm run build`, with the files in `public/data/` (the build copies them into `dist/data/`).
- **Runtime fallback** in the normal build: if the API cannot be reached and a copy exists, the app switches to it. An answer of the API (404, 422, 503) is never replaced by the copy.
- In both cases a notice says "Offline copy" with the date it was made and the data snapshot. The map, calendar, evidence, witness chart, anomaly list and the CSV of every preset area work; custom areas (typed or drawn) and the CSV of a box are disabled with "Custom areas need the live service. This offline copy has the preset views only."
- **Which copy:** the full copy (all months, about 474 MB gzipped) is for the demo laptop, generated on that machine; the 24-month copy (`--latest-months 24`, measured 55.3 MB gzipped, 225 MB raw) is for any web host. The two commands are in `api/README.md`. In a 24-month copy the month slider and the map month picker list only the months that have a map (the manifest's list), a month chosen in the calendar that has no map says "No offline map for this month", and a note reads "Offline copy: map available for <first>–<last>; the calendar and charts cover every month." The calendar, series, evidence and CSVs cover every month in both.
- The files are generated, never committed (`public/data/` is ignored). Publishing them is documented, not done: serve `dist/` with its `data/` folder from any static host (nothing is deployed from this repository without the Lead's go-ahead and a named host).
- `src/api/staticData.ts` reads the files and decodes the columnar map months; `src/api/client.ts` chooses between the API and the copy in one place (`route`).

## Raw-only data

When `metadata.method_version` ends in `-raw-only` (real raw counts, no harmonization yet, T-039 phase 1) the app shows a "Raw data only, harmonization in progress" note, forces the raw / activity views, disables Harmonized, Verdict and % of normal with the reason written out, and shows "Not available yet" in the evidence panel, the anomaly list and the chart. The raw-only note and the per-area wording are decided per series from its records (`method_version` ending in `-raw-only`, or the `NOT_HARMONIZED` reason code), not from the global metadata: a preset area is raw-only for now, while a custom-area series from `harmonize_area()` is shown with its harmonized estimate and interval and no raw-only note (its `% of normal` stays unavailable until a baseline exists, T-014). The map controls still follow the metadata, because the map products are raw-only. The SYNTHETIC banner follows `metadata.synthetic` only. Real products are never mixed with fixtures.

## Custom areas

A custom rectangle is sent to `POST /api/series/custom`; the API returns the series, and the calendar and evidence panel show it. The API computes it with Member 2's `harmonize_area()` (verdict and baseline fields are empty until T-014); a country-sized box takes about 3 s on a local machine, the whole world about 13 s. If the function or the products are unavailable, the API answers `503` and the app shows that message. Boxes must have west less than east (boxes that cross the antimeridian are not supported) and south less than north. A rectangle can also be drawn on the map with two clicks (terra-draw with `terra-draw-maplibre-gl-adapter`, D-024); drawing needs a pointer, so the typed fields are the keyboard route.

**Free polygon (T-044).** Under the rectangle fields, "Custom polygon" offers two routes. *Typed (keyboard and screen reader):* a text box with one `longitude, latitude` per line (comma and/or spaces; blank lines ignored; rounded to 4 decimals) and "Show polygon". *Drawn:* "Draw a polygon on the map" (terra-draw `TerraDrawPolygonMode`): one click per corner, finish with a double-click or Enter, Escape drops the polygon in progress, the button again leaves drawing. A drawn polygon fills the text box. Both routes go through the same check as the API (3 to 100 different points, inside the world box, first point not repeated, non-zero area, no side spanning more than 180 degrees of longitude, no self-intersection) with the API's messages, and the server's own message is shown too. The polygon is outlined on the map and announced as "Custom polygon, N corner points, M grid cells" (`role="status"`; M is `n_cells` of its series). Next to the polygon the app states the rule: a grid cell belongs when its centre lies inside the polygon; a cell covered 60% whose centre is outside is left out; a tiny polygon may contain no cell centre ("No analysis cells have their centre inside this area."). The CSV button uses `POST /api/export.csv` for a polygon. In the offline copy the polygon controls and its CSV are disabled with the rectangle's message. Link format: `area=POLY:lon,lat;lon,lat;...` (4 decimals, first point not repeated); a malformed, over-limit or invalid polygon in a link is ignored and the world is shown.

## Configuration

- `VITE_API_BASE_URL`: base URL of the API (for example `http://localhost:8000`). Optional; it holds no secret. Without a reachable API the map still shows the country layer and reports that data are not available. Contract v0.1.0 defines no response envelope, so the client expects the bare payload of `GET /api/meta` and `GET /api/map`.
- `VITE_STATIC_ONLY`: set to `1` to build for a deployment with no API (the app reads the static files in `public/data/` only; see "Offline copy" above). Build-time, no secret.

## Country boundaries

`public/geo/ne_admin_0_countries_india_pov.geojson` is Natural Earth admin-0 countries, India point of view (1:10m source `ne_10m_admin_0_countries_ind.geojson`, public domain), simplified to 837,805 bytes and 243 features so India's official boundary (Jammu and Kashmir, Ladakh, Aksai Chin) is drawn inside India (T-085). Source, SHA-256 and processing are in `docs/DATA_SOURCES.md`. The app takes each country's ISO 3166-1 alpha-3 code from `ISO_A3_EH`, because `ISO_A3` is `-99` for Norway and France. Six polygons (Dhekelia, Akrotiri, Guantanamo Bay, Bir Tawil, Spratly Islands, Scarborough Reef) have no ISO code; they are drawn but cannot be selected, and no code is invented for them. In this view Western Sahara, Kosovo, Northern Cyprus and Somaliland are part of Morocco, Serbia, Cyprus and Somalia.

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
