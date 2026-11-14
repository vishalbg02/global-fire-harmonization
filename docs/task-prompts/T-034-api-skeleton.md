# Task prompt: T-034 API skeleton serving fixtures (all endpoints)

> Prepared for: Member 3 · Date: 2026-11-14 · Based on main @ 53e3c46
> Source of truth: docs/TASK_TRACKER.md row T-034. This prompt adds no scope beyond it.
> **Assignment status:** the Lead assigns T-034 in PR #12 ("Assign T-034 and T-031 to Member 3"), open and not yet merged at the time of writing. The Lead's text: "Starts from the approved contract v0.1.0 (models and routes) and serves the T-010 fixtures once they are merged."

## 1. Project context

The team is building a global web platform for the NASA Space Apps Challenge 2026, "Harmonization of MODIS and VIIRS Hot Spots" (Many Witnesses + Witness Stand, global scope, D-002/D-003). Member 2's pipeline produces monthly harmonized products; Member 3 builds the API and the web app around them (D-015: Member 3 owns the API). The web app (`app/`) talks only to this API. T-034 creates the API in `api/`, so the map (T-031) and every later view can fetch contract-shaped data (`docs/PROJECT_PLAN.md`).

## 2. Task objective

When the task is done, `api/` contains a read-only FastAPI service, run with Uvicorn, that serves the contract v0.1.0 products through the endpoints in `docs/ARCHITECTURE.md` §5, using DuckDB over Parquet and JSON files. Pydantic models mirror the contract, and every response is validated against them. The API starts from the contract (tests use tiny SYNTHETIC products built inside the test files) and switches to the T-010 fixtures once they are merged. It does no science.

## 3. Assigned responsibility

- Task ID / priority: T-034 / P0
- Owner: Member 3 (Application Development & UI)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-0D (done); T-010 (Member 2's fixtures, not merged). Per the Lead, work starts from the contract and switches to the T-010 fixtures when merged.

## 4. Relevant files and directories

- Read: `CLAUDE.md`, `docs/TASK_TRACKER.md`, `docs/TEAM_WORKFLOW.md`, `docs/ARCHITECTURE.md` (§2, §3, §5), `docs/DATA_CONTRACT.md`, `docs/TECH_STACK.md` (§3.3, §7), `docs/DECISION_LOG.md`, `docs/prompts/MEMBER_3_APPLICATION_PROMPT.md` (§0, §16, §19, §S), `.env.example`, `.gitignore`
- Create/modify (nothing else; see §15 for items awaiting the Lead):
  - `api/` (new): the FastAPI package, `requirements.txt`, tool configuration, `tests/`, `README.md`
  - `docs/task-prompts/T-034-api-skeleton.md` (this file)
  - `docs/TASK_TRACKER.md` (the T-034 row only)

## 5. Approved technologies

From `docs/TECH_STACK.md` §7 (D-008). Verified on PyPI on 2026-11-14 (local Python 3.14.7, within the approved 3.12 to 3.14 range):

- Python 3.14 (virtual environment, `python3.14 -m venv`; never the machine's default `python3`, which is 3.15.2 and out of range)
- FastAPI 0.162.7, Uvicorn 0.54.0, DuckDB 2.0.0, Pydantic 2.14.3
- pytest 9.2.0 and ruff 0.17.5 (tests and lint); httpx 0.28.1 (HTTP client, also used by FastAPI's test client)
- `pip` with a pinned `requirements.txt`

Nothing outside this list may be added without a new Lead decision.

## 6. Architecture and data contract

- Component: API (`docs/ARCHITECTURE.md` §2). Read-only. It reads Member 2's products and imports `harmonize_area()` from `pipeline/` for custom areas; it never reimplements it (single implementation of the science, §3 item 2).
- Contract `0.1.0` (D-016) products read: `cells`, `cell_month_harmonized`, `entity_month`, `validation_results.json`, `metadata.json`. `cell_month_witness` and `calibration` are not served.
- Endpoints (ARCHITECTURE §5): `GET /api/meta`, `GET /api/entities`, `GET /api/map`, `GET /api/series`, `POST /api/series/custom`, `GET /api/evidence`, `GET /api/anomalies`, `GET /api/validation`. `GET /api/export.csv` is T-038 (see §15).
- The envelope, error format, `PRODUCTS_DIR` and product path rule are [PROPOSED ADDITION] items (D-022), not binding until approved (see §15).

## 7. Inputs

- Products directory: SYNTHETIC test products built inside the test files now; T-010 fixtures later, read from `data/fixtures/v0.1.0/` (Member 2's folder; read only, never edited).
- Environment variables: the products location (name pending the Lead's decision, §15). Names only in docs; never values.

## 8. Expected outputs

1. An `api/` Python package with the FastAPI app and one route per endpoint above.
2. Pydantic models mirroring the contract: map cell record, `entity_month` record, entity list item, anomaly item, metadata, validation results; contract enums as Python enums, so unknown values fail validation.
3. A products reader using DuckDB for Parquet and plain JSON loading for `metadata.json` and `validation_results.json`; `null` stays `null` and a real zero stays `0`.
4. Parameter validation and errors: `400` invalid parameters, `404` unknown entity, `422` invalid custom area, `503` products unavailable (status codes as in the workstream prompt §S.5; body format pending §15).
5. `api/requirements.txt` with pinned versions; `api/README.md` with setup, run, test and lint commands.
6. pytest tests for every endpoint and error path.

## 9. Implementation requirements

1. **No science.** The API never computes conversions, baselines, percentiles, probabilities or verdicts. It selects, filters, joins and orders stored fields only. Anomalies are filtered to `ABOVE_NORMAL` and `BELOW_NORMAL` and sorted by `max(p_above, p_below)` descending, as specified.
2. **Contract fidelity.** Field names, types, enums and null rules come from `docs/DATA_CONTRACT.md`. Response models are declared on the routes so the framework validates every response; rows that violate the contract fail loudly and are never coerced.
3. **Custom areas** call `harmonize_area(cell_ids, months=None)` from `pipeline/` (contract §8). It does not exist yet, so the route follows the Lead's decision in §15 and never reimplements it. Cells are selected by **centre** inside the box, as specified.
4. **Series order:** by `year`, then `month`. **Evidence:** one `entity_month` record with `raw_by_witness` decoded from its JSON string to an object.
5. **Read-only.** No endpoint writes anything. No secrets. CORS only if the Lead approves it (the web app is served from a different origin in development; see §15).
6. Python: type hints and ruff-clean code (`CLAUDE.md`). Conventional Commits with the task ID.

## 10. Constraints: do not modify

- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify".
- Do not touch `pipeline/`, `data/`, or `app/` (T-031 and later tasks are separate).
- No secrets, no `.env`, no data files committed, no direct pushes to `main`, no self-merge.
- No AI tool names or attribution in commits, PR text, branch names, code comments or metadata (D-020).
- Do not mark anything validated that has not run.

## 11. Acceptance criteria

From the tracker: **"Responses validate against the contract."** Made measurable:

1. From a clean virtual environment on Python 3.14, `pip install -r api/requirements.txt` succeeds and the app starts with Uvicorn.
2. Every implemented endpoint returns a response that validates against its Pydantic model, tested against SYNTHETIC products.
3. The error cases return the right status codes: `400`, `404`, `422` and `503`.
4. `null` is preserved and never turned into zero; unknown enum values in a product fail validation.
5. No science is computed in the API (reviewable in the diff).
6. `pytest` passes and `ruff check` is clean.
7. When T-010 merges, the same endpoints serve the real fixtures. This criterion cannot be met until T-010 is merged and will be reported as not yet verified until then.

## 12. Required tests

Run from `api/` inside the Python 3.14 virtual environment; paste actual output into the PR.

- `pytest`: for each endpoint, a success case, an empty or missing case, and the error statuses; ordering of series and anomalies; `null` and zero preserved; `raw_by_witness` decoded in evidence; custom area route calls a mocked `harmonize_area` and does not reimplement it.
- `ruff check .`
- Manual: start the server and request each endpoint (reported honestly; fixtures are not available until T-010).

## 13. Documentation updates

- `docs/TASK_TRACKER.md`: the T-034 row only (status, branch, PR link).
- `api/README.md`: setup, run, test and lint instructions, and the endpoint list.
- `docs/ARCHITECTURE.md`: **not edited**; any proposed change goes in the PR for the Lead (approval first).
- Root `README.md` "Setup" and `.env.example`: **not edited**; proposed lines go in the PR for the Lead.
- `docs/HANDOFF.md` and `docs/PROGRESS_LOG.md`: a PR note asking the Lead to update them.

## 14. Git branch and PR instructions

- Branch: `api/T-034-api-skeleton`, created from the latest `main`.
- First commit: this prompt file.
- Open a DRAFT PR early; title "T-034: API skeleton serving fixtures (all endpoints)"; fill in `.github/pull_request_template.md`.
- Mark Ready for review only when §11 and §12 are satisfied (criterion 7 reported as pending T-010).
- Never merge; wait for the Project Lead.
- Commit with your own Git identity; no AI names or attribution (D-020).

## 15. Out-of-scope or blocking issues

Open questions for the Lead. None is decided here. Suggested defaults are what I will do if the Lead does not answer.

1. **Assignment is not on `main` yet.** PR #12 assigns T-034 but is open. Work starts on the strength of the Lead's PR text.
2. **Envelope and error format (D-022).** Not approved, so the default is bare payloads (as the T-031 client expects) and FastAPI's default error body `{"detail": ...}`, with the status codes above. Confirm, or approve D-022.
3. **`PRODUCTS_DIR` and the product path rule (D-022).** The API needs a way to find the products. Default: an environment variable named `PRODUCTS_DIR`, default `data/fixtures/v0.1.0`, and each Parquet product read as `<name>.parquet` if present, else `<name>/**/*.parquet`. Not binding until D-022 is approved; please confirm. May `.env.example` get the new variable?
4. **`GET /api/entities` bbox.** The workstream prompt (§S.5) says each item includes `bbox: [W,S,E,N]`, but the contract has no product with entity bounding boxes (`entity_month` has `entity_name` only; `cells` has `country_iso3` and `continent` per cell). Where should the bbox come from? Default: the envelope of the bounds of the cells assigned to that country or continent (min and max of the cell bounds; selection and arithmetic only, no science). Please confirm, or have Member 2 provide a product.
5. **`type` parameter case.** `ARCHITECTURE.md` §5 writes `country|continent` (lowercase); the contract enums and the workstream prompt use `COUNTRY|CONTINENT`. Default: accept the contract's uppercase values and reject others with `400`.
6. **`layer` parameter of `/api/map`.** The response is the same cell fields for all three layers per §S.5. Default: validate `layer` (`verdict`, `raw` or `harmonized`) and return the same payload. Is that intended?
7. **`POST /api/series/custom` before `harmonize_area()` exists.** The function is not in `pipeline/` yet (the stub is due at about H10). Default: the route is built and tested against a mock, and returns `503` with a clear message until the real function can be imported. Confirm.
8. **`GET /api/export.csv`.** T-038 owns CSV export (`api/T-038-csv-export`). Default: not implemented in T-034, although the tracker says "all endpoints". Confirm.
9. **Test data.** There are no fixtures yet. Default, matching the Lead's decision for T-031: tiny SYNTHETIC products built inside the test files only; nothing in `data/fixtures/`. Confirm.
10. **CORS.** The web app runs on another port in development. Default: no CORS until the Lead approves a development-only allowance (the Vite dev server can proxy `/api` instead). Which do you prefer?
11. **Python tooling files.** Default: `api/pyproject.toml` for pytest and ruff settings and `api/requirements.txt` for pinned dependencies. Any objection?
