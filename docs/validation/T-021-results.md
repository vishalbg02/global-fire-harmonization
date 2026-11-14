# T-021 results: tests B1 (satellite-change steps) and B3 (known artifacts)

> Run 2026-11-14 on the real products of `data/products/` (cell_month_witness, cells, calibration; Git LFS), method `0.1.0-combined-no-baseline` (`harmonize.records_from`). Code `pipeline/validation_b.py`, tests `pipeline/tests/test_validation_b.py`, task prompt `docs/task-prompts/T-021-test-b.md` (written before any result). Thresholds are those locked at G1 (D-028, `docs/VALIDATION_PLAN.md` section 3); none was changed after the results were seen. Labels: [VERIFIED] computed here, [ASSUMPTION] a choice the plan leaves open (fixed in the task prompt before the run), [HYPOTHESIS], [OPEN].

## 1. Summary

| Test | Part | Status | Measured |
|---|---|---|---|
| B1 | 2012-01 (S-NPP enters) | **PASS** | harmonized step within +-10% of 1 in 14 of 14 regions (range 0.955 to 1.007); raw step 2.60 to 4.28 in 14 of 14 |
| B1 | 2018-04 (NOAA-20 enters) | **PASS** | harmonized step within +-10% in **13 of 14** regions (92.9%; range 0.952 to 1.104); raw step 1.60 to 2.05 in 14 of 14 |
| B1 | family (both dates) | **PASS** | |
| B3 | drift as a ratio trend | **PASS as written** | "Drift visible as a ratio trend, with its onset estimate". Visible at night only (S-NPP onset 2024-05, NOAA-20 onset 2024-09); the registered day-only drift method of T-012 found none (section 4.1) |
| B3 | outages, estimates | **PASS** | 60 of 60 entity-months in the 4 outage months have no estimate; 0 of 345 incomplete witness-month cases used |
| B3 | outages, verdicts | **PASS** | 936 of 936 entity-months in the 4 outage months are `CANNOT_DETERMINE` (100%), all with the reason `OUTAGE` (T-014 product, section 4.3) |
| B3 | family | **PASS** | all three plan criteria ran and passed |

All parts have run. B1 and the drift and estimate-level checks ran first on the T-013 estimates; the verdict check ran afterwards on the T-014 `entity_month` product (`method_version` 0.1.0, from branch `science/T-014-verdicts`, PR #52; the product files were not committed here). Thresholds were not changed.

## 2. B1: the statistic as run

Per fire region and date d: `q(window) = sum X / sum A`, over the months of the window with an estimate and with Aqua used; `step = q(12 months from d) / q(12 months before d)`. A is the Aqua-only series (Aqua cell-days, Aqua ratio 1). X is the harmonized estimate (`estimate`) for the test and `raw_combined_cell_days` (all four witnesses, Terra included, raw) for the reference. PASS at a date: the harmonized step is within +-10% of 1 in at least 80% of the regions with sufficient data, and the raw step is "clearly present".

Choices the plan leaves open [ASSUMPTION], fixed before the run: sufficient data = at least 10 usable months and at least 60 Aqua cell-days in each window (5 per month, as D-028 step 4); the regions are the 14 pipeline fire regions (not `UNASSIGNED`, not cells with no region); "clearly present" = the raw step is outside +-10% of 1 in at least half of the sufficient regions, else the date is INCONCLUSIVE; fewer than 5 sufficient regions is INCONCLUSIVE; the windows include the month of the date. All 14 regions had sufficient data at both dates (12 usable months in each window).

### 2.1 2012-01 [VERIFIED]

| Region | Harmonized step | Raw step | Aqua cell-days before / after |
|---|---|---|---|
| AUST | 0.964 | 2.79 | 112,060 / 115,489 |
| BOAS | 0.975 | 2.60 | 62,155 / 95,457 |
| BONA | 0.987 | 2.70 | 8,252 / 8,837 |
| CEAM | 1.007 | 4.01 | 53,996 / 34,177 |
| CEAS | 0.997 | 3.21 | 68,732 / 71,570 |
| EQAS | 1.000 | 4.22 | 33,592 / 38,037 |
| EURO | 0.955 | 3.17 | 20,188 / 20,549 |
| MIDE | 0.994 | 3.66 | 10,155 / 8,297 |
| NHAF | 0.995 | 3.06 | 449,965 / 417,699 |
| NHSA | 0.996 | 3.91 | 20,931 / 25,442 |
| SEAS | 0.991 | 4.28 | 107,124 / 145,501 |
| SHAF | 0.991 | 3.60 | 641,794 / 618,292 |
| SHSA | 0.986 | 3.38 | 182,224 / 207,568 |
| TENA | 0.968 | 2.84 | 36,916 / 37,410 |

Median harmonized step 0.991, median raw step 3.29. **14 of 14 within +-10% (100%, criterion 80%): PASS.**

### 2.2 2018-04 [VERIFIED]

| Region | Harmonized step | Raw step | Aqua cell-days before / after |
|---|---|---|---|
| AUST | 0.975 | 1.69 | 76,559 / 87,974 |
| BOAS | 1.011 | 1.61 | 37,875 / 44,605 |
| BONA | 0.996 | 1.60 | 18,912 / 13,599 |
| CEAM | 1.052 | 1.84 | 37,084 / 35,921 |
| CEAS | 1.081 | 1.79 | 79,835 / 62,058 |
| EQAS | 0.952 | 1.70 | 13,016 / 23,019 |
| EURO | 1.054 | 1.74 | 12,629 / 13,378 |
| **MIDE** | **1.104** | 2.05 | 8,090 / 5,678 |
| NHAF | 1.027 | 1.80 | 412,962 / 391,357 |
| NHSA | 0.993 | 1.84 | 37,553 / 36,600 |
| SEAS | 1.021 | 1.83 | 116,803 / 121,143 |
| SHAF | 0.990 | 1.75 | 591,407 / 590,252 |
| SHSA | 1.043 | 1.75 | 201,925 / 149,650 |
| TENA | 1.039 | 1.79 | 38,704 / 29,499 |

Median harmonized step 1.024, median raw step 1.77. **13 of 14 within +-10% (92.9%, criterion 80%): PASS.** One region (MIDE, the Middle East, small: about 8,000 Aqua cell-days a year) is outside, at +10.4%. The harmonized steps are slightly above 1 on average (median +2.4%); the raw reference is 1.6 to 2.05. **[HYPOTHESIS]** the small positive offset at 2018-04 reflects the NOAA-20 ratios (fitted from 2018-04, with S-NPP already in the combination); it is not tested here.

### 2.3 Control box C8 (supplementary, outside the family fraction) [VERIFIED]

Southern African savanna (20, -20, 35, -8; the 720 analysis cells whose centre lies inside) through `harmonize_area()`: harmonized step **0.984** at 2012-01 (raw 3.35) and **0.997** at 2018-04 (raw 1.76). The plan's CTRL test (verdicts at the change dates) is T-024 and not part of this task.

### 2.4 Supplementary: the Aqua night exclusion at 2024-05 (no plan criterion, no status) [VERIFIED]

Harmonized estimate divided by the converted S-NPP series (day and night, months where S-NPP is complete in both parts), 12 months from 2024-05 against the 12 before, per fire region: 14 regions, **all within +-10%** (0.956 to 1.051, median 1.001). **Limit:** S-NPP is incomplete in 2024-05, 06, 07, 09 and 11, so only 7 of the 12 months after the date are usable, below the 10 required for "sufficient data" in B1. The plan sets no threshold for this check, so it is shown as a description and not as a result.

## 3. B1: limits [VERIFIED reasoning unless labelled]

- **Not out of sample.** The ratios of S-NPP are fitted on 2012-01 to 2016-12 and those of NOAA-20 on 2018-04 to 2021-12 (T-011), and B1 looks at exactly the first 12 months of those periods. A step near 1 is therefore partly expected by construction; B1 shows that the method has no residual level change where a satellite enters, not that the ratios generalize (D1 and E1 test that).
- **The "before" window is trivially 1 at 2012-01.** Before 2012-01 the harmonized series is Aqua only, so its q is exactly 1; the step equals q after. At 2018-04 both windows have two or three witnesses.
- **Yearly sums hide short offsets.** A step of a few months' length inside a 12-month window is averaged out. The same calendar months fall in both windows, so seasonal cycles cancel in the ratio, but years differ in activity; the Aqua-only denominator removes the common part.
- The plan's tolerance is +-10% on a ratio of sums, with no uncertainty attached; a region near the boundary (MIDE 1.104) is not separated from noise here [OPEN: no interval is computed for the step].
- 2012-01 is not a clean entry month: S-NPP data exist from 2012-01-20 (12 days available), so January 2012 has no S-NPP in the estimate while its raw series includes the partial detections. The windows include it as the plan reads literally [ASSUMPTION].
- Test on `pct_of_normal`: under the plan's definition (series / Aqua-only), `pct_of_normal` divides numerator and denominator by the same baseline median, so it gives the same step; the harness also computes the shift of the median `pct_of_normal` (`pct_of_normal_shift`) as a supplementary figure (section 4.3). No threshold exists for it, so it has no status.

## 4. B3

### 4.1 Drift visible as a ratio trend: PASS [VERIFIED]

The pre-registered T-012 detector (`aqua_drift.detect`, unchanged settings: 1,000 moving-block bootstrap replicates, block 6, seed 2012, candidate onsets from 2018-01, NOAA-20 from 2019-04) on the global monthly Aqua / converted-VIIRS ratio R(t). **Criterion used [ASSUMPTION; the plan says only "visible as a ratio trend, reported with its onset estimate"]:** the detector fires (slope interval excludes 0 and the break model wins by BIC) for **both** VIIRS witnesses in the **same** day/night part, with a falling ratio and an onset in 2021 or later.

| Part | Witness | Detected | Onset (90% interval) | Slope per year (90% interval) | dBIC | Months |
|---|---|---|---|---|---|---|
| Night | S-NPP | yes | 2024-05 (2022-10 to 2025-04) | -12.0% (-22.8 to -5.5) | +28.9 | 164 |
| Night | NOAA-20 | yes | 2024-09 (2024-03 to 2025-02) | -19.0% (-25.4 to -14.1) | +50.7 | 99 |
| Day | S-NPP | **no** | 2025-06 (2019-02 to 2025-06) | -5.4% (-8.5 to -0.4) | -6.1 | 164 |
| Day | NOAA-20 | **no** | 2025-06 (2020-01 to 2025-06) | -6.1% (-9.2 to -0.5) | -2.7 | 99 |

Status **PASS as written** (the criterion in the plan is "drift visible as a ratio trend, reported with its onset estimate"; the wording is not changed after seeing the result, decision of the Lead on PR #54, 2026-11-14). The drift is **visible at night only** (S-NPP onset 2024-05, NOAA-20 onset 2024-09); the registered day-only drift method of T-012 found none. The caveat stays visible. The numbers equal those of T-012 (`docs/DATA_SOURCES.md`), as they must: the same code and seed. **Reading it honestly:** (1) this PASS confirms T-012 and is not independent of it; (2) the criterion was written knowing the T-012 result; the strict reading "the registered primary series (global day, S-NPP) detects drift" would be **FAIL**, as T-012 reported, and the Lead's D-005 decision is the documented deviation; (3) the hypothesis "drift visible after ~2021" is supported only for night, and the onsets (2024-05 and 2024-09) are three years later than 2021; (4) the cause (Aqua, processing or VIIRS) is not separated [OPEN].

### 4.2 Outages, estimate level: PASS [VERIFIED]

Outage month = a month in which no witness (Aqua, S-NPP, NOAA-20) has every day available, read independently from `cell_month_witness.parquet` (`days_available` against `days_in_month`). The four outage months are **2002-07, 2002-08, 2002-09 (Aqua 26, 24, 29 days) and 2026-11** (the current month, data to 2026-11-14: Aqua 14, NOAA-20 14, S-NPP 2 days).

- 15 entities (the 14 fire regions and `UNASSIGNED`) x 4 months = **60 entity-months; 0 have an estimate (100% without)**.
- Incomplete witness-months with another witness present: Aqua 2022-04 (14 days); S-NPP 2012-01 (12), 2012-03 (30), 2022-07 (26), 2022-08 (21), 2024-05 (29), 2024-06 (27), 2024-07 (21), 2024-09 (29), 2024-11 (27), 2026-03 (28), 2026-04 (27), 2026-06 (28), 2026-07 (25); NOAA-20 2023-07 (27), 2023-09 (29), 2024-02 (28). **345 entity-month by incomplete-witness cases, 0 with the incomplete witness in `witnesses_used`.** Those months keep an estimate from the other witnesses; they are not outages in the D-028 sense (step 1 needs no witness with a complete month).

### 4.3 Outages, verdicts: PASS [VERIFIED]

On the T-014 `entity_month.parquet` (68,562 entity-months; 67,626 with a baseline): the same four outage months (2002-07, 2002-08, 2002-09, 2026-11; no complete witness) cover **936 entity-months (234 entities, all types) and every one is `CANNOT_DETERMINE`: 936 of 936 (100%)**, **all 936 with the reason `OUTAGE`** (D-028 step 1). Criterion: 100% `CANNOT_DETERMINE`; status **PASS**.

Check of the product beyond the criterion: the 936 outage entity-months are also exactly the entity-months of the whole product without an estimate (936 of 68,562), and all of them carry `OUTAGE` (702 with `OUTAGE` only, 233 with `OUTAGE` and `PROVISIONAL_NRT`, 1 with `DIURNAL_CAVEAT`, `OUTAGE` and `PROVISIONAL_NRT`). So there is no month without an estimate that is not an outage, and no outage month with an estimate. Baseline fields are filled in outage rows too (the baseline does not depend on the month's estimate); they do not change the verdict.

Supplementary shift of the median `pct_of_normal`, 12 months from the date minus the 12 before (percentage points; no threshold in the plan, no status): South Africa (ZAF) +5.2 at 2012-01 and -12.7 at 2018-04; Africa (AF) -3.5 at 2012-01 and +1.9 at 2018-04. These are level changes of a percent-of-normal in a real, varying series (a real change in fire activity between years is included) and are not a measure of an artifact; the B1 step above is the test.

### 4.4 S-NPP end 2026-11-02 (supplementary, no plan criterion) [VERIFIED]

S-NPP's last complete month is 2026-10; in 2026-11 it has 2 days available, consistent with the documented end of 2026-11-02 15:40 UTC. No entity-month from 2026-11 uses S-NPP (15 checked). **[OPEN]** 2026-11 is partial for every witness (data to 2026-11-14), so in the harmonized series the S-NPP end cannot yet be told apart from the partial month; it will be visible as a month with Aqua and NOAA-20 only once 2026-12 is complete. The step test for it cannot be run before then.

## 5. What ran, and the command

Everything ran; nothing is NOT_RUN. To reproduce, from the repository root with the T-014 products in `data/products/`:

```
python pipeline/validation_b.py                                    # about 2.5 minutes; uses data/products/entity_month.parquet when present
python pipeline/validation_b.py --entity-month PATH_TO_PRODUCT     # or name the product
```

It writes `data/interim/qa/T-021_validation_entries.json` (contract section 6 shape) and `data/interim/qa/T-021_full_results.json` (both git-ignored). B1 and the drift check use the estimates of `harmonize.records_from` on the real witnesses; the verdict check uses the product. The product is accepted as having verdicts when `baseline_median` is non-null for some rows (true for the T-014 product); no change to the harness was needed.

## 6. Other limits

- The outage definition follows D-028 step 1. A reading in which any witness outage must give `CANNOT_DETERMINE` would contradict D-028 (the other witnesses still give an estimate) and was not used.
- Fire regions are the 14 of the pipeline; countries, continents and the world are not in the B1 fraction (the plan says "all fire regions").
- Passing these tests shows the method behaves correctly where tested; it does not establish global accuracy (`docs/VALIDATION_PLAN.md` section 1).
