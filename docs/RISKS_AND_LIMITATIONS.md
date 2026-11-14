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
| S10 | MODIS `version` inconsistency hides a processing change | L–M | M | T-007 investigation |

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
