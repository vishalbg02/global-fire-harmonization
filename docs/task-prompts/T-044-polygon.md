# Task prompt: T-044 Free-polygon custom area

> Prepared for: Member 3 · Date: 2026-11-15 · Based on main @ cd4a532
> Source of truth: docs/TASK_TRACKER.md row T-044 (P1, depends on T-035, merged), the Lead's assignment in PR #38 ("free polygon via terra-draw (D-024); point-in-cell rule documented; `503` until `harmonize_area()` exists" — `harmonize_area()` has been wired since #47, so the `503` applies only when it cannot be loaded) and the Lead's note on #38 ("custom areas (rectangle in T-035, polygon in T-044) can now return real harmonized series"). Status of 2026-11-15: T-044 follows T-039 phase 2. This prompt adds no scope beyond these.

## 1. Objective

A user can outline any shape on the map (or type its corner points) and get the same views as for a rectangle: the calendar, the evidence panel and the satellite chart for that area, from `harmonize_area()`, with the rule that decides which grid cells belong to the shape written down and tested. Nothing is computed in the app; the API selects the cells and calls the single implementation of the science.

## 2. What exists today

- Rectangle: typed W, S, E, N or two clicks on the map (`terra-draw` with its MapLibre adapter, D-024, rectangle mode). `POST /api/series/custom` takes `{"bbox": [W, S, E, N]}`; the API selects the cells whose **centre** lies inside the box (bounds inclusive), passes them to `harmonize_area(cell_ids, months)` with the module defaults, caches the answer, and returns `422` for an empty or invalid box and `503` when the function or products cannot be loaded. The CSV export takes `bbox=W,S,E,N`; the offline copy disables custom areas.
- `terra-draw` 1.39.0 already contains a polygon mode: no new dependency is expected.
- Measured (T-042): a country-sized area takes about 3.3 s the first time and about 0.01 s from the cache; the whole world 8 s.

## 3. In scope

- API: accept a polygon in `POST /api/series/custom`; the point-in-cell rule; validation and limits; the CSV export for a polygon (question 6); tests against the fixtures and the real products; `api/README.md`.
- App: polygon drawing mode on the map, a typed list of corner points as the keyboard route, the same loading and error states as the rectangle, the polygon outline on the map, the link keeping the area (question 4), tests, screenshots, `app/README.md`, `docs/RISKS_AND_LIMITATIONS.md`.

## 4. Out of scope

- Any change in `pipeline/`, `data/` or the data contract; a new science function; areas that cross the antimeridian (not supported for the rectangle either); editing a polygon after it is drawn beyond redrawing.

## 5. Open questions, with defaults

1. **Is it still wanted?** T-044 is P1 and the risk table lists "polygon custom area" among the first things to cut if behind schedule. Default: build it after T-039 phase 2; say if it should be cut or postponed instead.
2. **Request shape.** Default: extend `POST /api/series/custom` so the body is either `{"bbox": [W, S, E, N]}` (unchanged) or `{"polygon": [[lon, lat], ...]}` (one outer ring, at least 3 distinct points, first point not repeated; the API closes it), never both (`422`). It is an API-level request shape, not the data contract of the products. Do you approve this shape (the other option is a GeoJSON `Polygon`)?
3. **Which cells belong to the shape.** Default, consistent with the rectangle: **a grid cell belongs when its centre lies inside the polygon, boundary included** (even-odd rule, own ray-casting code with tests, no new dependency). Its consequence, to document: a cell that the polygon covers 60% but whose centre is outside is left out, and the polygon of a tiny shape may contain no cell centre (`422` "No analysis cells have their centre inside this area."). Alternative: a cell belongs when at least 50% of its area is inside, which needs a geometry library (a new dependency, not approved). Do you accept the centre rule?
4. **Limits and the link.** Default: at most 100 corner points; coordinates within the world box and not crossing the antimeridian; a self-intersecting ring is rejected with a clear `422` (rather than interpreted by the even-odd rule); the polygon is kept in the page link (`area=POLY:lon,lat;lon,lat;...`, rounded to 4 decimals) so a view can be shared. Do you agree with these limits, and should a polygon be kept in the link at all (the alternative: not shared, only in the session)?
5. **Keyboard and accessibility.** Drawing needs a pointer. Default: a text box where each line is `longitude, latitude` (the keyboard and screen-reader route, with the same validation and messages), plus the map drawing; the polygon is announced as "Custom polygon, N corner points, M grid cells".
6. **CSV export of a polygon.** The rectangle's export is a `GET` with `bbox` in the URL; a polygon of up to 100 points is long for a URL. Default: `POST /api/export.csv` with the same body as the series request (the existing `GET` stays), and the file header names the area as "CUSTOM polygon (N points)". Or: the CSV is not offered for a polygon in this version. Which?
7. **Offline copy.** Default: polygons are disabled in the offline copy with the same message as the rectangle ("Custom areas need the live service. This offline copy has the preset views only.").
8. **Cache.** Default: the existing cache key (the sorted cell set, product files and method version) is reused, so two polygons that select the same cells share an answer.

## 6. Acceptance

- A polygon drawn or typed returns the series of the cells whose centres lie inside it (a test compares the selected cells with a brute-force check on the fixtures and on the real products); invalid shapes give clear `422` messages; the calendar, evidence and chart follow.
- The rule and its consequences are in `api/README.md` and in the app next to the polygon; the app's limits are tested.
- Lint, typecheck, tests (API and app), build and audit pass; screenshots of drawing, the typed route and an error state go with the PR.
