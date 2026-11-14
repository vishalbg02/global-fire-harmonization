# Task prompt: T-037 Witness comparison chart + satellite timeline + outages

> Prepared for: Member 3 · Date: 2026-11-14 · Based on main @ 8295b86
> Source of truth: docs/TASK_TRACKER.md row T-037. This prompt adds no scope beyond it.
> **Assignment status:** the Lead assigns T-037 (with T-035, T-036, T-038 and T-040) in PR #26 ("Assign T-035, T-036, T-037, T-038, T-040 to Member 3"). T-035 and T-036 are merged. T-037 is next in the Lead's suggested order.

## 1. Project context

The team is building a global web platform for the NASA Space Apps Challenge 2026, "Harmonization of MODIS and VIIRS Hot Spots" (Many Witnesses + Witness Stand, global scope, D-002/D-003). Member 2's pipeline produces monthly harmonized products; Member 3 builds the API and web app around them (`docs/PROJECT_PLAN.md`). T-030 to T-036 are merged: the map, the calendar, the raw/harmonized toggle, the API, area selection and the evidence panel. T-037 adds the time-series view and the satellite timeline that make the demo's core claim visible over time, not just one month at a time: harmonized values move smoothly across satellite transitions, while the raw per-witness picture shows why.

## 2. Task objective

When the task is done, the web app shows, for the selected area (country, continent, world or custom rectangle) and its full monthly history: a time-series chart with the harmonized estimate and its 90% band, the baseline band and median, the raw combined line, and a separate line per witness from `raw_by_witness`; a static satellite timeline listing each satellite's operating dates, sourced from `docs/DATA_SOURCES.md`; a one-sentence explanation of why raw counts jump at satellite transitions while harmonized values do not; and outage months (reason code `OUTAGE`) marked on the chart.

## 3. Assigned responsibility

- Task ID / priority: T-037 / P0
- Owner: Member 3 (Application Development & UI)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-034 (merged). It uses the same series as the calendar (T-032) and area selection (T-035); no new endpoint is needed.

## 4. Relevant files and directories

- Read: `CLAUDE.md`, `docs/TASK_TRACKER.md`, `docs/TEAM_WORKFLOW.md`, `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACT.md` (§3, §4), `docs/DATA_SOURCES.md` (§4, satellite record dates), `docs/TECH_STACK.md` (§7), `docs/DECISION_LOG.md`, `docs/prompts/MEMBER_3_APPLICATION_PROMPT.md` (§0, §9, §12, §17, §18, §19, §S), `api/README.md`, `app/README.md`
- Create/modify (nothing else; see §15 for items awaiting the Lead):
  - `app/src/components/witness/` (new): the time-series chart, the satellite timeline, outage marking, legend
  - `app/src/content/witnessTimeline.ts` (new): the satellite date ranges and citation, from `docs/DATA_SOURCES.md`
  - `app/src/App.tsx`, `app/src/index.css`: place the new view
  - new and existing `*.test.ts(x)` files under `app/src/`
  - `app/README.md` (folder map)
  - `docs/task-prompts/T-037-witness-chart.md` (this file)

## 5. Approved technologies

From `docs/TECH_STACK.md` §7 (D-008). Already installed and pinned in `app/package-lock.json`: React 19.3.1, Vite 8.3.8, TypeScript 7.0.2 (strict), Apache ECharts 6.1.0, TanStack Query 5.107.1, Vitest 5.1.0. Nothing outside this list may be added without a new Lead decision.

## 6. Architecture and data contract

- Component: web app (`docs/ARCHITECTURE.md` §2). It talks only to the API.
- Contract `0.1.0` (D-016), product `entity_month` (§4). Fields used: `year`, `month`, `estimate`, `ci90_low`, `ci90_high`, `baseline_median`, `baseline_p25`, `baseline_p75`, `raw_combined_cell_days`, `raw_by_witness` (JSON string, decoded to an object), `reason_codes`, `data_level`, `witnesses_used`.
- Endpoint: `GET /api/series?entity_type=&entity_id=` (preset areas) and `POST /api/series/custom` (custom rectangle), both already used by the calendar and area selection (T-032, T-035). No API change.
- The satellite timeline (start/end dates per satellite) is **not** a contract product: it is a fixed reference fact, sourced from `docs/DATA_SOURCES.md` §4 and written into `app/src/content/`, not fetched or computed.

## 7. Inputs

- The merged API (T-034) serving the T-010 SYNTHETIC fixtures in development (Vite dev proxy, `app/README.md`).
- The series already fetched for the selected area (shared with the calendar via `useAreaSeries`, T-035); no duplicate request.
- Test data: tiny `SYNTHETIC` objects inside test files only. Nothing in `data/fixtures/` is edited.

## 8. Expected outputs

1. A time-series chart for the selected area, covering its full series (not just the selected month):
   - **Harmonized line:** `estimate`, with a shaded 90% band (`ci90_low` to `ci90_high`).
   - **Baseline band:** `baseline_p25` to `baseline_p75`, plus a `baseline_median` line.
   - **Raw combined line:** `raw_combined_cell_days`, dashed.
   - **Per-witness raw lines:** one per witness in `raw_by_witness` (decoded), each with a distinct colour **and** line style (not colour alone). Legend names: Aqua MODIS, Terra MODIS (raw only), S-NPP VIIRS, NOAA-20 VIIRS.
2. Provisional months (`data_level` not `SP`) and `AQUA_DRIFT_ERA` months are marked on the chart.
3. Outage months (reason code `OUTAGE`) are marked on the chart, distinctly from provisional/drift marks.
4. Zoom and range selection on the time axis, and a hover crosshair showing the values at that month.
5. A static satellite timeline: Terra MODIS from 1 Nov 2000 (raw only), Aqua MODIS from Jul 2002, S-NPP VIIRS 20 Jan 2012 to 2 Nov 2026, NOAA-20 VIIRS from 1 Apr 2018, NOAA-21 (from 17 Jan 2024, not used) — each dated and cited to `docs/DATA_SOURCES.md`.
6. One sentence, next to the chart or the timeline, explaining why raw counts jump when a satellite joins or leaves while harmonized values do not (the T-033 caption already exists in `app/src/content/source.ts`; reuse it rather than writing a second one — see §15, item 2).
7. States from the workstream prompt §17: loading, error with retry, empty selection, and the persistent synthetic banner (already provided).
8. `null` values (for example a null `estimate`) are gaps in the line, never zero.

## 9. Implementation requirements

1. **No science.** Every line and band is a stored value, plotted as given. No conversion, no new baseline, no interpolation across a gap.
2. **Contract fidelity.** The series type and parser already exist (T-032/T-035); this task adds no new contract type beyond decoding `raw_by_witness`, which `evidenceFromEntityMonth` already does (reuse its decoding logic or the function itself — see §15, item 3).
3. **Wording.** "Satellite-detected fire activity" and "fire-active cell-days", never "number of fires".
4. **Accessibility:** WCAG 2.1 AA contrast, an ECharts `aria` description and a text/table alternative for the chart (the calendar's table-view pattern, T-032, is the precedent), visible focus, `prefers-reduced-motion` respected (disable chart animation), no information by colour alone (every witness line needs its own dash pattern, not just its own colour).
5. TypeScript strict; code consumes only the documented contract.

## 10. Constraints: do not modify

- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify".
- Do not touch `pipeline/`, `data/` or `api/`.
- Do not build the global anomaly list (T-040) or CSV export (T-038).
- No secrets, no `.env` files, no large files, no direct pushes to `main`, no self-merge.
- No AI tool names or attribution in commits, PR text, branch names, code comments or metadata (D-020).
- Do not mark anything validated that has not run.

## 11. Acceptance criteria

From the tracker: **"Per-witness raw and converted series."** Made measurable:

1. For the selected area, the chart shows the harmonized line with its band, the baseline band and median, the raw combined dashed line, and one line per witness present in the series' `raw_by_witness` values.
2. Every witness line is distinguishable without colour (distinct dash pattern), and the legend uses the specified names.
3. Provisional, `AQUA_DRIFT_ERA` and `OUTAGE` months are each marked, and distinguishably from each other.
4. The chart supports zoom/range selection and a hover crosshair with values.
5. The satellite timeline shows each satellite's dates as specified, cited to `docs/DATA_SOURCES.md`.
6. The one-sentence jump explanation is shown.
7. A text/table alternative exists for keyboard and screen-reader users.
8. No value is computed in the app (reviewable in the diff).
9. `npm ci`, `npm run build`, `npm test`, `npm run lint` and `npm run typecheck` pass in `app/`.

## 12. Required tests

Run from `app/`; paste actual output into the PR.

- Vitest: the chart-option builder (series present for each witness in the data, dash patterns distinct, baseline band, harmonized band, `null` as a gap not zero); outage/provisional/drift marking (a month with `OUTAGE` is marked, a month without is not, and the three mark types do not collide); the satellite timeline data (every satellite has a date range and the citation); the table/text alternative shows the same values as the chart.
- Component smoke tests with SYNTHETIC objects defined inside test files.
- Manual (reported honestly, including what was not done): the chart against the API serving `data/fixtures/v0.1.0` for an area whose series includes an outage month, a drift-era month and a provisional month; a keyboard-only pass on the text alternative; screenshots with the synthetic banner visible.

## 13. Documentation updates

- `docs/TASK_TRACKER.md`: **not edited**. The Lead marks the row in PR #26 when this PR merges.
- `app/README.md`: folder map.
- `docs/RISKS_AND_LIMITATIONS.md`: any limitation found, in the same PR.
- `docs/HANDOFF.md` and `docs/PROGRESS_LOG.md`: a PR note asking the Lead to update them.

## 14. Git branch and PR instructions

- Branch: `frontend/T-037-witness-chart`, created from the latest `main`.
- First commit: this prompt file.
- Open a DRAFT PR early; title "T-037: Witness comparison chart + satellite timeline + outages"; fill in `.github/pull_request_template.md` with the real summary, changed files and results.
- Mark Ready for review only when §11 and §12 are satisfied.
- Never merge; wait for the Project Lead.
- Commit with your own Git identity; no AI names or attribution (D-020).

## 15. Out-of-scope or blocking issues

Open questions for the Lead. None is decided here. Suggested defaults are what I will do if the Lead does not answer.

1. **Assignment and tracker.** PR #26 assigns T-037. I will start on the strength of the Lead's PR text and not edit the tracker.
2. **Reusing the T-033 jump caption.** `app/src/content/source.ts` already has `JUMP_CAPTION` ("Raw counts jump when satellites join or leave; harmonized values adjust for this."), approved by the Lead for T-033. Default: reuse it here rather than write a near-duplicate sentence. Confirm, or ask for different wording for this context.
3. **Decoding `raw_by_witness` a second time.** `evidenceFromEntityMonth` (T-036) already decodes a series record's `raw_by_witness` string into an object, for one record. Default: factor the decoding into a small shared helper in `app/src/api/contract.ts` that both `evidenceFromEntityMonth` and the chart use, rather than duplicating the JSON parsing. This is a refactor of existing code, not a contract change; flagging it since it touches a file outside the usual new-file list.
4. **Where this view lives.** Default: a new section below the calendar/evidence row, for the same area (so the user does not re-pick it), always covering the area's whole series regardless of the calendar's selected month. Confirm, or specify a different placement (for example, inside the evidence panel, or a separate page/tab).
5. **Terra MODIS has no harmonized or baseline values (raw only, per the contract).** Default: the per-witness line for Terra is drawn only when Terra appears in `raw_by_witness`; it is never expected to appear in `witnesses_used`, and the chart does not treat its absence from the harmonized witnesses as an outage.
6. **Satellite timeline dates.** `docs/DATA_SOURCES.md` §4 gives verified dates (Terra 1 Nov 2000; Aqua Jul 2002; S-NPP 20 Jan 2012 to 2 Nov 2026 15:40 UTC; NOAA-20 1 Apr 2018; NOAA-21 17 Jan 2024, not used) which differ slightly in precision from the workstream prompt §12's rounder dates (for example "2012-01-20" vs "20 Jan 2012", and the prompt omits S-NPP's end date). Default: use the verified `DATA_SOURCES.md` dates and cite that document. Confirm.
7. **Zoom/range library choice.** Default: ECharts' built-in `dataZoom` component (slider and inside/scroll), already part of the approved ECharts package; no new library. Confirm.
8. **Custom-area series are empty today.** `POST /api/series/custom` returns `503` until Member 2 delivers `harmonize_area()` (T-035, D-024 risk T9). Default: for a custom area the chart shows the same "not available yet" message the calendar already shows, reusing that state; it is not a new limitation introduced here.
