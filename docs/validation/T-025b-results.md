# T-025b: S1, confidence-filter half (A1 and B1 without the confidence filter)

> Task prompt: `docs/task-prompts/T-025b-s1-confidence.md` (feasibility check in section 7, decision rule in section 9, both written before the run). Products: v0.1 on main (T-011 ratios, `data/products/`, not changed). Entries: `data/interim/qa/T-025b_validation_entries.json` (not committed; T-027 merges them). All numbers in `data/interim/qa/T-025b_report.json`.

## 1. Result

| Entry | Status | Headline |
|---|---|---|
| **S1-CONFIDENCE-FILTER** | **PASS** (by the strict rule fixed in advance) | 22 of 22 compared conclusions are unchanged without the confidence filter: the A1 status of C1 to C6 (6), the A1 family (1), the B1 status at 2012-01 and 2018-04 (2), the verdict of every peak-window month of C1 to C6 (13). |
| **S1** as a whole | **FAIL** | S1-BASELINE (T-025) is FAIL; S1 fails when either half fails. The confidence-filter half does not change that. |

How to read the PASS (important, verified from the numbers below): it says the conclusions do not depend on the confidence filter. It does **not** say A1 passes. A1 is FAIL (family) with the filter and FAIL without it; four cases fail and two are inconclusive in both runs. "Unchanged" is partly a floor effect: a FAIL stays a FAIL under a small shift. The numbers moved by a few percent, listed in section 4, are the more informative result.

## 2. What was done
1. **Feasibility (verified before running):** the normalized detections (6.3 GB, with `confidence_class`), the static mask and the raw archive are on disk; the confidence filter is one condition in the T-006 kept set; the restricted regridding costs minutes. Full reasoning in the task prompt, section 7.
2. **Regridding (private, `data/interim/T-025b/`, nothing in `data/products/`):** as `gridding.observe_year` (fine 0.05 degree cell-days, analysis 0.5 degree cell-months, zero-filled, ALL = D + N), for the rows A1 and B1 read: the cells of the six case boxes in the 220 A1 months (analysis windows and the same calendar months 2003-2022), and every cell in the 48 B1 months (2011-01 to 2012-12, 2017-04 to 2019-03). 31,024,968 rows per table. About 5 minutes for both builds (control and unfiltered), plus about 1 minute for the harness runs.
3. **Control (validity gate, passed):** the same code with the confidence filter reproduces the product rows of the selection exactly: 31,024,968 of 31,024,968 rows joined, 0 differences in `cell_days`, `detections` and `frp_sum_mw`; 89,966,148 cell-days on both sides [VERIFIED]. So the only difference between the two runs is the confidence condition.
4. **Re-run, code of the earlier tasks unchanged:** A1 (`validation_a1.build_case_frames`, `entry_for`, `family_entry`), B1 (`validation_b.evaluate_b1`, `b1_status`, as `validation_b.run`: 14 fire regions plus NONE excluded), peak-window verdicts (`validation_e1_s1.verdict_for` and `baselines`, harmonized baseline 2003-2022 of the case-box series). The filtered side reproduces the stored T-020 statuses exactly (C1 INCONCLUSIVE, C2 INCONCLUSIVE, C3 to C6 FAIL, family FAIL) [VERIFIED].
5. **Rule (fixed before the run):** PASS if all 22 conclusions are unchanged; FAIL if any changes; INCONCLUSIVE if a part cannot be computed; NOT_RUN if the control fails.

## 3. A1 (official reading per case: C1 own baseline, C2 to C6 shared Aqua baseline)

| Case | Status filtered | Status unfiltered | Aqua % of normal (f / u) | S-NPP % of normal (f / u) | S-NPP 90% interval filtered | unfiltered | Aqua interval |
|---|---|---|---|---|---|---|---|
| C1 | INCONCLUSIVE | INCONCLUSIVE | 361.3 / 364.4 | no baseline (both) | n/a | n/a | n/a |
| C2 | INCONCLUSIVE | INCONCLUSIVE | 94.6 / 94.5 | 86.1 / 87.8 | 77.7-94.5 | 79.2-96.5 | 85.4-103.8 |
| C3 | FAIL | FAIL | 253.1 / 258.4 | 191.9 / 199.1 | 176.2-207.6 | 182.8-215.5 | 233.0-273.2 |
| C4 | FAIL | FAIL | 3962.9 / 4067.9 | 2313.9 / 2280.4 | 2095.6-2532.3 | 2065.0-2495.9 | 3596.4-4329.4 |
| C5 | FAIL | FAIL | 637.1 / 640.2 | 375.6 / 367.8 | 334.6-416.7 | 327.7-407.9 | 571.1-703.1 |
| C6 | FAIL | FAIL | 805.2 / 807.5 | 644.8 / 601.6 | 584.1-705.6 | 544.8-658.4 | 733.3-877.1 |

A1 family: FAIL in both. The reasons are the same in both runs: in C3 to C6 the two paths have the same direction (above normal) and the same peak month, but their 90% intervals do not overlap; C1 has no S-NPP baseline; C2 is within normal on both paths. The unfiltered S-NPP-only path is closer to Aqua in C2 and C3 (+1.7 and +7.2 points) and further in C6 (-43 points), but never enough to change a status.

## 4. B1 (fire regions, 14 with enough data at both dates)

| Date | Status f / u | Regions within +-10% (f / u) | Median harmonized step (f / u) | Median raw step (f / u) |
|---|---|---|---|---|
| 2012-01 (S-NPP enters) | PASS / PASS | 14 of 14 / 14 of 14 | 0.991 / 0.999 | 3.293 / 3.349 |
| 2018-04 (NOAA-20 enters) | PASS / PASS | 13 of 14 / 13 of 14 | 1.024 / 1.028 | 1.769 / 1.777 |

The largest change of any region's harmonized step is 0.059 (BONA at 2012-01, 0.987 to 0.928, still within 10%) and 0.027 at 2018-04. The regions outside the tolerance at 2018-04 are the same with and without the filter.

## 5. Peak-window verdicts (13 months of C1 to C6)
All 13 verdicts are identical (for example C1 ABOVE_NORMAL, C2 2019-08 WITHIN_NORMAL, C2 2019-09 CANNOT_DETERMINE (`WIDE_INTERVAL`), C3 to C6 ABOVE_NORMAL). The estimate itself rises by about 1.5 to 7% without the filter (for example C3 2020-08: 3,130.6 to 3,341.5; C2 2019-08: 18,464.4 to 19,447.1 Aqua-equivalent cell-days), as expected when low-confidence VIIRS detections are added to numerators converted with ratios fitted on filtered counts.

## 6. Limitations and [ASSUMPTION]s
- [ASSUMPTION] The T-011 ratios are not refitted: the filter varies in the numerators only (task prompt 9.3). A refit without the filter would be a different test.
- [ASSUMPTION] The cell set is the product's. In the selection, 257 unfiltered detections fall in 230 cells that are not in `cells.parquet` (cells whose only detections have low confidence), and are not used. Their effect is negligible next to millions of cell-days, but it is not zero [VERIFIED count].
- The strict rule makes any single change a FAIL; none occurred. The PASS is a statement about robustness of the conclusions, which are mostly FAIL/INCONCLUSIVE already (section 1).
- Only the confidence condition was varied; the type filter and the D-025 static mask stay as in T-006.
- The comparison is on the v0.1 products on main. If the Lead adopts v0.2 (T-020c), the same command re-runs on the new products.
- A1 and B1 are re-run on selected cells and months only: B1 on the 14 fire regions, A1 on the six case boxes. Peak-window verdicts use the case-box series (harmonized baseline of the same series). Regions and countries elsewhere were not re-gridded.
- S1 as a whole is FAIL because S1-BASELINE (T-025) is FAIL (strict rule, one change at C2 2019-09, `CANNOT_DETERMINE` to `BELOW_NORMAL`); that result is not repeated here.

## 7. How to re-run
```
# takes the heavy lock first (data/interim/.heavy_lock); about 7 minutes (regridding cached in data/interim/T-025b)
python pipeline/validation_s1_confidence.py          # add --force to redo the regridding
python -m pytest pipeline/tests/test_validation_s1_confidence.py -q -p no:cacheprovider
```
