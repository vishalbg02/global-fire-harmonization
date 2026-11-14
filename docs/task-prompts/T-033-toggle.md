# Task prompt: T-033 Raw vs harmonized toggle

> Prepared for: Member 3 · Date: 2026-11-14 · Based on main @ 632f512
> Source of truth: docs/TASK_TRACKER.md row T-033. This prompt adds no scope beyond it.
> **Assignment status:** the Lead assigns T-033 in PR #19 ("Assign T-032 and T-033 to Member 3"), open and not yet merged at the time of writing. The Lead's text there: "T-033 (raw vs harmonized toggle): ASSIGNED, to start after T-032 since it depends on it."
> **Dependency status:** the T-032 calendar code is on `main` (PR #20, merged). The tracker row for T-032 still reads `TODO` on `main`, because the Lead moved that bookkeeping into PR #19 (PR #22 was reverted by PR #23). This prompt treats the code as the dependency and leaves the tracker to the Lead.

## 1. Project context

The team is building a global web platform for the NASA Space Apps Challenge 2026, "Harmonization of MODIS and VIIRS Hot Spots" (Many Witnesses + Witness Stand, global scope, D-002/D-003). Member 2's pipeline produces monthly harmonized products; Member 3 builds the API and web app around them (`docs/PROJECT_PLAN.md`). T-030 (skeleton), T-031 (map), T-032 (calendar) and T-034 (API) are merged. T-033 adds the control behind the demo moment judges must see: flip **raw to harmonized** and watch the artificial jumps when satellites join or leave disappear, while real extreme events remain (workstream prompt §2).

## 2. Task objective

When the task is done, one control switches both the calendar and the map between **raw** and **harmonized** activity, on the **same colour scale**, so that the step changes in the raw view (for example around 2012 and 2018) are visible and can be compared with the harmonized view. The control does not compute anything: raw values are the stored `raw_combined_cell_days`, harmonized values are the stored `estimate`. Because the contract has no raw baseline, **% of normal exists only for harmonized data**: in % of normal mode the raw option is disabled and explains why. The app never computes a raw baseline.

## 3. Assigned responsibility

- Task ID / priority: T-033 / P0
- Owner: Member 3 (Application Development & UI)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-032 (code merged; see the dependency note above).

## 4. Relevant files and directories

- Read: `CLAUDE.md`, `docs/TASK_TRACKER.md`, `docs/TEAM_WORKFLOW.md`, `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACT.md` (§3, §4), `docs/TECH_STACK.md` (§7), `docs/DECISION_LOG.md`, `docs/SCIENTIFIC_METHODOLOGY.md` (to word things correctly, not to compute), `docs/prompts/MEMBER_3_APPLICATION_PROMPT.md` (§0, §2, §6, §8, §10, §12, §17, §18, §19), `app/README.md`
- Create/modify (nothing else; see §15 for items awaiting the Lead):
  - `app/src/state/selection.ts` (the shared raw/harmonized choice)
  - `app/src/components/calendar/` (`scales.ts`, `CalendarLegend.tsx`, `CalendarPanel.tsx`, `CalendarTable.tsx`, `chartOption.ts`, `text.ts`, `ValueModeSelector.tsx` as needed)
  - `app/src/components/map/` (`LayerSelector.tsx`, `Legend.tsx`, `scale.ts` as needed)
  - `app/src/components/common/` (a toggle control that supports a disabled option with a visible explanation)
  - `app/src/content/` (toggle labels and the explanation text)
  - `app/src/App.tsx`, `app/src/index.css`
  - new and existing `*.test.ts(x)` files under `app/src/`
  - `app/README.md` (folder map, if it changes)
  - `docs/task-prompts/T-033-toggle.md` (this file)
  - `docs/TASK_TRACKER.md` (the T-033 row only)

## 5. Approved technologies

From `docs/TECH_STACK.md` §7 (D-008). Already installed and pinned in `app/package-lock.json`: React 19.3.1, Vite 8.3.8, TypeScript 7.0.2 (strict), MapLibre GL JS 6.18.0, deck.gl 9.4.1 modules, Apache ECharts 6.1.0, TanStack Query 5.107.1, Vitest 5.1.0. Nothing outside this list may be added without a new Lead decision.

## 6. Architecture and data contract

- Component: web app (`docs/ARCHITECTURE.md` §2). It talks only to the API.
- Contract `0.1.0` (D-016):
  - raw: `raw_combined_cell_days`, "naive raw sum across all operating witnesses (for the raw view)" (§3), present in both `cell_month_harmonized` and `entity_month` (§4);
  - harmonized: `estimate`, with `ci90_low` and `ci90_high`, on the Aqua-equivalent scale (§3);
  - there is **no** raw baseline, raw percentile or raw verdict.
- Endpoints (as built in T-034, bare payloads): `GET /api/map` (one record per cell, all fields for every `layer` value) and `GET /api/series`. The raw and harmonized values arrive in the same records, so switching needs no new API call. The API is not changed.

## 7. Inputs

- The merged API (T-034) serving the T-010 SYNTHETIC fixtures in development (Vite dev proxy, `app/README.md`).
- Test data: tiny `SYNTHETIC` objects inside test files only. Nothing in `data/fixtures/` is edited.

## 8. Expected outputs

1. A raw/harmonized control, visible above the map and the calendar, whose state is shared: switching it changes **both** views at once.
2. Calendar, Activity mode: harmonized colours by `estimate`; raw colours by `raw_combined_cell_days`. Both on **one colour scale per area**, scaled to the largest value across both series, so switching never rescales. The legend states what is shown and the units for each source.
3. Map: the cell layer shows `raw_combined_cell_days` or `estimate` on the same single scale it already shares (T-031), following the same control.
4. % of normal mode: the raw option is **disabled**, with a visible explanation that % of normal needs a baseline that exists only for harmonized data. The explanation must be available to keyboard and screen-reader users (not a hover-only tooltip).
5. Raw mode never shows `pct_of_normal`, `p_*`, interval, baseline or any value derived from them as if it were raw. Verdict icons and probabilities belong to the harmonized estimate (see §15).
6. Wording that keeps raw and harmonized distinct: raw is "raw combined count, all operating satellites", harmonized is "harmonized, Aqua-equivalent". "Satellite-detected fire activity" and "fire-active cell-days", never "number of fires".
7. Tooltips, the table view and accessible labels follow the control, so every view says which source it shows.
8. All existing behaviour, states and the synthetic banner are unchanged.

## 9. Implementation requirements

1. **No science.** Raw and harmonized values are displayed exactly as stored. No raw baseline, percentile, probability, normalisation or rescaling to make the two comparable is computed in the app; "the same scale" means one shared colour domain over the two stored value sets, not a conversion of either.
2. **Contract fidelity.** Types and parsers are unchanged; unknown enum values and missing fields still surface as errors.
3. **`null` is never zero.** `raw_combined_cell_days` is a non-null integer in the contract, and a real `0` is a value; `estimate` can be `null` and shows as "no data".
4. **Accessibility:** WCAG 2.1 AA contrast, visible focus, a keyboard-operable control, the disabled option explained in text (use `aria-disabled` plus visible helper text rather than relying on a tooltip), no information by colour alone, `prefers-reduced-motion` respected.
5. TypeScript strict; code consumes only the documented contract.

## 10. Constraints: do not modify

- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify".
- Do not touch `pipeline/`, `data/` or `api/`.
- Do not add the per-witness chart, the satellite timeline or an explanation of why raw counts jump (T-037), the evidence panel (T-036) or area selection (T-035).
- No secrets, no `.env` files, no large files, no direct pushes to `main`, no self-merge.
- No AI tool names or attribution in commits, PR text, branch names, code comments or metadata (D-020).
- Do not mark anything validated that has not run.

## 11. Acceptance criteria

From the tracker: **"Switches calendar and map."** Made measurable:

1. One control switches the calendar and the map between raw and harmonized together.
2. In Activity mode, calendar and map use one shared colour scale for raw and harmonized: the colour of a given value does not depend on the source, and switching never rescales (tested).
3. In % of normal mode the raw option is disabled, the reason is shown in text, and it is reachable by keyboard and screen reader (tested).
4. Raw mode shows `raw_combined_cell_days` as stored, harmonized shows `estimate` as stored; `null` shows "no data" and a real zero stays a value (tested).
5. No raw baseline or raw verdict is computed or shown (reviewable in the diff).
6. Tooltips, the table view and the legend follow the control and name the source and its units.
7. `npm ci`, `npm run build`, `npm test`, `npm run lint` and `npm run typecheck` pass in `app/`.

## 12. Required tests

Run from `app/`; paste actual output into the PR.

- Vitest: the shared state (raw/harmonized choice, default, interaction with the value mode); the shared colour domain (the same value gets the same colour in either source; the maximum is taken over both sources); raw value selection (`raw_combined_cell_days` for raw, `estimate` for harmonized; `null` and zero handled); the raw option disabled in % of normal mode with its explanation present in the markup; legend and tooltip text name the source and the units; the table view follows the control; the map's value and colour helpers follow the control.
- Component smoke tests with SYNTHETIC objects defined inside test files.
- Manual (reported honestly, including what was not done): flip the control on the calendar and the map against the API serving `data/fixtures/v0.1.0`, a keyboard-only pass through the control and its disabled state, and screenshots of both sources with the synthetic banner visible.

## 13. Documentation updates

- `docs/TASK_TRACKER.md`: the T-033 row only (status, branch, PR link).
- `app/README.md`: folder map, if it changes.
- `docs/RISKS_AND_LIMITATIONS.md`: any limitation found, in the same PR.
- `docs/HANDOFF.md` and `docs/PROGRESS_LOG.md`: a PR note asking the Lead to update them.

## 14. Git branch and PR instructions

- Branch: `frontend/T-033-toggle`, created from the latest `main`.
- First commit: this prompt file.
- Open a DRAFT PR early; title "T-033: Raw vs harmonized toggle"; fill in `.github/pull_request_template.md` with the real summary, changed files and results.
- Mark Ready for review only when §11 and §12 are satisfied.
- Never merge; wait for the Project Lead.
- Commit with your own Git identity; no AI names or attribution (D-020).

## 15. Out-of-scope or blocking issues

Open questions for the Lead. None is decided here. Suggested defaults are what I will do if the Lead does not answer.

1. **Assignment and tracker.** PR #19 assigns T-033 but is open, and the T-032 row still reads `TODO` on `main` (PR #22 was reverted). I will start on the strength of the Lead's PR text and update only my T-033 row after the Lead's bookkeeping lands.
2. **How the control relates to the map's three layers.** T-031 gave the map a Verdict / Raw / Harmonized selector, and a verdict exists only for harmonized data. Default: a single shared **Raw / Harmonized** control drives both views, and the map's selector becomes **Verdict / Activity**, where Activity follows the shared control (choosing Raw while on Verdict switches the map to Activity). The Verdict layer is always harmonized. Alternative: keep the map's three-way selector and link its Raw and Harmonized options to the same shared state. Which do you prefer?
3. **Where the control sits.** Default: one control in the controls bar above the map, applying to the calendar below, with the calendar's value-mode control (% of normal / Activity) unchanged.
4. **Disabled raw option in % of normal mode.** Per the workstream prompt §8, the raw option is disabled in that mode. Default: it stays visible but disabled (`aria-disabled`), with a visible one-sentence explanation. To see raw, the user first chooses Activity. Alternative: choosing Raw while in % mode automatically switches the calendar to Activity. Confirm the first.
5. **Verdict icons in raw mode.** Verdicts, probabilities and intervals belong to the harmonized estimate, and showing them on raw colours could mislead. Default: in raw mode the calendar and map show no verdict icons, and tooltips show the raw value only, labelled as not harmonized. Confirm.
6. **Wording of the raw source.** The contract calls `raw_combined_cell_days` a "naive raw sum across all operating witnesses". Default legend text: "Raw combined count, all operating satellites (fire-active cell-days, not harmonized)" versus "Harmonized (fire-active cell-days, Aqua-equivalent)". The science wording needs the Lead's approval; please edit freely.
7. **One-sentence explanation of why raw jumps.** The workstream prompt §12 asks for it under T-037. Default: not included in T-033, only the labels above. Should T-033 add a short caption near the control (for example, "Raw counts change when satellites join or leave; harmonized values adjust for this")? If yes, please supply or approve the exact text.
8. **Shared scale across sources on the calendar.** Default: the maximum is taken over both the raw and the harmonized values of the displayed area, so a raw view is never rescaled when toggling. Confirm.
