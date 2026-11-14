# Task prompt: T-031 Global map: country layer + analysis-cell layer

> Prepared for: Member 3 · Date: 2026-11-14 · Based on main @ 53e3c46
> Source of truth: docs/TASK_TRACKER.md row T-031. This prompt adds no scope beyond it.
> **Assignment status:** the Lead assigns T-031 in PR #12 ("Assign T-034 and T-031 to Member 3"), which is open and not yet merged at the time of writing. The Lead's text: "The country layer can be built now; the cell layer uses the T-010 fixtures once they are merged."

## 1. Project context

The team is building a global web platform for the NASA Space Apps Challenge 2026, "Harmonization of MODIS and VIIRS Hot Spots" (Many Witnesses + Witness Stand, global scope, D-002/D-003). Member 2's pipeline turns FIRMS hotspots into one harmonized monthly record; Member 3 builds the API and web app around those products (`docs/PROJECT_PLAN.md`). T-030 (merged) created the app skeleton in `app/`. T-031 adds the first real view: the global map, which the demo and every later view (calendar, evidence panel, area selection) build on.

## 2. Task objective

When the task is done, the web app shows a global map with (a) Natural Earth country polygons on a plain background and (b) an analysis-cell layer for a selected month, coloured by a layer mode (verdict, raw, harmonized), with a month selector, a legend with units, and a tooltip per cell. Clicking a cell or country updates the shared selection state. The country layer and map shell can be completed before fixtures exist. The cell layer is completed against the T-010 fixtures once they are merged.

## 3. Assigned responsibility

- Task ID / priority: T-031 / P0
- Owner: Member 3 (Application Development & UI)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-030 (merged); T-010 (Member 2's fixtures, not yet merged). Per the Lead, work starts from the contract and switches to the T-010 fixtures when merged.

## 4. Relevant files and directories

- Read: `CLAUDE.md`, `docs/TASK_TRACKER.md`, `docs/TEAM_WORKFLOW.md`, `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACT.md`, `docs/TECH_STACK.md` (§7), `docs/DECISION_LOG.md`, `docs/prompts/MEMBER_3_APPLICATION_PROMPT.md` (§0, §5, §6, §10, §17, §18, §19, §S), `app/README.md`
- Create/modify (nothing else):
  - `app/src/api/` (contract TypeScript types for the map payloads and a typed client)
  - `app/src/state/` (selection state: entity, month, layer mode)
  - `app/src/components/map/` (map, legend, month selector, tooltip)
  - `app/src/components/common/` (loading and error states used by the map)
  - `app/src/content/` (verdict labels)
  - `app/public/geo/` (Natural Earth admin-0 boundaries, small scale; see §15)
  - `app/src/App.tsx`, `app/src/App.test.tsx`, related `*.test.ts(x)` files
  - `app/package.json` / `package-lock.json` only if a library from the approved stack is needed
  - `app/README.md` (folder map and run notes)
  - `docs/task-prompts/T-031-global-map.md` (this file)
  - `docs/TASK_TRACKER.md` (the T-031 row only)

## 5. Approved technologies

From `docs/TECH_STACK.md` §7 (D-008). Already installed in T-030: React 19.3.1, Vite 8.3.8, TypeScript 7.0.2 (strict), MapLibre GL JS 6.18.0, deck.gl 9.4.1 modules (`@deck.gl/core`, `@deck.gl/layers`, `@deck.gl/react`, `@deck.gl/maplibre`), TanStack Query 5.107.1, Vitest 5.1.0. Country boundaries: Natural Earth admin-0 (public domain). Nothing outside this list may be added without a new Lead decision.

## 6. Architecture and data contract

- Component: web app (`docs/ARCHITECTURE.md` §2). It talks only to the API or the static JSON export, never to Parquet.
- Contract `0.1.0` (D-016) products used: `cells` (bounds), `cell_month_harmonized` (`estimate`, `ci90_low`, `ci90_high`, `raw_combined_cell_days`, `pct_of_normal`, `verdict`, `reason_codes`, `data_level`), `metadata.json` (`latest_month`, `provisional_months`, `synthetic`).
- Endpoint: `GET /api/map?year=&month=&layer=verdict|raw|harmonized` (one record per cell: `cell_id`, `lat_min`, `lat_max`, `lon_min`, `lon_max` plus that cell-month's `cell_month_harmonized` fields) and `GET /api/meta`. The envelope and error format in the workstream prompt §S.5 are [PROPOSED ADDITION] items (D-022), so they are not binding until approved. They are used only if the Lead confirms (see §15).

## 7. Inputs

- Natural Earth admin-0 countries file (see §15).
- Fixtures from T-010 (when merged): `data/fixtures/v0.1.0/` (synthetic; geography is real).
- The API from T-034 (when built), base URL from a Vite environment variable (name only; no values committed).

## 8. Expected outputs

1. A map view filling the main area, with pan and zoom, using MapLibre GL JS and deck.gl, with no external tile dependency.
2. A country layer from the Natural Earth boundaries file (kept small).
3. A cell layer drawn from `lat_min`/`lat_max`/`lon_min`/`lon_max`, with three layer modes: Verdict (categorical colours, each with an icon and text label, never colour alone), Raw (`raw_combined_cell_days`, sequential ramp) and Harmonized (`estimate`, the **same** sequential scale as Raw).
4. A month selector from 2002-07 to `metadata.latest_month`, with provisional months marked.
5. A tooltip per cell: cell, verdict, `% of normal`, estimate with its 90% interval, reason codes as short text; `null` shown as "no data", never as zero.
6. A legend, always visible, with units ("fire-active cell-days, Aqua-equivalent").
7. Selection state (entity, month, layer mode); clicking a cell selects a `CELL` entity, clicking a country selects the `COUNTRY` (ISO3 from the boundary attributes).
8. A persistent, non-dismissable banner "SYNTHETIC DATA — not NASA observations" whenever `metadata.synthetic` is `true` (deferred to this task by the Lead's answer in PR #5).
9. Loading, error (with retry) and empty states as in the workstream prompt §17.

## 9. Implementation requirements

1. Components consume only the documented data contract. TypeScript types mirror the contract; unknown enum values and missing fields surface as visible errors and are never silently coerced.
2. No science in the app: no conversions, baselines, percentiles, probabilities or verdicts. Display exactly what the products contain.
3. Use the colour-blind-safe categorical palette (Okabe–Ito derived) for verdicts, paired with an icon and a text label. Check WCAG AA contrast for text on fills.
4. Wording: "satellite-detected fire activity" and "fire-active cell-days", never "number of fires". `NO_DETECTED_ACTIVITY` is never described as "below normal". No detection ≠ no fire.
5. Everything on the map is keyboard-reachable where possible; the month selector and layer-mode control are keyboard-operable with visible focus and ARIA labels. Respect `prefers-reduced-motion`.
6. Never present synthetic data as results. Fixtures are not used in submission screenshots or the demo.
7. Do not invent performance numbers. Report any measured pan/zoom or month-change timings as measured, with the machine.

## 10. Constraints: do not modify

- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify".
- Do not touch `pipeline/`, `data/` (Member 2) or `api/` (T-034 is a separate task).
- No secrets, no `.env` files, no large data files committed (the boundaries file must stay small), no direct pushes to `main`, no self-merge.
- No AI tool names or attribution in commits, PR text, branch names, code comments, UI credits or metadata (D-020).
- Do not mark anything validated that has not run.

## 11. Acceptance criteria

From the tracker: **"Selected month renders; tooltip per cell."** Made measurable:

1. Country layer: the world's countries render from the boundaries file, with no external tile requests (check the network panel).
2. Cell layer (needs T-010 fixtures): selecting any month from 2002-07 to the latest renders that month's cells for the chosen layer mode.
3. Hovering or focusing a cell shows the tooltip fields in §8 item 5; `null` shows "no data".
4. Verdict colours always come with an icon and a text label; Raw and Harmonized use the same scale.
5. The synthetic banner is visible whenever `metadata.synthetic` is `true`.
6. Loading, error and empty states each render.
7. `npm ci`, `npm run build`, `npm test` and `npm run lint` pass in `app/`.

## 12. Required tests

Run from `app/`; paste actual output into the PR.

- Vitest: contract type guards and parsing of fixture-shaped responses; colour/scale mapping (nulls to "no data"); every `verdict` has a label, icon and colour; the synthetic banner appears when `synthetic = true`; selection state updates.
- Component smoke tests for the map shell, legend, month selector and each state in §8 item 9.
- Manual: keyboard-only walkthrough, a colour-blindness simulation check, and screenshots of each view and state (with the synthetic banner visible when fixtures are used).

## 13. Documentation updates

- `docs/TASK_TRACKER.md`: the T-031 row only (status, branch, PR link).
- `app/README.md`: folder map and any new run notes.
- `docs/RISKS_AND_LIMITATIONS.md`: any performance or browser-support limitation found, in the same PR.
- `docs/HANDOFF.md` and `docs/PROGRESS_LOG.md`: a PR note asking the Lead to update them.

## 14. Git branch and PR instructions

- Branch: the tracker plans `frontend/T-031-global-map`. Member 3 asked to keep working on `Swastik`. The Lead accepted `Swastik` for T-030 only (PR #5 comment), so this needs the Lead's confirmation (§15, item 1).
- First commit: this prompt file.
- Open a DRAFT PR early; title "T-031: Global map: country layer + analysis-cell layer"; fill in `.github/pull_request_template.md`.
- Mark Ready for review only when §11 and §12 are satisfied.
- Never merge; wait for the Project Lead.
- Commit with your own Git identity; no AI names or attribution (D-020). Conventional Commits with the task ID, e.g. `feat(app): add country layer (T-031)`.

## 15. Out-of-scope or blocking issues

Open questions for the Lead. None is decided here.

1. **Branch.** Member 3 wants to continue on `Swastik`. The Lead said `Swastik` was accepted for T-030 only and that later tasks use `frontend/T-0XX-<short-name>`. Please confirm `Swastik` for T-031, or ask for a new branch.
2. **Assignment is not on `main` yet.** PR #12 assigns T-031 but is open. Work on the country layer starts on the strength of the Lead's PR text.
3. **Boundaries file.** Natural Earth admin-0, 1:110m (small) or 1:50m? The workstream prompt prefers one of these. The file must be downloaded from the Natural Earth project and committed in `app/public/geo/` (public domain). Member 3 must approve the download (filename, source, size) before it happens.
4. **Cell data source.** The map must talk only to the API. T-034 (API) and T-010 (fixtures) are not merged. Is the cell layer built against a typed client with mock responses in tests only until both land, or should T-031 read the fixtures through a temporary adapter? Default if not answered: typed client plus `SYNTHETIC` mock objects in test files only (workstream prompt §22).
5. **Envelope and error format.** These are [PROPOSED ADDITION] items (D-022). Should the client assume `{"contract_version", "method_version", "synthetic", "data"}` now?
6. **Month range and latest month.** The month selector needs `metadata.latest_month`, which comes from the fixtures or API. Until they exist, it is not wired to real data.
7. **Base map.** No external tile dependency, as the workstream prompt says. Confirm that a plain background with country polygons is acceptable.
