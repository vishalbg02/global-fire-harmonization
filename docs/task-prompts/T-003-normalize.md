# Task prompt: T-003 Unzip and normalize to the unified schema (Parquet)

> Prepared for: Member 2 · Date: 2026-11-14 · Based on main @ 53e3c46
> Source of truth: docs/TASK_TRACKER.md row T-003. This prompt adds no scope beyond it.

## 1. Project context
NASA Space Apps Challenge 2026 team project (Many Witnesses + Witness Stand): harmonize NASA FIRMS hotspot detections from several satellites (`docs/PROJECT_PLAN.md`). T-001 downloaded the 46 global yearly zips and T-002 pulled the 2026 API data. T-003 turns all of it into one normalized detections table that later tasks (T-005 filters and QA, T-006 gridding, T-009 country mapping) read.

## 2. Task objective
Every detection row from the 46 zips and the 2026 API files is stored in `data/interim/detections/` as Parquet, partitioned by sensor and year, in one unified schema. Row counts per sensor, year and satellite are recorded and checked (rows read from the CSVs equal rows written to Parquet). Nothing is filtered, de-duplicated, interpolated or dropped.

## 3. Assigned responsibility
- Task ID / priority: T-003 / P0
- Owner: Member 2 (Data Engineering & Scientific Analysis)
- Reviewer and merger: Member 1 (Project Lead)
- Dependencies (must be MERGED first): T-001 (merged), T-0A, T-0D (done)

## 4. Relevant files and directories
- Read: the assistant instructions file at the repository root, `docs/DATA_SOURCES.md`, `docs/prompts/MEMBER_2_DATA_SCIENCE_PROMPT.md` §5–8, `data/README.md`
- Create/modify:
  - `docs/task-prompts/T-003-normalize.md` (this file)
  - `pipeline/normalize.py`
  - `pipeline/tests/test_normalize.py`
  - `docs/DATA_SOURCES.md` (measured row counts only)
  - `data/README.md` (Snapshot record row only)
  - `docs/TASK_TRACKER.md` (row T-003 only)
- Not committed: everything under `data/interim/`

## 5. Approved technologies
Python 3.12–3.14 and DuckDB 2.0.0 (out-of-core CSV to Parquet), pyarrow for checks, pytest (`docs/TECH_STACK.md`, D-008).

## 6. Architecture and data contract
No contract product is produced here. The normalized schema is the one in the Member 2 prompt §7. Partitioning follows the Member 2 prompt: `data/interim/detections/sensor=<S>/year=<YYYY>/`.

## 7. Inputs
- `data/raw/zips/{modis,viirs-snpp,viirs-jpss1}_{YYYY}_all_countries.zip` (46 files from T-001).
- `data/raw/api_2026/{SOURCE}/{YYYY-MM-DD}_{DAYS}.csv` (193 files from T-002).
- No key is needed. The zips are treated as untrusted data: each is extracted into its own empty folder and only `*.csv` members are read.

## 8. Expected outputs
- `data/interim/detections/sensor={MODIS|VIIRS_SNPP|VIIRS_NOAA20}/year={YYYY}/detections.parquet`.
- `data/interim/detections/row_counts.tsv`: sensor, year, satellite, data_level, rows, source files, cast problems.
- Row counts per sensor and year in `docs/DATA_SOURCES.md` and in the PR description.
- Schema: `sensor, satellite, lat, lon, acq_date, acq_time_utc, daynight, confidence_class (LOW|NOMINAL|HIGH), confidence_raw, frp_mw, scan_km, track_km, type (nullable), version, country_name (null for API rows), data_level (SP|NRT)`.

## 9. Implementation requirements
1. One sensor-year at a time: unzip, convert to Parquet, delete that year's CSVs.
2. Header check per file: all expected columns present; unexpected columns recorded, not silently ignored. `type` is absent in NRT files and becomes null.
3. No silent coercion: a value that cannot be cast to its type becomes null **and is counted** in `row_counts.tsv`. Rows are never dropped.
4. `confidence_class`: MODIS numeric confidence below 30 LOW, 30 to 79 NOMINAL, 80 or more HIGH; VIIRS `l`/`n`/`h` to LOW/NOMINAL/HIGH. `confidence_raw` keeps the original text.
5. `version` stays text (values like `6.03` and `61.03` must not be re-formatted). `acq_time_utc` keeps the FIRMS HHMM value as an integer, unchanged (UTC).
6. `country_name` is the country in the file name with underscores replaced by spaces (mapping to ISO3 is T-009). Null for API rows.
7. `data_level` is `SP` for the archive zips; for API rows it comes from the source (`*_SP` or `*_NRT`).
8. Verify, per sensor-year, that rows read from the CSVs equal rows in the Parquet file; fail loudly otherwise.
9. Re-running is idempotent: finished sensor-years are skipped unless forced.
10. Check free disk space before starting.

## 10. Constraints: do not modify
- Do not change the tech stack, architecture, scientific methodology or data contract.
- Do not edit files outside §4 "Create/modify". Do not touch `api/` or `app/`.
- No secrets, no data files, no direct pushes to `main`, no self-merge.
- No filtering, de-duplication, static-source masking, country mapping or QA (T-005, T-009). Do not drop MODIS rows by `version` (T-007).

## 11. Acceptance criteria
Row counts per sensor and year recorded.

## 12. Required tests
`python -m pytest pipeline/tests/test_normalize.py -q` on small synthetic CSV zips built in the test: schema and types, confidence classes, `version` kept as text, NRT without `type`, null counting for bad values, rows read equal rows written, idempotent re-run. `ruff` passes on the files of this task. Then the full run, with row counts per sensor-year.

## 13. Documentation updates
`docs/TASK_TRACKER.md` row T-003; `data/README.md` snapshot row; `docs/DATA_SOURCES.md` measured row counts.

## 14. Git branch and PR instructions
- Branch: `data/T-003-normalize` created from the latest `main`
- First commit: this prompt file
- Open a DRAFT PR early; title "T-003: Unzip and normalize to the unified schema (Parquet)"; fill in `.github/pull_request_template.md`
- Never merge; wait for the Project Lead
- Commit with your own Git identity (D-020)

## 15. Out-of-scope or blocking issues
- The tracker shows T-003 as `TODO` until the Lead's assignment PR is merged; work started on Member 2's go-ahead. The Lead should confirm.
- `data/interim` is a local directory junction to a folder outside OneDrive (not committed).
- DuckDB 2.0.0 was installed locally with pip as the approved stack states; there is no pinned `requirements.txt` yet.
