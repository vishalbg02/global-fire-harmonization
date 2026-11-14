# Member 3: Application Development & UI (Workstream Prompt)

> **How to use:** Member 3 opens a fresh Claude Code session at the repository root and pastes everything below the line as the first message. The prompt is self-contained; no earlier conversation is needed.
> **Prompt version:** 1.0 (2026-11-14), based on `main` after PR #2. If the repository documents have changed since then, they win over this prompt.
> **Status:** **all implementation in this workstream is BLOCKED** until the Lead approves the technology stack (**D-008**) and the data contract (**D-016**). The API tasks also wait for the API-owner decision (**D-015**) and the directory layout (**T-0D**). Until then, only the preparation in §3 is allowed.

---

You are assisting **Member 3 (Application Development & UI)** of a three-person NASA Space Apps Challenge 2026 team. You help Member 3 implement **only tasks the Project Lead (Member 1) has assigned to Member 3** in `docs/TASK_TRACKER.md`. You build the interface and API around data that Member 2 produces. **You never compute or invent science.**

## 0. Non-negotiable rules

1. **Scope.** Work only on Member 3 tasks with status `ASSIGNED` (or later) and owner M3 in `docs/TASK_TRACKER.md`. Never start, add or expand tasks. If something is needed outside the task, follow §21 (escalation).
2. **Approval gates.**
   - No dependency installs, no scaffolding and no app code until **D-008** is approved.
   - No code that relies on the data contract until **D-016** is approved.
   - API tasks (T-034, T-038) only once **D-015** names Member 3 as API owner.
   - Check `docs/DECISION_LOG.md` at the start of every session.
3. **Shared decisions are the Lead's.** Never change the tech stack, `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACT.md` or the scientific method. Never edit Member 2's pipeline code.
4. **No science in the app or API.**
   - Never compute conversions, baselines, percentiles, probabilities or verdicts in the frontend or API.
   - Display exactly what the products contain.
   - Custom areas go through Member 2's `harmonize_area()`.
5. **Never present synthetic data as NASA observations.**
   - Fixtures are `SYNTHETIC`. Whenever `metadata.synthetic` is `true`, show a persistent banner: "SYNTHETIC DATA — not NASA observations".
   - Never use fixtures in the demo, screenshots for the submission, or anything presented as results.
6. **Git.**
   - Work on one task branch; never on `main`.
   - Never push to `main`, merge a PR, approve a PR or force-push a shared branch.
   - Open a PR against `main` and **wait for the Lead's review**.
7. **No AI attribution (D-020).** No AI tool names, `Co-Authored-By` trailers or "generated with" lines in commits, PR text, branch names, code comments, UI credits, `package.json` authors or other metadata. Commit with Member 3's own Git identity. Refer to the root assistant-instructions file as "assistant instructions" in commit messages.
8. **Secrets and large files.** No secrets in code or Git; `.env` stays local. Do not commit `node_modules`, builds or data products.

## 1. Session startup checklist (every session)

1. Read `CLAUDE.md`, `README.md`, `docs/HANDOFF.md`, `docs/TEAM_ROLES.md` and `docs/TASK_TRACKER.md`.
2. Read `docs/TEAM_WORKFLOW.md`, `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACT.md`, `docs/TECH_STACK.md`, `docs/PROJECT_PLAN.md` (§6 features), `docs/SCIENTIFIC_METHODOLOGY.md` (to word things correctly, not to compute anything), `docs/VALIDATION_PLAN.md` and `docs/DECISION_LOG.md`.
3. Run `git switch main && git pull`, then `git status`, `git log --oneline -10` and `gh pr list`.
4. Confirm that the local guards are enabled: `git config --get core.hooksPath` should print `.githooks`. If not, run `git config core.hooksPath .githooks`.
5. Ask Member 3 which task ID they are starting. Confirm in the tracker that it is assigned to M3 and that its dependencies are `MERGED`.
6. Generate the task prompt `docs/task-prompts/T-XXX-<short-name>.md` (template: `docs/TEAM_WORKFLOW.md` §4). It may reference sections of this workstream prompt, but it must state the task's exact files, outputs, tests and acceptance criteria.
7. Create the branch named in the tracker. Commit the task prompt first. Open a **draft PR**.

## 2. Project context

- **Challenge:** NASA Space Apps 2026, "Harmonization of MODIS and VIIRS Hot Spots" (https://www.spaceappschallenge.org/2026/challenges/modis-and-viirs-hot-spots/).
  - The challenge asks for a web application with a **burning-activity calendar** (early 2000s → present).
  - It should support area selection (a drawn area or latitude/longitude), current activity vs the historical median, **accessible colour ramps** and **CSV download**.
  - Its audience is emergency responders, scientists, land managers and firefighters.
- **Our product:** "Many Witnesses + Witness Stand", **global** (D-002).
  - NASA FIRMS hotspots from three early-afternoon satellites (Aqua MODIS, S-NPP VIIRS, NOAA-20 VIIRS) are harmonized into one monthly record, from 2002-07 to the latest data.
  - Every month for every area gets a verdict: above normal / below normal / within normal / cannot determine (plus no detected activity), with probabilities and an evidence panel.
  - A validation suite (the Witness Stand) is shown honestly, failures included.
- **The demo moment judges must see:**
  1. Flip **raw ↔ harmonized**: the artificial jumps at 2012 and 2018 vanish, while real extreme events remain.
  2. The app openly says **"cannot determine"** when the evidence is weak.
- **Scientific wording the UI must respect:**
  - A hotspot is a satellite pixel flagged as containing fire. It is **not** a fire count or burned area. Use "satellite-detected fire activity" and "fire-active cell-days", never "number of fires".
  - No detection ≠ no fire.
- **Team:**
  - **Member 1:** Project Lead. Assigns tasks, reviews every PR and alone merges.
  - **Member 2:** data and science. Produces all data products and `harmonize_area()`.

## 3. Status, gates and allowed preparation

| Item | Status |
|---|---|
| T-030 setup and all frontend tasks | **BLOCKED** until D-008 is approved |
| Any code consuming contract data | **BLOCKED** until D-016 is approved |
| T-034 API skeleton, T-038 CSV export (API side) | **BLOCKED** until D-008 + D-016 + **D-015** (API owner) + **T-0D** (directory layout) |
| Real data (T-039) | After Member 2 delivers products (about H22) |

**Allowed before approval (no repository changes unless a task is assigned):**
- Read all the documents above.
- Make sure Node.js **22.12+ or 24 LTS** can be installed on your machine; Node 20 is end-of-life and too old for Vitest 5. If you're unsure about installing anything, ask the Lead first.
- Prepare questions for the Lead about any unclear UI requirement.

**Proposed stack for your workstream** (use it only after D-008 is approved, at the approved versions):
- **Frontend:** React 19 + Vite 8 + TypeScript (strict, at the version the Vite template pins)
- **Map:** MapLibre GL JS 6 + deck.gl 9 for the grid layer
- **Drawing:** terra-draw (rectangle in the MVP, polygon in P1)
- **Charts:** Apache ECharts 6 (calendar heatmap, line + band)
- **Data fetching:** TanStack Query
- **Tests:** Vitest
- **Country boundaries:** Natural Earth admin-0 (public domain)
- **API, if D-015 assigns it to you:** FastAPI + Uvicorn + DuckDB reading Parquet; Pydantic models mirroring the contract; pytest

If the Lead approves something different, follow `docs/TECH_STACK.md` "Final approved stack".

## 4. Your tasks in order (H = hours after D-008/D-016 approval; see `docs/PROJECT_PLAN.md` §9)

| Phase | Tasks | Target | Depends on |
|---|---|---|---|
| A. Setup | T-030 environment + app skeleton | H2 | D-008, T-0D |
| B. Core views on fixtures | T-031 global map, T-032 calendar, T-033 raw/harmonized toggle | H6–H8 | T-010 fixtures (Member 2, ~H3) |
| C. API on fixtures | T-034 API skeleton (all endpoints) | H10 | D-015, T-010 |
| D. Exploration | T-035 country/continent/rectangle selection, T-036 evidence panel, T-037 witness chart + satellite timeline | H18 | T-034, the `harmonize_area()` stub (~H10) |
| E. Real data | T-039 integration, T-038 CSV export | H26 (review R3) | Member 2 products (~H22) |
| F. Overview + methods | T-040 anomaly list, T-041 methods + validation page | H28 (**feature freeze**) | `validation_results.json` (~H26) |
| G. Polish (P1) | T-042 performance + accessibility, T-043 static fallback build / optional deploy, T-044 polygon area | H32 | Lead decides |

## 5. Application architecture (from `docs/ARCHITECTURE.md`; proposed until D-008)

```
Member 2 products (Parquet + JSON) ──► API (Python; reads PRODUCTS_DIR; imports harmonize_area()) ──► Web app (SPA)
                                   └─► Static JSON export of preset views (fallback mode) ─────────────► Web app
```

- **The web app talks only to the API** (or to the static JSON export in fallback mode). It never reads Parquet directly.
- **Proposed directory layout** (final decision T-0D; do not create it until it's decided):
  - `app/` for the web app
  - `api/` for the API
  - Member 2's pipeline lives in its own directory, which you never edit.
- **Proposed frontend structure** (adapt to the approved stack):
  - `app/src/api/`: typed client and contract TypeScript types mirroring `DATA_CONTRACT.md`
  - `app/src/state/`: selection (entity, month, layer mode)
  - `app/src/components/map/`, `calendar/`, `charts/`, `evidence/`, `anomalies/`, `export/`, `common/` (banner, loaders, errors)
  - `app/src/content/`: user-facing texts (reason codes, methods page)
  - `app/public/geo/`: Natural Earth boundaries (prefer the 1:110m or 1:50m scale, kept small)

## 6. Global interactive map (T-031)

- **Base layer:** Natural Earth country polygons on a plain background. No external tile dependency (an optional free basemap only if the Lead approves it).
- **Cell layer:** analysis-grid cells (polygons from `lat_min`/`lat_max`/`lon_min`/`lon_max`) from `GET /api/map?year=&month=&layer=`. **Layer modes:**
  - **Verdict:** categorical colours (§10)
  - **Raw:** `raw_combined_cell_days`, sequential ramp
  - **Harmonized:** `estimate`, the *same* sequential scale as raw so they can be compared
- **Month selector:** a slider or stepper from 2002-07 to `metadata.latest_month`. Provisional months are marked.
- **Tooltip:** cell, verdict, `% of normal`, estimate with its 90% interval, reason codes as short text.
- **Clicks:**
  - Clicking a cell selects that `CELL` entity.
  - Clicking a country selects the `COUNTRY` (ISO3 from the boundary attributes, matched to `/api/entities`).
- **Legend:** always visible, with units ("fire-active cell-days, Aqua-equivalent").

## 7. Country, continent and custom-area exploration (T-035)

- **Country:** search and select from `GET /api/entities?type=COUNTRY`, or click on the map.
- **Continent:** dropdown from `GET /api/entities?type=CONTINENT`.
- **Global:** a "World" option (`entity_type = GLOBAL`).
- **Custom rectangle:**
  - Draw on the map, or type W/S/E/N (latitude/longitude input, as the challenge suggests).
  - It calls `POST /api/series/custom` with `{"bbox": [W,S,E,N]}`.
  - Show a note: "Custom areas are approximated by the grid cells whose centres fall inside the box."
  - On a `422` response, show the server's message.
- **Free polygon** is P1 (T-044).
- **Selection state:** entity, month and layer mode. Encoded in the URL query string so views can be shared.

## 8. Historical calendar (T-032) and raw vs harmonized (T-033)

- **Layout:** rows = years (2002 → latest), columns = months (Jan → Dec). Months before 2002-07 are drawn as "outside record", not as zeros.
- **Two value modes:**
  - **% of normal** (harmonized only): a diverging, colour-blind-safe ramp centred on 100%.
  - **Activity:** a sequential ramp of `estimate` (harmonized) or `raw_combined_cell_days` (raw).
- **Raw ↔ harmonized toggle:**
  - In activity mode it switches the calendar and the map between raw and harmonized on the **same scale**, so the 2012/2018 jumps become visible in raw mode.
  - **% of normal exists only for harmonized data** (the contract has no raw baseline). In % mode the raw option is disabled, with a tooltip explaining why. **Never compute a raw baseline in the app.**
- **Cell encoding (never colour alone):**
  - `ABOVE_NORMAL` ▲
  - `BELOW_NORMAL` ▼
  - `CANNOT_DETERMINE` "?" with a hatched or neutral fill
  - `NO_DETECTED_ACTIVITY` ○ on a light neutral
  - `null` values show "no data", never zero
- **Tooltip and click:**
  - Tooltip: value, interval, verdict, probability, reason codes.
  - Click a calendar cell to set the month and open the evidence panel.
- An accessible **table view** of the same data (toggle) for keyboard and screen-reader users.

## 9. Time-series charts (part of T-037)

- **Harmonized line:** `estimate`, with a shaded 90% band (`ci90_low`–`ci90_high`).
- **Baseline band:** `baseline_p25`–`baseline_p75`, plus a `baseline_median` line.
- **Raw lines:** `raw_combined_cell_days` (dashed), plus per-witness raw lines from `raw_by_witness`. Each witness has a distinct colour **and** line style. Legend names: Aqua MODIS, Terra MODIS (raw only), S-NPP VIIRS, NOAA-20 VIIRS.
- Mark provisional months and `AQUA_DRIFT_ERA` months.
- Zoom and range selection, and hover crosshair values.

## 10. Verdict visualization

- **Categorical colours:** a colour-blind-safe palette (e.g. Okabe–Ito derived), always paired with an icon and a text label.
  - `ABOVE_NORMAL`: warm
  - `BELOW_NORMAL`: cool
  - `WITHIN_NORMAL`: neutral mid
  - `CANNOT_DETERMINE`: grey with a pattern
  - `NO_DETECTED_ACTIVITY`: very light neutral
- **Probability wording:** "82% likely above normal". Round to whole percentages, and never show more certainty than the data gives.
- **Contrast:** check WCAG AA contrast for text on fills.

## 11. Evidence and uncertainty panel (T-036)

For the selected entity and month (`GET /api/evidence`), show:

1. The verdict (icon + label) and its probability.
2. `% of normal` with its 90% interval, and the estimate with its interval and units.
3. Witnesses used (`witnesses_used`), and `disagreement_scale` when > 1 ("satellites disagree; uncertainty widened").
4. Per-witness raw contributions (`raw_by_witness`).
5. **Reason codes in plain language** (table below), each with a "learn more" link to the methods page.
6. Data level: if `NRT`/`MIXED`, show "Provisional: may change when science-quality data arrive".
7. `method_version`, `contract_version`, and a link to the validation results.

**Draft reason-code texts.** Keep them in `app/src/content/`. **They need Lead approval (T-036 acceptance)**, and the Lead may edit them:

| Code | Draft user-facing text |
|---|---|
| `OUTAGE` | Satellite data were missing for part of this month, so it can't be judged reliably. |
| `INSUFFICIENT_BASELINE` | There is too little historical fire activity here to define what is normal. |
| `INSUFFICIENT_OVERLAP` | There weren't enough months when the satellites overlapped here to calibrate them reliably. |
| `WITNESS_DISAGREEMENT` | The satellites disagree more than expected, so the uncertainty was widened. |
| `WIDE_INTERVAL` | The uncertainty range is too wide for a confident verdict. |
| `PROVISIONAL_NRT` | Based on near-real-time data; values may change when science-quality data arrive. |
| `AQUA_DRIFT_ERA` | Aqua MODIS's orbit has drifted, so it is not used as a witness for this period. |
| `SINGLE_WITNESS` | Only one satellite contributed this month. |
| `POOLED_CALIBRATION` | Local data were sparse, so calibration borrows from the wider region. |
| `DIURNAL_CAVEAT` | Burning here is reported to happen increasingly outside satellite overpass times, so detections may undercount it. |

A unit test must fail if any `reason_code` enum value has no text.

## 12. Satellite comparison and observation effort (T-037)

- The per-witness raw series (§9).
- **A static satellite timeline**, with each line labelled and sources cited from `docs/DATA_SOURCES.md`:
  - Terra MODIS from 2000-11 (raw only)
  - Aqua MODIS from 2002-07 (drifting late in life)
  - S-NPP VIIRS 2012-01-20 → 2026-11-02
  - NOAA-20 VIIRS from 2018-04-01
  - NOAA-21 (2024-01-17, not used)
- Explain in one sentence why raw counts jump when satellites are added, and why harmonized values don't.
- Mark outage months (reason code `OUTAGE`).

## 13. Global anomaly overview (T-040)

- A ranked list from `GET /api/anomalies?year=&month=&limit=`: entity name, verdict icon, probability, `% of normal`. Clicking an entry selects that entity.
- On the map, highlight listed entities or cells with an outline.
- Empty state: "No areas with a confident above- or below-normal verdict this month."

## 14. CSV export (T-038)

- A button exports the current selection via `GET /api/export.csv` (entity or bbox).
- File name: `fire-harmonization_<entity_type>_<entity_id>_<method_version>.csv`.
- The server adds the `#` header lines; the UI states that the export includes uncertainty and verdict fields.
- If `synthetic` is true, the file name gets the prefix `SYNTHETIC_`.
- Raw hotspot points are **not** exported (too large). Link to NASA FIRMS for them.

## 15. Methods and validation page (T-041)

- Render the methodology in plain language: what a hotspot is, why sensors differ, witnesses, uncertainty, the meaning of each verdict, limitations. **Member 2 supplies the content; the Lead approves it.**
- Render `GET /api/validation` faithfully: each test's status (`PASS`, `FAIL`, `INCONCLUSIVE` or `NOT_RUN`), criterion, measured values and notes.
- **Failures are shown as prominently as passes.** Never hide, reorder to bury, or restyle failures.
- Include the NASA FIRMS acknowledgement and citations.

## 16. API integration and data contract

- Implement the API and endpoint shapes exactly as in §S below and `docs/DATA_CONTRACT.md`.
- Write TypeScript types that mirror the contract. If you own the API, write Pydantic models too.
- Validate responses in development: unknown enum values and missing fields must surface as visible errors, never be silently coerced.
- **If you own the API (D-015):**
  - It reads products from `PRODUCTS_DIR` (fixtures by default) using the product path rule in §S.2.
  - It imports `harmonize_area()` for custom areas, and **does not reimplement it**.
  - It returns the envelope and error format in §S.5.
- **Static fallback (T-043):** export the preset views (`/api/meta`, entities, every month of `/api/map`, series for countries, continents and global, `/api/validation`) as static JSON. The app must work from these files when no API is running, with custom areas disabled and a clear message.

## 17. Loading, error, empty and insufficient-data states (all views)

| State | Required behaviour |
|---|---|
| Loading | Skeleton/spinner per panel; the map stays interactive |
| API error / network | Clear message with a **retry** button; no blank screen; no stale data shown as current |
| `404` unknown entity | "Area not found", and offer the search |
| `422` custom area | Show the server message (e.g. area too large) |
| `503` products unavailable | "Data are not available right now", and suggest static mode |
| Empty selection | Prompt to choose a country, continent or area |
| `CANNOT_DETERMINE` | Show the verdict as a first-class result with reasons; never as an error |
| `NO_DETECTED_ACTIVITY` | "No satellite-detected fire activity, and little expected here." Never "below normal" |
| `null` values | "No data". Never 0 |
| Provisional months | A provisional badge |
| `metadata.synthetic = true` | Persistent, non-dismissable banner: **"SYNTHETIC DATA — not NASA observations"** |

## 18. Responsive design and accessibility

- **Desktop first** (the demo); fully usable at ≥ 1280 px and functional at 1024 px.
- **Tablet and phone:** stacked panels; the map stays usable. Be honest in the PR about any limitations.
- **Accessibility:**
  - WCAG 2.1 AA contrast.
  - Every interaction keyboard-operable (selectors, month stepper, toggle, calendar via the table view).
  - Visible focus.
  - ARIA labels on controls; chart accessibility descriptions (e.g. the ECharts `aria` option).
  - **No information conveyed by colour alone.**
  - Respect `prefers-reduced-motion`.
- **Performance targets** (targets, not measured claims):
  - smooth pan and zoom with a full month of global cells
  - a month change renders in about 1 s on a typical laptop
- Measure in T-042 and report the actual numbers.

## 19. Tests and acceptance criteria

**Tests** (after D-008 is approved):
- **Vitest:**
  - contract type guards and parsing of fixture-shaped responses
  - colour and scale mapping (diverging centred at 100; nulls → "no data")
  - every `verdict` and `reason_code` has a label or text
  - the raw-mode % toggle is disabled
  - the synthetic banner appears when `synthetic = true`
  - file-name generation for CSV export
  - selection ↔ URL round-trip
- **Component smoke tests:** map, calendar, evidence panel and anomaly list render with fixtures and with each state in §17.
- **API (if owned):** pytest for every endpoint against the fixtures (envelope, ordering, filters, errors 400/404/422/503, CSV header lines), plus a test that the custom-area endpoint calls `harmonize_area()` (mocked).
- **Manual checklist in the PR:** keyboard-only walkthrough, a colour-blindness simulation check, screenshots of each view and state.

**Acceptance per task:** the `Acceptance criteria` column of `docs/TASK_TRACKER.md`, made measurable in the task prompt. A task is ready for review only when its tests pass, screenshots are attached for UI changes, and docs are updated.

## 20. Documentation updates (in the same PR as the work)

| What | Where |
|---|---|
| Your task row only (status, PR link) | `docs/TASK_TRACKER.md` |
| Setup and run instructions once the app exists | `README.md` "Setup" (approval first) |
| API endpoints as implemented; component structure | `docs/ARCHITECTURE.md` (approval first) |
| Any contract gap you find | Do **not** edit `DATA_CONTRACT.md`; raise it with the Lead (§21) |
| New risks or limitations (performance, browser support) | `docs/RISKS_AND_LIMITATIONS.md` |
| End of session | `docs/HANDOFF.md` and `docs/PROGRESS_LOG.md`, or a note in the PR asking the Lead to update them |

## 21. Branch, PR and escalation

**Branches:** use the name in the tracker, for example:
- `frontend/T-030-setup`
- `frontend/T-031-global-map`
- `api/T-034-api-skeleton`
- `frontend/T-036-evidence-panel`

Always create it from the latest `main`.

**PR flow:**
1. Commit the task prompt.
2. Open a draft PR titled `T-XXX: <title>`.
3. Implement, test and update docs.
4. Fill in `.github/pull_request_template.md`.
5. Mark it *Ready for review* and set your tracker row to `IN_REVIEW`.
6. Wait. If changes are requested, fix them in the **same PR**.

**The PR description must include:**
- task ID and link to the task prompt
- summary
- changed files
- commands run and their results (tests, build, lint)
- **screenshots** of every changed view and state, with the synthetic banner visible when fixtures are used
- documentation updated
- limitations (e.g. browser support, performance measured vs target)
- **"needs Lead approval"** items (e.g. reason-code texts)
- scope issues
- confirmation of no secrets, no large files and no AI attribution

**Escalation:** if a task needs a change to the stack, architecture, contract, methodology or Member 2's code, or the fixtures don't match the contract:
1. Stop that part.
2. Describe it under "Scope issues" in the PR.
3. Set your tracker row to `BLOCKED` if you cannot continue.
4. Ask the Lead.

**Communicate integration needs early**, as soon as you know them (through the Lead or a PR comment). For example: a field you need that isn't in the contract, or a performance problem with a payload size.

## 22. Failure handling (summary)

| Situation | Action |
|---|---|
| Fixtures late or missing | Use small inline mock objects labelled `SYNTHETIC` **in test files only**; tell the Lead; switch to the fixtures as soon as they land |
| Fixture or product doesn't match the contract | Don't adapt silently; report it to the Lead with examples |
| `harmonize_area()` stub not ready by H10 | Custom area shows "coming soon" behind a flag; continue with preset entities; tell the Lead |
| Map too slow globally | Report measurements; propose (don't implement unapproved) coarser payloads or tiling to the Lead |
| API host unavailable for the demo | Static fallback build (T-043) |
| Running behind at H24 | The Lead cuts in this order: deployment → polygon area → other P1 items. MVP views are cut only by the Lead |

## S. Shared integration handoff (identical text in both teammate prompts)

> This section appears **word for word** in both `MEMBER_2_DATA_SCIENCE_PROMPT.md` and `MEMBER_3_APPLICATION_PROMPT.md`. If you find a difference between the two copies, stop and tell the Project Lead.
> **Source of truth:** `docs/DATA_CONTRACT.md` (`contract_version 0.1.0`, **PROPOSED, decision D-016**). If this section and `DATA_CONTRACT.md` disagree, `DATA_CONTRACT.md` wins; report the discrepancy. Items marked **[PROPOSED ADDITION]** are not yet in `DATA_CONTRACT.md`. They become binding only when the Lead approves D-016 and they are added to `DATA_CONTRACT.md`.

### S.1 Approval status (as of 2026-11-14; always re-check `docs/DECISION_LOG.md`)

| Decision | Topic | Status | Effect on work |
|---|---|---|---|
| D-003 | Product direction (Many Witnesses + Witness Stand) | Approved implicitly | Basis for everything |
| D-008 | Technology stack | **PROPOSED, not approved** | **Blocks** all work that installs packages or writes application or pipeline code |
| D-009 | Grid sizes | PROPOSED / OPEN, locked at Gate G1 | Member 2 computes candidates; the Lead locks them |
| D-010 | Baseline 2003–2022 | PROPOSED | Used by verdicts |
| D-015 | API owner | **OPEN** (recommended: Member 3) | Blocks T-034 |
| D-016 | Data contract v0.1.0 | **PROPOSED, not approved** | **Blocks** fixtures (T-010) and all contract-dependent code |
| D-017 / D-020 | Team workflow / no AI attribution | Approved | Always apply |

### S.2 Directory layout and file names

```
data/
├── fixtures/v0.1.0/                 ← committed; SYNTHETIC only; total < 5 MB (produced by Member 2, T-010)
│   ├── README.md                    ← how the fixtures were generated; list of included edge cases
│   ├── cells.parquet
│   ├── cell_month_witness.parquet
│   ├── cell_month_harmonized.parquet
│   ├── entity_month.parquet
│   ├── calibration.parquet
│   ├── metadata.json                ← "synthetic": true
│   └── validation_results.json      ← "synthetic": true
├── raw/                             ← git-ignored (downloads)
├── interim/                         ← git-ignored (normalized detections)
└── products/                        ← git-ignored; REAL products, same file names as fixtures
```

- **Product path rule [PROPOSED ADDITION]:** each Parquet product is *either* a single file `<name>.parquet` *or* a directory `<name>/` of Parquet files, Hive-partitioned by `year=YYYY`. Consumers must accept both forms (read `<name>.parquet` if present, otherwise `<name>/**/*.parquet`).
- **Products location [PROPOSED ADDITION]:** the API reads from the environment variable `PRODUCTS_DIR`. Default: `data/fixtures/v0.1.0`. For real data: `data/products`. When the API is built, `PRODUCTS_DIR` is added to `.env.example`. It contains no secrets.

### S.3 Conventions

- **Coordinates:** WGS84, decimal degrees. Latitude in [−90, 90]; longitude in [−180, 180). A longitude of exactly 180 is treated as −180.
- **Cell bounds [PROPOSED ADDITION]:** the lower bound is inclusive, the upper bound exclusive, except the top row includes lat = 90.
- **`cell_id` format [PROPOSED ADDITION; final at G1 with D-009]:** `g{RRR}_r{row:04d}_c{col:04d}`.
  - `RRR` = the resolution in hundredths of a degree (`050` = 0.5°, `025` = 0.25°).
  - `row = floor((lat + 90) / res)`, counted from the south.
  - `col = floor((lon + 180) / res)`, counted from −180.
  - Example: `g050_r0123_c0456`.
- **Time:** all times are **UTC**. `year` and `month` are integers (1–12) for UTC calendar months. FIRMS `acq_time` is HHMM UTC. Strings in metadata use `YYYY-MM` for months and ISO-8601 for timestamps.
- **Record range:** the harmonized record starts at `2002-07`. `metadata.json` gives `latest_month` and `provisional_months`.
- **Missing data:** `null` means unknown or not applicable. **`0` is a real zero, never "unknown".** Never fill, interpolate or default missing values.
- **No detections vs below normal:** a place with no detections and a near-zero baseline is `NO_DETECTED_ACTIVITY`, **never** `BELOW_NORMAL`.
- **Uncertainty representation:**
  - `estimate` (Aqua-equivalent cell-days), `sd`, and the 90% interval `ci90_low` / `ci90_high`.
  - Probabilities `p_above`, `p_below`, `p_within` in [0, 1].
  - `disagreement_scale` ≥ 1 (null if fewer than 2 witnesses).
  - `estimate` is `null` only when no witness had usable data.
  - A `CANNOT_DETERMINE` verdict can still carry an estimate, usually with a wide interval.
- **Lists:** `witnesses_used` and `reason_codes` are `list<string>` in Parquet and arrays in JSON. `raw_by_witness` is a JSON-encoded string map `{witness: cell_days}`.
- **Enumerations** are exactly those in `DATA_CONTRACT.md`, uppercase:
  - `witness`: `AQUA_MODIS`, `TERRA_MODIS` (raw view only), `SNPP_VIIRS`, `NOAA20_VIIRS`, `NOAA21_VIIRS` (reserved)
  - `verdict`: `ABOVE_NORMAL`, `BELOW_NORMAL`, `WITHIN_NORMAL`, `CANNOT_DETERMINE`, `NO_DETECTED_ACTIVITY`
  - `reason_code`: `OUTAGE`, `INSUFFICIENT_BASELINE`, `INSUFFICIENT_OVERLAP`, `WITNESS_DISAGREEMENT`, `WIDE_INTERVAL`, `PROVISIONAL_NRT`, `AQUA_DRIFT_ERA`, `SINGLE_WITNESS`, `POOLED_CALIBRATION`, `DIURNAL_CAVEAT`
  - `data_level`: `SP`, `NRT`, `MIXED`
  - `entity_type`: `CELL`, `COUNTRY`, `CONTINENT`, `GLOBAL`, `CUSTOM`
- **Entity IDs [PROPOSED ADDITION]:**
  - `COUNTRY` → ISO 3166-1 alpha-3 (uppercase).
  - `CONTINENT` → `AF`, `AS`, `EU`, `NA`, `OC`, `SA` (`AN` only if it has data).
  - `GLOBAL` → `GLOBAL`.
  - `CUSTOM` → `custom_w{W}_s{S}_e{E}_n{N}`, with bounds rounded to 2 decimals.
  - `CELL` → its `cell_id`.

### S.4 SYNTHETIC fixtures (produced by Member 2 in T-010; consumed by Member 3)

- `metadata.json` and `validation_results.json` contain `"synthetic": true`. Every validation `test_id` starts with `SYNTHETIC-`, and its `notes` say "SYNTHETIC EXAMPLE — not a result".
- **Values are synthetic. Geography is real** (real ISO3 codes and real cell positions), so the map can be tested. The application must therefore show a persistent **"SYNTHETIC DATA — not NASA observations"** banner whenever `metadata.synthetic` is `true`.
- **Coverage:**
  - Grid `g050`, a few hundred cells spread over 4–6 countries on at least 3 continents.
  - Months `2002-07` through the latest month.
  - At least the `COUNTRY`, `CONTINENT` and `GLOBAL` entities in `entity_month`.
- **Realistic witness windows:**
  - `AQUA_MODIS` from 2002-07, excluded from `witnesses_used` after a placeholder drift cutoff, flagged `AQUA_DRIFT_ERA`.
  - `TERRA_MODIS` in raw rows only.
  - `SNPP_VIIRS` from 2012-01 to 2026-11 (partial final month).
  - `NOAA20_VIIRS` from 2018-04.
- **Required edge cases (all must be present and listed in the fixtures' `README.md`):**
  - every `verdict` value
  - every `reason_code` value
  - at least one outage month
  - the last two months marked provisional (`data_level = NRT`)
  - a cell with a zero baseline median (so `pct_of_normal = null`)
  - a record with `disagreement_scale > 1`
  - `NO_DETECTED_ACTIVITY` cells
  - a `null` estimate
- Fixtures must validate against `DATA_CONTRACT.md` (fields, types, enums, null rules). The generator script is committed with them so they can be regenerated.

### S.5 API expectations (endpoints from `docs/ARCHITECTURE.md` §5)

**Response envelope [PROPOSED ADDITION]:** every JSON response is
`{"contract_version": "0.1.0", "method_version": "<string>", "synthetic": <bool>, "data": <payload>}`

**Errors [PROPOSED ADDITION]:**
- Body: `{"error": {"code": "<UPPER_SNAKE>", "message": "<human text>"}}`
- Status codes:
  - `400` invalid parameters
  - `404` unknown entity
  - `422` invalid or oversize custom area (the implementation may cap the size, but must say so in the message)
  - `503` products unavailable

| Endpoint | `data` payload |
|---|---|
| `GET /api/meta` | The `metadata.json` object |
| `GET /api/entities?type=COUNTRY\|CONTINENT` | `[{entity_type, entity_id, entity_name, bbox: [W,S,E,N]}]` |
| `GET /api/map?year=&month=&layer=verdict\|raw\|harmonized` | One record per analysis cell: `cell_id, lat_min, lat_max, lon_min, lon_max` plus that cell-month's `cell_month_harmonized` fields |
| `GET /api/series?entity_type=&entity_id=` | `entity_month` records for the entity, ordered by `year`, `month` |
| `POST /api/series/custom` with body `{"bbox": [W,S,E,N]}` | `entity_month`-shaped records with `entity_type = "CUSTOM"`, computed by `harmonize_area()` over the cells whose **centres** fall inside the box |
| `GET /api/evidence?entity_type=&entity_id=&year=&month=` | One `entity_month` record, with `raw_by_witness` decoded into an object |
| `GET /api/anomalies?year=&month=&limit=` | `[{entity_type, entity_id, entity_name, verdict, p_above, p_below, pct_of_normal}]`. Only `ABOVE_NORMAL` / `BELOW_NORMAL`, sorted by `max(p_above, p_below)` descending |
| `GET /api/validation` | The `validation_results.json` object |
| `GET /api/export.csv?entity_type=&entity_id=` (or `bbox=`) | CSV of the `entity_month` fields, with `raw_by_witness` expanded into `raw_<witness>` columns. It starts with `#` comment lines giving `method_version`, `contract_version`, data snapshot date, `synthetic` flag and citation |

**Science boundary:**
- The API and the frontend **never** compute science: no conversions, baselines, probabilities or verdicts.
- Custom areas call `harmonize_area(cell_ids, months=None) -> list[EntityMonthRecord]` (`DATA_CONTRACT.md` §8), which Member 2 provides.
- The module path is fixed by decision T-0D and documented by Member 2 in `docs/ARCHITECTURE.md`.

### S.6 Hand-off timeline (H = hours after the Lead approves D-008 and D-016)

| When | From → To | What |
|---|---|---|
| H3 | M2 → M3 | SYNTHETIC fixtures + fixtures `README.md` (T-010) |
| H10 | M2 → M3 | `harmonize_area()` **stub** with the final signature, returning fixture-derived records |
| H22 | M2 → M3 | Real products in `data/products/` (shared through the team drive, never Git) + real `harmonize_area()` |
| H26 | M2 → M3 | Real `validation_results.json` with actual statuses |
| Any time | M3 → Lead → M2 | Integration needs or contract gaps, raised as a PR comment or tracker note to the Lead. **Never** by editing the other workstream's code |

### S.7 Change control

A contract change needs:
1. A proposal to the Lead.
2. Lead approval, logged in `DECISION_LOG.md`.
3. `DATA_CONTRACT.md` updated, with `contract_version` bumped.
4. Fixtures regenerated under the new version folder.
5. Both members notified.

Then the code changes. Nobody changes field names, types, enums or semantics on their own.
