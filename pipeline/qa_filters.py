"""QA summary, filter counts and static-source mask evidence for the normalized detections (T-005).

Nothing is dropped, de-duplicated or altered: every check counts, nothing is applied
destructively. The share threshold, minimum count and fine grid size of the static mask are
proposals for the Lead (D-009 is open), so the mask is evaluated at several settings.

    python pipeline/qa_filters.py            # full run, writes data/interim/qa/ and qa_summary.md
    python pipeline/qa_filters.py --only qa  # one part: qa | filters | mask | daynight
"""
from __future__ import annotations

import argparse
import json
import time
import zipfile
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DET = ROOT / "data" / "interim" / "detections"
QA = ROOT / "data" / "interim" / "qa"
ZIPS = ROOT / "data" / "raw" / "zips"
DB_TMP = ROOT / "data" / "interim" / "_duckdb_tmp"

FINE_SIZES = (0.05, 0.1)  # D-009 candidates (degrees)
SHARES = (0.3, 0.5, 0.7, 0.9)
MIN_DETS = (3, 10)
TRAIN_YEARS = (2012, 2023)
EVAL_YEARS = (2024, 2025)
FULL_YEARS = (2012, 2025)
NIGHT_ZENITH_DEG = 85.0
SAMPLE_PCT = 0.5
PROPOSED_SHARE, PROPOSED_MIN_DETS = 0.5, 10  # a proposal for the Lead, not a decision


def connect(tmp: Path = DB_TMP) -> duckdb.DuckDBPyConnection:
    tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{tmp.as_posix()}'")
    con.execute("SET memory_limit='5GB'")
    con.execute("SET max_temp_directory_size='15GB'")  # a runaway query must fail, not fill the disk
    return con


def source(det_dir: Path = DET) -> str:
    return f"read_parquet('{(det_dir / 'sensor=*' / 'year=*' / 'detections.parquet').as_posix()}', hive_partitioning=true)"


def partitions(det_dir: Path = DET) -> list[str]:
    """One read_parquet source per sensor-year file, so heavy checks never hold the whole table at once."""
    return [f"read_parquet('{f.as_posix()}', hive_partitioning=true)"
            for f in sorted(det_dir.glob("sensor=*/year=*/detections.parquet"))]


# --------------------------------------------------------------------------- QA: value domains
def domain_violations(con, src: str) -> list[tuple]:
    """Per sensor and year: rows and the number of rows violating each documented value domain."""
    sql = f"""SELECT sensor, year, count(*) AS rows,
        count(*) FILTER (WHERE lat < -90 OR lat > 90) AS lat_out,
        count(*) FILTER (WHERE lon < -180 OR lon > 180) AS lon_out,
        count(*) FILTER (WHERE acq_date IS NOT NULL AND year(acq_date) <> year) AS date_outside_year,
        count(*) FILTER (WHERE acq_time_utc < 0 OR acq_time_utc > 2359 OR acq_time_utc % 100 >= 60) AS time_out,
        count(*) FILTER (WHERE CASE WHEN sensor = 'MODIS'
              THEN TRY_CAST(confidence_raw AS INTEGER) IS NULL OR TRY_CAST(confidence_raw AS INTEGER) NOT BETWEEN 0 AND 100
              ELSE lower(confidence_raw) IS NULL OR lower(confidence_raw) NOT IN ('l', 'n', 'h') END) AS confidence_out,
        count(*) FILTER (WHERE daynight IS NULL OR daynight NOT IN ('D', 'N')) AS daynight_out,
        count(*) FILTER (WHERE type IS NOT NULL AND type NOT IN (0, 1, 2, 3)) AS type_out,
        count(*) FILTER (WHERE frp_mw < 0) AS frp_negative,
        count(*) FILTER (WHERE scan_km <= 0) AS scan_not_positive,
        count(*) FILTER (WHERE track_km <= 0) AS track_not_positive,
        count(*) FILTER (WHERE lat IS NULL OR lon IS NULL OR acq_date IS NULL OR acq_time_utc IS NULL OR satellite IS NULL) AS null_key,
        count(*) FILTER (WHERE frp_mw IS NULL) AS frp_null
        FROM {src} GROUP BY sensor, year ORDER BY sensor, year"""
    return con.execute(sql).fetchall()


DOMAIN_COLUMNS = ["sensor", "year", "rows", "lat_out", "lon_out", "date_outside_year", "time_out", "confidence_out",
                  "daynight_out", "type_out", "frp_negative", "scan_not_positive", "track_not_positive", "null_key", "frp_null"]


# ------------------------------------------------------------------------------ QA: duplicates
def duplicates(con, src: str) -> list[tuple]:
    """Exact duplicates on (satellite, lat, lon, acq_date, acq_time) per sensor and year.

    dup_rows = rows that repeat an earlier row. same_country = repeats inside one country file,
    cross_country = repeats found only in another country's file. Counted, never removed.
    """
    sql = f"""SELECT sensor, year, count(*) AS rows,
        count(*) - count(DISTINCT (satellite, lat, lon, acq_date, acq_time_utc)) AS dup_rows,
        count(*) - count(DISTINCT (satellite, lat, lon, acq_date, acq_time_utc, coalesce(country_name, ''))) AS same_country
        FROM {src} GROUP BY sensor, year ORDER BY sensor, year"""
    rows = con.execute(sql).fetchall()
    return [(s, y, n, d, sc, d - sc) for s, y, n, d, sc in rows]


DUP_COLUMNS = ["sensor", "year", "rows", "dup_rows", "dup_same_country_file", "dup_cross_country_files"]


def year_boundary(con, src: str) -> list[tuple]:
    """Date range of each sensor-year: a partition must not run into the next one."""
    return con.execute(f"SELECT sensor, year, min(acq_date), max(acq_date) FROM {src} GROUP BY sensor, year ORDER BY sensor, year").fetchall()


# ------------------------------------------------------------------------------------- filters
def filter_funnel(con, src: str) -> list[tuple]:
    """Before/after counts per sensor and data level. Rows are counted, never removed.

    keep_type: SP rows with type 0 (vegetation fire); NRT rows have no type and are kept here
    (the static mask handles them). conf_ok: MODIS confidence >= 30, VIIRS n or h.
    """
    sql = f"""SELECT sensor, data_level, count(*) AS rows,
        count(*) FILTER (WHERE data_level = 'SP' AND type IS NULL) AS sp_type_missing,
        count(*) FILTER (WHERE data_level = 'SP' AND type = 1) AS sp_type1_volcano,
        count(*) FILTER (WHERE data_level = 'SP' AND type = 2) AS sp_type2_static,
        count(*) FILTER (WHERE data_level = 'SP' AND type = 3) AS sp_type3_offshore,
        count(*) FILTER (WHERE (data_level = 'SP' AND type = 0) OR data_level = 'NRT') AS after_type_filter,
        count(*) FILTER (WHERE confidence_class IN ('NOMINAL', 'HIGH')) AS after_confidence_only,
        count(*) FILTER (WHERE ((data_level = 'SP' AND type = 0) OR data_level = 'NRT')
                         AND confidence_class IN ('NOMINAL', 'HIGH')) AS after_type_and_confidence,
        count(*) FILTER (WHERE confidence_class IS NULL) AS confidence_unclassified
        FROM {src} GROUP BY sensor, data_level ORDER BY sensor, data_level"""
    return con.execute(sql).fetchall()


FUNNEL_COLUMNS = ["sensor", "data_level", "rows", "sp_type_missing", "sp_type1_volcano", "sp_type2_static", "sp_type3_offshore",
                  "after_type_filter", "after_confidence_only", "after_type_and_confidence", "confidence_unclassified"]


# ---------------------------------------------------------------------------------- static mask
def fine_cell_sql(fine: float) -> str:
    """Fine cell indices (row from the south, column from -180); longitude 180 counts as -180."""
    return (f"CAST(floor((lat + 90) / {fine}) AS INTEGER) AS r, "
            f"CAST(floor((CASE WHEN lon >= 180 THEN lon - 360 ELSE lon END + 180) / {fine}) AS INTEGER) AS c")


def build_cells(con, src: str, fine: float, years: tuple[int, int]) -> None:
    """TEMP table cells_<years>: per fine cell, SP detections and how many are type 2 or 3 (static or offshore)."""
    name = f"cells_{years[0]}_{years[1]}"
    con.execute(f"DROP TABLE IF EXISTS {name}")
    con.execute(f"""CREATE TEMP TABLE {name} AS
        SELECT {fine_cell_sql(fine)}, count(*) AS n_total, count(*) FILTER (WHERE type IN (2, 3)) AS n_static
        FROM {src} WHERE data_level = 'SP' AND type IS NOT NULL AND year BETWEEN {years[0]} AND {years[1]} GROUP BY 1, 2""")


def mask_sweep(con, src: str, fine: float) -> list[dict]:
    """For each (share, min detections): cells masked, NRT rows masked, and a hold-out score.

    Hold-out: cells built from SP years TRAIN_YEARS, tested on SP years EVAL_YEARS (type is known there):
    static_removed = share of type 2 or 3 detections that fall in a masked cell;
    fire_lost = share of type 0 detections that fall in a masked cell (wrongly removed).
    """
    build_cells(con, src, fine, TRAIN_YEARS)
    build_cells(con, src, fine, FULL_YEARS)
    train, full = f"cells_{TRAIN_YEARS[0]}_{TRAIN_YEARS[1]}", f"cells_{FULL_YEARS[0]}_{FULL_YEARS[1]}"
    combos = [(s, m) for m in MIN_DETS for s in SHARES]
    def cond(tbl_alias, s, m):
        return f"({tbl_alias}.n_total >= {m} AND {tbl_alias}.n_static >= {s} * {tbl_alias}.n_total)"
    sel = []
    for i, (s, m) in enumerate(combos):
        sel.append(f"count(*) FILTER (WHERE {cond('t', s, m)} AND e.type IN (2, 3)) AS tp_{i}")
        sel.append(f"count(*) FILTER (WHERE {cond('t', s, m)} AND e.type = 0) AS fire_lost_{i}")
        sel.append(f"count(*) FILTER (WHERE {cond('t', s, m)} AND e.type = 1) AS volcano_masked_{i}")
    ev = con.execute(f"""SELECT count(*) FILTER (WHERE e.type IN (2, 3)), count(*) FILTER (WHERE e.type = 0), {', '.join(sel)}
        FROM (SELECT {fine_cell_sql(fine)}, type FROM {src}
              WHERE data_level = 'SP' AND type IS NOT NULL AND year BETWEEN {EVAL_YEARS[0]} AND {EVAL_YEARS[1]}) e
        LEFT JOIN {train} t ON e.r = t.r AND e.c = t.c""").fetchone()
    n_static_eval, n_fire_eval, vals = ev[0], ev[1], ev[2:]
    nsel = []
    for i, (s, m) in enumerate(combos):
        nsel.append(f"count(*) FILTER (WHERE {cond('f', s, m)}) AS nrt_masked_{i}")
    nrt = con.execute(f"""SELECT count(*), {', '.join(nsel)}
        FROM (SELECT {fine_cell_sql(fine)} FROM {src} WHERE data_level = 'NRT') n
        LEFT JOIN {full} f ON n.r = f.r AND n.c = f.c""").fetchone()
    n_nrt, nrt_vals = nrt[0], nrt[1:]
    out = []
    for i, (s, m) in enumerate(combos):
        tp, lost, volc = vals[3 * i], vals[3 * i + 1], vals[3 * i + 2]
        cells = con.execute(f"SELECT count(*) FROM {full} f WHERE {cond('f', s, m)}").fetchone()[0]
        masked_all = tp + lost + volc
        out.append({"fine_deg": fine, "min_share": s, "min_detections": m, "cells_masked": cells,
                    "nrt_rows_total": n_nrt, "nrt_rows_masked": nrt_vals[i],
                    "eval_static_total": n_static_eval, "eval_fire_total": n_fire_eval,
                    "static_removed": tp, "fire_lost": lost,
                    "static_removed_share": tp / n_static_eval if n_static_eval else None,
                    "fire_lost_share": lost / n_fire_eval if n_fire_eval else None,
                    "precision": tp / masked_all if masked_all else None})
    return out


def save_mask(con, fine: float, share: float, min_det: int, path: Path) -> int:
    """Write the cells of one proposed setting (from the full SP history) as a local Parquet file."""
    full = f"cells_{FULL_YEARS[0]}_{FULL_YEARS[1]}"
    path.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"""COPY (SELECT r, c, n_total, n_static, n_static * 1.0 / n_total AS share_static FROM {full}
        WHERE n_total >= {min_det} AND n_static >= {share} * n_total ORDER BY r, c)
        TO '{path.as_posix()}' (FORMAT parquet, COMPRESSION zstd)""")
    return con.execute(f"SELECT count(*) FROM read_parquet('{path.as_posix()}')").fetchone()[0]


# -------------------------------------------------------------------------- day / night check
def zenith_sql(lat: str = "lat", lon: str = "lon", date: str = "acq_date", hhmm: str = "acq_time_utc") -> str:
    """Solar zenith angle in degrees (NOAA general solar position approximation; about 0.5 degree accuracy)."""
    hour = f"(({hhmm} // 100) + ({hhmm} % 100) / 60.0)"
    g = f"(2 * pi() / 365.0 * (dayofyear({date}) - 1 + ({hour} - 12) / 24.0))"
    decl = (f"(0.006918 - 0.399912 * cos({g}) + 0.070257 * sin({g}) - 0.006758 * cos(2 * {g}) + 0.000907 * sin(2 * {g})"
            f" - 0.002697 * cos(3 * {g}) + 0.00148 * sin(3 * {g}))")
    eqt = f"(229.18 * (0.000075 + 0.001868 * cos({g}) - 0.032077 * sin({g}) - 0.014615 * cos(2 * {g}) - 0.040849 * sin(2 * {g})))"
    hour_angle = f"(radians(({hour} * 60 + {eqt} + 4 * {lon}) / 4.0 - 180))"
    cosz = f"(sin(radians({lat})) * sin({decl}) + cos(radians({lat})) * cos({decl}) * cos({hour_angle}))"
    return f"degrees(acos(greatest(-1.0, least(1.0, {cosz}))))"


def daynight_check(con, src: str, pct: float = SAMPLE_PCT) -> list[tuple]:
    """On a sample, how often `daynight` agrees with the solar zenith rule (night above 85 degrees).

    Rows within 1 degree of the 85 degree limit are excluded because the approximation cannot decide them.
    Reported only; no row is recomputed.
    """
    sql = f"""WITH s AS (SELECT sensor, data_level, daynight, {zenith_sql()} AS z
                         FROM {src} USING SAMPLE {pct} PERCENT (bernoulli, 20261114))
        SELECT sensor, data_level, count(*) AS sample_rows,
            count(*) FILTER (WHERE abs(z - {NIGHT_ZENITH_DEG}) > 1) AS decidable,
            count(*) FILTER (WHERE abs(z - {NIGHT_ZENITH_DEG}) > 1
                             AND ((z > {NIGHT_ZENITH_DEG} AND daynight = 'N') OR (z <= {NIGHT_ZENITH_DEG} AND daynight = 'D'))) AS agree
        FROM s GROUP BY sensor, data_level ORDER BY sensor, data_level"""
    return con.execute(sql).fetchall()


# ----------------------------------------------------------------------------------- measurements
def unzipped_bytes(zips: Path = ZIPS) -> tuple[int, int]:
    """(zip count, total uncompressed CSV bytes) from the zip central directories."""
    total, n = 0, 0
    for f in sorted(zips.glob("*.zip")):
        with zipfile.ZipFile(f) as z:
            total += sum(i.file_size for i in z.infolist() if i.filename.lower().endswith(".csv"))
        n += 1
    return n, total


# -------------------------------------------------------------------------------------- report
def md(columns, rows, fmt=None) -> str:
    fmt = fmt or {}
    def cell(c, v):
        if v is None:
            return "-"
        if c in fmt:
            return fmt[c](v)
        if c == "year":
            return str(v)
        return f"{v:,}" if isinstance(v, int) else str(v)
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    lines += ["| " + " | ".join(cell(c, v) for c, v in zip(columns, r, strict=True)) + " |" for r in rows]
    return "\n".join(lines)


def pct(v) -> str:
    return f"{100 * v:.2f}%"


def run(det_dir: Path = DET, out_dir: Path = QA, only: str | None = None, tmp: Path = DB_TMP, zips: Path = ZIPS) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    con = connect(tmp)
    src = source(det_dir)
    res: dict = {}
    saved = out_dir / "qa_results.json"
    if only and saved.exists():  # a partial run updates its own parts and keeps the rest
        res = json.loads(saved.read_text(encoding="utf-8"))
    t0 = time.time()
    if only in (None, "qa"):
        res["domain"], res["duplicates"], res["boundaries"] = [], [], []
        for part in partitions(det_dir):  # one sensor-year at a time: bounded memory
            res["domain"] += domain_violations(con, part)
            res["duplicates"] += duplicates(con, part)
            res["boundaries"] += year_boundary(con, part)
        print(f"qa done {time.time() - t0:.0f}s", flush=True)
    if only in (None, "filters"):
        res["funnel"] = filter_funnel(con, src)
        print(f"filters done {time.time() - t0:.0f}s", flush=True)
    if only in (None, "mask"):
        res["mask"], res["mask_files"] = [], {}
        for fine in FINE_SIZES:
            res["mask"] += mask_sweep(con, src, fine)
            name = f"static_mask_fine{fine}_share{PROPOSED_SHARE}_min{PROPOSED_MIN_DETS}.parquet"
            res["mask_files"][name] = save_mask(con, fine, PROPOSED_SHARE, PROPOSED_MIN_DETS, out_dir / name)
            print(f"mask {fine} done {time.time() - t0:.0f}s", flush=True)
    if only in (None, "daynight"):
        res["daynight"] = daynight_check(con, src)
        print(f"daynight done {time.time() - t0:.0f}s", flush=True)
    res["unzipped"] = unzipped_bytes(zips)
    (out_dir / "qa_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    (out_dir / "qa_summary.md").write_text(summary(res), encoding="utf-8")
    return res


def summary(res: dict) -> str:
    parts = ["# QA summary (T-005), generated by pipeline/qa_filters.py\n"]
    if "domain" in res:
        bad = [r for r in res["domain"] if any(r[3:13])]
        parts.append("## Value domains\n\nViolations per sensor-year (only years with a violation are listed; `frp_null` is informational).\n")
        parts.append(md(DOMAIN_COLUMNS, bad) if bad else "No sensor-year has a value-domain violation.")
        totals = [sum(r[i] for r in res["domain"]) for i in range(2, len(DOMAIN_COLUMNS))]
        parts.append("\nTotals: " + ", ".join(f"{c} {v:,}" for c, v in zip(DOMAIN_COLUMNS[2:], totals, strict=True)) + "\n")
    if "duplicates" in res:
        parts.append("## Exact duplicates (satellite, lat, lon, date, time)\n")
        parts.append(md(DUP_COLUMNS, [r for r in res["duplicates"] if r[3]]) or "")
        tot = [sum(r[i] for r in res["duplicates"]) for i in (2, 3, 4, 5)]
        parts.append(f"\nTotals: rows {tot[0]:,}, duplicate rows {tot[1]:,}, same country file {tot[2]:,}, across country files {tot[3]:,}.\n")
    if "boundaries" in res:
        parts.append("## Year boundaries\n")
        bounds = {(s, y): (a, b) for s, y, a, b in res["boundaries"]}
        overlap = [f"{s} {y}/{y + 1}" for (s, y), (_, b) in bounds.items() if (s, y + 1) in bounds and str(b) >= str(bounds[(s, y + 1)][0])]
        parts.append("Partitions overlapping in time: " + (", ".join(overlap) if overlap else "none") + ".\n")
    if "funnel" in res:
        parts.append("## Filter funnel (counted, not applied)\n")
        parts.append(md(FUNNEL_COLUMNS, res["funnel"]))
        parts.append("")
    if "mask" in res:
        parts.append("## Static-source mask: threshold sweep (proposals, need Lead approval)\n")
        cols = ["fine_deg", "min_share", "min_detections", "cells_masked", "nrt_rows_masked", "static_removed_share", "fire_lost_share", "precision"]
        rows = [[m[c] for c in cols] for m in res["mask"]]
        parts.append(md(cols, rows, {"static_removed_share": pct, "fire_lost_share": pct, "precision": pct,
                                     "fine_deg": str, "min_share": str}))
        parts.append("")
    if res.get("mask_files"):
        parts.append("Proposed masks written locally (not committed): " + ", ".join(f"`{k}` ({v:,} cells)" for k, v in res["mask_files"].items()) + ".\n")
    if "daynight" in res:
        parts.append("## Day/night against the solar zenith rule (sample)\n")
        parts.append(md(["sensor", "data_level", "sample_rows", "decidable", "agree"], res["daynight"]))
        parts.append("")
    n, tot = res["unzipped"]
    parts.append(f"## Measured sizes\n\n{n} zips, {tot:,} bytes of CSV when unzipped ({tot / 1e9:.2f} GB, {tot / 2**30:.2f} GiB).\n")
    return "\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["qa", "filters", "mask", "daynight"])
    ap.add_argument("--render", action="store_true", help="rewrite qa_summary.md from the saved qa_results.json")
    args = ap.parse_args()
    if args.render:
        res = json.loads((QA / "qa_results.json").read_text(encoding="utf-8"))
        (QA / "qa_summary.md").write_text(summary(res), encoding="utf-8")
    else:
        run(only=args.only)
    print(f"wrote {QA / 'qa_summary.md'}")


if __name__ == "__main__":
    main()
