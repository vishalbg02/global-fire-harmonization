# Task prompt: T-084 Map: realistic Earth

> Prepared for: Member 3 · Date: 2026-11-15 · Based on main @ 6617331
> Source of truth: decision D-032 and the Lead's T-084 brief on PR #73 ("New from the Lead: realistic Earth and best experience"). Depends on T-070 and T-071 merging first. Display only: no product value, verdict rule, API shape or contract change. This prompt is written first; implementation waits for the Lead's answers to section 5.

## 1. Objective

The map looks like the real planet. A NASA GIBS Blue Marble shaded-relief and bathymetry basemap replaces the plain blue background; an off-by-default "Satellite view" shows Aqua MODIS true colour for a chosen day of the selected month, so that in Indonesia, September 2015, a judge sees the actual smoke behind the verdict cells. A Globe / Flat switch is added only if the deck.gl cells render correctly on the MapLibre globe. Cells stay readable over imagery. The offline copy falls back to the plain background with a note.

## 2. In scope

1. **Basemap.** GIBS `BlueMarble_ShadedRelief_Bathymetry`, EPSG:3857, `GoogleMapsCompatible_Level8`, fixed date 2004-08-01, as a MapLibre raster source below the cells and the country outlines. Pattern (HTTP 200 checked, see the PR): `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/BlueMarble_ShadedRelief_Bathymetry/default/2004-08-01/GoogleMapsCompatible_Level8/{z}/{y}/{x}.jpeg`.
2. **Satellite view (off by default).** A toggle that shows `MODIS_Aqua_CorrectedReflectance_TrueColor`, `GoogleMapsCompatible_Level9`, for one day of the selected month: `.../MODIS_Aqua_CorrectedReflectance_TrueColor/default/{YYYY-MM-DD}/GoogleMapsCompatible_Level9/{z}/{y}/{x}.jpg`. A day picker (default the 15th, clamped to the days of the month that exist, and to dates GIBS has) and the date shown on the map ("Aqua MODIS true colour, 2015-09-15"). Aqua only: `VIIRS_SNPP_CorrectedReflectance_TrueColor` gave 404 at this path in EPSG:3857.
3. **Globe / Flat switch** using MapLibre's globe projection, only if the deck.gl `MapboxOverlay` draws the cells in the right place on the globe (interleaved mode may be needed). If not, keep Flat, drop the switch and say so in the PR.
4. **Cells over imagery.** Semi-transparent fill (values in question 4), outlines appearing on zoom (with T-071), country labels and the selected-cell outline readable on imagery (halo or a pale casing). The "no detected activity" sand tone (T-071) is re-checked on imagery.
5. **Credit.** A GIBS credit and link on the map ("Imagery: NASA GIBS / EOSDIS, Blue Marble; MODIS Aqua"), always visible, plus the layer date.
6. **Docs.** Both layers in `docs/DATA_SOURCES.md` with a verification label for each claim (URL answers, date range, licence, attribution wording); risk row in `docs/RISKS_AND_LIMITATIONS.md`.
7. **Offline copy.** With no network the map keeps the plain background and shows a short note ("Imagery needs an internet connection"); tile errors never break the cells.

## 3. Out of scope

Any product value, verdict rule or API shape; `app/public/geo/` and the country-boundary code (read only); header, tabs and layout (T-070); the T-071 items; analytics (T-083); basemap tiles from any provider other than NASA GIBS; a tile proxy or server; downloading imagery into the repo.

## 4. Files and coordination

- Likely touched: `app/src/components/map/MapView.tsx` (style, sources, `MapboxOverlay` mode, projection), a new small module for the GIBS layer definitions and the date clamp (for example `app/src/components/map/gibs.ts`), `app/src/components/map/mapOverlays.tsx` and `.css` (switches, day picker, credit, note), `app/src/content/ui.ts` (strings; created by T-070), tests, `docs/DATA_SOURCES.md`, `docs/RISKS_AND_LIMITATIONS.md`, `app/README.md`.
- **Coordination:** T-072 (PR #82) also edits the `MapView.tsx` world-view fit. T-084 rebases after T-072 and keeps the fit as is; the two do not touch the same lines except around `map.fitBounds`.
- Do not edit `docs/TASK_TRACKER.md`.

## 5. Open questions for the Lead, with defaults

1. **Day for Satellite view.** Default: a day picker defaulting to the 15th of the selected month, clamped to the last day available (the current month ends at the latest date GIBS has). Alternative: the day with the most hotspots in the selected cell, which needs data the app does not load.
2. **What is on by default.** Default: Blue Marble basemap on, true colour off (Satellite view is a switch).
3. **Network failure.** Default: on tile errors fall back silently to the plain background colour and show the note once; the verdict cells never wait on imagery.
4. **Cell opacity.** Default: verdict fill alpha about 0.65 over imagery (0.85 on the plain background), outline 0.5 px at alpha 35 from zoom 3 (T-071 values); final numbers chosen with the colour-vision tests run over imagery.
5. **Globe default.** Default: Flat. Globe is an opt-in switch, shown only if the cells render correctly on it.
6. **Zoom cap.** Default: raster `maxzoom` 8 for Blue Marble and 9 for true colour (the GIBS levels), so MapLibre overzooms the last level instead of requesting missing tiles; map `maxZoom` unchanged.
7. **Caching.** Default: no app-side tile cache. GIBS sends `cache-control: public, max-age=259200` for the basemap and `no-store` for the daily true colour (see the PR facts), so the browser re-requests true-colour tiles; accept that, and report load times in the PR.
8. **Third-party requests and privacy.** Imagery tiles are requested from `gibs.earthdata.nasa.gov`. No user data is sent beyond the standard tile request; NASA GIBS sees the visitor's IP address and the tile coordinates. Default: state this in `docs/DATA_SOURCES.md` and in the credit's tooltip. Alternative: ask the Lead whether this is acceptable for the demo.

## 6. Acceptance

- Blue Marble basemap shows; Satellite view toggles and shows the date; cells and labels stay readable over both; credit and link are on the map.
- Indonesia, September 2015, Satellite view on: smoke visible behind the cells.
- Globe switch present and correct, or absent with the reason in the PR.
- Offline (network blocked): plain background, note shown, no console errors from the app, cells draw.
- Screenshots at 1440x900, 1280x720 and 375 px wide, including Indonesia Sep 2015 in Satellite view; before and after.
- Lint, typecheck, tests, build and audit pass; `DATA_SOURCES.md` entries carry verification labels.

## 7. Risks

- **Tile load time and bandwidth** on slow links: Level9 true colour is heavy at close zoom; measure and report.
- **GIBS availability and CORS:** `access-control-allow-origin: *` is returned today **[verified in the PR]**; availability of a third-party service during the demo is not under our control **[risk]**; the plain background is the fallback.
- **Attribution:** GIBS asks for acknowledgement of NASA GIBS/ESDIS; wording to be confirmed from the GIBS pages **[unverified]**.
- **Colour-vision tests** (`colorVision.test.tsx`, risk T18) assume a plain background; cells over imagery change the effective colours. Re-run with imagery-colour samples (ocean blue, desert tan, forest green, cloud white) and do not weaken thresholds.
- **Performance:** a second raster layer and the globe projection cost frame time on low-end devices; measure at 375 px.
- **Reduced motion:** no animated transitions on the layer switch or projection change when `prefers-reduced-motion` is set.
- **Imagery gaps:** true colour has swath gaps and cloud; the date and an "imagery is context, not a measurement" line must be shown so it is not read as a result **[honesty]**.
