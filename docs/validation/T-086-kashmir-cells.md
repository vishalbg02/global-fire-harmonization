# T-086: Jammu and Kashmir cells by India's official boundary (D-033)

> Member 2 · 2026-11-15 · method 0.1.0 unchanged. Script: `python pipeline/kashmir_cells.py --ne <ne_10m_admin_0_countries_ind.geojson> [--apply]`; tests: `pipeline/tests/test_kashmir_cells.py`. Raw output: `data/interim/qa/kashmir_cells.json` (not committed).

## 1. Input and rule

- **File [VERIFIED]:** `ne_10m_admin_0_countries_ind.geojson`, Natural Earth Admin 0 Countries, India point of view, version 5.1.1, **1:10m**, 13,242,091 bytes, SHA-256 `3e67a5a6ddeff3247ca8400cd2514fd4a5ac6e5432823b25d610a7028597d45f`. There is no 1:50m India point-of-view file.
- **Labelled limitation, resolution mix:** the existing country mapping uses the 1:50m default boundary. Only cells in the box 72.5 to 80.5 degrees E, 32.5 to 37.2 degrees N are changed.
- **Rule:** a cell in the box whose **centre** is inside the India polygon and whose country is Pakistan or China becomes India. A cell with no country is not given one. Nothing else in `cells.parquet` changes.

## 2. Result [VERIFIED]

- Cells in the box before: 109 (none 1, CHN 27, IND 39, PAK 42).
- **Reassigned to India: 32 cells** (PAK 26, CHN 6).
- Reported, not changed: 0 Indian cells in the box with the centre outside the India polygon; 12 cells outside the box with the centre inside the polygon (country in FIRMS: PAK g050_r0228_c0497, PAK g050_r0228_c0498, PAK g050_r0228_c0500, MMR g050_r0228_c0548, BGD g050_r0229_c0544, PAK g050_r0231_c0500, NPL g050_r0232_c0534, NPL g050_r0232_c0535, BGD g050_r0232_c0536, BTN g050_r0233_c0543, NPL g050_r0235_c0524, NPL g050_r0238_c0520); 2 cells with no country inside the polygon (g050_r0227_c0496, g050_r0251_c0518).

### The reassigned cells

| Cell | Centre (E, N) | Was |
|---|---|---|
| `g050_r0246_c0507` | 73.75, 33.25 | PAK |
| `g050_r0246_c0518` | 79.25, 33.25 | CHN |
| `g050_r0247_c0507` | 73.75, 33.75 | PAK |
| `g050_r0248_c0507` | 73.75, 34.25 | PAK |
| `g050_r0248_c0517` | 78.75, 34.25 | CHN |
| `g050_r0248_c0518` | 79.25, 34.25 | CHN |
| `g050_r0249_c0507` | 73.75, 34.75 | PAK |
| `g050_r0249_c0511` | 75.75, 34.75 | PAK |
| `g050_r0249_c0517` | 78.75, 34.75 | CHN |
| `g050_r0250_c0507` | 73.75, 35.25 | PAK |
| `g050_r0250_c0508` | 74.25, 35.25 | PAK |
| `g050_r0250_c0509` | 74.75, 35.25 | PAK |
| `g050_r0250_c0510` | 75.25, 35.25 | PAK |
| `g050_r0250_c0511` | 75.75, 35.25 | PAK |
| `g050_r0250_c0512` | 76.25, 35.25 | PAK |
| `g050_r0250_c0519` | 79.75, 35.25 | CHN |
| `g050_r0250_c0520` | 80.25, 35.25 | CHN |
| `g050_r0251_c0506` | 73.25, 35.75 | PAK |
| `g050_r0251_c0507` | 73.75, 35.75 | PAK |
| `g050_r0251_c0508` | 74.25, 35.75 | PAK |
| `g050_r0251_c0509` | 74.75, 35.75 | PAK |
| `g050_r0251_c0510` | 75.25, 35.75 | PAK |
| `g050_r0251_c0511` | 75.75, 35.75 | PAK |
| `g050_r0251_c0512` | 76.25, 35.75 | PAK |
| `g050_r0252_c0505` | 72.75, 36.25 | PAK |
| `g050_r0252_c0507` | 73.75, 36.25 | PAK |
| `g050_r0252_c0508` | 74.25, 36.25 | PAK |
| `g050_r0252_c0509` | 74.75, 36.25 | PAK |
| `g050_r0252_c0510` | 75.25, 36.25 | PAK |
| `g050_r0252_c0511` | 75.75, 36.25 | PAK |
| `g050_r0253_c0508` | 74.25, 36.75 | PAK |
| `g050_r0253_c0509` | 74.75, 36.75 | PAK |

## 3. Regenerated products (Git LFS)

- `cells.parquet`: only `country_iso3` of the 32 cells changed; every other column, row and the order are equal (asserted by the script).
- `entity_month.parquet`: the COUNTRY rows IND, PAK, CHN (879 rows) come from `verdicts.entity_month` run on the new cells; the other 67,683 rows are those of `main` (verified equal). `n_cells`: IND 1,221 (was 1,189), PAK 294 (320), CHN 3,285 (3,291). Raw cell-days summed over the three countries are equal in all 293 months. Verdicts change in 22 country-months: IND 7, PAK 15, CHN 0.
- A full recomputation of the untouched rows agrees with `main` to float rounding (estimate to 2.0e-15 relative; a tail probability to 2.8e-7 relative where the value is below 1e-14); the script keeps the rows of `main`.
- SHA-256: `cells.parquet` `decd81e6d32c046fb004cdf2f7dc52c4ea0fd52c22d4398e9842662209c6558d`; `entity_month.parquet` `1d8bf0bf4ffe0948870da9f3e6b9ebabf469833866f2142d31babd97ee921195`.

## 4. Checks

| Check | Result |
|---|---|
| `contract_check` on `entity_month`, `cells`, `calibration` (`real=True`) | 0 errors |
| Full `contract_check` of all tables | **Not completed: memory error** on this machine (the known limit of T-077; `cell_month_harmonized.parquet`, which this PR does not change, is the large table) |
| `python pipeline/number_check.py` | 0 mismatches, 1 note (as before) |
| `python pipeline/featured_stories.py --check` | up to date (the five featured cases are not among the changed entities) |
| `python pipeline/analytics_check.py` | 0 mismatches |
| `pytest` kashmir_cells, featured_stories, analytics_check, number_check | 32 passed |
| `ruff check pipeline api` | clean |

## 5. Limitations

- Resolution mix (1:10m boundary, 1:50m default mapping); 12 cells outside the box and 2 cells without a country are reported, not changed.
- `cell_month_harmonized.parquet` is not regenerated: the 32 cells lack the cell-level `DIURNAL_CAVEAT` (October and November from 2020) until it is; no value or verdict is affected by that caveat.
- Country borders on the map are Member 3's (T-085).
