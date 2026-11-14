# Task prompt: T-043 Static fallback build (optional deploy)

> Prepared for: Member 3 · Date: 2026-11-15 · Based on main @ 9367b68
> Source of truth: docs/TASK_TRACKER.md row T-043 ("Preset views work without the API"), the Lead's assignment in PR #38 ("static fallback for preset views; deploy is optional"), `docs/prompts/MEMBER_3_APPLICATION_PROMPT.md` §16 ("export the preset views (`/api/meta`, entities, every month of `/api/map`, series for countries, continents and global, `/api/validation`) as static JSON. The app must work from these files when no API is running, with custom areas disabled and a clear message"), `docs/ARCHITECTURE.md` ("Static export: pre-render API responses for preset views, `public/data/*.json`"). This prompt adds no scope beyond them. The Lead marks the tracker row.

## 1. Objective

A build of the app that shows the preset views (map, calendar, evidence, witness chart, anomaly list, methods page) from static JSON files, with no API running. Custom areas and the CSV download need the API and say so clearly. The static files are generated from the same API code and the same products, so they cannot disagree with it, and they carry the same `synthetic` flag.

## 2. Measured sizes (local, real products, 2026-11-15) that shape the design

- Entity series: 233 presets (226 countries, 7 continents) plus the world. About 166 KB raw and 4.3 KB gzipped each; about 39 MB raw and about 1 MB gzipped in all.
- The API's map response for one month: 28.7 MB raw and 645 KB gzipped (all contract fields for 56,238 cells). Every month would be about 8.4 GB raw and about 190 MB gzipped (293 months, 2002-07 to 2026-11): too large to publish.
- A compact form of the same month (one number per cell, in the order of one shared cell list): 184 KB raw and 34 KB gzipped; about 54 MB raw and about 10 MB gzipped for every month. The cell list (ids and bounds) is written once: 2.7 MB raw and 332 KB gzipped.
- `GET /api/anomalies` for a month is a few entries in raw-only data.

## 3. In scope

- **Export script** (in `api/`, using the real endpoint code in-process, so the files are the API's own answers): writes `meta.json`, `validation.json`, `entities-COUNTRY.json`, `entities-CONTINENT.json`, one series file per country, continent and the world, one anomalies file per month, and the map files (open question 1) under an output directory (default `app/public/data/`, ignored by Git).
- **App data layer**: one place that decides where data come from (the API, or the static files), used by the existing queries; the app keeps working unchanged when the API is up. Static mode shows a visible note ("Static copy of the preset views; custom areas and CSV download need the live service"), disables custom areas and the CSV button with that reason, and keeps the SYNTHETIC banner if the files say `synthetic`.
- Tests (SYNTHETIC data only in test files; the export script is also run on the fixtures and on the real products).
- `app/README.md`, `api/README.md`, `docs/RISKS_AND_LIMITATIONS.md` (what the static copy is and is not).

## 4. Out of scope

- Changes in `pipeline/`, `data/` or the contract; the live API stays as it is.
- Deploying (open question 6).
- A polygon area (T-044) and anything that needs the live `harmonize_area()`.

## 5. Open questions, with defaults

1. **Map files.** Publishing the API's full map response for every month is about 190 MB gzipped. Default: the static map uses the compact form of section 2 (one shared `cells.json` with ids and bounds, then per month a file with the numbers the map shows: `raw_combined_cell_days`, `estimate` and the verdict code, `data_level`), and the app rebuilds the same `MapCell` objects from them, so the map code is unchanged. Nothing is computed: it is the same stored values in a smaller layout. It is a static-only file format, not an API or contract change. Is a compact static layout acceptable, or should the static copy contain only the latest N months of the full response?
2. **Where the script lives and how it runs.** Default: `api/fire_api/static_export.py`, run as `python -m fire_api.static_export --out ../app/public/data` with `PRODUCTS_DIR` set; it calls the endpoint functions through the FastAPI test client, so there is one implementation.
3. **Files in Git.** Default: never committed (generated, about 10 to 50 MB); `app/public/data/` is ignored and the README says how to generate it.
4. **How the app chooses.** Default: a build-time switch `VITE_STATIC_ONLY=1` for a static-only deployment (no API calls at all), and a runtime fallback in the normal build: if `/api/meta` cannot be reached, the app switches to the static files when they exist and says so.
5. **Evidence, anomalies, CSV in static mode.** Default: evidence is the selected month's record of the static series; the anomaly list comes from the per-month static files (the API's ranking, not recomputed); the CSV download is disabled with the reason, because the file needs the API's export code.
6. **Deploy.** Optional per the tracker. Default: no deployment in this PR; the README documents how to publish `app/dist` with `public/data` on any static host. I will not deploy or publish anything without the Lead's explicit go-ahead and the host named.
7. **Real and synthetic.** Default: the export reads one products directory and writes its `synthetic` flag through unchanged; real and fixture exports are never mixed in one output directory (the script refuses a non-empty output directory unless told to overwrite).

## 6. Acceptance

- With the API stopped, the static build shows the map, calendar, evidence, witness chart, anomaly list and methods page for the preset views on the real products, with the note, and custom areas and CSV disabled with a reason; with the API running, the normal build behaves as before.
- Each static file equals the API's answer for the same request (a test compares them on the fixtures).
- The total size of the real export is reported (raw and gzipped), with the generation time.
- Lint, typecheck, tests and build pass; screenshots of the static mode and of the disabled states go with the PR.
