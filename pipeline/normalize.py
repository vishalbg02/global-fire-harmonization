"""Unzip and normalize FIRMS detections to one Parquet schema (T-003).

Reads the global yearly zips (data/raw/zips) and the 2026 API CSVs (data/raw/api_2026)
and writes data/interim/detections/sensor=<S>/year=<YYYY>/detections.parquet.

Nothing is filtered, de-duplicated or dropped. A value that cannot be cast becomes null
and is counted, never silently coerced. One sensor-year is processed at a time: unzip,
convert, verify, delete the CSVs.

    python pipeline/normalize.py                    # everything not yet done
    python pipeline/normalize.py --only modis:2002  # one zip (use api:2026 for the API data)
    python pipeline/normalize.py --force            # redo finished sensor-years
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "interim" / "detections"
TMP = ROOT / "data" / "interim" / "_extract"
DB_TMP = ROOT / "data" / "interim" / "_duckdb_tmp"

# zip prefix -> (sensor, years)
ARCHIVES = {
    "modis": ("MODIS", range(2002, 2026)),
    "viirs-snpp": ("VIIRS_SNPP", range(2012, 2026)),
    "viirs-jpss1": ("VIIRS_NOAA20", range(2018, 2026)),
}
API_SOURCES = {"MODIS": ["MODIS_SP", "MODIS_NRT"], "VIIRS_SNPP": ["VIIRS_SNPP_SP", "VIIRS_SNPP_NRT"],
               "VIIRS_NOAA20": ["VIIRS_NOAA20_SP", "VIIRS_NOAA20_NRT"]}
API_YEAR = 2026
REQUIRED = ["latitude", "longitude", "scan", "track", "acq_date", "acq_time", "satellite", "confidence", "version", "frp", "daynight"]
OPTIONAL = ["type"]
IGNORED = ["brightness", "bright_t31", "bright_ti4", "bright_ti5", "instrument"]  # not in the unified schema
EXPECTED_SATELLITES = {"MODIS": {"Terra", "Aqua"}, "VIIRS_SNPP": {"N"}, "VIIRS_NOAA20": {"N20"}}
SCHEMA = ["sensor", "satellite", "lat", "lon", "acq_date", "acq_time_utc", "daynight", "confidence_class", "confidence_raw",
          "frp_mw", "scan_km", "track_km", "type", "version", "country_name", "data_level"]


@dataclass
class Paths:
    raw: Path = RAW
    out: Path = OUT
    tmp: Path = TMP
    db_tmp: Path = DB_TMP


def confidence_class_sql(sensor: str) -> str:
    if sensor == "MODIS":
        n = "TRY_CAST(confidence AS INTEGER)"
        return f"CASE WHEN {n} IS NULL THEN NULL WHEN {n} < 30 THEN 'LOW' WHEN {n} < 80 THEN 'NOMINAL' ELSE 'HIGH' END"
    return ("CASE lower(trim(confidence)) WHEN 'l' THEN 'LOW' WHEN 'n' THEN 'NOMINAL' WHEN 'h' THEN 'HIGH' ELSE NULL END")


def extract_csvs(zip_path: Path, dest: Path) -> int:
    """Extract only the *.csv members of an untrusted zip into a fresh folder (flat, base names only)."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    n = 0
    with zipfile.ZipFile(zip_path) as z:
        for info in z.infolist():
            name = Path(info.filename).name
            if info.is_dir() or not name.lower().endswith(".csv") or ".." in name:
                continue
            with z.open(info) as src, open(dest / name, "wb") as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
            n += 1
    return n


def convert(con: duckdb.DuckDBPyConnection, sensor: str, year: int, csv_source: str, kind: str, out_dir: Path) -> dict:
    """Convert all CSVs of one sensor-year into one Parquet file. csv_source is an SQL literal: a quoted glob or a list of them."""
    con.execute("DROP TABLE IF EXISTS stage")
    con.execute(f"CREATE TABLE stage AS SELECT * FROM read_csv({csv_source}, header=true, all_varchar=true, "
                "union_by_name=true, filename=true)")
    cols = [r[0] for r in con.execute("DESCRIBE stage").fetchall()]
    missing = [c for c in REQUIRED if c not in cols]
    if missing:
        raise RuntimeError(f"{sensor} {year}: missing expected columns {missing}")
    known = set(REQUIRED + OPTIONAL + IGNORED + ["filename"])
    unexpected = sorted(set(cols) - known)
    type_sql = "TRY_CAST(type AS SMALLINT)" if "type" in cols else "CAST(NULL AS SMALLINT)"
    raw_type = "type" if "type" in cols else "CAST(NULL AS VARCHAR)"
    if kind == "zip":
        country = "replace(regexp_extract(filename, '_[0-9]{4}_(.+)[.]csv$', 1), '_', ' ')"
        level = "'SP'"
    else:
        country = "CAST(NULL AS VARCHAR)"
        level = "CASE WHEN regexp_matches(filename, '_NRT[/\\\\]') THEN 'NRT' ELSE 'SP' END"
    cls = confidence_class_sql(sensor)
    select = f"""SELECT '{sensor}' AS sensor, satellite,
        TRY_CAST(latitude AS DOUBLE) AS lat, TRY_CAST(longitude AS DOUBLE) AS lon,
        TRY_CAST(acq_date AS DATE) AS acq_date, TRY_CAST(acq_time AS INTEGER) AS acq_time_utc,
        daynight, {cls} AS confidence_class, confidence AS confidence_raw,
        TRY_CAST(frp AS DOUBLE) AS frp_mw, TRY_CAST(scan AS DOUBLE) AS scan_km, TRY_CAST(track AS DOUBLE) AS track_km,
        {type_sql} AS type, version, {country} AS country_name, {level} AS data_level
        FROM stage"""
    rows_csv, files = con.execute("SELECT count(*), count(DISTINCT filename) FROM stage").fetchone()
    # values that exist in the CSV but cannot be cast (they become null in the Parquet and are counted here)
    bad = con.execute(f"""SELECT
        count(*) FILTER (WHERE latitude IS NOT NULL AND TRY_CAST(latitude AS DOUBLE) IS NULL),
        count(*) FILTER (WHERE longitude IS NOT NULL AND TRY_CAST(longitude AS DOUBLE) IS NULL),
        count(*) FILTER (WHERE acq_date IS NOT NULL AND TRY_CAST(acq_date AS DATE) IS NULL),
        count(*) FILTER (WHERE acq_time IS NOT NULL AND TRY_CAST(acq_time AS INTEGER) IS NULL),
        count(*) FILTER (WHERE frp IS NOT NULL AND TRY_CAST(frp AS DOUBLE) IS NULL),
        count(*) FILTER (WHERE scan IS NOT NULL AND TRY_CAST(scan AS DOUBLE) IS NULL),
        count(*) FILTER (WHERE track IS NOT NULL AND TRY_CAST(track AS DOUBLE) IS NULL),
        count(*) FILTER (WHERE {raw_type} IS NOT NULL AND {type_sql} IS NULL),
        count(*) FILTER (WHERE confidence IS NOT NULL AND ({cls}) IS NULL),
        count(*) FILTER (WHERE latitude IS NULL OR longitude IS NULL OR acq_date IS NULL OR acq_time IS NULL),
        count(*) FILTER (WHERE TRY_CAST(acq_date AS DATE) IS NOT NULL AND year(TRY_CAST(acq_date AS DATE)) <> {year})
        FROM stage""").fetchone()
    names = ["latitude", "longitude", "acq_date", "acq_time", "frp", "scan", "track", "type", "confidence",
             "rows_with_a_missing_key_field", "acq_date_outside_partition_year"]
    problems = dict(zip(names, (int(b) for b in bad), strict=True))
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_file = out_dir / "detections.parquet.tmp"
    con.execute(f"COPY ({select}) TO '{tmp_file.as_posix()}' (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 1000000)")
    rows_pq = con.execute(f"SELECT count(*) FROM read_parquet('{tmp_file.as_posix()}')").fetchone()[0]
    if rows_pq != rows_csv:
        tmp_file.unlink()
        raise RuntimeError(f"{sensor} {year}: {rows_csv} rows read but {rows_pq} written")
    sats = dict(con.execute("SELECT satellite, count(*) FROM stage GROUP BY 1").fetchall())
    stats = {"sensor": sensor, "year": year, "source_files": int(files), "rows_csv": int(rows_csv), "rows_parquet": int(rows_pq),
             "cast_problems": problems, "unexpected_columns": unexpected,
             "satellites_unexpected": sorted(set(sats) - EXPECTED_SATELLITES[sensor]), "rows_by_satellite": sats}
    tmp_file.replace(out_dir / "detections.parquet")
    (out_dir / "stats.json").write_text(json.dumps(stats, indent=2, default=str), encoding="utf-8")
    con.execute("DROP TABLE stage")
    return stats


def connect(paths: Paths) -> duckdb.DuckDBPyConnection:
    paths.db_tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(paths.db_tmp / "work.duckdb"))
    con.execute(f"SET temp_directory='{paths.db_tmp.as_posix()}'")
    con.execute("SET memory_limit='6GB'")
    return con


def part_dir(paths: Paths, sensor: str, year: int) -> Path:
    return paths.out / f"sensor={sensor}" / f"year={year}"


def done(paths: Paths, sensor: str, year: int) -> bool:
    d = part_dir(paths, sensor, year)
    return (d / "detections.parquet").exists() and (d / "stats.json").exists()


def run_zip(paths: Paths, prefix: str, year: int, con: duckdb.DuckDBPyConnection, force: bool = False) -> dict | None:
    sensor = ARCHIVES[prefix][0]
    if done(paths, sensor, year) and not force:
        return None
    zip_path = paths.raw / "zips" / f"{prefix}_{year}_all_countries.zip"
    work = paths.tmp / f"{prefix}_{year}"
    try:
        n = extract_csvs(zip_path, work)
        if n == 0:
            raise RuntimeError(f"{zip_path.name}: no CSV members")
        return convert(con, sensor, year, f"'{(work / '*.csv').as_posix()}'", "zip", part_dir(paths, sensor, year))
    finally:
        shutil.rmtree(work, ignore_errors=True)  # the CSVs are deleted as soon as the year is done


def run_api(paths: Paths, sensor: str, con: duckdb.DuckDBPyConnection, force: bool = False) -> dict | None:
    if done(paths, sensor, API_YEAR) and not force:
        return None
    base = paths.raw / "api_2026"
    present = [s for s in API_SOURCES[sensor] if (base / s).is_dir()]
    if not present:
        return None
    # all segments (SP and NRT) of one sensor go into one partition; data_level comes from the source folder
    source = "[" + ", ".join(f"'{(base / src).as_posix()}/*.csv'" for src in present) + "]"
    return convert(con, sensor, API_YEAR, source, "api", part_dir(paths, sensor, API_YEAR))


def write_counts(paths: Paths) -> Path:
    """Row counts per sensor, year, satellite and data level, read back from the Parquet files."""
    con = duckdb.connect()
    pattern = (paths.out / "sensor=*" / "year=*" / "detections.parquet").as_posix()
    rows = con.execute(f"""SELECT sensor, CAST(year AS INTEGER) AS year, satellite, data_level, count(*) AS rows
        FROM read_parquet('{pattern}', hive_partitioning=true) GROUP BY ALL ORDER BY sensor, year, satellite, data_level""").fetchall()
    path = paths.out / "row_counts.tsv"
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("sensor\tyear\tsatellite\tdata_level\trows\n")
        f.writelines("\t".join(map(str, r)) + "\n" for r in rows)
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="e.g. modis:2002 or api:2026")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    paths = Paths()
    free = shutil.disk_usage(paths.out.parent if paths.out.parent.exists() else ROOT).free
    print(f"free disk: {free / 1e9:.1f} GB", flush=True)
    con = connect(paths)
    jobs: list[tuple[str, str, int]] = [(p, "zip", y) for p, (_, ys) in ARCHIVES.items() for y in ys]
    jobs += [(s, "api", API_YEAR) for s in API_SOURCES]
    if args.only:
        key, _, yr = args.only.partition(":")
        jobs = [j for j in jobs if (j[1] == "zip" and j[0] == key and j[2] == int(yr)) or (key == "api" and j[1] == "api")]
    for name, kind, year in jobs:
        t0 = time.time()
        try:
            stats = run_zip(paths, name, year, con, args.force) if kind == "zip" else run_api(paths, name, con, args.force)
        except Exception as e:  # noqa: BLE001  record and continue with the next sensor-year
            print(f"FAIL {name} {year}: {e}", flush=True)
            continue
        if stats is None:
            print(f"skip {name} {year} (done)", flush=True)
            continue
        flag = "" if not any(stats["cast_problems"].values()) and not stats["unexpected_columns"] else "  (see stats.json)"
        print(f"OK   {stats['sensor']} {year}: {stats['rows_parquet']:,} rows, {stats['source_files']} files, "
              f"{time.time() - t0:.0f}s{flag}", flush=True)
    print("counts:", write_counts(paths), flush=True)


if __name__ == "__main__":
    main()
