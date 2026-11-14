"""Grid-size comparison for D-009 / Gate G1: Aqua MODIS against S-NPP VIIRS, 2012-01 to 2016-12.

Four combinations: fine grid 0.05 or 0.1 degrees x analysis grid 0.25 or 0.5 degrees. Standard (SP) data only.
Filters: type 0, confidence (MODIS 30 or more; VIIRS n or h) and, in the main run, the approved static-source mask
(0.05 degree cells, static share at least 0.5, at least 10 detections). A second run without the mask is reported too.

Unit: a detection marks its fine cell as fire-active for that UTC day, per satellite. The cell-month value is the
number of such fine-cell-days whose fine-cell centre lies in the analysis cell.
Aggregate statistics only: no region, country or case is looked at, and nothing from the validation plan.

    python pipeline/grid_test.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DET = ROOT / "data" / "interim" / "detections"
MASK = ROOT / "data" / "interim" / "qa" / "static_mask_fine0.05_share0.5_min10.parquet"
OUT = ROOT / "data" / "interim" / "gridtest"
START, END = "2012-01-01", "2016-12-31"
MONTHS = 60
FINE = (0.05, 0.1)
ANALYSIS = (0.25, 0.5)
MIN_ACTIVITY = 5  # proposed: Aqua cell-days needed for a verdict (reported only)


def connect(tmp: Path | None = None) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    if tmp is not None:
        tmp.mkdir(parents=True, exist_ok=True)
        con.execute(f"SET temp_directory='{tmp.as_posix()}'")
    con.execute("SET memory_limit='5GB'")
    con.execute("SET max_temp_directory_size='15GB'")
    return con


def detections_sql(det_dir: Path) -> str:
    """Filtered SP detections of the two satellites in the period (type 0 and confidence)."""
    sp = lambda sensor: f"read_parquet('{(det_dir / f'sensor={sensor}' / 'year=*' / 'detections.parquet').as_posix()}', hive_partitioning=true)"
    cols = "lat, lon, acq_date, daynight, confidence_class"
    return f"""(SELECT 'AQUA' AS sat, {cols} FROM {sp('MODIS')} WHERE satellite = 'Aqua'
                  AND data_level = 'SP' AND type = 0 AND confidence_class IN ('NOMINAL', 'HIGH') AND acq_date BETWEEN DATE '{START}' AND DATE '{END}'
               UNION ALL
               SELECT 'SNPP' AS sat, {cols} FROM {sp('VIIRS_SNPP')}
                  WHERE data_level = 'SP' AND type = 0 AND confidence_class IN ('NOMINAL', 'HIGH') AND acq_date BETWEEN DATE '{START}' AND DATE '{END}')"""


def cell_index(fine: float, p: str = "") -> str:
    """Fine cell indices (row from the south, column from -180); longitude 180 counts as -180. p prefixes the columns."""
    return (f"CAST(floor(({p}lat + 90) / {fine}) AS INTEGER) AS fr, "
            f"CAST(floor((CASE WHEN {p}lon >= 180 THEN {p}lon - 360 ELSE {p}lon END + 180) / {fine}) AS INTEGER) AS fc")


def build_fine_cell_days(con, det: str, fine: float, use_mask: bool, mask_path: Path = MASK) -> str:
    """TEMP table of distinct (satellite, fine cell, UTC day, day/night). Returns its name."""
    name = f"fcd_{str(fine).replace('.', '')}_{'m' if use_mask else 'n'}"
    con.execute(f"DROP TABLE IF EXISTS {name}")
    mask_join, mask_where = "", ""
    if use_mask:  # the approved mask is defined on 0.05 degree cells whatever the fine grid is
        mask_join = (f"LEFT JOIN read_parquet('{mask_path.as_posix()}') m ON m.r = CAST(floor((d.lat + 90) / 0.05) AS INTEGER) "
                     "AND m.c = CAST(floor((CASE WHEN d.lon >= 180 THEN d.lon - 360 ELSE d.lon END + 180) / 0.05) AS INTEGER)")
        mask_where = "WHERE m.r IS NULL"
    con.execute(f"""CREATE TEMP TABLE {name} AS
        SELECT DISTINCT sat, fr, fc, acq_date, daynight FROM
          (SELECT d.sat, {cell_index(fine, 'd.')}, d.acq_date, d.daynight
           FROM {det} d {mask_join} {mask_where})""")
    return name


def cell_months(con, fcd: str, fine: float, analysis: float, dn: str | None) -> str:
    """TEMP table (sat, cell, month, cell_days) from the fine-cell-days; dn is None (D and N combined), 'D' or 'N'."""
    name = "cm"
    con.execute(f"DROP TABLE IF EXISTS {name}")
    dn_sql = "" if dn is None else f"WHERE daynight = '{dn}'"
    sel = "DISTINCT sat, fr, fc, acq_date" if dn is None else "sat, fr, fc, acq_date"
    con.execute(f"""CREATE TEMP TABLE {name} AS
        SELECT sat, CAST(floor({fine} * (fr + 0.5) / {analysis}) AS INTEGER) AS ar, CAST(floor({fine} * (fc + 0.5) / {analysis}) AS INTEGER) AS ac,
               date_trunc('month', acq_date) AS month, count(*) AS cell_days
        FROM (SELECT {sel} FROM {fcd} {dn_sql}) GROUP BY ALL""")
    return name


def metrics(con, cm: str, months: int = MONTHS, min_activity: int = MIN_ACTIVITY) -> dict:
    """Agreement statistics for Aqua against S-NPP on the cell-months table."""
    con.execute("DROP TABLE IF EXISTS joined")
    con.execute(f"""CREATE TEMP TABLE joined AS
        SELECT coalesce(a.ar, s.ar) AS ar, coalesce(a.ac, s.ac) AS ac, coalesce(a.month, s.month) AS month,
               coalesce(a.cell_days, 0) AS a, coalesce(s.cell_days, 0) AS s
        FROM (SELECT * FROM {cm} WHERE sat = 'AQUA') a FULL OUTER JOIN (SELECT * FROM {cm} WHERE sat = 'SNPP') s
          ON a.ar = s.ar AND a.ac = s.ac AND a.month = s.month""")
    n_either, n_both = con.execute("SELECT count(*), count(*) FILTER (WHERE a > 0 AND s > 0) FROM joined").fetchone()
    if n_either == 0:
        return {"active_cells": 0, "cell_months_either": 0}
    n_cells = con.execute("SELECT count(*) FROM (SELECT DISTINCT ar, ac FROM joined)").fetchone()[0]
    universe = n_cells * months
    rho = con.execute("""WITH r AS (SELECT rank() OVER (ORDER BY a) + (count(*) OVER (PARTITION BY a) - 1) / 2.0 AS ra,
                                           rank() OVER (ORDER BY s) + (count(*) OVER (PARTITION BY s) - 1) / 2.0 AS rs FROM joined)
                         SELECT corr(ra, rs) FROM r""").fetchone()[0]
    q = con.execute("""SELECT quantile_cont(a * 1.0 / s, [0.25, 0.5, 0.75]) FROM joined WHERE a > 0 AND s > 0""").fetchone()[0]
    one_zero = n_either - n_both
    ge = con.execute(f"SELECT count(*) FROM joined WHERE a >= {min_activity}").fetchone()[0]
    return {"active_cells": n_cells, "cell_months_either": n_either, "universe_cell_months": universe,
            "spearman": rho, "ratio_q25": q[0], "ratio_median": q[1], "ratio_q75": q[2],
            "share_both_zero": (universe - n_either) / universe, "share_one_zero": one_zero / universe, "share_both_positive": n_both / universe,
            "share_aqua_ge_min": ge / universe, "aqua_ge_min_cell_months": ge,
            "share_either_both_positive": n_both / n_either}


def run_combo(con, fcd: str, fine: float, analysis: float, dn: str | None, out_dir: Path | None) -> dict:
    t0 = time.time()
    cm = cell_months(con, fcd, fine, analysis, dn)
    res = metrics(con, cm)
    size = None
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"cell_months_f{fine}_a{analysis}_{dn or 'ALL'}.parquet"
        con.execute(f"COPY (SELECT * FROM joined ORDER BY ar, ac, month) TO '{path.as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
        size = path.stat().st_size
        path.unlink()  # only the size is of interest; the table is rebuilt in seconds
    res.update({"fine": fine, "analysis": analysis, "dn": dn or "ALL", "seconds": round(time.time() - t0, 1), "output_bytes": size})
    return res


def run(det_dir: Path = DET, out_dir: Path | None = OUT, mask_path: Path = MASK, tmp: Path | None = None) -> list[dict]:
    con = connect(tmp)
    det = detections_sql(det_dir)
    results = []
    for use_mask in (True, False):
        for fine in FINE:
            t0 = time.time()
            fcd = build_fine_cell_days(con, det, fine, use_mask, mask_path)
            build_s = round(time.time() - t0, 1)
            n_fcd = con.execute(f"SELECT count(*) FROM {fcd}").fetchone()[0]
            for analysis in ANALYSIS:
                for dn in (None, "D", "N"):
                    r = run_combo(con, fcd, fine, analysis, dn, out_dir)
                    r.update({"mask": use_mask, "fine_cell_day_build_seconds": build_s, "fine_cell_days": n_fcd})
                    results.append(r)
                    print(f"mask={use_mask} fine={fine} analysis={analysis} {r['dn']}: spearman={r.get('spearman')} "
                          f"median ratio={r.get('ratio_median')} {r['seconds']}s", flush=True)
            con.execute(f"DROP TABLE {fcd}")  # free the memory before the next fine grid
    return results


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    res = run(tmp=ROOT / "data" / "interim" / "_duckdb_tmp")
    (OUT / "grid_test_results.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print("wrote", OUT / "grid_test_results.json")


if __name__ == "__main__":
    main()
