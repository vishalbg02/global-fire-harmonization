# Task prompt: T-038 CSV export

> Prepared for: Member 3 · Date: 2026-11-14 · Based on main @ 6eb351d
> Source of truth: docs/TASK_TRACKER.md row T-038. This prompt adds no scope beyond it.
> **Assignment status:** the Lead assigns T-038 (with T-035, T-036, T-037 and T-040) in PR #26. T-035, T-036, T-037 and T-040 are merged; this is the last task of that batch. The Lead marks each row in that PR when its own PR merges, so this task does not edit the tracker (see §13).

## 1. Project context

The team is building a global web platform for the NASA Space Apps Challenge 2026, "Harmonization of MODIS and VIIRS Hot Spots" (Many Witnesses + Witness Stand, global scope, D-002/D-003). Member 2's pipeline produces monthly harmonized products; Member 3 builds the API and web app around them (D-015: Member 3 owns the API). The challenge asks for a way to download the data. T-038 adds it: the monthly series of the selected area as a CSV file, with the uncertainty, the verdict and the provenance a reader needs to cite it correctly.

## 2. Task objective

When the task is done, `GET /api/export.csv` returns the monthly series of one preset area (`entity_type` and `entity_id`) or of a custom rectangle (`bbox`) as a CSV file, and the web app has a button that downloads it for the currently selected area. The file starts with `#` comment lines giving the method version, the contract version, the data snapshot date, the synthetic flag and the citation. Each row is one month, with the `entity_month` fields and the per-witness raw counts expanded into `raw_<witness>` columns. Raw hotspot points are not exported (too large); the app links to NASA FIRMS for them. The file name is `fire-harmonization_<entity_type>_<entity_id>_<method_version>.csv`, with the prefix `SYNTHETIC_` when the products are synthetic.

## 3. Assigned responsibility

- Task ID / priority: T-038 / P0
- Owner: Member 3 (Application Development & UI)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-034 (merged). A custom rectangle needs Member 2's `harmonize_area()`, which is not delivered (see §15, item 5).

## 4. Relevant files and directories

- Read: `CLAUDE.md`, `docs/TASK_TRACKER.md`, `docs/TEAM_WORKFLOW.md`, `docs/ARCHITECTURE.md` (§4 export flow, §5), `docs/DATA_CONTRACT.md` (§4, §7), `docs/TECH_STACK.md` (§7), `docs/DECISION_LOG.md`, `docs/prompts/MEMBER_3_APPLICATION_PROMPT.md` (§0, §14, §17, §19, §S.5), `api/README.md`, `app/README.md`, `README.md` (the data acknowledgement)
- Create/modify (nothing else; see §15 for items awaiting the Lead):
  - `api/fire_api/export.py` (new): building the CSV text and the file name
  - `api/fire_api/main.py`: the `GET /api/export.csv` route
  - `api/tests/` (new and extended): endpoint and unit tests
  - `api/README.md`: the endpoint table and notes
  - `app/src/components/export/` (new): the download button, its states and the FIRMS link
  - `app/src/api/client.ts`: the download request
  - `app/src/App.tsx`, `app/src/index.css`: place the button
  - new and existing `*.test.ts(x)` files under `app/src/`
  - `app/README.md` (folder map)
  - `docs/RISKS_AND_LIMITATIONS.md` (if a limitation is found)
  - `docs/task-prompts/T-038-csv-export.md` (this file)

## 5. Approved technologies

From `docs/TECH_STACK.md` §7 (D-008). API: Python 3.14 (the existing virtual environment `api/.venv`), FastAPI 0.162.7, DuckDB 2.0.0, Pydantic 2.14.3, pytest 9.2.0, ruff 0.17.5, pinned in `api/requirements.txt`. The CSV is written with Python's standard `csv` module. Web app: React 19.3.1, TypeScript 7.0.2 (strict), TanStack Query 5.107.1, Vitest 5.1.0. Nothing outside the list may be added without a new Lead decision; no new package is needed.

## 6. Architecture and data contract

- Components: API and web app (`docs/ARCHITECTURE.md` §2). The web app talks only to the API.
- Contract `0.1.0` (D-016), product `entity_month` (§4): `entity_type`, `entity_id`, `entity_name`, `year`, `month`, `estimate`, `ci90_low`, `ci90_high`, `sd`, `raw_combined_cell_days`, `witnesses_used`, `n_witnesses`, `disagreement_scale`, `baseline_median`, `baseline_p25`, `baseline_p75`, `pct_of_normal`, `p_above`, `p_below`, `p_within`, `verdict`, `reason_codes`, `data_level`, `method_version`, `n_cells`, and `raw_by_witness` (a JSON string of witness to raw cell-days). Header values come from `metadata.json` (§7): `method_version`, `contract_version`, `synthetic`, `data_snapshot` (`zips_downloaded`, `api_pulled`), `citation`.
- Endpoint (workstream prompt §S.5 and `docs/ARCHITECTURE.md` §5): `GET /api/export.csv?entity_type=&entity_id=` (or `bbox=`). The series come from the same reader the series endpoints use (T-034). Errors keep the conventions of T-034: bare payloads for data, FastAPI's default error body, `400` invalid parameters, `404` unknown entity, `422` invalid custom area, `503` products or the harmonization function unavailable.
- No contract change and no change to any existing endpoint.

## 7. Inputs

- The products read by the API through `PRODUCTS_DIR` (the SYNTHETIC fixtures `data/fixtures/v0.1.0` in development).
- Test data: tiny `SYNTHETIC` products built inside the test files (as in T-034), plus the T-010 fixtures when present. Nothing in `data/fixtures/` is edited.

## 8. Expected outputs

**API**

1. `GET /api/export.csv?entity_type=COUNTRY|CONTINENT|GLOBAL&entity_id=` and `GET /api/export.csv?bbox=W,S,E,N` return `text/csv; charset=utf-8` with a `Content-Disposition: attachment; filename="..."` header carrying the file name defined in §2.
2. The body starts with `#` comment lines: the area, `method_version`, `contract_version`, the data snapshot dates, `synthetic` (`true` or `false`), the citation and the data acknowledgement, a statement that raw hotspot points are not included, and a statement that the file includes uncertainty and verdict fields. A SYNTHETIC export also says so in plain words ("SYNTHETIC DATA, not NASA observations").
3. Then one header row and one row per month, ordered by year then month. Columns: the `entity_month` fields in the order above, with `raw_by_witness` expanded into one `raw_<witness>` column per witness (see §15, item 3). `null` is an empty cell, never `0`; a real zero is `0`. Lists are joined with a separator (see §15, item 4).
4. Values containing commas, quotes or newlines are quoted correctly (standard CSV).
5. A custom rectangle (`bbox`) takes its series from `harmonize_area()` as the series endpoint does, with the same `422` and `503` behaviour.

**Web app**

6. A "Download CSV" button for the currently selected area (a country, a continent, the world or a custom rectangle). It states that the file includes uncertainty and verdict fields, and links to NASA FIRMS for the raw hotspot points.
7. The download shows its state (downloading, done, or an error with the server's message and a retry), never a silent failure, and names the file as the server says.

## 9. Implementation requirements

1. **No science.** The export writes stored values exactly: no rounding beyond what the products hold, no conversion, no recomputation, no filling of gaps.
2. **Contract fidelity.** Rows are validated through the existing models before writing; a stored value that breaks the contract is reported as `503`, never written as a guess.
3. **Provenance.** The header lines come from `metadata.json`; nothing in them is invented. If `metadata.json` is unavailable the export fails with `503` rather than writing a file without a citation.
4. **Safe writing.** CSV is written with the `csv` module (quoting handled), and comment lines never contain a line break from a stored value. A cell that starts with `=`, `+`, `-`, `@` or a tab is treated as in §15, item 7.
5. **Accessibility (web app):** the button is a real button, keyboard-operable, with visible focus; its status is announced (`role="status"` or `role="alert"`); nothing relies on colour alone.
6. Python: type hints and ruff-clean code (`CLAUDE.md`). TypeScript strict.

## 10. Constraints: do not modify

- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify".
- Do not touch `pipeline/`, `data/`. Do not change any existing endpoint or model.
- No secrets, no `.env` files, no large files, no direct pushes to `main`, no self-merge.
- No AI tool names or attribution in commits, PR text, branch names, code comments, the CSV header lines or metadata (D-020).
- Do not mark anything validated that has not run.

## 11. Acceptance criteria

From the tracker: **"Header with method version, snapshot date, citation."** Made measurable:

1. The CSV starts with `#` lines containing the method version, the contract version, the data snapshot date(s), the synthetic flag and the citation, taken from `metadata.json` (tested).
2. The rows are the area's monthly series in order, with every `entity_month` field and the `raw_<witness>` columns; `null` is an empty cell and a real zero stays `0` (tested).
3. The file name follows `fire-harmonization_<entity_type>_<entity_id>_<method_version>.csv`, with the `SYNTHETIC_` prefix for synthetic products (tested), and is sent in `Content-Disposition`.
4. The `400`, `404`, `422` and `503` cases return the right status (tested); a custom rectangle calls `harmonize_area()` (mocked) and does not reimplement it.
5. The web app downloads the file for the selected area, shows the uncertainty and verdict note and the FIRMS link, and shows its states (tested; checked in the browser against the API serving the fixtures).
6. No raw hotspot points are exported (the columns are the monthly fields only).
7. `pytest` and `ruff check` pass in `api/`; `npm ci`, `npm run build`, `npm test`, `npm run lint` and `npm run typecheck` pass in `app/`.

## 12. Required tests

- API (`api/`, Python 3.14 virtual environment): header lines (each required line present and correct, from the metadata); the header row and column order; the rows for a preset area against the SYNTHETIC products (order, `null` as empty, zero kept, `raw_<witness>` expansion for a witness present and absent, lists joined); quoting of a name with a comma or a quote; the file name (plain, with the `SYNTHETIC_` prefix, for a custom box); `Content-Type` and `Content-Disposition`; `400` (missing or invalid parameters, both an entity and a box, neither), `404`, `422`, `503` (products missing, `metadata.json` missing, harmonization unavailable); a custom box calling a mocked `harmonize_area()`; a stored value that breaks the contract reported as `503`; the T-010 fixtures (every row validates, row count equals the series length).
- Web app (`app/`): the download request and its errors (`404`, `422`, `503` with the server's message, network failure); reading the file name from `Content-Disposition`; the button and its states; the uncertainty and verdict note; the FIRMS link.
- Manual (reported honestly, including what was not done): download for a country, a continent, the world and a custom box (against the real API, expecting `503` for the box, and against a throwaway local stand-in for `harmonize_area()` outside the repo, labelled SYNTHETIC); open the file in a spreadsheet program and a text editor; a keyboard-only pass; screenshots with the synthetic banner visible.

## 13. Documentation updates

- `docs/TASK_TRACKER.md`: **not edited**. The Lead marks the row in PR #26 when this PR merges.
- `api/README.md`: the endpoint table and the notes on the format. `app/README.md`: folder map.
- `docs/RISKS_AND_LIMITATIONS.md`: any limitation found, in the same PR.
- `docs/HANDOFF.md` and `docs/PROGRESS_LOG.md`: a PR note asking the Lead to update them.

## 14. Git branch and PR instructions

- Branch: `api/T-038-csv-export`, created from the latest `main`.
- First commit: this prompt file.
- Open a DRAFT PR early; title "T-038: CSV export"; fill in `.github/pull_request_template.md` with the real summary, changed files and results.
- Mark Ready for review only when §11 and §12 are satisfied.
- Never merge; wait for the Project Lead.
- Commit with your own Git identity; no AI names or attribution (D-020).

## 15. Out-of-scope or blocking issues

Open questions for the Lead. None is decided here. Suggested defaults are what I will do if the Lead does not answer.

1. **Assignment and tracker.** PR #26 assigns T-038. I will start on the strength of the Lead's PR text and not edit the tracker.
2. **Who names the file.** The workstream prompt gives the file name rule and lists "file-name generation" among the web app's tests, but a server can also name it. Default: the API builds the name once and sends it in `Content-Disposition`; the web app reads it from that header and falls back to a name it builds by the same rule only if the header is missing. One rule, two places to keep in step, so both are tested. Alternative: the web app alone names the file. Which?
3. **Which `raw_<witness>` columns.** Default: always all five (`raw_AQUA_MODIS`, `raw_TERRA_MODIS`, `raw_SNPP_VIIRS`, `raw_NOAA20_VIIRS`, `raw_NOAA21_VIIRS`) in contract order, empty where a witness did not contribute, so every file has the same columns. Alternative: only the witnesses present in that series.
4. **List separator and other format choices.** `witnesses_used` and `reason_codes` are lists. Default: join with `;` (for example `AQUA_MODIS;SNPP_VIIRS`); comma as the field separator; UTF-8 without a byte-order mark; line endings `\r\n` (the `csv` module default); `null` as an empty cell. Note that Excel may need "import as UTF-8" for non-ASCII names. Confirm, or specify.
5. **A custom rectangle before `harmonize_area()` exists.** `pipeline/` still has no such function, so `bbox=` answers `503` today, as the series endpoint does. Default: build and test it against a mock and a local stand-in, show the server's message in the app, and say plainly that the real function has not been exercised. Confirm.
6. **Query parameters for a custom box.** Default: `GET /api/export.csv?bbox=W,S,E,N` (comma-separated, the same order and checks as `POST /api/series/custom`), used instead of `entity_type` and `entity_id`; giving both, or neither, is a `400`. The entity name in the file is "Custom area" and the id is the rounded `custom_w..._s..._e..._n...` form the app already uses. Confirm.
7. **Spreadsheet formula injection.** A cell that begins with `=`, `+`, `-` or `@` can run as a formula in a spreadsheet program. The only free-text fields are `entity_name` and `method_version`, both from our own products. Default: no change to values (the export must write stored values exactly), and a note in the header lines; a test pins that no stored value in the fixtures starts with those characters. Alternative: prefix such cells with an apostrophe. Which?
8. **Header lines.** Default: `# key: value` lines for `entity`, `method_version`, `contract_version`, `synthetic`, `data_snapshot_zips_downloaded`, `data_snapshot_api_pulled`, `citation`, the NASA FIRMS data acknowledgement (from the project `README.md`), a pointer to FIRMS for raw hotspot points, and a note that the file includes uncertainty and verdict fields. Please edit the wording, especially the acknowledgement and the citation text, which are the Lead's to approve.
9. **Where the button goes.** Default: in the area picker, under "Showing: <area>", because the export is of the selected area. Alternatives: the calendar header, or the witness panel. Which?
10. **Streaming.** `docs/ARCHITECTURE.md` says the API streams the series. A series is at most a few hundred rows, so default: build the file in memory and return it in one response. Confirm.

### Lead answers (PR #37) and how this prompt applies them

The Lead approved the defaults with these changes, which supersede the matching §15 defaults:

- **Byte-order mark:** the file is UTF-8 **with** a BOM, before the first `#` line (supersedes item 4).
- **Formula injection:** text cells beginning with `=`, `+`, `-` or `@` are prefixed with an apostrophe; numeric cells are never prefixed (supersedes item 7).
- **Header lines:** include `data_status` (SYNTHETIC or REAL), the fixed meaning line "Values are satellite-detected fire activity in fire-active cell-days (Aqua-equivalent scale); not fire counts or burned area.", the FIRMS acknowledgement, and the MODIS and VIIRS dataset DOIs copied from an official source, not written from memory (item 8).
- Other defaults (file name by the API, all five `raw_<witness>` columns, `;` list separator, `bbox=W,S,E,N`, button in the area picker, in-memory build) stand.

Added by me beyond the approved header list, for the Lead to keep or cut: an `area` line, the metadata `citation` line, the "raw hotspot points are not included" note and the uncertainty and verdict note.
