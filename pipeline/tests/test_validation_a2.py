"""Tests for pipeline/validation_a2.py on SYNTHETIC data with answers known by hand (T-023).

    python -m pytest pipeline/tests/test_validation_a2.py -q -p no:cacheprovider
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import harmonize as hz
import validation_a2 as v2
from test_harmonize import make, month_rows

EVENT = (2015, 10)
BOX = ["A1", "A2", "B1"]          # C1 (stratum S3) is outside the box
OLD, NEW = (2010, 2), (2023, 2)   # February: 28 days, shorter than the 31-day event month


def event_rows(snpp_scale: float = 1.0) -> list[tuple]:
    """The real event month (October 2015, 31 days): Aqua 230 raw cell-days, S-NPP 780 raw (x scale), one Terra row that is never planted."""
    aqua = {("A1", "AQUA_MODIS", "D"): 100, ("A2", "AQUA_MODIS", "D"): 60, ("B1", "AQUA_MODIS", "D"): 40, ("A1", "AQUA_MODIS", "N"): 30}
    snpp = {("A1", "SNPP_VIIRS", "D"): 200, ("A2", "SNPP_VIIRS", "D"): 120, ("B1", "SNPP_VIIRS", "D"): 160, ("A1", "SNPP_VIIRS", "N"): 300}
    snpp = {k: int(v * snpp_scale) for k, v in snpp.items()}
    terra = {("A1", "TERRA_MODIS", "D"): 999}
    return month_rows(*EVENT, {**aqua, **snpp, **terra}, dim=31)


def quiet_rows() -> list[tuple]:
    """Real quiet months with their own rows: 2010-02 (Aqua, Terra) and 2023-02 (Aqua, NOAA-20, S-NPP); C1 is outside the box and must survive."""
    old = month_rows(*OLD, {("A1", "AQUA_MODIS", "D"): 5, ("A1", "TERRA_MODIS", "D"): 7, ("C1", "AQUA_MODIS", "D"): 11}, dim=28, level="SP")
    new = month_rows(*NEW, {("A1", "AQUA_MODIS", "D"): 3, ("A1", "NOAA20_VIIRS", "D"): 9, ("A1", "SNPP_VIIRS", "D"): 2, ("C1", "SNPP_VIIRS", "D"): 13},
                     dim=28, level="NRT")
    return old + new


@pytest.fixture
def world(tmp_path):
    (tmp_path / "p").mkdir()
    paths = make(tmp_path / "p", event_rows() + quiet_rows())
    cmw = pd.read_parquet(paths.products / "cell_month_witness.parquet")
    cells = pd.read_parquet(paths.products / "cells.parquet")
    cal = pd.read_parquet(paths.products / "calibration.parquet")
    return paths, cmw, cells, cal


# ------------------------------------------------------------------------------------------------ quiet month
def series(values: dict[int, list[float | None]]) -> pd.DataFrame:
    """values: calendar month -> the 20 yearly estimates 2003-2022 (None = no estimate)."""
    rows = [{"year": 2003 + i, "month": m, "estimate": (np.nan if x is None else x)} for m, xs in values.items() for i, x in enumerate(xs)]
    return pd.DataFrame(rows)


def test_quiet_month_is_the_calendar_month_with_the_lowest_median():
    s = series({m: [10.0 * m] * 20 for m in range(1, 13)} | {7: [3.0] * 20})
    q = v2.quiet_calendar_month(s)
    assert q["month"] == 7 and q["median"] == 3.0 and q["n_years"] == 20


def test_quiet_month_uses_the_median_not_the_mean():
    s = series({m: [50.0] * 20 for m in range(1, 13)} | {4: [0.0] * 11 + [1000.0] * 9})        # median 0 although the mean is large
    assert v2.quiet_calendar_month(s)["month"] == 4


def test_quiet_month_tie_goes_to_the_earliest_calendar_month():
    s = series({m: [8.0] * 20 for m in range(1, 13)} | {9: [2.0] * 20, 3: [2.0] * 20})
    assert v2.quiet_calendar_month(s)["month"] == 3


def test_quiet_month_needs_15_years_with_an_estimate():
    ok = [1.0] * 15 + [None] * 5
    few = [0.0] * 14 + [None] * 6
    s = series({m: [9.0] * 20 for m in range(1, 13)} | {2: few, 6: ok})
    q = v2.quiet_calendar_month(s)
    assert q["month"] == 6 and q["n_years"] == 15 and "2" not in q["medians"]      # February (14 years) is not eligible although it is lower


def test_quiet_month_ignores_years_outside_2003_2022_and_has_no_floor_of_5_cell_days():
    rows = series({m: [9.0] * 20 for m in range(1, 13)} | {5: [0.5] * 20})
    rows = pd.concat([rows, pd.DataFrame([{"year": 2023, "month": 8, "estimate": -100.0}, {"year": 2002, "month": 8, "estimate": -100.0}])])
    q = v2.quiet_calendar_month(rows)
    assert q["month"] == 5 and q["median"] == 0.5          # below the 5 cell-day floor of D-028 step 4, still chosen


def test_quiet_month_none_when_no_calendar_month_has_15_years():
    assert v2.quiet_calendar_month(series({m: [1.0] * 10 + [None] * 10 for m in range(1, 13)})) is None


# ------------------------------------------------------------------------------------------------ event month
def test_event_month_is_the_peak_window_month_with_most_raw_aqua_and_ties_go_earliest():
    peak = ((2015, 9), (2015, 10))
    assert v2.event_month({(2015, 9): 10.0, (2015, 10): 30.0, (2015, 8): 999.0}, peak) == (2015, 10)      # Aug is outside the peak window
    assert v2.event_month({(2015, 9): 30.0, (2015, 10): 30.0}, peak) == (2015, 9)
    assert v2.event_month({(2015, 10): 4.0}, peak) == (2015, 10)
    assert v2.event_month({(2015, 9): 0.0}, peak) is None and v2.event_month({}, peak) is None


# ------------------------------------------------------------------------------------------------ planting
def test_planting_preserves_the_events_totals_and_fields(world):
    _, cmw, _, _ = world
    table, info = v2.plant_case(cmw, BOX, EVENT, 2)
    assert info["old"]["ok"] and info["new"]["ok"]
    for tgt, w in ((OLD, "AQUA_MODIS"), (NEW, "SNPP_VIIRS")):
        src = cmw[(cmw.year == EVENT[0]) & (cmw.month == EVENT[1]) & (cmw.witness == w)]
        got = table[(table.year == tgt[0]) & (table.month == tgt[1]) & (table.witness == w) & table.cell_id.isin(BOX)]
        assert got.cell_days.sum() == src.cell_days.sum() and got.detections.sum() == src.detections.sum() and got.frp_sum_mw.sum() == src.frp_sum_mw.sum()
        key = ["cell_id", "daynight"]
        merged = src.merge(got, on=key, suffixes=("_s", "_g"), validate="one_to_one")
        assert len(merged) == len(src) == len(got)
        assert (merged.cell_days_s == merged.cell_days_g).all() and (merged.detections_s == merged.detections_g).all()
    assert info["old"]["cell_days"] == 230 and info["new"]["cell_days"] == 780


def test_planted_months_are_coherent_calendar_months_with_one_witness(world):
    _, cmw, _, _ = world
    table, info = v2.plant_case(cmw, BOX, EVENT, 2)
    old = table[(table.year == 2010) & (table.month == 2) & table.cell_id.isin(BOX)]
    new = table[(table.year == 2023) & (table.month == 2) & table.cell_id.isin(BOX)]
    assert set(old.witness) == {"AQUA_MODIS"} and set(new.witness) == {"SNPP_VIIRS"}       # Terra, NOAA-20 and the real Aqua 2023 are removed
    for part in (old, new):
        assert (part.days_in_month == 28).all() and (part.days_available == 28).all()
    assert (old.data_level == "SP").all()          # the quiet month's own level for Aqua
    assert (new.data_level == "NRT").all()         # the quiet month's own level for S-NPP, not the event's
    assert info["old"]["event_days_in_month"] == 31 and info["old"]["days_in_month"] == 28


def test_planting_leaves_everything_else_untouched(world):
    _, cmw, _, _ = world
    table, _ = v2.plant_case(cmw, BOX, EVENT, 2)
    outside = lambda t: t[t.cell_id == "C1"].sort_values(["year", "month", "witness", "daynight"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(outside(table), outside(cmw))
    ev = lambda t: t[(t.year == 2015)].sort_values(["witness", "cell_id", "daynight"]).reset_index(drop=True)            
    pd.testing.assert_frame_equal(ev(table), ev(cmw))                                       # the real event month is still there, including Terra
    assert len(cmw) == len(world[1])               # the input frame was not modified


def test_level_falls_back_to_the_events_when_the_quiet_month_has_no_row_of_the_witness(tmp_path):
    p = tmp_path / "p"
    p.mkdir()
    paths = make(p, event_rows() + month_rows(*OLD, {("A1", "TERRA_MODIS", "D"): 7}, dim=28, level="NRT"))
    cmw = pd.read_parquet(paths.products / "cell_month_witness.parquet")
    table, info = v2.plant_month(cmw, BOX, EVENT, OLD, "AQUA_MODIS")
    assert info["ok"]
    assert (table[(table.year == 2010) & (table.witness == "AQUA_MODIS")].data_level == "SP").all()


def test_an_incomplete_or_missing_event_record_is_not_planted(tmp_path):
    p = tmp_path / "p"
    p.mkdir()
    rows = month_rows(*EVENT, {("A1", "AQUA_MODIS", "D"): 5, ("A2", "AQUA_MODIS", "D"): 5}, dim=31, avail={"AQUA_MODIS": 30})
    paths = make(p, rows + month_rows(*OLD, {("A1", "AQUA_MODIS", "D"): 1}, dim=28))
    cmw = pd.read_parquet(paths.products / "cell_month_witness.parquet")
    table, info = v2.plant_month(cmw, BOX, EVENT, OLD, "AQUA_MODIS")
    assert not info["ok"] and "not complete" in info["reason"]
    pd.testing.assert_frame_equal(table, cmw)                                  # unchanged
    table, info = v2.plant_month(cmw, BOX, EVENT, NEW, "SNPP_VIIRS")
    assert not info["ok"] and "no SNPP_VIIRS rows" in info["reason"]


def test_month_days_are_calendar_days():
    assert (v2.month_days(2010, 2), v2.month_days(2012, 2), v2.month_days(2023, 12), v2.month_days(2023, 4)) == (28, 29, 31, 30)


# ------------------------------------------------------------------------------------------------ overlap and raw mismatch
def test_overlap_rule_at_the_boundary():
    assert v2.intervals_overlap((0.0, 10.0), (10.0, 20.0))           # touching intervals overlap
    assert not v2.intervals_overlap((0.0, 10.0), (10.0001, 20.0))
    assert v2.intervals_overlap((5.0, 6.0), (0.0, 100.0)) and v2.intervals_overlap((0.0, 100.0), (5.0, 6.0))


def test_interval_is_1645_sd_with_a_floor_at_zero():
    lo, hi = v2.interval90(100.0, 10.0)
    assert lo == pytest.approx(100 - 16.448536269514722) and hi == pytest.approx(100 + 16.448536269514722)
    assert v2.interval90(5.0, 10.0)[0] == 0.0


def test_raw_mismatch_rule_at_1_5_and_its_inverse():
    assert v2.raw_mismatch(100, 150)["mismatch"] is True                 # exactly 1.5
    assert v2.raw_mismatch(100, 149)["mismatch"] is False
    assert v2.raw_mismatch(150, 100)["mismatch"] is True                 # exactly 1/1.5: counts, as a deflation
    assert v2.raw_mismatch(150, 101)["mismatch"] is False
    r = v2.raw_mismatch(100, 340)
    assert r["ratio"] == pytest.approx(3.4) and r["direction"] == "inflation" and r["large_inflation"] is True
    assert v2.raw_mismatch(100, 190)["large_inflation"] is False
    assert v2.raw_mismatch(200, 100)["direction"] == "deflation"
    assert v2.raw_mismatch(0, 100)["mismatch"] is None and v2.raw_mismatch(100, 0)["ratio"] is None


# ------------------------------------------------------------------------------------------------ status
OK = {"ok": True}
BIG_RAW = v2.raw_mismatch(230, 780)


def test_status_pass_fail_inconclusive():
    r = v2.case_status(OK, OK, {"estimate": 230.0, "sd": 20.0}, {"estimate": 250.0, "sd": 20.0}, BIG_RAW)
    assert r["status"] == "PASS" and r["intervals_overlap"] is True and r["reasons"] == []
    r = v2.case_status(OK, OK, {"estimate": 230.0, "sd": 5.0}, {"estimate": 460.0, "sd": 5.0}, BIG_RAW)
    assert r["status"] == "FAIL" and r["intervals_overlap"] is False
    r = v2.case_status(OK, OK, {"estimate": 230.0, "sd": 5.0}, {"estimate": 460.0, "sd": 5.0}, v2.raw_mismatch(230, 240))
    assert r["status"] == "INCONCLUSIVE" and "no mismatch" in r["reasons"][0]            # no raw mismatch: INCONCLUSIVE even if the intervals do not overlap
    r = v2.case_status(OK, OK, {"estimate": 230.0, "sd": 20.0}, {"estimate": 230.0, "sd": 20.0}, v2.raw_mismatch(230, 240))
    assert r["status"] == "INCONCLUSIVE"                                                  # and not a PASS when the intervals do overlap


def test_status_boundary_of_the_overlap_is_a_pass():
    lo_hi = hz.Z90 * 10.0
    r = v2.case_status(OK, OK, {"estimate": 100.0, "sd": 10.0}, {"estimate": 100.0 + 2 * lo_hi, "sd": 10.0}, BIG_RAW)
    assert r["status"] == "PASS"       # the upper end of one interval touches the lower end of the other (up to rounding)
    r = v2.case_status(OK, OK, {"estimate": 100.0, "sd": 10.0}, {"estimate": 100.0 + 2 * lo_hi + 0.01, "sd": 10.0}, BIG_RAW)
    assert r["status"] == "FAIL"


def test_status_inconclusive_reasons():
    bad = {"ok": False, "reason": "the event month has no SNPP_VIIRS rows in the box"}
    e = {"estimate": 1.0, "sd": 1.0}
    assert v2.case_status(OK, bad, e, e, BIG_RAW)["status"] == "INCONCLUSIVE"
    assert v2.case_status(OK, OK, e, None, BIG_RAW)["status"] == "INCONCLUSIVE"
    assert v2.case_status(OK, OK, {"estimate": None, "sd": None}, e, BIG_RAW)["status"] == "INCONCLUSIVE"
    assert v2.case_status(OK, OK, e, e, v2.raw_mismatch(0, 5))["status"] == "INCONCLUSIVE"
    assert v2.case_status(OK, OK, e, e, BIG_RAW, quiet_ok=False)["status"] == "INCONCLUSIVE"
    assert v2.case_status(OK, OK, e, e, BIG_RAW, event_ok=False)["status"] == "INCONCLUSIVE"


# ------------------------------------------------------------------------------------------------ family
def fam(*s: str) -> dict:
    return v2.family_entry([{"test_id": f"A2-{c}", "status": st} for c, st in zip(v2.CASE_IDS, s, strict=False)])


def test_family_needs_all_three_cases_to_pass():
    assert fam("PASS", "PASS", "PASS")["status"] == "PASS"
    assert fam("PASS", "PASS", "FAIL")["status"] == "FAIL"
    assert fam("PASS", "PASS", "INCONCLUSIVE")["status"] == "FAIL"      # an INCONCLUSIVE case does not count as a PASS
    assert fam("PASS", "PASS")["status"] == "INCONCLUSIVE"              # C6 not run: still open
    assert fam("PASS", "FAIL")["status"] == "FAIL"                      # cannot reach three passes any more
    m = fam("PASS", "INCONCLUSIVE", "FAIL")["measured"]
    assert (m["n_pass"], m["n_fail"], m["n_inconclusive"], m["n_not_run"]) == (1, 1, 1, 0)
    assert fam("PASS", "PASS", "PASS")["test_id"] == "A2"


# ------------------------------------------------------------------------------------------------ end to end on synthetic products
def run_pair(world, tmp_path, name: str, cal: pd.DataFrame | None = None) -> tuple[dict, dict, dict, dict]:
    _, cmw, cells, cal0 = world
    table, info = v2.plant_case(cmw, BOX, EVENT, 2)
    keep = table[(table.year.isin([2010, 2023]) & (table.month == 2)) | (table.year == 2015)]
    h = v2.harmonize_table(keep, cells, cal0 if cal is None else cal, BOX, [(2010, 2), (2023, 2), EVENT], tmp_path / name)
    old = next(r for r in h["combined"] if (r["year"], r["month"]) == (2010, 2))
    new = next(r for r in h["combined"] if (r["year"], r["month"]) == (2023, 2))
    return old, new, h, info


def test_end_to_end_same_fire_gives_the_same_harmonized_value_and_a_raw_mismatch(world, tmp_path):
    old, new, h, info = run_pair(world, tmp_path, "w1")
    # by hand: Aqua ratio 1: 100 + 60 + 40 + 30 = 230; S-NPP: 0.5 x 200 + 0.5 x 120 + 0.25 x 160 + 0.1 x 300 = 100 + 60 + 40 + 30 = 230
    assert old["estimate"] == pytest.approx(230.0) and new["estimate"] == pytest.approx(230.0)
    assert old["witnesses_used"] == ["AQUA_MODIS"] and new["witnesses_used"] == ["SNPP_VIIRS"]
    assert (old["raw_combined_cell_days"], new["raw_combined_cell_days"]) == (230, 780)       # one witness each: Terra and the quiet month's rows are gone
    raw = v2.raw_mismatch(old["raw_combined_cell_days"], new["raw_combined_cell_days"])
    assert raw["mismatch"] and raw["direction"] == "inflation"
    res = v2.case_status(info["old"], info["new"], v2._est(old), v2._est(new), raw)
    assert res["status"] == "PASS" and res["intervals_overlap"]
    ctx = v2._measured(old, new, raw, {"median": 10.0}, h["single"], EVENT)
    assert ctx["identity_check_aqua"]["equal"] is True                         # planted 2010 Aqua == the real event month's Aqua-only estimate
    assert ctx["real_event_month_context"]["SNPP_VIIRS"]["estimate"] == pytest.approx(230.0)
    assert ctx["harmonized_ratio_new_over_old"] == pytest.approx(1.0) and ctx["difference_in_sd"] == pytest.approx(0.0)


def test_end_to_end_a_conversion_that_is_off_by_a_factor_two_fails(tmp_path):
    p = tmp_path / "p"
    p.mkdir()
    paths = make(p, event_rows(snpp_scale=2.0) + quiet_rows())
    cmw = pd.read_parquet(paths.products / "cell_month_witness.parquet")
    cells = pd.read_parquet(paths.products / "cells.parquet")
    cal = pd.read_parquet(paths.products / "calibration.parquet")
    table, info = v2.plant_case(cmw, BOX, EVENT, 2)
    h = v2.harmonize_table(table[table.month == 2], cells, cal, BOX, [(2010, 2), (2023, 2)], tmp_path / "w2")
    old = next(r for r in h["combined"] if r["year"] == 2010)
    new = next(r for r in h["combined"] if r["year"] == 2023)
    assert new["estimate"] == pytest.approx(460.0) and old["estimate"] == pytest.approx(230.0)
    res = v2.case_status(info["old"], info["new"], v2._est(old), v2._est(new), v2.raw_mismatch(old["raw_combined_cell_days"], new["raw_combined_cell_days"]))
    assert res["status"] == "FAIL" and res["intervals_overlap"] is False


def test_the_target_months_season_picks_the_ratio_and_the_event_season_variant_swaps_it(world, tmp_path):
    _, _, _, cal0 = world
    cal = cal0.copy()
    cal.loc[(cal.season == "DJF") & (cal.witness == "SNPP_VIIRS") & (cal.daynight == "D"), "ratio"] *= 2.0          # winter ratio doubled (February is DJF)
    _, new, _, _ = run_pair(world, tmp_path, "w3", cal)
    day = 0.5 * 200 + 0.5 * 120 + 0.25 * 160                                                                          # 200 by hand
    assert new["estimate"] == pytest.approx(2 * day + 30.0)                                                           # 430: the season of the target month (DJF)
    assert v2.season_of(2) == "DJF" and v2.season_of(10) == "SON" and v2.season_of(12) == "DJF" and v2.season_of(5) == "MAM" and v2.season_of(7) == "JJA"
    swapped = v2.calibration_with_season(cal, "SON", "DJF")                                                           # the event's (autumn) ratios in a DJF month
    old2, new2, _, _ = run_pair(world, tmp_path, "w4", swapped)
    assert new2["estimate"] == pytest.approx(230.0) and old2["estimate"] == pytest.approx(230.0)
    assert (swapped[swapped.season == "SON"].ratio.to_numpy() == cal[cal.season == "SON"].ratio.to_numpy()).all()    # other seasons unchanged


def test_the_products_on_disk_are_not_touched_and_the_run_is_deterministic(world, tmp_path):
    paths, *_ = world

    def digest() -> dict:
        return {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(paths.products.glob("*.parquet"))}
    before = digest()
    a = run_pair(world, tmp_path, "w5")
    b = run_pair(world, tmp_path, "w6")
    assert digest() == before
    assert (a[0]["estimate"], a[0]["sd"], a[1]["estimate"], a[1]["sd"]) == (b[0]["estimate"], b[0]["sd"], b[1]["estimate"], b[1]["sd"])
