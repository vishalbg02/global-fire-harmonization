"""Tests for pipeline/modis_version.py on small synthetic data with known answers (T-007).

    python -m pytest pipeline/tests/test_modis_version.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modis_version as mv

COLS = ["sensor", "satellite", "acq_date", "confidence_class", "confidence_raw", "frp_mw", "daynight", "type", "version",
        "country_name", "data_level"]


def rec(date="2010-05-01", version="6.2", sat="Aqua", country="Brazil", conf="HIGH", conf_raw="90", frp=10.0, dn="D", typ=0,
        level="SP", sensor="MODIS"):
    return {"sensor": sensor, "satellite": sat, "acq_date": date, "confidence_class": conf, "confidence_raw": conf_raw,
            "frp_mw": frp, "daynight": dn, "type": typ, "version": version, "country_name": country, "data_level": level}


def write(det_dir: Path, rows: list[dict]) -> None:
    con = duckdb.connect()
    groups: dict[tuple, list] = {}
    for r in rows:
        groups.setdefault((r["sensor"], int(r["acq_date"][:4])), []).append(r)
    for (sensor, year), rs in groups.items():
        d = det_dir / f"sensor={sensor}" / f"year={year}"
        d.mkdir(parents=True, exist_ok=True)
        vals = ", ".join("(" + ", ".join("NULL" if r[c] is None else (f"'{r[c]}'" if isinstance(r[c], str) else str(r[c]))
                                          for c in COLS) + ")" for r in rs)
        con.execute(f"""COPY (SELECT sensor, satellite, CAST(acq_date AS DATE) acq_date, confidence_class, confidence_raw,
            CAST(frp_mw AS DOUBLE) frp_mw, daynight, CAST(type AS SMALLINT) type, version, country_name, data_level
            FROM (VALUES {vals}) t({', '.join(COLS)})) TO '{(d / 'detections.parquet').as_posix()}' (FORMAT parquet)""")


@pytest.fixture
def con():
    return duckdb.connect()


# --------------------------------------------------------------------------------- timeline
def test_timeline_and_minority_rows(tmp_path, con):
    rows = ([rec(date="2010-05-01"), rec(date="2010-05-02"), rec(date="2010-05-03", version="6.03", country="Morocco")]
            + [rec(date="2019-03-01", version="6.03"), rec(date="2019-03-02", version="6.03")]
            + [rec(date="2026-09-02", version="6.1NRT", level="NRT", typ=None)])
    write(tmp_path, rows)
    src = mv.source(tmp_path, "MODIS")
    tl = mv.version_timeline(con, src)
    assert [(v, n, str(a), str(b)) for v, _, _, n, a, b in tl] == [("6.2", 2, "2010-05-01", "2010-05-02"),
                                                                    ("6.03", 3, "2010-05-03", "2019-03-02"),   # one row per version, satellite and level
                                                                    ("6.1NRT", 1, "2026-09-02", "2026-09-02")]
    minority = mv.minority_rows(con, src)
    # 2010: the dominant version is 6.2, so the Morocco 6.03 row is the minority; 2019 and 2026 are uniform
    assert minority == [(2010, 2010, "6.03", "Morocco", 1)]


# -------------------------------------------------------------------------------- windows
def series(first_year, last_year, fn):
    """Monthly records for one satellite; fn(year, month) returns the field overrides."""
    out = []
    for y in range(first_year, last_year + 1):
        for m in range(1, 13):
            d = {"satellite": "Aqua", "y": y, "m": m, "n": 100, "n_low": 5, "sum_conf": 6700.0, "sum_frp": 1000.0, "n_frp": 100,
                 "n_day": 80, "n_static": 3, "n_typed": 100, "n0": 90, "n_kept": 85, "snpp_n": 200, "snpp_n0": 180, "snpp_n_kept": 170}
            d.update(fn(y, m))
            out.append(d)
    return out


def test_window_sums_twelve_months_and_requires_all_of_them():
    s = series(2010, 2011, lambda y, m: {})
    w = mv.window(s, (2010, 1), 12)
    assert w["n"] == 1200 and w["n_static"] == 36
    assert mv.window(s, (2011, 6), 12) is None            # runs past the end of the data
    assert mv.window(s[1:], (2010, 1), 12) is None        # a missing month


def test_jan_step_ratios_on_a_flat_series_are_one():
    step = mv.jan_step(series(2010, 2012, lambda y, m: {}), 2011)
    assert all(v == pytest.approx(1.0) for v in step.values())


def test_planted_step_is_found_with_the_right_size():
    def fn(y, m):
        return {"n_static": 6} if y >= 2018 else {}      # the static-source share doubles from 2018
    step = mv.jan_step(series(2016, 2019, fn), 2018)
    assert step["static_share"] == pytest.approx(2.0) and step["rows"] == pytest.approx(1.0)
    assert step["rows_vs_snpp"] == pytest.approx(1.0) and step["low_share"] == pytest.approx(1.0)


def test_boundary_is_ranked_against_the_ordinary_januaries():
    def fn(y, m):
        wobble = {2005: 3.1, 2006: 2.9, 2007: 3.0, 2008: 3.2, 2009: 2.8, 2010: 3.0, 2011: 3.1}.get(y, 3.0)
        return {"n_static": 6 if y >= 2013 else wobble}
    s = series(2004, 2014, fn)
    summary = mv.boundary_summary(s, [2013], range(2005, 2014))
    b = summary["static_share"]["boundaries"][2013]
    assert b["ratio"] == pytest.approx(2.0, rel=0.05)
    assert b["outside_range"] is True and b["rank_from_lowest"] == b["n_ref"] + 1
    assert summary["rows"]["boundaries"][2013]["outside_range"] is False   # counts did not move


def test_boundary_inside_the_normal_range_is_not_flagged():
    def fn(y, m):
        return {"n_static": {2006: 2.5, 2007: 3.5, 2008: 3.0, 2009: 2.8, 2010: 3.4}.get(y, 3.0)}
    summary = mv.boundary_summary(series(2004, 2011, fn), [2008], range(2005, 2011))
    assert summary["static_share"]["boundaries"][2008]["outside_range"] is False


def test_no_data_before_the_boundary_gives_none():
    summary = mv.boundary_summary(series(2010, 2011, lambda y, m: {}), [2010], range(2010, 2011))
    assert summary["rows"]["boundaries"][2010] is None


def test_viirs_letter_confidence_does_not_break_the_measures():
    s = series(2010, 2011, lambda y, m: {"sum_conf": None})
    step = mv.jan_step(s, 2011)
    assert step["mean_conf"] is None and step["low_share"] == pytest.approx(1.0)


# --------------------------------------------------------------------------- from parquet
def test_monthly_sums_from_parquet_with_the_snpp_control(tmp_path, con):
    modis = [rec(date="2013-01-05", conf="LOW", conf_raw="10", frp=-1.0, typ=2),
             rec(date="2013-01-06"), rec(date="2013-01-07", dn="N")]
    snpp = [rec(sensor="VIIRS_SNPP", sat="N", date="2013-01-05", conf_raw="n", conf="NOMINAL") for _ in range(4)]
    write(tmp_path, modis + snpp)
    rows = mv.monthly_sums(con, mv.source(tmp_path, "MODIS"), mv.source(tmp_path, "VIIRS_SNPP"))
    (d,) = rows
    assert (d["satellite"], d["y"], d["m"], d["n"]) == ("Aqua", 2013, 1, 3)
    assert d["n_low"] == 1 and d["n_day"] == 2 and d["n_static"] == 1 and d["n_typed"] == 3 and d["n0"] == 2
    assert d["n_frp"] == 2 and d["sum_frp"] == pytest.approx(20.0)        # the negative FRP is left out of the FRP mean
    assert d["n_kept"] == 2 and d["snpp_n"] == 4 and d["snpp_n0"] == 4 and d["snpp_n_kept"] == 4


def test_run_writes_results_and_never_changes_the_data(tmp_path):
    rows = []
    for y in range(2013, 2017):
        for m in range(1, 13):
            rows.append(rec(date=f"{y}-{m:02d}-10"))
            rows.append(rec(sensor="VIIRS_SNPP", sat="N", date=f"{y}-{m:02d}-10", conf="NOMINAL", conf_raw="n"))
    write(tmp_path / "det", rows)
    before = sorted((p.name, p.stat().st_size) for p in (tmp_path / "det").rglob("*.parquet"))
    res = mv.run(tmp_path / "det", tmp_path / "out.json", boundaries=(2015,))
    assert (tmp_path / "out.json").exists() and "steps" in res and "control_snpp" in res
    assert res["steps"]["Aqua"]["rows"]["boundaries"][2015]["ratio"] == pytest.approx(1.0)
    after = sorted((p.name, p.stat().st_size) for p in (tmp_path / "det").rglob("*.parquet"))
    assert before == after
