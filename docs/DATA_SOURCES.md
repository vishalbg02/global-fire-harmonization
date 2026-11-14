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
