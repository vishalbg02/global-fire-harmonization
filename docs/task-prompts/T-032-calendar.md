# Task prompt: T-032 Calendar (years × months; % of normal / activity)

> Prepared for: Member 3 · Date: 2026-11-14 · Based on main @ 87d97a5
> Source of truth: docs/TASK_TRACKER.md row T-032. This prompt adds no scope beyond it.
> **Assignment status:** the Lead assigns T-032 and T-033 in PR #19 ("Assign T-032 and T-033 to Member 3"), open and not yet merged at the time of writing. The Lead's text: "T-032 (calendar: years × months, % of normal / activity): ASSIGNED. Its dependency T-010 is merged; the API (T-034) is merged too." T-033 starts after T-032 and is **not** part of this prompt.

## 1. Project context

The team is building a global web platform for the NASA Space Apps Challenge 2026, "Harmonization of MODIS and VIIRS Hot Spots" (Many Witnesses + Witness Stand, global scope, D-002/D-003). Member 2's pipeline produces monthly harmonized products; Member 3 builds the API and web app around them (`docs/PROJECT_PLAN.md`). T-030 (app skeleton), T-031 (global map) and T-034 (API) are merged. T-032 adds the burning-activity calendar the challenge asks for: years down, months across, for the selected area.

## 2. Task objective

When the task is done, the web app shows a historical calendar for the selected area (a country, a continent or the world): one row per year from 2002 to the latest month, one column per month. Each cell shows a value, a verdict icon and a tooltip, in one of two value modes: **% of normal** (a diverging, colour-blind-safe ramp centred on 100%) and **Activity** (a sequential ramp of the harmonized estimate). Months outside the record are drawn as "outside record", never as zero, and `null` values are shown as "no data". Clicking a calendar cell sets the selected month, which the map already follows. An accessible table view shows the same data. The calendar reads `GET /api/series` and `GET /api/meta` from the API (T-034).

## 3. Assigned responsibility

- Task ID / priority: T-032 / P0
- Owner: Member 3 (Application Development & UI)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-010 (merged), T-034 (merged, a related dependency for the data source). T-033 depends on this task and is not started here.

## 4. Relevant files and directories

- Read: `CLAUDE.md`, `docs/TASK_TRACKER.md`, `docs/TEAM_WORKFLOW.md`, `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACT.md` (§4 `entity_month`), `docs/TECH_STACK.md` (§7), `docs/DECISION_LOG.md`, `docs/prompts/MEMBER_3_APPLICATION_PROMPT.md` (§0, §8, §10, §17, §18, §19, §S), `api/README.md`, `app/README.md`, `data/fixtures/v0.1.0/README.md`
- Create/modify (nothing else; see §15 for items awaiting the Lead):
  - `app/src/components/calendar/` (new): the calendar, its legend, value-mode selector, table view, colour scales and tooltip content
  - `app/src/api/contract.ts` and `app/src/api/client.ts`: add the `entity_month` type and parser, and `fetchSeries()`
  - `app/src/state/selection.ts`: allow `CONTINENT` and `GLOBAL` entities, and a calendar value mode
  - `app/src/App.tsx`, `app/src/index.css`: place the calendar in the page
  - `app/vite.config.ts`: the Vite dev proxy for `/api` the Lead chose instead of CORS (see §15, item 8)
  - `app/src/content/`: calendar wording only (value-mode labels, "outside record")
  - `app/package.json` / `package-lock.json` only if a library from the approved stack is needed
  - new and existing `*.test.ts(x)` files under `app/src/`
  - `app/README.md` (folder map)
  - `docs/task-prompts/T-032-calendar.md` (this file)
  - `docs/TASK_TRACKER.md` (the T-032 row only)

## 5. Approved technologies

From `docs/TECH_STACK.md` §7 (D-008). Already installed and pinned in `app/package-lock.json`: React 19.3.1, Vite 8.3.8, TypeScript 7.0.2 (strict), Apache ECharts 6.1.0, TanStack Query 5.107.1, Vitest 5.1.0. Nothing outside this list may be added without a new Lead decision.

## 6. Architecture and data contract

- Component: web app (`docs/ARCHITECTURE.md` §2). It talks only to the API.
- Contract `0.1.0` (D-016), product `entity_month` (§4), fields used: `entity_type`, `entity_id`, `entity_name`, `year`, `month`, `estimate`, `ci90_low`, `ci90_high`, `raw_combined_cell_days`, `pct_of_normal`, `p_above`, `p_below`, `p_within`, `verdict`, `reason_codes`, `data_level`, `method_version`, `n_cells`, `raw_by_witness` (a JSON string; not used by the calendar). Also `metadata.json` (`first_month`, `latest_month`, `provisional_months`, `synthetic`).
- Endpoints (as built in T-034): `GET /api/series?entity_type=COUNTRY|CONTINENT|GLOBAL&entity_id=` returns the entity's monthly records ordered by year then month; `GET /api/meta`. Bare payloads, FastAPI's default error body, `404` for an unknown entity (D-022 not approved).

## 7. Inputs

- The API from T-034. Base URL from `VITE_API_BASE_URL`; in development a Vite dev proxy for `/api` is the Lead's choice (no CORS), see §15.
- Test data: tiny `SYNTHETIC` objects inside test files only. Nothing in `data/fixtures/` is edited.

## 8. Expected outputs

1. A calendar component: rows are years (2002 to the latest year), columns are Jan to Dec. Months before 2002-07 and after `latest_month` are drawn as "outside record" with a distinct neutral style, never as zero.
2. Two value modes:
   - **% of normal:** `pct_of_normal`, on a diverging, colour-blind-safe ramp centred on 100%, with a legend.
   - **Activity:** the harmonized `estimate` on a sequential ramp, with a legend and units ("fire-active cell-days, Aqua-equivalent").
3. Cell encoding that never relies on colour alone: `ABOVE_NORMAL` ▲, `BELOW_NORMAL` ▼, `WITHIN_NORMAL` ●, `CANNOT_DETERMINE` "?" with a hatched or neutral fill, `NO_DETECTED_ACTIVITY` ○ on a light neutral. `null` values show "no data", never zero.
4. Tooltip: value, 90% interval, verdict with probability wording, reason codes as short text, a "provisional" note for `NRT` and `MIXED` months.
5. Click a calendar cell: the selected month is set (the map's month follows).
6. An accessible table view of the same data, toggled on and off, keyboard-operable.
7. A value-mode control, an empty state when no area is selected or available, and the loading, error-with-retry and "Area not found" states from the workstream prompt §17.
8. Persistent "SYNTHETIC DATA — not NASA observations" banner remains visible whenever `metadata.synthetic` is true (already provided by T-031).

## 9. Implementation requirements

1. **No science.** The calendar displays stored values exactly: no conversions, baselines, percentiles, probabilities or verdicts, and no raw baseline. `% of normal` exists only where the product has `pct_of_normal`.
2. **Contract fidelity.** Types mirror the contract; unknown enum values and missing fields surface as visible errors and are never coerced.
3. **Wording.** "Satellite-detected fire activity" and "fire-active cell-days", never "number of fires". `NO_DETECTED_ACTIVITY` is never called "below normal". `CANNOT_DETERMINE` is a first-class result with reasons, not an error.
4. **Probability wording:** whole percentages ("82% likely above normal").
5. **Accessibility:** WCAG 2.1 AA contrast for text on fills, visible focus, ARIA labels, ECharts `aria` option and a text description, a keyboard-operable table view, `prefers-reduced-motion` respected, no information by colour alone.
6. TypeScript strict; code consumes only the documented contract.

## 10. Constraints: do not modify

- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify".
- Do not touch `pipeline/`, `data/` or `api/` (T-034 is merged; any API change is a Lead decision).
- Do not implement the raw ↔ harmonized toggle (T-033), the evidence panel (T-036), area selection UI (T-035) or the witness chart (T-037).
- No secrets, no `.env` files, no large files, no direct pushes to `main`, no self-merge.
- No AI tool names or attribution in commits, PR text, branch names, code comments or metadata (D-020).
- Do not mark anything validated that has not run.

## 11. Acceptance criteria

From the tracker: **"Accessible ramps; legend; null shown as 'no data'."** Made measurable:

1. The calendar renders rows from 2002 to the latest year and 12 columns, with months outside the record drawn as "outside record" and not as zero.
2. % of normal uses a diverging ramp centred on 100%; Activity uses a sequential ramp; both have a legend with units where applicable.
3. Every value cell carries a verdict icon and text in its tooltip, so colour is never the only cue; `null` values read "no data" and are never shown as zero.
4. Text on fills meets WCAG AA contrast (checked and reported; not claimed before it is measured).
5. Clicking a cell sets the selected month; the table view shows the same data and is operable with the keyboard alone.
6. Loading, error with retry, empty, and "Area not found" states render; provisional months are marked.
7. `npm ci`, `npm run build`, `npm test`, `npm run lint` and `npm run typecheck` pass in `app/`.

## 12. Required tests

Run from `app/`; paste actual output into the PR.

- Vitest: `entity_month` parsing (valid record, unknown verdict rejected, missing field rejected, `null` kept as `null`); diverging scale centred at 100 (100 is the neutral colour, values below and above differ, `null` is "no data"); sequential scale; every `verdict` has an icon and label; year/month grid builder (outside-record months, a missing month inside the record); selection reducer for the new entity types and the value mode; table view lists the same values as the calendar.
- Component smoke tests: calendar, legend, table view and each state in §8 item 7, with SYNTHETIC objects defined inside the test files.
- Manual (reported honestly, including what was not done): keyboard-only walkthrough, colour-blindness simulation, contrast check, and screenshots of each state with the synthetic banner visible, run against the API serving `data/fixtures/v0.1.0` (SYNTHETIC).

## 13. Documentation updates

- `docs/TASK_TRACKER.md`: the T-032 row only (status, branch, PR link).
- `app/README.md`: folder map.
- `docs/RISKS_AND_LIMITATIONS.md`: any limitation found, in the same PR.
- `docs/HANDOFF.md` and `docs/PROGRESS_LOG.md`: a PR note asking the Lead to update them.

## 14. Git branch and PR instructions

- Branch: `frontend/T-032-calendar`, created from the latest `main`.
- First commit: this prompt file.
- Open a DRAFT PR early; title "T-032: Calendar (years × months; % of normal / activity)"; fill in `.github/pull_request_template.md` with the real summary, changed files and results.
- Mark Ready for review only when §11 and §12 are satisfied.
- Never merge; wait for the Project Lead.
- Commit with your own Git identity; no AI names or attribution (D-020).

## 15. Out-of-scope or blocking issues

Open questions for the Lead. None is decided here. Suggested defaults are what I will do if the Lead does not answer.

1. **Assignment is not on `main` yet.** PR #19 assigns T-032 but is open.
2. **Scope against T-033.** Default: T-032 shows the harmonized data in its two value modes (% of normal and Activity from `estimate`). Switching the calendar and the map between raw and harmonized is T-033. Confirm.
3. **Which area the calendar shows.** The series API serves `COUNTRY`, `CONTINENT` and `GLOBAL` only, and area selection UI is T-035. Default: the calendar shows the selected country (from the map click) or, when nothing is selected, `GLOBAL`. If a cell is selected, it says the calendar is available for countries, continents and the world, and keeps the last area. A country the API does not know shows "Area not found". Confirm, or specify.
4. **Chart type.** The stack and the workstream prompt name ECharts for the calendar heatmap, which is a canvas and not keyboard-navigable; the table view covers keyboard and screen-reader use. Default: ECharts heatmap plus the table view. Would you prefer a plain HTML grid of buttons instead?
5. **Diverging ramp range.** `pct_of_normal` has no upper bound (the fixtures contain values far above 200%). Default: a continuous ramp centred on 100%, clamped for colour at 0% and 200%, with the legend saying so ("200% or more"); tooltips always show the true value. This is a display choice and implies no scientific threshold. Confirm the cap, or prefer a different treatment.
6. **Two encodings in one cell.** In % of normal mode, colour shows `pct_of_normal` and the icon shows the verdict; in Activity mode, colour shows `estimate` and the icon still shows the verdict. Confirm.
7. **Provisional months.** Default: a marker in the cell, a legend entry, and a note in the tooltip for months in `metadata.provisional_months` or with `data_level` of `NRT` or `MIXED`.
8. **Vite dev proxy.** The Lead chose a Vite dev proxy for `/api` instead of CORS (T-034 review). That is a one-line change in `app/vite.config.ts`, not yet made. Default: add it in this PR, since the map and the calendar both need the API during development and neither works against a running API without it. Confirm.
9. **Click behaviour.** The evidence panel is T-036. Default: clicking a cell sets the selected month only. Confirm.
