# Task prompt: Validation integration PR (all real test statuses into the products and the plan)

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main @ 14bfacb
> Source of truth: the Lead's merge plan on PR #50 ("Then **one integration PR (Member 2)** writes every real status (including FAILs, the D1 per-region and night entries, and the NOT_RUN halves) into `data/products/validation_results.json` and `docs/VALIDATION_PLAN.md` §4, so the methods page shows them") and the Lead's decisions on PRs #55, #56 and #57. **This work has no row in `docs/TASK_TRACKER.md`; the Lead is asked to add one (see §15).** This prompt adds no scope beyond those comments.

## 1. Project context
The Witness Stand publishes pre-registered validation tests, failures included. The validation PRs T-020 (A1), T-021 (B1, B3), T-022 (D1, D2) and T-025 (E1, S1) are merged, but their results exist only in their reports and in uncommitted files under `data/interim/qa/`. `data/products/validation_results.json` still has an empty test list and `docs/VALIDATION_PLAN.md` §4 still says `NOT_RUN` everywhere, so the methods page (T-041) cannot show anything.

## 2. Task objective
Re-run the four merged harnesses on the final products, merge their entries into one contract-valid `validation_results.json` (committed through Git LFS, D-027), and update `docs/VALIDATION_PLAN.md` §4 and §5 with the actual results, exactly as decided by the Lead.

## 3. Assigned responsibility
- Task ID / priority: none yet (named by the Lead on #50) / P0
- Owner: Member 2 · Reviewer and merger: Member 1 (Project Lead)
- Dependencies (merged): T-014, T-020, T-021, T-022, T-025

## 4. Relevant files and directories
- Read: `docs/validation/T-020-results.md`, `T-021-results.md`, `T-022-results.md`, `T-025-results.md`, `docs/DATA_CONTRACT.md` §6, `pipeline/validation_a1.py`, `validation_b.py`, `validation_d.py`, `validation_e1_s1.py`, `pipeline/contract_check.py`
- Create/modify: `docs/task-prompts/validation-integration.md` (this file), `pipeline/validation_integrate.py` and `pipeline/tests/test_validation_integrate.py` (merge and checks), `data/products/validation_results.json` (LFS), `docs/VALIDATION_PLAN.md` (§4 and §5 only; no criterion text), `docs/HANDOFF.md` and `docs/PROGRESS_LOG.md` if the session is substantial
- Not committed: `data/interim/`

## 5. Approved technologies
Python, pandas, pytest, ruff, DuckDB (D-008). No new dependency.

## 6. Architecture and data contract
Contract 0.1.1 §6: `validation_results.json` with `contract_version`, `method_version`, `generated_at`, `synthetic: false` and a `tests` list of `{test_id, family, title, case, criterion, threshold, measured, status, notes}`. Statuses are `PASS`, `FAIL`, `INCONCLUSIVE` or `NOT_RUN`. No contract change.

## 7. Inputs
The entries files written by the harnesses: `data/interim/qa/T-020_validation_entries.json`, `T-021_validation_entries.json`, `T-022_validation_entries.json` (with the D2 verdict half merged by `validation_d.py verdicts`), `T-025_validation_entries.json`; the T-014 products.

## 8. Expected outputs
- `data/products/validation_results.json` with, in this order: A1 (six cases and the family), A2, B1 (both dates and the family), B2, B3 (parts and family), C1, CTRL, D1 (pooled, per-region, night, total, countries as their own entries), D2 (estimates, verdicts, overall), E1, S1 (S1-BASELINE, S1-CONFIDENCE-FILTER, S1 overall). Tests nobody has run are present as `NOT_RUN` entries (A2, B2, C1, CTRL), never omitted.
- `docs/VALIDATION_PLAN.md` §4 table with actual results, status and run date for every row, §5 listing every failure.

## 9. Implementation requirements
1. **Re-run, never copy:** regenerate every entries file by running the merged harnesses on the committed products (A1: `python pipeline/validation_a1.py`; B: `python pipeline/validation_b.py`; D: `python pipeline/validation_d.py` then `python pipeline/validation_d.py verdicts data/products/cell_month_harmonized.parquet`; E1 and S1: `python pipeline/validation_e1_s1.py all`). Compare each regenerated status with its merged report (`docs/validation/T-0xx-results.md`); **any difference is reported, not smoothed**.
2. **Statuses as decided by the Lead:** A1 family FAIL for method 0.1.0 (C1 INCONCLUSIVE, C2 to C6 as run under D-029); D1 official result is the pooled share, the per-region result (7 of 14 inside) and the night result (0.750) are **their own entries, equally visible**, as FAIL; E1 PASS as written with the caveats prominent in `notes`; S1-BASELINE FAIL by the strict rule, S1-CONFIDENCE-FILTER NOT_RUN and S1 overall NOT_RUN; B3 PASS as written, drift visible at night only. No threshold, wording or status is changed here.
3. **VALIDATION_PLAN.md:** fill §4 (Actual, Status, Run date, Notes) and §5 from the entries. Do not touch criterion text. Add only the note the Lead asked for on D1: "D1 read as the pooled share as defined; per-region and night shares reported separately (both below 80%)."
4. **Checks (`validation_integrate.py`):** every entry has the contract fields; statuses are in the allowed set; `test_id`s are unique; every plan test (A1, A2, B1, B2, B3, C1, CTRL, D1, D2, E1, S1) appears; no `NOT_RUN` entry carries measured numbers; no PASS entry for a test that did not run; the file passes `contract_check.py`.
5. The v0.2 comparison (T-020c, D-030) is **not** a plan test and is not included.

## 10. Constraints: do not modify
- Do not change thresholds, criteria, earlier reports, other products, `api/` or `app/`. No raw or interim data in Git; the product only through Git LFS. No direct pushes to `main`, no self-merge. No AI attribution (D-020).

## 11. Acceptance criteria
`validation_results.json` validates against the contract and shows every real status including the FAILs and the NOT_RUN halves; `VALIDATION_PLAN.md` §4 and §5 match it; a table of regenerated against merged statuses shows no unexplained difference.

## 12. Required tests
`python -m pytest pipeline/tests -q` and `ruff check` on the files of this task; the integration checks above on synthetic entries (a missing field, a duplicate id, a NOT_RUN entry with numbers, a missing plan test each fail) and on the real file.

## 13. Documentation updates
`docs/VALIDATION_PLAN.md` §4 and §5; tracker row (once the Lead adds one); `docs/HANDOFF.md` and `docs/PROGRESS_LOG.md` at the end.

## 14. Git branch and PR instructions
- Branch: `science/validation-integration` from the latest `main`; first commit: this prompt; open a PR with the template; never merge.

## 15. Out-of-scope or blocking issues
- **No tracker row:** the Lead named this work on #50 but it has no ID. Please add one (suggested `T-027`, owner M2) before merge.
- If any harness no longer reproduces its merged status, stop and report it under "Scope issues".
