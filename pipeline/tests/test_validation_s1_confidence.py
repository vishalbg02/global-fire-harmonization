"""Tests of validation_s1_confidence on SYNTHETIC data with known answers (T-025b). Nothing here is a result."""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gridding as gr
import validation_s1_confidence as sc

COLS = ["satellite", "lat", "lon", "acq_date", "acq_time_utc", "daynight", "confidence_class", "confidence_raw", "frp_mw", "scan_km",
        "track_km", "type", "version", "country_name", "data_level"]


def det(sat, lat, lon, d, dn, conf, frp, typ=0, level="SP"):
    return [sat, lat, lon, d, 1000, dn, conf, "x", frp, 1.0, 1.0, typ, "v", "X", level]


@pytest.fixture()
def world(tmp_path):
    """SYNTHETIC. Aqua detections in July 2019 around lat 10.0, lon 20.0 (fine rows 2000.., cols 4000..; analysis cell r200_c400)."""
    d1, d2 = date(2019, 7, 3), date(2019, 7, 4)
    rows = [
        det("Aqua", 10.02, 20.02, d1, "D", "HIGH", 5.0),            # fine cell A, day 1: kept
        det("Aqua", 10.03, 20.03, d1, "D", "NOMINAL", 7.0),         # same fine cell A and day: 1 cell-day, 2nd detection
        det("Aqua", 10.12, 20.12, d1, "D", "LOW", 3.0),             # fine cell B, LOW: kept only without the confidence filter
        det("Aqua", 10.12, 20.12, d2, "D", "LOW", 4.0),             # fine cell B, day 2, LOW
        det("Aqua", 10.22, 20.22, d1, "D", "LOW", 9.0, typ=1),      # volcano, SP: never kept
        det("Aqua", 10.32, 20.32, d1, "D", "HIGH", 9.0),            # in the static mask: never kept
        det("Aqua", 10.42, 20.42, d1, "N", "LOW", 2.0, typ=None, level="NRT"),   # NRT row without type, LOW, night
        det("N", 10.02, 20.02, d1, "D", "LOW", 1.0),                # S-NPP, LOW only (another witness)
        det("Aqua", 10.02, 180.02, d1, "D", "HIGH", 1.0),           # longitude wrap: -179.98
    ]
    folder = tmp_path / "det" / "sensor=MODIS" / "year=2019"
    folder.mkdir(parents=True)
    pd.DataFrame([r for r in rows if r[0] == "Aqua"], columns=COLS).astype({"type": "Int16"}).to_parquet(folder / "detections.parquet", index=False)
    f2 = tmp_path / "det" / "sensor=VIIRS_SNPP" / "year=2019"
    f2.mkdir(parents=True)
    pd.DataFrame([r for r in rows if r[0] == "N"], columns=COLS).astype({"type": "Int16"}).to_parquet(f2 / "detections.parquet", index=False)
    mask = tmp_path / "mask.parquet"
    pd.DataFrame({"r": [int((10.32 + 90) // 0.05)], "c": [int((20.32 + 180) // 0.05)]}).to_parquet(mask, index=False)
    paths = gr.Paths(detections=tmp_path / "det", mask=mask)
    return paths, sc.connect(tmp_path / "duck")


CELL = "g050_r0200_c0400"
CUT = "TRUE"


def key(df):
    return {(r.witness, r.daynight, r.cell_id, r.month): (r.cell_days, r.detections, round(r.frp_sum_mw, 6)) for r in df.itertuples()}


def test_regrid_with_the_filter_matches_the_t006_rules(world):
    paths, con = world
    k = key(sc.regrid_year(con, paths, 2019, True, CUT))
    # Aqua day: fine cell A on day 1 (2 detections, 12 MW) = 1 cell-day; LOW rows, the volcano and the masked cell are out
    assert k[("AQUA_MODIS", "D", CELL, 7)] == (1, 2, 12.0)
    assert ("AQUA_MODIS", "N", CELL, 7) not in k           # the only night row is LOW
    assert ("SNPP_VIIRS", "D", CELL, 7) not in k           # the S-NPP row is LOW
    assert k[("AQUA_MODIS", "D", "g050_r0200_c0000", 7)] == (1, 1, 1.0)   # lon 180.02 wraps to -179.98 (column 0)


def test_regrid_without_the_filter_adds_only_low_confidence_rows(world):
    paths, con = world
    k = key(sc.regrid_year(con, paths, 2019, False, CUT))
    # + fine cell B on two days (2 cell-days, 2 detections, 7 MW); the volcano (type 1) and the static-mask cell are still out
    assert k[("AQUA_MODIS", "D", CELL, 7)] == (3, 4, 19.0)
    assert k[("AQUA_MODIS", "N", CELL, 7)] == (1, 1, 2.0)    # the NRT row without a type is kept (as T-006)
    assert k[("SNPP_VIIRS", "D", CELL, 7)] == (1, 1, 1.0)


def test_cut_restricts_months_and_boxes(world):
    paths, con = world
    assert sc.regrid_year(con, paths, 2019, False, "ym IN (201901)").empty
    assert key(sc.regrid_year(con, paths, 2019, False, "ym IN (201907) AND lon < 0")) == {}


def test_assemble_zero_fills_and_all_is_day_plus_night(world, tmp_path):
    paths, con = world
    obs = sc.regrid_year(con, paths, 2019, False, CUT)
    rows = []
    for dn in ("D", "N", "ALL"):
        for w in ("AQUA_MODIS", "SNPP_VIIRS", "NOAA20_VIIRS"):
            for cid in (CELL, "g050_r0001_c0001"):
                rows.append([cid, 2019, 7, w, dn, 0, 0, 0.0, 31, 31, "SP"])
    sk = tmp_path / "sk.parquet"
    pd.DataFrame(rows, columns=["cell_id", "year", "month", "witness", "daynight", "detections", "cell_days", "frp_sum_mw", "days_available",
                                "days_in_month", "data_level"]).to_parquet(sk, index=False)
    out = sc.assemble_year(con, f"read_parquet('{sk.as_posix()}')", obs, 2019)
    k = key(out)
    assert k[("AQUA_MODIS", "ALL", CELL, 7)][0] == k[("AQUA_MODIS", "D", CELL, 7)][0] + k[("AQUA_MODIS", "N", CELL, 7)][0] == 4
    assert k[("NOAA20_VIIRS", "D", CELL, 7)] == (0, 0, 0.0)                 # operated, nothing detected: zero, not missing
    assert k[("AQUA_MODIS", "D", "g050_r0001_c0001", 7)] == (0, 0, 0.0)
    assert len(out) == 3 * 3 * 2
    assert (out.days_available == 31).all()


def test_control_check_detects_a_planted_difference(tmp_path):
    base = pd.DataFrame({"cell_id": ["a", "b"], "year": 2019, "month": 7, "witness": "AQUA_MODIS", "daynight": "D", "detections": [3, 4],
                         "cell_days": [2, 3], "frp_sum_mw": [1.0, 2.0]})
    f, c, bad = tmp_path / "f.parquet", tmp_path / "c.parquet", tmp_path / "bad.parquet"
    base.to_parquet(f, index=False)
    base.to_parquet(c, index=False)
    assert sc.control_check(f, c)["ok"] is True
    base.assign(cell_days=[2, 4]).to_parquet(bad, index=False)
    r = sc.control_check(f, bad)
    assert r["ok"] is False and r["cell_days_differences"] == 1
    base.iloc[:1].to_parquet(bad, index=False)
    assert sc.control_check(f, bad)["ok"] is False                           # a missing row is also a failure


A1 = {"status": {"C1": "INCONCLUSIVE", "C2": "PASS"}, "family": "FAIL"}
B1 = {"b1": {"2012-01": {"status": "PASS"}, "2018-04": {"status": "INCONCLUSIVE"}}}
VERD = {"C1|2015-09": {"verdict": "ABOVE_NORMAL"}, "C2|2019-08": {"verdict": "CANNOT_DETERMINE"}}


def run(a1=A1, b1=B1, verd=VERD):
    return {"a1": a1, "b1": b1, "verdicts": verd}


def test_rule_pass_when_everything_is_unchanged():
    r = sc.compare_runs(run(), run())
    assert r["status"] == "PASS" and r["n_compared"] == 2 + 1 + 2 + 2 and r["n_changed"] == 0


@pytest.mark.parametrize("which", ["case", "family", "b1", "verdict"])
def test_rule_fails_on_any_single_change(which):
    changed = run(
        a1={"status": {"C1": "INCONCLUSIVE", "C2": "FAIL" if which == "case" else "PASS"}, "family": "PASS" if which == "family" else "FAIL"},
        b1={"b1": {"2012-01": {"status": "FAIL" if which == "b1" else "PASS"}, "2018-04": {"status": "INCONCLUSIVE"}}},
        verd={"C1|2015-09": {"verdict": "WITHIN_NORMAL" if which == "verdict" else "ABOVE_NORMAL"}, "C2|2019-08": {"verdict": "CANNOT_DETERMINE"}})
    r = sc.compare_runs(run(), changed)
    assert r["status"] == "FAIL" and r["n_changed"] == 1


def test_rule_inconclusive_not_run_and_a_change_beats_a_missing_part():
    missing = run()
    missing["b1"] = None
    assert sc.compare_runs(run(), missing)["status"] == "INCONCLUSIVE"
    changed = run(verd={"C1|2015-09": {"verdict": "BELOW_NORMAL"}, "C2|2019-08": {"verdict": "CANNOT_DETERMINE"}})
    assert sc.compare_runs(run(), {**changed, "b1": None})["status"] == "FAIL"
    assert sc.compare_runs(run(), run(), control_ok=False)["status"] == "NOT_RUN"


def test_s1_overall():
    assert sc.s1_overall("PASS", "PASS") == "PASS"
    assert sc.s1_overall("FAIL", "PASS") == "FAIL"
    assert sc.s1_overall("PASS", "FAIL") == "FAIL"
    assert sc.s1_overall("PASS", "NOT_RUN") == "NOT_RUN"
    assert sc.s1_overall(None, "PASS") == "NOT_RUN"
    assert sc.s1_overall("PASS", "INCONCLUSIVE") == "INCONCLUSIVE"


def test_selection_covers_the_baseline_and_b1_windows():
    ma, mb = sc.a1_months(), sc.b1_months()
    assert (2015, 9) in ma and (2003, 9) in ma and (2022, 10) in ma and (2002, 9) not in ma
    assert (2012, 1) in mb and (2011, 1) in mb and (2012, 12) in mb and (2017, 4) in mb and (2019, 3) in mb and (2019, 4) not in mb
    assert len(mb) == 24 + 24
    assert sc.months_sql([]) == "FALSE"
