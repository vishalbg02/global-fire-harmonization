# T-025 results: tests E1 (leave one region out) and S1 (sensitivity)

> Run on the final T-011 products, 2026-11-15, with `python pipeline/validation_e1_s1.py all` (code and tests: `pipeline/validation_e1_s1.py`, `pipeline/tests/test_validation_e1_s1.py`; task prompt: `docs/task-prompts/T-025-test-e1-s1.md`). Thresholds are the ones locked at G1 (D-028) and the rules written in the task prompt before any result; none was changed after seeing the numbers. Labels: [VERIFIED] measured here, [ASSUMPTION], [HYPOTHESIS], [OPEN].

## 1. Verdicts

| Test | Status | In one line |
|---|---|---|
| **E1** generalization (leave one region out) | **PASS** | Our conversion beats the naive raw merge in 14 of 14 regions (threshold: at least 11 of 14). But see 3.3: this is a weak bar, and the leave-out error is 2 to 6 times the error with the region seen. |
| **S1-BASELINE** (Aqua-measured baseline instead of the harmonized baseline) | **FAIL** (by the strict rule fixed in advance) | 12 of 13 peak-window verdicts of C1 to C6 are unchanged; one changes (C2, 2019-09, `CANNOT_DETERMINE` to `BELOW_NORMAL`). |
| **S1-CONFIDENCE-FILTER** (A1 and B1 without the confidence filter) | **NOT_RUN** | Needs data and tests that do not exist yet (section 5). |
| **S1** as a whole (VALIDATION_PLAN.md) | **NOT_RUN** | Half of it cannot run yet. The half that ran is reported above as S1-BASELINE. |

Entries in the contract section 6 shape: `data/interim/qa/T-025_validation_entries.json` (not committed; the Lead integrates them).

## 2. What was done

### E1
1. For each of the 14 GFED fire regions R (`cells.fire_region`; UNASSIGNED is not a region) the S-NPP calibration (`calibration.calibrate()`, unchanged, 1,000 bootstrap replicates, seed 20261114) was fitted again **without R**. The files handed to the fit were written fresh and audited: no cell of R in `cells.parquet`, no row of R in the cell-month table, no year after 2016, only Aqua and S-NPP rows [VERIFIED by `audit_fit_products`, which raises otherwise]. The S-NPP fit period is 2012-01 to 2016-12; nothing from 2017 on enters any fit. NOAA-20 is not refitted (its fit period, 2018-04 to 2021-12, lies inside the holdout window, and E1 predicts from S-NPP).
2. R is converted as an unseen region is: its strata take the global ratio and global ratio_sd of the fit without R (a data-less phantom UNASSIGNED stratum is added to the fit input; the pooling gives it exactly the global estimate; the check against the independently computed global ratio without R agrees to 2e-16 in all 14 regions).
3. The converted S-NPP series of R in 2017-01 to 2021-12 (`harmonize.aggregate`, the T-013 aggregation) is compared with R's Aqua series in the units of the T-012 holdout: fire-region-months, complete months of both witnesses, at least 20 Aqua cell-days, day (D) and night (N) separately, plus the day+night total (T). The unit counts equal those of the T-012 report in every region and part [VERIFIED].
4. Predictions: **ours** (leave-out conversion), **raw** (the naive raw merge: raw S-NPP cell-days), **glob** (one global ratio per day/night and season, whole globe including R, fitted on 2012-2016, as in T-012), **gloo** (the same global ratio fitted without R).
5. Metric: median absolute log error (MALE) of predicted against actual Aqua cell-days, with a floor of one cell-day for a zero prediction (as T-012).
6. Rule fixed in advance: a region wins when ours has a lower MALE than raw in day and in night (each part counted only with at least 12 units; a tie is not a win). PASS needs at least 11 wins of 14; FAIL if even counting every not-evaluable region as a win there are fewer than 11; otherwise INCONCLUSIVE.

### S1 (the part that can run)
The verdict rules of D-028 (fixed order; probability from a Normal truncated at 0; p25/p50/p75 with linear interpolation; 15 of 20 baseline years; p50 of at least 5 cell-days; and so on) were applied to the harmonized estimate series (T-013, `harmonize.records_from`, D-005 default) of the 14 fire regions (120 months each), Canada, and the case boxes C1 to C6 of `docs/VALIDATION_PLAN.md` section 2a, for the months 2012-01 to 2021-12, in two ways: with the harmonized baseline (same calendar month, 2003-2022) and with the Aqua-measured baseline (2003-2021, Aqua-only estimates from the same aggregation). The estimate being judged is the harmonized one in both; only the baseline changes. Rule fixed in advance: PASS if the verdict is identical in every peak-window month of C1 to C6; any change is reported.

## 3. E1 results (all 14 regions, nothing left out)

### 3.1 Median absolute log error (lower is better)
| Region | D units | N units | D ours | D raw | D glob | D gloo | N ours | N raw | N glob | N gloo | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| AUST | 60 | 60 | 0.343 | 0.905 | 0.335 | 0.343 | 0.558 | 2.636 | 0.509 | 0.558 | WIN |
| BOAS | 50 | 38 | 0.367 | 0.875 | 0.352 | 0.367 | 0.494 | 2.957 | 0.461 | 0.494 | WIN |
| BONA | 56 | 30 | 0.293 | 0.938 | 0.292 | 0.293 | 0.625 | 2.578 | 0.622 | 0.625 | WIN |
| CEAM | 60 | 43 | 0.373 | 1.631 | 0.367 | 0.373 | 0.311 | 2.961 | 0.309 | 0.311 | WIN |
| CEAS | 60 | 55 | 0.126 | 1.204 | 0.121 | 0.126 | 0.818 | 3.542 | 0.795 | 0.818 | WIN |
| EQAS | 60 | 31 | 0.438 | 1.640 | 0.433 | 0.438 | 0.431 | 2.794 | 0.408 | 0.431 | WIN |
| EURO | 60 | 33 | 0.134 | 1.348 | 0.134 | 0.134 | 0.226 | 2.916 | 0.223 | 0.226 | WIN |
| MIDE | 60 | 57 | 0.348 | 1.574 | 0.347 | 0.348 | 0.271 | 3.038 | 0.269 | 0.271 | WIN |
| NHAF | 60 | 50 | 0.310 | 1.422 | 0.164 | 0.310 | 0.257 | 3.025 | 0.205 | 0.257 | WIN |
| NHSA | 60 | 38 | 0.306 | 1.546 | 0.295 | 0.306 | 0.322 | 2.749 | 0.290 | 0.322 | WIN |
| SEAS | 60 | 41 | 0.397 | 1.627 | 0.359 | 0.397 | 0.976 | 3.908 | 0.924 | 0.976 | WIN |
| SHAF | 60 | 58 | 0.273 | 1.559 | 0.263 | 0.273 | 0.660 | 3.154 | 0.476 | 0.660 | WIN |
| SHSA | 60 | 60 | 0.117 | 1.168 | 0.120 | 0.117 | 0.667 | 2.277 | 0.542 | 0.667 | WIN |
| TENA | 60 | 42 | 0.266 | 0.995 | 0.260 | 0.266 | 0.731 | 3.116 | 0.708 | 0.731 | WIN |

Units are fire-region-months with at least 20 Aqua cell-days in 2017-2021 (D: day, N: night). Every region wins in both parts. [VERIFIED]

### 3.2 Median predicted / actual, day+night total error, and 90% coverage of ours
Median of (predicted / actual); 1.00 is unbiased. Coverage is the share of units whose Aqua value lies inside the 90% interval of ours (T-013 variance, as in T-012); it is not an E1 criterion.

| Region | D ours | D raw | D glob | N ours | N raw | N glob | T (D+N) MALE ours | T MALE raw | 90% coverage D / N / T (ours) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| AUST | 0.71 | 2.47 | 0.72 | 0.75 | 13.96 | 0.79 | 0.399 | 1.239 | 0.33 / 0.33 / 0.28 |
| BOAS | 0.70 | 2.40 | 0.71 | 0.99 | 19.24 | 1.06 | 0.409 | 1.159 | 0.24 / 0.32 / 0.16 |
| BONA | 0.77 | 2.55 | 0.77 | 0.86 | 13.17 | 0.86 | 0.350 | 1.218 | 0.48 / 0.33 / 0.37 |
| CEAM | 1.45 | 5.11 | 1.44 | 1.07 | 19.32 | 1.07 | 0.275 | 1.695 | 0.30 / 0.65 / 0.42 |
| CEAS | 1.02 | 3.33 | 1.02 | 2.27 | 34.53 | 2.22 | 0.117 | 1.490 | 0.80 / 0.18 / 0.80 |
| EQAS | 1.55 | 5.16 | 1.54 | 0.81 | 16.35 | 0.84 | 0.337 | 1.704 | 0.10 / 0.55 / 0.19 |
| EURO | 1.10 | 3.85 | 1.10 | 1.18 | 18.47 | 1.17 | 0.136 | 1.578 | 0.73 / 0.64 / 0.76 |
| MIDE | 1.42 | 4.83 | 1.42 | 1.17 | 20.87 | 1.16 | 0.316 | 1.967 | 0.37 / 0.67 / 0.40 |
| NHAF | 1.14 | 4.15 | 1.13 | 1.24 | 20.59 | 1.13 | 0.186 | 1.473 | 0.43 / 0.70 / 0.54 |
| NHSA | 1.36 | 4.69 | 1.34 | 0.79 | 15.62 | 0.80 | 0.198 | 1.585 | 0.35 / 0.71 / 0.53 |
| SEAS | 1.49 | 5.09 | 1.43 | 2.65 | 49.81 | 2.52 | 0.384 | 1.806 | 0.25 / 0.10 / 0.17 |
| SHAF | 1.31 | 4.76 | 1.30 | 1.86 | 23.44 | 1.52 | 0.288 | 1.617 | 0.45 / 0.36 / 0.47 |
| SHSA | 0.99 | 3.22 | 1.00 | 0.51 | 9.75 | 0.58 | 0.131 | 1.339 | 0.78 / 0.10 / 0.75 |
| TENA | 0.77 | 2.71 | 0.78 | 1.27 | 22.64 | 1.25 | 0.291 | 1.270 | 0.43 / 0.26 / 0.33 |

### 3.3 Reading E1 correctly
- **Passing is the weak bar [VERIFIED numbers, interpretation labelled].** The raw merge is the unconverted S-NPP count, which is about 2.4 to 5.2 times Aqua by day and 10 to 50 times Aqua by night (median predicted / actual, table 3.2). Any conversion near the right scale beats it, so 14 of 14 mainly says that the S-NPP-to-Aqua scale is similar enough across regions that a ratio fitted elsewhere removes most of the level difference. It does not say the conversion is accurate in an unseen region.
- **What the leave-out costs [VERIFIED].** Against the T-012 result for the same regions (same units, region seen in the fit; values from `data/interim/qa/holdout_report.json` of the T-012 run):

| Region | D ours (T-012, region seen) | D ours (leave-out) | D raw | N ours (T-012, region seen) | N ours (leave-out) | N raw |
|---|---:|---:|---:|---:|---:|---:|
| AUST | 0.064 | 0.343 | 0.905 | 0.251 | 0.558 | 2.636 |
| BOAS | 0.090 | 0.367 | 0.875 | 0.304 | 0.494 | 2.957 |
| BONA | 0.115 | 0.293 | 0.938 | 0.437 | 0.625 | 2.578 |
| CEAM | 0.070 | 0.373 | 1.631 | 0.217 | 0.311 | 2.961 |
| CEAS | 0.065 | 0.126 | 1.204 | 0.444 | 0.818 | 3.542 |
| EQAS | 0.113 | 0.438 | 1.640 | 0.290 | 0.431 | 2.794 |
| EURO | 0.146 | 0.134 | 1.348 | 0.281 | 0.226 | 2.916 |
| MIDE | 0.164 | 0.348 | 1.574 | 0.162 | 0.271 | 3.038 |
| NHAF | 0.096 | 0.310 | 1.422 | 0.083 | 0.257 | 3.025 |
| NHSA | 0.075 | 0.306 | 1.546 | 0.156 | 0.322 | 2.749 |
| SEAS | 0.084 | 0.397 | 1.627 | 0.314 | 0.976 | 3.908 |
| SHAF | 0.086 | 0.273 | 1.559 | 0.105 | 0.660 | 3.154 |
| SHSA | 0.088 | 0.117 | 1.168 | 0.112 | 0.667 | 2.277 |
| TENA | 0.093 | 0.266 | 0.995 | 0.362 | 0.731 | 3.116 |

  The leave-out MALE is higher than the seen-region MALE in 13 of 14 regions, in both day and night; only EURO is lower in both. It is 2 to 6 times higher in many regions (for example AUST day 0.343 against 0.064, SHAF night 0.660 against 0.105). The median night prediction is too high by a factor of 2.3 and 2.7 in CEAS and SEAS and too low by a factor of 0.5 to 0.8 in SHSA, EQAS and NHSA (table 3.2).
- **ours and gloo are the same thing here [VERIFIED].** For an unseen region the T-011 method has nothing regional to use, so its prediction is the global ratio of the fit without R times raw S-NPP; its MALE equals that of `gloo` to the digits shown. E1 therefore also tests the one-global-ratio baseline in the leave-out setting. `glob` (global ratio with R inside the fit) is a little better in most regions and clearly better in NHAF (day 0.164 against 0.310), SHAF (night 0.476 against 0.660) and SHSA (night 0.542 against 0.667): a large region contributes to the global ratio it is then judged with.
- **The uncertainty is too narrow for an unseen region [VERIFIED numbers; cause is a HYPOTHESIS].** The 90% interval covers only 10% to 80% of the units across the regions (table 3.2; the plan's D1 range for coverage is 80% to 97%). The intervals carry the counting noise and the sd of the global ratio, but not a region-to-region spread of the ratio. [HYPOTHESIS] A between-region variance term is missing for regions without their own ratio; E1 was not designed to test this and no fix was attempted. [OPEN] for the Lead: whether an unseen-region interval needs one before verdicts are shown for such areas. This is separate from test D1 (T-022).
- **Variance model not refitted.** The overdispersion phi and kappa (`harmonize.PHI`, `KAPPA`) were estimated once on country-months of the fit periods of all regions. They were not re-estimated without R, so the coverage numbers are not a clean leave-one-out test of the variance model [ASSUMPTION: the effect is small, not measured].

## 4. S1 results (baseline half)

### 4.1 Peak-window months of the cases (the pass/fail months)
| Case | Month | Estimate (cell-days, Aqua-equivalent) | Verdict, harmonized baseline | Verdict, Aqua baseline | p50 harmonized | p50 Aqua | Unchanged |
|---|---|---:|---|---|---:|---:|---|
| C1 | 2015-09 | 14558 | ABOVE_NORMAL | ABOVE_NORMAL | 6076 | 6393 | yes |
| C1 | 2015-10 | 11152 | ABOVE_NORMAL | ABOVE_NORMAL | 1424 | 1548 | yes |
| C2 | 2019-08 | 18464 | WITHIN_NORMAL | WITHIN_NORMAL | 15346 | 15524 | yes |
| C2 | 2019-09 | 14729 | CANNOT_DETERMINE (WIDE_INTERVAL) | BELOW_NORMAL | 19521 | 20498 | **NO** |
| C3 | 2020-08 | 3131 | ABOVE_NORMAL | ABOVE_NORMAL | 1278 | 1292 | yes |
| C3 | 2020-09 | 4354 | ABOVE_NORMAL | ABOVE_NORMAL | 2113 | 2366 | yes |
| C3 | 2020-10 | 2357 | ABOVE_NORMAL | ABOVE_NORMAL | 1170 | 1269 | yes |
| C4 | 2019-12 | 4333 | ABOVE_NORMAL | ABOVE_NORMAL | 130 | 125 | yes |
| C4 | 2020-01 | 3378 | ABOVE_NORMAL | ABOVE_NORMAL | 160 | 167 | yes |
| C5 | 2020-08 | 1293 | ABOVE_NORMAL | ABOVE_NORMAL | 538 | 543 | yes |
| C5 | 2020-09 | 2380 | ABOVE_NORMAL | ABOVE_NORMAL | 269 | 353 | yes |
| C6 | 2021-07 | 18686 | ABOVE_NORMAL | ABOVE_NORMAL | 3597 | 3552 | yes |
| C6 | 2021-08 | 17777 | ABOVE_NORMAL | ABOVE_NORMAL | 1518 | 1914 | yes |
| C7 | 2023-06 | 9514 | ABOVE_NORMAL | ABOVE_NORMAL | 1049 | 1074 | yes |
| C7 | 2023-07 | 12800 | ABOVE_NORMAL | ABOVE_NORMAL | 1957 | 1784 | yes |

C7 (Canada 2023) is outside the pre-registered window and not part of the status; it is shown for information. [VERIFIED]

**Verdict: FAIL by the rule fixed in advance**, because of one month: C2 (Brazilian Amazon) 2019-09. With the harmonized baseline the estimate (14,729 cell-days) gives `CANNOT_DETERMINE` (`WIDE_INTERVAL`: no probability reaches 0.8); with the Aqua baseline (percentiles shifted slightly) the probability of "below" crosses 0.8 and the verdict is `BELOW_NORMAL`. The 12 other months (C1, C3, C4, C5, C6 and the other C2 month) keep the same verdict, and every `ABOVE_NORMAL` is the same under both baselines. The baseline medians differ by -4% to +31% in these months (the largest: C5 2020-09, 269 against 353; C6 2021-08, 1518 against 1914). The change is a borderline case between a non-committal and a committed verdict, not a reversal from above to below normal, but the rule was strict and the status is FAIL [ASSUMPTION: "unchanged" is read strictly; the plan says "report any that change"].

### 4.2 All entity-months, 2012-01 to 2021-12 (information, no threshold)
| Entity type | Entity-months | Same verdict | Changed | Median relative difference of p50 (Aqua vs harmonized) | 95th percentile of the absolute difference |
|---|---:|---:|---:|---:|---:|
| CASE | 720 | 85.0% | 108 | +0.6% | 100.0% |
| COUNTRY | 120 | 88.3% | 14 | +1.4% | 18.7% |
| REGION | 1680 | 85.3% | 247 | +0.7% | 12.1% |

"Same verdict" is the share of entity-months with the same verdict under both baselines. For the 14 regions the 247 changes are: `CANNOT_DETERMINE` to `WITHIN_NORMAL` 84, `WITHIN_NORMAL` to `CANNOT_DETERMINE` 47, `CANNOT_DETERMINE` to `BELOW_NORMAL` 47, `CANNOT_DETERMINE` to `ABOVE_NORMAL` 34, `BELOW_NORMAL` to `CANNOT_DETERMINE` 21, `ABOVE_NORMAL` to `CANNOT_DETERMINE` 13, `ABOVE_NORMAL` to `WITHIN_NORMAL` 1. No month switches directly between `ABOVE_NORMAL` and `BELOW_NORMAL` in the regions, Canada or the boxes; in the six boxes `ABOVE_NORMAL` to `WITHIN_NORMAL` occurs twice and `WITHIN_NORMAL` to `BELOW_NORMAL` once (counts per transition are in `T-025_s1_report.json`). [VERIFIED]

## 5. NOT_RUN, and why
- **S1 without the confidence filter (A1 and B1 re-run).** It needs the raw FIRMS archive regridded without the T-005 confidence filter (the products contain filtered data only), and the A1 and B1 tests it re-runs (T-020, T-021) do not exist yet. Status NOT_RUN.
- **S1 verdict agreement with the T-014 products.** The T-014 baseline products do not exist. `compare_baselines()` already takes entity_month-shaped frames (so it runs on the T-014 products and an Aqua-only equivalent), and `crosscheck_with_t014()` compares the verdict function used here with the T-014 `verdict` column. Neither was run on T-014 output. Until then the verdicts of 4.1 and 4.2 are computed with this task's own implementation of D-028, not with the T-014 one [ASSUMPTION: the implementations agree; the cross-check will show].
- **S1 overall.** NOT_RUN while a half is missing (the plan's S1 is "A1 and B1, without the confidence filter and with the Aqua baseline").

## 6. Limitations
- E1 uses Aqua as the reference (no ground truth) and tests one pair of witnesses (S-NPP against Aqua). NOAA-20 was not left out by region.
- The naive raw merge is a very weak baseline for this metric (3.3); a comparison with `gloo` or with the seen-region fit is more informative. Both are reported, but the pass criterion is the plan's.
- The median absolute log error is a robust measure: it hides a few large misses. The 5th and 95th percentiles of predicted / actual are in `T-025_e1_report.json`.
- 14 regions, 30 to 60 units each (night has the fewer units). Months of one region are autocorrelated, so the units are not independent.
- S1: the baseline half uses 14 regions, Canada and 6 boxes, not every country or the globe. The harmonized and Aqua-only series come from the same aggregation and share the Aqua data, so they differ only where VIIRS adds to the combination (2012 onward). The estimate judged is the harmonized one (a baseline sensitivity, not a re-estimation). The Aqua-only series in 2012-2021 is Aqua as measured, with no drift correction.
- The baseline percentiles carry no uncertainty (D-028 limitation kept).
- The DuckDB aggregation sums in parallel, so a float sum can differ in its last digit between runs (relative differences near 1e-16); the calibration itself is exactly reproducible for a fixed seed.

## 7. Assumptions made without the Lead (no one was available) [ASSUMPTION]
1. The win rule: ours must beat raw in **both** day and night (each with at least 12 units); a tie is not a win. Strict on purpose.
2. A region left out is converted with the global ratio of the fit without it (the only thing an unseen region has under the T-011 pooling).
3. E1 refits S-NPP only; NOAA-20 is not refitted.
4. Units and the 20 cell-day threshold are those of T-012; the global-ratio baseline is reported with and without the region.
5. S1 is judged strictly (any change in a peak-window month of C1 to C6 is a FAIL), on 2012-2021 months, with the Aqua-only series built by `harmonize.records_from` on the Aqua rows with Aqua kept in every month.
6. The overall S1 status is NOT_RUN, with the baseline half recorded as its own entry S1-BASELINE.

## 8. How to re-run
```
python pipeline/validation_e1_s1.py all            # E1 (about 25 minutes: 14 calibrations with 1,000 replicates) and S1 (a few minutes)
python pipeline/validation_e1_s1.py e1 --boot 200  # faster E1, a different bootstrap resolution
python pipeline/validation_e1_s1.py entries        # rebuild the entries file from the two reports
python -m pytest pipeline/tests/test_validation_e1_s1.py -q -p no:cacheprovider
```
Outputs (git-ignored): `data/interim/qa/T-025_e1_report.json`, `T-025_s1_report.json`, `T-025_validation_entries.json`. Temporary folders `data/interim/_e1_tmp` and `_s1_tmp` are removed at the end of a run.
