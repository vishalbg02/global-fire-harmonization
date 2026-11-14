# T-020b: does the Aqua/VIIRS ratio rise with activity (cell-day saturation)?

> Member 2 · 2026-11-15 · diagnostic requested by the Lead on PR #55 · method 0.1.0 (nothing changed here)
> Task prompt: `docs/task-prompts/T-020b-extreme-months.md` (decision rule fixed before any result was seen). Harness: `pipeline/saturation.py`, tests `pipeline/tests/test_saturation.py`. Raw output: `data/interim/qa/saturation_report.json` (not committed).

## 1. Question and data

A 0.05 degree fine cell counts at most once per day, so in very active areas every sensor saturates. If so, the Aqua over VIIRS ratio should **rise** with activity, whereas the T-011 ratio is one value per stratum, day/night and season, fitted mostly on typical months. That would explain why the converted S-NPP estimate falls below Aqua in the peak windows of A1 (S-NPP over Aqua 0.58 to 0.80).

Only the **calibration fit periods** were used (S-NPP 2012-01 to 2016-12, NOAA-20 2018-04 to 2021-12, complete months, exactly as `calibration.monthly_sums`). No S-NPP data from 2017 on and no A1 case window entered. Units are stratum-months, day and night apart (S-NPP 232,928 per day/night, NOAA-20 180,720 per day/night). Activity is cell-days per analysis cell and month, in eight fixed bins (0 to 0.05, 0.05 to 0.15, 0.15 to 0.5, 0.5 to 1.5, 1.5 to 5, 5 to 15, 15 to 50, 50 and above). Ratio per bin = sum(Aqua) / sum(witness). 90% intervals: bootstrap over whole months (1,000 replicates, seed 20261115). Slope: OLS of log(ratio) on log(mean activity of the bin) over bins with at least 50 units.

Three binnings: (a) Aqua activity of the month (biased: the numerator defines the bin, regression to the mean), (b) symmetric proxy (mean of the Aqua activity and the stratum-ratio-scaled VIIRS activity), (c) typical activity of the stratum (median over the fit months of its Aqua cell-days per cell).

## 2. Decision by the rule fixed in advance

**Confirmed** if, in at least two of three binnings, the slope is positive with a 90% interval excluding 0 in at least three of the four combinations (witness x day/night); binning (a) alone never decides.

| Binning | S-NPP day | S-NPP night | NOAA-20 day | NOAA-20 night | Combinations positive | Passes |
|---|---|---|---|---|---|---|
| (a) Aqua activity | 0.176 [0.174, 0.178] | 0.299 [0.290, 0.308] | 0.186 [0.183, 0.189] | 0.314 [0.300, 0.345] | 4 of 4 | yes |
| (b) symmetric proxy | 0.111 [0.108, 0.114] | 0.258 [0.242, 0.275] | 0.120 [0.117, 0.123] | 0.282 [0.258, 0.305] | 4 of 4 | yes |
| (c) typical stratum | -0.019 [-0.025, -0.012] | 0.108 [0.095, 0.120] | -0.033 [-0.039, -0.026] | 0.133 [0.116, 0.150] | 2 of 4 | no |

(slope and 90% interval.) Two binnings pass, so **saturation is confirmed by the rule**. The result is a statement about the sign of the slope, not about its exact size.

## 3. The ratio by activity bin (S-NPP; NOAA-20 is similar)

Binning (b), the less biased one, ratio Aqua/S-NPP with 90% interval:

| Activity (cell-days per cell and month) | Day | Night |
|---|---|---|
| 0 to 0.05 | 0.094 [0.090, 0.099] | 0.012 [0.011, 0.012] |
| 0.05 to 0.15 | 0.200 [0.196, 0.204] | 0.040 [0.038, 0.041] |
| 0.15 to 0.5 | 0.236 [0.231, 0.241] | 0.056 [0.054, 0.058] |
| 0.5 to 1.5 | 0.254 [0.248, 0.260] | 0.062 [0.059, 0.066] |
| 1.5 to 5 | 0.258 [0.251, 0.265] | 0.065 [0.060, 0.071] |
| 5 to 15 | 0.275 [0.266, 0.285] | 0.090 [0.078, 0.103] |
| 15 to 50 | 0.283 [0.274, 0.291] | (14 units, not used) |
| 50 and above | 0.346 [0.337, 0.354] | (0 units) |

By day the ratio rises from about 0.2 to 0.35 (a factor of 1.7) from moderate to extreme activity; by night it rises by a factor of about 1.5 between 0.15 and 15 cell-days. Binning (a) shows the same direction with larger numbers. The full tables for all binnings, witnesses and day/night are in the JSON report.

A higher Aqua/VIIRS ratio in active months means VIIRS counts relatively **fewer** detections than Aqua there than the typical-month ratio assumes, so a conversion fitted on typical months **under-converts** extreme months. That is the direction of the A1 failure (converted S-NPP below Aqua in the peak windows).

## 4. Caveats (what this does and does not show)

- **[VERIFIED]** The slope is positive in all 12 combinations of binning (a) and (b); the intervals are narrow because the units are many.
- **[LIMITATION]** The lowest bins drive part of the slope. At night the ratio is 0.01 below 0.05 cell-days, plausibly because VIIRS night detects many small and persistent sources that MODIS does not (D-025 handles persistent sources only in part). Without the lowest bin the rise from 0.05 upward is still present by day (0.20 to 0.35) and at night (0.04 to 0.09), but I expect the slope would be smaller (not computed). I did not re-run the slope without the lowest bin, because that would be a choice made after seeing the data.
- **[LIMITATION]** Binning (c), the one least affected by regression to the mean, **did not pass**. By day its ratio is higher in the lowest bin (0.39) than in the middle ones (0.26 to 0.28), which gives the negative day slope; between 0.15 and 5 cell-days it rises mildly (0.26 to 0.31). Its high bins have few or no units (S-NPP day: 232 units above 15; night: no stratum above 1.5), so it cannot speak for extreme months. The confirmation is therefore less firm than the 4 of 4 and 4 of 4 suggest.
- **[LIMITATION]** The fit periods contain few extreme stratum-months (S-NPP night: 34 units above 15 cell-days, one above 50). The night evidence for the very high end is thin; the day evidence is much better (1,488 units at 50 or more in binning (b)).
- **[HYPOTHESIS, not tested here]** Saturation (one count per cell and day) is the mechanism. The data show a rising ratio, which saturation predicts, but other mechanisms also predict it, for example a different overpass time sampling the diurnal peak or different detection thresholds of the two instruments for very large fires. This diagnostic cannot tell them apart.
- A positive slope in the fit periods does not show that the A1 gap is fully explained; a conversion with an activity term has to be built and checked on the holdout and on A1 (below).

## 5. What follows (proposal only; nothing built, nothing changed)

Under the task prompt this PR builds no v0.2. If the Lead approves, a v0.2 conversion would be:

1. A conversion with an **activity term**, fitted on the fit periods only, either per stratum with partial pooling (log(Aqua) = a + b log(VIIRS), b above 1 where saturation matters) or the ratios per activity bin with pooling across strata. The activity used must be known at estimation time (the symmetric proxy of binning (b), computed from the witnesses of the month, not the Aqua count alone).
2. Reported against v0.1: holdout (T-012) errors, D1 coverage, and the A1 re-run.
3. Labelled a **post-hoc improvement prompted by A1**: it cannot make A1 a clean pass. The A1 FAIL for v0.1 stays in the record (PR #55) and v0.1 results stay visible beside the v0.2 ones.
4. A new decision (D-030, Lead's approval) before any product changes, because it changes the scientific methodology and the products.

If the Lead prefers not to build v0.2, the alternative is to keep v0.1 with A1 FAIL as a documented limitation and add the finding of this diagnostic (extreme months are under-converted) to `docs/RISKS_AND_LIMITATIONS.md`.

## 6. Status

Diagnostic complete. By the rule fixed in advance: **saturation confirmed** (binnings (a) and (b) pass, (c) does not). Tests: 9 pass on synthetic data with known answers; `ruff` clean. No product, threshold or earlier result changed.
