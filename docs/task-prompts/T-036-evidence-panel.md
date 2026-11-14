# Task prompt: T-036 Evidence panel (verdict, probability, reason codes in plain language)

> Prepared for: Member 3 · Date: 2026-11-14 · Based on main @ c8071b1
> Source of truth: docs/TASK_TRACKER.md row T-036. This prompt adds no scope beyond it.
> **Assignment status:** the Lead assigns T-036 (with T-035, T-037, T-038 and T-040) in PR #26 ("Assign T-035, T-036, T-037, T-038, T-040 to Member 3"), open and not yet merged at the time of writing. The Lead's text: "All five depend only on T-034 (API), which is merged." Suggested order: T-036 first. Each row is marked `MERGED` by the Lead when its PR merges, so this task does not edit the tracker (see §13).

## 1. Project context

The team is building a global web platform for the NASA Space Apps Challenge 2026, "Harmonization of MODIS and VIIRS Hot Spots" (Many Witnesses + Witness Stand, global scope, D-002/D-003). Member 2's pipeline produces monthly harmonized products; Member 3 builds the API and web app around them (`docs/PROJECT_PLAN.md`). T-030 (skeleton), T-031 (map), T-032 (calendar), T-033 (raw/harmonized toggle) and T-034 (API) are merged. T-036 adds the evidence and uncertainty panel: for the selected area and month, why the app says what it says, in plain language, with its uncertainty. It is the second half of the demo moment: the app openly says "cannot determine" when the evidence is weak.

## 2. Task objective

When the task is done, the web app shows an evidence panel for the selected area (a country, a continent or the world) and the selected month, read from `GET /api/evidence`. It shows: the verdict with its probability; `% of normal`; the harmonized estimate with its 90% interval and units; the witnesses used, and a note when the satellites disagree; the raw contribution of each witness; every reason code as plain-language text; a provisional notice for near-real-time data; and the method and contract versions. `CANNOT_DETERMINE` is shown as a first-class result with its reasons, never as an error. Every `reason_code` in the contract has user-facing text, in `app/src/content/`, which the Lead approves.

## 3. Assigned responsibility

- Task ID / priority: T-036 / P0
- Owner: Member 3 (Application Development & UI)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-034 (merged).

## 4. Relevant files and directories

- Read: `CLAUDE.md`, `docs/TASK_TRACKER.md`, `docs/TEAM_WORKFLOW.md`, `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACT.md` (§3, §4, §7), `docs/SCIENTIFIC_METHODOLOGY.md` (to word things correctly, not to compute), `docs/TECH_STACK.md` (§7), `docs/DECISION_LOG.md`, `docs/prompts/MEMBER_3_APPLICATION_PROMPT.md` (§0, §2, §10, §11, §12, §17, §18, §19, §S), `api/README.md`, `app/README.md`
- Create/modify (nothing else; see §15 for items awaiting the Lead):
  - `app/src/components/evidence/` (new): the panel and its parts
  - `app/src/content/reasonTexts.ts` (new): the plain-language reason texts (draft, awaiting Lead approval); `app/src/content/witnesses.ts` (new): witness display names
  - `app/src/api/contract.ts` and `app/src/api/client.ts`: the evidence type and parser (with `raw_by_witness` decoded to an object), and `fetchEvidence()`
  - `app/src/App.tsx`, `app/src/index.css`: place the panel in the page
  - new and existing `*.test.ts(x)` files under `app/src/`
  - `app/README.md` (folder map)
  - `docs/task-prompts/T-036-evidence-panel.md` (this file)

## 5. Approved technologies

From `docs/TECH_STACK.md` §7 (D-008). Already installed and pinned in `app/package-lock.json`: React 19.3.1, Vite 8.3.8, TypeScript 7.0.2 (strict), TanStack Query 5.107.1, Vitest 5.1.0. Nothing outside this list may be added without a new Lead decision. No chart library is needed for this task.

## 6. Architecture and data contract

- Component: web app (`docs/ARCHITECTURE.md` §2). It talks only to the API.
- Contract `0.1.0` (D-016), product `entity_month` (§4). Fields shown: `verdict`, `p_above`, `p_below`, `p_within`, `pct_of_normal`, `estimate`, `ci90_low`, `ci90_high`, `witnesses_used`, `disagreement_scale`, `raw_by_witness`, `reason_codes`, `data_level`, `method_version`, `n_cells`, `entity_name`, `year`, `month`. `contract_version` comes from `GET /api/meta` (§7), because the record does not carry it.
- Endpoint (as built in T-034, bare payloads, FastAPI's default error body): `GET /api/evidence?entity_type=&entity_id=&year=&month=` returns one `entity_month` record with `raw_by_witness` decoded into an object. The API serves `COUNTRY`, `CONTINENT` and `GLOBAL` entities (the types in `entity_month`); `CELL` and `CUSTOM` give `404`. `404` means the entity or the month is unknown.
- No raw baseline, raw verdict or interval for `% of normal` exists in the contract.

## 7. Inputs

- The merged API (T-034) serving the T-010 SYNTHETIC fixtures in development (Vite dev proxy, `app/README.md`).
- Selection state from T-032/T-033: the selected area and month.
- Test data: tiny `SYNTHETIC` objects inside test files only. Nothing in `data/fixtures/` is edited.

## 8. Expected outputs

For the selected area and month:

1. The verdict as icon and label, with its probability in whole percentages (for example "82% likely above normal"). `CANNOT_DETERMINE` shows no probability and is presented as a result, with its reasons. `NO_DETECTED_ACTIVITY` reads "No satellite-detected fire activity, and little expected here." and is never "below normal".
2. `% of normal` as stored, and the harmonized estimate with its 90% interval and units ("fire-active cell-days, Aqua-equivalent"). `null` is shown as "no data", never as zero.
3. The witnesses used, named in plain language, and, when `disagreement_scale` is greater than 1, the note "satellites disagree; uncertainty widened".
4. The raw contribution of each witness from `raw_by_witness` (fire-active cell-days, raw, not harmonized).
5. Every reason code as plain-language text from `app/src/content/reasonTexts.ts`.
6. If `data_level` is `NRT` or `MIXED`: "Provisional: may change when science-quality data arrive".
7. `method_version` and `contract_version`.
8. States from the workstream prompt §17: loading, error with retry, "Area not found" (`404`), `503` "Data are not available right now", empty selection, and the persistent synthetic banner (already provided).
9. A unit test that fails if any contract `reason_code` has no text.

## 9. Implementation requirements

1. **No science.** Values are displayed exactly as stored: no conversion, no new interval, no probability or verdict computed. In particular, no interval for `% of normal` is computed (see §15, item 4).
2. **Contract fidelity.** Types mirror the contract; unknown enum values and missing fields surface as visible errors and are never coerced.
3. **Wording.** "Satellite-detected fire activity" and "fire-active cell-days", never "number of fires". Probabilities in whole percentages, never showing more certainty than the data gives. Claims in the reason texts stay as drafted and are labelled for the Lead's approval.
4. **Accessibility:** WCAG 2.1 AA contrast, visible focus, a heading structure for screen readers, no information by colour alone, `prefers-reduced-motion` respected.
5. TypeScript strict; code consumes only the documented contract.

## 10. Constraints: do not modify

- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify".
- Do not touch `pipeline/`, `data/` or `api/`.
- Do not build the witness chart or satellite timeline (T-037), the methods and validation page (T-041), area selection (T-035) or the anomaly list (T-040).
- No secrets, no `.env` files, no large files, no direct pushes to `main`, no self-merge.
- No AI tool names or attribution in commits, PR text, branch names, code comments or metadata (D-020).
- Do not mark anything validated that has not run.

## 11. Acceptance criteria

From the tracker: **"Every reason code has user-facing text approved by M1."** Made measurable:

1. Every one of the 10 contract `reason_code` values has user-facing text, and a unit test fails if one is missing.
2. The texts are the Lead's approved wording (the drafts are used verbatim until the Lead edits or approves them; see §15, item 6).
3. For a selected area and month the panel shows the seven items in §8, from the API's evidence record, with `null` shown as "no data" and never as zero.
4. `CANNOT_DETERMINE` is shown as a result with its reasons, not as an error.
5. Loading, error with retry, "Area not found", empty selection and provisional states render.
6. No value is computed in the app (reviewable in the diff).
7. `npm ci`, `npm run build`, `npm test`, `npm run lint` and `npm run typecheck` pass in `app/`.

## 12. Required tests

Run from `app/`; paste actual output into the PR.

- Vitest: evidence parsing (valid record, `raw_by_witness` object and `null`, unknown verdict and witness rejected, missing field rejected); every reason code has text (the required guard test); every witness has a display name; verdict wording (probability in whole percentages, none for `CANNOT_DETERMINE` or `NO_DETECTED_ACTIVITY`, never "below normal" for no detections); `null` shown as "no data" and a real zero kept; the disagreement note only when the scale is above 1; the provisional notice for `NRT` and `MIXED` and not for `SP`; `fetchEvidence` builds the request and reports `404` as an `ApiError` with status 404.
- Component smoke tests for the panel and each state, with SYNTHETIC objects defined inside test files.
- Manual (reported honestly, including what was not done): the panel against the API serving `data/fixtures/v0.1.0` for a month with each verdict that the fixtures contain, a `CANNOT_DETERMINE` month, a provisional month and an unknown area; a keyboard-only pass; screenshots of each state with the synthetic banner visible.

## 13. Documentation updates

- `docs/TASK_TRACKER.md`: **not edited**. The Lead marks each row in PR #26 when its PR merges.
- `app/README.md`: folder map.
- `docs/RISKS_AND_LIMITATIONS.md`: any limitation found, in the same PR.
- `docs/HANDOFF.md` and `docs/PROGRESS_LOG.md`: a PR note asking the Lead to update them.

## 14. Git branch and PR instructions

- Branch: `frontend/T-036-evidence-panel`, created from the latest `main`.
- First commit: this prompt file.
- Open a DRAFT PR early; title "T-036: Evidence panel (verdict, probability, reason codes in plain language)"; fill in `.github/pull_request_template.md` with the real summary, changed files and results.
- Mark Ready for review only when §11 and §12 are satisfied.
- Never merge; wait for the Project Lead.
- Commit with your own Git identity; no AI names or attribution (D-020).

## 15. Out-of-scope or blocking issues

Open questions for the Lead. None is decided here. Suggested defaults are what I will do if the Lead does not answer.

1. **Assignment and tracker.** PR #26 assigns T-036 but is open. I will start on the strength of the Lead's PR text and not edit the tracker.
2. **Which entity the panel shows.** `GET /api/evidence` serves countries, continents and the world, but not cells, and a map click selects a cell. Default: the panel follows the calendar's area (the last selected country, continent or the world) and the selected month; when a cell is selected the panel keeps showing the area's evidence and says that cell-level evidence is not available. Alternative: for a selected cell, show the cell's map record (verdict, probability and reason codes, but no per-witness raw contributions). Which do you prefer?
3. **Placement and opening.** Default: an Evidence section next to the calendar, always showing the selected area and month; clicking a calendar cell sets the month and moves keyboard focus to the panel's heading, so the workstream prompt's "click a calendar cell to open the evidence panel" holds. Confirm, or specify.
4. **"% of normal with its 90% interval" cannot be shown as written.** The contract gives `pct_of_normal` with no interval, and an interval would have to be computed in the app (for example from `ci90_low`, `ci90_high` and `baseline_median`), which the workstream prompt forbids. Default: show `pct_of_normal` as stored, and the estimate with its 90% interval and units, without an interval for the percentage. Please confirm, or ask Member 2 to add a field through a contract change.
5. **The "learn more" and "validation results" links.** The workstream prompt asks for a "learn more" link per reason code to the methods page, and a link to the validation results. That page is T-041 and does not exist yet. Default: no dead links; show the texts and the versions as text now, and add the links when T-041 lands. Alternative: link the validation results to the raw `GET /api/validation` JSON in the meantime. Which?
6. **Reason-code texts need your approval.** Default: the ten drafts from the workstream prompt §11, used verbatim, in `app/src/content/reasonTexts.ts`, marked as awaiting approval in the PR. Please edit freely. In particular `DIURNAL_CAVEAT` makes a claim ("reported to happen increasingly outside satellite overpass times") that should be labelled and sourced before it is shown as fact.
7. **Showing the code next to the text.** Default: show the plain text, with the code (for example `OUTAGE`) as small secondary text for traceability. Remove if you prefer text only.
8. **Witness names.** Default: Aqua MODIS, Terra MODIS (raw only), S-NPP VIIRS, NOAA-20 VIIRS, NOAA-21 VIIRS (reserved), as in the workstream prompt §9.
9. **The raw/harmonized control (T-033).** Default: the panel is not affected by it. It always shows the harmonized verdict, probability and estimate together with the raw contribution of each witness, because the evidence needs both.
10. **"Area not found".** The workstream prompt says to offer the search, which is T-035. Default: the message plus a "Show the world" button, as in the calendar.
