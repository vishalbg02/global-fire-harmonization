"""Grid the detections: fine-cell-days to analysis cell-months per witness and day/night (T-006).

Builds two products under data/products/ (local, not committed), as in docs/DATA_CONTRACT.md v0.1.0:

  cells.parquet               one row per 0.5 degree analysis cell with at least one kept detection
  cell_month_witness.parquet  one row per cell x month x witness x daynight (D, N, ALL = D + N) for every
                              month the witness operated, with cell_days = 0 where nothing was detected

Grids (D-009, locked at G1): analysis 0.5 degrees, fine 0.05 degrees. A fine cell belongs to the
analysis cell that holds its centre, which for these sizes is simply (fine row // 10, fine column // 10).

Kept detections: confidence MODIS 30 or more and VIIRS n or h; type 0 for SP rows (NRT rows have no type);
and not in the approved static-source mask (applied to every row, as in the D-009 test).

    python pipeline/gridding.py build      # writes both products (about 10 to 20 minutes)
    python pipeline/gridding.py validate   # contract and integrity checks on the products
"""
from __future__ import annotations

import argparse
import calendar
import csv
import datetime as dt
import json
import math
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
FINE = 0.05
ANALYSIS = 0.5
RATIO = round(ANALYSIS / FINE)  # fine cells per analysis cell along one axis (10)
RECORD_START = dt.date(2002, 7, 1)
WITNESS = {"Aqua": "AQUA_MODIS", "Terra": "TERRA_MODIS", "N": "SNPP_VIIRS", "N20": "NOAA20_VIIRS"}
MISSING_NAMES = {"Aqua (MODIS)": "AQUA_MODIS", "Terra (MODIS)": "TERRA_MODIS", "Suomi NPP (VIIRS)": "SNPP_VIIRS",
                 "NOAA-20 (VIIRS)": "NOAA20_VIIRS"}
EARTH_RADIUS_KM = 6371.0088


@dataclass
class Paths:
    detections: Path = ROOT / "data" / "interim" / "detections"
    mask: Path = ROOT / "data" / "interim" / "qa" / "static_mask_fine0.05_share0.5_min10.parquet"
    fire_regions: Path = ROOT / "data" / "interim" / "fire_regions" / "fire_region_g050.parquet"
    country_map: Path = ROOT / "pipeline" / "country_map.csv"
    missing_json: Path | None = None  # default: the newest data/raw/availability/missing_data_*.json
    out: Path = ROOT / "data" / "products"
    work: Path = ROOT / "data" / "interim" / "gridding"
    tmp: Path = ROOT / "data" / "interim" / "_duckdb_tmp"
    raw_availability: Path = ROOT / "data" / "raw" / "availability"


def connect(paths: Paths) -> duckdb.DuckDBPyConnection:
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    con.execute("SET memory_limit='5GB'")
    con.execute("SET max_temp_directory_size='20GB'")
    return con


def det_source(paths: Paths, year: int | None = None) -> str:
    y = "*" if year is None else str(year)
    return f"read_parquet('{(paths.detections / 'sensor=*' / f'year={y}' / 'detections.parquet').as_posix()}', hive_partitioning=true)"


def cell_id_sql(row: str, col: str) -> str:
    return f"'g050_r' || lpad(CAST({row} AS VARCHAR), 4, '0') || '_c' || lpad(CAST({col} AS VARCHAR), 4, '0')"


def cell_id(row: int, col: int) -> str:
    return f"g050_r{row:04d}_c{col:04d}"


# ----------------------------------------------------------------------------------- filters
def kept_sql(paths: Paths, year: int) -> str:
    """Kept detections of one year with witness, fine cell indices and attributes."""
    witness = "CASE satellite " + " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in WITNESS.items()) + " END"
    return f"""(SELECT {witness} AS witness, daynight, data_level, acq_date, frp_mw, country_name,
                       CAST(floor((lat + 90) / {FINE}) AS INTEGER) AS fr,
                       CAST(floor((CASE WHEN lon >= 180 THEN lon - 360 ELSE lon END + 180) / {FINE}) AS INTEGER) AS fc
                FROM {det_source(paths, year)}
                WHERE acq_date >= DATE '{RECORD_START}' AND satellite IN ({', '.join(f"'{k}'" for k in WITNESS)})
                  AND confidence_class IN ('NOMINAL', 'HIGH') AND ((data_level = 'SP' AND type = 0) OR data_level = 'NRT')) k"""


MASK_JOIN = "LEFT JOIN read_parquet('{mask}') m ON m.r = k.fr AND m.c = k.fc"


# --------------------------------------------------------------------------------- availability
def parse_missing(path: Path) -> dict[str, set[dt.date]]:
    """Dates FIRMS lists as missing, per witness, from the saved `missing_data` response."""
    html = json.loads(path.read_text(encoding="utf-8"))["html"]
    cells = re.findall(r"<td>([^<]*)</td>", html)
    out: dict[str, set[dt.date]] = {w: set() for w in WITNESS.values()}
    for date, name in zip(cells[0::2], cells[1::2], strict=False):
        if name in MISSING_NAMES and date:
            out[MISSING_NAMES[name]].add(dt.date.fromisoformat(date))
    return out


def newest_missing(paths: Paths) -> Path | None:
    if paths.missing_json is not None:
        return paths.missing_json
    found = sorted(paths.raw_availability.glob("missing_data_*.json"))
    return found[-1] if found else None


def operating_windows(con, paths: Paths) -> dict[str, tuple[dt.date, dt.date]]:
    """First and last date with any detection per witness (before any filter), clipped to the record start."""
    rows = con.execute(f"SELECT satellite, min(acq_date), max(acq_date) FROM {det_source(paths)} GROUP BY 1").fetchall()
    out = {}
    for sat, lo, hi in rows:
        if sat in WITNESS:
            out[WITNESS[sat]] = (max(lo, RECORD_START), hi)
    return out


def detection_days(con, paths: Paths) -> dict[str, set[dt.date]]:
    """Days with at least one detection (before any filter) per witness: proof that the satellite delivered data."""
    out: dict[str, set[dt.date]] = {w: set() for w in WITNESS.values()}
    for sat, d in con.execute(f"SELECT DISTINCT satellite, acq_date FROM {det_source(paths)} WHERE acq_date >= DATE '{RECORD_START}'").fetchall():
        if sat in WITNESS:
            out[WITNESS[sat]].add(d)
    return out


def witness_months(con, paths: Paths, missing: dict[str, set[dt.date]] | None) -> list[dict]:
    """One record per witness and month the witness operated: days_in_month, days_available, data_level.

    A day listed in `missing_data` is subtracted only if the witness has no detection that day. FIRMS lists all of
    May 2026 as missing for S-NPP, yet the data has normal volumes on every one of those days; days with detections
    count as available (evidence of data). For the other witnesses the list and the zero-detection days agree exactly.
    """
    windows = operating_windows(con, paths)
    with_data = detection_days(con, paths)
    levels = {(w, y, m): lvl for w, y, m, lvl in con.execute(f"""
        SELECT CASE satellite {' '.join(f"WHEN '{k}' THEN '{v}'" for k, v in WITNESS.items())} END AS w, year(acq_date), month(acq_date),
               CASE WHEN count(*) FILTER (WHERE data_level = 'NRT') = 0 THEN 'SP'
                    WHEN count(*) FILTER (WHERE data_level = 'SP') = 0 THEN 'NRT' ELSE 'MIXED' END
        FROM {det_source(paths)} WHERE satellite IN ({', '.join(f"'{k}'" for k in WITNESS)}) GROUP BY ALL""").fetchall()}
    out = []
    for w, (lo, hi) in sorted(windows.items()):
        gaps = (missing or {}).get(w, set()) - with_data.get(w, set())
        y, m = lo.year, lo.month
        while (y, m) <= (hi.year, hi.month):
            dim = calendar.monthrange(y, m)[1]
            first, last = max(lo, dt.date(y, m, 1)), min(hi, dt.date(y, m, dim))
            days = (last - first).days + 1 - sum(1 for d in gaps if first <= d <= last)
            if days >= 1 and (w, y, m) in levels:  # a month with no available day has no row
                out.append({"witness": w, "year": y, "month": m, "days_in_month": dim, "days_available": days,
                            "data_level": levels[(w, y, m)]})
            y, m = (y, m + 1) if m < 12 else (y + 1, 1)
    return out


def availability_check(con, paths: Paths, missing: dict[str, set[dt.date]]) -> dict:
    """Compare the missing_data gaps with the days on which a witness has detections at all (diagnostic)."""
    res = {}
    wins = operating_windows(con, paths)
    for sat, w in WITNESS.items():
        if w not in wins:  # no detections at all for this witness
            continue
        days = {r[0] for r in con.execute(f"SELECT DISTINCT acq_date FROM {det_source(paths)} WHERE satellite = '{sat}' "
                                          f"AND acq_date >= DATE '{RECORD_START}'").fetchall()}
        lo, hi = wins[w]
        all_days = {lo + dt.timedelta(i) for i in range((hi - lo).days + 1)}
        listed = {d for d in missing.get(w, set()) if lo <= d <= hi}
        res[w] = {"window": (lo.isoformat(), hi.isoformat()), "days_in_window": len(all_days), "days_with_detections": len(days & all_days),
                  "listed_missing": len(listed), "listed_missing_but_has_detections": len(listed & days),
                  "no_detections_not_listed": len((all_days - days) - listed)}
    return res


# ---------------------------------------------------------------------------------------- build
def observe_year(con, paths: Paths, year: int, work: Path) -> int:
    """Pass 1 for one year: kept fine-cell-days rolled up to analysis cell-months, and country counts per cell."""
    mask = MASK_JOIN.format(mask=paths.mask.as_posix())
    con.execute("DROP TABLE IF EXISTS kept")
    con.execute(f"CREATE TEMP TABLE kept AS SELECT k.* FROM {kept_sql(paths, year)} {mask} WHERE m.r IS NULL")
    n = con.execute("SELECT count(*) FROM kept").fetchone()[0]
    con.execute(f"""COPY (
        SELECT witness, daynight, fr // {RATIO} AS ar, fc // {RATIO} AS ac, month(acq_date) AS m,
               count(*) AS cell_days, sum(det) AS detections, coalesce(sum(frp), 0.0) AS frp_sum_mw
        FROM (SELECT witness, daynight, fr, fc, acq_date, count(*) AS det, sum(frp_mw) FILTER (WHERE frp_mw >= 0) AS frp FROM kept
              GROUP BY ALL)
        GROUP BY ALL) TO '{(work / f'obs_{year}.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)""")
    con.execute(f"""COPY (SELECT fr // {RATIO} AS ar, fc // {RATIO} AS ac, country_name, count(*) AS n FROM kept
        WHERE country_name IS NOT NULL GROUP BY ALL) TO '{(work / f'country_{year}.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)""")
    con.execute("DROP TABLE kept")
    return n


def read_country_map(path: Path) -> dict[str, tuple[str, str]]:
    with open(path, encoding="utf-8", newline="") as f:
        return {r["firms_name"]: (r["iso3"], r["continent"]) for r in csv.DictReader(f)}


def area_km2(row: int) -> float:
    lat_min = -90.0 + ANALYSIS * row
    return round(EARTH_RADIUS_KM**2 * math.radians(ANALYSIS) * (math.sin(math.radians(lat_min + ANALYSIS)) - math.sin(math.radians(lat_min))), 2)


def build_cells(con, paths: Paths, work: Path) -> int:
    """cells.parquet from the observed cell-months, the country counts, the country map and the T-004 fire regions."""
    obs = (work / "obs_*.parquet").as_posix()
    cmap = read_country_map(paths.country_map)
    top = con.execute(f"""SELECT ar, ac, arg_max(country_name, (n, country_name)) FROM
        (SELECT ar, ac, country_name, sum(n) AS n FROM read_parquet('{(work / 'country_*.parquet').as_posix()}') GROUP BY ALL)
        GROUP BY ar, ac""").fetchall()
    country = {(ar, ac): name for ar, ac, name in top}
    regions = {r[0]: r[1] for r in con.execute(f"SELECT cell_id, fire_region FROM read_parquet('{paths.fire_regions.as_posix()}')").fetchall()}
    cells = con.execute(f"SELECT DISTINCT ar, ac FROM read_parquet('{obs}') ORDER BY ar, ac").fetchall()
    cols: dict[str, list] = {k: [] for k in ["cell_id", "lat_min", "lat_max", "lon_min", "lon_max", "lat_c", "lon_c", "area_km2",
                                              "country_iso3", "continent", "fire_region", "stratum_id"]}
    for ar, ac in cells:
        cid = cell_id(ar, ac)
        lat0, lon0 = -90.0 + ANALYSIS * ar, -180.0 + ANALYSIS * ac
        name = country.get((ar, ac))
        iso, cont = cmap[name] if name is not None else (None, None)
        region = regions[cid]
        for k, v in (("cell_id", cid), ("lat_min", lat0), ("lat_max", lat0 + ANALYSIS), ("lon_min", lon0), ("lon_max", lon0 + ANALYSIS),
                     ("lat_c", lat0 + ANALYSIS / 2), ("lon_c", lon0 + ANALYSIS / 2), ("area_km2", area_km2(ar)),
                     ("country_iso3", iso), ("continent", cont), ("fire_region", region),
                     ("stratum_id", f"{region}_{iso or 'NOCOUNTRY'}")):  # provisional rule; T-011 may redefine
            cols[k].append(v)
    schema = pa.schema([("cell_id", pa.string()), *[(k, pa.float64()) for k in ["lat_min", "lat_max", "lon_min", "lon_max", "lat_c", "lon_c", "area_km2"]],
                        ("country_iso3", pa.string()), ("continent", pa.string()), ("fire_region", pa.string()), ("stratum_id", pa.string())])
    paths.out.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table(cols, schema=schema), paths.out / "cells.parquet", compression="zstd")
    return len(cells)


CMW_COLUMNS = ("cell_id, year, month, witness, daynight, detections, cell_days, frp_sum_mw, days_available, days_in_month, data_level")


def write_year(con, paths: Paths, year: int, work: Path, parts: Path) -> int:
    """Pass 2 for one year: every active cell x operated witness-month x D/N, zero-filled, plus ALL = D + N."""
    con.execute(f"""CREATE OR REPLACE TEMP TABLE dn AS
        SELECT {cell_id_sql('c.ar', 'c.ac')} AS cell_id, {year} AS year, w.m AS month, w.witness, d.dn AS daynight,
               CAST(coalesce(o.detections, 0) AS INTEGER) AS detections, CAST(coalesce(o.cell_days, 0) AS INTEGER) AS cell_days,
               coalesce(o.frp_sum_mw, 0.0) AS frp_sum_mw, w.days_available, w.days_in_month, w.data_level
        FROM active c CROSS JOIN (SELECT * FROM wm WHERE y = {year}) w CROSS JOIN (VALUES ('D'), ('N')) d(dn)
        LEFT JOIN read_parquet('{(work / f'obs_{year}.parquet').as_posix()}') o
          ON o.ar = c.ar AND o.ac = c.ac AND o.m = w.m AND o.witness = w.witness AND o.daynight = d.dn""")
    con.execute(f"""COPY (
        SELECT {CMW_COLUMNS} FROM (
          SELECT * FROM dn
          UNION ALL
          SELECT cell_id, year, month, witness, 'ALL', CAST(sum(detections) AS INTEGER), CAST(sum(cell_days) AS INTEGER), sum(frp_sum_mw),
                 any_value(days_available), any_value(days_in_month), any_value(data_level)
          FROM dn GROUP BY cell_id, year, month, witness)
        ORDER BY cell_id, witness, daynight, month) TO '{(parts / f'part_{year}.parquet').as_posix()}'
        (FORMAT parquet, COMPRESSION zstd, ROW_GROUP_SIZE 500000)""")
    n = con.execute(f"SELECT count(*) FROM read_parquet('{(parts / f'part_{year}.parquet').as_posix()}')").fetchone()[0]
    con.execute("DROP TABLE dn")
    return n


def build(paths: Paths | None = None, keep_work: bool = False) -> dict:
    paths = paths or Paths()
    t0 = time.time()
    con = connect(paths)
    work = paths.work
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    parts = work / "parts"
    parts.mkdir()
    years = [int(r[0]) for r in con.execute(f"SELECT DISTINCT year FROM {det_source(paths)} ORDER BY 1").fetchall()]
    kept = 0
    for y in years:
        kept += observe_year(con, paths, y, work)
        print(f"observed {y} ({time.time() - t0:.0f}s)", flush=True)
    n_cells = build_cells(con, paths, work)
    missing_path = newest_missing(paths)
    missing = parse_missing(missing_path) if missing_path else None
    wm = witness_months(con, paths, missing)
    con.execute("CREATE TEMP TABLE wm (witness VARCHAR, y INTEGER, m INTEGER, days_in_month INTEGER, days_available INTEGER, data_level VARCHAR)")
    con.executemany("INSERT INTO wm VALUES (?, ?, ?, ?, ?, ?)",
                    [(r["witness"], r["year"], r["month"], r["days_in_month"], r["days_available"], r["data_level"]) for r in wm])
    con.execute(f"""CREATE TEMP TABLE active AS SELECT DISTINCT ar, ac FROM read_parquet('{(work / 'obs_*.parquet').as_posix()}')""")
    rows = 0
    for y in sorted({r["year"] for r in wm}):
        rows += write_year(con, paths, y, work, parts)
        print(f"wrote {y} ({time.time() - t0:.0f}s, {rows:,} rows so far)", flush=True)
    paths.out.mkdir(parents=True, exist_ok=True)
    final = paths.out / "cell_month_witness.parquet"
    # concatenate the yearly parts in year order without re-sorting
    writer = None
    for p in sorted(parts.glob("part_*.parquet")):
        with pq.ParquetFile(p) as pf:
            if writer is None:
                writer = pq.ParquetWriter(final, pf.schema_arrow, compression="zstd")
            for i in range(pf.num_row_groups):
                writer.write_table(pf.read_row_group(i))
    writer.close()
    con.close()  # release every file handle (Windows cannot delete open files)
    if not keep_work:
        shutil.rmtree(parts)
    return {"years": years, "kept_detections": kept, "cells": n_cells, "witness_months": len(wm), "rows": rows,
            "bytes": final.stat().st_size, "seconds": round(time.time() - t0)}


# -------------------------------------------------------------------------------------- validate
CONTRACT_CELL_MONTH_WITNESS = {"cell_id": "string", "year": "int", "month": "int", "witness": "string", "daynight": "string",
                               "detections": "int", "cell_days": "int", "frp_sum_mw": "float", "days_available": "int",
                               "days_in_month": "int", "data_level": "string"}
WITNESS_START = {"AQUA_MODIS": (2002, 7), "TERRA_MODIS": (2002, 7), "SNPP_VIIRS": (2012, 1), "NOAA20_VIIRS": (2018, 4)}


def _kind(t: pa.DataType) -> str:
    return "string" if pa.types.is_string(t) or pa.types.is_large_string(t) else "int" if pa.types.is_integer(t) else \
        "float" if pa.types.is_floating(t) else str(t)


def validate(paths: Paths | None = None) -> list[str]:
    """Contract and integrity checks on the products. Returns the problems found (empty means valid)."""
    paths = paths or Paths()
    problems: list[str] = []
    path = paths.out / "cell_month_witness.parquet"
    schema = pq.read_schema(path)
    got = {f.name: _kind(f.type) for f in schema}
    if got != CONTRACT_CELL_MONTH_WITNESS:
        problems.append(f"cell_month_witness schema differs from the contract: {got}")
    con = connect(paths)
    p = f"read_parquet('{path.as_posix()}')"
    one = lambda sql: con.execute(sql).fetchone()[0]
    for col in CONTRACT_CELL_MONTH_WITNESS:
        if one(f"SELECT count(*) FROM {p} WHERE {col} IS NULL"):
            problems.append(f"nulls in non-nullable column {col}")
    for col, allowed in (("witness", WITNESS_START), ("daynight", ("D", "N", "ALL")), ("data_level", ("SP", "NRT", "MIXED"))):
        bad = one(f"SELECT count(*) FROM {p} WHERE {col} NOT IN ({', '.join(repr(a) for a in allowed)})")
        if bad:
            problems.append(f"{bad} rows with {col} outside the enumeration")
    for sql, text in (
        (f"SELECT count(*) FROM {p} WHERE month < 1 OR month > 12", "month outside 1 to 12"),
        (f"SELECT count(*) FROM {p} WHERE days_available < 1 OR days_available > days_in_month", "days_available outside 1..days_in_month"),
        (f"SELECT count(*) FROM {p} WHERE cell_days < 0 OR detections < 0 OR frp_sum_mw < 0", "negative counts or FRP"),
        (f"SELECT count(*) FROM {p} WHERE cell_days > detections", "cell_days above detections"),
        (f"SELECT count(*) FROM {p} WHERE cell_days > {RATIO * RATIO} * days_available", "cell_days above fine cells x days available"),
        (f"SELECT count(*) FROM {p} WHERE year * 100 + month < 200207", "rows before the record start (2002-07)"),
    ):
        bad = one(sql)
        if bad:
            problems.append(f"{bad} rows: {text}")
    for w, (y, m) in WITNESS_START.items():
        bad = one(f"SELECT count(*) FROM {p} WHERE witness = '{w}' AND year * 100 + month < {y * 100 + m}")
        if bad:
            problems.append(f"{bad} rows for {w} before it operated")
    years = [r[0] for r in con.execute(f"SELECT DISTINCT year FROM {p} ORDER BY 1").fetchall()]
    for y in years:  # per year: bounded memory
        dup = one(f"SELECT count(*) - count(DISTINCT (cell_id, month, witness, daynight)) FROM {p} WHERE year = {y}")
        if dup:
            problems.append(f"{y}: {dup} duplicate keys")
        bad = one(f"""SELECT count(*) FROM (SELECT cell_id, month, witness,
              sum(cell_days) FILTER (WHERE daynight IN ('D', 'N')) AS dn, sum(cell_days) FILTER (WHERE daynight = 'ALL') AS a,
              sum(detections) FILTER (WHERE daynight IN ('D', 'N')) AS dn_d, sum(detections) FILTER (WHERE daynight = 'ALL') AS a_d,
              count(*) AS n FROM {p} WHERE year = {y} GROUP BY ALL) WHERE n <> 3 OR dn <> a OR dn_d <> a_d""")
        if bad:
            problems.append(f"{y}: {bad} cell-months where the D, N and ALL rows do not fit (ALL must be D + N)")
    cells = f"read_parquet('{(paths.out / 'cells.parquet').as_posix()}')"
    missing_cells = one(f"SELECT count(DISTINCT cell_id) FROM {p} WHERE cell_id NOT IN (SELECT cell_id FROM {cells})")
    if missing_cells:
        problems.append(f"{missing_cells} cell_ids are not in cells.parquet")
    return problems


def integrity(paths: Paths | None = None) -> dict:
    """Independent counts from the interim detections, compared with the products."""
    paths = paths or Paths()
    con = connect(paths)
    out = {}
    mask = MASK_JOIN.format(mask=paths.mask.as_posix())
    tot = {"detections": 0, "fine_cell_days": 0}
    for y in [int(r[0]) for r in con.execute(f"SELECT DISTINCT year FROM {det_source(paths)} ORDER BY 1").fetchall()]:
        d, f = con.execute(f"""SELECT count(*), count(DISTINCT (witness, daynight, fr, fc, acq_date)) FROM
            (SELECT k.* FROM {kept_sql(paths, y)} {mask} WHERE m.r IS NULL)""").fetchone()
        tot["detections"] += d
        tot["fine_cell_days"] += f
    p = f"read_parquet('{(paths.out / 'cell_month_witness.parquet').as_posix()}')"
    prod = con.execute(f"SELECT sum(detections), sum(cell_days) FROM {p} WHERE daynight = 'ALL'").fetchone()
    out.update({"kept_detections_independent": tot["detections"], "kept_detections_product": int(prod[0]),
                "fine_cell_days_independent": tot["fine_cell_days"], "fine_cell_days_product": int(prod[1])})
    out["match"] = out["kept_detections_independent"] == out["kept_detections_product"] and \
        out["fine_cell_days_independent"] == out["fine_cell_days_product"]
    return out


def monthly_totals(paths: Paths | None = None) -> list[tuple]:
    """Global raw combined cell_days per month and witness (ALL), the G1 sensor-jump evidence."""
    paths = paths or Paths()
    con = connect(paths)
    p = f"read_parquet('{(paths.out / 'cell_month_witness.parquet').as_posix()}')"
    return con.execute(f"SELECT year, month, witness, sum(cell_days) FROM {p} WHERE daynight = 'ALL' GROUP BY ALL ORDER BY 1, 2, 3").fetchall()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "validate"])
    args = ap.parse_args()
    paths = Paths()
    if args.cmd == "build":
        print(build(paths))
    else:
        problems = validate(paths)
        print("\n".join(problems) if problems else "cell_month_witness validates against the contract")
        print(integrity(paths))
        return 1 if problems else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
