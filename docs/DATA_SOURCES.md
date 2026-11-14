# Data Sources

All facts are marked with their verification status. Re-verify anything marked **[ASSUMPTION]** before relying on it.

## 1. NASA FIRMS global yearly archives: **primary historical source**

- **URL pattern [VERIFIED 2026-11-14]:**
  `https://firms.modaps.eosdis.nasa.gov/data/country/zips/{SENSOR}_{YYYY}_all_countries.zip`
  `SENSOR` ∈ `modis`, `viirs-snpp`, `viirs-jpss1` (NOAA-20)
- **Access:** plain HTTPS download, **no login required** (tested).
- **Contents:** one CSV per country per year, e.g. `modis/2020/modis_2020_India.csv`. The 2020 MODIS zip has 213 members; S-NPP 2020 has 220.
- **Single-country files** are also available: `https://firms.modaps.eosdis.nasa.gov/data/country/{SENSOR}/{YYYY}/{SENSOR}_{YYYY}_{Country}.csv`

### Sizes (zipped, from HTTP Content-Length) **[VERIFIED 2026-11-14]**

| Sensor | Years available | Total zipped |
|---|---|---|
| MODIS (Terra + Aqua) | 2000–2025 (2000 is partial) | 1.8 GB (≈62–86 MB per full year) |
| VIIRS S-NPP | 2012–2025 | 4.7 GB (≈293–368 MB per year) |
| VIIRS NOAA-20 (`viirs-jpss1`) | 2018–2025 | 2.6 GB (≈248–383 MB per year) |
| **Total** | | **≈9.1 GB** |

- **Not available as zips [VERIFIED]:** any 2026 file; NOAA-21 (`viirs-jpss2` and `viirs-noaa21` return nothing).
- **Unzipped size [VERIFIED 2026-11-14, T-005]:** 43,314,408,585 bytes of CSV when unzipped (40.3 GiB, 43.3 GB) across the 46 zips. The earlier estimate was ≈41 GB.
- **Row count [VERIFIED 2026-11-14, T-003]:** 546,469,853 detections in the 46 zips (the earlier estimate was ≈475 million), before any filtering. Per sensor and year: see "Row counts per sensor and year" below.

### Columns [VERIFIED 2026-11-14 from file headers]

- **MODIS:** `latitude, longitude, brightness, scan, track, acq_date, acq_time, satellite, instrument, confidence, version, bright_t31, frp, daynight, type`
- **VIIRS:** `latitude, longitude, bright_ti4, scan, track, acq_date, acq_time, satellite, instrument, confidence, version, bright_ti5, frp, daynight, type`
- Field notes:
  - `satellite`: `Terra`, `Aqua`, `N` (S-NPP), `N20` (NOAA-20).
  - `acq_time`: HHMM in **UTC**.
  - MODIS `confidence`: 0–100. VIIRS `confidence`: `l`, `n` or `h`.
  - `type` (archive data only): 0 = presumed vegetation fire, 1 = active volcano, 2 = other static land source, 3 = offshore.
- **MODIS `version` values [VERIFIED 2026-11-14, T-007]:** `6.2` (2002 to 2017), `6.03` (2018 to 2022), `61.03` (2023 to 2026-08), `6.1NRT` (NRT from 2026-09). See the T-007 section below for the finding and its limits.
- **Coverage note:** country files contain only detections attributed to a country. Open-ocean detections, and possibly some disputed areas, are absent. Acceptable, because we filter offshore and static sources anyway.

### Row counts per sensor and year (T-003) **[VERIFIED 2026-11-14]**

Rows read from the CSVs of the 46 zips (2002 to 2025) and the 2026 API files (T-002), and written to `data/interim/detections/` in the unified schema. Nothing was filtered, de-duplicated or dropped, so these are raw counts. For every sensor-year the rows read equal the rows written. No value failed to cast, no unexpected columns or satellite codes were found, and no row had a date outside its year.

| Year | MODIS (Terra + Aqua) | VIIRS S-NPP | VIIRS NOAA-20 | Total |
|---|---|---|---|---|
| 2002 | 3,699,859 | - | - | 3,699,859 |
| 2003 | 5,149,401 | - | - | 5,149,401 |
| 2004 | 5,092,534 | - | - | 5,092,534 |
| 2005 | 5,125,152 | - | - | 5,125,152 |
| 2006 | 4,688,046 | - | - | 4,688,046 |
| 2007 | 5,134,642 | - | - | 5,134,642 |
| 2008 | 4,818,997 | - | - | 4,818,997 |
| 2009 | 4,456,446 | - | - | 4,456,446 |
| 2010 | 4,715,142 | - | - | 4,715,142 |
| 2011 | 4,699,314 | - | - | 4,699,314 |
| 2012 | 4,959,509 | 20,864,680 | - | 25,824,189 |
| 2013 | 4,226,648 | 19,296,980 | - | 23,523,628 |
| 2014 | 4,434,374 | 20,190,209 | - | 24,624,583 |
| 2015 | 4,741,228 | 21,329,469 | - | 26,070,697 |
| 2016 | 4,415,910 | 20,247,889 | - | 24,663,799 |
| 2017 | 4,453,181 | 19,984,137 | - | 24,437,318 |
| 2018 | 4,184,262 | 19,067,085 | 14,524,817 | 37,776,164 |
| 2019 | 4,578,188 | 20,990,294 | 20,742,304 | 46,310,786 |
| 2020 | 4,440,623 | 20,619,331 | 20,385,806 | 45,445,760 |
| 2021 | 4,384,343 | 20,247,675 | 20,059,802 | 44,691,820 |
| 2022 | 3,789,164 | 17,164,365 | 18,043,578 | 38,997,107 |
| 2023 | 4,664,302 | 21,750,317 | 21,288,380 | 47,702,999 |
| 2024 | 4,848,247 | 20,976,982 | 22,511,092 | 48,336,321 |
| 2025 | 3,693,555 | 18,415,101 | 18,376,493 | 40,485,149 |
| 2026 (API) | 3,098,525 | 15,461,912 | 17,020,284 | 35,580,721 |
| **Total** | **112,491,592** | **296,606,426** | **172,952,556** | **582,050,574** |

2026 combines standard (SP) and near-real-time (NRT) API data. Terra and Aqua, S-NPP (`N`) and NOAA-20 (`N20`) appear only in their own sensor's files. Counts per satellite and data level are in `data/interim/detections/row_counts.tsv` (not committed).

### QA summary of the normalized detections (T-005) **[VERIFIED 2026-11-14]**

Computed by `python pipeline/qa_filters.py` over all 582,050,574 rows. Nothing was dropped, de-duplicated or altered; every filter below is counted, not applied.

**Value domains.** No row has latitude or longitude out of range, a date outside its file's year, an invalid time (`acq_time_utc` 0000 to 2359, minutes below 60), a confidence value outside its domain (MODIS 0 to 100, VIIRS l/n/h), a `daynight` value other than D or N, a `type` other than 0 to 3, a non-positive `scan` or `track`, or a missing key field. The one exception is **478 rows with a negative `frp`** (values from -59.2 to -0.01 MW, scattered across the three sensors and many years; kept as delivered in the normalized data). **Decision, approved by the Lead 2026-11-14:** negative `frp` is treated as `null` when summing `frp_sum_mw`; cell-day counts are unaffected.

**Duplicates.** Exact duplicates on (satellite, lat, lon, date, time): 252 rows in total (244 repeat inside the same country file, 8 appear only in another country's file), which is 0.00004% of the rows. Partitions do not overlap in time, so there are no duplicates between the 2025 zip and the 2026 API data. Not removed from the normalized data. **Lead decision (2026-11-14):** remove exact duplicates when computing cell-days in T-006; they cannot change presence-based cell-days anyway.

**Filter funnel** (`SCIENTIFIC_METHODOLOGY.md` §4.1; counted only):

| Sensor | Level | Rows | Type filter (SP type 0, NRT kept) | Confidence only | Type and confidence |
|---|---|---|---|---|---|
| MODIS | NRT | 796,045 | 796,045 | 756,434 | 756,434 |
| MODIS | SP | 111,695,547 | 107,875,842 | 106,395,345 | 102,835,267 |
| VIIRS_NOAA20 | NRT | 7,460,323 | 7,460,323 | 6,600,887 | 6,600,887 |
| VIIRS_NOAA20 | SP | 165,492,233 | 153,977,067 | 146,392,919 | 135,255,051 |
| VIIRS_SNPP | NRT | 6,602,259 | 6,602,259 | 5,888,989 | 5,888,989 |
| VIIRS_SNPP | SP | 290,004,167 | 270,217,892 | 257,514,732 | 238,377,999 |

Standard-data rows by `type` (the filter keeps type 0):

| Sensor (SP) | type 1 volcano | type 2 static land | type 3 offshore |
|---|---|---|---|
| MODIS | 84,167 | 3,691,725 | 43,813 |
| VIIRS_NOAA20 | 176,214 | 10,700,270 | 638,682 |
| VIIRS_SNPP | 331,538 | 18,399,472 | 1,055,265 |

**Static-source mask** (needed because NRT rows have no `type`). Per fine cell, the share of SP detections from 2012 to 2025 whose `type` is 2 or 3. Hold-out: cells built from SP 2012 to 2023, tested on SP 2024 to 2025, where `type` is known. Minimum 10 detections per cell (a minimum of 3 gives almost the same numbers; see the full table in the local summary):

| Fine grid | Min share static | Cells masked | NRT rows masked | Static detections removed (hold-out) | Fire (type 0) wrongly removed (hold-out) | Precision |
|---|---|---|---|---|---|---|
| 0.05° | 0.3 | 17,092 | 861,542 (5.8%) | 91.3% | 0.68% | 90.1% |
| 0.05° | 0.5 | 10,929 | 808,973 (5.4%) | 87.8% | 0.55% | 91.6% |
| 0.05° | 0.7 | 7,208 | 733,542 (4.9%) | 82.5% | 0.41% | 93.2% |
| 0.05° | 0.9 | 3,675 | 530,229 (3.6%) | 61.9% | 0.19% | 95.6% |
| 0.1° | 0.3 | 9,955 | 885,511 (6.0%) | 91.3% | 0.88% | 87.6% |
| 0.1° | 0.5 | 6,781 | 825,763 (5.6%) | 88.0% | 0.70% | 89.5% |
| 0.1° | 0.7 | 4,612 | 733,125 (4.9%) | 81.7% | 0.49% | 91.9% |
| 0.1° | 0.9 | 2,151 | 488,701 (3.3%) | 57.2% | 0.20% | 95.1% |

**Decision, approved by the Lead 2026-11-14:** the static-source mask uses 0.05° cells, a static share of at least 0.5 and at least 10 detections, built on SP data. This also fits a 0.05° fine grid for D-009 / T-051, which is not locked yet. Evidence: fine grid 0.05°, share static at least 0.5, at least 10 detections. It masks 10,929 cells and 808,973 of the 14,858,627 NRT rows (5.4%), removes 87.8% of static detections on held-out years, and wrongly removes 0.55% of fire detections. The 0.1° grid removes slightly more static detections at the same share but loses more fire. A higher share lowers the fire loss and the recall. The setting is approved but not yet applied anywhere; the mask files stay local.

**Day/night against the solar zenith rule** (night when the zenith angle is above 85 degrees; 0.5% sample; rows within 1 degree of the limit excluded):

| Sensor | Level | Decidable sample rows | Agree with the zenith rule |
|---|---|---|---|
| MODIS | NRT | 3,989 | 3,984 (99.87%) |
| MODIS | SP | 557,430 | 557,430 (100.00%) |
| VIIRS_NOAA20 | NRT | 37,677 | 37,675 (99.99%) |
| VIIRS_NOAA20 | SP | 826,093 | 825,808 (99.97%) |
| VIIRS_SNPP | NRT | 32,996 | 32,991 (99.98%) |
| VIIRS_SNPP | SP | 1,451,276 | 1,450,888 (99.97%) |

NRT day/night agrees with the zenith rule almost as well as SP does (99.87% to 99.99%), so recomputing it would change very few rows. **Decision, approved by the Lead 2026-11-14: not recomputed.** FIRMS's `daynight` is kept as delivered, because source values are not altered. Measured only.

### MODIS `version` values (T-007) **[VERIFIED 2026-11-14 unless labelled]**

Computed by `python pipeline/modis_version.py` on the normalized MODIS detections (standard data for the step test). No row was dropped, filtered or changed.

**What the values are.** The FIRMS readme in each zip calls the field "Collection / Version" and says to use it to tell NRT from standard data; it does not explain individual values. So the meaning of each string below is **not documented in the shipped files [OPEN]**.

| `version` | Applies to | Rows |
|---|---|---|
| `6.2` | Terra and Aqua standard data, 2002-01-01 to 2017-12-31 | 74,794,635 |
| `6.03` | Terra and Aqua standard data, 2018-01-01 to 2022-12-31 (and the Morocco and Somalia files in earlier years, see below) | 21,392,328 |
| `61.03` | Terra and Aqua standard data, 2023-01-01 to 2026-08-31 | 15,508,584 |
| `6.1NRT` | Terra and Aqua near-real-time data, 2026-09-01 onward | 796,045 |

**Rows with a minority version.** Before 2018 the only `6.03` rows are 15,748 rows in two country files, Somalia (10,637) and Morocco (5,111), covering 2002 to 2017; every other country file carries `6.2` in those years. The reason is not documented **[OPEN]**; they are 0.014% of the MODIS rows.

**Step test.** For every 1 January from 2004 to 2025, the 12 months after are compared with the 12 months before. Each cell shows the after/before ratio at the version boundary and, in brackets, the range of the same ratio at the other 1 January boundaries (21 to 22 years for MODIS, 11 for S-NPP). A star marks a value outside that range. S-NPP is a control: a different instrument that did not change version.

*Boundary 2018-01-01 (`6.2` to `6.03`)*

| Measure | Terra | Aqua | S-NPP (control) |
|---|---|---|---|
| Rows (all) | 0.927 [0.71 to 1.12] | 0.947 [0.79 to 1.09] | 0.954 [0.85 to 1.10] |
| Rows relative to S-NPP | 0.971 [0.80 to 1.06] | 0.992 [0.90 to 1.12] | - |
| Type 0 rows relative to S-NPP | 0.941 [0.79 to 1.07] | 0.982 [0.91 to 1.11] | - |
| Kept rows (type 0 and confidence) relative to S-NPP | 0.942 [0.80 to 1.07] | 0.981 [0.92 to 1.12] | - |
| Low-confidence share | 0.986 [0.94 to 1.10] | 0.983 [0.95 to 1.05] | 0.977 [0.96 to 1.09] |
| Mean confidence | 0.996 [0.98 to 1.01] | 0.996 [0.99 to 1.01] | - |
| Mean FRP | 1.015 [0.79 to 1.16] | 0.987 [0.89 to 1.09] | 0.982 [0.96 to 1.06] |
| Daytime share | 1.019 [0.91 to 1.05] | 1.006 [0.99 to 1.02] | 1.009 [0.97 to 1.06] |
| Static-source share (type 2 or 3) | 1.574 [0.83 to 1.40]* | 1.504 [0.87 to 1.22]* | 1.045 [0.90 to 1.12] |

*Boundary 2023-01-01 (`6.03` to `61.03`)*

| Measure | Terra | Aqua | S-NPP (control) |
|---|---|---|---|
| Rows (all) | 1.253 [0.71 to 1.12]* | 1.220 [0.79 to 1.09]* | 1.267 [0.85 to 1.10]* |
| Rows relative to S-NPP | 0.989 [0.80 to 1.06] | 0.963 [0.90 to 1.12] | - |
| Type 0 rows relative to S-NPP | 0.990 [0.79 to 1.07] | 0.956 [0.91 to 1.11] | - |
| Kept rows (type 0 and confidence) relative to S-NPP | 0.972 [0.80 to 1.07] | 0.944 [0.92 to 1.12] | - |
| Low-confidence share | 1.126 [0.94 to 1.10]* | 1.085 [0.95 to 1.05]* | 0.944 [0.96 to 1.09]* |
| Mean confidence | 1.018 [0.98 to 1.01]* | 1.004 [0.99 to 1.01] | - |
| Mean FRP | 1.291 [0.79 to 1.16]* | 1.117 [0.89 to 1.09]* | 1.059 [0.96 to 1.06] |
| Daytime share | 0.899 [0.91 to 1.05]* | 0.986 [0.99 to 1.02]* | 0.954 [0.97 to 1.06]* |
| Static-source share (type 2 or 3) | 0.885 [0.83 to 1.40] | 0.904 [0.87 to 1.22] | 0.869 [0.90 to 1.12]* |

**Findings.**
1. **Counts: no step beyond normal variation [verified].** Rows, type 0 rows and kept rows relative to S-NPP are inside the range of the other years at both boundaries. The raw MODIS count rise in 2023 (about 1.22 to 1.25 times) is matched by S-NPP (1.27 times), so it is year-to-year fire variability, not a MODIS processing step.
2. **2018 boundary: the static-source share rises [verified; cause is a hypothesis].** The share of type 2 or 3 detections is about 1.5 times higher after 2018-01-01 (Terra 1.57, Aqua 1.50), above anything at the other 1 January boundaries, while S-NPP shows no such step (1.05). Type 0 and kept counts do not move, so the added detections are static-source rows. **Hypothesis:** the `6.03` processing flags more static sources. It does not affect the type 0 filter.
3. **2023 boundary: some distribution measures move [verified; cause open].** The low-confidence share rises (Terra 1.13, Aqua 1.09, outside the range of the other years) while S-NPP's falls; mean FRP rises more in MODIS (Terra 1.29, Aqua 1.12) than in S-NPP (1.06). The daytime share falls in both MODIS and S-NPP, so that one is common to both instruments. The cause of the MODIS-specific moves is not determined **[OPEN]**.
4. **Confidence and day/night at 2018: no step.**

**Method impact (logged; no change proposed).**
- The harmonization unit is the cell-day from type 0, confidence-filtered rows. Their count relative to S-NPP shows no step at either boundary, so no correction by `version` is needed on this evidence.
- The extra low-confidence rows after 2023 are removed by the confidence filter (MODIS 30 or more).
- FRP is not used for the harmonization (only for the informational `frp_sum_mw`); the 2023 FRP shift is recorded as a limitation.
- The static-source mask was built from standard data of all sensors from 2012 to 2025 (approved by the Lead); the 2018 rise in MODIS static share is a reason to keep reporting the mask's hold-out score per sensor, not a reason to change it.
- **Whether to flag or adjust by `version` is the Lead's decision. Nothing was dropped.**

### Gridding (T-006) **[VERIFIED 2026-11-14]**

`python pipeline/gridding.py build` turns the normalized detections into two local products under `data/products/` (not committed): `cells.parquet` and `cell_month_witness.parquet`, in the schema of `DATA_CONTRACT.md` v0.1.0. Grids (D-009, locked at G1): analysis cells 0.5 degrees, fine cells 0.05 degrees; a fine cell belongs to the analysis cell that holds its centre.

- **Kept detections:** confidence MODIS 30 or more and VIIRS n or h; `type = 0` for SP rows (NRT rows have no `type`); the approved static-source mask applied to every row, as in the D-009 test (**approved by the Lead 2026-11-14**: one rule across all years avoids an artificial step at the SP to NRT boundary in 2026, and the measured effect is small, a Spearman difference of 0.006 to 0.009); negative FRP counted as null in `frp_sum_mw`. The record starts in 2002-07. Result: 485,158,861 kept detections, 220,647,772 fine-cell-days.
- **Cell-day:** a distinct `(witness, daynight, fine cell, UTC date)`. `daynight` rows are `D`, `N` and `ALL`, where `ALL` is D + N as the contract says (the D-009 test counted the union of day and night fine-cell-days instead; the difference is small).
- **Rows:** 146,625,501 rows (48,875,167 per `daynight` value) over 56,243 active cells and 869 witness-months, written for every month a witness operated, with `cell_days = 0` where nothing was detected (77.5% of the `ALL` rows). The Parquet file is 180 MB. Witness ranges: Aqua and Terra from 2002-07, S-NPP from 2012-01, NOAA-20 from 2018-04, all to 2026-11. `data_level` of the `ALL` rows: 48,087,765 SP and 787,402 NRT.
- **Cells:** 56,243 cells (contract check passes). Country is the one with most kept detections in the cell (zip rows only); 926 cells have none (all their kept detections come from the 2026 API data, which carries no country). Continents: EU 13,593, AS 12,127, NA 10,036, AF 8,786, SA 6,373, OC 3,611, AN 791. Fire region from T-004: 1,234 cells are `UNASSIGNED`. **`stratum_id` is a provisional rule (fire region and country), approved by the Lead 2026-11-14 as provisional.** If T-011 redefines it, T-011 documents the final rule and regenerates `cells.parquet`.
- **`days_available` and the FIRMS `missing_data` list.** A listed day is subtracted only if the witness has no detection that day. For Aqua (26 days), Terra (31) and NOAA-20 (6) the list matches the days with no detections exactly, and no other day without detections exists. For S-NPP the list marks all 31 days of May 2026 as missing, yet the data has 20,634 to 36,564 detections on each of them. Those days count as available (evidence of data); the other 49 listed S-NPP days have no detections and are subtracted. **Approved by the Lead 2026-11-14:** a listed day counts as available when the witness has detections that day, so May 2026 S-NPP is kept (dropping it would lose 687,805 real detections). The discrepancy between the FIRMS list and the data is recorded here.
- **Validation (verified):** `python pipeline/gridding.py validate` finds no contract problem (schema and types, enumerations, no nulls, no duplicate keys, `ALL` = D + N for `cell_days` and `detections`, `days_available` between 1 and `days_in_month`, `cell_days` at most 100 per available day, no row before a witness operated or before 2002-07, every `cell_id` in `cells.parquet`). An independent count from the interim detections equals the product: 485,158,861 detections and 220,647,772 fine-cell-days. The first build differed by 687,805 detections; the check found the S-NPP May 2026 issue above.

**G1 evidence: the raw combined record shows the sensor jumps.** Global raw cell-days per month: VIIRS arrives in January 2012 and NOAA-20 in April 2018.

| Month | Raw combined cell-days (all witnesses, D + N) | By witness |
|---|---|---|
| 2011-11 | 170,715 | Aqua: 113,865, Terra: 56,850 |
| 2011-12 | 251,898 | Aqua: 167,238, Terra: 84,660 |
| 2012-01 | 464,950 | Aqua: 152,025, Terra: 83,193, S-NPP: 229,732 |
| 2012-02 | 671,082 | Aqua: 106,989, Terra: 54,459, S-NPP: 509,634 |
| 2012-03 | 804,225 | Aqua: 159,957, Terra: 62,808, S-NPP: 581,460 |
| 2018-01 | 872,763 | Aqua: 156,558, Terra: 82,195, S-NPP: 634,010 |
| 2018-02 | 589,828 | Aqua: 91,453, Terra: 48,212, S-NPP: 450,163 |
| 2018-03 | 710,489 | Aqua: 111,259, Terra: 51,528, S-NPP: 547,702 |
| 2018-04 | 1,067,790 | Aqua: 102,513, Terra: 60,446, S-NPP: 448,261, NOAA-20: 456,570 |
| 2018-05 | 828,692 | Aqua: 73,850, Terra: 49,365, S-NPP: 349,816, NOAA-20: 355,661 |

**G1 evidence: D-009 grid-size comparison** (Aqua MODIS vs S-NPP VIIRS, SP only, 2012-01 to 2016-12; type 0, confidence and the approved static mask; D and N combined; aggregate statistics only, no validation case looked at; `pipeline/grid_test.py`):

| Fine | Analysis | Active cells | Cell-months with activity | Spearman | Ratio Aqua/S-NPP median (IQR) | Both 0 / one 0 / both > 0 | Aqua ≥ 5 cell-days | Time | Output |
|---|---|---|---|---|---|---|---|---|---|
| 0.05° | 0.25° | 154,835 | 2,698,461 | 0.672 | 0.33 (0.20–0.50) | 71.0% / 15.8% / 13.3% | 4.5% | 6.0s | 4.7 MB |
| 0.05° | 0.5° | 48,185 | 1,170,257 | 0.739 | 0.29 (0.17–0.48) | 59.5% / 19.5% / 21.0% | 8.8% | 4.4s | 2.2 MB |
| 0.1° | 0.25° | 153,788 | 2,669,062 | 0.664 | 0.33 (0.21–0.50) | 71.1% / 15.7% / 13.2% | 4.1% | 5.1s | 4.5 MB |
| 0.1° | 0.5° | 48,185 | 1,170,257 | 0.733 | 0.30 (0.18–0.50) | 59.5% / 19.5% / 21.0% | 8.4% | 4.5s | 2.1 MB |

Definitions: *Active cells* are analysis cells with any activity by either satellite in the 60 months. *Both 0 / one 0 / both > 0* are shares of all active-cell x 60-month cell-months (S-NPP starts 2012-01-20). The ratio is Aqua / S-NPP where both are above 0. *Aqua ≥ 5* is the share of those cell-months with at least 5 Aqua cell-days. Time is the cell-month step; the build of the fine-cell-days took 5 to 7 seconds per fine grid.

**Decision (Lead, 2026-11-14): D-009 locked at analysis 0.5 degrees and fine 0.05 degrees.** 0.05 / 0.5 has the highest Spearman (0.739), the most cell-months with both satellites active (21.0%) and the most with Aqua ≥ 5 (8.8%), and it matches the approved static-mask grid. Noted for later steps: Aqua night activity is thin (Spearman 0.41 to 0.51), so calibration will lean on pooling for night strata; only about 9% of cell-months reach Aqua ≥ 5, so cell-level verdicts will often be `CANNOT_DETERMINE` and country and continent are the main verdict levels.

### Calibration (T-011) **[VERIFIED 2026-11-14 unless labelled]**

`python pipeline/calibration.py` writes `data/products/calibration.parquet` (local, not committed; 96,384 rows = 4,016 strata x 2 witnesses x 3 day/night values x 4 seasons; contract check passes) and regenerates `cells.parquet` with the final `stratum_id`. The full run with 1,000 bootstrap replicates takes about 80 seconds.

- **Ratio:** sum of Aqua `cell_days` / sum of witness `cell_days` per stratum x day/night x season. It is the multiplier that converts the witness to the Aqua-equivalent scale. `D` and `N` have their own ratios; `ALL` is fitted on the `ALL` cell-days and is informational only (the combination converts `D` and `N`).
- **Fit periods:** S-NPP 2012-01 to 2016-12, NOAA-20 2018-04 to 2021-12. The held-out years (2017 to 2021 for S-NPP) are never read. S-NPP uses 58 of 60 months (2012-01 and 2012-03 are partial), NOAA-20 all 45.
- **Strata:** a 2.5 degree block inside a GFED fire region, `{region}_b{row}_{col}` (row from the south, column from -180, in 2.5 degree steps). 4,016 strata. This replaces the provisional T-006 rule.
- **Partial pooling:** the log-ratio of a stratum is shrunk toward its fire region, and the region toward the global ratio. The weight on the lower level is tau^2 / (tau^2 + v): v is the monthly block-bootstrap variance of its log-ratio, never below the counting-noise floor 1/sum(Aqua) + 1/sum(witness), and tau^2 the spread between units (DerSimonian-Laird, from the data). **A stratum keeps a local weight only with at least 3 overlap months, and only if no single overlap month holds more than half of its overlap cell-days (Aqua or witness; D-025)**; otherwise it takes its region's estimate (or the global one for `UNASSIGNED`). `pooling_level` is the level with the largest weight in the final estimate; a stratum that takes its region's estimate is labelled `GLOBAL` when that region itself leans on the global ratio.
- **Uncertainty:** 1,000 bootstrap replicates resample whole fit months within each season (fixed seed); the whole procedure, including tau^2, is repeated per replicate; `ratio_sd` is the standard deviation of the final ratio. `n_overlap_months` counts the fit months in which the stratum had both Aqua and witness cell-days.
- **A problem found and fixed while building it:** for a stratum active in only one or two months, the bootstrap variance is about 0, which let such strata keep a very noisy ratio (up to 4.9) and broke tau^2 for their whole group. The counting-noise floor fixes it; a test covers it.

**Approved by the Lead 2026-11-14:** the 2.5 degree block inside a fire region as the local stratum; precision-weight shrinkage with DerSimonian-Laird tau^2 and the counting-noise floor; `pooling_level` by the largest weight (ties to the more local level); complete months only; seasons DJF / MAM / JJA / SON; the final `stratum_id` rule and the regenerated `cells.parquet`. **Changes asked by the Lead (done):** at least 3 overlap months for a local weight; 1,000 bootstrap replicates; the sanity tables below; the persistent night-source mask and the one-month burst rule (D-025, below).

**The products below are built with the D-025 mask** (the approved T-005 mask plus persistent night sources) and the one-month burst rule. Figures for the T-005 mask alone appear as "before" where they matter.

- **Regenerated products** (`gridding.py build`, `validate`, then `calibration.py`; all local, not committed):
  - The independent recount matches the product: 483,456,394 kept detections and 219,583,156 fine-cell-days.
  - `cell_month_witness.parquet`: 146,612,466 rows, 56,238 cells, 869 witness-months; it validates against the contract.
  - `calibration.parquet`: 96,384 rows (4,016 strata); it validates against the contract. The run takes 80 seconds.
  - `cells.parquet` is regenerated with the final `stratum_id`.
- **One-month burst rule** (D-025): a stratum x witness x day/night x season whose single largest overlap month holds more than 50% of its overlap cell-days (Aqua or witness) takes its region's estimate.
  - It moves 974 S-NPP day, 1,100 S-NPP night, 1,121 NOAA-20 day and 1,000 NOAA-20 night rows away from `LOCAL`: 4,195 rows in all (`burst_rows` in `calibration_report.json`).
  - That is far more than the volcano cases, because in many fire regions one month dominates a season.

**Global ratios** (Aqua-equivalent multiplier; the witness sees about 1 / ratio times the Aqua cell-days). They differ from the T-005-mask run by at most 0.002.

| Witness | Day/night | DJF | MAM | JJA | SON |
|---|---|---|---|---|---|
| S-NPP | D | 0.281 | 0.273 | 0.350 | 0.279 |
| S-NPP | N | 0.051 | 0.041 | 0.071 | 0.075 |
| S-NPP | ALL (informational) | 0.238 | 0.230 | 0.301 | 0.242 |
| NOAA-20 | D | 0.277 | 0.263 | 0.331 | 0.272 |
| NOAA-20 | N | 0.046 | 0.041 | 0.076 | 0.075 |
| NOAA-20 | ALL (informational) | 0.232 | 0.217 | 0.286 | 0.236 |

By day a VIIRS witness records about 3 to 4 times the Aqua cell-days; by night about 13 to 25 times. S-NPP and NOAA-20 agree closely.

**Between-unit variance tau^2:**

| Witness | Day/night | tau^2 local (DJF / MAM / JJA / SON) | tau^2 region (DJF / MAM / JJA / SON) |
|---|---|---|---|
| S-NPP | D | 0.08 / 0.09 / 0.06 / 0.08 | 0.05 / 0.08 / 0.16 / 0.12 |
| S-NPP | N | 0.38 / 0.28 / 0.28 / 0.21 | 0.40 / 0.15 / 0.16 / 0.46 |
| NOAA-20 | D | 0.08 / 0.10 / 0.09 / 0.10 | 0.06 / 0.08 / 0.23 / 0.15 |
| NOAA-20 | N | 0.37 / 0.25 / 0.31 / 0.26 | 0.48 / 0.16 / 0.29 / 0.57 |

**Pooling levels** (rows per witness and day/night; each row is a stratum x season). Before (T-005 mask, no burst rule) the `LOCAL` counts were 5,833, 3,191, 5,413 and 2,700.

| Witness | Day/night | LOCAL | REGION | GLOBAL |
|---|---|---|---|---|
| S-NPP | D | 5,403 (33.6%) | 7,239 (45.1%) | 3,422 (21.3%) |
| S-NPP | N | 2,286 (14.2%) | 10,352 (64.4%) | 3,426 (21.3%) |
| NOAA-20 | D | 4,887 (30.4%) | 8,263 (51.4%) | 2,914 (18.1%) |
| NOAA-20 | N | 1,846 (11.5%) | 10,404 (64.8%) | 3,814 (23.7%) |

**Sanity check: the `LOCAL` ratios.** Every `LOCAL` row has at least 3 overlap months and no month holding more than half of its cell-days. An extreme row is a `LOCAL` ratio more than 3 times, or less than a third of, the global ratio of the same witness, day/night and season.

| Witness | Day/night | LOCAL rows | 5th percentile | Median | 95th percentile | Extreme rows before / after (low / high after) |
|---|---|---|---|---|---|---|
| S-NPP | D | 5,403 | 0.132 | 0.278 | 0.505 | 71 / 72 (71 / 1) |
| S-NPP | N | 2,286 | 0.018 | 0.060 | 0.178 | 411 / 259 (142 / 117) |
| NOAA-20 | D | 4,887 | 0.124 | 0.266 | 0.508 | 84 / 78 (78 / 0) |
| NOAA-20 | N | 1,846 | 0.017 | 0.058 | 0.179 | 411 / 238 (157 / 81) |

Extreme rows fall from **977 in 560 strata** (T-005 mask) to **647 in 391 strata** (497 night, 150 day).

The 10 most extreme `LOCAL` ratios (largest distance from the global ratio, in log terms):

| Stratum | Fire region | Witness | Day/night | Season | Ratio | Global ratio | Ratio / global | `ratio_sd` | Overlap months |
|---|---|---|---|---|---|---|---|---|---|
| `SEAS_b044_110` | SEAS | NOAA-20 | N | DJF | 0.005 | 0.046 | 0.10 | 0.001 | 7 |
| `SEAS_b043_103` | SEAS | S-NPP | N | DJF | 0.005 | 0.051 | 0.11 | 0.001 | 6 |
| `SHAF_b029_081` | SHAF | NOAA-20 | N | JJA | 0.008 | 0.076 | 0.11 | 0.002 | 5 |
| `EURO_b061_063` | EURO | NOAA-20 | N | JJA | 0.656 | 0.076 | 8.62 | 0.147 | 3 |
| `SHAF_b030_078` | SHAF | S-NPP | N | JJA | 0.008 | 0.071 | 0.12 | 0.001 | 12 |
| `SHAF_b030_083` | SHAF | NOAA-20 | N | JJA | 0.009 | 0.076 | 0.12 | 0.002 | 10 |
| `SEAS_b044_111` | SEAS | NOAA-20 | N | DJF | 0.006 | 0.046 | 0.12 | 0.001 | 5 |
| `SEAS_b049_101` | SEAS | NOAA-20 | N | SON | 0.009 | 0.075 | 0.12 | 0.002 | 4 |
| `NHAF_b040_069` | NHAF | NOAA-20 | N | DJF | 0.006 | 0.046 | 0.12 | 0.001 | 9 |
| `SEAS_b047_102` | SEAS | NOAA-20 | N | SON | 0.009 | 0.075 | 0.12 | 0.002 | 4 |

- **Nine** are peak fire seasons in savanna and agricultural fire regions (hypothesis below).
- **The tenth** is Fagradalsfjall in summer (below).
- **Gone since the mask change:** the T-005-mask top 10 held three flare rows (`TENA_b047_032`, and `TENA_b048_030` twice) and two volcano rows (`EURO_b061_063` MAM, `EQAS_b028_139` MAM). None of them is left.

#### Extreme ratios: causes (T-011 review) **[VERIFIED 2026-11-14 unless labelled]**

`python pipeline/night_sources.py` diagnoses every extreme `LOCAL` row against a control sample of 600 ordinary `LOCAL` rows. On the T-005 mask there were **977 extreme rows in 560 strata** (822 night, 155 day; 603 low, 374 high).

- **Persistent night sources (flares, industrial heat).** The low night ratios with the largest volumes include the Permian (`TENA_b048_030`), the Bakken (`TENA_b055_030`) and the Eagle Ford (`TENA_b047_032`). Persistence alone does not separate them from fires, because many fire fields burn every year; the D-025 rule does. Its cells cluster in oil, gas and industrial areas: the Permian, Bakken, Eagle Ford, South African Highveld, Basra and Khuzestan, Vaca Muerta, Shanxi, Indian coal fields, Ghawar, Kirkuk and West Siberia **[location of the boxes VERIFIED; their identification as flaring or industrial areas is an ASSUMPTION from known geography]**.
- **Volcanoes** (volcano coordinates are **ASSUMPTIONS** from public catalogues, not read from a dataset):
  - `EQAS_b028_139` (Yasur, Tanna): 95% of its S-NPP SP detections are FIRMS type 1. Its S-NPP night ratios were 7 to 9 times global; now all four seasons take the region's estimate.
  - `EURO_b061_063` (Fagradalsfjall, Iceland): FIRMS gives no type 1. Its NOAA-20 night ratios were 8 to 11 times global, and 56% of the spring NOAA-20 night cell-days fall in one month (the 2021 eruption).
  - 12 extreme rows had more than 10% type 1 detections, and Fagradalsfjall added 2. Holuhraun (2014 to 2015) was not among the extreme rows.
- **Classification of the 977 rows** (T-005 mask):

  | Cause | Rows |
  |---|---|
  | Stratum contains a cell flagged by the first night-source rule (before the day/night condition) | 459 |
  | Volcano: FIRMS type 1 above 10% | 12 |
  | Volcano: Fagradalsfjall | 2 |
  | Neither | 504 |

  "Contains" only means the cell is there; the re-run is the evidence.
- **The rest: seasonal fire regions.** Most remaining low night ratios fall in peak fire seasons: SE Asia (`SEAS`) in DJF and SON, southern Africa (`SHAF`) in JJA, and northern Africa (`NHAF`) in DJF.
  - The countries are an **ASSUMPTION** from the block coordinates: Myanmar, Thailand and Laos; Zambia, Angola and Mozambique; the Sahel.
  - Their static share and persistence are low, like the control rows.
  - **Hypothesis, accepted by the Lead as such (2026-11-14):** VIIRS (375 m) detects many small night fires that MODIS (1 km) misses, more so where small agricultural and savanna fires dominate. These would then be real regional differences. **For T-012 and validation test E1 (by region) to confirm.**
  - The mask is not tightened for them.

#### Persistent night-source mask (D-025) **[APPROVED by the Lead 2026-11-14]**

`python pipeline/night_mask.py` builds the mask. A 0.05 degree fine cell is a persistent night source if its kept VIIRS night detections (S-NPP or NOAA-20; SP, type 0, confidence n or h, not already in the T-005 mask) meet all four conditions:
1. they light it on at least 1% of nights;
2. in at least 10 of the 12 calendar months;
3. with at least half of those nights outside its 3 busiest calendar months;
4. and its kept VIIRS day detections fall on at most 0.5 times as many days as its nights (`MAX_DAY_NIGHT`).

The cells are added to the T-005 mask, which applies to every witness, both day and night, and all years. `gridding.py` uses the combined mask (`data/interim/qa/static_mask_plus_night_sources.parquet`) by default, and `--mask` selects another mask for comparisons.

**Why condition 4: the Bolivia cluster (Lead review 3).** The box 20 to 15 S, 62.5 to 60 W (the Chiquitano dry forest) held 220 cells flagged by conditions 1 to 3. Their kept VIIRS SP detections, 2012 to 2025:

| Year | 2012 | 2013 | 2014 | 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Type 0 (day and night) | 2,171 | 2,688 | 4,084 | 7,447 | 10,402 | 10,638 | 18,456 | 20,639 | 15,363 | 18,462 | 22,254 | 17,775 | 15,463 | 6,609 |

| Month | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Type 0 (all years) | 10,240 | 5,765 | 6,383 | 8,166 | 11,048 | 16,147 | 22,799 | 20,404 | 20,561 | 22,925 | 17,930 | 11,833 |

- **Jul to Oct (fire season):** 49.8% of type 0 detections fall in these 4 months; the other 8 months hold 50.2%.
- **FIRMS type 2 or 3:** 0.5% of the SP detections. In their flagged cells, the Permian has 10.4%, the Bakken 15.8% and the Eagle Ford 15.0%.

**Finding: seasonal vegetation fires, not a year-round source.** There is a strong Jul to Oct peak, the count grows over the decade, and there are almost no static labels. The cells passed conditions 1 to 3 because the area burns in every month.

- **The off-season share does not separate them from flares.** For the cells that meet conditions 1 and 2, the median is 0.47 in Bolivia, 0.55 in the Permian, 0.45 in the Bakken and 0.56 in the Eagle Ford. Raising the threshold to 0.6 would still keep 23 Bolivian cells, but would drop 147 of 238 Permian cells.
- **The day/night balance does.** A flare burns around the clock and is hard to see by day; a vegetation fire burns mostly in the afternoon. For the flagged cells, the median ratio of day-lit to night-lit days is 0.72 in Bolivia, against 0.07 in the Permian, 0.11 in the Bakken and 0.10 in the Eagle Ford.

**Effect of condition 4** (cells flagged on 2012 to 2025; the names are **ASSUMPTIONS** from geography):

| Box | Cells, conditions 1 to 3 | Cells, all four |
|---|---|---|
| Permian (30 to 32.5 N, 105 to 102.5 W) | 238 | 236 |
| Bakken (47.5 to 50 N, 105 to 102.5 W) | 74 | 73 |
| Eagle Ford (27.5 to 30 N, 100 to 97.5 W) | 103 | 103 |
| Chiquitano, Bolivia (20 to 15 S, 62.5 to 60 W) | 220 | 8 |
| All | 4,768 | 3,458 |

The 8 Bolivian cells still flagged have no type 2 or 3 detections and also peak in Jul to Nov (4,712 type 0 detections over 14 years). Their cause is **OPEN**.

**Held-out check:** the rule is built on 2012 to 2023 and applied to the 2024 and 2025 SP detections that the T-005 mask does not remove. The type 0 column is an upper bound on vegetation fires lost, because unlabelled flares are type 0.

| Rows | Static (type 2 or 3) removed: conditions 1 to 3 / all four | Type 0 removed: conditions 1 to 3 / all four |
|---|---|---|
| VIIRS night | 34.3% / 28.5% | 1.26% / 0.94% |
| VIIRS day | 21.5% / 15.4% | 0.14% / 0.06% |
| Aqua day | 3.7% / 1.9% | 0.11% / 0.04% |
| Aqua night | 28.7% / 9.6% | 0.70% / 0.27% |

Built on 2012 to 2023, the rule flags 2,985 cells (4,123 without condition 4); built on 2012 to 2025, it flags 3,458. The combined mask has 14,387 cells (T-005 mask: 10,929).

**Flare strata after the re-run.** Extreme `LOCAL` night rows in `TENA_b047_032`, `TENA_b048_030` and `TENA_b055_030`: 11 before, 2 after.
- `TENA_b047_032` (Eagle Ford) has none left.
- `TENA_b048_030` (Permian) has NOAA-20 DJF at 0.14 of global. Its other night seasons take the region's estimate, except NOAA-20 JJA (`LOCAL`, 0.43).
- `TENA_b055_030` (Bakken) has S-NPP JJA at 0.15 of global.
- **Hypothesis:** the rule does not catch flares lit on fewer than 1% of nights or in fewer than 10 months.

**Fagradalsfjall after the burst rule.** NOAA-20 MAM night now takes the region's estimate. NOAA-20 JJA stays `LOCAL` at 8.6 times global, because the 2021 eruption lasted from March to September and no single summer month holds more than half of the cell-days. **[Accepted as a limitation by the Lead, 2026-11-14.]**
- **Option, not applied:** run the same test on one season-year instead of one month.
- It would catch Fagradalsfjall, because all its NOAA-20 night cell-days fall in 2021.
- It would also move 3,345 of the 14,422 day and night `LOCAL` rows.

**Tests** (`pipeline/tests/test_night_mask.py`, `pipeline/tests/test_calibration.py`):
- **Planted flare:** three flares lit every night in one synthetic stratum make its S-NPP night ratio `LOCAL` and below a third of global in all four seasons. The rule finds exactly those three cells. With them masked, the ratio is within a factor of 3 of global.
- **Seasonal fire field:**
  - A field lit every night and day from July to October is never flagged.
  - A field lit year-round at night but busy by day passes conditions 1 to 3 and is dropped by condition 4.
  - A flare lit at night and rarely by day is flagged.
- **One-month burst:** a stratum with 4 overlap months, one holding 4/7 of the cell-days, is not `LOCAL`. A stratum with 4 equal months stays `LOCAL`.
- **Breaking the rule on purpose makes the tests fail.** Checked by requiring 13 months, dropping condition 4, and dropping the burst test.

**Accepted limitations (Lead, 2026-11-14):** the 8 Bolivian cells and Fagradalsfjall NOAA-20 JJA night, because a general fix would discard far more good data. They are in `docs/RISKS_AND_LIMITATIONS.md` (S12 to S15). The T-005-mask products are kept locally in `C:\IgnisLine-data\products_T006_T011v2\`; `--mask data/interim/qa/static_mask_fine0.05_share0.5_min10.parquet` rebuilds them.

**Not done here:** the holdout evaluation and the Aqua drift diagnostic (T-012), the combination (T-013) and any validation test.

## 2. NASA FIRMS area API: **2026 data**

- Documentation: https://firms.modaps.eosdis.nasa.gov/api/area/
- Pattern **[VERIFIED]:**
  - `/api/area/csv/{MAP_KEY}/{SOURCE}/{west,south,east,north | world}/{DAY_RANGE}/{YYYY-MM-DD}`
  - The response covers DATE through DATE + DAY_RANGE − 1.
- `DAY_RANGE` is 1–5. The limit is **5,000 transactions per 10 minutes** per MAP_KEY; large requests can count as several transactions.
- Sources: `MODIS_NRT`, `MODIS_SP`, `VIIRS_SNPP_NRT`, `VIIRS_SNPP_SP`, `VIIRS_NOAA20_NRT`, `VIIRS_NOAA20_SP`, `VIIRS_NOAA21_NRT`, `VIIRS_NOAA21_SP`, `LANDSAT_NRT` (US/Canada only).
- Requires a free **MAP_KEY** (https://firms.modaps.eosdis.nasa.gov/api/map_key/). Store it in `.env` as `FIRMS_MAP_KEY`. **Never commit it.**
- **2026 volume [ESTIMATE]:** about 64 requests per source for Jan–Nov, which is small relative to the limit.
- The `country` endpoint is listed as **currently unavailable [VERIFIED 2026-11-14]**. Do not depend on it.
- Other endpoints: `data_availability` (date coverage per source) and `missing_data` (dates with missing satellite data). Both are used for observation-effort tracking.

## 3. Product levels

| Level | Latency | Notes |
|---|---|---|
| URT / RT | Minutes to ~1 h | Direct broadcast, limited regions. Not used |
| NRT | ~1–3 h | **No `type` field**; NRT day/night uses the orbit direction; larger geolocation errors after manoeuvres. Used for recent 2026 months, flagged `PROVISIONAL_NRT` |
| Standard (SP / archive) | 2–3 month lag | Science quality; `type` included; day/night from solar zenith angle > 85°. Used wherever available |

Source: FIRMS FAQ **[VERIFIED 2026-11-14]**: https://www.earthdata.nasa.gov/data/tools/firms/faq

## 4. Satellite record dates **[VERIFIED 2026-11-14, FIRMS FAQ]**

| Satellite | Start | End |
|---|---|---|
| Terra MODIS | 1 Nov 2000 | Still delivering detections on 2026-11-14 **[VERIFIED 2026-11-14, T-008]**. Mission end: ending around early 2027 **[ASSUMPTION: NASA sources disagree]** |
| Aqua MODIS | Jul 2002 | Still delivering detections on 2026-11-14 **[VERIFIED 2026-11-14, T-008]**. Mission end: between ~Nov 2026 and ~Sep 2027 **[OPEN: cannot be determined from FIRMS data]** |
| S-NPP VIIRS | 20 Jan 2012 | **2 Nov 2026, 15:40 UTC** |
| NOAA-20 VIIRS | 1 Apr 2018 | Ongoing |
| NOAA-21 VIIRS | 17 Jan 2024 | Ongoing (not used in the MVP) |

### Aqua/Terra 2026 availability (T-008) **[VERIFIED 2026-11-14]**

Evidence: the 2026 MODIS files pulled in T-002 (world, 2026-01-01 to 2026-11-14, `MODIS_SP` then `MODIS_NRT`) and the FIRMS `missing_data` response saved the same day. Reproduce with `python -I pipeline/check_modis_availability.py`.

- `data_availability` lists MODIS as one source (`MODIS_SP` to 2026-08-31, `MODIS_NRT` 2026-09-01 to 2026-11-14). It cannot separate Aqua from Terra, so the `satellite` column of the detections is used.

| Satellite | First detection | Last detection | Days with detections | Days without | Days without that FIRMS lists as missing |
|---|---|---|---|---|---|
| Aqua | 2026-01-01 | 2026-11-14 | 318 of 318 | none | none |
| Terra | 2026-01-01 | 2026-11-14 | 317 of 318 | 2026-01-12 | 2026-01-12 |

- Both satellites were still delivering on the last day pulled. Terra's single day without detections matches an entry in FIRMS `missing_data`, so it is a documented outage and not a quiet day. Aqua has none.
- Per month, Aqua has about 1.7 to 3 times as many detection rows as Terra in 2026 (Jan 203,892 vs 73,894; Aug 381,385 vs 164,293). This is an observation only; the cause is not investigated here **[OPEN]**.
- **Cannot determine from FIRMS data:** when either mission will end. Those dates stay marked as above.
- Caveat: the `missing_data` table is read from the endpoint that the FIRMS missing-data web page loads (`?action=fetch_data`). It is not a documented API and may change.

## 5. Additional NASA products considered (not used in the MVP)

| Product | Why considered | Why not used now |
|---|---|---|
| VNP64A1 / MCD64A1 burned area | Independent corroboration of anomalies | In FIRMS it is a map layer only; downloads are HDF via LP DAAC; ~5-month lag; ~72% omission errors (Giglio et al. 2025) |
| MOD14A1 / MYD14A1, VNP14A1 / VJ114A1 daily 1 km fire masks | Per-cell clear-sky observation counts (cloud class in the fire mask) | Global HDF tiles; too heavy for 36 hours |
| VNP14 / VJ114 750 m active fire | MODIS-C6-heritage algorithm built for continuity | Not in FIRMS; granule-level data |
| MODIS CMG fire (MOD14CMQ etc.) | Gridded, observation-normalized | No VIIRS equivalent found, so the sensors couldn't be treated symmetrically |

## 6. Non-NASA data

| Data | Use | Source / licence |
|---|---|---|
| Natural Earth admin-0 countries (1:50m) | Map boundaries; country attributes | https://www.naturalearthdata.com/ (public domain) |
| GFED basis regions (14 fire regions) | Pooling parent in calibration | GFED4s basis-regions grid, http://www.geo.vu.nl/~gwerf/GFED/GFED4/ (free with citation). **Access verified 2026-11-14 (T-004)**; no fallback needed. See the T-004 section below |

FIRMS country names (e.g. `Democratic_Republic_of_the_Congo`, `Russian_Federation`) are mapped to ISO3 codes and continents in `pipeline/country_map.csv` (task T-009).

### Country name mapping (T-009) **[VERIFIED 2026-11-14]**

- **Coverage:** all 238 distinct country names in the normalized detections (T-003) are mapped (100%). The check `python pipeline/country_mapping.py check` fails if a name is missing from the table or the table has a name the data lacks.
- **Source of the codes:** Natural Earth 1:50m admin-0 countries, version 5.1.1 (`ne_50m_admin_0_countries.zip`, 799,734 bytes, SHA-256 `5fed433373581fa648920435f937d95f2d3c0200e067409c6478dcdf1b853139`, downloaded 2026-11-14; only the attribute table is read, the file is not committed). 219 names matched by name; 19 were resolved by hand, each with a note in the table.
- **Continent codes:** `AF`, `AN`, `AS`, `EU`, `NA`, `OC`, `SA`. `AN` is included because the data has detections in Antarctica. Continents follow Natural Earth (so Russia is `EU`, Turkey, Cyprus, Georgia and Kazakhstan are `AS`). Where Natural Earth says "Seven seas (open ocean)", the UN M49 region is used.
- **Approved by the Lead 2026-11-14:** Kosovo has no ISO 3166-1 code, so the user-assigned `XKX` is used. `UMI` (United States Minor Outlying Islands) is `OC`. The continent policy is approved as written: continents follow Natural Earth (Russia `EU`; Turkey, Cyprus, Georgia, Armenia, Azerbaijan and Kazakhstan `AS`), "Seven seas" territories use the UN M49 region (ATF, MUS, SHN and SYC `AF`; HMD and UMI `OC`; MDV `AS`), and Antarctica `AN` is included because it has data.
- Territories keep their own code (Greenland `GRL`, Hong Kong `HKG`, Norfolk Island `NFK`); they are not merged into their sovereign state. Codes in common use are used for disputed territories (Palestine `PSE`, Taiwan `TWN`); this is not a political statement.

### Fire-region mask (T-004) **[VERIFIED 2026-11-14]**

The pooling parent in calibration is the GFED basis region (14 regions: BONA, TENA, CEAM, NHSA, SHSA, EURO, MIDE, NHAF, SHAF, BOAS, CEAS, SEAS, EQAS, AUST). The lookup is `pipeline/fire_regions.py`; every analysis cell gets a `fire_region`.

- **Source:** the basis-regions grid (`ancill/basis_regions`, 720 x 1440 cells of 0.25 degrees, classes 0 = ocean and 1 to 14) inside `GFED4.1s_2001.hdf5` (30,765,559 bytes, SHA-256 `1b684bf0b348e92a5d63ea660564f01439f69c4eb88eacd46280237d51ce5815`), downloaded on 2026-11-14 over plain HTTP from http://www.geo.vu.nl/~gwerf/GFED/GFED4/ (no login). The file and the derived grids stay local (`data/interim/fire_regions/`, not committed). Cite: van der Werf et al. (2017), Earth System Science Data 9, 697-720, https://essd.copernicus.org/articles/9/697/2017/. GFED data are free to use with citation; the licence terms were not independently verified beyond the project pages **[ASSUMPTION]**.
- **Cell rule (0.5 degree cells; works for any multiple of 0.25 degrees):** the most common GFED region among the cell's land 0.25 degree sub-cells (`GFED`). A tie takes the lowest region number; only 2 of the 259,200 cells are decided by a tie.
- **Fallback rules (approved by the Lead 2026-11-14):** a cell with no land sub-cell takes the region of the nearest land cell within 1.0 degree (`NEAREST_LAND`); otherwise it is `UNASSIGNED` and is pooled directly to the global ratio.
- **Cells:** 66,768 `GFED`, 14,305 `NEAREST_LAND`, 178,127 `UNASSIGNED` (mostly open ocean), 259,200 in total.
- **Detections** (all 582,050,574 normalized rows): 581,209,529 (99.856%) fall in a `GFED` cell, 300,184 (0.052%) in a `NEAREST_LAND` cell and 540,861 (0.093%) in an `UNASSIGNED` cell. The unassigned ones are on islands that the 0.25 degree grid does not mark as land: the United States (348,504; latitudes 18.9 to 51.9, which spans Hawaii and the Aleutians), Ecuador (68,078, Galapagos), rows without a country (44,699, the 2026 API data), Reunion (28,227), Antarctica (13,980), Fiji, Mauritius, Cape Verde, Portugal (Azores and Madeira), Tonga and others; 41 country names in all.

| Region | Name | Cells (GFED land) | Cells (nearest land) | Detections (GFED land) | Detections (nearest land) |
|---|---|---|---|---|---|
| BONA | Boreal North America | 8,962 | 2,187 | 14,790,548 | 152 |
| TENA | Temperate North America | 3,428 | 314 | 14,076,642 | 545 |
| CEAM | Central America | 1,270 | 862 | 13,730,358 | 15,833 |
| NHSA | Northern Hemisphere South America | 1,064 | 197 | 12,234,675 | 632 |
| SHSA | Southern Hemisphere South America | 5,474 | 754 | 63,428,485 | 1,323 |
| EURO | Europe | 5,839 | 1,929 | 5,133,612 | 82,705 |
| MIDE | Middle East | 4,752 | 648 | 17,394,576 | 119,503 |
| NHAF | Northern Hemisphere Africa | 5,014 | 366 | 119,803,461 | 5,017 |
| SHAF | Southern Hemisphere Africa | 3,515 | 597 | 172,334,780 | 10,193 |
| BOAS | Boreal Asia | 11,727 | 2,182 | 31,254,394 | 2,405 |
| CEAS | Central Asia | 8,259 | 876 | 28,490,644 | 21,718 |
| SEAS | Southeast Asia | 2,652 | 700 | 44,208,960 | 4,802 |
| EQAS | Equatorial Asia | 1,612 | 1,851 | 9,770,484 | 28,735 |
| AUST | Australia and New Zealand | 3,200 | 842 | 34,557,910 | 6,621 |

- **Approved by the Lead 2026-11-14:** (1) GFED4s basis regions as the source (public, no login, the same 14 regions as GFED5; the GFED5 grids are offered over SFTP with login details published by GFED, which were not used); (2) the fallback rules above, including the code `UNASSIGNED`, which pools to the global ratio (0.09% of detections); (3) `h5py` as a **one-off build tool only**: it reads the GFED HDF5 file once and writes a plain NumPy array. It is not a runtime dependency of the pipeline, the API or the app, so the stack does not change.

## 7. Update strategy

- Historical zips are downloaded once, and the snapshot date is recorded in `metadata.json`.
- 2026 is pulled through the API at build time. Months younger than the SP lag are marked provisional.
- A rebuild re-pulls 2026 and recomputes products. Calibration does **not** change unless `method_version` changes.

## 8. Acknowledgement and terms

FIRMS asks users to acknowledge FIRMS, LANCE and ESDIS when sharing data. Data are provided "as is". See the README.
