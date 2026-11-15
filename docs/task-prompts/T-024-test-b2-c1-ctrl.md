# Task prompt: T-024 Tests B2, C1 and CTRL

> Prepared for: Member 2 · Date: 2026-11-15 · Based on main @ cd4a532
> Source of truth: docs/TASK_TRACKER.md row T-024 (on `origin/docs/assign-M2-batch-final`, PR #61). This prompt adds no scope beyond it.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand, global scope, `docs/PROJECT_PLAN.md`): hotspot detections of Aqua MODIS, S-NPP VIIRS and NOAA-20 VIIRS are put on the Aqua-equivalent scale (T-011 ratios), combined with an honest uncertainty (T-013), and judged against a baseline (T-014). The Witness Stand (`docs/VALIDATION_PLAN.md`) tests the method with criteria locked at Gate G1 (D-028) before any result existed. T-024 runs three of those tests: B2 asks whether a sensor jump planted in one witness is noticed, C1 whether two independently converted VIIRS satellites agree, CTRL whether the harmonization invents anomalies at the satellite-change dates in a region where nothing happened.

## 2. Task objective
Three validation tests are implemented, run on the final T-011 products (contract 0.1.1, method `0.1.0-combined-no-baseline`), and recorded honestly with PASS, FAIL or INCONCLUSIVE as actually obtained: **B2** (planted jumps, 200 trials), **C1** (S-NPP against NOAA-20, fire-region-months), **CTRL** (southern African savanna box C8 at 2012-01 and 2018-04). Everything the plan leaves open is fixed in section 15 BEFORE any real run. Thresholds are those of `docs/VALIDATION_PLAN.md` section 3 and are not changed after the results.

## 3. Assigned responsibility
- Task ID / priority: T-024 / P1 (priority 3 of the batch)
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-014 (merged). The products on main are the v0.1 conversion; the v0.2 conversion (T-020c) is a separate task, and these tests re-run unchanged on it (`python pipeline/validation_b2_c1_ctrl.py all`).

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/TEAM_WORKFLOW.md` 4 and 5, `docs/DECISION_LOG.md` D-005, D-028 (with amendment A) and D-029, `docs/VALIDATION_PLAN.md` 2a and 3, `docs/SCIENTIFIC_METHODOLOGY.md`, `docs/DATA_CONTRACT.md` 6, `pipeline/harmonize.py`, `pipeline/validation_a1.py`, `pipeline/validation_d.py`, `pipeline/validation_e1_s1.py`, `pipeline/calibration.py`, `data/products/*.parquet`
- Create/modify:
  - `docs/task-prompts/T-024-test-b2-c1-ctrl.md` (this file)
  - `pipeline/validation_b2_c1_ctrl.py`, `pipeline/tests/test_validation_b2_c1_ctrl.py`
  - `docs/validation/T-024-results.md` (new file)
  - `docs/TASK_TRACKER.md` row T-024 only, and only if PR #61 is on main when the PR is opened
- Not committed: everything under `data/interim/` (caches in `data/interim/T-024/`, reports and `T-024_validation_entries.json` in `data/interim/qa/`).

## 5. Approved technologies
Python, NumPy, pandas, DuckDB, pyarrow, pytest, ruff (D-008). Nothing is added.

## 6. Architecture and data contract
Component: validation (`docs/ARCHITECTURE.md`, Member 2). Inputs are the products `cells`, `cell_month_witness` and `calibration` of contract 0.1.1. Output: entries in the `validation_results.json` shape (contract 6: test_id, family, title, case, criterion, threshold, measured, status, notes; status PASS, FAIL, INCONCLUSIVE or NOT_RUN). No contract change. No product on disk is changed: planted jumps are made on the in-memory aggregated table only.

## 7. Inputs
`data/products/cells.parquet`, `cell_month_witness.parquet`, `calibration.parquet`. No environment variables, no network.

## 8. Expected outputs
- `data/interim/qa/T-024_validation_entries.json`: entries `B2`, `C1`, `CTRL` and the supplementary `B2-CODE-ONLY`, `B2-FALSE-FLAG-MONTHLY`, `C1-OVERLAP`, `C1-OUT-OF-SAMPLE-2022-2024`, `CTRL-SHARED-BASELINE`.
- `data/interim/qa/T-024_report.json`: all numbers, and the trial table of B2.
- `docs/validation/T-024-results.md`: what was done, the numbers, the verdict per test, honest failures, limitations, how to re-run.

## 9. Implementation requirements

### 9.1 Common building blocks (reused, not edited)
`harmonize.aggregate` (the aggregated table: one row per entity x month x witness x day/night with e, vc, vr, raw, complete), `harmonize.records_from` (contract-shaped records; `WITNESS_DISAGREEMENT` when S > 2; the combined sd is multiplied by max(S, 1)), `validation_a1.restrict_witness` (single-witness paths), `validation_e1_s1.verdict_for` and `baselines` (D-028 verdict rules, step 3 with the raw refinement of amendment A) and `box_cells`. Fire regions are the 14 GFED regions of `cells.fire_region` (UNASSIGNED is not a region). "Aqua-equivalent cell-days" are the unit of every estimate.

### 9.2 B2 planted sensor jump
1. **Entities.** Fire regions (14) and a pool of 2000 single cells drawn uniformly without replacement (numpy `default_rng(20261115)`) from the cells whose `fire_region` is a real region. Aggregated for 2012-01 to 2021-12 (S-NPP exists from 2012-01; 2021-12 is the end of NOAA-20's fit period).
2. **Unplanted records** (`records_from` on the unperturbed table) for every entity-month of that period whose upper bound sum over day/night of max over witnesses of e is at least 5 (an estimate is never larger than that bound, so no eligible month is lost).
3. **Eligible (entity, jump month d, witness w):** d in 2012-01 to 2021-10, and in each of the three months d, d+1, d+2 the unplanted record has an estimate of at least 5 Aqua-equivalent cell-days (the D-028 step 4 size), uses w, and uses at least one other witness.
4. **Trials:** 100 on regions and 100 on cells (200 in all, plan minimum 50), seed 20261115. A trial draws an entity uniformly among the entities with at least one eligible pair, then a pair (d, w) uniformly among that entity's eligible pairs, then the factor: |ln f| uniform on [ln 1.5, ln 3], multiplier f or 1/f with probability 1/2 each.
5. **Perturbation** (in memory, the products are not touched): for the rows of that entity and witness from month d to 2021-12 (both day and night): raw x f, e x f, vc x f, vr x f^2 (cell-days scale by f; the Poisson term follows the count, the ratio-error term follows the square). Records for months d to d+2 are recomputed with `records_from`.
6. **Flagged record:** the reason code `WITNESS_DISAGREEMENT` (S > 2) **or** a widened interval, defined as `disagreement_scale` >= 1.5 (the combined sd inflated by at least 50% by the disagreement rule). Detection of a trial: some record of d, d+1, d+2 is flagged ("within 3 months" = the jump month and the two after it).
7. **False flags, official reading:** the unplanted twin of each trial (same entity, same three months, no jump) is flagged by the same rule if any of the three months is. Rate = flagged twins / 200.
8. **PASS** when detection >= 90% **and** false-flag rate < 5% (both locked); FAIL if either is violated; INCONCLUSIVE only if fewer than 50 trials could be drawn. Wilson 95% intervals are reported next to both rates; the decision uses the point estimates, as the plan states.
9. **Supplementary, same thresholds, reported not decisive:** (a) `B2-CODE-ONLY`: flagged = `WITNESS_DISAGREEMENT` only; (b) `B2-FALSE-FLAG-MONTHLY`: share of eligible unplanted entity-months (all of the entities above, 2012-01 to 2021-12, at least 2 witnesses, estimate >= 5) that are flagged, and the share of entities flagged in any month; detection by region/cell, by witness, by |ln f| tercile and by the jump month are in `measured`.

### 9.3 C1 cross-satellite agreement
1. Series: for each fire region, the single-witness record frames of S-NPP and of NOAA-20 (`restrict_witness`, `records_from`, `aqua_from` default): the estimate is the day+night total in Aqua-equivalent cell-days with its sd (counting, kappa and ratio error; no disagreement scaling with one witness).
2. Unit: a fire-region-month in 2018-01 to 2021-12 where both witnesses have an estimate (complete months) and **both estimates are at least 5 Aqua-equivalent cell-days** (so that two zeros do not count as agreement).
3. **Agree within the combined 90% intervals** (official reading): |e_S - e_N| <= 1.645 x sqrt(sd_S^2 + sd_N^2) (the 90% interval of the difference; the two witnesses are treated as independent, which they are not entirely, because both ratios are relative to Aqua: limitation). Supplementary `C1-OVERLAP`: the two 90% intervals overlap (a more lenient reading).
4. **PASS** when the share of agreeing units is >= 85%; FAIL below; INCONCLUSIVE with fewer than 100 units. Per-region shares are reported.
5. **In-sample status, stated, not hidden:** S-NPP's fit is 2012-01 to 2016-12, so every month of 2018-2021 is out of sample for S-NPP (its holdout). NOAA-20's calibration is 2018-04 to 2021-12, so every month in the plan window with NOAA-20 data is IN SAMPLE for NOAA-20 (2018-01 to 2018-03 have no NOAA-20 data). There is no month in the plan window that is out of sample for both. The official entry therefore is the plan's reading; `C1-OUT-OF-SAMPLE-2022-2024` repeats the test on 2022-01 to 2024-04 (out of sample for both fits; it ends before the earliest VIIRS night drift onset, 2024-05), same criterion and threshold, supplementary only.

### 9.4 CTRL control at the satellite-change dates
1. Cells: the analysis cells with centre inside C8 = (W 20, S -20, E 35, N -8) (`box_cells`). Aggregated for 2003-01 to 2022-12.
2. Series: (a) **harmonized** (all witnesses, `records_from` default, D-005 irrelevant before 2024-05); (b) **Aqua-only** (Aqua rows only, `aqua_from` none).
3. Baselines (D-028, same calendar month, 2003-2022, p25/p50/p75 linear interpolation): the harmonized series is judged against the **harmonized** baseline (the product's own), the Aqua-only series against the **Aqua-measured** baseline (its own estimates). This is the reading of D-028 as written for each path and of the Aqua-measured baseline of D-029; `CTRL-SHARED-BASELINE` (supplementary) judges both against the same Aqua-measured baseline (the form A1 uses for C2-C6 under D-029).
4. Verdicts: `verdict_for` (D-028 order, amendment A with the raw combined cell-days of the month, for both series).
5. Evaluated months: the 25 months from 12 before to 12 after each change date, 2012-01 (2011-01 to 2013-01) and 2018-04 (2017-04 to 2019-04), inside the plan's analysis windows. The plan lists the first window as 2011-01 to 2013-12; the verdicts of the whole analysis windows are reported too (supplementary numbers in the report, not part of the status).
6. **Spurious** verdict: a month in the evaluated months where the harmonized verdict is `ABOVE_NORMAL` or `BELOW_NORMAL` and the Aqua-only verdict of the same month is not that same verdict ("absent from the Aqua-only series").
7. **PASS** when there is no spurious verdict **and** at least 12 of the evaluated months have a harmonized verdict of `ABOVE_NORMAL`, `BELOW_NORMAL` or `WITHIN_NORMAL` (otherwise the control had no power: INCONCLUSIVE); FAIL when there is at least one spurious verdict. All verdict counts, the spurious months and the Aqua-only verdicts of those months are listed.

### 9.5 Other
No result is invented; missing data stay missing; synthetic fixtures live in the tests only and are labelled SYNTHETIC. Reproducible by one command, `python pipeline/validation_b2_c1_ctrl.py all`; cached stages in `data/interim/T-024/` are skipped on a rerun, `--fresh` recomputes them.

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside section 4. In particular `pipeline/harmonize.py`, `calibration.py`, `holdout.py`, `verdicts.py`, `validation_a1.py`, `validation_b.py`, `validation_d.py`, `validation_e1_s1.py` and `docs/VALIDATION_PLAN.md` are imported, not edited.
- Do not touch `api/`, `app/` or `data/products/`.
- No secrets, no raw or interim data files committed, no push to `main`, no self-merge.
- Do not mark a validation as passed unless it ran; no thresholds changed after the results.

## 11. Acceptance criteria
From the tracker ("Results recorded, pass or fail"), made measurable: (1) B2, C1 and CTRL ran, each with a status and its numbers; (2) every choice of section 15 was written down before the first real run (this file is the first commit); (3) entries in the contract 6 shape exist; (4) the results file lists every number and every failure; (5) tests and ruff pass.

## 12. Required tests
`python -m pytest pipeline/tests/test_validation_b2_c1_ctrl.py -q -p no:cacheprovider`, `python -m ruff check pipeline/validation_b2_c1_ctrl.py pipeline/tests/test_validation_b2_c1_ctrl.py`, then the whole suite. SYNTHETIC tests with known answers: the perturbation scales exactly the rows it should and leaves the rest and the input table unchanged; a large jump in a witness of a large synthetic entity is flagged and the unplanted twin is not; sampling is reproducible and respects eligibility; the flag rule (code, widened, neither); the status logic of B2, C1 and CTRL on hand-made numbers; the C1 agreement on hand-made estimates (combined interval against overlap); the CTRL spurious logic on hand-made verdict series. Mutation checks: break a rule on purpose, confirm a test fails, restore.

## 13. Documentation updates
`docs/validation/T-024-results.md`. The tracker row only as stated in section 4. The Lead integrates the entries into `validation_results.json` (T-027) and `docs/VALIDATION_PLAN.md`.

## 14. Git branch and PR instructions
- Branch: `science/T-024-test-b2-c1-ctrl` from the latest `origin/main`
- First commit: this prompt file
- Draft PR early, ready at the end; never merge; commits with the contributor's own Git identity; no AI names or attribution (D-020)

## 15. [ASSUMPTION]s, out-of-scope and blocking issues (fixed before the first real run)
The plan is silent on the points below; each is the most literal and least favourable reading I found, and each is flagged for the Lead in the PR.
1. **B2 size and range of the jump.** Factor 1.5 to 3, up or down, log-uniform. A "random factor" has no range in the plan; a jump of 1.25 would be harder to see and one of 5 easier.
2. **B2 what is flagged.** `WITNESS_DISAGREEMENT` or `disagreement_scale` >= 1.5. The plan's "widened interval" cannot mean any widening (S > 1 is reached by chance in about 32% of two-witness months, so no rule could keep false flags under 5%); 1.5 is my choice. The code-only reading is reported as `B2-CODE-ONLY`.
3. **B2 false flags.** The official unit is the unplanted twin window (any flag in the same three months); the plan says "series" without a window. Under pure chance S > 2 occurs in about 4.6% of two-witness months (chi-square with one degree of freedom), so a three-month window has about 13% by chance alone: this reading may fail for that reason, and it is reported as such. The monthly rate and the share of entities flagged anywhere are reported as `B2-FALSE-FLAG-MONTHLY`.
4. **B2 minimum data.** At least 5 Aqua-equivalent cell-days in each of the three months and a second witness; trials where nothing could be flagged by construction (one witness) are not drawn. This excludes the cases that cannot succeed; the test therefore says how well the method works where a disagreement is detectable at all.
5. **B2 jump month granularity.** Jumps start at a month boundary; "within 3 months" is the jump month and the two after it.
6. **C1 units and rule.** Fire-region-months, 2018-01 to 2021-12, both estimates >= 5; combined interval = interval of the difference (quadrature), the less lenient of the two readings. Treating the two converted series as independent overstates the combined sd slightly (both are scaled to Aqua): limitation.
7. **C1 in-sample.** As in 9.3 item 5: no month of 2018-2021 is out of sample for both; the supplementary entry uses 2022-01 to 2024-04, which is outside the plan's window.
8. **CTRL baselines, series and months.** As in 9.4. The 25-month window is read from "+-12 months" and the analysis windows of 2a; a verdict is spurious only where the Aqua-only series does not give the same verdict.
9. **CTRL power rule.** At least 12 determinable harmonized months, else INCONCLUSIVE; fixed before the run.
10. The products are the v0.1 conversion. If T-020c is adopted, the tests re-run unchanged and v0.1 results stay visible.
11. Seeds: 20261115 for every random draw (the calibration seed 20261114 plus one).
