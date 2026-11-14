# Task prompt: T-040 Global anomaly list

> Prepared for: Member 3 · Date: 2026-11-14 · Based on main @ 700b261
> Source of truth: docs/TASK_TRACKER.md row T-040. This prompt adds no scope beyond it.
> **Assignment status:** the Lead assigns T-040 (with T-035, T-036, T-037 and T-038) in PR #26. T-035, T-036 and T-037 are merged. The Lead marks each row in that PR when its own PR merges, so this task does not edit the tracker (see §13).

## 1. Project context

The team is building a global web platform for the NASA Space Apps Challenge 2026, "Harmonization of MODIS and VIIRS Hot Spots" (Many Witnesses + Witness Stand, global scope, D-002/D-003). Member 2's pipeline produces monthly harmonized products; Member 3 builds the API and web app around them (`docs/PROJECT_PLAN.md`). T-030 to T-037 are merged: the map, the calendar, the raw/harmonized control, the API, area selection, the evidence panel and the witness chart. Today a user must already know where to look. T-040 adds the global overview: for the selected month, a ranked list of the areas whose verdict is confidently above or below normal, so a first-time user can start from what stands out.

## 2. Task objective

When the task is done, the web app shows, for the selected month, a ranked list read from `GET /api/anomalies`: each entry shows the area name, the verdict icon and label, the probability in whole percentages, and `% of normal`. Clicking an entry selects that area, so the calendar, the evidence panel and the witness chart follow. Listed areas are outlined on the map. When there are none, the list says "No areas with a confident above- or below-normal verdict this month." The ranking is the API's; the app does not re-sort or compute anything.

## 3. Assigned responsibility

- Task ID / priority: T-040 / P0
- Owner: Member 3 (Application Development & UI)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-034 (merged).

## 4. Relevant files and directories

- Read: `CLAUDE.md`, `docs/TASK_TRACKER.md`, `docs/TEAM_WORKFLOW.md`, `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACT.md` (§4), `docs/TECH_STACK.md` (§7), `docs/DECISION_LOG.md`, `docs/prompts/MEMBER_3_APPLICATION_PROMPT.md` (§0, §10, §13, §17, §18, §19, §S), `api/README.md`, `app/README.md`
- Create/modify (nothing else; see §15 for items awaiting the Lead):
  - `app/src/components/anomalies/` (new): the list and its states
  - `app/src/api/contract.ts` and `app/src/api/client.ts`: the anomaly type and parser, and `fetchAnomalies()`
  - `app/src/components/map/MapView.tsx`: outline the listed countries
  - `app/src/App.tsx`, `app/src/index.css`: place the list
  - new and existing `*.test.ts(x)` files under `app/src/`
  - `app/README.md` (folder map)
  - `docs/task-prompts/T-040-anomaly-list.md` (this file)

## 5. Approved technologies

From `docs/TECH_STACK.md` §7 (D-008). Already installed and pinned in `app/package-lock.json`: React 19.3.1, Vite 8.3.8, TypeScript 7.0.2 (strict), MapLibre GL JS 6.18.0, TanStack Query 5.107.1, Vitest 5.1.0. Nothing outside the list may be added without a new Lead decision. No new package is needed.

## 6. Architecture and data contract

- Component: web app (`docs/ARCHITECTURE.md` §2). It talks only to the API.
- Endpoint (as built in T-034, bare payloads, FastAPI's default error body): `GET /api/anomalies?year=&month=&limit=` returns `[{entity_type, entity_id, entity_name, verdict, p_above, p_below, pct_of_normal}]`. Only `ABOVE_NORMAL` and `BELOW_NORMAL` verdicts, ordered by the larger of `p_above` and `p_below`, descending, with ties broken by entity type and id. The default limit is 20 and the maximum 500. `400` for invalid parameters, `503` if products are unavailable.
- Contract `0.1.0` (D-016), product `entity_month` (§4): the entities are `COUNTRY`, `CONTINENT` and `GLOBAL` records. There are no cell anomalies and no custom areas in the response.
- The API is not changed.

## 7. Inputs

- The merged API (T-034) serving the T-010 SYNTHETIC fixtures in development (Vite dev proxy, `app/README.md`).
- The selected month from the selection state (T-032).
- Test data: tiny `SYNTHETIC` objects inside test files only. Nothing in `data/fixtures/` is edited.

## 8. Expected outputs

1. A ranked list for the selected month, in the order the API returns. Each entry shows: the area name; the verdict as icon and label; the verdict's probability in whole percentages ("82% likely above normal", using `p_above` for `ABOVE_NORMAL` and `p_below` for `BELOW_NORMAL`); and `% of normal` as stored (`null` shown as "no data", never zero).
2. Clicking an entry selects that area: a country, a continent or the world. The calendar, evidence panel and witness chart follow, and the map fits to the area as in the area picker.
3. Listed countries are outlined on the map (see §15, item 3 for continents and the world).
4. The empty state "No areas with a confident above- or below-normal verdict this month."
5. Loading, error with retry, and `503` "Data are not available right now" states (workstream prompt §17). A month with no selection yet shows a prompt, not an error.
6. A provisional badge when the selected month is provisional.
7. The list is keyboard-operable (each entry is a button) and named for screen readers, with the rank, area, verdict, probability and percentage in its accessible label.

## 9. Implementation requirements

1. **No science.** The order, the verdicts and the probabilities are the API's, shown as received: no re-sorting, no filtering by a threshold, no recomputation. The only derivation is choosing which stored probability belongs to the verdict.
2. **Contract fidelity.** The anomaly type mirrors the endpoint; unknown enum values and missing fields surface as errors and are never coerced.
3. **Wording.** "Satellite-detected fire activity", never "number of fires". `CANNOT_DETERMINE` and `NO_DETECTED_ACTIVITY` never appear here (the API excludes them).
4. **Accessibility:** WCAG 2.1 AA contrast, visible focus, no information by colour alone (icon and text label with every verdict), `prefers-reduced-motion` respected.
5. TypeScript strict; code consumes only the documented contract.

## 10. Constraints: do not modify

- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify".
- Do not touch `pipeline/`, `data/` or `api/`.
- Do not build the CSV export (T-038).
- No secrets, no `.env` files, no large files, no direct pushes to `main`, no self-merge.
- No AI tool names or attribution in commits, PR text, branch names, code comments or metadata (D-020).
- Do not mark anything validated that has not run.

## 11. Acceptance criteria

From the tracker: **"Ranked by probability; links to the entity."** Made measurable:

1. For the selected month the list shows the API's entries in the API's order, each with area name, verdict icon and label, probability in whole percentages and `% of normal`.
2. Clicking an entry selects that entity and the other views follow (tested; checked against the API serving the fixtures).
3. Listed countries are outlined on the map.
4. The empty state, loading, error with retry and `503` states render, as does a provisional badge.
5. No value is computed or re-ordered in the app (reviewable in the diff).
6. `npm ci`, `npm run build`, `npm test`, `npm run lint` and `npm run typecheck` pass in `app/`.

## 12. Required tests

Run from `app/`; paste actual output into the PR.

- Vitest: anomaly parsing (valid, `null` percentage kept, unknown verdict and entity type rejected, missing field rejected, a verdict other than above or below rejected); `fetchAnomalies` (request, `400`, `503`, network failure); the verdict's probability (`p_above` for above, `p_below` for below, whole percentages, never more precise); the entry text and accessible label; the order is preserved and not re-sorted; the empty state wording; the mapping from a clicked entry to a selection (country, continent, world); the set of countries to outline.
- Component smoke tests with SYNTHETIC objects defined inside test files.
- Manual (reported honestly, including what was not done): the list against the API serving `data/fixtures/v0.1.0` for a month with anomalies and a month without; clicking entries; the map outlines; a keyboard-only pass; screenshots with the synthetic banner visible.

## 13. Documentation updates

- `docs/TASK_TRACKER.md`: **not edited**. The Lead marks each row in PR #26 when its PR merges.
- `app/README.md`: folder map.
- `docs/RISKS_AND_LIMITATIONS.md`: any limitation found, in the same PR.
- `docs/HANDOFF.md` and `docs/PROGRESS_LOG.md`: a PR note asking the Lead to update them.

## 14. Git branch and PR instructions

- Branch: `frontend/T-040-anomaly-list`, created from the latest `main`.
- First commit: this prompt file.
- Open a DRAFT PR early; title "T-040: Global anomaly list"; fill in `.github/pull_request_template.md` with the real summary, changed files and results.
- Mark Ready for review only when §11 and §12 are satisfied.
- Never merge; wait for the Project Lead.
- Commit with your own Git identity; no AI names or attribution (D-020).

## 15. Out-of-scope or blocking issues

Open questions for the Lead. None is decided here. Suggested defaults are what I will do if the Lead does not answer.

1. **Assignment and tracker.** PR #26 assigns T-040. I will start on the strength of the Lead's PR text and not edit the tracker.
2. **Mixed entity types.** The API returns countries, continents and the world together, and a continent's anomaly is largely its countries' anomalies, so the list can look repetitive. Default: show every entry as the API returns it, with a small type label ("Country", "Continent", "World"), and do not filter or de-duplicate. Alternative: list countries only. Which?
3. **Map outlines.** The workstream prompt says to outline listed "entities or cells", but the API returns no cells, and only countries have a polygon on the map. Default: outline the listed countries (matched by ISO 3166-1 alpha-3 code, as the existing country selection is); continents and the world appear in the list only. Alternative: also outline the bounding box of a listed continent. Which?
4. **How many entries.** Default: request the top 10 and show them all, with the count and a "Show more" button that asks for 20. The API's own default is 20. Confirm, or specify a number.
5. **Placement.** Default: a panel in the map's right-hand column, below the area picker, so the list sits next to the map it outlines. Alternative: a section below the map or in the evidence row. Which?
6. **Clicking an entry.** Default: selects the area exactly like choosing it in the area picker (including fitting the map to it, using its bounds from the entity list), and moves focus to the evidence panel's heading as a calendar click does. Confirm.
7. **Interaction with the other controls.** Default: the list is harmonized only (verdicts exist only for the harmonized estimate) and does not change with the Raw / Harmonized control or the map mode. Confirm.
8. **Provisional months.** Default: a "Provisional" badge on the list when the selected month is in `metadata.provisional_months`. Anomalies in provisional months can change, so the list says so. Confirm the wording "Provisional: may change when science-quality data arrive" (the text already used in the evidence panel).
