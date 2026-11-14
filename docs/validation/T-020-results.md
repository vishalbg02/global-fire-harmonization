# T-020: test A1 (real anomaly preserved, two independent paths): results

> Run 2026-11-15 on the T-011/T-013 products on `main` (`cell_month_witness`, `cells`, `calibration`), method `harmonize.METHOD_VERSION` = `0.1.0-combined-no-baseline`. The two single-witness paths and their baselines are built in `pipeline/validation_a1.py` (the T-014 product, PR #52, holds only the combined series; it is used for context and a cross-check, section 8). Labels: [VERIFIED] computed here, [ASSUMPTION] a reading chosen where the documents are silent, [HYPOTHESIS], [OPEN].
>
> **Official results.** C1: **INCONCLUSIVE**, as pre-registered (D-028). **D-029** (Lead, 2026-11-15; `docs/DECISION_LOG.md`) makes the shared Aqua-measured 2003-2022 baseline the baseline of both paths for **C2 to C6**. D-029 was adopted **after C1 had been run and its three readings seen**, and before C2 to C6 were run; it does not change C1's official result. **Family result: FAIL** (0 of 6 cases PASS; the plan needs at least 5; C1 counts as INCONCLUSIVE, not PASS).

| Case | Official reading | Aqua-only pct_of_normal (90%) | S-NPP-only pct_of_normal (90%) | Status |
|---|---|---|---|---|
| C1 Indonesia, Sep-Oct 2015 | D-028 as pre-registered | 361.3 (328.6 to 394.0) | none (no baseline) | **INCONCLUSIVE** |
| C2 Brazilian Amazon, Aug-Sep 2019 | D-029 | 94.6 (85.4 to 103.8) | 86.1 (77.7 to 94.5) | **INCONCLUSIVE** (both within normal) |
| C3 Pantanal, Aug-Oct 2020 | D-029 | 253.1 (233.0 to 273.2) | 191.9 (176.2 to 207.6) | **FAIL** (intervals do not overlap) |
| C4 SE Australia, Dec 2019-Jan 2020 | D-029 | 3962.9 (3596.4 to 4329.4) | 2313.9 (2095.6 to 2532.3) | **FAIL** (intervals do not overlap) |
| C5 California, Aug-Sep 2020 | D-029 | 637.1 (571.1 to 703.1) | 375.6 (334.6 to 416.7) | **FAIL** (intervals do not overlap) |
| C6 Sakha/Yakutia, Jul-Aug 2021 | D-029 | 805.2 (733.3 to 877.1) | 644.8 (584.1 to 705.6) | **FAIL** (intervals do not overlap) |
| **Family** | | | | **FAIL** (0 PASS, 4 FAIL, 2 INCONCLUSIVE of 6) |

## 1. What was done
- **Cases** (VALIDATION_PLAN section 2a; boxes, analysis and peak windows used as written). C1: box W 95, S -6, E 119, N 4; analysis window 2015-06 to 2015-12; peak window 2015-09 to 2015-10; 548 analysis cells have their centre in the box [ASSUMPTION: centre in the box, edges included; ocean cells are included, they hold few detections]. Cells per box: C2 1,191; C3 140; C4 296; C5 315; C6 2,174.
- **Two independent paths** from `harmonize.aggregate()` and `harmonize.records_from()`, with `harmonize.py` untouched: the aggregated table is filtered to one witness before the records are built. Aqua-only keeps `AQUA_MODIS`; S-NPP-only keeps `SNPP_VIIRS`; NOAA-20 and Terra enter neither. Each path is a single-witness estimate (`SINGLE_WITNESS`), converted with the T-011 ratios (Aqua ratio 1), with the T-013 variance (phi, kappa, shared ratio errors).
- **Baseline** (D-028; for C2 to C6 shared by both paths, D-029): same calendar month, 2003-2022, empirical p25/p50/p75 (linear interpolation) over the years that have an estimate; fewer than 15 of 20 years, or a median below 5 cell-days, gives no baseline; by D-028 each path's baseline is built from its own estimates, by D-029 (C2 to C6) both paths use the Aqua-only path's baseline. The event year 2015 is inside the baseline, as D-028 says.
- **`pct_of_normal`** = estimate / baseline median x 100.
- **Criterion, as written** (thresholds locked, nothing tuned on the case): both paths above (or both below) normal; peak months at most 1 month apart; 90% intervals overlap. Definitions the plan does not fix [ASSUMPTION]: the peak month is the month of the largest `pct_of_normal` in the analysis window; a path's direction is its peak-window estimate (summed over Sep and Oct) against the summed p75 (above) or summed p25 (below); its interval is the peak-window estimate +/- 1.645 x sqrt(sum of the monthly variances), floored at 0, over the summed baseline medians (months treated as independent, which makes the interval narrower, so it is the stricter choice for "overlap"; the baseline's own uncertainty is not propagated, D-028); intervals that touch overlap.
- **Not tuned.** Windows, boxes, thresholds and definitions are the same for every case and were fixed before any case was run; only the baseline choice of D-029 followed C1.
- **Status rule** [ASSUMPTION]: PASS if all three hold; FAIL if both paths can be judged and one fails; INCONCLUSIVE if a path has no baseline or an incomplete peak window, or if both paths are within normal (no anomaly to preserve).

## 2. Case C1 (three readings, unchanged)
**Official status: INCONCLUSIVE (D-028 as pre-registered).** [VERIFIED] The S-NPP-only path cannot have a D-028 baseline: S-NPP starts in 2012, so at most 11 of the 20 baseline years (2012-2022) can have an estimate, and D-028 step 2 requires 15. Without a baseline there is no `pct_of_normal`, so the criterion cannot be applied to that path. The plan does not say how the S-NPP-only path gets a baseline before 2012 [OPEN, for the Lead]. The other two readings are published beside it; **neither is C1's official result** (the shared baseline is D-029, adopted after C1 was seen).

| Reading | Aqua-only pct_of_normal (90% interval) | S-NPP-only pct_of_normal (90% interval) | Direction | Peak month (Aqua / S-NPP) | Intervals overlap | Provisional status |
|---|---|---|---|---|---|---|
| **Formal (D-028, each path its own baseline): OFFICIAL** | 361.3 (328.6 to 394.0) | none (no baseline: 11 of 20 years at most) | Aqua ABOVE, S-NPP undefined | 2015-10 / none | not applicable | **INCONCLUSIVE** |
| Shared Aqua baseline (the D-029 reading, adopted after C1) | 361.3 (328.6 to 394.0) | 328.2 (298.3 to 358.0) | both ABOVE | 2015-10 / 2015-10 | yes | PASS (not official) |
| Exploratory: S-NPP-only against its own 2012-2022 baseline, minimum lowered from 15 to 10 years | 361.3 (328.6 to 394.0) | 588.9 (535.3 to 642.4) | both ABOVE | 2015-10 / 2015-10 | **no** | FAIL (not official) |

[VERIFIED] In every reading the two paths agree on the direction (above normal) and on the peak month (October 2015). The estimates themselves agree closely: Aqua-only peak window 27,097 and S-NPP-only 24,614 Aqua-equivalent cell-days (S-NPP 9.2% lower), and the monthly series follow each other (table below). The only point where the result changes is the baseline.

### Estimates by month, Aqua-equivalent cell-days (estimate and sd) [VERIFIED]
| Month | Aqua-only | S-NPP-only (converted) |
|---|---|---|
| 2015-06 | 1273.0 (122.2) | 1460.4 (128.9) |
| 2015-07 | 3769.0 (317.7) | 3901.1 (322.6) |
| 2015-08 | 9441.0 (792.0) | 8968.3 (751.9) |
| 2015-09 | 15751.0 (1215.1) | 13638.0 (1064.6) |
| 2015-10 | 11346.0 (864.9) | 10976.2 (847.5) |
| 2015-11 | 1309.0 (119.7) | 1719.3 (143.5) |
| 2015-12 | 325.0 (39.5) | 327.8 (31.5) |

### Baselines (p25 / median / p75, cell-days; years with an estimate in brackets) and pct_of_normal [VERIFIED]
| Month | Aqua-only baseline (2003-2022) | Aqua pct | S-NPP-only own baseline (2012-2022) | S-NPP pct (own) | S-NPP pct (Aqua baseline) |
|---|---|---|---|---|---|
| 2015-06 | 331.0 / 1039.5 / 1856.2 (20) | 122.5 | 223.9 / 404.4 / 1562.7 (11) | 361.1 | 140.5 |
| 2015-07 | 814.8 / 1434.0 / 2609.5 (20) | 262.8 | 910.6 / 1174.6 / 2112.0 (10) | 332.1 | 272.0 |
| 2015-08 | 2250.2 / 4629.0 / 7744.5 (20) | 204.0 | 1912.9 / 4029.1 / 4611.3 (10) | 222.6 | 193.7 |
| 2015-09 | 1645.5 / 6076.0 / 8728.5 (20) | 259.2 | 1397.2 / 3031.9 / 8684.4 (11) | 449.8 | 224.5 |
| 2015-10 | 809.2 / 1424.0 / 2995.5 (20) | 796.8 | 807.2 / 1148.2 / 3160.4 (11) | 956.0 | 770.8 |
| 2015-11 | 135.2 / 236.0 / 618.0 (20) | 554.7 | 158.1 / 235.4 / 993.3 (11) | 730.5 | 728.5 |
| 2015-12 | 88.0 / 110.5 / 145.0 (20) | 294.1 | 96.6 / 105.8 / 126.0 (11) | 309.7 | 296.7 |

The S-NPP own-baseline columns are exploratory; in the formal reading they do not exist.

## 3. Caveats
- **Shared fires.** [VERIFIED by construction] Both paths measure the same fires; they are independent instruments with independent conversions, not independent events. Agreement shows that the conversion preserves a large real signal, not that either path is accurate in absolute terms.
- **Aqua is itself an estimate.** [VERIFIED] The Aqua-equivalent scale is a display scale (D-005); the Aqua path is Aqua cell-days with ratio 1, and the S-NPP path is a converted count. The ratios were fitted on 2012-2016 and 2018-2021, so 2015 lies inside the fit period of the conversion: the S-NPP agreement for 2015 is in-sample, not an out-of-sample result.
- **S-NPP baseline length.** [VERIFIED] 11 baseline years at most, and some months have 10 (a year without a complete month is dropped). The S-NPP own baseline covers a different period from the Aqua one. [HYPOTHESIS] The much lower S-NPP own medians (for example September, 3031.9 against 6076.0) come from the 2003-2011 years, which may include other strong Indonesian burning seasons that the S-NPP window lacks; not tested here.
- **Baseline uncertainty** is not propagated (D-028), and the 2015 event is itself one of the baseline years (D-028 as written), which makes `pct_of_normal` somewhat less extreme than against a baseline without it.
- **Peak-window interval** treats September and October as independent; the shared ratio error across months is not modelled, so the intervals are narrower than a fully correlated treatment would give. That is the stricter choice for the overlap condition.
- **Six cases, one region each.** [VERIFIED] Passing or failing A1 shows how the method behaves in these six boxes, not globally (VALIDATION_PLAN principle 4).
- The boxes are the Lead's (T-050), used as written; the boxes include ocean cells.

## 4. Cases C2 to C6 under D-029 [VERIFIED]
Peak window summed over its months; baseline = Aqua-only 2003-2022 (20 usable years in every month of every case). Peak month = month of the largest pct_of_normal in the analysis window.

| Case | Peak window | Direction (Aqua / S-NPP) | Peak month (Aqua / S-NPP) | Same direction | Peak within +-1 | Intervals overlap | Status |
|---|---|---|---|---|---|---|---|
| C2 | 2019-08, 09 | WITHIN / WITHIN | 2019-08 / 2019-06 | no anomaly | (2 apart) | yes | INCONCLUSIVE |
| C3 | 2020-08 to 10 | ABOVE / ABOVE | 2020-07 / 2020-07 | yes | yes (0) | **no** | FAIL |
| C4 | 2019-12, 2020-01 | ABOVE / ABOVE | 2019-12 / 2019-12 | yes | yes (0) | **no** | FAIL |
| C5 | 2020-08, 09 | ABOVE / ABOVE | 2020-09 / 2020-09 | yes | yes (0) | **no** | FAIL |
| C6 | 2021-07, 08 | ABOVE / ABOVE | 2021-08 / 2021-08 | yes | yes (0) | **no** | FAIL |

- **C2 is INCONCLUSIVE, not a fail** [VERIFIED]: both paths are within the 2003-2022 normal in the peak window (pct 94.6 and 86.1), so there is no anomaly in this record for the paths to preserve (the plan's rule as read here: both paths within normal gives INCONCLUSIVE). [HYPOTHESIS] The 2019 Amazon fire season was widely reported as exceptional, but the 2003-2022 baseline contains very high years of the 2000s, so 2019 is not extreme against it; not tested.
- **C3 to C6: direction and peak month agree in all four, the intervals do not overlap** [VERIFIED]. The converted S-NPP-only estimate is below the Aqua-only estimate in every peak window: the ratio S-NPP-only / Aqua-only of the peak-window estimate is 0.76 (C3), 0.58 (C4), 0.59 (C5), 0.80 (C6). In the C1 box the same ratio was 0.91. The monthly tables below show the gap is largest in the heaviest months (C4 Nov-Dec, C5 Sep, C6 Aug).
- [HYPOTHESIS] The conversion ratios (T-011) are fitted on typical months and applied here to extreme fire seasons; very intense fires or the different overpass times of Aqua and S-NPP may make the converted VIIRS count lower than Aqua in such months. Not tested here. [OPEN] The T-012 holdout and test D1 speak to calibration in ordinary months, not to extremes.
- **Sensitivity, not official and not used for any status:** the peak-window interval here assumes independent months (the stricter choice, section 1). If the months were fully correlated (standard deviations added), the intervals widen and only **C6** would overlap (Aqua 704 to 907, S-NPP 559 to 731, in percent of normal); C3, C4 and C5 would still not. Reported so that the Lead can see how much of the C6 result rests on that assumption.

### Monthly estimates and pct_of_normal under the shared baseline (Aqua-equivalent cell-days)
Columns: estimate Aqua-only / S-NPP-only; baseline p25 / median / p75 (Aqua-only, 20 years); pct_of_normal Aqua / S-NPP.

**C2**

| Month | Estimate Aqua / S-NPP | Baseline p25 / median / p75 | pct Aqua / S-NPP |
|---|---|---|---|
| 2019-05 | 967 / 1076 | 703 / 912 / 1054 | 106 / 118 |
| 2019-06 | 2406 / 2709 | 1919 / 2202 / 2512 | 109 / 123 |
| 2019-07 | 4513 / 4877 | 3887 / 4800 / 6213 | 94 / 102 |
| 2019-08 | 20146 / 18363 | 13200 / 16506 / 20808 | 122 / 111 |
| 2019-09 | 15721 / 14279 | 15621 / 21402 / 30837 | 73 / 67 |
| 2019-10 | 6463 / 8539 | 10441 / 12537 / 14994 | 52 / 68 |
| 2019-11 | 7904 / 8418 | 7053 / 8430 / 10788 | 94 / 100 |

**C3**

| Month | Estimate Aqua / S-NPP | Baseline p25 / median / p75 | pct Aqua / S-NPP |
|---|---|---|---|
| 2020-06 | 419 / 423 | 133 / 248 / 414 | 169 / 171 |
| 2020-07 | 1539 / 1380 | 334 / 520 / 751 | 296 / 265 |
| 2020-08 | 3722 / 2965 | 817 / 1266 / 2351 | 294 / 234 |
| 2020-09 | 5559 / 3757 | 1394 / 2213 / 3486 | 251 / 170 |
| 2020-10 | 2509 / 2218 | 955 / 1179 / 1478 | 213 / 188 |
| 2020-11 | 779 / 952 | 366 / 446 / 614 | 175 / 214 |

**C4**

| Month | Estimate Aqua / S-NPP | Baseline p25 / median / p75 | pct Aqua / S-NPP |
|---|---|---|---|
| 2019-09 | 1025 / 756 | 370 / 453 / 673 | 226 / 167 |
| 2019-10 | 722 / 486 | 160 / 286 / 372 | 253 / 170 |
| 2019-11 | 4517 / 2250 | 88 / 141 / 244 | 3204 / 1596 |
| 2019-12 | 6842 / 3532 | 70 / 123 / 190 | 5563 / 2871 |
| 2020-01 | 4373 / 3017 | 86 / 160 / 367 | 2733 / 1886 |
| 2020-02 | 587 / 395 | 166 / 210 / 306 | 279 / 188 |
| 2020-03 | 251 / 322 | 418 / 566 / 844 | 44 / 57 |

**C5**

| Month | Estimate Aqua / S-NPP | Baseline p25 / median / p75 | pct Aqua / S-NPP |
|---|---|---|---|
| 2020-06 | 108 / 151 | 97 / 116 / 168 | 94 / 131 |
| 2020-07 | 287 / 233 | 166 / 244 / 648 | 118 / 96 |
| 2020-08 | 1466 / 1327 | 201 / 541 / 989 | 271 / 245 |
| 2020-09 | 4188 / 2006 | 228 / 346 / 458 | 1209 / 579 |
| 2020-10 | 1088 / 690 | 194 / 286 / 366 | 380 / 241 |
| 2020-11 | 324 / 337 | 180 / 224 / 300 | 145 / 150 |

**C6**

| Month | Estimate Aqua / S-NPP | Baseline p25 / median / p75 | pct Aqua / S-NPP |
|---|---|---|---|
| 2021-05 | 289 / 368 | 129 / 170 / 354 | 171 / 217 |
| 2021-06 | 2901 / 2512 | 211 / 624 / 2248 | 465 / 403 |
| 2021-07 | 20635 / 17520 | 2242 / 3664 / 7198 | 563 / 478 |
| 2021-08 | 21094 / 15899 | 521 / 1518 / 5294 | 1390 / 1047 |
| 2021-09 | 2408 / 1727 | 104 / 186 / 693 | 1295 / 929 |

## 5. Family result
**FAIL** [VERIFIED]: 0 of the 6 cases PASS (C1 INCONCLUSIVE, C2 INCONCLUSIVE, C3 to C6 FAIL); the plan needs at least 5. C1 counts as INCONCLUSIVE, not PASS. A decided FAIL or INCONCLUSIVE case is final, so the family cannot reach 5. In C1 and C3 to C6 the direction and the peak month of the two paths agree; the stated uncertainty does not cover the gap between the paths in C3 to C6.

## 6. What the Lead must decide, and what remains open
1. **Reading of the result.** The intervals are the point of failure in C3 to C6. Whether the uncertainty of the S-NPP conversion should include a term for extreme months is a question for the T-013 variance, not for this test. No threshold was changed; any change to the variance or to the test must be logged and applied before the tests are re-run.
2. The peak-window definitions of section 1 (peak month, direction, interval over the peak window) are [ASSUMPTION]s that the Lead should confirm or amend. Under fully correlated months only C6 would change (section 4, sensitivity).
3. D-029 is applied as the Lead decided; C1 stays INCONCLUSIVE and the family is FAIL as recorded.
4. [OPEN] The recorded family entry uses FAIL with the counts; whether the app should word it as "not met" is for the Lead.

## 7. Recorded entries and re-run
- Entries (contract section 6 shape, git-ignored): `data/interim/qa/T-020_validation_entries.json`, one entry per case (`A1-C1` to `A1-C6`) plus `A1-FAMILY`; each case entry carries its official reading, the other readings (`measured.other_readings`) and its official `status`. Tables per case: `data/interim/qa/T-020_a1_tables_C1.json` and so on.
- Command (all six cases and the family, about 3 minutes): `python pipeline/validation_a1.py`; one case: `--case C3`.
- Which reading is official for which case is the explicit table `FORMAL_READING` in `pipeline/validation_a1.py` (C1: D-028 as pre-registered; C2 to C6: D-029).
- If the T-014 pipeline later produces single-witness series, build the two `entity_month`-shaped frames for a box (columns `year`, `month`, `estimate`, `sd`, `baseline_median`, `baseline_p25`, `baseline_p75`, `pct_of_normal`), restrict each to the analysis window and call `validation_a1.compare_paths(aqua_frame, snpp_frame, case["analysis"], case["peak"])`.
- The section 8 checks need `data/products/entity_month.parquet` and `metadata.json` of T-014 (uncommitted copies of PR #52); without them (or with the raw-only product) they are skipped and the rest runs unchanged.
- Tests: `python -m pytest pipeline/tests/test_validation_a1.py -q -p no:cacheprovider`.

## 8. Cross-check with the T-014 product (C1, Indonesia) (PR #52, method 0.1.0)
The product is a combined series for countries, continents and the world, so it cannot replace the two path series. It is used for two checks, both on the country entity `COUNTRY:IDN` (Indonesia, 1,047 analysis cells), which is a larger area than the C1 box (548 cells, which also takes in parts of Malaysia and Brunei); numbers differ from section 2 for that reason.

**(a) Context: the combined product for Indonesia, 2015** [VERIFIED]. Witnesses used: Aqua and S-NPP in every month shown.

| Month | Estimate | pct_of_normal | p_above | Verdict |
|---|---|---|---|---|
| 2015-06 | 1456.4 | 128.9 | 0.0000 | WITHIN_NORMAL |
| 2015-07 | 4229.3 | 264.5 | 1.0000 | ABOVE_NORMAL |
| 2015-08 | 10627.3 | 216.5 | 1.0000 | ABOVE_NORMAL |
| 2015-09 | 19068.7 | 264.9 | 1.0000 | ABOVE_NORMAL |
| 2015-10 | 17202.7 | 541.6 | 1.0000 | ABOVE_NORMAL |
| 2015-11 | 3039.2 | 428.1 | 1.0000 | ABOVE_NORMAL |
| 2015-12 | 1084.9 | 503.9 | 1.0000 | ABOVE_NORMAL |

With the same peak-window rules as section 1 the combined series is ABOVE normal, peak month 2015-10 (pct_of_normal 541.6), peak-window pct_of_normal 349.6 (90% interval 327.0 to 372.1). It agrees in direction and peak month with both paths (section 2), and its magnitude (349.6) lies between the S-NPP-only (328.2, Aqua baseline) and Aqua-only (361.3) values. The product's verdicts are ABOVE_NORMAL for every month from July to December.

**(b) Does the Aqua-only stand-in reproduce the product's baseline where only Aqua contributes?** [VERIFIED] For Indonesia (the whole 2003-2022 range, calendar months 1 to 12):
- **Estimates 2003-2011** (108 country-months): the Aqua-only path and the product's estimate are identical (maximum relative difference 0.0), as expected, since both are Aqua-only there.
- **Baseline over 2003-2011 only** (p25, p50, p75 built from the two series, same rules): identical for all 12 calendar months (maximum relative difference 0.0). So the stand-in's percentile rule reproduces the product's.
- **Baseline over the full 2003-2022**: the stand-in is Aqua-only throughout and the product is combined from 2012, so they differ by construction. The ratio of the medians (Aqua-only over product) is between 0.909 and 1.023 over the 12 months (median 0.993): Jan 1.007, Feb 0.940, Mar 0.992, Apr 1.020, May 0.994, Jun 1.000, Jul 0.989, Aug 1.023, Sep 1.000, Oct 0.982, Nov 0.909, Dec 0.948. For the peak months of C1 (September and October) the medians are 7199.5 against 7199.5 and 3120.5 against 3176.5.

This supports using the Aqua-only baseline of this module as the stand-in for the Aqua path, and, for exploratory reading 1, as the common baseline. [HYPOTHESIS] the small Nov and Dec differences reflect the VIIRS years entering the product's medians; not tested. The check was run for one country only.
