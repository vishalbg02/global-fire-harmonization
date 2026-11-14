# T-020: test A1 (real anomaly preserved, two independent paths): results

> Case C1, Indonesia (Sumatra + Kalimantan), Sep-Oct 2015. Run 2026-11-14 on the T-011/T-013 products on `main` (`cell_month_witness`, `cells`, `calibration`), method `harmonize.METHOD_VERSION` = `0.1.0-combined-no-baseline`.
> **PROVISIONAL.** Computed with a baseline built inside `pipeline/validation_a1.py` (the D-028 rules), because the T-014 products (baseline, `pct_of_normal`, verdicts) do not exist yet. **Formal status: `NOT_RUN` until the test is re-run on the T-014 products.** Labels: [VERIFIED] computed here, [ASSUMPTION] a reading chosen where the documents are silent, [HYPOTHESIS], [OPEN].

## 1. What was done
- **Case** (VALIDATION_PLAN section 2a): box W 95, S -6, E 119, N 4; analysis window 2015-06 to 2015-12; peak window 2015-09 to 2015-10. 548 analysis cells have their centre in the box [ASSUMPTION: centre in the box, edges included; ocean cells are included, they hold few detections].
- **Two independent paths** from `harmonize.aggregate()` and `harmonize.records_from()`, with `harmonize.py` untouched: the aggregated table is filtered to one witness before the records are built. Aqua-only keeps `AQUA_MODIS`; S-NPP-only keeps `SNPP_VIIRS`; NOAA-20 and Terra enter neither. Each path is a single-witness estimate (`SINGLE_WITNESS`), converted with the T-011 ratios (Aqua ratio 1), with the T-013 variance (phi, kappa, shared ratio errors).
- **Baseline per path** (D-028): same calendar month, 2003-2022, empirical p25/p50/p75 (linear interpolation) over the years that have an estimate; fewer than 15 of 20 years, or a median below 5 cell-days, gives no baseline; each path's baseline is built from its own estimates. The event year 2015 is inside the baseline, as D-028 says.
- **`pct_of_normal`** = estimate / baseline median x 100.
- **Criterion, as written** (thresholds locked, nothing tuned on the case): both paths above (or both below) normal; peak months at most 1 month apart; 90% intervals overlap. Definitions the plan does not fix [ASSUMPTION]: the peak month is the month of the largest `pct_of_normal` in the analysis window; a path's direction is its peak-window estimate (summed over Sep and Oct) against the summed p75 (above) or summed p25 (below); its interval is the peak-window estimate +/- 1.645 x sqrt(sum of the monthly variances), floored at 0, over the summed baseline medians (months treated as independent, which makes the interval narrower, so it is the stricter choice for "overlap"; the baseline's own uncertainty is not propagated, D-028); intervals that touch overlap.
- **Status rule** [ASSUMPTION]: PASS if all three hold; FAIL if both paths can be judged and one fails; INCONCLUSIVE if a path has no baseline or an incomplete peak window, or if both paths are within normal (no anomaly to preserve).

## 2. Result
**Provisional status under the literal D-028 reading: INCONCLUSIVE.** [VERIFIED] The S-NPP-only path cannot have a D-028 baseline: S-NPP starts in 2012, so at most 11 of the 20 baseline years (2012-2022) can have an estimate, and D-028 step 2 requires 15. Without a baseline there is no `pct_of_normal`, so the criterion cannot be applied to that path. The plan does not say how the S-NPP-only path gets a baseline before 2012 [OPEN, for the Lead]. Two exploratory readings are reported below; **neither is the formal reading**, and the outcome depends on which one is chosen.

| Reading | Aqua-only pct_of_normal (90% interval) | S-NPP-only pct_of_normal (90% interval) | Direction | Peak month (Aqua / S-NPP) | Intervals overlap | Provisional status |
|---|---|---|---|---|---|---|
| **Formal (D-028, each path its own baseline)** | 361.3 (328.6 to 394.0) | none (no baseline: 11 of 20 years at most) | Aqua ABOVE, S-NPP undefined | 2015-10 / none | not applicable | **INCONCLUSIVE** |
| Exploratory 1: S-NPP-only estimates against the Aqua-only path's 2003-2022 baseline | 361.3 (328.6 to 394.0) | 328.2 (298.3 to 358.0) | both ABOVE | 2015-10 / 2015-10 | yes | PASS (exploratory) |
| Exploratory 2: S-NPP-only against its own 2012-2022 baseline, minimum lowered from 15 to 10 years | 361.3 (328.6 to 394.0) | 588.9 (535.3 to 642.4) | both ABOVE | 2015-10 / 2015-10 | **no** | FAIL (exploratory) |

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
- **Only C1 was run.** [OPEN] The A1 family pass needs 5 of 6 cases (C1 to C6). The harness takes any of C1 to C6 as data (`python pipeline/validation_a1.py --case C2`), but only C1 was run here.
- The boxes are the Lead's (T-050), used as written; the 548-cell box includes ocean cells.

## 4. What is provisional until T-014
1. The baseline and `pct_of_normal` (built here, not the T-014 products; where the T-014 rules differ from D-028 as read here, T-014 wins).
2. The reading of how the S-NPP-only path gets a baseline (a decision for the Lead; this is why the formal status stays `NOT_RUN`).
3. The definitions in section 1 that the plan does not fix (peak month, direction, interval over the peak window).
4. The recorded entry has `status: "NOT_RUN"` and carries the computed result as `measured.provisional_status`.

## 5. Recorded entry and re-run
- Entry (contract section 6 shape, git-ignored): `data/interim/qa/T-020_validation_entries.json`; tables: `data/interim/qa/T-020_a1_tables.json`. Test id `A1-C1`.
- Command: `python pipeline/validation_a1.py --case C1` (about 30 seconds).
- **After T-014 lands:** build the two `entity_month`-shaped frames for the box from the single-witness runs of the T-014 pipeline (columns `year`, `month`, `estimate`, `sd`, `baseline_median`, `baseline_p25`, `baseline_p75`, `pct_of_normal`), restrict each to the analysis window, and call `validation_a1.compare_paths(aqua_frame, snpp_frame, case["analysis"], case["peak"])` (and `entry_for` with those frames). Set `status` in the recorded entry to the returned status only once the Lead has confirmed that the T-014 baseline for the S-NPP-only path is the intended one.
- Tests: `python -m pytest pipeline/tests/test_validation_a1.py -q -p no:cacheprovider`.
