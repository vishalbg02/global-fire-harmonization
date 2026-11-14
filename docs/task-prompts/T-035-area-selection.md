# Task prompt: T-035 Country/continent selection + rectangle custom area

> Prepared for: Member 3 · Date: 2026-11-14 · Based on main @ f4cbf07
> Source of truth: docs/TASK_TRACKER.md row T-035. This prompt adds no scope beyond it.
> **Assignment status:** the Lead assigns T-035 (with T-036, T-037, T-038 and T-040) in PR #26 ("Assign T-035, T-036, T-037, T-038, T-040 to Member 3"), open and not yet merged at the time of writing. The Lead said they mark each row in that PR when its own PR merges, so this task does not edit the tracker (see §13). Suggested order: T-036 (merged), then T-035.

## 1. Project context

The team is building a global web platform for the NASA Space Apps Challenge 2026, "Harmonization of MODIS and VIIRS Hot Spots" (Many Witnesses + Witness Stand, global scope, D-002/D-003). Member 2's pipeline produces monthly harmonized products; Member 3 builds the API and web app around them (`docs/PROJECT_PLAN.md`). T-030 to T-034 and T-036 are merged: the map, the calendar, the raw/harmonized control, the API and the evidence panel. Today the only way to choose an area is to click a country on the map. T-035 adds the controls the challenge asks for: pick a country, a continent or the world, or define a custom rectangle by its latitude and longitude.

## 2. Task objective

When the task is done, the user can choose the area that the calendar and the evidence panel show: by searching for a country, by choosing a continent, by choosing the world, or by defining a custom rectangle (typed W/S/E/N, and drawn on the map if the drawing library is approved, see §15). A custom rectangle calls `POST /api/series/custom` and its series drives the calendar and the evidence panel. The app shows a note that a custom area is approximated by the grid cells whose centres fall inside the box, shows the server's message on a `422` or `503`, and keeps the selection (area, month and display modes) in the URL query string so views can be shared.

## 3. Assigned responsibility

- Task ID / priority: T-035 / P0
- Owner: Member 3 (Application Development & UI)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-034 (merged). The custom-area series itself needs Member 2's `harmonize_area()`, which is not delivered (see §15, item 3).

## 4. Relevant files and directories

- Read: `CLAUDE.md`, `docs/TASK_TRACKER.md`, `docs/TEAM_WORKFLOW.md`, `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACT.md` (§4, §8), `docs/TECH_STACK.md` (§7), `docs/DECISION_LOG.md`, `docs/prompts/MEMBER_3_APPLICATION_PROMPT.md` (§0, §7, §17, §18, §19, §S), `api/README.md`, `app/README.md`
- Create/modify (nothing else; see §15 for items awaiting the Lead):
  - `app/src/components/area/` (new): the area picker (world, country search, continent), the custom-area form, and helpers
  - `app/src/state/urlState.ts` (new): reading and writing the selection in the URL query string
  - `app/src/state/selection.ts`: a custom area (with its box) as a selectable area
  - `app/src/api/contract.ts` and `app/src/api/client.ts`: the entity-list type and `fetchEntities()`, and `fetchCustomSeries()` with the server's message on errors
  - `app/src/components/calendar/CalendarPanel.tsx` and `app/src/components/evidence/EvidencePanel.tsx`: use the custom series when the area is a custom rectangle
  - `app/src/components/map/MapView.tsx`: show the custom rectangle on the map
  - `app/src/App.tsx`, `app/src/index.css`
  - new and existing `*.test.ts(x)` files under `app/src/`
  - `app/package.json` / `package-lock.json` only for a package the Lead approves (see §15, item 2)
  - `app/README.md` (folder map)
  - `docs/task-prompts/T-035-area-selection.md` (this file)

## 5. Approved technologies

From `docs/TECH_STACK.md` §7 (D-008). Already installed and pinned in `app/package-lock.json`: React 19.3.1, Vite 8.3.8, TypeScript 7.0.2 (strict), MapLibre GL JS 6.18.0, deck.gl 9.4.1 modules, terra-draw 1.39.0, TanStack Query 5.107.1, Vitest 5.1.0. **`terra-draw` alone does not draw on a MapLibre map:** it needs the separate adapter package `terra-draw-maplibre-gl-adapter` (checked on npm: version 1.5.0, MIT), which is not in the approved list. Nothing outside the list may be added without a new Lead decision (see §15, item 2).

## 6. Architecture and data contract

- Component: web app (`docs/ARCHITECTURE.md` §2). It talks only to the API.
- Contract `0.1.0` (D-016), product `entity_month` (§4): a custom-area response uses the same shape with `entity_type = "CUSTOM"` (§4, and `harmonize_area()` in §8).
- Endpoints (as built in T-034, bare payloads, FastAPI's default error body):
  - `GET /api/entities?type=COUNTRY|CONTINENT` returns `[{entity_type, entity_id, entity_name, bbox: [W,S,E,N]}]` for the entities present in the products.
  - `POST /api/series/custom` with `{"bbox": [W,S,E,N]}` returns `entity_month`-shaped records with `entity_type = "CUSTOM"`. `422` for an invalid area or one with no cell centres inside it, `503` while `harmonize_area()` is unavailable. The error body is `{"detail": "<message>"}`.
  - `GET /api/series` and `GET /api/evidence` serve `COUNTRY`, `CONTINENT` and `GLOBAL` only. They answer `404` for `CUSTOM`.
- The API is not changed.

## 7. Inputs

- The merged API (T-034) serving the T-010 SYNTHETIC fixtures in development (Vite dev proxy, `app/README.md`). In the fixtures only 7 countries and 6 continents exist.
- Test data: tiny `SYNTHETIC` objects inside test files only. Nothing in `data/fixtures/` is edited.

## 8. Expected outputs

1. An area picker with: a **World** option; a **country** search that lists the countries returned by `GET /api/entities?type=COUNTRY`; a **continent** choice from `GET /api/entities?type=CONTINENT`. Choosing one sets the selected area, so the calendar and the evidence panel follow. It works by keyboard and with a screen reader.
2. A **custom rectangle** form with west, south, east and north fields (degrees, WGS84). It checks the values before sending (W less than E, S less than N, within ±180 and ±90) with a clear message, calls `POST /api/series/custom`, and shows the note: "Custom areas are approximated by the grid cells whose centres fall inside the box."
3. On a `422` or `503` the server's message is shown (for example an area with no grid cells, or "Custom areas are not available yet…"); a network failure shows the usual error with retry.
4. The custom rectangle is outlined on the map while it is selected, and a clear way back to the world.
5. The calendar and the evidence panel show a custom area from its series. The evidence panel reads the month's record from the series (decoding `raw_by_witness`, which is a JSON string there), because `GET /api/evidence` does not serve `CUSTOM`.
6. The selection is encoded in the URL query string (area, month, raw/harmonized, map mode, value mode) and restored when the page loads, so a link reproduces the view. An unknown or malformed value is ignored, not an error.
7. Drawing a rectangle on the map, if the Lead approves the adapter package (§15, item 2).

## 9. Implementation requirements

1. **No science.** The app sends the box and displays what the API returns. It never computes which cells fall inside the box, and never aggregates anything. The cell-centre rule is stated in a note, and applied by the API.
2. **Contract fidelity.** Types mirror the contract; unknown enum values and missing fields surface as errors and are never coerced.
3. **Messages.** Server messages are shown as received (plain text, escaped). The client-side checks only prevent obviously invalid boxes and do not replace the server's.
4. **Accessibility:** WCAG 2.1 AA contrast, visible focus, labelled inputs with units, errors announced (`role="alert"`), a heading structure, `prefers-reduced-motion` respected, nothing available only by pointer (the typed form is the keyboard route to a custom area).
5. TypeScript strict; code consumes only the documented contract.

## 10. Constraints: do not modify

- Do not change the tech stack, architecture, scientific methodology or data contract. Adding a package needs a new Lead decision.
- Do not edit files outside §4 "Create/modify".
- Do not touch `pipeline/`, `data/` or `api/`.
- Do not build a free polygon (T-044), the witness chart (T-037), the anomaly list (T-040) or the CSV export (T-038).
- No secrets, no `.env` files, no large files, no direct pushes to `main`, no self-merge.
- No AI tool names or attribution in commits, PR text, branch names, code comments or metadata (D-020).
- Do not mark anything validated that has not run.

## 11. Acceptance criteria

From the tracker: **"Custom area returns a series via `harmonize_area()`."** Made measurable:

1. A country, a continent and the world can each be chosen from the picker, and the calendar and evidence panel follow (tested; checked against the API serving the fixtures).
2. A valid custom box is sent to `POST /api/series/custom`, and the returned records drive the calendar and evidence panel (tested with mocked responses, because `harmonize_area()` is not delivered; **not verified against the real function until Member 2 delivers it**).
3. An invalid box shows a clear message before sending; a `422` and a `503` show the server's message; neither blocks choosing another area.
4. The note about grid cells is shown with the custom area.
5. The selection round-trips through the URL (state to URL to state is unchanged) and bad values are ignored (tested).
6. No value is computed in the app (reviewable in the diff).
7. `npm ci`, `npm run build`, `npm test`, `npm run lint` and `npm run typecheck` pass in `app/`.

## 12. Required tests

Run from `app/`; paste actual output into the PR.

- Vitest: entity-list parsing and `fetchEntities`; `fetchCustomSeries` (request body, success, `422` and `503` messages, network failure); the box validation (valid, W not less than E, S not less than N, out of range, non-numeric, empty); the selection reducer for a custom area; the URL encoding and decoding (round-trip for each area kind, month, source, modes; malformed and unknown values ignored); the country filter (case-insensitive, matches on name, no match); the area name and id for a custom box.
- Component smoke tests: the area picker, the custom-area form with its note and messages, the calendar and evidence panel for a custom area, with SYNTHETIC objects defined inside test files.
- Manual (reported honestly, including what was not done): the picker against the API serving `data/fixtures/v0.1.0`; a custom box against the real API (expected `503` until `harmonize_area()` exists) and against a throwaway local stub outside the repo that stands in for it, clearly labelled SYNTHETIC; the URL restoring a view; a keyboard-only pass; screenshots with the synthetic banner visible.

## 13. Documentation updates

- `docs/TASK_TRACKER.md`: **not edited**. The Lead marks each row in PR #26 when its PR merges.
- `app/README.md`: folder map and how links encode the selection.
- `docs/RISKS_AND_LIMITATIONS.md`: any limitation found (for example that custom areas wait on `harmonize_area()`), in the same PR.
- `docs/HANDOFF.md` and `docs/PROGRESS_LOG.md`: a PR note asking the Lead to update them.

## 14. Git branch and PR instructions

- Branch: `frontend/T-035-area-selection`, created from the latest `main`.
- First commit: this prompt file.
- Open a DRAFT PR early; title "T-035: Country/continent selection + rectangle custom area"; fill in `.github/pull_request_template.md` with the real summary, changed files and results.
- Mark Ready for review only when §11 and §12 are satisfied (criterion 2 reported as not verified against the real function).
- Never merge; wait for the Project Lead.
- Commit with your own Git identity; no AI names or attribution (D-020).

## 15. Out-of-scope or blocking issues

Open questions for the Lead. None is decided here. Suggested defaults are what I will do if the Lead does not answer.

1. **Assignment and tracker.** PR #26 assigns T-035 but is open. I will start on the strength of the Lead's PR text and not edit the tracker.
2. **Drawing needs a package outside the approved stack.** `terra-draw` has no MapLibre adapter built in; it needs `terra-draw-maplibre-gl-adapter` (npm, version 1.5.0, MIT licence), which is not in `docs/TECH_STACK.md` §7. May I add it? Alternatives: write a small adapter myself (more code to review), or ship the typed W/S/E/N form only and draw later. Default: build everything else now, with the typed form as the custom-area input, and add drawing only if you approve the adapter.
3. **`harmonize_area()` is not delivered.** `pipeline/` has no such function, so `POST /api/series/custom` returns `503` today. Default: build and test the custom-area flow against mocked responses, show the server's message, and verify against a throwaway stub outside the repo; I will state plainly that the real function has not been exercised. The tracker's acceptance ("returns a series via `harmonize_area()`") cannot be fully verified until it lands.
4. **What a custom area drives.** `GET /api/series` and `GET /api/evidence` answer `404` for `CUSTOM`. Default: the calendar uses the series returned by the custom call, and the evidence panel picks the selected month's record from that series (decoding `raw_by_witness`). Confirm.
5. **Link sharing is in the workstream prompt §7 under this task.** Default: include it, encoding area, month, raw/harmonized, map mode and value mode with `history.replaceState` and no router library. Confirm, or defer it to a later task.
6. **Country search control.** Default: a text input with a native `<datalist>` over the countries returned by the API (built-in filtering, keyboard and screen-reader friendly), plus the existing click on the map. The list holds only countries present in the products (7 in the fixtures). Alternative: a custom accessible combobox. Which?
7. **Map feedback.** Default: outline the custom rectangle on the map; no outline or zoom for a continent, and no automatic zoom to a chosen area. Should a chosen country or continent also fit the map to its box?
8. **Box rules.** Default: the client rejects W not less than E, S not less than N, and values outside ±180 and ±90, with a message; a box crossing the antimeridian is not supported (the API requires W less than E). No size cap, because the API has none; if the server adds one, its message is shown. Confirm.
