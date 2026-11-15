# Handoff: Current Project State

**Last updated:** 2026-11-15, about 14:00 IST (Lead, T-082). Read this first, then `docs/TASK_TRACKER.md`.

## Exact current state

- **Phase:** built, validated and accepted for presentation (T-081). `main` @ `076847e` plus the Lead's documentation PR (#75).
- **Product:** a global, harmonized fire-activity record for July 2002 to November 2026 (NASA FIRMS: Aqua MODIS, S-NPP VIIRS, NOAA-20 VIIRS on the Aqua scale; 0.5° grid), with verdicts, evidence, validation and an interactive web app.
- **Data:**
  - **Real** products in `data/products/` (Git LFS, D-027), `synthetic: false`, method 0.1.0, contract 0.1.1.
  - Kashmir cells are counted by India's official boundary (D-033, T-086).
  - The whole Earth is named "World" (T-092).
- **Validation:** 38 pre-registered results: 18 PASS, 18 FAIL, 2 INCONCLUSIVE (`data/products/validation_results.json`, `docs/VALIDATION_PLAN.md`). v0.2 was not adopted (D-030).
- **Checks on `main`:**
  - contract check conforms
  - `number_check.py` 0 mismatches in 6,492,028 values (T-078, Lead re-run)
  - about 1,500 automated tests pass (app 693; pipeline and API about 820)

## Completed

- Pipeline, calibration, combination, verdicts, entity aggregation (T-001 to T-016, T-085, T-086).
- Validation suite and integration (T-020 to T-027).
- App and API:
  - map, calendar, evidence, satellites, anomalies, CSV, custom rectangle and polygon, methods page, offline copy (T-030 to T-044)
  - the UI round: design system, map UX, stories and How to read, faster map, responsive and accessibility, NASA GIBS imagery and globe, India's official boundary, month picker, methods redesign, analytics with compare and coverage (T-070 to T-074, T-083 to T-092)
- Docs: README for judges, architecture as built (T-075), fresh-clone check (T-077), number checks (T-026, T-078).
- Lead:
  - mock approval (T-080)
  - **browser acceptance (T-081, `docs/validation/T-081-acceptance.md`)**
  - **demo script (T-060, `docs/demo/DEMO_SCRIPT.md`)**
  - **project page text (T-062 draft, `docs/demo/PROJECT_PAGE_DRAFT.md`)**
  - this handoff (T-082)

## In progress (optional)

- **T-093, UI and UX excellence pass** (Member 2, PR #99, prompt `docs/prompts/T-093-UI-EXCELLENCE-PROMPT.md`). **Optional:** the app is complete and presentable without it. Merge only after the Lead's browser test against section 8 of the prompt.

## Pending: needs the Project Lead (actions only the Lead can take)

1. **T-061, record the demo video** (outside the repo), following `docs/demo/DEMO_SCRIPT.md`. Real data only.
2. **T-062, post the project page** text from `docs/demo/PROJECT_PAGE_DRAFT.md` on the Space Apps site, and add the video link.
3. **T-064, repo visibility (D-014).** Today: `PRIVATE` (checked 2026-11-15). Judges usually need to open the code. **Recommendation:** make it public before submitting (GitHub → Settings → General → Danger Zone). Run a last secret scan first; the rules forbid keys and `.env` files, and none are known to be committed. Only the Lead changes this.
4. **T-0F, protect `main` (D-019).** Today: not protected (checked 2026-11-15). **Recommendation:** after the last merge, add a rule requiring a PR (no direct pushes) and blocking force-pushes. Only the Lead changes settings.
5. **T-063, submit** on the Space Apps site before the deadline.
6. **Before an offline demo:** generate the full offline copy on the demo laptop (about 17 min; `api/README.md`). A 24-month copy was tested in T-081.

## Known limitations (say them, don't hide them)

- Extreme fire months are under-converted (VIIRS 20–40% low; A1 and A2 FAIL; S19).
- Night and per-region intervals are too narrow (D1 sub-readings FAIL; S16).
- The disagreement flag is not a jump detector (B2 FAIL; S20). Verdicts near satellite-change dates can differ from Aqua-only (CTRL FAIL; S21).
- Quiet cells with a big fire read "cannot determine" (D-031; S22).
- Safari and Firefox were not tested in T-081; a real screen reader was not tested.

## How to resume work

1. Read `CLAUDE.md`, `README.md`, this file, `docs/TASK_TRACKER.md`.
2. `git lfs install && git lfs pull` (products, about 600 MB).
3. Run the API (`README.md`; start from the repo root with `--app-dir api`) and the app (`cd app && npm ci && npm run dev`).
4. Checks:
   - `python pipeline/contract_check.py data/products --real`
   - `python pipeline/number_check.py` (Node 22.6+)
   - `pytest`
   - `npm test`

## Important files

- `README.md` (judges), `docs/ARCHITECTURE.md`, `docs/DATA_CONTRACT.md`, `docs/SCIENTIFIC_METHODOLOGY.md`, `docs/VALIDATION_PLAN.md`, `docs/RISKS_AND_LIMITATIONS.md`, `docs/DECISION_LOG.md` (D-001 to D-033), `docs/NUMBER_INVENTORY.md`
- `docs/demo/` (script, project page), `docs/validation/` (every report)
- `CLAUDE.md` (rules for AI assistants), `docs/TEAM_WORKFLOW.md`

## Repository facts (2026-11-15, via GitHub CLI)

- URL: https://github.com/vishalbg02/global-fire-harmonization; visibility **PRIVATE**; default branch `main`.
- Branch protection on `main`: **none** (the PR rule is policy). All work since the bootstrap went through PRs reviewed by the Lead.
