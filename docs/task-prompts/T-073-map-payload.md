# Task prompt: T-073 Performance: map payload and month switching

> Prepared for: Member 3 · Date: 2026-11-15 · Based on main @ 8408758
> Source of truth: docs/TASK_TRACKER.md row T-073 (P1) and the Lead's audit in PR #73 ("`/api/map` sends about 3.1 MB per month even with gzip, about 0.7 s locally and much more on venue Wi-Fi"). Rule from the Lead: no data-contract change and no change of an API response shape without the Lead's approval. This prompt adds no scope beyond these.

## 1. Objective

Switching the month on the map feels instant and never blanks the map, and a repeat or prefetched month costs no download. Where the payload can be made smaller or faster without changing a single value or the response shape, that is done; where it cannot, the options are measured and proposed for the Lead's decision, not built.

## 2. Audit findings (measured on the real products, month 2023-07, `layer=verdict`)

- `GET /api/map` returns 56,238 cells: 32.4 MB of JSON (already compact separators), 3.07 MB with gzip level 6, about 0.8 s on every request, because DuckDB, contract validation, serialization and compression all run again each time. The three layers return identical bytes (the layer only changes how the app colours cells).
- What dominates the gzipped size: the floating-point fields (`estimate`, `ci90_*`, `sd`, `baseline_*`, `p_*`, `pct_of_normal`: about 1.7 MB of the 3.07 MB), then `cell_id` (about 0.12 MB). Repeated JSON keys cost about 0.09 MB after gzip (21.6 MB raw, but they compress almost entirely). Nulls are cheap. The values are stored as DOUBLE, so no lossless shortening of the digits exists.
- Consequence: lossless server changes cannot shrink the bytes much (gzip level 9 saves about 4%); they can remove the repeat cost (cache) and make repeats free for the browser (headers).
- Client: the map query key changes with the month and shows a loading state each time; nothing is prefetched; React Query's defaults (`staleTime` 0) refetch on remount.

## 3. In scope

- API (no change of shape or values): an in-process cache of the serialized, compressed map month keyed by the products directory, the month and the modified time and size of the two product files read; `ETag`, `If-None-Match` (304), `Cache-Control`, `Vary`; gzip level for the cached bytes; tests (hit, invalidation when a file is touched, headers, 304, errors not cached, identical payload).
- App (`app/src/api/*`, `app/src/state/*`): long `staleTime` and a small cap on cached months for the map query, previous month kept while the next loads, prefetch of the adjacent months (previous, next, then the two beyond when idle) for the layer in use; tests on synthetic data. Any wiring in `App.tsx` is a minimal one-line hook call, reported to the Lead.
- Measurements before and after (bytes raw and gzipped, first and repeat request, per layer) on the real products.
- Proposals (measured offline, not implemented) for cutting the payload further: lean per-layer fields, the columnar layout as a new endpoint, transport precision.

## 4. Out of scope

- Any change of an API response shape or of the data contract; `pipeline/`, `data/`; `app/src/App.tsx` layout, styles, `MapView.tsx`, `Legend.tsx`; new dependencies; the offline copy's format.

## 5. Open questions, with defaults

1. **Browser cache lifetime.** Default: `Cache-Control: public, max-age=300` plus an `ETag`, so a rebuilt product is seen within five minutes and a revalidation costs a 304. Longer, or `immutable`, is possible if products are only replaced with a restart.
2. **Cache bound.** Default: 16 months in memory (about 50 MB compressed) on the server; 8 months of map data in the browser.
3. **Prefetch depth.** Default: previous and next month at once, the two beyond when the browser is idle, only for the layer in use and only in the live (non-offline) mode.
4. **Payload reductions.** Default: none built; see the proposals, which need the Lead's approval because each changes a response shape or the displayed precision.

## 6. Acceptance

- The payload bytes of every month are identical to those before the change (test and a real-product comparison); values and shape unchanged.
- A repeat request is served from memory (measured), a touched product file invalidates it, `ETag` and `304` work, errors are never cached.
- In the app, a month already seen or prefetched shows with no request; while a new month loads, the previous map stays visible.
- API `ruff format --check`, `ruff check`, `pytest`; app lint, `tsc -b`, `vitest`, build, `npm audit` pass. Before and after numbers and the proposals are in the PR description.
