# Task prompt: T-005 Filters, static-source mask and QA summary

> Prepared for: Member 2 · Date: 2026-11-14 · Based on main @ 87d97a5
> Source of truth: docs/TASK_TRACKER.md row T-005. This prompt adds no scope beyond it.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand): harmonize NASA FIRMS hotspot detections from several satellites (`docs/PROJECT_PLAN.md`). T-003 produced the normalized detections table (582,050,574 rows). Before gridding (T-006), the detections must be inspected, the filters defined and counted, and a static-source mask built, because near-real-time (NRT) rows have no `type` field to tell fires from static heat sources.

## 2. Task objective
A QA summary of the normalized detections (value-domain checks, duplicates, filter counts), the filters from `SCIENTIFIC_METHODOLOGY.md` §4.1 defined as one reusable rule with recorded before/after counts, and a static-source mask built from standard (SP) history with its threshold evidence (including a hold-out check). The estimates in `docs/DATA_SOURCES.md` are replaced by the measured values. No row is dropped or altered; the filters are counted, not applied destructively.

## 3. Assigned responsibility
- Task ID / priority: T-005 / P0
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-003 (merged)

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/SCIENTIFIC_METHODOLOGY.md` §4.1, `docs/DATA_SOURCES.md`, `docs/prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md` §7 and §9, `docs/DECISION_LOG.md` (D-009)
- Create/modify:
  - `docs/task-prompts/T-005-filters-qa.md` (this file)
  - `pipeline/qa_filters.py`
  - `pipeline/tests/test_qa_filters.py`
  - `docs/DATA_SOURCES.md` (replace estimates with measurements; add the QA table)
  - `docs/RISKS_AND_LIMITATIONS.md` (only if a measured limitation needs recording)
  - `docs/TASK_TRACKER.md` (row T-005 only)
- Not committed: everything under `data/interim/` (QA tables, the mask)

## 5. Approved technologies
Python and DuckDB (D-008), pytest, ruff. Standard library for the rest.

## 6. Architecture and data contract
No contract product is produced. The static mask is an interim table on a fine grid; the fine grid size is still open (D-009, candidates 0.05 and 0.1 degrees), so the mask is built and evaluated at both and nothing is locked.

## 7. Inputs
`data/interim/detections/sensor=*/year=*/detections.parquet` (T-003, local, 582,050,574 rows).

## 8. Expected outputs
- `data/interim/qa/` (not committed): value-domain violations per sensor-year, duplicate counts, filter funnel, static-mask tables, hold-out evaluation, day/night check, and a Markdown summary.
- A QA table in `docs/DATA_SOURCES.md`, and the estimates (unzipped size) replaced with measurements.
- The static mask table (fine cell, shares) for the proposed setting, local only.

## 9. Implementation requirements
1. Value-domain checks per sensor-year: latitude in [-90, 90], longitude in [-180, 180], `acq_date` inside its year, `acq_time_utc` 0000 to 2359 with minutes below 60, confidence domain (MODIS 0 to 100; VIIRS l, n, h), `daynight` in {D, N}, `type` in {0, 1, 2, 3} where present, `frp` at least 0, `scan` and `track` above 0, no null key fields. Violations are counted, never fixed.
2. Duplicates: exact duplicates on (satellite, lat, lon, acq_date, acq_time) within a country file and across country files, per sensor-year, and at the 2025/2026 boundary. Counted, not removed.
3. Filters (`SCIENTIFIC_METHODOLOGY.md` §4.1): keep `type = 0` in SP data; NRT rows have no `type`; confidence MODIS at least 30 and VIIRS n or h. Record before and after counts for each step, per sensor and data level, and keep the unfiltered counts (for sensitivity test S1).
4. Static-source mask: per fine cell, the share of SP detections (2012 to 2025) with `type` 2 or 3. Build at both candidate fine sizes, report the number of cells and the number of NRT rows masked for several share thresholds, and evaluate each setting on held-out years (build on 2012 to 2023 SP, test on 2024 to 2025 SP): share of static detections removed, and share of `type = 0` fire detections wrongly removed.
5. The share threshold and minimum detection count are proposals and are reported for the Lead's approval; nothing is applied as final.
6. Day/night consistency: on a sample, compare `daynight` with the solar zenith angle rule (night above 85 degrees) for SP and for NRT rows. Reported only; no row is recomputed.
7. Replace the estimates in `docs/DATA_SOURCES.md` with the measured values.

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify". Do not touch `api/` or `app/`.
- No secrets, no data files, no direct pushes to `main`, no self-merge.
- Never drop, de-duplicate, recompute or alter rows. No gridding (T-006). No decision on MODIS `version` (T-007).
- Do not present a proposed threshold as approved.

## 11. Acceptance criteria
QA table; estimates in `DATA_SOURCES.md` replaced with measurements.

## 12. Required tests
`python -m pytest pipeline/tests/test_qa_filters.py -q` on a small synthetic partitioned dataset with known answers: each domain violation is counted; duplicates within and across files; the filter funnel; the mask shares, the minimum-count rule and the hold-out scores; the solar zenith rule on known times and places. `ruff` passes on the files of this task. Then the full run on the real data, with the numbers reported.

## 13. Documentation updates
`docs/TASK_TRACKER.md` row T-005; `docs/DATA_SOURCES.md` (QA table, measured values, proposals needing approval).

## 14. Git branch and PR instructions
- Branch: `data/T-005-filters-qa` created from the latest `main`
- First commit: this prompt file
- Open a DRAFT PR early; title "T-005: Filters, static-source mask and QA summary"; fill in `.github/pull_request_template.md`
- Never merge; wait for the Project Lead
- Commit with your own Git identity (D-020)

## 15. Out-of-scope or blocking issues
- The fine grid size (D-009) and the share threshold are open and need Lead approval; both candidate sizes are evaluated and the results are reported for the Lead to choose.
- Applying the NRT day/night recomputation needs Lead approval (prompt §9); here it is only measured.
- Duplicates are counted but not removed; whether to remove them is for T-006 and the Lead.
