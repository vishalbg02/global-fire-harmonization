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

`python pipeline/gridding.py build` turns the normalized detections into two local products under `data/products/` (committed via Git LFS from T-014a on, D-027): `cells.parquet` and `cell_month_witness.parquet`, in the schema of `DATA_CONTRACT.md` v0.1.0. Grids (D-009, locked at G1): analysis cells 0.5 degrees, fine cells 0.05 degrees; a fine cell belongs to the analysis cell that holds its centre.

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

`python pipeline/calibration.py` writes `data/products/calibration.parquet` (committed via Git LFS from T-014a on, D-027; 96,384 rows = 4,016 strata x 2 witnesses x 3 day/night values x 4 seasons; contract check passes) and regenerates `cells.parquet` with the final `stratum_id`. The full run with 1,000 bootstrap replicates takes about 80 seconds.

- **Ratio:** sum of Aqua `cell_days` / sum of witness `cell_days` per stratum x day/night x season. It is the multiplier that converts the witness to the Aqua-equivalent scale. `D` and `N` have their own ratios; `ALL` is fitted on the `ALL` cell-days and is informational only (the combination converts `D` and `N`).
- **Fit periods:** S-NPP 2012-01 to 2016-12, NOAA-20 2018-04 to 2021-12. The held-out years (2017 to 2021 for S-NPP) are never read. S-NPP uses 58 of 60 months (2012-01 and 2012-03 are partial), NOAA-20 all 45.
- **Strata:** a 2.5 degree block inside a GFED fire region, `{region}_b{row}_{col}` (row from the south, column from -180, in 2.5 degree steps). 4,016 strata. This replaces the provisional T-006 rule.
- **Partial pooling:** the log-ratio of a stratum is shrunk toward its fire region, and the region toward the global ratio. The weight on the lower level is tau^2 / (tau^2 + v): v is the monthly block-bootstrap variance of its log-ratio, never below the counting-noise floor 1/sum(Aqua) + 1/sum(witness), and tau^2 the spread between units (DerSimonian-Laird, from the data). **A stratum keeps a local weight only with at least 3 overlap months, and only if no single overlap month holds more than half of its overlap cell-days (Aqua or witness; D-025)**; otherwise it takes its region's estimate (or the global one for `UNASSIGNED`). `pooling_level` is the level with the largest weight in the final estimate; a stratum that takes its region's estimate is labelled `GLOBAL` when that region itself leans on the global ratio.
- **Uncertainty:** 1,000 bootstrap replicates resample whole fit months within each season (fixed seed); the whole procedure, including tau^2, is repeated per replicate; `ratio_sd` is the standard deviation of the final ratio. `n_overlap_months` counts the fit months in which the stratum had both Aqua and witness cell-days.
- **A problem found and fixed while building it:** for a stratum active in only one or two months, the bootstrap variance is about 0, which let such strata keep a very noisy ratio (up to 4.9) and broke tau^2 for their whole group. The counting-noise floor fixes it; a test covers it.

**Approved by the Lead 2026-11-14:** the 2.5 degree block inside a fire region as the local stratum; precision-weight shrinkage with DerSimonian-Laird tau^2 and the counting-noise floor; `pooling_level` by the largest weight (ties to the more local level); complete months only; seasons DJF / MAM / JJA / SON; the final `stratum_id` rule and the regenerated `cells.parquet`. **Changes asked by the Lead (done):** at least 3 overlap months for a local weight; 1,000 bootstrap replicates; the sanity tables below; the persistent night-source mask and the one-month burst rule (D-025, below).

**The products below are built with the D-025 mask** (the approved T-005 mask plus persistent night sources) and the one-month burst rule. Figures for the T-005 mask alone appear as "before" where they matter.

- **Regenerated products** (`gridding.py build`, `validate`, then `calibration.py`; committed via Git LFS from T-014a on, D-027):
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

### Combining the witnesses and `harmonize_area()` (T-013) **[VERIFIED where marked]**

`pipeline/harmonize.py` holds the single implementation of the science for an area (`harmonize_area(cell_ids, months=None)`, `docs/DATA_CONTRACT.md` section 8). `python pipeline/harmonize.py phi` re-estimates `phi` and `kappa` and `python pipeline/harmonize.py` runs the diagnostic below (it writes `data/interim/qa/harmonize_report.json` and takes about 15 minutes). The records have the shape of `entity_month` (section 4). The baseline fields are `null` and the verdict is `CANNOT_DETERMINE`, as the contract requires without a baseline; T-014 adds them. `method_version` is `0.1.0-combined-no-baseline`.

**Approved by the Lead 2026-11-14 (PR #43):** day and night converted separately and added; the variance floor of one cell-day for a zero count; only complete witness-months count; a 90% normal interval with the lower bound at 0; no estimate for the 2002-07 to 2002-09 outage months; `aqua_cutoff` stays unset until T-012. **Changes asked by the Lead (done):** shared ratio errors, an overdispersion factor, the `WITNESS_DISAGREEMENT` threshold, and the size-dependent term `kappa` (approved 2026-11-14), all below.

**The estimator** (per area and month):
- **Per witness:** `E_w` = the sum, over strata and day/night, of `ratio x cell_days`. Raw cell-days are summed per witness and stratum first, then converted. `D` and `N` have their own ratios (`ALL` is not used); the ratio is the one of the stratum, witness, day/night and season of the month. Aqua has ratio 1 and no ratio uncertainty. Terra is raw view only.
- **Variance** has two parts, added:
  1. **Counting noise**, per stratum and day/night: `phi x ratio^2 x cell_days`, plus a term that grows with the size of the estimate, `kappa x E^2` (`E`: the witness estimate of the area for that day/night). `phi` is the overdispersion factor and `kappa` a relative error (below); both are the same for every witness, including single-witness months.
  2. **Ratio error, shared.** Strata that take the same ratio share its error, so the errors are added **fully correlated** inside each *ratio source*: a `LOCAL` stratum is its own source, the strata with pooling level `REGION` of one fire region form one source, the strata with level `GLOBAL` form one source (per witness, day/night and season). Each source adds `(sum of cell_days x ratio_sd)^2` (the Lead's `(sum cell_days)^2 x ratio_sd^2`, with each stratum's own `ratio_sd`; the two agree when the `ratio_sd` of a source is common). Different sources are independent **[LIMITATION]**: the region estimates share the global one, and `LOCAL` strata are partly shrunk toward their region, which this grouping by the dominant level does not capture, so the interval of a very large area can still be too narrow.
- **Zero counts:** the variance of a witness is never below `mean(ratio)^2` (one cell-day).
- **Combination (one method for every month):** the witnesses are combined **separately for day and for night** (a precision-weighted mean of the witnesses that count in that part) and the two combined estimates are **added**; the variances add. `S = sqrt(chi^2 / (N - 1))` is **pooled over both parts** (the `chi^2` and the degrees of freedom are summed) and multiplies the combined sd whenever `S > 1`; `disagreement_scale` is `max(S, 1)` with 2 or more witnesses and `null` with one. **The code `WITNESS_DISAGREEMENT` is given only when `S > 2`** (Lead's decision); `SINGLE_WITNESS` with one witness.
- **Witnesses that count:** only those with every day of the month available. If none counts, the estimate is `null` and `n_witnesses` is 0. The Aqua drift cutoff (D-005, approved by the Lead 2026-11-14) is `AQUA_FROM = {"D": None, "N": (2024, 5)}`: **Aqua night is not combined from 2024-05 on, Aqua day stays** (reason `AQUA_DRIFT_ERA`). The method is the same for every month: days and nights are combined separately and added, `S` is pooled over both with the degrees of freedom summed, and a night or day part that has data but no witness that counts gives no estimate for the month.
- **Interval:** 90% normal, `estimate +/- 1.645 sd`, lower bound at 0. `data_level` follows the witnesses that count, with the reason `PROVISIONAL_NRT` for `NRT` and `MIXED`.
- **First version ("totals method"):** summing day and night per witness and then combining the witnesses is kept as `separate=False`, only for the seam check below. The Indonesia 2015 table and the country shares in this section were computed with the totals method and are labelled "totals method"; the numbers of the method now used are in the subsection "The seam at 2024-05" below.

**Overdispersion `phi` and the size-dependent term `kappa`** (`estimate_dispersion`, fit periods only). **Approved by the Lead 2026-11-14.**
- **Model:** the variance of a witness estimate for one day/night is `phi x count + kappa x estimate^2`, plus the shared ratio variance. `phi` = 1, `kappa` = 0 is Poisson. The `kappa` term is a relative error: it grows with the square of the size, as the extra-Poisson variance does.
- **Method:** for Aqua against one VIIRS witness inside that witness's fit period (S-NPP 2012-01 to 2016-12; NOAA-20 2018-04 to 2021-12; **S-NPP is not used after 2016**, so no held-out year is read), take the difference `d` of the converted estimates in each country-month where both are at least 5 cell-days (10,888 units by day, 4,421 by night). `phi` and `kappa` are found **jointly** so that the median of `d^2 / expected variance` is as close as possible to the median of a chi-square(1) variable (0.455) in every size band (5 to 20, 20 to 100, 100 to 500, 500 and more cell-days): for each `phi` on a grid, `kappa >= 0` is the value that puts the pooled median at 0.455, and the `phi` whose four band medians are closest to 0.455 (sum of squared log-medians) is kept. With `kappa` fixed at 0 this is the earlier `phi`-only estimate.
- **Result [VERIFIED]:** by day `phi` = **2.25**, `kappa` = **0.0084** (a relative error of 9% per witness); by night `phi` = **2.47**, `kappa` = **0.0164** (13%). Applied to every witness, including Aqua and single-witness months.
- **Fit by size band [VERIFIED]:** the median of `d^2 / expected variance`, target 0.455 (units per band in brackets).

  | Model | Day: 5 to 20 | 20 to 100 | 100 to 500 | 500 and more | Night: 5 to 20 | 20 to 100 | 100 to 500 | 500 and more |
  |---|---|---|---|---|---|---|---|---|
  | `phi` only (7.72 / 6.53, the first PR #43 version) | 0.107 | 0.220 | 0.425 | **1.418** | 0.138 | 0.446 | 0.599 | **1.664** |
  | `phi` and `kappa` | 0.340 | 0.565 | 0.622 | 0.368 | 0.318 | 0.737 | 0.449 | 0.404 |
  | Units | 2,394 | 3,284 | 2,199 | 3,011 | 1,543 | 1,640 | 978 | 260 |

  The `phi`-only model was too wide for small units (0.11 to 0.14) and too narrow for the largest (1.4 to 1.7). With `kappa` all eight medians lie between 0.32 and 0.74: the size dependence is captured, but the fit is not perfect (the middle bands are slightly too narrow, the outer ones slightly too wide), which a model with two parameters cannot remove **[LIMITATION]**.
- **Lower bound:** the ratios were fitted on these months, so the two witnesses agree better in them than out of sample, and `phi` and `kappa` are lower bounds. Test D1 (coverage on the holdout years) is the final check.
- **Compare with the first version:** a single `phi` of 7.7 (day) and 6.5 (night) estimated on units of at least 20 cell-days. The estimate rose with the size of the unit (5.5, 7.7, 14.0 and 24.8 by day for minimum sizes of 5, 20, 100 and 500 cell-days), which is why a constant factor was replaced.

**Tests** (`pipeline/tests/test_harmonize.py`; 27 tests of the first version, 38 now, listed in the T-012 subsections below; synthetic data with answers computed by hand):
- the weighted mean, `chi^2` and sd; equal witnesses are not inflated and conflicting ones are; the stratum-first sum;
- **shared ratio errors:** two strata on the same pooled region ratio get a larger area variance (74.47) than two `LOCAL` strata (58.37); `GLOBAL` strata of different regions form one source, `REGION` strata of different regions do not;
- **`phi`:** it scales the counting variance of every witness, including a single one; `solve_phi` recovers planted values and ignores 5% outliers;
- **`kappa`:** it adds `kappa x E^2` to the variance of every witness, including a single one and Aqua; `kappa = 0` gives back the `phi`-only variance; `solve_dispersion` recovers planted `phi` and `kappa` (the variance they give at sizes 10, 100 and 1,000 within 25%; the two parameters are negatively correlated, so the variance is what is tested); it returns `kappa` near 0 when there is no size effect; `estimate_dispersion` recovers them from synthetic negative-binomial country-months with a relative error, fits the size bands better than `phi` alone, and **does not change when 5,000 cell-days are added to S-NPP from 2017**;
- **the code:** `S` of 1.35 inflates the sd but gives no `WITNESS_DISAGREEMENT`; `S` of 2.9 gives it;
- partial months, the Aqua cutoff, NRT flags, Terra, seasons, the `months` filter, order, determinism and contract shape.
- Breaking the code on purpose (regions not shared, `GLOBAL` not shared, ratio errors independent, `phi` ignored or not applied to Aqua, `kappa` ignored, not squared, not applied to Aqua, never positive, size bands ignored, code threshold at 1, fit window ignored, wrong chi-square target) makes tests fail (checked).

**On the real products** (final T-011 products):
- **Indonesia 2015, totals method** (`harmonize_area` with `separate=False`; the numbers of the method now used are below). Raw Aqua cell-days are 4,118, 10,761, 20,370, 17,386 and 2,800.

  | Month | Poisson only, independent strata | `phi` only (7.72 / 6.53) | **`phi` and `kappa`** | `S` | Code |
  |---|---|---|---|---|---|
  | July | 4,249 (114) | 4,289 (100) | **4,229 (251)** | 1.00 | none |
  | August | 10,660 (127) | 10,583 (160) | **10,628 (633)** | 1.00 | none |
  | September | 19,693 (1,060) | 18,869 (1,121) | **19,065 (1,161)** | 1.09 | none |
  | October | 17,279 (164) | 17,157 (216) | **17,204 (947)** | 1.00 | none |
  | November | 3,132 (275) | 3,218 (243) | **3,044 (278)** | 1.48 | none |

  Estimate (sd). The September interval (17,155 to 20,975) contains the raw Aqua value. Over all 176 Indonesian months with 2 or more witnesses: `S > 1` in 43% and `S > 2` in 8% (with `phi` only: 54% and 26%).
- **Every country, totals method** (66,218 country-months, 39,776 with 2 or more witnesses):

  | | Poisson only | `phi` only | **`phi` and `kappa`** |
  |---|---|---|---|
  | `S > 1` | 45% | 19% | **26%** |
  | `S > 2` (the code) | 24% | 6.2% | **6.8%** |
  | `S > 3` | 14% | 2.7% | 1.9% |
  | `S > 5` | 5.2% | 0.76% | 0.15% |
  | 95th percentile of `S` | 5.1 | 2.2 | 2.2 |
  | Median relative sd | 0.17 | 0.35 | 0.23 |

  The share of `S > 1` is higher than with `phi` alone, while the extreme disagreements (`S > 3`, `S > 5`) fall. **[HYPOTHESIS]** the intervals of small areas are narrower again (the constant `phi` is lower: 2.3 instead of 7.7) and those of large areas wider. Median relative sd is 0.23.
- **Level check (unchanged, the estimates do not depend on the variance):** converted witness against Aqua, country-months where both are at least 100 cell-days: S-NPP median 1.011 (5th to 95th percentile 0.71 to 1.53, 8,785); NOAA-20 median 1.005 (0.72 to 1.58, 5,006).
- **No estimate:** 904 country-months: 2002-07 to 2002-09 (Aqua outage days) and 2026-11 (a partial month).
- **Run time:** one area takes seconds; `python pipeline/harmonize.py` (every country, two variance variants) takes about 15 minutes; `python pipeline/harmonize.py phi` takes 10 seconds.

- **Every country with the method now used (day and night combined separately), `phi` and `kappa`** (66,218 country-months, 39,776 with 2 or more witnesses; 65,314 with an estimate; the 904 without are the same months as before):

  | | Totals method (first version) | **Day and night separately (now)** |
  |---|---|---|
  | `S > 1` | 26% | **23.7%** |
  | `S > 2` (the code) | 6.8% | **4.6%** |
  | `S > 3` | 1.9% | 0.83% |
  | `S > 5` | 0.15% | 0.02% |
  | 95th percentile of `S` | 2.23 | 1.95 |
  | Median relative sd | 0.23 | 0.22 |
  | Indonesia `S > 1` / `S > 2` | 43% / 8% | 58.5% / 13.6% |

  **[VERIFIED, re-run 2026-11-15]** `python pipeline/harmonize.py` was re-run with the final code of T-014 (both bug fixes, shared ratio errors, the `S > 2` rule) over all 66,218 country-months: `S > 1` 23.66%, `S > 2` 4.62%, `S > 3` 0.83%, `S > 5` 0.02%; 95th percentile of `S` 1.95 (99th 2.90); median relative sd 0.223; Indonesia `S > 1` 58.5% and `S > 2` 13.6%. These equal the "now" column above to the digits shown, so the two fixes did not move the shares. With `phi` only: `S > 1` 18.3%, `S > 2` 5.0%, median relative sd 0.345.

**Reading it correctly (totals method):** the witnesses disagree beyond their stated uncertainty (`S > 1`) in 26% of the multi-witness country-months and beyond a factor of 2 in 6.8%, so the code `WITNESS_DISAGREEMENT` flags the exceptions. Whether the intervals are the right width is test D1: the Aqua-only years (2002-07 to 2011-12, inside the 2003 to 2022 baseline) have no second witness, so their width rests on `phi` and `kappa` alone.

### Holdout evaluation 2017 to 2021 (T-012) **[VERIFIED 2026-11-14 unless labelled]**

Source: `python pipeline/holdout.py`; the report is `data/interim/qa/holdout_report.json` (not committed). Code: `pipeline/holdout.py`; tests: `pipeline/tests/test_holdout.py` (SYNTHETIC fixtures with answers known by hand).

**How it is done**

- Question: how well does the converted S-NPP estimate predict what Aqua MODIS counted, in months that were not used to fit the ratios?
- Units: fire-region-months and country-months, 2017-01 to 2021-12, day and night separately. A unit needs a complete month for both Aqua and S-NPP and at least 20 Aqua cell-days (sensitivity at 5 and 100). The day+night total (T) exists only where both a day and a night unit exist.
- Actual value: the Aqua cell-day count (an estimate with ratio 1, not ground truth).
- Three predictions on the same units:
  - ours: the converted S-NPP estimate (T-011 ratios, T-013 aggregation);
  - raw: the naive raw merge (raw S-NPP cell-days);
  - global ratio (glob): one ratio per day/night and season (sum Aqua / sum S-NPP raw over the globe), fitted on 2012-01 to 2016-12 only and applied to raw S-NPP cell-days.
- Global ratios (fit 2012-2016): D {DJF 0.281, MAM 0.273, JJA 0.350, SON 0.279}; N {DJF 0.051, MAM 0.041, JJA 0.071, SON 0.075}.
- Nothing is fitted on 2017-2021 except as noted under "Reading it correctly".
- 90% interval = prediction +/- 1.645 x sqrt(var_pred + var_aqua). Per day/night unit, var_pred = phi x vc_S + kappa x e_S^2 + vr_S (S-NPP counting variance at phi = 1, relative-error term on the converted estimate, shared ratio variance) and var_aqua = phi x vc_A + kappa x actual^2. Totals sum the D and N variances. phi = {D 2.25, N 2.47}, kappa = {D 0.0084, N 0.0164} (`harmonize.PHI`, `harmonize.KAPPA`).
- Variance variants compared: with_phi_kappa (the final model), with_phi_only (phi D 7.72, N 6.53, kappa 0), poisson_only (phi 1, kappa 0).
- Error measures: ratio predicted/actual (median, 5th and 95th percentile) and the median absolute log error (MALE). A prediction of 0 is floored at 1 cell-day in the log error **[ASSUMPTION]**.

**Main result (Aqua >= 20 cell-days; ours / raw / glob)**

| Level | D/N/T | n | median pred/actual | p05 | p95 | MALE ours | MALE raw | MALE glob |
|---|---|---|---|---|---|---|---|---|
| Region | D | 830 | 1.03 / 3.85 / 1.12 | 0.84 / 2.21 / 0.65 | 1.46 / 7.05 / 2.24 | 0.090 | 1.347 | 0.265 |
| Region | N | 636 | 1.08 / 19.66 / 1.08 | 0.57 / 6.52 / 0.40 | 2.09 / 58.13 / 3.21 | 0.209 | 2.979 | 0.447 |
| Region | T | 636 | 1.02 / 4.60 / 1.07 | 0.82 / 2.97 / 0.62 | 1.34 / 7.83 / 1.95 | 0.086 | 1.526 | 0.224 |
| Country | D | 4798 | 1.04 / 4.19 / 1.21 | 0.69 / 2.19 / 0.64 | 1.74 / 9.62 / 2.83 | 0.149 | 1.434 | 0.316 |
| Country | N | 1611 | 1.02 / 19.08 / 1.03 | 0.47 / 5.69 / 0.31 | 1.89 / 61.76 / 3.66 | 0.224 | 2.949 | 0.569 |
| Country | T | 1600 | 0.99 / 4.22 / 0.98 | 0.73 / 2.79 / 0.61 | 1.36 / 7.96 / 1.79 | 0.100 | 1.439 | 0.213 |

- Ours has a lower pooled MALE than both baselines in every row (D, N, T at region and country level); against the raw merge it is roughly 10 to 18 times lower.
- Raw S-NPP counts exceed Aqua by a median factor of about 4 by day and about 19 to 20 by night, so the raw merge is not usable as a combined count; that is the reason for the conversion.
- Median pred/actual of ours is within about 8% of 1 in every pooled row (1.02 to 1.08 for regions, 0.995 to 1.04 for countries).

**By fire region (n units; median = median pred/actual of ours; MALE of ours, raw, glob)**

| Region | D n | D median | D ours | D raw | D glob | N n | N median | N ours | N raw | N glob |
|---|---|---|---|---|---|---|---|---|---|---|
| AUST | 60 | 1.00 | 0.064 | 0.905 | 0.335 | 60 | 1.15 | 0.251 | 2.636 | 0.509 |
| BOAS | 50 | 0.98 | 0.090 | 0.875 | 0.352 | 38 | 1.08 | 0.304 | 2.957 | 0.461 |
| BONA | 56 | 1.03 | 0.115 | 0.938 | 0.292 | 30 | 0.74 | 0.437 | 2.578 | 0.622 |
| CEAM | 60 | 0.96 | 0.070 | 1.631 | 0.367 | 43 | 0.99 | 0.217 | 2.961 | 0.309 |
| CEAS | 60 | 0.99 | 0.065 | 1.204 | 0.121 | 55 | 1.43 | 0.444 | 3.542 | 0.795 |
| EQAS | 60 | 1.12 | 0.113 | 1.640 | 0.433 | 31 | 1.31 | 0.290 | 2.794 | 0.408 |
| EURO | 60 | 1.04 | 0.146 | 1.348 | 0.134 | 33 | 1.04 | 0.281 | 2.916 | 0.223 |
| MIDE | 60 | 1.13 | 0.164 | 1.574 | 0.347 | 57 | 1.07 | 0.162 | 3.038 | 0.269 |
| NHAF | 60 | 1.08 | 0.096 | 1.422 | 0.164 | 50 | 1.03 | 0.083 | 3.025 | 0.205 |
| NHSA | 60 | 1.02 | 0.075 | 1.546 | 0.295 | 38 | 1.07 | 0.156 | 2.749 | 0.290 |
| SEAS | 60 | 1.03 | 0.084 | 1.627 | 0.359 | 41 | 1.28 | 0.314 | 3.908 | 0.924 |
| SHAF | 60 | 1.07 | 0.086 | 1.559 | 0.263 | 58 | 1.07 | 0.105 | 3.154 | 0.476 |
| SHSA | 60 | 1.00 | 0.088 | 1.168 | 0.120 | 60 | 1.05 | 0.112 | 2.277 | 0.542 |
| TENA | 60 | 1.02 | 0.093 | 0.995 | 0.260 | 42 | 0.90 | 0.362 | 3.116 | 0.708 |
| UNASSIGNED | 4 | 0.94 | 0.155 | 1.373 | 0.245 | - | - | - | - | - |

**Where ours does not beat a baseline (groups with at least 30 units where MALE ours is larger than a baseline; raw is never the better one)**

- Regions: EURO D (ours 0.146, glob 0.134, n 60) and EURO N (0.281 vs 0.223, n 33). No other region group, D, N or T, loses.
- Countries (8 groups, all against glob): ESP D (0.177 vs 0.153), KAZ N (0.490 vs 0.383), PRY D (0.104 vs 0.103), SDN D (0.173 vs 0.142), SDN N (0.168 vs 0.136), URY D (0.208 vs 0.184), MLI T (0.080 vs 0.076), SDN T (0.108 vs 0.088).
- Night is the weaker half: pooled N MALE 0.209 (regions) and 0.224 (countries) against 0.090 and 0.149 by day, and the 5th to 95th percentile range of the N ratio is wide (0.57 to 2.09 for regions, 0.47 to 1.89 for countries). **[HYPOTHESIS]** few night detections per unit and a night ratio estimated from fewer cells; not tested.

**Bias by year (median log(pred/actual), ours)**

| Level | D/N/T | 2017 | 2018 | 2019 | 2020 | 2021 |
|---|---|---|---|---|---|---|
| Region | D | -0.007 | +0.035 | +0.026 | +0.052 | +0.029 |
| Region | N | +0.026 | +0.101 | +0.046 | +0.105 | +0.126 |
| Region | T | -0.004 | +0.020 | +0.022 | +0.030 | +0.025 |
| Country | D | +0.001 | +0.061 | +0.034 | +0.049 | +0.033 |
| Country | N | -0.004 | +0.065 | +0.022 | +0.021 | +0.019 |
| Country | T | -0.020 | +0.001 | -0.003 | -0.006 | -0.005 |

- Ours is slightly high from 2018 on at region level, most at night (+0.10 to +0.13 in 2018, 2020 and 2021); by day and in the total it is at most +0.05 and +0.03. The pattern is not a clean monotonic drift. **[OPEN]** whether the night offset is Aqua drift or an S-NPP effect; that is the subject of the Aqua drift analysis, not of this section.

**Coverage of the 90% interval (target 80% to 97%)**

| Level | Variant | D/N units | D | N | Total (D+N) |
|---|---|---|---|---|---|
| Region | with_phi_kappa | 0.818 | 0.870 | 0.750 | 0.847 |
| Region | with_phi_only | 0.616 | 0.587 | 0.654 | 0.506 |
| Region | poisson_only | 0.333 | 0.307 | 0.366 | 0.266 |
| Country | with_phi_kappa | 0.811 | 0.817 | 0.794 | 0.826 |
| Country | with_phi_only | 0.779 | 0.775 | 0.791 | 0.601 |
| Country | poisson_only | 0.452 | 0.451 | 0.455 | 0.301 |

- Final model (with_phi_kappa): pooled coverage is inside 80% to 97% for D/N units (regions 0.818, countries 0.811), for day (0.870, 0.817) and for the totals (0.847, 0.826). It is below 80% for night units at both levels (regions 0.750, countries 0.794). So the target is met for the pooled units and totals and not met for night units taken alone.
- With phi only the target is not met: regions 0.616 (total 0.506), country totals 0.601 (country D/N units 0.779 is also just below). Poisson only is far too narrow (0.333 regions, 0.452 countries). The kappa term is what brings the intervals into the target range (with phi and kappa estimated on the S-NPP fit period, see below).
- By group (at least 30 units, final model): 7 of 14 region groups are inside 80% to 97% for D/N units (range 0.70 to 0.96) and 7 of 14 for region totals (0.67 to 1.00). 45 of 87 countries are inside for D/N units (range 0.39 to 1.00); 16 of 19 countries for totals (0.68 to 0.96). The pooled number meets the target, but roughly half of the individual regions and countries fall below 80%.
- Lowest country D/N unit coverages (at least 30 units) include DZA 0.41, MWI 0.39, DEU 0.56, JPN 0.57, CHN 0.58 and PER 0.54; reasons were not investigated. **[OPEN]**

**Coverage check asked by the Lead on PR #43 [VERIFIED]** (final model `phi` and `kappa`; 90% and 50% intervals; the rule below was fixed by the Lead before these numbers were seen).

| Level | Units | 90% interval | 50% interval |
|---|---|---|---|
| Regions, day/night units | 1,466 | **0.818** | 0.471 |
| Regions, day | 830 | 0.870 | 0.516 |
| Regions, night | 636 | 0.750 | 0.414 |
| Regions, day+night total | 636 | 0.847 | 0.497 |
| Countries, day/night units | 6,409 | **0.811** | 0.439 |
| Countries, day | 4,798 | 0.817 | 0.448 |
| Countries, night | 1,611 | 0.794 | 0.412 |
| Countries, day+night total | 1,600 | 0.826 | 0.463 |

**By size band** (Aqua cell-days of the unit; 90% interval and 50% interval in brackets; units in brackets of the band at 20 or more; the 5 to 20 band comes from the run with a minimum of 5):

| Band | Regions D | Regions N | Countries D | Countries N |
|---|---|---|---|---|
| 5 to 20 | 0.828 (0.483), n 29 | 0.582 (0.276), n 134 | 0.831 (0.482), n 1,750 | 0.858 (0.486), n 1,118 |
| 20 to 100 | 0.727 (0.273), n 22 | 0.712 (0.349), n 229 | 0.814 (0.424), n 1,852 | 0.779 (0.396), n 926 |
| 100 to 500 | 0.770 (0.415), n 135 | 0.752 (0.407), n 226 | 0.764 (0.409), n 1,239 | 0.830 (0.429), n 529 |
| 500 and more | 0.895 (0.544), n 673 | 0.796 (0.503), n 181 | 0.858 (0.501), n 1,707 | 0.763 (0.449), n 156 |

**By period** (the Lead's split: a widening factor `c` on 2017 to 2018 only, coverage on 2019 to 2021):

| Level | 90%, 2017-2018 | 90%, 2019-2021 | 50%, 2017-2018 | 50%, 2019-2021 |
|---|---|---|---|---|
| Regions | 0.828 (587 units) | 0.811 (879) | 0.504 | 0.449 |
| Countries | 0.824 (2,520) | 0.803 (3,889) | 0.437 | 0.440 |

**The pre-registered rule (Lead, PR #43):** if coverage is below 80%, estimate one factor `c` on 2017 to 2018 only and report 2019 to 2021 with it; if it is 80% to 97%, change nothing and report it; above 97%, report only.
- **Applied here:** the pooled coverage of the 90% interval is 0.818 (regions) and 0.811 (countries), inside 80% to 97%, so **nothing is changed** and the honest holdout number is **0.811 and 0.803 on 2019 to 2021**.
- **Not met, and not hidden:** night units alone (0.750 regions, 0.794 countries), the 100 to 500 and 20 to 100 bands at region level (0.71 to 0.77), country night over 500 cell-days (0.763), and the 5 to 20 band at region night (0.582). The 50% interval covers 0.47 and 0.44, below 50%, so the intervals are slightly too narrow in the middle as well.
- **For information, not applied:** the smallest `c` giving 90% on 2017 to 2018 is 1.26 (regions) and 1.31 (countries); with it, the coverage on 2019 to 2021 would be 0.877 and 0.887 (the 50% interval, `c` 0.97 and 1.16: 0.439 and 0.500).

**Sensitivity to the minimum Aqua cell-days**

| Level | min | n D | n N | MALE ours D / N | with_phi_kappa coverage: D/N, D, N, total | with_phi_only: D/N, total |
|---|---|---|---|---|---|---|
| Region | 5 | 859 | 770 | 0.094 / 0.260 | 0.799, 0.868, 0.721, 0.839 | 0.630, 0.530 |
| Region | 20 | 830 | 636 | 0.090 / 0.209 | 0.818, 0.870, 0.750, 0.847 | 0.616, 0.506 |
| Region | 100 | 808 | 407 | 0.088 / 0.161 | 0.840, 0.874, 0.771, 0.860 | 0.584, 0.405 |
| Country | 5 | 6548 | 2729 | 0.191 / 0.286 | 0.821, 0.821, 0.820, 0.806 | 0.828, 0.678 |
| Country | 20 | 4798 | 1611 | 0.149 / 0.224 | 0.811, 0.817, 0.794, 0.826 | 0.779, 0.601 |
| Country | 100 | 2946 | 685 | 0.113 / 0.173 | 0.818, 0.819, 0.815, 0.869 | 0.682, 0.483 |

- The error falls as the minimum rises (more cell-days, less relative noise). With the final model the pooled coverage stays between 0.72 and 0.87 over all thresholds; night units are below 0.80 at region level for all three thresholds (0.721, 0.750, 0.771). At 5 cell-days the pooled region D/N coverage (0.799) is just under the target. With phi only, the totals stay far below target at every threshold.

**Reading it correctly**

- Aqua and S-NPP observe many of the same fires, so the two sides are not independent. The interval adds var_pred and var_aqua as if they were, which ignores their covariance. **[ASSUMPTION]** independence; the covariance was not quantified. The coverage numbers describe this approximation.
- phi and kappa (T-013) were estimated on country-months of the fit periods: Aqua against S-NPP in 2012 to 2016 and Aqua against NOAA-20 in 2018-04 to 2021-12. The second pair overlaps the months of this holdout (the Aqua side is the same), so coverage on 2017-2021 is not a clean out-of-sample test of the variance model. The T-011 ratios and the global baseline are out-of-sample for S-NPP.
- Aqua is the reference here but is itself an estimate and subject to drift; agreement with Aqua is not agreement with the truth. Hotspots are not fire counts or burned area.
- D1, the independent final check, has not been run; these results do not replace it. **[OPEN]**

### Aqua drift diagnostic (T-012) **[VERIFIED 2026-11-14 unless labelled]**

Code `pipeline/aqua_drift.py`, tests `pipeline/tests/test_aqua_drift.py`, figure `docs/figures/aqua_drift.png`, report `data/interim/qa/aqua_drift_report.json` (not committed). **Nothing in this section is applied anywhere**; the proposal is for the Lead's decision (D-005).

#### Question and series

Is the Aqua / converted-VIIRS ratio R(t) stable after the T-011 fit years? R(t) is the monthly ratio of the Aqua estimate to the converted VIIRS estimate (the T-011 ratios exactly as fitted, nothing refitted), computed globally and per fire region, day and night separately, from S-NPP and from NOAA-20 separately. Only months in which both witnesses are complete enter a series. The primary series is global day, S-NPP (164 months from 2012-01). The last complete month of both VIIRS witnesses is 2026-10.

#### Pre-registered method (fixed in the task prompt before any result was seen) [VERIFIED]

On y(t) = log R(t) of the global day series from S-NPP, fit by least squares a model that is flat up to a break month b and linear afterwards, continuous at b: y = a + s x max(0, t - b). Candidate b run from 2018-01 to 2025-06. The onset is the b with the smallest residual sum of squares. Its 90% interval is the 5th to 95th percentile of b over 1,000 moving-block bootstrap replicates of the residuals (blocks of 6 months, fixed seed; every replicate repeats the whole search over b). The slope after b is reported with the 5th to 95th percentile of the replicate slopes. Drift is DETECTED only if the slope interval excludes 0 AND the break model beats the flat model by BIC, where BIC = n log(RSS / n) + k log n. The same procedure is repeated, as confirmation and not as selection, for the night series, for NOAA-20 (from 2018-04) and for each fire region.

#### Choices the registered method left open [VERIFIED]

- BIC parameter counts: flat k = 2 (level, sigma); break k = 4 (level, slope, break month, sigma).
- Incomplete months are dropped: a month enters only if Aqua and the VIIRS witness are both complete (the global value needs every entity complete) and both values are above zero.
- Regional series: a month also needs at least 20 cell-days on each side; series with fewer than 60 months are not fitted. Region UNASSIGNED has too few months (2 to 12) and is not fitted.
- NOAA-20 series start in 2018-04, so their first candidate month is 2019-04 (12 months after the first month); the last candidate stays 2025-06.
- Interval definitions: the onset interval is the 5th to 95th percentile of the bootstrap break months, reported on the month grid; the slope is the log-slope s converted to percent per year as 100 x (exp(12 s) - 1), with the 5th to 95th percentile of the replicate slopes converted the same way. dBIC is BIC(flat) minus BIC(break), so positive favours the break model.
- Bootstrap: 1000 replicates, block length 6 months, seed 2012.

#### Result of the primary series [VERIFIED]

Global day, S-NPP: onset 2025-06 (90% interval 2019-02 to 2025-06); slope after onset -5.4% per year (90% interval -8.5 to -0.4); BIC break -853.5 against flat -859.6, so the flat model is better by 6.1. The slope interval excludes 0 but the break model does not beat the flat model by BIC. **Drift is NOT detected by the registered rule.** The onset sits at the last allowed candidate (2025-06), so the break is at the edge of the range and the fitted decline covers only the final months.

#### Confirmation series, global [VERIFIED]

| Daynight | Witness | Detected | Onset | Onset 90% interval | Slope %/yr (90%) | dBIC | Months |
|---|---|---|---|---|---|---|---|
| N | SNPP_VIIRS | yes | 2024-05 | 2022-10 to 2025-04 | -12.0 (-22.8 to -5.5) | +28.9 | 164 |
| N | NOAA20_VIIRS | yes | 2024-09 | 2024-03 to 2025-02 | -19.0 (-25.4 to -14.1) | +50.7 | 99 |
| D | NOAA20_VIIRS | no | 2025-06 | 2020-01 to 2025-06 | -6.1 (-9.2 to -0.5) | -2.7 | 99 |

Global night is detected in both witnesses (S-NPP onset 2024-05, NOAA-20 onset 2024-09). Global day from NOAA-20 is not detected.

#### Fire regions, day and night, both witnesses [VERIFIED]

Each cell: detected; onset; slope in %/yr. Region codes are the fire-region codes of the pipeline. Intervals for every cell are in the report.

| Region | Day S-NPP | Day NOAA-20 | Night S-NPP | Night NOAA-20 |
|---|---|---|---|---|
| AUST | no; 2021-02; +0.8 | no; 2021-01; +0.9 | no; 2025-02; -16.1 | no; 2025-03; -20.1 |
| BOAS | no; 2020-08; +1.8 | no; 2023-11; +4.9 | no; 2023-05; -13.0 | yes; 2024-04; -28.1 |
| BONA | no; 2024-03; +3.1 | no; 2020-03; +1.6 | no; 2018-01; +5.8 | not fitted (n=50) |
| CEAM | yes; 2018-10; +1.7 | yes; 2019-04; +2.1 | no; 2025-06; +4.4 | no; 2024-08; -3.1 |
| CEAS | yes; 2018-12; +2.1 | no; 2019-04; +1.6 | no; 2019-08; -3.2 | yes; 2023-04; -9.4 |
| EQAS | no; 2018-01; -0.9 | no; 2025-06; +11.2 | no; 2018-10; -3.0 | not fitted (n=48) |
| EURO | no; 2020-07; +2.5 | no; 2020-05; +3.1 | no; 2025-06; -3.6 | not fitted (n=50) |
| MIDE | no; 2022-03; +4.1 | yes; 2021-04; +4.7 | no; 2019-12; -1.0 | no; 2020-01; -1.9 |
| NHAF | no; 2025-06; -11.7 | no; 2025-06; -5.4 | yes; 2024-10; -12.5 | yes; 2023-10; -8.6 |
| NHSA | yes; 2022-06; +4.0 | yes; 2022-03; +5.0 | yes; 2024-03; -11.8 | yes; 2024-03; -13.1 |
| SEAS | no; 2023-06; +4.8 | no; 2021-05; +2.1 | no; 2019-05; -2.3 | no; 2019-08; -3.0 |
| SHAF | no; 2025-06; -5.0 | no; 2025-06; -8.6 | yes; 2018-01; -3.2 | yes; 2024-04; -16.9 |
| SHSA | yes; 2021-06; +3.6 | yes; 2020-12; +3.0 | yes; 2024-06; -12.3 | yes; 2024-08; -18.4 |
| TENA | yes; 2024-10; -13.2 | yes; 2021-11; -2.6 | no; 2021-09; -8.4 | no; 2021-08; -7.4 |
| UNASSIGNED | not fitted (n=12) | not fitted (n=6) | not fitted (n=2) | not fitted (n=2) |

The regional results are descriptive confirmation, not a selection of a cutoff. They are many tests without a multiplicity correction [ASSUMPTION: the registered method has none, and none was added]. Several regional series are detected with onsets years before 2024; those are not the same phenomenon as the night-time decline and are not interpreted here [OPEN].

#### R(t) in the fit years [VERIFIED]

Near 1 by construction, because T-011 fitted the ratios on these years.

| Series | Months | Median R | Min R | Max R |
|---|---|---|---|---|
| S-NPP day, 2012-2016 | 58 | 0.990 | 0.878 | 1.114 |
| S-NPP night, 2012-2016 | 58 | 0.978 | 0.802 | 1.170 |
| NOAA-20 day, 2018-2021 | 45 | 0.992 | 0.677 | 1.141 |
| NOAA-20 night, 2018-2021 | 45 | 0.972 | 0.703 | 1.282 |

#### Sensitivity (not part of the registered method) [VERIFIED as computed; sensitivity only]

- Block length 3 months: not detected, onset 2025-06 (interval 2019-01 to 2025-06). Block length 12 months: not detected, onset 2025-06 (interval 2019-04 to 2025-06).
- Null bootstrap of the break search (primary series): observed gain 0.0246, null 95th percentile 0.0307, p = 0.074.
- Candidate range extended to 2026-04: day not detected (onset 2025-09, slope -7.7% per year, dBIC -5.4); night detected (onset 2024-05, interval 2022-10 to 2025-04, slope -12.0% per year, dBIC +28.9).
- Primary residuals: lag-1 autocorrelation -0.19, standard deviation 0.071 (log units).

#### Proposal

**[VERIFIED]** By the registered rule **no `aqua_cutoff` is proposed**, because the primary series (global day, S-NPP) is not detected. The report holds `aqua_cutoff: null`.

**[APPROVED by the Lead 2026-11-14 as a documented deviation from the registered rule; see D-005]** Night-time Aqua / converted VIIRS falls from about 2024-05 (S-NPP) to about 2024-09 (NOAA-20), in both witnesses; the onset intervals overlap (S-NPP 2022-10 to 2025-04, NOAA-20 2024-03 to 2025-02). The Lead approved a **night-only cutoff from 2024-05** (the earlier onset; Aqua day stays, as the registered rule says). This is a deviation from the registered day-only rule, chosen after seeing the results, and is therefore not a registered result; it is recorded as such in D-005 and in the risk S17. The cause (an Aqua change, a processing change, or a VIIRS change) is [OPEN]; this diagnostic cannot separate them.

#### Effect of the cutoff in `harmonize_area` [VERIFIED]

`AQUA_FROM = {"D": None, "N": (2024, 5)}` is the module default. There is one method for every month (days and nights combined separately and added, see T-013 above), so the cutoff changes only which witnesses enter. Checked on the real products:
- **Months before 2024-05 are identical with and without the cutoff**: the same method and the same witnesses (Indonesia, Brazil and Australia, 262 months each: identical to 1e-12, the floating-point order of the sums).
- **2024-05 to 2026-10** (31 months; the month 2026-11 is partial): the estimates change only through the exclusion of Aqua night; the months carry `AQUA_DRIFT_ERA`. **Size of the change [VERIFIED], default against no cutoff, with the single method:** the estimate moves by +1.18% on average for Indonesia, +0.68% for Brazil and +0.85% for Australia, and the sd by -19.2%, -0.6% and -11.8% (the sd falls where Aqua night, with its large variance, no longer enters the night part). Months before 2024-05 differ by at most 1.5e-11 (the order of floating-point sums).
- **The holdout does not move:** its window is 2017 to 2021 and Aqua is the target there, not a combined witness (90% coverage 0.818 for regions and 0.811 for countries, as before).
- **Tests** (`pipeline/tests/test_harmonize.py`, 38 tests, all pass): the default is night from 2024-05 and no day cutoff; night excluded from 2024-05 with Aqua day kept, by hand; the code `AQUA_DRIFT_ERA` present and absent; two months, before and after 2024-05, with identical inputs differ only through the Aqua night exclusion (with no Aqua night rows the two months are identical; May equals the data without Aqua night; April keeps it); Aqua day still weighs in after the cutoff (and Aqua night's 500 does not); a night with no other witness gives no estimate; the disagreement is pooled over day and night; the two ways of combining agree exactly when day and night agree, and the totals method (`separate=False`) differs when they disagree.

#### The seam at 2024-05: both ways of combining (Lead review, PR #45) [VERIFIED]

**Concern:** switching the combination method at the cutoff month could create an artificial step. **Rule (fixed by the Lead before the run):** compute both ways for 2012-01 to 2024-04, every country-month and fire-region-month. If the median of the absolute value of log(separate / totals) of the estimate is at most 1% **and** its 95th percentile is at most 5%, keep the code as it was; otherwise use the separate day/night combination for all months and re-run the holdout coverage and Indonesia 2015. Run: `python pipeline/harmonize.py seam` (`data/interim/qa/harmonize_seam.json`). 29,542 entity-months, 29,229 of them with 2 or more witnesses.

| | Entity-months | Median abs. log ratio | 95th pct | 99th pct | Max | sd ratio, median | sd ratio, 5th to 95th pct |
|---|---|---|---|---|---|---|---|
| All | 29,542 | 0.0035 | 0.280 | 0.894 | 4.30 | 1.000 | 0.71 to 1.70 |
| Country | 27,322 | 0.0039 | 0.315 | 0.907 | 4.30 | 1.000 | 0.71 to 1.70 |
| Fire region | 2,220 | 0.0012 | 0.041 | 0.259 | 0.72 | 1.000 | 0.73 to 1.77 |

(log units; `python pipeline/harmonize.py seam`, `data/interim/qa/harmonize_seam.json`.) Over the 29,229 entity-months with 2 or more witnesses the figures are the same to the third decimal.

- **Decision:** the median is within 1% but the 95th percentile (0.280, about 28%) is far above 5%, so by the rule **the separate day/night combination is used for all months**. This is the method described in T-013 above.
- **Holdout re-run:** unchanged, because it does not use the combined estimate (Aqua is its target): 90% coverage 0.818 (regions) and 0.811 (countries); 50% coverage 0.471 and 0.439; 2019 to 2021 0.811 and 0.803.
- **Indonesia 2015, new method vs totals method** (estimate (sd), `S`):

  | Month | New method | `S` | Totals method | `S` |
  |---|---|---|---|---|
  | July | 4,229.3 (251.4) | 1.00 | 4,229.0 (251.5) | 1.00 |
  | August | 10,627.3 (633.4) | 1.00 | 10,627.6 (633.4) | 1.00 |
  | September | 19,068.7 (1,063.0) | 1.00 | 19,065.3 (1,161.3) | 1.09 |
  | October | 17,202.7 (946.7) | 1.00 | 17,204.0 (946.9) | 1.00 |
  | November | 3,039.2 (306.2) | 1.63 | 3,044.3 (277.6) | 1.48 |

  Raw Aqua cell-days in September: 20,370; the new September interval (17,320 to 20,817) contains it. Over all 176 Indonesian months with 2 or more witnesses: `S > 1` in 58.5% and `S > 2` in 13.6% (totals method: 43% and 8%); median relative sd 0.093.
- **Why the tail is large [HYPOTHESIS, not investigated]:** the two ways differ most where day and night disagree differently across the witnesses, so that weighting the witnesses once for the total and weighting them separately for day and night give different answers.

#### Problem of the registered design [VERIFIED as a property of the design]

A drift visible only at night, or only in the last months before the end of the candidate range, can fail a day-only decision rule. Here the day series has a slope interval that excludes 0 but a break at the range edge, which BIC does not reward, while night is clearly detected in both witnesses. The registered primary series therefore does not report the night-time change.

**Nothing is applied.** Figure: `docs/figures/aqua_drift.png`.

### Baseline, probabilities, verdicts and the real harmonized products (T-014) **[VERIFIED 2026-11-15 unless labelled]**

`python pipeline/verdicts.py` (about 25 minutes) writes `cell_month_harmonized.parquet`, `entity_month.parquet`, `metadata.json` and `validation_results.json` into `data/products/` (Git LFS for the Parquet files, D-027), from the final T-011 products and the T-013 method. They replace the raw-only tables of T-014a. `method_version` is `0.1.0` (no `-raw-only`), `contract_version` 0.1.1. The rules are D-028 (approved by the Lead 2026-11-14), implemented without changing a threshold.

**What is computed** (per cell, per country, per continent and for the world, every month with data):
- **Estimate and interval:** the T-013 combination (`phi` and `kappa`, shared ratio errors, day and night combined separately, Aqua night excluded from 2024-05), vectorised in `pipeline/verdicts.py`; **tested equal to `harmonize.records_from`** on random inputs. The 90% interval is `estimate +/- 1.645 sd`, lower bound 0.
- **Baseline:** the same calendar month over 2003 to 2022, empirical p25, p50, p75 (linear interpolation) of the estimates of the years that have one; fewer than 15 of the 20 years: no baseline. 98.6% of cell-months have a baseline.
- **Probabilities:** the estimate is Normal(estimate, sd) truncated at 0; `p_above` = P(X > p75), `p_below` = P(X < p25), `p_within` = the rest. `pct_of_normal` = estimate / p50 x 100.
- **Verdict**, in the order of D-028: no estimate (`OUTAGE`); fewer than 15 baseline years (`INSUFFICIENT_BASELINE`); estimate 0 and p75 at most 1 (`NO_DETECTED_ACTIVITY`); p50 below 5 (`INSUFFICIENT_BASELINE`); then `ABOVE_NORMAL`, `BELOW_NORMAL`, `WITHIN_NORMAL` at probability 0.8 or more; otherwise `CANNOT_DETERMINE` with `WIDE_INTERVAL`.
- **Caveat codes:** `PROVISIONAL_NRT`, `SINGLE_WITNESS`, `WITNESS_DISAGREEMENT` (S above 2), `AQUA_DRIFT_ERA`, `POOLED_CALIBRATION` (more than 50% of the converted cell-days of the witnesses that count use a `REGION` or `GLOBAL` ratio), `DIURNAL_CAVEAT` (India and the cells with centres in 29.5 to 32.5 N, 73.8 to 77.5 E, October and November, from 2020). `INSUFFICIENT_OVERLAP` is not used.

**Refinement of D-028 step 3 [APPROVED by the Lead 2026-11-15, D-028 amendment A].** The contract checker forbids `NO_DETECTED_ACTIVITY` where any witness, Terra included, detected something. Step 3 therefore also requires the raw combined cell-days to be 0. In a first run without that condition, 216,103 cell-months (2.0% of the `NO_DETECTED_ACTIVITY` rows), 545 country-months and 3 continent-months had an estimate of 0 but a raw detection (mostly Terra, or a witness that was not complete); they now go on to step 4 and get `INSUFFICIENT_BASELINE`.

**The products** (293 months, 2002-07 to 2026-11; the months 2026-08 to 2026-11 are provisional):

| Table | Rows | Contract check (real mode) |
|---|---|---|
| `cell_month_harmonized` | 16,477,734 (56,238 cells) | 0 errors, every row group |
| `entity_month` | 68,562 (226 countries, 7 continents, the world) | 0 errors |

**Verdicts by level** (all months):

| Level | Rows | `ABOVE` | `BELOW` | `WITHIN` | `CANNOT_DETERMINE` | `NO_DETECTED_ACTIVITY` | Above, below or within | Not `CANNOT_DETERMINE` |
|---|---|---|---|---|---|---|---|---|
| Cells | 16,477,734 | 140,806 | 161,944 | 175,682 | 5,222,088 | 10,777,214 | 2.9% | 68.3% |
| Countries | 66,218 | 5,776 | 5,937 | 7,864 | 32,658 | 13,983 | 29.6% | 50.7% |
| Continents | 2,051 | 311 | 331 | 438 | 832 | 139 | 52.7% | 59.4% |
| World | 293 | 32 | 50 | 18 | 193 | 0 | 34.1% | 34.1% |

- **Most cells are quiet:** 65% of cell-months are `NO_DETECTED_ACTIVITY`, and the share of cell-months that can be judged is 2.9%, as the plan expected (about 9% of cell-months reach 5 Aqua cell-days); countries and continents are the main verdict levels.
- **The share of country-months that can be judged grows with the years:** 25% to 27% in 2003 to 2011 (Aqua only), 29% to 34% in 2012 to 2022, 37% to 39% in 2023 to 2025 (three witnesses).
- **Why most world months are `CANNOT_DETERMINE`:** 189 of the 293 carry `WIDE_INTERVAL`. **[HYPOTHESIS, not investigated]** the world's baseline range between p25 and p75 is narrow (about 10% around the median) against a relative error of about 6% from `kappa`, so `p_within` often stays below 0.8.
- **Reading the verdicts correctly:** `ABOVE_NORMAL` means the estimate is above the baseline p75 with at least 80% probability, not that it is an anomaly: about half of all months lie outside the middle half of their baseline by construction. Hotspots are not fires or burned area.
- **Reason codes, cell-months:** `SINGLE_WITNESS` 6,354,894; `INSUFFICIENT_BASELINE` 4,519,355; `AQUA_DRIFT_ERA` 1,687,140; `POOLED_CALIBRATION` 593,120; `WIDE_INTERVAL` 477,781; `OUTAGE` and `PROVISIONAL_NRT` 224,952 each; `DIURNAL_CAVEAT` 16,702; `WITNESS_DISAGREEMENT` 14,580.

**Indonesia 2015** (country, estimate and sd in Aqua-equivalent cell-days; baseline p25 / p50 / p75 of the same calendar month in 2003 to 2022):

| Month | Estimate (sd) | Baseline p25 / p50 / p75 | % of normal | `p_above` | Verdict |
|---|---|---|---|---|---|
| July | 4,229 (251) | 1,063 / 1,599 / 2,877 | 265 | 1.00 | `ABOVE_NORMAL` |
| August | 10,627 (633) | 2,551 / 4,908 / 8,121 | 217 | 1.00 | `ABOVE_NORMAL` |
| September | 19,069 (1,063) | 2,191 / 7,200 / 10,536 | 265 | 1.00 | `ABOVE_NORMAL` |
| October | 17,203 (947) | 1,698 / 3,177 / 4,601 | 542 | 1.00 | `ABOVE_NORMAL` |
| November | 3,039 (306) | 495 / 710 / 1,473 | 428 | 1.00 | `ABOVE_NORMAL` |
| December | 1,085 (73) | 144 / 215 / 275 | 504 | 1.00 | `ABOVE_NORMAL` |

Every month of the 2015 El Nino fire season is `ABOVE_NORMAL`, with no caveat code. (The case was not used to tune anything.) Over all 293 months Indonesia has 107 `WITHIN_NORMAL`, 62 `ABOVE_NORMAL`, 72 `BELOW_NORMAL` and 52 `CANNOT_DETERMINE`.

**A quiet control country, Germany:** 293 months: 207 `CANNOT_DETERMINE` (`WIDE_INTERVAL` 120, `INSUFFICIENT_BASELINE` 83 in the reason counts of the country), 32 `ABOVE_NORMAL`, 24 `BELOW_NORMAL`, 17 `WITHIN_NORMAL`, 13 `NO_DETECTED_ACTIVITY`. Even a quiet country gets above and below verdicts in 19% of its months, because the verdict compares with the middle half of the baseline.

**Limits [LIMITATION]:** the uncertainty of the baseline percentiles is not propagated (D-028); the products are in sample for `phi` and `kappa`; test D1 and the other validation tests are separate tasks.

### Raw-only products for the app (T-014a) **[VERIFIED 2026-11-14 unless labelled; replaced by the T-014 products above]**

`python pipeline/raw_only.py` writes `cell_month_harmonized.parquet`, `entity_month.parquet`, `metadata.json` and `validation_results.json` into `data/products/` (local, not committed), from `cell_month_witness.parquet` and `cells.parquet` (the final T-011 products). They have the exact shape of `docs/DATA_CONTRACT.md` v0.1.0 section 3, 4 and 7, so the API and app need no change. **They are not harmonized results**: every harmonized field is `null`, `witnesses_used` is `[]`, `n_witnesses` is 0, the verdict is `CANNOT_DETERMINE`, `reason_codes` is `["NOT_HARMONIZED"]` and `method_version` is `0.1.0-raw-only`. T-014 replaces them.

- **Cell level:** 16,477,734 rows, one per cell x month that has a witness row. `raw_combined_cell_days` is the sum of the `ALL` cell-days over every witness operating that month, **Terra included** (the contract's naive raw sum, as in the fixtures).
- **Entity level:** 68,562 rows over 293 months: 226 `COUNTRY` (`entity_id` = ISO3, name from `country_map.csv`), 7 `CONTINENT` (`AF AN AS EU NA OC SA`) and `GLOBAL`. `raw_by_witness` is a JSON map of the witnesses operating that month; `n_cells` is the number of cells of the entity. The 927 cells without a country (ocean) enter `GLOBAL` only: 29,031 cell-days in total.
- **Checks:** the `GLOBAL` total, the cell-level total and the independent fine-cell-days recount agree at 219,583,156; continents add up to countries at 219,554,125; `contract_check.py --real` passes. `data_level` is `SP` in 67,626 entity rows, `NRT` in 702 and `MIXED` in 234 (months where witnesses differ).
- **`metadata.json`:** `synthetic: false`; `first_month` 2002-07, `latest_month` 2026-11; `provisional_months` 2026-08 to 2026-11; `witnesses` Aqua, S-NPP and NOAA-20 (Terra is raw view only); `baseline_years` is empty because no baseline is computed; snapshot dates 2026-11-14 for the zips and for the API pull, from the modification times of the saved files.
- **Read the numbers correctly:** `raw_combined_cell_days` adds witnesses that see the same fire (Aqua, Terra and VIIRS), so it is not a measure of fire activity. The app must not show it as one.
- **Reason code [APPROVED, D-026, contract 0.1.1]:** every raw-only row has `reason_codes = ["NOT_HARMONIZED"]`. `metadata.json` and `validation_results.json` carry `contract_version` `0.1.1`.
- **Entity IDs [APPROVED, D-022, contract 0.1.1]:** ISO3 for countries, `AF AN AS EU NA OC SA` for continents, `GLOBAL`.
- **Checker:** `contract_check.py --real` requires `synthetic: false` and contract `0.1.1`, skips the SYNTHETIC test-id rules, and fails a raw-only row (`method_version` ending in `-raw-only`) without exactly `["NOT_HARMONIZED"]` and a harmonized row that carries it. The default mode accepts the fixtures (0.1.0 or 0.1.1).
- **Products in Git (D-027):** the five Parquet products are committed through Git LFS and `metadata.json` and `validation_results.json` as normal files, with the SHA-256 checksums in the PR.

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

### Map country boundaries, India point of view (T-085) **[VERIFIED 2026-11-15]**

The map's country outlines (hover, selection, anomaly outlines) use India's official boundary, so Jammu and Kashmir, Ladakh and Aksai Chin are drawn inside India. This is a display choice only: it changes no product value, verdict or cell attribution (cell attribution is T-086).

- **Source:** Natural Earth "Admin 0 countries, India point of view", 1:10m, file `geojson/ne_10m_admin_0_countries_ind.geojson` from the `nvkelso/natural-earth-vector` repository (branch `master`), https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_0_countries_ind.geojson. Downloaded 2026-11-15, 13,242,091 bytes, 248 features, SHA-256 `3e67a5a6ddeff3247ca8400cd2514fd4a5ac6e5432823b25d610a7028597d45f`. Public domain (Natural Earth terms of use, https://www.naturalearthdata.com/about/terms-of-use/).
- **Committed file:** `app/public/geo/ne_admin_0_countries_india_pov.geojson` (replaces `ne_110m_admin_0_countries.geojson`, the de facto line), 837,805 bytes, 243 features, SHA-256 `01fc884bf79d099abceee3be711529ccb20e17577d90a16287ccce82cc5b4769`.
- **Processing (mapshaper 0.7.101, run once with `npx`, not a project dependency):** keep the fields `ADMIN, NAME, NAME_LONG, SOVEREIGNT, ADM0_A3, ISO_A3, ISO_A3_EH, ISO_A2_EH`; `-simplify visvalingam keep-shapes 7.5%`; coordinates rounded to 0.001 degree. Then a small script merged five dependency fragments into their parent (Brazilian Island into Brazil, Clipperton into France, Ashmore and Cartier, Indian Ocean Territories and Coral Sea Islands into Australia) so that each `ISO_A3_EH` has one feature, and restored the `NAME` the 1:110m file had for countries in both files (six names).
- **Differences from the earlier 1:110m file:** India's outline reaches 37.05 N (was 35.49 N) and includes Jammu and Kashmir, Ladakh and Aksai Chin; Pakistan, China, Nepal, Bhutan, Bangladesh and Afghanistan follow the same line. Natural Earth's India view merges Western Sahara into Morocco, Kosovo into Serbia, Northern Cyprus into Cyprus and Somaliland into Somalia, so those four features and the id `ESH` are not in the file. 70 small states and territories that were not in the 1:110m file are added (for example Singapore, Maldives, Malta; 177 - 4 + 70 = 243). Six of the added polygons have no ISO code and cannot be selected: Dhekelia, Akrotiri, Guantanamo Bay, Bir Tawil, Spratly Islands, Scarborough Reef.

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

### India point-of-view boundary and the Jammu and Kashmir cells (T-086, D-033) **[VERIFIED 2026-11-15]**

- **File:** `ne_10m_admin_0_countries_ind.geojson`, Natural Earth Admin 0 Countries, India point of view, **version 5.1.1**, **1:10m**, 13,242,091 bytes (size matches the GitHub listing), **SHA-256 `3e67a5a6ddeff3247ca8400cd2514fd4a5ac6e5432823b25d610a7028597d45f`**. Source: `https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_10m_admin_0_countries_ind.geojson` (repository `nvkelso/natural-earth-vector`; Natural Earth data are public domain). Downloaded on 2026-11-15 with the user's approval into an empty folder outside the repository (`C:/IgnisLine-data/ne_ind/`).
- **Why this file:** the Lead decided (D-033, PR #74) to follow India's official boundary. Natural Earth publishes its point-of-view country files at **1:10m only**: there is no `ne_50m_admin_0_countries_ind` (checked 2026-11-15 on the Natural Earth downloads page and in the repository, `50m_cultural/` and `geojson/`; a direct request returned 404).
- **LIMITATION, resolution mix:** the country mapping of T-009 uses the **1:50m** default boundary (version 5.1.1); this boundary is **1:10m** and more detailed. To keep the change local, only the cells in the box 72.5 to 80.5 degrees E and 32.5 to 37.2 degrees N are changed; other differences are reported, not applied.
- **Rule** (`pipeline/kashmir_cells.py`): a cell in the box is reassigned to India if its **centre** lies inside the India polygon (ADM0_A3 = IND; even-odd ray casting over every ring, no new dependency) and its current country is Pakistan or China. A cell with no country is not given one. `cell_id`, the grid, `continent` (Asia for all three countries), `fire_region` and `stratum_id` are unchanged (the stratum is a 2.5 degree block inside a fire region, not a country), so the calibration is unaffected.
- **Result [VERIFIED, `data/interim/qa/kashmir_cells.json`]:** the box holds 109 cells before (Pakistan 42, China 27, India 39, no country 1). **32 cells are reassigned to India: 26 from Pakistan and 6 from China.** After: India 1,221 cells (was 1,189), Pakistan 294 (was 320), China 3,285 (was 3,291). The other Pakistan and China cells of the box are not inside India's boundary (Pakistan proper, Xinjiang) and stay.
- **Reported, not changed:** 0 Indian cells in the box have a centre outside the India polygon. **12 cells outside the box** have a centre inside India's 1:10m polygon but another country in FIRMS (Pakistan 4 along the southern India-Pakistan border, Nepal 4, Bangladesh 2, Bhutan 1, Myanmar 1: the 1:10m border differs from FIRMS's attribution); **2 cells with no country** lie inside India's polygon (centres 79.25E 35.75N and 68.25E 23.75N).
- **Products changed (Git LFS):** `data/products/cells.parquet` (only `country_iso3` of the 32 cells) and the IND, PAK and CHN COUNTRY rows of `data/products/entity_month.parquet` (879 rows), computed by the same code (`verdicts.entity_month`) on the new cells. Every other row of `entity_month` (all other countries, continents, the world: 67,683 rows) is **the row of `main`**, verified equal. A full recomputation of those rows agrees with `main` to float rounding: the largest relative difference of a probability is 2.8e-7 where the value itself is below 1e-14; of the estimate 2.0e-15. Raw cell-days summed over IND, PAK and CHN are equal in every one of the 293 months (cells only moved between them). New SHA-256: `cells.parquet` `decd81e6d32c046fb004cdf2f7dc52c4ea0fd52c22d4398e9842662209c6558d`, `entity_month.parquet` `1d8bf0bf4ffe0948870da9f3e6b9ebabf469833866f2142d31babd97ee921195`.
- **Effect on the rows:** `n_cells` IND 1,221 (was 1,189), PAK 294 (320), CHN 3,285 (3,291). Verdicts change in 22 country-months: IND 7, PAK 15, CHN 0 (CANNOT_DETERMINE to ABOVE_NORMAL 6, to BELOW_NORMAL 3, to WITHIN_NORMAL 7; ABOVE_NORMAL, BELOW_NORMAL and WITHIN_NORMAL (4) to CANNOT_DETERMINE 1, 1 and 4). Details in `docs/validation/T-086-kashmir-cells.md`.
- **LIMITATION, not regenerated:** `cell_month_harmonized.parquet` keeps its values (the Lead's scope). Its cell-level caveat `DIURNAL_CAVEAT` (India, October and November from 2020, D-028) is set from the cell's country when the cell table is built, so the 32 reassigned cells do not carry it in that table until it is regenerated (the IND entity rows carry it). A caveat never changes a verdict or a value.

## 7. Update strategy

- Historical zips are downloaded once, and the snapshot date is recorded in `metadata.json`.
- 2026 is pulled through the API at build time. Months younger than the SP lag are marked provisional.
- A rebuild re-pulls 2026 and recomputes products. Calibration does **not** change unless `method_version` changes.

## 8. Acknowledgement and terms

FIRMS asks users to acknowledge FIRMS, LANCE and ESDIS when sharing data. Data are provided "as is". See the README.

## 9. Source links shown in the interface (T-076) **[VERIFIED 2026-11-15]**

The app shows its sources (map footer, per-month source line, chart and calendar captions, featured stories). Every link comes from this table; no other URL, version or date is shown. **Verification:** each URL was requested on 2026-11-15 and answered HTTP 200 (the DOI links after redirecting to the NASA Earthdata catalogue page). The DOIs and product names are the ones in `SP_DOIS` and `NRT_DOIS` in `api/fire_api/export.py` (the CSV header block).

| Shown as | Product (standard, SP) | Link |
|---|---|---|
| NASA FIRMS | FIRMS, the service that distributes the detections | https://www.earthdata.nasa.gov/data/tools/firms |
| FIRMS FAQ (SP and NRT levels) | Product levels, latency, record dates (sections 3 and 4) | https://www.earthdata.nasa.gov/data/tools/firms/faq |
| MODIS Collection 6.1 | MODIS/Aqua MYD14 V061, DOI 10.5067/MODIS/MYD14.061 | https://doi.org/10.5067/MODIS/MYD14.061 |
| VIIRS 375 m S-NPP | VIIRS/NPP VNP14IMG V002, DOI 10.5067/VIIRS/VNP14IMG.002 | https://doi.org/10.5067/VIIRS/VNP14IMG.002 |
| VIIRS 375 m NOAA-20 | VIIRS/JPSS1 VJ114IMG V002, DOI 10.5067/VIIRS/VJ114IMG.002 | https://doi.org/10.5067/VIIRS/VJ114IMG.002 |

Near-real-time products (recent months, provisional): MODIS MCD14DL NRT, DOI 10.5067/FIRMS/MODIS/MCD14DL.NRT.0061; VIIRS S-NPP VNP14IMGT NRT, DOI 10.5067/FIRMS/VIIRS/VNP14IMGT_NRT.002; VIIRS NOAA-20 VJ114IMGT NRT, DOI 10.5067/FIRMS/VIIRS/VJ114IMGT_NRT.002 (all three resolve as above with the `https://doi.org/` prefix).

**What the interface states about the data** (from `data/products/metadata.json`, never typed by hand): the first and latest month, the provisional months (near-real-time, may change when science-quality data arrive), the analysis grid (`grid.analysis_deg`, 0.5 degrees, D-009), the method version (0.1.0) and the snapshot dates. "MODIS Collection 6.1" is the product version of the DOIs above (V061); the `version` column of the detections carries finer labels (`6.2`, `6.03`, `61.03`, `6.1NRT`, section 1).
