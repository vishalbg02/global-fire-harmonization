# T-015: large-fire consistency check (diagnostic series per entity)

> Member 2 · 2026-11-15 · method 0.1.0 (nothing changed here). Diagnostic only: no PASS/FAIL, no product, no contract change.
> Task prompt: `docs/task-prompts/T-015-large-fire.md` (definitions and thresholds fixed before the run). Harness `pipeline/large_fire.py`, tests `pipeline/tests/test_large_fire.py` (9, SYNTHETIC data with known answers). Outputs, not committed: `data/interim/qa/T-015_large_fire_series.parquet` (210,298 rows) and `T-015_large_fire_summary.json`.
> Reproduce: `python pipeline/large_fire.py` (reads the products; heavy-job lock), then `python pipeline/large_fire.py summary` recomputes only the summary.

## 1. Definition [ASSUMPTION, see task prompt section 15]

The docs name the check (F12; `SCIENTIFIC_METHODOLOGY.md` 4.3: the ratios assume a stationary fire-size distribution) but do not define it. Literal reading used: a fire-active cell-day counts once however many detections or how much FRP fall on it, so the cell-day count is blind to fire size. Per entity (COUNTRY, FIRE_REGION incl. UNASSIGNED, GLOBAL), witness (all four) and month:

- `S` = detections / cell-days (pile-up), `F` = FRP (MW) / cell-days; rows `daynight = ALL`.
- Reference level = median of `S` (and `F`) over the judged months of the witness's calibration fit period (Aqua, Terra, S-NPP 2012-01 to 2016-12; NOAA-20 2018-04 to 2021-12). `S_index = S / reference`.
- Judged only with at least 100 cell-days (else LOW_COUNT, nothing filled in); reference needs 12 judged months (else NO_REFERENCE).
- Flag `LARGE_FIRE_HIGH` (descriptive) when `S_index >= 1.5`; second view at 2.
- `S_rel = S_witness / S_Aqua` (cross-witness consistency).

Rows: 62,690 judged (OK), 144,876 LOW_COUNT, 2,732 NO_REFERENCE. Months without a row stay absent.

## 2. Findings

**Global level is stable [verified on the products].** Global `S` by year (detections per cell-day): Aqua 1.52 to 1.65 (2002 highest, 1.65; 2026 partial year, lowest, 1.52), S-NPP 2.37 to 2.65, NOAA-20 2.32 to 2.52, Terra 1.52 to 1.66. OLS slope of global `S` on year (complete years): Aqua -0.0004, Terra +0.0012, S-NPP +0.0037, NOAA-20 +0.0018 per year; these are small against the level but I set no threshold and do not call them significant. Global FRP per cell-day moves more (Aqua 57 to 90 MW; high in 2002 and 2021/2023).

**VIIRS piles up more than MODIS, and its pile-up varies much more between months [verified].** Share of judged entity-months flagged at 1.5: Aqua 0.3% (countries) and 0.6% (fire regions), Terra 0.4% and 0.7%, but S-NPP 5.8% and 9.1%, NOAA-20 6.6% and 8.7%. At the factor 2: Aqua 0.0 to 0.02%, S-NPP 1.9% and 5.1%, NOAA-20 2.1% and 4.9%. No global month is flagged for any witness: the world average hides the large regional fires.

**The flagged months are the large known fire episodes [verified as a list, interpretation is mine].** Highest `S_index` among rows with at least 1,000 cell-days (all VIIRS): Chile 2017-01 (S-NPP 11.4 detections per cell-day against a reference of 1.7, index 6.7), Spain and Portugal 2025-08, Europe 2014-12, Chile 2023-02, Canada and BONA 2025-05, USA and TENA 2020-09. FRP per cell-day rises in the same rows (index 7 to 33). These months are exactly where one cell-day stands for many detections.

**Flagged months are high-activity months [verified, descriptive].** Median cell-days of flagged rows 4,236, of judged non-flagged rows 1,122. This is consistent with T-020b (saturation at high activity) but is not a test of it, and part of it is selection (a flag needs a large month).

**Flags are not limited to the period outside the reference [verified].** For VIIRS, countries: S-NPP 4.5% inside the reference, 6.4% outside; NOAA-20 6.2% inside, 6.8% outside; Aqua 0.2% and 0.4%. So the flag is mostly the natural month-to-month variability of VIIRS pile-up, with a modest excess after the reference period; it is not a clean drift signal.

**Cross-witness consistency is stable globally [verified].** Median `S_rel`: S-NPP 1.51 inside the reference, 1.52 outside; NOAA-20 1.47 and 1.49; Terra 0.98 and 0.98. By fire region the inside and outside medians agree within about 0.1 in nearly all regions. The exceptions: BONA with NOAA-20 (1.80 inside, 2.62 outside: the 2025 Canadian fires) and UNASSIGNED (S-NPP 1.75 outside, NOAA-20 4.43; no reference). In BONA the VIIRS to Aqua pile-up relation changes in large-fire months, which is the situation in which a ratio fitted on typical months is applied outside its fit conditions.

## 3. Caveats

- **[LIMITATION]** `S` measures pile-up of detections per cell-day, a proxy of fire size/intensity, not fire size. Several detections can come from one fire and one detection can hold several fires (`SCIENTIFIC_METHODOLOGY.md`). Nothing here is a fire count or a burned area.
- **[LIMITATION]** `ALL` cell-days equal day plus night cell-days, so a cell-day with both a day and a night detection counts twice; this affects every witness equally but lowers `S` slightly where night detections are common.
- **[LIMITATION]** Thresholds (100 cell-days, 12 months, 1.5, 2) are my reading, fixed in advance, not tuned. The flag shares depend on them. VIIRS flags are frequent partly because VIIRS detects more small and persistent pixels, so its `S` reference is itself noisy.
- **[LIMITATION]** The reference period is the fit period of the witness; a flag outside it says the month differs from the typical fit month, not that the calibration is wrong. This check does not correct the estimate, does not change a verdict and does not assess whether v0.2 handles it (T-020c).
- **[HYPOTHESIS, not tested]** Saturation (T-020b) is the mechanism behind the VIIRS excess pile-up in large-fire months; a different overpass time or instrument threshold would give the same pattern.
- UNASSIGNED fire-region cells have no reference for most witnesses; their numbers are shown, not interpreted.

## 4. Status

Diagnostic complete. Nothing was tested against a threshold, so there is no PASS/FAIL. Tests: 9 pass (SYNTHETIC data with known answers); `ruff` clean on the task files. No product, threshold or earlier result changed.
