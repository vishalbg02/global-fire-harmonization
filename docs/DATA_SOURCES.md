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
- **Unzipped size [ESTIMATE]:** about 4.5× expansion, measured on 2020 (MODIS 78 MB → 350 MB; S-NPP 368 MB → 1,625 MB). Total ≈41 GB.
- **Row count [VERIFIED 2026-11-14, T-003]:** 546,469,853 detections in the 46 zips (the earlier estimate was ≈475 million), before any filtering. Per sensor and year: see "Row counts per sensor and year" below.

### Columns [VERIFIED 2026-11-14 from file headers]

- **MODIS:** `latitude, longitude, brightness, scan, track, acq_date, acq_time, satellite, instrument, confidence, version, bright_t31, frp, daynight, type`
- **VIIRS:** `latitude, longitude, bright_ti4, scan, track, acq_date, acq_time, satellite, instrument, confidence, version, bright_ti5, frp, daynight, type`
- Field notes:
  - `satellite`: `Terra`, `Aqua`, `N` (S-NPP), `N20` (NOAA-20).
  - `acq_time`: HHMM in **UTC**.
  - MODIS `confidence`: 0–100. VIIRS `confidence`: `l`, `n` or `h`.
  - `type` (archive data only): 0 = presumed vegetation fire, 1 = active volcano, 2 = other static land source, 3 = offshore.
- **Data-quality question [OPEN, T-007]:** the MODIS `version` field varies (`6.2` in 2012, `6.03` in 2020, `61.03` in 2025).
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
| GFED basis regions (14 fire regions) | Pooling parent in calibration | globalfiredata.org. **Access to be verified (T-004)**. Fallback: UN geoscheme subregions mapped from country names |

FIRMS country names (e.g. `Democratic_Republic_of_the_Congo`, `Russian_Federation`) are mapped to ISO3 codes and continents in `pipeline/country_map.csv` (task T-009).

### Country name mapping (T-009) **[VERIFIED 2026-11-14]**

- **Coverage:** all 238 distinct country names in the normalized detections (T-003) are mapped (100%). The check `python pipeline/country_mapping.py check` fails if a name is missing from the table or the table has a name the data lacks.
- **Source of the codes:** Natural Earth 1:50m admin-0 countries, version 5.1.1 (`ne_50m_admin_0_countries.zip`, 799,734 bytes, SHA-256 `5fed433373581fa648920435f937d95f2d3c0200e067409c6478dcdf1b853139`, downloaded 2026-11-14; only the attribute table is read, the file is not committed). 219 names matched by name; 19 were resolved by hand, each with a note in the table.
- **Continent codes:** `AF`, `AN`, `AS`, `EU`, `NA`, `OC`, `SA`. `AN` is included because the data has detections in Antarctica. Continents follow Natural Earth (so Russia is `EU`, Turkey, Cyprus, Georgia and Kazakhstan are `AS`). Where Natural Earth says "Seven seas (open ocean)", the UN M49 region is used.
- **Needs Lead approval:** Kosovo has no ISO 3166-1 code, so the user-assigned `XKX` is used. `UMI` (United States Minor Outlying Islands) is `OC`. The continent policy for transcontinental countries and ocean territories above.
- Territories keep their own code (Greenland `GRL`, Hong Kong `HKG`, Norfolk Island `NFK`); they are not merged into their sovereign state. Codes in common use are used for disputed territories (Palestine `PSE`, Taiwan `TWN`); this is not a political statement.

## 7. Update strategy

- Historical zips are downloaded once, and the snapshot date is recorded in `metadata.json`.
- 2026 is pulled through the API at build time. Months younger than the SP lag are marked provisional.
- A rebuild re-pulls 2026 and recomputes products. Calibration does **not** change unless `method_version` changes.

## 8. Acknowledgement and terms

FIRMS asks users to acknowledge FIRMS, LANCE and ESDIS when sharing data. Data are provided "as is". See the README.
