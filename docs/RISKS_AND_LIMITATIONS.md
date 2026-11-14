# Risks and Limitations

Likelihood and impact: L (low) · M (medium) · H (high).

## 1. Scientific risks

| # | Risk | L | I | Mitigation / fallback |
|---|---|---|---|---|
| S1 | One conversion ratio is invalid across fire regimes | H (certain if done naively) | H | Partial pooling by stratum; Fallback A = fixed regional ratios |
| S2 | Ratios not stationary (fire sizes change within a region) | M | M | Calibration never re-fitted per year; large-fire diagnostic (P1); disclosed |
| S3 | Aqua drift contaminates the reference scale after ~2021–22 | H | M | Drift measured empirically; Aqua removed from the combination after the cutoff; wider intervals shown |
| S4 | Intervals too narrow (witness errors correlated) | H | M | Disagreement inflation; coverage test D1; disclosed |
| S5 | Regional burning-time shifts (e.g. Punjab) cause false "decline" | H (where present) | M | `DIURNAL_CAVEAT`; never claim burning fell there |
| S6 | Real anomalies suppressed by calibration | L–M | H | Tests A1, A2, CTRL; calibration fitted only on overlap years |
| S7 | Baseline depends on harmonization | M | M | Sensitivity test S1 with an Aqua-measured baseline |
| S8 | Results sensitive to grid size or thresholds chosen after seeing results | M | H | Pre-registration at G1 |
| S9 | Validation tests fail | M | M | Publish the failures and narrow claims. Honesty is part of the product |
| S10 | MODIS `version` inconsistency hides a processing change | L–M | M | Investigated in T-007: no step in type 0 or kept counts relative to S-NPP at the 2018 or 2023 version changes; static-source share rises about 1.5 times in 2018 and low-confidence share and mean FRP rise in 2023 (cause open); nothing dropped; flag or adjust is the Lead's decision |
| S11 | Static-source mask for NRT is imperfect (NRT has no `type`) | H (certain) | M | Measured on held-out years: removes 88% of static detections and wrongly removes 0.55% of fire detections at the proposed setting; residual static sources remain in NRT months, which are already provisional; the setting (0.05° cells, share at least 0.5, at least 10 detections) was approved by the Lead 2026-11-14 |
| S12 | Night-source mask (D-025) misses flares lit on fewer than 1% of nights or in fewer than 10 months (residual rows in the Permian and Bakken: `TENA_b048_030` NOAA-20 DJF at 0.14 of global, `TENA_b055_030` S-NPP JJA at 0.15) | M | L | Held-out cost is at most 0.94% of VIIRS night type 0 detections (2024 to 2025); the residual rows are visible in the sanity table; approved by the Lead 2026-11-14 |
| S13 | Eight Bolivian cells (Chiquitano, 20 to 15 S, 62.5 to 60 W) are still flagged by the night-source rule. Cause **OPEN**: no type 2 or 3 labels, a Jul to Nov peak, 4,712 type 0 detections over 14 years | L | L | Negligible volume against the dry-forest total (Jul to Oct holds 49.8% of the 220 cells flagged before condition 4); accepted as a documented limitation by the Lead 2026-11-14 |
| S14 | Fagradalsfjall (`EURO_b061_063`) NOAA-20 JJA night ratio stays `LOCAL` at 8.6 times global: the 2021 eruption ran from March to September, so no single month passes the burst rule's 50% | L | L | One stratum and season; a season-year test would catch it but would move about 23% of `LOCAL` rows (3,345 of 14,422), so it is not applied; accepted by the Lead 2026-11-14. Treat night conversions there with care |
| S15 | Low night ratios in savanna and agricultural fire regions (SE Asia DJF and SON, southern Africa JJA, northern Africa DJF) are kept as `LOCAL`. They are a **hypothesis**, not a verified fact: VIIRS (375 m) sees many small night fires that MODIS (1 km) misses | M | M | Accepted by the Lead as real regional differences (2026-11-14); to be confirmed in T-012 and test E1 by region; if they are artefacts, night conversions in those regions would be too low or too high |
| S16 | Interval coverage on the holdout years (T-012, 2017 to 2021) is inside 80% to 97% when pooled (regions 0.818, countries 0.811; totals 0.847 and 0.826) but below 80% for night units alone (0.750 regions, 0.794 countries), and about half of the individual regions and countries are below 80% | M | M | The `phi` and `kappa` variance (T-013) lifted pooled coverage from 0.62 and 0.78; test D1 (T-022) is the final check; night and small-area verdicts need wider thresholds or a `WIDE_INTERVAL` caveat; `phi` and `kappa` are in-sample lower bounds |
| S17 | Aqua drift: the pre-registered test (global day, S-NPP) detects none, but night-time Aqua / converted VIIRS falls from about 2024-05 (S-NPP) to 2024-09 (NOAA-20) in both witnesses. The cutoff of D-005 (Aqua night excluded from 2024-05, Aqua day kept) **was chosen after seeing the results**, as a documented deviation from the registered rule; it uses the earlier of two overlapping onsets; its cause (Aqua, processing or VIIRS) is open | M | M | Approved by the Lead 2026-11-14 (D-005); months from 2024-05 carry `AQUA_DRIFT_ERA`; the estimates of 2024-05 to 2026-10 move by +0.7% to +1.2% on average (Brazil, Australia, Indonesia) and their sd by -0.6% to -19%; check in T-021 (B3) and T-022; a change of date needs the Lead; one combination method for all months (seam check, PR #45: the totals method differs from it by 0.35% at the median but 28% at the 95th percentile) |
| S18 | Intervals are not valid for regions without their own calibration data. In test E1 (T-025) a left-out region is converted with the global ratio fitted without it, and the 90% interval covers only 10% to 80% of its units; the leave-out error is 2 to 6 times the error with the region seen, and E1 passes against a weak bar (the naive merge) | M | M | Every region in the product is calibrated with its own data, so the E1 situation does not occur in the products; no unseen-region interval now (Lead decision on PR #57, 2026-11-15); do not present intervals for areas outside the calibrated fire regions |

## 2. Technical risks

| # | Risk | L | I | Mitigation / fallback |
|---|---|---|---|---|
| T1 | Slow venue internet for 9.1 GB | M | H | Start at H0 on the best connection; MODIS + S-NPP first; NOAA-20 2018–2021 minimum plus 2026 via the API |
| T2 | Global processing slower than estimated | M | H | Coarser grid; split years across machines. **Never silently drop global coverage**: degrade resolution instead |
| T3 | 2026 API pulls fail or are throttled | L–M | H | Start early; retry with backoff; if unavailable, the record ends 2025-12 with a clear label |
| T4 | Contract mismatch between workstreams | M | H | Contract-first; fixtures by H3; validators on both sides |
| T5 | Integration crunch | H | H | Fixture-driven UI from H1; feature freeze at H28; submit at H34 |
| T6 | Fire-region mask unavailable | M | L | UN-subregion fallback from country names |
| T7 | Country name mapping errors | M | M | T-009 with 100% coverage check |
| T8 | Node 20 (EOL) on team machines | H | L | Install Node 22/24 LTS at setup |
| T9 | Custom areas now return the real series from `harmonize_area()` (T-035 follow-up); verdicts and baselines stay empty until T-014. The flow has been run against the real products through the API; the area is limited only by the response time (T16) | M | L | The app shows the server's message on `503`; preset areas are unaffected |
| T10 | Drawing a rectangle needs a pointer (terra-draw with its MapLibre adapter, D-024) | M | L | The typed W/S/E/N form is the keyboard and screen-reader route to a custom area (T-035) |
| T11 | The witness comparison chart (T-037) is a canvas, not keyboard-navigable; its Aqua-drift and provisional marks are shown as shaded bands, which a screen reader cannot read from the chart | M | L | A table view gives the same values with a Notes column stating outage, drift-era or provisional per month; not yet checked with a real screen reader |
| T12 | The anomaly overview (T-040) cannot say how many areas were left out because they cannot be judged: the API returns only the above and below verdicts and gives no count of the others, so the app shows "N of M are in neither ranking" (which also includes areas that are within normal). An exact count would need an API addition | M | L | The wording says what the number includes; an API field for the excluded counts can be proposed to the Lead |
| T13 | A custom-rectangle CSV export (T-038) uses the same `harmonize_area()` call as the custom series, so it is as slow as T16 and answers `503` only when the function or the products are unavailable | M | L | Verified on a country-sized box against the real products |
| T14 | Raw-only real data (T-039 phase 1): harmonized values, baselines, verdicts and the anomaly list are not available yet; the raw-only products carry `witnesses_used = []` and `n_witnesses = 0` even where raw counts exist, and `metadata.json` lists three witnesses although Terra MODIS is in the data; an outage indicator from `days_available` is not exposed by any served product | H until T-014 | M | The app hides what is missing and labels the view; the products and the indicator are for the Lead and Member 2 to settle |
| T15 | A real `GET /api/map` month is about 28 MB and 0.6 s (56,238 cells × all contract fields) | M | L | Measured on a local machine; acceptable for the demo; compression or a slimmer map payload is a T-042 or contract question |
| T16 | A custom-area request runs `harmonize_area()` over the 146.6 million-row witness product: about 3.2 to 3.5 s for a country-sized box and about 12.9 s for the whole world (local machine, 2026-11-14); no cache or size limit | M | M | Measured, not yet tuned. A limit or cache needs the Lead's decision; the app shows a loading state meanwhile |
| T17 | After T-042: a new custom area still takes about 3.3 s (country-sized box) to 8 s (world) on the first request, because `harmonize_area()` scans the witness product (profile: about 2.7 to 4.5 s of DuckDB scan and aggregate plus about 1.4 to 2 s of pandas record building in `pipeline/`); a repeat request is about 0.01 s from a bounded in-process cache (per process, 32 entries). Cutting the first request needs a change in `pipeline/` or a pre-aggregated product, revisited after T-014 | M | M | Loading message in the app; measured, not tuned further |
| T18 | Colour-vision check (T-042): a few colour pairs stay below the project's threshold (the drift-era mark against the harmonized line under protanopia; CANNOT_DETERMINE against NO_DETECTED_ACTIVITY; the "no data" calendar cell). Each has a non-colour cue (text, icon, dash pattern, width). The cells that had none now do: "outside the record" in the calendar has a diagonal cross (chart) or hatching (table and legend), and "no detected activity" and "no data" on the map have a dark outline, shown in the legends | L | L | Pinned in `colorVision.test.tsx` with the cue; the map canvas has no cell-by-cell keyboard selection (routes: search, typed box, calendar table, anomaly list) |
| T19 | The offline copy (T-043) is a snapshot: it shows the values of the products it was exported from, on the date in its notice, and has no custom areas. A stale copy would show old data as current | M | M | A visible "Offline copy" notice with the export date and data snapshot; the copy is regenerated from the final products (T-014) before the demo; never mixed real and synthetic (one products directory per export) |

## 3. Performance risks

| # | Risk | Mitigation |
|---|---|---|
| P1 | Tens of thousands of cells per month in the browser | WebGL grid layer; per-month payloads; 0.5° analysis grid |
| P2 | Custom-area queries over many cells | DuckDB over partitioned Parquet; cap the area size if needed (disclose) |
| P3 | Free hosting cold starts or limits | Local demo primary; static fallback for preset views |

## 4. Data limitations (permanent; disclose in the app)

- Hotspots ≠ fires, burned area or emissions.
- No detection ≠ no fire (clouds, smoke, canopy, gaps, short fires).
- Snapshots at overpass times only.
- NRT months are provisional; NRT lacks the `type` field.
- The country archives exclude detections outside country boundaries (open ocean, possibly some disputed areas).
- No per-cell overpass or cloud counts in the MVP.
- MODIS ends 2026–27; S-NPP ended 2026-11-02.

## 5. Fallback summary

| Trigger | Fallback |
|---|---|
| Pooling not working by G2 | **Fallback A:** fixed fire-region × season × day/night ratios |
| Combination not working by G3 | **Fallback B:** sequential witnesses (Aqua → S-NPP → NOAA-20) with cross-checks |
| API host unavailable | Static fallback build (preset views); custom area local-only |
| Behind schedule at H24 | Cut in order: deployment → large-fire check → polygon custom area → test E1 → blindness indicator |
