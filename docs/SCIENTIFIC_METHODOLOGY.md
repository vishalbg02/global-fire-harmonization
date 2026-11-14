# Scientific Methodology: `method_version: 0.1.0-proposed`

> Changes to this document require Project Lead approval (`DECISION_LOG.md`). Labels: **[VERIFIED date]**, **[ESTIMATE]**, **[ASSUMPTION]**, **[HYPOTHESIS]**, **[PROPOSED]**, **[OPEN]**.

## 1. What a hotspot is (and is not)

- A FIRMS detection is the **centre of a satellite pixel flagged as containing one or more active fires** at overpass time. The fire is usually much smaller than the pixel. **[VERIFIED 2026-11-14, FIRMS FAQ]**
- A detection is **not** a fire, a fire count, a perimeter or burned area. Several detections can come from one fire. One detection can contain several fires.
- **No detection ≠ no fire.** Clouds, heavy smoke, canopy, data gaps, and fires that start and end between overpasses all produce silence. FIRMS points carry no cloud or missing-data information. **[VERIFIED, FIRMS FAQ]**
- Polar orbiters take **snapshots**, a few per day, not continuous monitoring.

We therefore describe our quantity as **"satellite-detected fire activity"** in units of fire-active cell-days. Never "number of fires".

## 2. Why MODIS and VIIRS cannot be added together

| Factor | MODIS (Terra, Aqua) | VIIRS 375 m (S-NPP, NOAA-20, NOAA-21) | Effect |
|---|---|---|---|
| Pixel at nadir | ~1 km, growing strongly toward the swath edge | 375 m | VIIRS splits one fire into more points; MODIS edge pixels are huge |
| Small-fire sensitivity | Lower | Much higher. Schroeder et al. 2014 report ~3× more fire pixels by day and ~25× at night, vs the 750 m baseline | Counts differ by fire-size regime |
| Confidence | 0–100 (low / nominal / high classes) | Categorical l/n/h | Not equivalent scales |
| Overpass (nominal local time) | Terra ~10:30 / 22:30; Aqua ~13:30 / 01:30 | S-NPP ~13:30; NOAA-20/21 ~12:40 | Different points in the daily fire cycle |
| Orbit | **Drifting** (fuel exhausted): Terra earlier, Aqua later **[VERIFIED, LAADS]** | Maintained | The time of day Aqua samples changes over its late life |
| Record | Terra Nov 2000–; Aqua Jul 2002–; ending 2026–27 (NASA sources disagree) | S-NPP 20 Jan 2012 – 2 Nov 2026; NOAA-20 2018–; NOAA-21 2024– **[VERIFIED, FIRMS FAQ]** | Satellites joining and leaving create steps |
| FRP agreement | — | Aqua vs S-NPP differ by about 20% on average at 1° (Li et al. 2018) | FRP is not interchangeable |

Adding everything together creates artificial jumps:
- January 2012, when VIIRS arrives.
- 2018, when NOAA-20 is added.
- 2024, when NOAA-21 is added.
- November 2026, when S-NPP ends.
- Gradually during the drift years.

The ratio of VIIRS to MODIS detections **varies by region and fire regime**, because small fires are where MODIS misses most. Unreviewed figures from another team suggest roughly 2× (California) to 4× (North India) **[HYPOTHESIS until we measure]**. **A single global conversion factor is therefore not valid.**

## 3. Critical review of the inherited plan (2026-11-14)

| Inherited element | Assessment | Action |
|---|---|---|
| Use MODIS Terra + Aqua | Terra observes the morning; mixing it in brings a different diurnal phase and a separate drift | **Aqua only** in the harmonized record; Terra shown in the raw view only **[PROPOSED, D-006]** |
| Records from 2002 | Aqua starts July 2002. Including Terra-only months (Nov 2000–Jun 2002) would need a second calibration chain | Harmonized record starts **2002-07** **[PROPOSED, D-006]** |
| Aqua as reference | Aqua is not stable after its orbit maintenance ended; the onset date is **[OPEN]** (a 2017 NASA plan suggested ~2021–22) | Aqua is a *display scale*, not "truth". It is excluded from the combination after a drift cutoff, and the drift is **measured empirically** (Aqua/VIIRS ratio over time) before the cutoff is fixed |
| One calibration globally | Invalid (see §2) | Partial pooling: local → fire region → global |
| Regional/seasonal calibration | Necessary but not sufficient: ratios can change if fire sizes change within a region | Keep it, plus a large-fire diagnostic (P1) and disclosure |
| 2003–2022 baseline | It mixes measured years (Aqua-only before 2012) with converted years, so the baseline itself depends on harmonization | Keep it **[PROPOSED, D-010]**, plus a **sensitivity test** using an Aqua-measured baseline (2003–2021) |
| Day/night separation | Necessary: most of VIIRS's extra detections are at night | Keep: convert D and N separately |
| Combination with uncertainty | The witnesses observe the same fires, so their errors are not independent and naive intervals are too narrow | Disagreement inflation, plus explicit disclosure; check interval coverage empirically (test D1) |
| Validation cases | Proposed only; no result exists | Status `NOT_RUN` until executed |
| Dataset size | Measured | 9.1 GB zipped **[VERIFIED]**; ~41 GB unzipped and ~475M rows **[ESTIMATE]** |

## 4. Harmonization method **[PROPOSED]**

### 4.1 Inputs and filters
- FIRMS standard archives 2002-07 → 2025-12 (global yearly zips), plus 2026 from the area API (SP where available, otherwise NRT flagged as provisional).
- Keep `type = 0` (presumed vegetation fire). In NRT data, which has no `type`, mask cells historically dominated by `type = 2` (static land sources) or `type = 3` (offshore).
- Confidence: MODIS ≥ 30; VIIRS `n` or `h`. A sensitivity run without the confidence filter is part of validation.
- Satellite codes in the data **[VERIFIED 2026-11-14]**: `Terra`, `Aqua`, `N` (S-NPP), `N20` (NOAA-20).

### 4.2 Spatial and temporal aggregation
- **Fine grid:** a detection marks its fine cell as fire-active for that UTC day, per witness and per day/night. This removes multiple points per fire and same-day duplicates. Fine-cell size **[OPEN, D-009]** candidates are 0.05° and 0.1°. The fine cell should be no smaller than a MODIS edge pixel.
- **Analysis grid:** monthly sums of fine-cell-days on a regular latitude/longitude grid. Candidates are **0.5° (recommended)** and 0.25°. Larger cells hold more activity, which means more cells get a determinable verdict.
- **Choose at Gate G1** the pair that maximizes Aqua vs S-NPP agreement in the 2012–2016 overlap. Lock it before any validation is run.

### 4.3 Calibration (conversion of each VIIRS witness to the Aqua-equivalent scale)
- Fit periods: S-NPP on 2012-01 → 2016-12 (2017–2021 held out). NOAA-20 on 2018-04 → 2021-12.
- **Ratio** = Σ Aqua cell-days / Σ witness cell-days over the overlap months, per **stratum × day/night × season**.
- **Partial pooling:** a stratum's ratio is shrunk toward its fire-region ratio, and that toward the global ratio, in proportion to how little data it has (empirical-Bayes style shrinkage). `pooling_level` records which level dominates.
- **Uncertainty of the ratio:** a block bootstrap over months (monthly blocks keep within-month dependence).
- **Fallback A:** fixed fire-region × season × day/night ratios with bootstrap uncertainty and no local pooling.
- **Known limitation:** ratios assume the fire-size distribution within a stratum is stationary. If fires get systematically smaller or larger, the ratio drifts. This is not corrected. The P1 large-fire check is a diagnostic for it.

### 4.4 Combining witnesses
- Each witness *w* operating in month *m* gives an Aqua-equivalent estimate `E_w = ratio_w × cell_days_w`, with variance from the ratio uncertainty plus count noise.
- Combined estimate: precision-weighted mean of the available `E_w`. Aqua contributes directly (ratio = 1) until the drift cutoff.
- **Disagreement inflation:** if the witnesses disagree more than their uncertainties allow, the combined uncertainty is multiplied by the scale factor `S = sqrt(χ²/(N−1))`, used only when S > 1. This is the standard rule for combining discordant measurements.
- **Limitation:** the witnesses share the same fires and partly correlated errors, so intervals may still be too narrow. Test D1 measures this.
- **Fallback B:** sequential witnesses (Aqua until the drift cutoff, then converted S-NPP, then converted NOAA-20 after 2026-11-02), with the others shown as cross-checks only.

### 4.5 Area aggregation
For any area (country, continent, custom), sum the raw cell-days **per witness per stratum** first, convert per stratum, then combine. Do **not** sum per-cell intervals: the ratio error is shared within a stratum. A single function, `harmonize_area()`, implements this for both batch and API use.

### 4.6 Baseline and verdicts
- Baseline: the same calendar month, years 2003–2022 **[PROPOSED, D-010]**. Percentiles p25, p50 and p75 come from the harmonized estimates.
- Probabilities `p_above` (> p75), `p_below` (< p25) and `p_within` come from the estimate's uncertainty distribution. Baseline percentile uncertainty is not propagated in v0.1 **[LIMITATION]**.
- **Verdict rules** (thresholds to be locked at G1):

| Condition | Verdict |
|---|---|
| `p_above ≥ 0.8` | `ABOVE_NORMAL` |
| `p_below ≥ 0.8` | `BELOW_NORMAL` |
| `p_within ≥ 0.8` | `WITHIN_NORMAL` |
| Anything else | `CANNOT_DETERMINE` |
| Outage (`days_available` below threshold) | `CANNOT_DETERMINE` (`OUTAGE`) |
| Baseline activity below the minimum, or too few overlap months | `CANNOT_DETERMINE` (`INSUFFICIENT_BASELINE`, `INSUFFICIENT_OVERLAP`) |
| No detections and the baseline is also near zero | `NO_DETECTED_ACTIVITY` (**never** "below normal") |

- **Nothing is ever interpolated or filled.**

### 4.7 Observation effort
- Converting each witness separately means **adding a satellite changes precision, not the level of the record**. This handles the largest effort artifact by design.
- Tracked: daily witness availability from the FIRMS `missing_data` and `data_availability` endpoints, giving `days_available` per witness per month.
- **Not modelled [LIMITATION]:** per-cell overpass counts and cloud cover. The global swath/cloud data needed is not available in FIRMS points and cannot be processed in the time available. Ratios estimated locally partly absorb latitude-dependent overpass frequency.

### 4.8 Observation timing
- Using only afternoon witnesses limits diurnal mismatch: Aqua and S-NPP pass ~13:30, NOAA-20 ~12:40.
- The Aqua drift is handled by the empirical cutoff (§3).
- **Not corrected [LIMITATION]:** regional shifts in burning time relative to overpasses. Example: geostationary studies report Punjab/Haryana burning moving from ~13:30 to ~17:00 between 2020 and 2024 (ISRO/SAC; iFOREST). Flagged with `DIURNAL_CAVEAT` where documented.

## 5. Avoiding suppression of genuine anomalies
- Calibration is fitted only on overlap years and never re-fitted per year. Per-year re-fitting would absorb real changes.
- Real-event tests (Witness Stand A1, A2) check that known extremes survive with similar magnitude in independent paths.
- The control region (savanna) checks that no spurious anomalies appear at satellite-change dates.

## 6. Handling insufficient data
"Insufficient" is defined by explicit thresholds: minimum baseline activity, minimum overlap months, and minimum `days_available`. These are locked at G1. Those cells and areas get `CANNOT_DETERMINE` with reason codes. The app reports the share of land cells with determinable verdicts.

## 7. Validation
See `VALIDATION_PLAN.md`. Thresholds are pre-registered at G1, and results, including failures, are published in the app.

## 8. Limitations (summary)
- Hotspot-based, so it is not burned area, emissions or fire counts.
- No correction for regional burning-time shifts.
- Ratio stationarity is assumed within strata.
- Intervals may be optimistic because witness errors are correlated.
- Baseline uncertainty is not propagated.
- Custom areas are approximated by grid cells.
- Validation is sampled, not global. **We make no claim of global accuracy.**
- MODIS `version` strings differ across years (`6.2` in 2012, `6.03` in 2020, `61.03` in 2025) **[VERIFIED in archive files]**. Whether these represent the same processing collection is **[OPEN, T-007]**.

## 9. References
- Schroeder, W. et al. (2014) *Remote Sensing of Environment*: the VIIRS 375 m active fire product. https://directreadout.sci.gsfc.nasa.gov/publications_documents/Schroeder_et_al_2014b_RSE.pdf
- Giglio, L., Schroeder, W., Justice, C. (2016) *RSE*: the MODIS Collection 6 active fire algorithm. https://www.earthdata.nasa.gov/s3fs-public/imported/Giglio2016_C6_Fire.pdf
- Giglio, L. et al. (2006) *JGR*: global distribution of fire from MODIS (CMG gridding normalized by observations). https://dataserver-coids.inpe.br/queimadas/queimadas/Publicacoes-Impacto/material3os/2006_Giglio_etal_GlobalDistribuiton_JGR_DE3os.pdf
- Li, F. et al. (2018) *JGR Atmospheres*: Aqua MODIS vs S-NPP VIIRS FRP comparison. https://repository.library.noaa.gov/view/noaa/49896/noaa_49896_DS1.pdf
- MDPI *Remote Sensing* 18(10):1650 (2026): FRP correction and fusion using MYD14 and VNP14IMG (matched within 5 minutes). https://doi.org/10.3390/rs18101650
- VIIRS 750 m active fire ATBD (MODIS C6 heritage). https://viirsland.gsfc.nasa.gov/PDF/VIIRS_activefire_750m_ATBD.pdf
- LAADS: MODIS to VIIRS transition (orbit drift). https://ladsweb.modaps.eosdis.nasa.gov/learn/modis-to-viirs-transition
- Venema, V. et al. (2012) *Climate of the Past* 8:89–115: benchmarking homogenization algorithms (the synthetic-break validation concept).
- Stradiotti et al. (2025): ESA CCI soil moisture merging with inverse-uncertainty weighting. https://repositum.tuwien.at/bitstream/20.500.12708/218167/1/Stradiotti-2025-Science%20of%20Remote%20Sensing-vor.pdf
- Punjab burning-time shift (ISRO/SAC via Tribune). https://www.tribuneindia.com/news/haryana/farmers-shift-stubble-burning-time-to-dodge-satellite-tracking-isro-study
