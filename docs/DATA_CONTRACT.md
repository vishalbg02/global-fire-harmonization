# Data Contract: `contract_version: 0.1.0` · **APPROVED (D-016, 2026-11-14)**

This document is the only interface between Member 2 (pipeline) and Member 3 (application). Change it first, with approval, then change the code. Bump `contract_version` on every change: patch for additions, minor for breaking changes.

## Conventions

- **Time:** `year` (int), `month` (1–12). Months refer to UTC calendar months.
- **Missing values:** `null`. Never use `0` to mean "unknown". A real zero is `0`.
- **Units:** `cell_days` are fire-active fine-grid cell-days (explained in `SCIENTIFIC_METHODOLOGY.md`). `frp_sum_mw` is in megawatts. Probabilities are in [0, 1].
- **Harmonized values** are expressed on the **Aqua-equivalent scale** (`scale = "AQUA_EQ_CELL_DAYS"`). The primary user-facing value is `pct_of_normal`.
- **Enumerations** are uppercase strings.
- Files are Parquet unless marked JSON. Fixtures live in `data/fixtures/`, carry `"synthetic": true` in metadata, and are labelled SYNTHETIC.

### Enumerations

| Name | Values |
|---|---|
| `witness` | `AQUA_MODIS`, `TERRA_MODIS` (raw view only), `SNPP_VIIRS`, `NOAA20_VIIRS`, `NOAA21_VIIRS` (reserved) |
| `daynight` | `D`, `N`, `ALL` |
| `data_level` | `SP` (standard/science), `NRT` (provisional), `MIXED` |
| `verdict` | `ABOVE_NORMAL`, `BELOW_NORMAL`, `WITHIN_NORMAL`, `CANNOT_DETERMINE`, `NO_DETECTED_ACTIVITY` |
| `reason_code` | `OUTAGE`, `INSUFFICIENT_BASELINE`, `INSUFFICIENT_OVERLAP`, `WITNESS_DISAGREEMENT`, `WIDE_INTERVAL`, `PROVISIONAL_NRT`, `AQUA_DRIFT_ERA`, `SINGLE_WITNESS`, `POOLED_CALIBRATION`, `DIURNAL_CAVEAT` |
| `entity_type` | `CELL`, `COUNTRY`, `CONTINENT`, `GLOBAL`, `CUSTOM` |
| `pooling_level` | `LOCAL`, `REGION`, `GLOBAL` |
| `test_status` | `PASS`, `FAIL`, `INCONCLUSIVE`, `NOT_RUN` |

## 1. `cells.parquet`: grid definition (one row per analysis cell)

| Field | Type | Description |
|---|---|---|
| `cell_id` | string | Stable ID, e.g. `"g050_r0123_c0456"` (grid code, row, column) |
| `lat_min`, `lat_max`, `lon_min`, `lon_max` | float | Cell bounds (degrees, WGS84) |
| `lat_c`, `lon_c` | float | Cell centre |
| `area_km2` | float | Cell area |
| `country_iso3` | string \| null | Country with the most detections in the cell (from FIRMS file names) |
| `continent` | string \| null | Derived from the country |
| `fire_region` | string | Pooling parent (GFED basis region code or fallback) |
| `stratum_id` | string | Calibration stratum the cell belongs to |

## 2. `cell_month_witness.parquet`: raw observations (one row per cell × month × witness × daynight)

Rows are present only when the witness was operating that month. Rows with zero detections **are** present when the witness had data.

| Field | Type | Description |
|---|---|---|
| `cell_id`, `year`, `month` | | Keys |
| `witness` | enum | |
| `daynight` | enum | `D`, `N` (and `ALL` = D+N) |
| `detections` | int | Hotspot points after filters (informational only; not used for harmonization) |
| `cell_days` | int | Fire-active fine-grid cell-days (**harmonization unit**) |
| `frp_sum_mw` | float | Sum of FRP of the filtered detections |
| `days_available` | int | Days in the month with data for this witness (from outage tables) |
| `days_in_month` | int | |
| `data_level` | enum | |

## 3. `cell_month_harmonized.parquet` (one row per cell × month)

| Field | Type | Description |
|---|---|---|
| `cell_id`, `year`, `month` | | Keys |
| `estimate` | float \| null | Harmonized activity (Aqua-equivalent cell-days) |
| `ci90_low`, `ci90_high` | float \| null | 90% interval |
| `sd` | float \| null | Standard deviation of the estimate |
| `raw_combined_cell_days` | int | Naive raw sum across all operating witnesses (for the raw view) |
| `witnesses_used` | list[enum] | Witnesses that contributed |
| `n_witnesses` | int | |
| `disagreement_scale` | float \| null | Scale factor ≥ 1 applied when witnesses disagree |
| `baseline_median`, `baseline_p25`, `baseline_p75` | float \| null | Same calendar month, baseline years |
| `pct_of_normal` | float \| null | `estimate / baseline_median × 100` (null if the median is 0 or null) |
| `p_above`, `p_below`, `p_within` | float \| null | Probability above p75 / below p25 / within the p25–p75 range |
| `verdict` | enum | |
| `reason_codes` | list[enum] | Why this verdict, and any caveats |
| `data_level` | enum | |
| `method_version` | string | |

## 4. `entity_month.parquet`: preset areas (one row per entity × month)

The same fields as §3 (from `estimate` to `method_version`), keyed by `entity_type`, `entity_id` and `entity_name` instead of `cell_id`. It also has:
- `n_cells` (int)
- `raw_by_witness`, a JSON string map `{witness: cell_days}` for the witness-comparison chart

Custom-area API responses use this same shape with `entity_type = "CUSTOM"`.

## 5. `calibration.parquet` (one row per stratum × witness × daynight × season)

| Field | Type | Description |
|---|---|---|
| `stratum_id`, `witness`, `daynight`, `season` | | Keys (season = `DJF`, `MAM`, `JJA` or `SON`, or month-of-year if adopted) |
| `ratio` | float | Multiplier converting the witness to the Aqua-equivalent scale |
| `ratio_sd` | float | Uncertainty of the ratio |
| `n_overlap_months` | int | Months used to fit |
| `fit_period` | string | e.g. `"2012-01/2016-12"` |
| `pooling_level` | enum | |

## 6. `validation_results.json`

```json
{
  "contract_version": "0.1.0",
  "method_version": "string",
  "generated_at": "ISO-8601",
  "synthetic": false,
  "tests": [
    {
      "test_id": "A1-INDONESIA-2015",
      "family": "A",
      "title": "Real anomaly preserved (two independent paths)",
      "case": "Indonesia Sep–Oct 2015",
      "criterion": "Same direction; peak month ±1; magnitudes overlap within 90% intervals",
      "threshold": "pre-registered at G1",
      "measured": {"aqua_only_pct_of_normal": null, "snpp_only_pct_of_normal": null},
      "status": "NOT_RUN",
      "notes": ""
    }
  ]
}
```

## 7. `metadata.json`

```json
{
  "contract_version": "0.1.0",
  "method_version": "string",
  "synthetic": false,
  "generated_at": "ISO-8601",
  "grid": {"analysis_deg": null, "fine_deg": null},
  "baseline_years": [2003, 2022],
  "first_month": "2002-07",
  "latest_month": "YYYY-MM",
  "provisional_months": ["YYYY-MM"],
  "witnesses": ["AQUA_MODIS", "SNPP_VIIRS", "NOAA20_VIIRS"],
  "data_snapshot": {"zips_downloaded": "YYYY-MM-DD", "api_pulled": "YYYY-MM-DD"},
  "citation": "NASA FIRMS ..."
}
```

## 8. Python function contract (shared science)

```text
harmonize_area(cell_ids: list[str], months: list[(year, month)] | None) -> list[EntityMonthRecord]
```

The return shape is §4. It must be deterministic for the same inputs and `method_version`. It is used by both the batch entity aggregation and the custom-area API.

## Status of additions

The workstream prompts (`docs/prompts/`, shared section §S) list items marked **[PROPOSED ADDITION]**:
- `cell_id` format and cell-bound convention
- entity IDs
- API envelope and error format
- `PRODUCTS_DIR`
- the product path rule

They are **not part of v0.1.0** until the Lead approves them (D-022). Approving them means adding them here and bumping the contract to `0.1.1`.

## Open items (decide at G1)

`analysis_deg` and `fine_deg` (D-009); `season` definition; final `cell_id` format; whether `entity_month` includes continents and global from the start (recommended: yes).
