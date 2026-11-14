"""Investigate the MODIS `version` values (T-007).

Reports, without changing any data:
  * the version timeline per satellite and data level;
  * rows whose version differs from the dominant version of their year, and which country files they are in;
  * a step test: for every 1 January, the 12 months after against the 12 months before, for several measures.
    The version boundaries are judged against the ordinary 1 January boundaries.

    python pipeline/modis_version.py
"""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DET = ROOT / "data" / "interim" / "detections"
OUT = ROOT / "data" / "interim" / "qa" / "modis_version.json"

METRICS = ["rows", "rows_vs_snpp", "type0_rows_vs_snpp", "kept_rows_vs_snpp", "low_share", "mean_conf", "mean_frp", "day_share", "static_share"]


def source(det_dir: Path, sensor: str) -> str:
    return f"read_parquet('{(det_dir / f'sensor={sensor}' / 'year=*' / 'detections.parquet').as_posix()}', hive_partitioning=true)"


# ----------------------------------------------------------------------------------- timeline
def version_timeline(con, src: str) -> list[tuple]:
    """(version, satellite, data_level, rows, first date, last date), earliest first."""
    return con.execute(f"""SELECT version, satellite, data_level, count(*), min(acq_date), max(acq_date) FROM {src}
        GROUP BY ALL ORDER BY min(acq_date), satellite, version""").fetchall()


def minority_rows(con, src: str) -> list[tuple]:
    """Rows whose version is not the dominant version of their year and satellite, by country file.

    Returns (year_from, year_to, version, country_name, rows) grouped by version and country over all such years.
    """
    return con.execute(f"""WITH v AS (SELECT year, satellite, version, country_name, count(*) AS n FROM {src} GROUP BY ALL),
        dom AS (SELECT year, satellite, arg_max(version, n) AS dominant FROM
                  (SELECT year, satellite, version, sum(n) AS n FROM v GROUP BY ALL) GROUP BY year, satellite)
        SELECT min(v.year), max(v.year), v.version, v.country_name, sum(v.n)
        FROM v JOIN dom USING (year, satellite) WHERE v.version <> dom.dominant GROUP BY v.version, v.country_name
        ORDER BY sum(v.n) DESC""").fetchall()


# ------------------------------------------------------------------------------ monthly measures
def monthly_sums(con, modis: str, snpp: str) -> list[dict]:
    """Monthly sums per satellite (standard data only), with the S-NPP monthly row count as a control."""
    ctl = {(y, m): (n, n0, nk) for y, m, n, n0, nk in con.execute(f"""SELECT year(acq_date), month(acq_date), count(*),
        count(*) FILTER (WHERE type = 0), count(*) FILTER (WHERE type = 0 AND confidence_class IN ('NOMINAL', 'HIGH'))
        FROM {snpp} WHERE data_level = 'SP' GROUP BY 1, 2""").fetchall()}
    rows = con.execute(f"""SELECT satellite, year(acq_date) AS y, month(acq_date) AS m, count(*) AS n,
        count(*) FILTER (WHERE confidence_class = 'LOW') AS n_low,
        sum(TRY_CAST(confidence_raw AS DOUBLE)) AS sum_conf, sum(frp_mw) FILTER (WHERE frp_mw >= 0) AS sum_frp,
        count(*) FILTER (WHERE frp_mw >= 0) AS n_frp, count(*) FILTER (WHERE daynight = 'D') AS n_day,
        count(*) FILTER (WHERE type IN (2, 3)) AS n_static, count(*) FILTER (WHERE type IS NOT NULL) AS n_typed,
        count(*) FILTER (WHERE type = 0) AS n0,
        count(*) FILTER (WHERE type = 0 AND confidence_class IN ('NOMINAL', 'HIGH')) AS n_kept
        FROM {modis} WHERE data_level = 'SP' GROUP BY ALL ORDER BY 1, 2, 3""").fetchall()
    cols = ["satellite", "y", "m", "n", "n_low", "sum_conf", "sum_frp", "n_frp", "n_day", "n_static", "n_typed", "n0", "n_kept"]
    out = []
    for r in rows:
        d = dict(zip(cols, r, strict=True))
        d["snpp_n"], d["snpp_n0"], d["snpp_n_kept"] = ctl.get((d["y"], d["m"]), (0, 0, 0))
        out.append(d)
    return out


def window(series: list[dict], start: tuple[int, int], months: int) -> dict | None:
    """Sum the monthly records of one satellite over `months` months from `start` (year, month). None if any is missing."""
    index = {(d["y"], d["m"]): d for d in series}
    keys, (y, m) = [], start
    for _ in range(months):
        keys.append((y, m))
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)
    if any(k not in index for k in keys):
        return None
    tot: dict = {}
    for k in keys:
        for f, v in index[k].items():
            if f not in ("satellite", "y", "m") and v is not None:
                tot[f] = tot.get(f, 0) + v
    return tot


def measures(t: dict) -> dict:
    """The step-test measures of a summed window."""
    return {"rows": t["n"],
            "rows_vs_snpp": t["n"] / t["snpp_n"] if t.get("snpp_n") else None,
            "type0_rows_vs_snpp": t["n0"] / t["snpp_n0"] if t.get("snpp_n0") else None,
            "kept_rows_vs_snpp": t["n_kept"] / t["snpp_n_kept"] if t.get("snpp_n_kept") else None,
            "low_share": t["n_low"] / t["n"],
            "mean_conf": t["sum_conf"] / t["n"] if t.get("sum_conf") is not None else None,  # VIIRS confidence is a letter
            "mean_frp": t["sum_frp"] / t["n_frp"] if t["n_frp"] else None,
            "day_share": t["n_day"] / t["n"],
            "static_share": t["n_static"] / t["n_typed"] if t["n_typed"] else None}


def jan_step(series: list[dict], year: int, months: int = 12) -> dict | None:
    """After/before ratio of every measure for the 1 January of `year` (12 months after over 12 months before)."""
    before = window(series, (year - 1, 1), months)
    after = window(series, (year, 1), months)
    if before is None or after is None:
        return None
    mb, ma = measures(before), measures(after)
    return {k: (ma[k] / mb[k] if mb[k] and ma[k] is not None else None) for k in METRICS}


def boundary_summary(series: list[dict], boundaries: list[int], years: range) -> dict:
    """For each measure: the ratio at each version boundary, and the ratios at all other 1 January boundaries."""
    steps = {y: jan_step(series, y) for y in years}
    out = {}
    for k in METRICS:
        ref = {y: s[k] for y, s in steps.items() if s and y not in boundaries and s[k] is not None}
        entry = {"reference": ref, "boundaries": {}}
        for b in boundaries:
            v = steps.get(b)
            v = v[k] if v else None
            if v is None or not ref:
                entry["boundaries"][b] = None
                continue
            vals = sorted(ref.values())
            med = statistics.median(vals)
            mad = statistics.median(abs(x - med) for x in vals) or 1e-12
            entry["boundaries"][b] = {"ratio": v, "ref_median": med, "ref_min": vals[0], "ref_max": vals[-1],
                                      "robust_z": (v - med) / (1.4826 * mad),
                                      "rank_from_lowest": sum(x < v for x in vals) + 1, "n_ref": len(vals),
                                      "outside_range": v < vals[0] or v > vals[-1]}
        out[k] = entry
    return out


# ------------------------------------------------------------------------------------------ run
def run(det_dir: Path = DET, out: Path = OUT, boundaries: tuple[int, ...] = (2018, 2023)) -> dict:
    con = duckdb.connect()
    con.execute("SET memory_limit='4GB'")
    modis, snpp = source(det_dir, "MODIS"), source(det_dir, "VIIRS_SNPP")
    res: dict = {"timeline": version_timeline(con, modis), "minority": minority_rows(con, modis)}
    monthly = monthly_sums(con, modis, snpp)
    res["steps"] = {}
    for sat in ("Terra", "Aqua"):
        series = [d for d in monthly if d["satellite"] == sat]
        if not series:
            continue
        first_year = min(d["y"] for d in series)
        years = range(first_year + 1, max(d["y"] for d in series))   # needs 12 months before and after
        res["steps"][sat] = boundary_summary(series, list(boundaries), years)
    # control: S-NPP (a different instrument, not part of the MODIS version change) at the same 1 January boundaries
    snpp_series = [d for d in monthly_sums(con, snpp, snpp) if d["satellite"] == "N"]
    res["control_snpp"] = boundary_summary(snpp_series, list(boundaries), range(2013, 2025))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    return res


def main() -> None:
    res = run()
    print("timeline:")
    for r in res["timeline"]:
        print(" ", r)
    print("minority-version rows (first 6):")
    for r in res["minority"][:6]:
        print(" ", r)
    for sat, steps in {**res["steps"], "S-NPP control": res["control_snpp"]}.items():
        print(sat)
        for k, e in steps.items():
            for b, v in e["boundaries"].items():
                if v:
                    print(f"  {k:13} {b}: ratio {v['ratio']:.3f}  reference median {v['ref_median']:.3f} "
                          f"[{v['ref_min']:.3f}, {v['ref_max']:.3f}]  z {v['robust_z']:+.1f}  rank {v['rank_from_lowest']}/{v['n_ref'] + 1}")


if __name__ == "__main__":
    main()
