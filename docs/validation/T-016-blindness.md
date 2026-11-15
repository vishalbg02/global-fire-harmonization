# T-016: "MODIS blindness" indicator per fire region (F13)

> Member 2 · 2026-11-15 · method 0.1.0 (nothing changed) · Task prompt: `docs/task-prompts/T-016-blindness.md` (definition, thresholds and reading rule fixed before the run). Harness: `pipeline/blindness.py`, tests `pipeline/tests/test_blindness.py` (12 tests, SYNTHETIC data). Derived file (not committed): `data/interim/blindness/blindness_by_region.csv` (320 rows). This is **not** a contract product and **not** a validation test: there is no PASS or FAIL.

## 1. What the number is

**B = VIIRS cell-days / Aqua cell-days**, summed over the calibration fit months of a fire region (S-NPP 2012-01 to 2016-12, 58 complete months, 2012-01 and 2012-03 excluded as partial; NOAA-20 2018-04 to 2021-12, 45 months), day and night apart. It is the inverse of the T-011 ratio taken at fire-region level. The "extra share" 1 - 1/B is in the table too (for B = 3.4 it is 0.71). Interval: 5th to 95th percentile of a bootstrap over whole months (1,000 replicates, seed 20261115): it shows month-to-month sampling only. Held-out years and validation case windows are not used. The project documents define the indicator only as one that "falls out of the calibration step" (assumption on the definition: task prompt section 15).

## 2. What it is not (caveat text, stored in every row)

- Not a fire count, not burned area and not a detection probability.
- B mixes the 375 m versus 1 km sensitivity with overpass times (Aqua about 13:30 and 01:30, S-NPP about 13:30, NOAA-20 about 12:40), thresholds and cell-day saturation. T-020b found that the Aqua/VIIRS ratio rises with activity, so B is lower in very active regions for that reason alone.
- It describes the fit months only. The interval excludes model error.
- That MODIS misses small fires is a **hypothesis** here, not shown by this number (S15 stays a hypothesis).

## 3. Result: all fit months (B with 90% interval)

(H) / (L): interval entirely above / below the global B of the same witness and day/night (the reading rule of the prompt). "burst": one month holds more than half of the cell-days.

| Region | S-NPP day | NOAA-20 day | S-NPP night | NOAA-20 night |
|---|---|---|---|---|
| AUST | 2.39 [2.35, 2.44] (L) | 2.45 [2.39, 2.53] (L) | 9.56 [8.44, 11.07] (L) | 10.24 [8.54, 12.63] (L) |
| BOAS | 2.19 [2.11, 2.30] (L) | 2.15 [2.05, 2.29] (L) | 10.68 [9.48, 12.95] (L) | 9.33 [7.84, 12.08] (L) |
| BONA | 2.48 [2.31, 2.70] (L) | 2.29 [2.19, 2.45] (L) | 11.68 [10.30, 14.08] (L) | 6.98 [6.01, 10.30] (L) |
| CEAM | 4.71 [4.56, 4.93] (H) | 4.66 [4.46, 4.95] (H) | 20.02 [18.88, 21.26] (H) | 17.88 [16.01, 20.15] |
| CEAS | 3.45 [3.34, 3.58] | 3.42 [3.30, 3.58] | 26.98 [24.68, 29.81] (H) | 33.00 [28.01, 38.33] (H) |
| EQAS | 4.09 [3.96, 4.27] (H) | 4.99 [4.61, 5.50] (H) | 10.12 [9.28, 11.52] (L) | 11.10 [8.89, 17.24] |
| EURO | 3.71 [3.60, 3.84] (H) | 3.96 [3.78, 4.18] (H) | 15.56 [13.06, 19.91] | 19.27 [14.72, 26.08] |
| MIDE | 4.29 [3.99, 4.61] (H) | 4.63 [4.28, 4.98] (H) | 18.30 [16.48, 20.42] (H) | 18.75 [16.72, 21.11] (H) |
| NHAF | 3.37 [3.27, 3.50] | 3.46 [3.35, 3.62] | 21.61 [20.39, 22.62] (H) | 24.28 [22.57, 25.70] (H) |
| NHSA | 4.54 [4.41, 4.68] (H) | 4.54 [4.40, 4.76] (H) | 13.64 [12.81, 14.74] (L) | 13.46 [12.27, 15.80] (L) |
| SEAS | 4.48 [4.31, 4.73] (H) | 4.61 [4.38, 4.97] (H) | 42.34 [38.71, 46.13] (H) | 42.21 [37.49, 47.90] (H) |
| SHAF | 3.16 [3.05, 3.32] (L) | 3.39 [3.20, 3.65] | 24.93 [23.84, 26.00] (H) | 27.43 [25.53, 29.26] (H) |
| SHSA | 3.23 [3.12, 3.36] | 3.19 [3.05, 3.36] (L) | 9.56 [9.26, 9.91] (L) | 9.08 [8.69, 9.55] (L) |
| TENA | 2.69 [2.62, 2.77] (L) | 2.78 [2.69, 2.88] (L) | 14.14 [11.27, 18.87] | 10.06 [7.78, 14.71] (L) |
| UNASSIGNED | 6.00 [5.41, 6.82] (H) | 9.64 [7.57, 12.86] (H) | 17.91 [12.50, 27.76] | cannot determine |
| GLOBAL | 3.34 [3.25, 3.44] | 3.46 [3.34, 3.58] | 16.42 [15.51, 17.52] | 16.44 [15.01, 18.03] |

Global B (verified from the run, all regions summed): day 3.34 (S-NPP) and 3.46 (NOAA-20); night 16.4 for both.

## 4. Reading

- **Night B is far larger than day B everywhere** (about 7 to 42 against about 2 to 5): Aqua records few night cell-days compared with VIIRS. Candidate causes are the 375 m versus 1 km sensitivity, thresholds and the overpass time; this report does not separate them (hypothesis).
- **Day:** lowest B in AUST, BOAS, BONA and TENA (about 2.2 to 2.8, above 1 everywhere); highest in CEAM, EQAS, NHSA, SEAS and MIDE (about 4 to 5). The two VIIRS witnesses agree closely (all-year B of NOAA-20 over S-NPP: median 1.03, range 0.60 to 1.24 over the 28 region and day/night pairs; correlation of log B 0.985).
- **Night:** highest B in SEAS (about 42), CEAS, SHAF, NHAF (about 22 to 33); lowest in SHSA, EQAS, AUST, BOAS (about 9 to 11). The high values are in the savanna and agricultural regions named in hypothesis S15; this is consistent with it and does not test it.
- The global B is dominated by the regions with the most cell-days (SHAF, NHAF), so many regions are "lower" or "higher" than it; the labels compare with that weighted value, not with a typical region.
- Regions where the interval is wide (for example TENA night, EURO night) have few Aqua night cell-days (2,000 to 15,000).
- Seasonal values (rows with `season` DJF, MAM, JJA, SON in the CSV): 227 OK, 9 BURST and 20 CANNOT_DETERMINE of 256 region-season rows. Seasonal B moves a lot in some regions (S-NPP night SEAS 25 in JJA to 70 in SON; NHAF day 3.3 outside JJA but 7.0 in JJA), so a single yearly value hides seasonal differences.
- UNASSIGNED (cells outside any fire region) is not a fire region: it has only 246 to 465 Aqua day cell-days and is shown for completeness (NOAA-20 night: cannot determine).

## 5. Checks

- Cross-check with the T-011 product: the inverse of the median stratum ratio of each region and season (`calib_inverse_median`) against the B of the same region and season: correlation of log values 0.992 over 220 pairs; median B / calib 1.00 (quartiles 1.00 to 1.01). The few large departures (up to 3.6) are thinly populated region-seasons, where the activity-weighted B differs from the unweighted median of strata. This only shows the two computations are consistent, not that either is right.
- Regional sums add up to the global sum (tested on SYNTHETIC data; the global row is computed from the same matrices).
- Seasonal rows flagged BURST (9) are listed in the CSV with the flag; their values are shown, not hidden.

## 6. Limits

Fit-period months only (2012 to 2016 for S-NPP and 2018 to 2021 for NOAA-20), not a time series. B is a ratio of cell-day sums: it says nothing about fire size, a fire count or burned area. Intervals are sampling intervals over months. The definition, the thresholds (100 cell-days, 6 months) and the use of GFED fire regions are assumptions for the Lead (task prompt section 15).

## 7. Reproduce

```
python pipeline/blindness.py        # about 1 minute; needs the heavy-job lock; writes data/interim/blindness/
python -m pytest pipeline/tests/test_blindness.py -q
```
