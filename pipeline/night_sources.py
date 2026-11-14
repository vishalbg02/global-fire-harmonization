"""Diagnose extreme LOCAL calibration ratios: fires, persistent point sources (flare-like) or volcanoes? (T-011 review)

For every LOCAL calibration row whose ratio is more than 3 times, or less than a third of, the global ratio of
the same witness, day/night and season, and for a control sample of ordinary LOCAL rows, this reports:

  persistent_share  share of the witness's kept fine-cell-days (fit period, season) that come from fine cells
                    active on at least PERSISTENT_FRACTION of the available days: a flare or a lava lake keeps
                    the same 0.05 degree cell lit night after night, a vegetation fire does not
  aqua_persistent   the same for Aqua
  top_month_share   share of the witness's kept fine-cell-days in its single busiest month (an eruption signature)
  static_share      share of the witness's SP detections in the stratum with FIRMS type 2 or 3 (2012 to 2025)
  volcano_share     share with FIRMS type 1

Nothing is changed; the results go to data/interim/qa/night_sources.csv.

    python pipeline/night_sources.py
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DET = ROOT / "data" / "interim" / "detections"
PRODUCTS = ROOT / "data" / "products"
QA = ROOT / "data" / "interim" / "qa"
MASK = QA / "static_mask_fine0.05_share0.5_min10.parquet"
EXTREME = 3.0
PERSISTENT_FRACTION = 0.10
CONTROL_ROWS = 600
SENSOR = {"SNPP_VIIRS": ("VIIRS_SNPP", "N"), "NOAA20_VIIRS": ("VIIRS_NOAA20", "N20")}
FIT = {"SNPP_VIIRS": ("2012-01-01", "2016-12-31"), "NOAA20_VIIRS": ("2018-04-01", "2021-12-31")}
SEASON_SQL = ("CASE WHEN month(acq_date) IN (12, 1, 2) THEN 'DJF' WHEN month(acq_date) IN (3, 4, 5) THEN 'MAM' "
              "WHEN month(acq_date) IN (6, 7, 8) THEN 'JJA' ELSE 'SON' END")


def rows_to_check(products: Path = PRODUCTS, qa: Path = QA, control: int = CONTROL_ROWS, seed: int = 1) -> pd.DataFrame:
    """Extreme LOCAL rows and a random control sample of ordinary LOCAL rows (same witnesses and day/night)."""
    report = json.loads((qa / "calibration_report.json").read_text(encoding="utf-8"))
    glob = {(x["witness"], x["daynight"], x["season"]): x["ratio"] for x in report["global"]}
    cal = pd.read_parquet(products / "calibration.parquet")
    loc = cal[(cal.pooling_level == "LOCAL") & cal.daynight.isin(["D", "N"])].copy()
    loc["global_ratio"] = [glob[k] for k in zip(loc.witness, loc.daynight, loc.season, strict=True)]
    loc["rel"] = loc.ratio / loc.global_ratio
    loc["group"] = np.where(loc.rel > EXTREME, "high", np.where(loc.rel < 1 / EXTREME, "low", "ordinary"))
    ext = loc[loc.group != "ordinary"]
    ordinary = loc[loc.group == "ordinary"]
    ctl = ordinary.sample(min(control, len(ordinary)), random_state=seed)
    return pd.concat([ext, ctl], ignore_index=True)


def cell_strata(con, products: Path) -> None:
    """TEMP table (ar, ac, stratum) from cells.parquet."""
    con.execute(f"""CREATE OR REPLACE TEMP TABLE cs AS SELECT CAST(round((lat_min + 90) / 0.5) AS INTEGER) AS ar,
        CAST(round((lon_min + 180) / 0.5) AS INTEGER) AS ac, stratum_id AS stratum FROM read_parquet('{(products / 'cells.parquet').as_posix()}')""")


def diagnose(rows: pd.DataFrame, det: Path = DET, products: Path = PRODUCTS, mask: Path = MASK) -> pd.DataFrame:
    con = duckdb.connect()
    con.execute("SET memory_limit='4GB'")
    cell_strata(con, products)
    out = []
    for witness, (sensor, sat) in SENSOR.items():
        want = rows[rows.witness == witness][["stratum_id", "daynight", "season"]].drop_duplicates()
        if want.empty:
            continue
        con.execute("CREATE OR REPLACE TEMP TABLE want (stratum VARCHAR, daynight VARCHAR, season VARCHAR)")
        con.executemany("INSERT INTO want VALUES (?, ?, ?)", want.itertuples(index=False, name=None))
        src = f"read_parquet('{(det / f'sensor={sensor}' / 'year=*' / 'detections.parquet').as_posix()}', hive_partitioning=true)"
        aqua = f"read_parquet('{(det / 'sensor=MODIS' / 'year=*' / 'detections.parquet').as_posix()}', hive_partitioning=true)"
        lo, hi = FIT[witness]
        for label, table, sat_filter in (("w", src, f"satellite = '{sat}'"), ("a", aqua, "satellite = 'Aqua'")):
            con.execute(f"""CREATE OR REPLACE TEMP TABLE k_{label} AS
                SELECT cs.stratum, d.daynight, {SEASON_SQL} AS season, d.fr, d.fc, d.acq_date FROM
                  (SELECT CAST(floor((lat + 90) / 0.05) AS INTEGER) AS fr,
                          CAST(floor((CASE WHEN lon >= 180 THEN lon - 360 ELSE lon END + 180) / 0.05) AS INTEGER) AS fc, acq_date, daynight
                   FROM {table} WHERE {sat_filter} AND data_level = 'SP' AND type = 0 AND confidence_class IN ('NOMINAL', 'HIGH')
                     AND acq_date BETWEEN DATE '{lo}' AND DATE '{hi}') d
                LEFT JOIN read_parquet('{mask.as_posix()}') m ON m.r = d.fr AND m.c = d.fc
                JOIN cs ON cs.ar = d.fr // 10 AND cs.ac = d.fc // 10
                JOIN want w ON w.stratum = cs.stratum AND w.daynight = d.daynight AND w.season = {SEASON_SQL.replace('acq_date', 'd.acq_date')}
                WHERE m.r IS NULL""")
        days = {s: n for s, n in con.execute(f"""SELECT {SEASON_SQL.replace('acq_date', 'd')} AS season, count(*) FROM
            (SELECT unnest(range(DATE '{lo}', DATE '{hi}' + INTERVAL 1 DAY, INTERVAL 1 DAY))::DATE AS d) GROUP BY 1""").fetchall()}
        for label in ("w", "a"):
            ndays = "CASE season " + " ".join(f"WHEN '{s}' THEN {n}" for s, n in days.items()) + " END"
            con.execute(f"""CREATE OR REPLACE TEMP TABLE p_{label} AS
                WITH fcd AS (SELECT DISTINCT stratum, daynight, season, fr, fc, acq_date FROM k_{label}),
                     per AS (SELECT stratum, daynight, season, fr, fc, count(*) AS n FROM fcd GROUP BY ALL),
                     agg AS (SELECT stratum, daynight, season, sum(n) AS cell_days,
                                    sum(n) FILTER (WHERE n >= {PERSISTENT_FRACTION} * {ndays}) * 1.0 / sum(n) AS persistent_share,
                                    max(n) * 1.0 / any_value({ndays}) AS top_cell_fraction
                             FROM per GROUP BY stratum, daynight, season),
                     mon AS (SELECT stratum, daynight, season, max(n) AS top FROM
                               (SELECT stratum, daynight, season, date_trunc('month', acq_date) AS mth, count(*) AS n FROM fcd GROUP BY ALL)
                             GROUP BY stratum, daynight, season)
                SELECT agg.stratum, agg.daynight, agg.season, agg.cell_days, coalesce(agg.persistent_share, 0.0), agg.top_cell_fraction,
                       mon.top * 1.0 / agg.cell_days AS top_month_share
                FROM agg JOIN mon USING (stratum, daynight, season)""")
        types = con.execute(f"""SELECT cs.stratum, d.daynight, count(*) AS n, count(*) FILTER (WHERE d.type IN (2, 3)) * 1.0 / count(*),
                count(*) FILTER (WHERE d.type = 1) * 1.0 / count(*) FROM
            (SELECT CAST(floor((lat + 90) / 0.5) AS INTEGER) AS ar, CAST(floor((CASE WHEN lon >= 180 THEN lon - 360 ELSE lon END + 180) / 0.5) AS INTEGER) AS ac,
                    daynight, type FROM {src} WHERE satellite = '{sat}' AND data_level = 'SP' AND type IS NOT NULL) d
            JOIN cs ON cs.ar = d.ar AND cs.ac = d.ac WHERE cs.stratum IN (SELECT DISTINCT stratum FROM want) GROUP BY ALL""").fetchall()
        tmap = {(s, dn): (n, st, vo) for s, dn, n, st, vo in types}
        w = {(r[0], r[1], r[2]): r[3:] for r in con.execute("SELECT * FROM p_w").fetchall()}
        a = {(r[0], r[1], r[2]): r[3:] for r in con.execute("SELECT * FROM p_a").fetchall()}
        for s, dn, season in want.itertuples(index=False, name=None):
            wv, av = w.get((s, dn, season), (0, None, None, None)), a.get((s, dn, season), (0, None, None, None))
            tv = tmap.get((s, dn), (0, None, None))
            out.append({"stratum_id": s, "witness": witness, "daynight": dn, "season": season,
                        "witness_cell_days": int(wv[0]), "persistent_share": wv[1], "top_cell_fraction": wv[2], "top_month_share": wv[3],
                        "aqua_cell_days": int(av[0]), "aqua_persistent": av[1], "sp_detections": tv[0], "static_share": tv[1],
                        "volcano_share": tv[2]})
    return rows.merge(pd.DataFrame(out), on=["stratum_id", "witness", "daynight", "season"], how="left")


def main() -> None:
    rows = rows_to_check()
    res = diagnose(rows)
    QA.mkdir(parents=True, exist_ok=True)
    res.to_csv(QA / "night_sources.csv", index=False)
    cols = ["persistent_share", "aqua_persistent", "top_month_share", "static_share", "volcano_share"]
    print(res.groupby(["group", "daynight"])[cols].median().round(3))
    print(res.groupby(["group", "daynight"]).size())


if __name__ == "__main__":
    main()
