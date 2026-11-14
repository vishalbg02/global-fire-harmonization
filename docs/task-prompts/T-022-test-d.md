# Task prompt: T-022 Validation tests D1 (coverage) and D2 (gaps)

> Prepared for: Member 2 · Date: 2026-11-14 · Based on main @ 02cd07c
> Source of truth: docs/TASK_TRACKER.md row T-022, `docs/DECISION_LOG.md` D-028 (thresholds locked at G1) and `docs/VALIDATION_PLAN.md` section 3. This prompt adds no scope beyond them.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand): harmonize NASA FIRMS hotspot detections from several satellites and say honestly how sure we are. T-012 produced the holdout evaluation 2017 to 2021 and the Lead's coverage check; T-013 the combined estimate with its uncertainty. T-014 (baseline, probabilities, verdicts) is in progress and not yet merged. T-022 runs two of the pre-registered validation tests.

## 2. Task objective
Run test D1 (are the 90% intervals honest on the 2017-2021 holdout) and test D2 (months without a complete witness must not get an estimate, and must be `CANNOT_DETERMINE` with `OUTAGE`) exactly as the validation plan defines them, record the results, failures included, and leave the verdict-level part of D2 ready to run once T-014 lands.

## 3. Assigned responsibility
- Task ID / priority: T-022 / P0
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies: T-012 (merged). T-014 is NOT merged: the verdict part of D2 stays `NOT_RUN`.

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/DECISION_LOG.md` D-005 and D-028, `docs/VALIDATION_PLAN.md` sections 2a, 3, 4, `docs/DATA_SOURCES.md` (T-012 and T-013 sections), `docs/DATA_CONTRACT.md` sections 4 and 6, `pipeline/holdout.py`, `pipeline/harmonize.py`
- Create/modify:
  - `docs/task-prompts/T-022-test-d.md` (this file)
  - `pipeline/validation_d.py`
  - `pipeline/tests/test_validation_d.py`
  - `docs/validation/T-022-results.md` (new)
  - `docs/TASK_TRACKER.md` (row T-022 only)
- Not committed: everything under `data/` (the entries file goes to `data/interim/qa/T-022_validation_entries.json`, git-ignored)

## 5. Approved technologies
Python, NumPy, pandas, DuckDB, pyarrow, pytest, ruff (D-008). No new dependency.

## 6. Architecture and data contract
Output entries have the shape of `validation_results.json` (`docs/DATA_CONTRACT.md` section 6: test_id, family, title, case, criterion, threshold, measured, status, notes; status one of PASS, FAIL, INCONCLUSIVE, NOT_RUN). The verdict-level check of D2 takes a DataFrame shaped like `entity_month` (section 4). No contract change.

## 7. Inputs
`data/products/*.parquet` (Git LFS) through `pipeline/holdout.py` (coverage) and `pipeline/harmonize.py` (`aggregate`, `records_from`).

## 8. Expected outputs
`pipeline/validation_d.py`, its tests, the entries file, and `docs/validation/T-022-results.md` with the numbers, the statuses, the reading of each criterion and the honest failures and limits.

## 9. Implementation requirements
1. **D1:** reuse `pipeline/holdout.py` (import, do not edit). Per fire region and pooled: D/N units and day+night totals, the 90% interval and the 50% interval as a second check, status against the locked target 80% to 97%. Decide pooled against per-region by reading the criterion; record the reading as an assumption. Report the per-region numbers and night units alone as known limits (risk S16). The Lead decided that no widening factor is applied; it is reported only. Never change a threshold.
2. **D2, estimate level (runs now):** over countries, fire regions and the globe, every month in which no witness is complete has no estimate; months with a partial witness do not use it (checked by making partial rows absurd and verifying the estimates do not move).
3. **D2, verdict level (NOT_RUN until T-014):** a function over an `entity_month`-shaped table: every row without an estimate is `CANNOT_DETERMINE` with `OUTAGE`; report the share of rows with a determinable verdict.
4. Plain precise English; labels VERIFIED, ASSUMPTION, HYPOTHESIS, OPEN; no AI attribution (D-020).

## 10. Constraints: do not modify
- Do not change thresholds, the data contract, scientific methodology, scope or the tech stack.
- Do not edit `pipeline/holdout.py`, `pipeline/harmonize.py`, `docs/DATA_SOURCES.md`, `docs/VALIDATION_PLAN.md` or any product; report needed changes to the Lead.
- Do not mark a test passed unless it ran. No secrets, no data files, no pushes, no PR.

## 11. Acceptance criteria
Tests pass on synthetic data with known answers; D1 and the estimate-level D2 are run on the real products and recorded with their actual statuses; the verdict-level D2 is `NOT_RUN` with the command to run it.

## 12. Required tests
`python -m pytest pipeline/tests/test_validation_d.py -q -p no:cacheprovider`: coverage counted on planted intervals; status logic including exactly 0.80 and 0.97; pooled against per-region; outage months have no estimate; the verdict-level check passes a planted good table and fails a planted bad one; reproducibility. Mutation check done. `ruff check` passes on both files.

## 13. Documentation updates
`docs/TASK_TRACKER.md` row T-022 only (IN_REVIEW, Review PENDING); `docs/validation/T-022-results.md`. The Lead integrates the results into `docs/VALIDATION_PLAN.md` section 4.

## 14. Git branch and PR instructions
- Branch: `science/T-022-test-d` created from the latest `main`
- First commit: this prompt file
- No push and no PR in this session; the Lead decides
- Commit with your own Git identity (D-020)

## 15. Out-of-scope or blocking issues
- **Blocked on T-014:** the verdict-level part of D2 and the share of land cells with a determinable verdict.
- **Reading of D1 (assumption):** "All fire regions" in the plan describes the population of the test; the criterion is one share. The pooled share over all fire-region units is the main status; per-region and night results are reported as limits.
