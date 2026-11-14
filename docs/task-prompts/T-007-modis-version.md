# Task prompt: T-007 Investigate MODIS `version` values

> Prepared for: Member 2 · Date: 2026-11-14 · Based on main @ c8071b1
> Source of truth: docs/TASK_TRACKER.md row T-007 (assigned by the Lead's assignment PR #27). This prompt adds no scope beyond it.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand): harmonize NASA FIRMS hotspot detections from several satellites (`docs/PROJECT_PLAN.md`). The MODIS `version` field takes different values over time (`6.2`, `6.03`, `61.03`, `6.1NRT`). If a processing change shifted detection counts or confidence, Aqua (the reference scale) would carry an artifact into every harmonized value (risk S10, `docs/RISKS_AND_LIMITATIONS.md`).

## 2. Task objective
A documented finding on what the `version` values are, when each applies, whether a version change coincides with a step in counts, confidence or other fields (measured against normal year-to-year variation), and what it means for the method. No data is dropped or altered.

## 3. Assigned responsibility
- Task ID / priority: T-007 / P1
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-003 (merged)

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/DATA_SOURCES.md` §1, `docs/RISKS_AND_LIMITATIONS.md` (S10), `docs/prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md` §7
- Create/modify:
  - `docs/task-prompts/T-007-modis-version.md` (this file)
  - `pipeline/modis_version.py`
  - `pipeline/tests/test_modis_version.py`
  - `docs/DATA_SOURCES.md` (the finding; replaces the open data-quality question)
  - `docs/RISKS_AND_LIMITATIONS.md` (S10 and any method impact)
  - `docs/TASK_TRACKER.md` (row T-007 only)

## 5. Approved technologies
Python and DuckDB (D-008), pytest, ruff. Standard library for the rest.

## 6. Architecture and data contract
Not touched.

## 7. Inputs
`data/interim/detections/sensor=MODIS/` (T-003, local) and, as a control, `sensor=VIIRS_SNPP/`.

## 8. Expected outputs
A finding section in `docs/DATA_SOURCES.md` with: the version timeline per satellite; the rows that carry a minority version and where they come from; step sizes at each version boundary compared with the same measure at ordinary 1 January boundaries; the method impact; and what stays open.

## 9. Implementation requirements
1. Timeline: rows, first and last date per version, satellite and data level.
2. Explain rows whose version differs from the version used for the rest of their year (which files they are in), without changing them.
3. Step test: for each 1 January from 2004 to 2025, compare the 12 months after with the 12 months before for row counts, row counts relative to S-NPP (control for real fire variability, 2013 onward), low-confidence share, mean confidence, mean FRP, daytime share and static-source (type 2 or 3) share, for Terra and Aqua separately. The version boundaries are judged against the other years: where they fall in that range.
4. Report what cannot be determined (for example the meaning of each version string, which FIRMS does not document in the shipped files).
5. Do not drop or filter rows by version. Any proposal is for the Lead.

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify". Do not touch `api/` or `app/`.
- No secrets, no data files, no direct pushes to `main`, no self-merge.
- Label every claim as verified, estimate, assumption or hypothesis. A step that is within normal year-to-year variation is not called an artifact, and a step outside it is not called proven to be a processing change.

## 11. Acceptance criteria
Finding documented; any method impact logged.

## 12. Required tests
`python -m pytest pipeline/tests/test_modis_version.py -q` on small synthetic data with known answers (timeline, minority-version rows, window sums, step ratio and rank of a planted step). `ruff` passes on the files of this task. Then the full run on the real data.

## 13. Documentation updates
`docs/TASK_TRACKER.md` row T-007; `docs/DATA_SOURCES.md`; `docs/RISKS_AND_LIMITATIONS.md`.

## 14. Git branch and PR instructions
- Branch: `data/T-007-modis-version` created from the latest `main`
- First commit: this prompt file
- Open a DRAFT PR early; title "T-007: Investigate MODIS version values"; fill in `.github/pull_request_template.md`
- Never merge; wait for the Project Lead
- Commit with your own Git identity (D-020)

## 15. Out-of-scope or blocking issues
- The tracker shows T-007 as `TODO` until the Lead's assignment PR #27 is merged; work started on Member 2's go-ahead. The Lead should confirm.
- Whether to filter, flag or adjust by version is a method decision for the Lead; this task only reports.
