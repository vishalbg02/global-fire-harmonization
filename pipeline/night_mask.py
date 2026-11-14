"""Year-round persistent night sources (flares, industrial heat): a proposed addition to the static mask (T-011 review).

The approved static mask (T-005) removes fine cells where FIRMS labels at least half of the SP detections as
type 2 or 3. Many gas flares are not labelled, so they survive as `type = 0` and inflate VIIRS night cell-days.
A flare is lit year-round; a vegetation fire, even one that recurs every year in the same field, is seasonal.

Rule (a proposal for the Lead's approval). A 0.05 degree fine cell is a persistent night source if, over the SP
years used, its kept VIIRS night detections (S-NPP or NOAA-20; type 0, confidence n or h, not already masked):
  * light it on at least MIN_NIGHT_FRACTION of the nights,
  * in at least MIN_MONTHS of the 12 calendar months,
  * with at least MIN_OFF_SEASON of its nights outside its 3 busiest calendar months,
  * and with kept VIIRS day detections on at most MAX_DAY_NIGHT times as many days as nights.
The last condition separates a flare, which burns around the clock and is hard to see against a sunlit
background, from a vegetation fire, which burns mostly in the afternoon (Lead review 3: the Chiquitano dry
forest in Bolivia was flagged by the first three conditions alone).
The new cells are added to the static mask, which, like the approved mask, applies to every witness and every
row (one rule for all years and both day and night, so no artificial step appears).

    python pipeline/night_mask.py            # held-out evaluation and the combined mask for gridding
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DET = ROOT / "data" / "interim" / "detections"
QA = ROOT / "data" / "interim" / "qa"
BASE_MASK = QA / "static_mask_fine0.05_share0.5_min10.parquet"
COMBINED_MASK = QA / "static_mask_plus_night_sources.parquet"
MIN_NIGHT_FRACTION = 0.01
MIN_MONTHS = 10
MIN_OFF_SEASON = 0.5
MAX_DAY_NIGHT = 0.5
TRAIN, EVAL, FULL = (2012, 2023), (2024, 2025), (2012, 2025)
# 2.5 degree boxes checked by name (lat0, lat1, lon0, lon1); the names are assumptions from known geography
BOXES = {"Permian": (30.0, 32.5, -105.0, -102.5), "Bakken": (47.5, 50.0, -105.0, -102.5), "Eagle Ford": (27.5, 30.0, -100.0, -97.5),
         "Chiquitano (Bolivia, 5 x 2.5 degrees)": (-20.0, -15.0, -62.5, -60.0)}


def fine_sql(p: str = "") -> str:
    return (f"CAST(floor(({p}lat + 90) / 0.05) AS INTEGER) AS r, "
            f"CAST(floor((CASE WHEN {p}lon >= 180 THEN {p}lon - 360 ELSE {p}lon END + 180) / 0.05) AS INTEGER) AS c")


def source(det: Path, sensors: str) -> str:
    return f"read_parquet('{(det / f'sensor={sensors}' / 'year=*' / 'detections.parquet').as_posix()}', hive_partitioning=true)"


def nights_in(years: tuple[int, int]) -> int:
    return (dt.date(years[1], 12, 31) - dt.date(years[0], 1, 1)).days + 1


def build(con, det: Path, base_mask: Path, years: tuple[int, int], min_fraction: float = MIN_NIGHT_FRACTION,
          min_months: int = MIN_MONTHS, min_off_season: float = MIN_OFF_SEASON, max_day_night: float | None = MAX_DAY_NIGHT) -> str:
    """TEMP table `night_cells` (r, c, nights, months_active, off_season_share, days) of the cells that meet the rule."""
    con.execute(f"""CREATE OR REPLACE TEMP TABLE fm AS SELECT d.r, d.c, month(d.acq_date) AS moy, count(DISTINCT d.acq_date) AS nights FROM
        (SELECT {fine_sql()}, acq_date FROM {source(det, 'VIIRS_*')}
         WHERE daynight = 'N' AND data_level = 'SP' AND type = 0 AND confidence_class IN ('NOMINAL', 'HIGH')
           AND year BETWEEN {years[0]} AND {years[1]}) d
        LEFT JOIN read_parquet('{base_mask.as_posix()}') m ON m.r = d.r AND m.c = d.c WHERE m.r IS NULL GROUP BY ALL""")
    con.execute(f"""CREATE OR REPLACE TEMP TABLE cand AS SELECT * FROM (
        SELECT r, c, sum(nights) AS nights, count(*) AS months_active,
               1 - list_sum(list_sort(list(nights), 'DESC')[1:3]) * 1.0 / sum(nights) AS off_season_share
        FROM fm GROUP BY r, c)
        WHERE nights >= {min_fraction} * {nights_in(years)} AND months_active >= {min_months} AND off_season_share >= {min_off_season}""")
    con.execute(f"""CREATE OR REPLACE TEMP TABLE night_cells AS SELECT cand.*, coalesce(dd.days, 0) AS days FROM cand LEFT JOIN
        (SELECT d.r, d.c, count(DISTINCT d.acq_date) AS days FROM
           (SELECT {fine_sql()}, acq_date FROM {source(det, 'VIIRS_*')}
            WHERE daynight = 'D' AND data_level = 'SP' AND type = 0 AND confidence_class IN ('NOMINAL', 'HIGH')
              AND year BETWEEN {years[0]} AND {years[1]}) d
         JOIN cand USING (r, c) GROUP BY ALL) dd USING (r, c)
        WHERE {'TRUE' if max_day_night is None else f'coalesce(dd.days, 0) <= {max_day_night} * cand.nights'}""")
    return "night_cells"


def evaluate(con, det: Path, base_mask: Path, cells: str, years: tuple[int, int]) -> list[dict]:
    """Effect of the new cells on SP detections of `years` not already removed by the base mask.

    static_removed: share of type 2 or 3 detections in the new cells; fire_removed: share of type 0 detections in them.
    (Unlabelled flares are type 0, so fire_removed is an upper bound on the vegetation fires lost.)
    """
    out = []
    for label, sensors, sat in (("VIIRS", "VIIRS_*", None), ("Aqua", "MODIS", "Aqua")):
        if not any(det.glob(f"sensor={sensors}/year=*/detections.parquet")):
            continue
        sat_sql = f"AND satellite = '{sat}'" if sat else ""
        rows = con.execute(f"""SELECT d.daynight, count(*) FILTER (WHERE d.type = 0), count(*) FILTER (WHERE d.type = 0 AND n.r IS NOT NULL),
                count(*) FILTER (WHERE d.type IN (2, 3)), count(*) FILTER (WHERE d.type IN (2, 3) AND n.r IS NOT NULL)
            FROM (SELECT {fine_sql()}, daynight, type FROM {source(det, sensors)}
                  WHERE data_level = 'SP' AND type IS NOT NULL AND confidence_class IN ('NOMINAL', 'HIGH') AND year BETWEEN {years[0]} AND {years[1]} {sat_sql}) d
            LEFT JOIN read_parquet('{base_mask.as_posix()}') m ON m.r = d.r AND m.c = d.c
            LEFT JOIN {cells} n ON n.r = d.r AND n.c = d.c
            WHERE m.r IS NULL GROUP BY 1 ORDER BY 1""").fetchall()
        for dn, n0, r0, ns, rs in rows:
            out.append({"witnesses": label, "daynight": dn, "type0": n0, "type0_removed": r0, "fire_removed_share": r0 / n0 if n0 else None,
                        "static": ns, "static_removed": rs, "static_removed_share": rs / ns if ns else None})
    return out


def in_box(box: tuple[float, float, float, float]) -> str:
    a, b, c, d = box
    return f"r * 0.05 - 90 >= {a} AND r * 0.05 - 90 < {b} AND c * 0.05 - 180 >= {c} AND c * 0.05 - 180 < {d}"


def box_detail(con, det: Path, cells: str, box: tuple[float, float, float, float], years: tuple[int, int] = FULL) -> dict:
    """Kept VIIRS SP detections in the flagged cells of one box: type 0 per year and calendar month, Jul-Oct share, type 2/3 share."""
    con.execute(f"""CREATE OR REPLACE TEMP TABLE bd AS SELECT d.* FROM
        (SELECT {fine_sql()}, acq_date, type, year FROM {source(det, 'VIIRS_*')}
         WHERE data_level = 'SP' AND type IS NOT NULL AND confidence_class IN ('NOMINAL', 'HIGH') AND year BETWEEN {years[0]} AND {years[1]}) d
        JOIN (SELECT r, c FROM {cells} WHERE {in_box(box)}) n USING (r, c)""")
    one = con.execute("""SELECT count(*) FILTER (WHERE type = 0), count(*) FILTER (WHERE type = 0 AND month(acq_date) BETWEEN 7 AND 10),
        count(*) FILTER (WHERE type IN (2, 3)), count(*) FROM bd""").fetchone()
    return {"cells": con.execute(f"SELECT count(*) FROM {cells} WHERE {in_box(box)}").fetchone()[0],
            "type0_by_year": con.execute("SELECT year, count(*) FROM bd WHERE type = 0 GROUP BY 1 ORDER BY 1").fetchall(),
            "type0_by_month": con.execute("SELECT month(acq_date), count(*) FROM bd WHERE type = 0 GROUP BY 1 ORDER BY 1").fetchall(),
            "type0": one[0], "jul_oct_share": one[1] / one[0] if one[0] else None, "static_share": one[2] / one[3] if one[3] else None}


def write_combined(con, base_mask: Path, cells: str, path: Path = COMBINED_MASK) -> int:
    """The approved static mask plus the persistent night cells, as one (r, c) Parquet file for gridding."""
    con.execute(f"""COPY (SELECT DISTINCT r, c FROM (SELECT r, c FROM read_parquet('{base_mask.as_posix()}') UNION ALL SELECT r, c FROM {cells})
        ORDER BY r, c) TO '{path.as_posix()}' (FORMAT parquet, COMPRESSION zstd)""")
    return con.execute(f"SELECT count(*) FROM read_parquet('{path.as_posix()}')").fetchone()[0]


def boxes(con, cells: str, limit: int = 15) -> list[tuple]:
    """Where the new cells are: the 2.5 degree boxes holding the most of their nights."""
    return con.execute(f"""SELECT -90 + 2.5 * CAST(floor(r * 0.05 / 2.5) AS INTEGER) AS lat0, -180 + 2.5 * CAST(floor(c * 0.05 / 2.5) AS INTEGER) AS lon0,
        count(*) AS cells, sum(nights) AS nights FROM {cells} GROUP BY ALL ORDER BY nights DESC LIMIT {limit}""").fetchall()


def run(det: Path = DET, base_mask: Path = BASE_MASK, out: Path = COMBINED_MASK) -> dict:
    con = duckdb.connect()
    con.execute("SET memory_limit='5GB'")
    res: dict = {"rule": {"min_night_fraction": MIN_NIGHT_FRACTION, "min_months": MIN_MONTHS, "min_off_season": MIN_OFF_SEASON,
                          "max_day_night": MAX_DAY_NIGHT}}
    build(con, det, base_mask, TRAIN)
    res["train_cells"] = con.execute("SELECT count(*) FROM night_cells").fetchone()[0]
    res["holdout"] = evaluate(con, det, base_mask, "night_cells", EVAL)
    build(con, det, base_mask, FULL)
    res["full_cells"] = con.execute("SELECT count(*) FROM night_cells").fetchone()[0]
    res["boxes"] = boxes(con, "night_cells")
    res["named_boxes"] = {name: box_detail(con, det, "night_cells", box) for name, box in BOXES.items()}
    res["combined_mask_cells"] = write_combined(con, base_mask, "night_cells", out)
    (QA / "night_mask_report.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return res


if __name__ == "__main__":
    r = run()
    print({k: v for k, v in r.items() if k not in ("holdout", "boxes")})
    for h in r["holdout"]:
        print(h)
    for b in r["boxes"]:
        print(b)
