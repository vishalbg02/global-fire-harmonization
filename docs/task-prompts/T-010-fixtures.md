# Task prompt: T-010 SYNTHETIC fixtures for all contract products

> Prepared for: Member 2 · Date: 2026-11-14 · Based on main @ 53e3c46
> Source of truth: docs/TASK_TRACKER.md row T-010. This prompt adds no scope beyond it.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand): harmonize NASA FIRMS hotspot detections from several satellites and tell users whether fire activity in a place and month was above or below normal (`docs/PROJECT_PLAN.md`). Member 3 builds the API and app. Until the real products exist, they develop against small fixtures. T-010 produces those fixtures, so it blocks Member 3 and is done first.

## 2. Task objective
`data/fixtures/v0.1.0/` contains one SYNTHETIC file for every contract product (`cells`, `cell_month_witness`, `cell_month_harmonized`, `entity_month`, `calibration`, `validation_results.json`, `metadata.json`), under 5 MB in total, matching `docs/DATA_CONTRACT.md` v0.1.0 exactly (fields, types, enums, null rules), with the required edge cases listed in a fixtures README. The generator and a contract checker are committed so everything can be regenerated and re-validated.

## 3. Assigned responsibility
- Task ID / priority: T-010 / P0
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-0B (data contract approved; done)

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/DATA_CONTRACT.md`, `docs/prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md` §S.2–S.4, `docs/TECH_STACK.md`, `docs/DECISION_LOG.md`, `docs/ARCHITECTURE.md`
- Create/modify:
  - `docs/task-prompts/T-010-fixtures.md` (this file)
  - `pipeline/make_fixtures.py` (generator; fixed random seed)
  - `pipeline/contract_check.py` (checks files against the contract)
  - `pipeline/tests/test_fixtures.py` (pytest)
  - `data/fixtures/v0.1.0/*` (the fixtures and their README)
  - `docs/TASK_TRACKER.md` (row T-010 only)

## 5. Approved technologies
Python 3.12–3.14, NumPy, pandas, pyarrow (Parquet), pytest, ruff (`docs/TECH_STACK.md`, D-008). Standard library for everything else. No new dependency.

## 6. Architecture and data contract
`DATA_CONTRACT.md` v0.1.0, products 1–7. Fixtures are SYNTHETIC: values are made up, geography is real (real ISO3 codes and cell positions). The proposed (not yet approved) conventions in prompt §S.3 are used where the prompt tells fixtures to use them: `cell_id` = `g{RRR}_r{row:04d}_c{col:04d}`, entity IDs (ISO3, continent codes, `GLOBAL`), one `<name>.parquet` file per product.

## 7. Inputs
None from NASA. No keys. The generator uses a fixed random seed so output is reproducible.

## 8. Expected outputs
`data/fixtures/v0.1.0/`: `README.md`, `cells.parquet`, `cell_month_witness.parquet`, `cell_month_harmonized.parquet`, `entity_month.parquet`, `calibration.parquet`, `metadata.json` (`"synthetic": true`), `validation_results.json` (`"synthetic": true`, every `test_id` starting `SYNTHETIC-`, notes "SYNTHETIC EXAMPLE — not a result").

## 9. Implementation requirements
1. Grid `g050` (0.5°), a few hundred cells over 4–6 countries on at least 3 continents; months `2002-07` through `2026-11`; entities `COUNTRY`, `CONTINENT`, `GLOBAL`.
2. Witness windows: `AQUA_MODIS` from 2002-07 (excluded from `witnesses_used` after a placeholder drift cutoff, flagged `AQUA_DRIFT_ERA`); `TERRA_MODIS` in raw rows only; `SNPP_VIIRS` 2012-01 to 2026-11 (partial last month); `NOAA20_VIIRS` from 2018-04.
3. Edge cases, all present and listed in the README: every `verdict` value; every `reason_code` value; an outage month; the last two months `NRT` and provisional; a zero baseline median (`pct_of_normal` null); `disagreement_scale` > 1; `NO_DETECTED_ACTIVITY` cells; a null `estimate`.
4. Internally consistent: baselines, `pct_of_normal`, probabilities and entity sums are computed from the synthetic series, not typed in.
5. Ratios, drift cutoff and verdict thresholds are **placeholders**, labelled as such. No real result is implied.
6. Total size under 5 MB.

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify". Do not touch `api/` or `app/`.
- No secrets, no NASA data, no direct pushes to `main`, no self-merge.
- Do not present synthetic values as results. Do not fill missing values with 0.

## 11. Acceptance criteria
Labelled synthetic; under 5 MB; validate against the contract.

## 12. Required tests
`python -m pytest pipeline/tests -q`: each file matches the contract schema and enums; null rules hold; every verdict, reason code and required edge case is present; total size under 5 MB; regenerating with the same seed gives identical content; `synthetic` flags are set. `python -m ruff check pipeline` passes.

## 13. Documentation updates
`docs/TASK_TRACKER.md` row T-010; `data/fixtures/v0.1.0/README.md` (how it was generated, edge-case list).

## 14. Git branch and PR instructions
- Branch: `data/T-010-fixtures` created from the latest `main`
- First commit: this prompt file
- Open a DRAFT PR early; title "T-010: SYNTHETIC fixtures for all contract products"; fill in `.github/pull_request_template.md`
- Never merge; wait for the Project Lead
- Commit with your own Git identity (D-020)

## 15. Out-of-scope or blocking issues
- The tracker shows T-010 as `TODO` until the Lead's assignment PR is merged; work started on Member 2's go-ahead. The Lead should confirm.
- D-022 (`cell_id` format, entity IDs, product path rule) is still PROPOSED. Fixtures use it as the prompt instructs; if it changes, the generator is re-run.
- `raw_combined_cell_days` is a non-nullable int, so a cell-month with no operating witness must carry 0, which reads like "unknown = 0". Raised for the Lead.
- No pinned `requirements.txt` exists yet, so dependencies are not pinned in the repository.
