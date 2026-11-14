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
- **Row count [ESTIMATE]:** ≈475 million detections, derived from typical line length. To be measured during ingestion (T-005).

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

FIRMS country names (e.g. `Democratic_Republic_of_the_Congo`, `Russian_Federation`) must be mapped to ISO3 codes (task T-009).

## 7. Update strategy

- Historical zips are downloaded once, and the snapshot date is recorded in `metadata.json`.
- 2026 is pulled through the API at build time. Months younger than the SP lag are marked provisional.
- A rebuild re-pulls 2026 and recomputes products. Calibration does **not** change unless `method_version` changes.

## 8. Acknowledgement and terms

FIRMS asks users to acknowledge FIRMS, LANCE and ESDIS when sharing data. Data are provided "as is". See the README.
