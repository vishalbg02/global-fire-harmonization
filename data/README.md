# Data directory

**Committed:** this README, small `SYNTHETIC` fixtures in `data/fixtures/`, and the contract products in `data/products/` **through Git LFS** (D-027). **Never committed:** the NASA raw archives (`data/raw/`, about 9.7 GB zipped) and interim files (`data/interim/`, about 6.3 GB). They are re-downloaded or regenerated.

## Planned layout (proposed; final names depend on the approved stack)

```
data/
├── README.md        ← this file (committed)
├── fixtures/        ← small SYNTHETIC samples matching docs/DATA_CONTRACT.md (committed, <5 MB)
├── raw/             ← downloaded FIRMS zips and 2026 API CSVs (ignored)
│   ├── zips/
│   └── api_2026/
├── interim/         ← normalized detections, Parquet by sensor/year (ignored)
└── products/        ← contract products: cells, cell_month_*, entity_month, calibration,
                       validation_results.json, metadata.json (committed; *.parquet via Git LFS)
```

## How to obtain the raw data

1. **Historical (2002–2025), no login.** One zip per sensor per year:
   ```
   https://firms.modaps.eosdis.nasa.gov/data/country/zips/modis_{YYYY}_all_countries.zip        (2000–2025)
   https://firms.modaps.eosdis.nasa.gov/data/country/zips/viirs-snpp_{YYYY}_all_countries.zip   (2012–2025)
   https://firms.modaps.eosdis.nasa.gov/data/country/zips/viirs-jpss1_{YYYY}_all_countries.zip  (2018–2025, NOAA-20)
   ```
   Save them to `data/raw/zips/`. Expected total ≈9.1 GB (per-year sizes are in `docs/DATA_SOURCES.md`).
2. **2026 (Jan → present).** FIRMS area API with your MAP_KEY from `.env` (`FIRMS_MAP_KEY`). Use area `world` and 5-day windows; sources `MODIS_SP`/`MODIS_NRT`, `VIIRS_SNPP_SP`/`_NRT` (S-NPP ends 2026-11-02), `VIIRS_NOAA20_SP`/`_NRT`. Save to `data/raw/api_2026/`.
3. **Outages and availability:** the FIRMS `missing_data` and `data_availability` endpoints.

## Sharing products within the team

Products are committed to `data/products/` through **Git LFS** (D-027), so a normal `git pull` brings them.

1. Once per machine: install Git LFS (macOS `brew install git-lfs`; Windows: included with Git for Windows) and run `git lfs install`.
2. Member 2 regenerates the products and commits them in the task's PR with `git add data/products/...`. `.gitattributes` sends every `data/products/**/*.parquet` file to LFS automatically. Check with `git lfs ls-files` before pushing.
3. Post SHA-256 checksums in the PR (`shasum -a 256 data/products/*` on macOS/Linux, `certutil -hashfile <file> SHA256` on Windows).
4. Everyone else runs `git pull` (and `git lfs pull` if a file shows as a small pointer).
5. Every regenerated version stays in LFS history and counts against the account's LFS storage and bandwidth quota. Commit products only when they change, and check the quota on GitHub's billing page.

Record the snapshot date of every download in `docs/DATA_SOURCES.md` and in `metadata.json`.

## Snapshot record

| Item | Date downloaded | By | Notes |
|---|---|---|---|
| Global zips | 2026-11-14 | Member 2 | 46 of 46 zips (MODIS 2002–2025, S-NPP 2012–2025, NOAA-20 2018–2025); 9,715,095,351 bytes (≈9.05 GiB); every size matched the server Content-Length and every zip passed the CRC test; SHA-256 manifest kept outside Git |
| 2026 API pull | 2026-11-14 | Member 2 | World, 5-day windows from 2026-01-01: MODIS and NOAA-20 to 2026-11-14, S-NPP to 2026-11-02. 193 segments, 35,580,721 detection rows, no date gaps. SP up to the SP end date in `data_availability`, NRT after it. `data_availability` and `missing_data` responses saved in `data/raw/availability/` |
| Normalized detections | 2026-11-14 | Member 2 | 582,050,574 rows (46 zips + 2026 API) in `data/interim/detections/`, partitioned by sensor and year; rows read equal rows written for all 49 sensor-years; no filtering. Output ≈6.3 GB |
