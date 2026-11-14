"""Tests for the persistent night-source rule (pipeline/night_mask.py) and its effect on calibration (T-011 review).

    python -m pytest pipeline/tests/test_night_mask.py -q
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import calibration as cal
import gridding as gr
import night_mask as nm

COLS = ["satellite", "lat", "lon", "acq_date", "daynight", "confidence_class", "type", "data_level", "frp_mw", "country_name"]


def write_det(folder: Path, sensor: str, df: pd.DataFrame) -> None:
    df = df.copy()
    df["year"] = df.acq_date.str[:4].astype(int)
    for year, part in df.groupby("year"):
        d = folder / f"sensor={sensor}" / f"year={year}"
        d.mkdir(parents=True, exist_ok=True)
        t = pa.table({"satellite": part.satellite, "lat": part.lat.astype(float), "lon": part.lon.astype(float),
                      "acq_date": pd.to_datetime(part.acq_date).dt.date, "daynight": part.daynight, "confidence_class": part.confidence_class,
                      "type": part["type"].astype("Int16"), "data_level": part.data_level, "frp_mw": part.frp_mw.astype(float),
                      "country_name": part.country_name})
        pq.write_table(t, d / "detections.parquet")


def rec(sat, lat, lon, date, dn="N", typ=0, conf="NOMINAL"):
    return {"satellite": sat, "lat": lat, "lon": lon, "acq_date": date, "daynight": dn, "confidence_class": conf, "type": typ,
            "data_level": "SP", "frp_mw": 5.0, "country_name": "Brazil"}


def days(y0, y1):
    d, out = dt.date(y0, 1, 1), []
    while d <= dt.date(y1, 12, 31):
        out.append(d)
        d += dt.timedelta(1)
    return out


def empty_mask(path: Path) -> Path:
    pq.write_table(pa.table({"r": pa.array([], pa.int32()), "c": pa.array([], pa.int32())}), path)
    return path


# ------------------------------------------------------------------------------------ the rule
def test_the_rule_flags_year_round_sources_only(tmp_path):
    rows = []
    for i, d in enumerate(days(2012, 2023)):
        if i % 10 == 0:
            rows.append(rec("N", 10.01, 20.01, d.isoformat()))                     # A: lit every 10th night, all year: a flare
        if d.month in (2, 3) and d.day <= 15:
            rows.append(rec("N", 11.01, 21.01, d.isoformat()))                     # B: 30 nights a year, February and March: a fire
        if i % 250 == 0:
            rows.append(rec("N", 12.01, 22.01, d.isoformat()))                     # C: rare, below 1% of nights
        if i % 10 == 0:
            rows.append(rec("N", 13.01, 23.01, d.isoformat()))                     # D: like A but already in the base mask
            rows.append(rec("N", 14.01, 24.01, d.isoformat(), dn="D"))             # E: day only: not used to build the rule
            rows.append(rec("N", 15.01, 25.01, d.isoformat(), typ=2))              # F: type 2: not a kept detection
    write_det(tmp_path / "det", "VIIRS_SNPP", pd.DataFrame(rows))
    base = tmp_path / "base.parquet"
    pq.write_table(pa.table({"r": [int((13.01 + 90) / 0.05)], "c": [int((23.01 + 180) / 0.05)]}), base)
    con = duckdb.connect()
    nm.build(con, tmp_path / "det", base, (2012, 2023))
    flagged = set(con.execute("SELECT r, c FROM night_cells").fetchall())
    assert flagged == {(int((10.01 + 90) / 0.05), int((20.01 + 180) / 0.05))}
    b_months = con.execute(f"SELECT count(DISTINCT moy), sum(nights) FROM fm WHERE r = {int((11.01 + 90) / 0.05)}").fetchone()
    assert b_months[0] == 2 and b_months[1] >= 0.01 * nm.nights_in((2012, 2023))      # B is persistent but seasonal: not flagged


def test_a_seasonal_fire_field_is_never_flagged(tmp_path):
    rows = []
    for i, d in enumerate(days(2012, 2023)):
        if 7 <= d.month <= 10:                                                     # G: lit every night and day, Jul to Oct only
            rows += [rec("N", 16.01, 26.01, d.isoformat()), rec("N", 16.01, 26.01, d.isoformat(), dn="D")]
        if i % 10 == 0:                                                            # H: year-round at night, but busy by day too
            rows.append(rec("N", 17.01, 27.01, d.isoformat()))
        if i % 2 == 0:
            rows.append(rec("N", 17.01, 27.01, d.isoformat(), dn="D"))
        if i % 10 == 0:                                                            # I: a flare: lit year-round at night, rarely by day
            rows.append(rec("N", 18.01, 28.01, d.isoformat()))
            if i % 50 == 0:
                rows.append(rec("N", 18.01, 28.01, d.isoformat(), dn="D"))
    write_det(tmp_path / "det", "VIIRS_SNPP", pd.DataFrame(rows))
    con = duckdb.connect()
    nm.build(con, tmp_path / "det", empty_mask(tmp_path / "m.parquet"), (2012, 2023))
    assert set(con.execute("SELECT r, c FROM night_cells").fetchall()) == {(int((18.01 + 90) / 0.05), int((28.01 + 180) / 0.05))}
    nm.build(con, tmp_path / "det", empty_mask(tmp_path / "m2.parquet"), (2012, 2023), max_day_night=None)
    assert int((17.01 + 90) / 0.05) in {r for r, _ in con.execute("SELECT r, c FROM night_cells").fetchall()}   # caught only by the day test


def test_evaluate_counts_what_the_new_cells_remove(tmp_path):
    rows = [rec("N", 10.01, 20.01, f"2024-0{m}-0{k}", typ=t) for m in range(1, 4) for k in range(1, 4) for t in (0, 2)]
    rows += [rec("N", 30.01, 30.01, "2024-05-05", typ=0)]
    write_det(tmp_path / "det", "VIIRS_SNPP", pd.DataFrame(rows))
    con = duckdb.connect()
    con.execute(f"CREATE TEMP TABLE cells AS SELECT {int((10.01 + 90) / 0.05)} AS r, {int((20.01 + 180) / 0.05)} AS c")
    res = {(r["witnesses"], r["daynight"]): r for r in nm.evaluate(con, tmp_path / "det", empty_mask(tmp_path / "m.parquet"), "cells", (2024, 2025))}
    v = res[("VIIRS", "N")]
    assert (v["type0"], v["type0_removed"], v["static"], v["static_removed"]) == (10, 9, 9, 9)


def test_the_combined_mask_is_the_union(tmp_path):
    base = tmp_path / "base.parquet"
    pq.write_table(pa.table({"r": [1, 2], "c": [1, 2]}), base)
    con = duckdb.connect()
    con.execute("CREATE TEMP TABLE cells AS SELECT * FROM (VALUES (2, 2), (3, 3)) t(r, c)")
    assert nm.write_combined(con, base, "cells", tmp_path / "combined.parquet") == 3


# ------------------------------------------- end to end: a planted night source does not survive
def build_world(tmp: Path, mask_path: Path):
    """Detections for 3 regions x 4 strata, 2012 to 2016, plus a flare in one stratum; then grid and calibrate."""
    rng = np.random.default_rng(4)
    regions = ["NHAF", "SHAF", "EURO"]
    rows_m, rows_v, region_rows = [], [], []
    for ri, region in enumerate(regions):
        for b in range(4):
            lat, lon = -40.0 + 2.5 * b + 0.01, -20.0 + 20.0 * ri + 0.01          # inside one 0.5 degree cell
            region_rows.append((gr.cell_id(int((lat + 90) // 0.5), int((lon + 180) // 0.5)), region))
            for y in range(2012, 2017):
                for m in range(1, 13):
                    # fires: scattered over 9 x 9 fine cells and random days, so no fine cell is lit on 1% of nights
                    for sat, dn, mean, out in (("Aqua", "D", 6, rows_m), ("Aqua", "N", 2, rows_m), ("N", "D", 20, rows_v), ("N", "N", 12, rows_v)):
                        for _ in range(int(rng.poisson(mean))):
                            i, j, day = rng.integers(0, 9), rng.integers(0, 9), rng.integers(1, 29)
                            out.append(rec(sat, lat + 0.05 * i, lon + 0.05 * j, f"{y}-{m:02d}-{day:02d}", dn=dn))
    flare = (-40.0 + 2.5 * 1 + 0.46, -20.0 + 20.0 * 1 + 0.46)                  # in SHAF, block 1, same cell, its own fine column
    for d in days(2012, 2016):
        for j in range(3):                                                           # three flares lit every night in one stratum
            rows_v.append(rec("N", flare[0] - 0.05 * j, flare[1], d.isoformat()))
    write_det(tmp / "det", "MODIS", pd.DataFrame(rows_m))
    write_det(tmp / "det", "VIIRS_SNPP", pd.DataFrame(rows_v))
    pq.write_table(pa.table({"cell_id": [c for c, _ in region_rows], "fire_region": [r for _, r in region_rows]}), tmp / "regions.parquet")
    (tmp / "map.csv").write_text("firms_name,iso3,continent,method,note\nBrazil,BRA,SA,NATURAL_EARTH,x\n", encoding="utf-8")
    paths = gr.Paths(detections=tmp / "det", mask=mask_path, fire_regions=tmp / "regions.parquet", country_map=tmp / "map.csv",
                     missing_json=None, out=tmp / "out", work=tmp / "work", tmp=tmp / "dbtmp", raw_availability=tmp / "avail")
    gr.build(paths)
    table, report = cal.calibrate(cal.Paths(products=tmp / "out", tmp=tmp / "dbtmp2"), boot=60, seed=3)
    df = pd.DataFrame(table)
    glob = {(x["witness"], x["daynight"], x["season"]): x["ratio"] for x in report["global"]}
    df["rel"] = [r / glob[k] for r, k in zip(df.ratio, zip(df.witness, df.daynight, df.season, strict=True), strict=True)]
    stratum = cal.stratum_id("SHAF", -40.0 + 2.5 * 1 + 0.25, -20.0 + 20.0 + 0.25)
    return df, stratum


def test_a_planted_persistent_night_source_does_not_survive_as_a_local_ratio(tmp_path):
    # without the night-source cells the flare stratum gets an extreme, local night ratio
    plain = tmp_path / "plain"
    plain.mkdir()
    df0, stratum = build_world(plain, empty_mask(tmp_path / "empty.parquet"))
    n0 = df0[(df0.stratum_id == stratum) & (df0.daynight == "N") & (df0.witness == "SNPP_VIIRS")]
    assert len(n0) == 4 and (n0.pooling_level == "LOCAL").all() and (n0.rel < 1 / 3).all()
    # the rule finds the flare cells; with them in the mask the stratum's night ratio is ordinary again
    con = duckdb.connect()
    nm.build(con, plain / "det", empty_mask(tmp_path / "empty2.parquet"), (2012, 2016))
    assert con.execute("SELECT count(*) FROM night_cells").fetchone()[0] == 3
    combined = tmp_path / "combined.parquet"
    nm.write_combined(con, empty_mask(tmp_path / "empty3.parquet"), "night_cells", combined)
    masked = tmp_path / "masked"
    masked.mkdir()
    df1, _ = build_world(masked, combined)
    n1 = df1[(df1.stratum_id == stratum) & (df1.daynight == "N") & (df1.witness == "SNPP_VIIRS")]
    assert len(n1) == 4 and ((n1.rel > 1 / 3) & (n1.rel < 3)).all()
    assert not ((n1.pooling_level == "LOCAL") & ((n1.rel < 1 / 3) | (n1.rel > 3))).any()
