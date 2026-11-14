# Task prompt: T-014a Raw-only `cell_month_harmonized` and `entity_month` for the app

> Prepared for: Member 2 · Date: 2026-11-14 · Based on main @ aa79228
> Source of truth: the Lead's request to Member 2 on PR #27 (comment of 2026-11-14 13:09, item 2: "Publish raw-only versions of `cell_month_harmonized` and `entity_month`"). **The task ID T-014a and its tracker row are a proposal by Member 2**: the Lead left open whether this is part of the T-013/T-014 path or its own task. The Lead should confirm or rename it. This prompt adds no scope beyond the request.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand): harmonize NASA FIRMS hotspot detections from several satellites (`docs/PROJECT_PLAN.md`). Member 3 builds the API and the app against the contract in `docs/DATA_CONTRACT.md`. The harmonized products come from T-013 and T-014; until then Member 3 has only SYNTHETIC fixtures. T-014a gives them the real raw observations in the exact contract shape, so the API and app need no changes and T-039 (real-data integration) can start. T-014 replaces these files.

## 2. Task objective
Real, local products `cell_month_harmonized.parquet` and `entity_month.parquet` (contract v0.1.0 §3 and §4) and a real `metadata.json` (§7, `synthetic: false`) in `data/products/`, built from `cell_month_witness.parquet` and `cells.parquet` (T-006, T-011). Only the raw fields are filled; every harmonized field is `null`. A short test and a real-data mode in `pipeline/contract_check.py` validate them.

## 3. Assigned responsibility
- Task ID / priority: T-014a (proposed) / P0, as it unblocks T-039
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-006 (merged), T-009 (merged), T-011 (merged, #36)

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/DATA_CONTRACT.md` §2, §3, §4 and §7, `docs/DATA_SOURCES.md` (T-006, T-009, T-011), `pipeline/contract_check.py`, `pipeline/country_map.csv`, `data/fixtures/v0.1.0/` (shape only)
- Create/modify:
  - `docs/task-prompts/T-014a-raw-only-products.md` (this file)
  - `pipeline/raw_only.py`
  - `pipeline/tests/test_raw_only.py`
  - `pipeline/contract_check.py` (a `--real` mode only; the synthetic checks are unchanged)
  - `docs/DATA_SOURCES.md` (a short section)
  - no tracker edit: only the Lead adds task rows (`TASK_TRACKER.md`); the PR asks the Lead to add T-014a
- Not committed: everything under `data/products/`

## 5. Approved technologies
Python, DuckDB, pyarrow, pandas, pytest, ruff (D-008). No new dependency.

## 6. Architecture and data contract
`cell_month_harmonized` (§3) and `entity_month` (§4) exactly as in v0.1.0. No new field, enumeration or file. Two gaps in the contract are handled without inventing anything, and are proposed to the Lead (section 15): a reason code for "not yet harmonized", and the entity ID scheme (D-022, not yet approved).

## 7. Inputs
`data/products/cell_month_witness.parquet` and `data/products/cells.parquet` (the final products of T-011, D-025 mask); `pipeline/country_map.csv` (T-009, for country names).

## 8. Expected outputs
- `data/products/cell_month_harmonized.parquet`, `data/products/entity_month.parquet`, `data/products/metadata.json`, all local.
- `data/products/validation_results.json` with `"synthetic": false` and an empty `tests` list (the contract check requires the file; no test has run).
- A report: row counts, entities, months, and the checksums.

## 9. Implementation requirements
1. **Cell level.** One row per cell x month that has at least one witness row (daynight `ALL`). `raw_combined_cell_days` is the sum of `cell_days` over all witnesses with a row that month (the contract's naive raw sum, which includes `TERRA_MODIS`, as in the fixtures).
2. **Entity level.** `COUNTRY` (`entity_id` = ISO3 from `cells.country_iso3`, `entity_name` from `country_map.csv`), `CONTINENT` (`entity_id` = the continent code of `cells.continent`, `entity_name` the continent's name) and `GLOBAL` (`entity_id` = `GLOBAL`, all cells, including cells without a country). `raw_by_witness` is a JSON map `{witness: cell_days}` of the witnesses operating that month; `raw_combined_cell_days` is its sum; `n_cells` is the number of cells of the entity.
3. **Harmonized fields.** `estimate`, `ci90_low`, `ci90_high`, `sd`, `disagreement_scale`, `baseline_median`, `baseline_p25`, `baseline_p75`, `pct_of_normal`, `p_above`, `p_below`, `p_within` are `null` (typed float). `witnesses_used` is `[]`, `n_witnesses` is 0, `verdict` is `CANNOT_DETERMINE`.
4. **Reason codes.** No contract code means "not yet harmonized". `reason_codes` is `[]` and the PR proposes a new code for the Lead (section 15). The rows are recognised by a `method_version` that ends in `-raw-only`.
5. **`data_level`.** `SP` or `NRT` when every witness row of that month has it, otherwise `MIXED`.
6. **`metadata.json`.** `synthetic: false`; `contract_version: 0.1.0`; `grid` from `cells.parquet`; `first_month` and `latest_month` from the data; `provisional_months` the months with any `NRT` row; `witnesses` the witnesses present (without `TERRA_MODIS`, as in the fixture); real snapshot dates; the NASA FIRMS, LANCE and ESDIS acknowledgement as `citation`. `baseline_years` is empty because no baseline is computed.
7. **`contract_check.py --real`.** The same table checks; for the JSON files it requires `synthetic: false` instead of `true` and skips the SYNTHETIC test-id rules. Nothing else changes.
8. Deterministic: the same inputs give the same files (apart from `generated_at`).

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, scientific methodology or data contract. Do not add an enumeration value.
- Do not edit files outside §4 "Create/modify". Do not touch `api/` or `app/`.
- No secrets, no data files, no direct pushes to `main`, no self-merge. The products go to Member 3 outside Git (WhatsApp as a Document or a shared Drive folder) with SHA-256 checksums.
- Do not compute any harmonized value, baseline, verdict other than `CANNOT_DETERMINE`, or validation test. Never present these files as harmonized results.

## 11. Acceptance criteria
`cell_month_harmonized`, `entity_month` and `metadata.json` validate against the contract with `contract_check.py --real`; the raw sums match `cell_month_witness`.

## 12. Required tests
`python -m pytest pipeline/tests/test_raw_only.py -q` on a small synthetic `cell_month_witness`/`cells` pair with known sums: the cell and entity sums match by hand; `GLOBAL` equals the sum of the countries plus the cells without a country; `CONTINENT` equals the sum of its countries; every harmonized field is null and `witnesses_used` is empty; `method_version` ends in `-raw-only`; `data_level` is `MIXED` for a mixed month; the output passes `contract_check --real` and a corrupted copy does not. `ruff` passes on the files of this task. Then the run on the real products, with the report.

## 13. Documentation updates
`docs/DATA_SOURCES.md`. The tracker row is the Lead's to add.

## 14. Git branch and PR instructions
- Branch: `science/T-014a-raw-only-products` created from the latest `main`
- First commit: this prompt file
- Open a DRAFT PR early; fill in `.github/pull_request_template.md`
- Never merge; wait for the Project Lead
- Commit with your own Git identity (D-020)

## 15. Out-of-scope or blocking issues
- **Task ID:** T-014a is not in the tracker, and a teammate does not add rows. The Lead confirms or renames it and adds the row.
- **Reason code:** a code meaning "not yet harmonized" is proposed (`NOT_HARMONIZED`, contract 0.1.1). Until it is approved, `reason_codes` stays empty.
- **Entity IDs:** D-022 (entity ID scheme) is PROPOSED. This task uses the fixtures' convention (ISO3, continent codes `AF AN AS EU NA OC SA`, `GLOBAL`). If the Lead approves a different scheme, only the IDs change.
- **Entity coverage:** cells without a country (927 of 56,238) enter `GLOBAL` only.
- **Scientific honesty:** the files carry raw cell-days only. `raw_combined_cell_days` adds witnesses that see the same fire, so it is not a measure of fire activity and must not be shown as one.
