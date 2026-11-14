# Task prompt: T-023 Validation test A2 (same fire, two eras)

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main @ the branch point of `science/T-023-test-a2`
> Source of truth: docs/TASK_TRACKER.md row T-023 (PR #61), docs/VALIDATION_PLAN.md §2a ("Quiet months for test A2") and §3 (test A2), D-005, D-028, D-029. This prompt adds no scope beyond them. Every design choice below is written down BEFORE any real run.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand): harmonize NASA FIRMS hotspot detections from Aqua MODIS, S-NPP VIIRS and NOAA-20 VIIRS onto one Aqua-equivalent scale, with an honest uncertainty (`docs/PROJECT_PLAN.md`). The Witness Stand is the set of validation tests of `docs/VALIDATION_PLAN.md`. A2 asks whether the same real fire, seen by Aqua in an old era and by VIIRS in a new era, gives the same harmonized value although the raw record differs.

## 2. Task objective
A harness that, for C1, C4 and C6, (1) fixes the quiet calendar month by the rule of §2a, (2) takes the event month's real Aqua cell-days and plants them into that quiet month of 2010, and the event month's real S-NPP cell-days and plants them into the same quiet month of 2023, at the level of the cell-month table `cell_month_witness` (in memory and in a temporary copy under `data/interim/`; the products on disk are never touched), (3) harmonizes both planted months with the real v0.1 method (`harmonize.aggregate` + `harmonize.records_from`), (4) applies the A2 criterion as fixed in §9, and records one entry per case (`A2-C1`, `A2-C4`, `A2-C6`) and one family entry (`A2`).

## 3. Assigned responsibility
- Task ID / priority: T-023 / P1 (priority 4 of the Member 2 batch)
- Owner: Member 2 (Data Engineering & Scientific Analysis); reviewer and merger: Member 1 (Project Lead)
- Dependencies: T-014 (merged), T-050 (merged; cases and quiet-month rule in the plan)

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/TEAM_WORKFLOW.md` §4 and §5, `docs/VALIDATION_PLAN.md` §2a and §3, `docs/DECISION_LOG.md` D-005, D-028, D-029, `docs/DATA_CONTRACT.md` §2 and §6, `pipeline/harmonize.py`, `pipeline/validation_a1.py`, the T-020 task prompt and results.
- Create: `docs/task-prompts/T-023-test-a2.md` (this file), `pipeline/validation_a2.py`, `pipeline/tests/test_validation_a2.py`, `docs/validation/T-023-results.md`.
- Not committed: `data/interim/qa/T-023_validation_entries.json` and the cache `data/interim/T-023/` (git-ignored); nothing under `data/`.
- Not edited: `pipeline/harmonize.py`, `validation_a1.py` and every other module of an earlier task (imported only), the products, `docs/VALIDATION_PLAN.md`.

## 5. Approved technologies
Python, NumPy, pandas, DuckDB, pyarrow, pytest, ruff (D-008). No new dependency.

## 6. Architecture and data contract
No contract change, no new product. The entries follow `docs/DATA_CONTRACT.md` §6 (contract_version 0.1.1, `synthetic: false`).

## 7. Inputs
`data/products/cell_month_witness.parquet`, `cells.parquet`, `calibration.parquet` (read only). Cases C1, C4, C6: boxes and peak windows from `validation_a1.CASES` (VALIDATION_PLAN §2a); cells are the analysis cells whose centre lies in the box, edges included (`validation_a1.box_cells`).

## 8. Expected outputs
`pipeline/validation_a2.py` (command-line run that writes the entries file), `pipeline/tests/test_validation_a2.py`, `data/interim/qa/T-023_validation_entries.json` with the test ids `A2-C1`, `A2-C4`, `A2-C6`, `A2`, and `docs/validation/T-023-results.md` with the numbers and the exact re-run command.

## 9. Implementation requirements (all fixed before any real run)

**9.1 Quiet month (plan §2a, literal).** For each case: take the harmonized series of the box (`harmonize.aggregate` over the box cells and every month 2003-01 to 2022-12, all witnesses, then `records_from`: the series D-028 builds its baseline from). For each calendar month 1 to 12 take the empirical median (numpy percentile 50) of the estimates of that calendar month over 2003-2022, over the years that have an estimate, requiring at least 15 of the 20 years (D-028 step 2). The quiet calendar month is the one with the lowest median; a tie goes to the earliest calendar month. The 5 cell-day floor of D-028 step 4 is NOT applied (a quiet month is by nature a low one; we are not issuing a verdict). The quiet pre-2012 month is (2010, that month); the quiet post-2022 month is (2023, that month): the same calendar month in both eras.

**9.2 Event month.** The event month is the month of the case's peak window (`CASES[...]["peak"]`) with the largest raw Aqua cell-days (day + night, summed over the box cells), earliest on a tie. One event month per case, the same for both eras (it is "the same fire"). The rule uses only the raw Aqua record, not any harmonized result.

**9.3 Planting (cell-month level).** Work on the rows of `cell_month_witness` of the box cells.
- Old era: remove every row of the box cells in (2010, m*) (all witnesses, Terra included); insert the event month's `AQUA_MODIS` rows (all day/night values present) relabelled to (2010, m*).
- New era: remove every row of the box cells in (2023, m*); insert the event month's `SNPP_VIIRS` rows relabelled to (2023, m*). Aqua, Terra and NOAA-20 of the quiet month are removed so that the planted month is the event as one sensor saw it. NOAA-20 is not used: it did not exist in the C1 event (2015); S-NPP is the one VIIRS witness present in all three events and the one used in A1.
- Coherent fields: `cell_id`, `witness`, `daynight`, `detections`, `cell_days`, `frp_sum_mw` are the event's (nothing scaled, nothing invented; totals are preserved exactly); `days_in_month` is the real number of days of the target month; `days_available` equals it (the event witness-month must itself be complete, otherwise INCONCLUSIVE); `data_level` is the level of the quiet month's own rows for that witness if it has any in the box, otherwise the event's level.
- A planted row whose `cell_days` exceeds the target month's `days_in_month` cannot be a real record: the case is INCONCLUSIVE ("cannot be planted coherently"), never trimmed.
- The ratio applied is that of the target month's season (the planted month is treated by the pipeline exactly as a real record of that month). [ASSUMPTION] Exploratory only, not part of the status: the same harmonization with the ratios of the event's season.
- Mechanics: the planted rows, the event month's real rows (kept, for the identity check below) and a copy of `cells` and `calibration` go to a temporary product directory under `data/interim/T-023/`; `harmonize.aggregate` is pointed at it. Nothing in `data/products` changes.
- Identity check: the harmonized estimate of the planted Aqua month must equal the Aqua-only estimate of the real event month exactly (same cell-days, ratio 1).

**9.4 Definitions of "peak" and "overlap" (A1 definitions, with the A1 reasons).** The "peak" of an era is the harmonized estimate of its planted month (a single month holds the whole event). Its 90% interval is `estimate +- 1.645 x sd`, lower bound floored at 0, as in `validation_a1.summarize_path` and `harmonize.interval`. Intervals that touch overlap. Both planted months have the same calendar month and therefore the same baseline, so overlap in Aqua-equivalent cell-days and overlap in `pct_of_normal` are the same; the estimates are compared directly (no baseline is needed and the D-028 baseline step is not involved). `pct_of_normal` against the box's baseline median of that calendar month is reported as context.

**9.5 "A mismatch in the raw record" (fixed number).** The raw ratio is `raw_new / raw_old`: the planted S-NPP cell-days (day + night) in 2023 over the planted Aqua cell-days (day + night) in 2010. The raw record shows a mismatch if the ratio is at least **1.5** or at most **1/1.5** (one sensor reports at least 50% more than the other, either direction). The plan's expectation is "a large post-2022 inflation" (ratio above 1); a mismatch in the other direction counts as a mismatch and is reported with its direction. A ratio of at least 2.0 is called a large inflation in the report (descriptive; it changes no status).

**9.6 Status of a case.**
- PASS: planted coherently, both estimates exist, the raw record shows a mismatch (9.5) AND the 90% intervals overlap (9.4).
- FAIL: the same preconditions, the raw mismatch is present, and the intervals do not overlap.
- INCONCLUSIVE: the raw ratio is inside (1/1.5, 1.5) (the raw record shows no mismatch, as the plan says); or the quiet month cannot be fixed (no calendar month with 15 years); or the event month has no complete Aqua or S-NPP record or zero raw cell-days; or the planted record is incoherent (9.3); or an era has no harmonized estimate.
- Nothing is tuned on a result. The thresholds 1.5, the 90% level and the overlap rule are not changed after seeing any number.

**9.7 Family entry `A2`.** The plan gives no family rule. [ASSUMPTION] Literal reading: PASS only if all three cases PASS; an INCONCLUSIVE case does not count as a PASS. As in the A1 family entry: FAIL if "all three PASS" can no longer be reached (a case is FAIL or INCONCLUSIVE and none is NOT_RUN); INCONCLUSIVE only while a case is NOT_RUN. The case statuses are always listed in the entry so that an INCONCLUSIVE is never read as a FAIL of the method. The Lead decides the family rule.

## 10. Constraints: do not modify
Do not change the tech stack, architecture, methodology, data contract or thresholds. Do not edit `pipeline/harmonize.py`, `validation_a1.py` or any earlier module; do not write to `data/products`; no AI attribution (D-020); no push to `main`; no merge.

## 11. Acceptance criteria
Results recorded, pass or fail, for each case and the family, with the planted months, the raw and harmonized numbers, the identity check, and the reproduction command; INCONCLUSIVE where the rules say so.

## 12. Required tests
`python -m pytest pipeline/tests/test_validation_a2.py -q -p no:cacheprovider` on SYNTHETIC data with answers known by hand: quiet-month selection (lowest median, tie, too few years), event-month rule, planting preserves totals and fields (cell-days, detections, FRP sums; target month length; levels; removal of the quiet month's other rows), incoherent planting detected, overlap rule at the boundary, raw-mismatch rule at 1.5 and 1/1.5, status rules, family rule, and an end-to-end synthetic harmonization of a planted pair with a known answer. A mutation check. `python -m ruff check` on the two files. The full suite.

## 13. Documentation updates
`docs/validation/T-023-results.md`. The tracker row T-023 is not edited here if PR #61 is not yet on `main` (the Lead updates it); otherwise only row T-023 (IN_REVIEW, PR link).

## 14. Git branch and PR instructions
Branch `science/T-023-test-a2` from the latest `main`; first commit: this prompt; draft PR early, ready at the end; commits in Conventional Commits with the task ID (`science: ... (T-023)`), the contributor's own Git identity, no AI names or attribution; never merge.

## 15. Out-of-scope or blocking issues; [ASSUMPTION] list for the Lead
1. Quiet month from the harmonized combined series of the box with the D-028 median rule (15 of 20 years), not from an Aqua-only series, and without the 5 cell-day floor (9.1).
2. One event month per case: the peak-window month with the most raw Aqua cell-days (9.2). The plan says "the event's real detections" without naming a month.
3. A planted month contains one witness only (Aqua in 2010, S-NPP in 2023), the other witnesses of the quiet month removed (9.3). The real 2023 month would also have Aqua and NOAA-20; they are left out so that the planted month is "the event as VIIRS saw it". The test therefore checks the conversion of one witness (single-witness estimate, `SINGLE_WITNESS`), not the combination.
4. Season of the ratio: the target month's season (9.3). An exploratory variant with the event's season is reported separately.
5. Raw mismatch threshold 1.5 either direction (9.5); the plan says only "a mismatch".
6. Family rule (9.7).
7. Known limits (honesty, [VERIFIED] from `calibration.fit_period`): the S-NPP ratios were fitted on 2012-01 to 2016-12, so the C1 event (2015) is inside the fit period (partly circular) while C4 (2019-20) and C6 (2021) are outside it. The planted months share the real event's spatial pattern and day/night split. A1 on the same boxes already showed S-NPP-only below Aqua-only for C3 to C6; A2 is a different design but not independent of that finding. None of this changes a rule.
