# Task prompt: T-008 Confirm Aqua/Terra 2026 availability

> Prepared for: Member 2 · Date: 2026-11-14 · Based on main @ e0cefc5
> Source of truth: docs/TASK_TRACKER.md row T-008. This prompt adds no scope beyond it.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand): harmonize NASA FIRMS hotspot detections from several satellites (`docs/PROJECT_PLAN.md`). Aqua and Terra (both MODIS) are two witnesses, and both are near the end of their missions. Whether each is still delivering in 2026 decides how the 2026 record is handled.

## 2. Task objective
`docs/DATA_SOURCES.md` states, with evidence, whether Aqua and Terra MODIS are still delivering detections in 2026, up to what date, and which days are missing. Each statement is labelled verified, estimate, assumption or open.

## 3. Assigned responsibility
- Task ID / priority: T-008 / P0
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): MAP_KEY. The evidence uses the files pulled in T-002 (`data/raw/api_2026/`, local only) and its saved `data_availability` and `missing_data` responses.

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/DATA_SOURCES.md` §4, `docs/prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md` §5, `data/raw/availability/`, `data/raw/api_2026/MODIS_SP/`, `data/raw/api_2026/MODIS_NRT/`
- Create/modify:
  - `docs/task-prompts/T-008-availability.md` (this file)
  - `pipeline/check_modis_availability.py` (standard library only; read-only on `data/raw/`)
  - `docs/DATA_SOURCES.md` (§4 satellite table, and a short "Aqua/Terra 2026 availability" result)
  - `docs/TASK_TRACKER.md` (row T-008 only)

## 5. Approved technologies
Python (approved, D-008), standard library only.

## 6. Architecture and data contract
Not touched.

## 7. Inputs
- `data/raw/availability/data_availability_*.csv` and `missing_data_*.json` (from T-002).
- `data/raw/api_2026/MODIS_SP/*.csv` and `MODIS_NRT/*.csv` (from T-002), column `satellite` (`Terra`, `Aqua`).
- No key is needed.

## 8. Expected outputs
- A table in `docs/DATA_SOURCES.md`: per satellite, first and last 2026 detection date, days with detections, days without, rows per month.
- The FIRMS `missing_data` entries for Terra and Aqua in 2026, compared with the days without detections.
- A sentence saying what the data cannot show (the mission end date).

## 9. Implementation requirements
1. Compute everything from the saved files; do not rely on memory or press reports.
2. `data_availability` lists MODIS as one source and cannot separate Aqua from Terra; say so, and use the `satellite` column instead.
3. A day with no detections is reported as "no detections", never filled or interpolated. Whether it is an outage is established only if `missing_data` lists it.
4. Do not state a mission end date unless a source in the repository documents it. Otherwise write "cannot determine from FIRMS data".

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify". Do not touch `api/` or `app/`.
- No secrets, no data files, no direct pushes to `main`, no self-merge.
- Do not change how Aqua/Terra are used in the method; propose it to the Lead if the finding affects the method.

## 11. Acceptance criteria
Result in `DATA_SOURCES.md`.

## 12. Required tests
- Run `python -I pipeline/check_modis_availability.py`; its output must match the table in `DATA_SOURCES.md`.
- The script must not write to `data/raw/`.

## 13. Documentation updates
`docs/DATA_SOURCES.md` §4; `docs/TASK_TRACKER.md` row T-008.

## 14. Git branch and PR instructions
- Branch: `data/T-008-availability` created from the latest `main`
- First commit: this prompt file
- Open a DRAFT PR early; title "T-008: Confirm Aqua/Terra 2026 availability"; fill in `.github/pull_request_template.md`
- Never merge; wait for the Project Lead
- Commit with your own Git identity (D-020)

## 15. Out-of-scope or blocking issues
- The tracker shows T-008 as `TODO`, not `ASSIGNED`; the Lead should confirm.
- The evidence comes from T-002's local files, which are not in the PR. The T-002 PR must be reviewed first for the numbers to be reproducible by the Lead.
- The `missing_data` table is read from the endpoint its web page loads (`?action=fetch_data`), not a documented API.
