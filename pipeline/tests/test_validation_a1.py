"""Tests for pipeline/validation_a1.py on SYNTHETIC data with answers known by hand (T-020).

    python -m pytest pipeline/tests/test_validation_a1.py -q -p no:cacheprovider
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import harmonize as hz
import validation_a1 as va
from test_harmonize import S1, make, month_rows  # noqa: F401  (S1 documents the synthetic calibration)

ANALYSIS = ((2015, 6), (2015, 12))
PEAK = ((2015, 9), (2015, 10))
Z = hz.Z90


def frame(est: dict[int, float], sd: float = 50.0, med: float = 100.0, p25: float = 80.0, p75: float = 120.0, baseline: bool = True) -> pd.DataFrame:
    """An entity_month-shaped frame for June to December 2015: est maps month -> estimate; one baseline for every month."""
    rows = []
    for m in range(6, 13):
        e = est.get(m, 100.0)
        rows.append({"year": 2015, "month": m, "estimate": e, "sd": sd, "baseline_median": med if baseline else np.nan,
                     "baseline_p25": p25 if baseline else np.nan, "baseline_p75": p75 if baseline else np.nan,
                     "pct_of_normal": e / med * 100.0 if baseline else np.nan})
    return pd.DataFrame(rows)


def run(a: dict[int, float], s: dict[int, float], **kw) -> dict:
    return va.compare_paths(frame(a, **kw), frame(s, **kw), ANALYSIS, PEAK)


# ------------------------------------------------------------------------------------------------ direction
def test_both_above_with_close_peaks_and_overlap_passes():
    r = run({9: 300, 10: 400}, {9: 350, 10: 300})
    assert r["aqua"]["direction"] == r["snpp"]["direction"] == va.ABOVE
    assert (r["same_direction"], r["peak_within_tolerance"], r["intervals_overlap"]) == (True, True, True)
    assert r["status"] == "PASS" and r["reasons"] == []
    assert r["aqua"]["peak_month"] == "2015-10" and r["snpp"]["peak_month"] == "2015-09"
    assert r["aqua"]["pct_of_normal"] == pytest.approx(350.0)      # (300 + 400) / (100 + 100) x 100


def test_both_below_passes():
    r = run({9: 10, 10: 10, 6: 100, 7: 100, 8: 100, 11: 100, 12: 100}, {9: 10, 10: 10})
    assert r["aqua"]["direction"] == r["snpp"]["direction"] == va.BELOW      # 20 < summed p25 of 160
    assert r["peak_month_distance"] == 0
    assert r["status"] == "PASS"


def test_opposite_directions_fail():
    r = run({9: 300, 10: 400}, {9: 10, 10: 10})
    assert (r["aqua"]["direction"], r["snpp"]["direction"]) == (va.ABOVE, va.BELOW)
    assert r["same_direction"] is False and r["status"] == "FAIL"
    assert any("directions differ" in x for x in r["reasons"])


def test_one_path_within_normal_fails():
    r = run({9: 300, 10: 400}, {9: 100, 10: 100})
    assert r["snpp"]["direction"] == va.WITHIN
    assert r["same_direction"] is False and r["status"] == "FAIL"


def test_both_within_normal_is_inconclusive_not_a_pass():
    r = run({9: 100, 10: 100}, {9: 110, 10: 100})
    assert r["aqua"]["direction"] == r["snpp"]["direction"] == va.WITHIN
    assert r["status"] == "INCONCLUSIVE" and any("no anomaly" in x for x in r["reasons"])


def test_direction_at_the_p75_boundary_is_not_above():
    r = run({9: 120, 10: 120}, {9: 120, 10: 120})      # exactly the summed p75 of 240
    assert r["aqua"]["direction"] == va.WITHIN
    r = run({9: 120.5, 10: 120}, {9: 120.5, 10: 120})
    assert r["aqua"]["direction"] == va.ABOVE


# ------------------------------------------------------------------------------------------------ peak month
def test_peak_month_one_apart_passes_and_two_apart_fails():
    near = run({9: 300, 10: 400}, {9: 300, 10: 300, 8: 100})      # Aqua Oct, S-NPP Sep (the earliest on a tie): 1 apart
    assert near["peak_month_distance"] == 1 and near["peak_within_tolerance"] is True and near["status"] == "PASS"
    far = run({9: 300, 10: 400}, {8: 500, 9: 300, 10: 300})       # Aqua Oct, S-NPP Aug: 2 apart
    assert far["peak_month_distance"] == 2 and far["peak_within_tolerance"] is False
    assert far["status"] == "FAIL" and any("2 months apart" in x for x in far["reasons"])


def test_peak_month_is_the_largest_pct_of_normal_and_the_earliest_on_a_tie():
    df = frame({7: 200, 11: 200})
    assert va.summarize_path(df, ANALYSIS, PEAK)["peak_month"] == "2015-07"


def test_peak_month_distance_crosses_the_year_boundary():
    win = ((2019, 11), (2020, 3))
    pk = ((2019, 12), (2020, 1))
    rows = lambda top: pd.DataFrame([{"year": y, "month": m, "estimate": 300.0 if (y, m) == top else 200.0, "sd": 10.0, "baseline_median": 100.0,
                                      "baseline_p25": 80.0, "baseline_p75": 120.0, "pct_of_normal": (300.0 if (y, m) == top else 200.0)}
                                     for y, m in va.month_range(*win)])
    r = va.compare_paths(rows((2019, 12)), rows((2020, 1)), win, pk)
    assert r["peak_month_distance"] == 1 and r["status"] == "PASS"


# ------------------------------------------------------------------------------------------------ intervals
def test_interval_by_hand():
    p = va.summarize_path(frame({9: 300, 10: 400}), ANALYSIS, PEAK)
    sd = float(np.sqrt(50.0 ** 2 + 50.0 ** 2))
    assert p["pct_low"] == pytest.approx((700 - Z * sd) / 200 * 100) and p["pct_high"] == pytest.approx((700 + Z * sd) / 200 * 100)


def test_interval_lower_bound_is_floored_at_zero():
    p = va.summarize_path(frame({9: 5, 10: 5}, sd=100.0), ANALYSIS, PEAK)
    assert p["pct_low"] == 0.0


def _single_month_pair(aqua_est: float, snpp_est: float, snpp_sd: float) -> dict:
    """Peak window of one month, baseline median 1 (so pct = estimate x 100 exactly), Aqua with zero sd."""
    pk = ((2015, 9), (2015, 9))
    mk = lambda est, sd: pd.DataFrame([{"year": 2015, "month": m, "estimate": est if m == 9 else 1.0, "sd": sd, "baseline_median": 1.0,
                                        "baseline_p25": 0.5, "baseline_p75": 2.0, "pct_of_normal": (est if m == 9 else 1.0)}
                                       for m in range(6, 13)])
    return va.compare_paths(mk(aqua_est, 0.0), mk(snpp_est, snpp_sd), ANALYSIS, pk)


def test_intervals_that_touch_overlap_and_a_gap_does_not():
    e, s = 50.0, 10.0
    touching = _single_month_pair(max(0.0, e - Z * s), e, s)           # Aqua's point value equals the lower end of the S-NPP interval
    assert touching["aqua"]["pct_high"] == touching["snpp"]["pct_low"]
    assert touching["intervals_overlap"] is True and touching["status"] == "PASS"
    apart = _single_month_pair(max(0.0, e - Z * s) - 1e-6, e, s)
    assert apart["aqua"]["pct_high"] < apart["snpp"]["pct_low"]
    assert apart["intervals_overlap"] is False and apart["status"] == "FAIL"
    assert any("do not overlap" in x for x in apart["reasons"])


# ------------------------------------------------------------------------------------------------ status
def test_no_baseline_on_one_path_is_inconclusive():
    r = va.compare_paths(frame({9: 300, 10: 400}), frame({9: 300, 10: 400}, baseline=False), ANALYSIS, PEAK)
    assert r["status"] == "INCONCLUSIVE" and r["same_direction"] is None
    assert any("S-NPP-only path cannot be judged" in x for x in r["reasons"])


def test_a_peak_window_month_without_an_estimate_is_inconclusive():
    s = frame({9: 300, 10: 400})
    s.loc[s.month == 10, ["estimate", "pct_of_normal"]] = np.nan
    r = va.compare_paths(frame({9: 300, 10: 400}), s, ANALYSIS, PEAK)
    assert r["status"] == "INCONCLUSIVE" and any("peak window" in x for x in r["reasons"])


def test_a_missing_peak_window_row_is_inconclusive_and_empty_frames_do_not_crash():
    s = frame({9: 300, 10: 400})
    r = va.compare_paths(frame({9: 300, 10: 400}), s[s.month != 9], ANALYSIS, PEAK)
    assert r["status"] == "INCONCLUSIVE"
    assert va.compare_paths(frame({}), pd.DataFrame(), ANALYSIS, PEAK)["status"] == "INCONCLUSIVE"


# ------------------------------------------------------------------------------------------------ the baseline
def test_baseline_percentiles_by_hand():
    b = va.baseline_stats(list(range(1, 21)))      # 1..20
    assert b["baseline_p25"] == pytest.approx(5.75) and b["baseline_median"] == pytest.approx(10.5) and b["baseline_p75"] == pytest.approx(15.25)
    assert b["n_baseline_years"] == 20


def test_baseline_needs_15_of_20_years():
    assert va.baseline_stats(list(range(1, 15))) is None                      # 14 years
    assert va.baseline_stats(list(range(10, 25)))["n_baseline_years"] == 15    # 15 years: allowed
    assert va.baseline_stats([None, np.nan] + list(range(10, 24))) is None     # 14 usable values, missing ones do not count
    assert va.baseline_stats(list(range(1, 12)), min_years=10) is not None     # the exploratory minimum is a parameter


def test_baseline_median_below_5_cell_days_gives_none():
    assert va.baseline_stats([4.0] * 20) is None
    assert va.baseline_stats([5.0] * 20)["baseline_median"] == 5.0


def test_attach_baseline_uses_only_the_baseline_years_with_an_estimate_of_the_same_month():
    base = pd.DataFrame([{"year": y, "month": 9, "estimate": float(y - 2002)} for y in range(2003, 2023)]            # 1..20 in September
                        + [{"year": 2023, "month": 9, "estimate": 1e6}, {"year": 2002, "month": 9, "estimate": 1e6}]  # outside 2003-2022
                        + [{"year": y, "month": 10, "estimate": 50.0} for y in range(2003, 2012)])                    # October: only 9 years
    numer = pd.DataFrame([{"year": 2015, "month": 9, "estimate": 21.0, "sd": 1.0}, {"year": 2015, "month": 10, "estimate": 60.0, "sd": 1.0}])
    out = va.attach_baseline(numer, base)
    sep, octo = out.iloc[0], out.iloc[1]
    assert (sep.baseline_p25, sep.baseline_median, sep.baseline_p75) == pytest.approx((5.75, 10.5, 15.25))
    assert sep.pct_of_normal == pytest.approx(21.0 / 10.5 * 100)
    assert np.isnan(octo.baseline_median) and np.isnan(octo.pct_of_normal) and octo.n_baseline_years == 0       # 9 of 20 years: no baseline


def test_attach_baseline_ignores_baseline_rows_without_an_estimate():
    base = pd.DataFrame([{"year": y, "month": 9, "estimate": np.nan if y < 2010 else float(y)} for y in range(2003, 2023)])      # 13 usable years
    out = va.attach_baseline(pd.DataFrame([{"year": 2015, "month": 9, "estimate": 2000.0, "sd": 1.0}]), base)
    assert np.isnan(out.baseline_median.iloc[0])


def test_baseline_and_comparison_are_reproducible():
    base = pd.DataFrame([{"year": y, "month": 9, "estimate": float((y * 37) % 23 + 6)} for y in range(2003, 2023)])
    numer = pd.DataFrame([{"year": 2015, "month": 9, "estimate": 40.0, "sd": 3.0}])
    pd.testing.assert_frame_equal(va.attach_baseline(numer, base), va.attach_baseline(numer, base))
    a, s = frame({9: 300, 10: 400}), frame({9: 350, 10: 300})
    assert va.compare_paths(a, s, ANALYSIS, PEAK) == va.compare_paths(a, s, ANALYSIS, PEAK)


# ------------------------------------------------------------------------------------------------ the witness restriction
def _two_witness_products(tmp_path: Path) -> hz.Paths:
    rows = month_rows(2015, 9, {("A1", "AQUA_MODIS", "D"): 30, ("B1", "AQUA_MODIS", "N"): 10,
                                ("A1", "SNPP_VIIRS", "D"): 60, ("A2", "SNPP_VIIRS", "D"): 40, ("A1", "SNPP_VIIRS", "N"): 50,
                                ("B1", "SNPP_VIIRS", "D"): 80, ("B1", "SNPP_VIIRS", "N"): 20,
                                ("A1", "NOAA20_VIIRS", "D"): 1000, ("B1", "NOAA20_VIIRS", "N"): 1000})
    return make(tmp_path, rows)


def test_restriction_keeps_only_the_chosen_witness(tmp_path):
    paths = _two_witness_products(tmp_path)
    rec = va.path_records(["A1", "A2", "B1"], [(2015, 9)], paths)
    a, s = rec["AQUA_MODIS"].iloc[0], rec["SNPP_VIIRS"].iloc[0]
    # Aqua keeps ratio 1: 30 + 10 = 40. S-NPP converted: day 0.5 x 100 + 0.25 x 80 = 70, night 0.1 x 50 + 0.05 x 20 = 6. NOAA-20's 1000s are in neither.
    assert a.estimate == pytest.approx(40.0) and s.estimate == pytest.approx(76.0)
    assert list(a.witnesses_used) == ["AQUA_MODIS"] and list(s.witnesses_used) == ["SNPP_VIIRS"]
    assert set(__import__("json").loads(a.raw_by_witness)) == {"AQUA_MODIS"} and set(__import__("json").loads(s.raw_by_witness)) == {"SNPP_VIIRS"}
    assert "SINGLE_WITNESS" in a.reason_codes and "SINGLE_WITNESS" in s.reason_codes


def test_restrict_witness_drops_other_rows_and_refuses_unknown_witnesses(tmp_path):
    paths = _two_witness_products(tmp_path)
    import duckdb
    con = duckdb.connect()
    con.register("m", pd.DataFrame({"entity_type": "CUSTOM", "entity_id": "X", "entity_name": "X", "cell_id": ["A1", "A2", "B1"]}))
    con.execute("CREATE TEMP TABLE members AS SELECT * FROM m")
    agg = hz.aggregate(con, paths, "members", [(2015, 9)])
    assert set(agg.witness) == {"AQUA_MODIS", "SNPP_VIIRS", "NOAA20_VIIRS"}
    assert set(va.restrict_witness(agg, "SNPP_VIIRS").witness) == {"SNPP_VIIRS"}
    with pytest.raises(ValueError):
        va.restrict_witness(agg, "TERRA_MODIS")


def test_a_month_where_the_chosen_witness_is_incomplete_has_no_estimate(tmp_path):
    rows = month_rows(2015, 9, {("A1", "SNPP_VIIRS", "D"): 60, ("A1", "SNPP_VIIRS", "N"): 5}, avail={"SNPP_VIIRS": 20}) \
        + month_rows(2015, 9, {("A1", "AQUA_MODIS", "D"): 30, ("A1", "AQUA_MODIS", "N"): 3})
    rec = va.path_records(["A1"], [(2015, 9)], make(tmp_path, rows))
    assert rec["AQUA_MODIS"].estimate.iloc[0] == pytest.approx(33.0)
    assert rec["SNPP_VIIRS"].estimate.isna().iloc[0]       # an outage is shown as missing, never interpolated


def test_box_cells_selects_by_cell_centre_edges_included():
    cells = pd.DataFrame({"cell_id": ["in", "edge", "out"], "lat_c": [0.25, -5.75, 4.25], "lon_c": [100.25, 95.25, 100.25]})
    assert va.box_cells(cells, (95.0, -6.0, 119.0, 4.0)) == ["edge", "in"]
    assert va.box_cells(cells, (95.25, -5.75, 100.25, 0.25)) == ["edge", "in"]


def test_month_range_across_a_year_boundary():
    assert va.month_range((2019, 11), (2020, 2)) == [(2019, 11), (2019, 12), (2020, 1), (2020, 2)]


# ------------------------------------------------------------------------------------------------ the recorded entry
SYN_CASE = {"label": "synthetic", "analysis": ANALYSIS, "peak": PEAK}      # the formal reading is chosen by the case id passed


def _frames(aqua_est, snpp_est):
    """Three readings: own baseline (no S-NPP baseline), shared baseline (S-NPP judged), and the min-10 reading."""
    a, s = frame(aqua_est), frame(snpp_est)
    return {va.OWN: (a, frame(snpp_est, baseline=False)), va.SHARED: (a, s), va.OWN_MIN10: (a, s)}


def test_entry_has_the_contract_test_shape():
    e = va.entry_for("C2", SYN_CASE, _frames({9: 300, 10: 400}, {9: 350, 10: 300}))
    for k in ("test_id", "family", "title", "case", "criterion", "threshold", "measured", "status", "notes"):
        assert k in e
    assert e["test_id"] == "A1-C2" and e["family"] == "A"
    assert e["measured"]["aqua_only_pct_of_normal"] == pytest.approx(350.0) and e["measured"]["snpp_only_pct_of_normal"] == pytest.approx(325.0)
    assert "D-029" in e["notes"]


def test_formal_reading_is_explicit_c1_keeps_d028_and_c2_to_c6_use_the_shared_baseline():
    assert va.FORMAL_READING["C1"] == va.OWN
    assert all(va.FORMAL_READING[c] == va.SHARED for c in ("C2", "C3", "C4", "C5", "C6"))
    assert set(va.FORMAL_READING) == set(va.CASES)


def test_c1_official_status_is_the_pre_registered_inconclusive_even_though_the_shared_reading_passes():
    frames = _frames({9: 300, 10: 400}, {9: 350, 10: 300})
    c1 = va.entry_for("C1", SYN_CASE, frames)
    assert c1["status"] == "INCONCLUSIVE" and c1["measured"]["official_reading"] == va.OWN
    assert c1["measured"]["other_readings"][va.SHARED]["status"] == "PASS"          # published beside it, not the official result
    assert "D-029" in c1["notes"] and "after this case was seen" in c1["notes"]
    assert c1["measured"]["snpp_only_pct_of_normal"] is None
    c3 = va.entry_for("C3", SYN_CASE, frames)
    assert c3["status"] == "PASS" and c3["measured"]["official_reading"] == va.SHARED
    assert c3["measured"]["other_readings"][va.OWN]["status"] == "INCONCLUSIVE"


def _entries(statuses: dict[str, str]) -> list[dict]:
    return [{"test_id": f"A1-{c}", "status": st} for c, st in statuses.items()]


def test_family_needs_5_of_6_passes_and_c1_inconclusive_is_not_a_pass():
    ok = {"C1": "INCONCLUSIVE", "C2": "PASS", "C3": "PASS", "C4": "PASS", "C5": "PASS", "C6": "PASS"}
    assert va.family_entry(_entries(ok))["status"] == "PASS"                                    # 5 passes, C1 not counted
    assert va.family_entry(_entries({**ok, "C6": "FAIL"}))["status"] == "FAIL"                  # 4 passes, all decided: not met
    assert va.family_entry(_entries({**ok, "C6": "INCONCLUSIVE"}))["status"] == "FAIL"          # an inconclusive case is final, not a pass


def test_family_is_inconclusive_only_while_cases_not_run_could_still_reach_5():
    assert va.family_entry(_entries({"C1": "PASS", "C2": "PASS", "C3": "PASS", "C4": "PASS"}))["status"] == "INCONCLUSIVE"   # 4 + 2 not run
    assert va.family_entry(_entries({"C1": "PASS", "C2": "PASS", "C3": "PASS", "C4": "FAIL", "C5": "FAIL"}))["status"] == "FAIL"   # 3 + 1 < 5
    f = va.family_entry(_entries({"C1": "INCONCLUSIVE", "C2": "FAIL", "C3": "FAIL", "C4": "FAIL", "C5": "FAIL", "C6": "PASS"}))
    assert f["status"] == "FAIL" and f["measured"]["n_pass"] == 1 and f["measured"]["n_fail"] == 4 and f["measured"]["n_inconclusive"] == 1
    assert va.family_entry(_entries({"C1": "PASS"}))["measured"]["n_not_run"] == 5              # cases not run are never passes



# ------------------------------------------------------------------------------------------------ the T-014 product
def _aqua_series(f=lambda y, m: 10.0 + (y % 7) + m) -> pd.DataFrame:
    return pd.DataFrame([{"year": y, "month": m, "estimate": float(f(y, m))} for y in range(2003, 2023) for m in range(1, 13)])


def _product_from(aqua: pd.DataFrame, after_2011_factor: float = 1.0) -> pd.DataFrame:
    """A fake T-014 entity series: equal to Aqua up to 2011, scaled afterwards; baseline_median built from its own estimates."""
    p = aqua.copy()
    p.loc[p.year > 2011, "estimate"] *= after_2011_factor
    med = p.groupby("month")["estimate"].median()
    p["baseline_median"] = p["month"].map(med)
    return p


def test_crosscheck_equal_series_agree_exactly_before_2012_and_the_baselines_match():
    aq = _aqua_series()
    r = va.crosscheck_aqua_baseline(_product_from(aq), aq)
    assert r["estimates_2003_2011"]["n"] == 9 * 12 and r["estimates_2003_2011"]["max_rel_diff"] == 0.0
    assert r["baseline_2003_2011"]["max_rel_diff"] == 0.0 and r["baseline_2003_2011"]["n_months"] == 12
    assert r["baseline_2003_2022"]["ratio_min"] == r["baseline_2003_2022"]["ratio_max"] == 1.0


def test_crosscheck_detects_a_planted_difference():
    aq = _aqua_series()
    r = va.crosscheck_aqua_baseline(_product_from(aq, after_2011_factor=2.0), aq)
    assert r["estimates_2003_2011"]["max_rel_diff"] == 0.0           # the Aqua-only years still agree
    assert r["baseline_2003_2022"]["ratio_max"] < 1.0 and r["baseline_2003_2022"]["ratio_min"] < 1.0   # the later years are doubled in the product
    bad = _product_from(aq)
    bad.loc[(bad.year == 2005) & (bad.month == 3), "estimate"] *= 1.5
    assert va.crosscheck_aqua_baseline(bad, aq)["estimates_2003_2011"]["max_rel_diff"] == pytest.approx(1 / 3)     # |a - 1.5a| / 1.5a


def test_product_context_applies_the_a1_quantities_to_the_combined_series():
    rows = []
    for m in range(6, 13):
        e = {9: 300.0, 10: 400.0}.get(m, 100.0)
        rows.append({"entity_type": "COUNTRY", "entity_id": "IDN", "year": 2015, "month": m, "estimate": e, "sd": 50.0, "baseline_median": 100.0,
                     "baseline_p25": 80.0, "baseline_p75": 120.0, "pct_of_normal": e, "p_above": 1.0, "verdict": "ABOVE_NORMAL",
                     "reason_codes": [], "witnesses_used": ["AQUA_MODIS"], "ci90_low": 0.0, "ci90_high": 0.0})
    rows.append({**rows[0], "entity_id": "OTHER"})
    ctx = va.product_context(pd.DataFrame(rows), "COUNTRY", "IDN", {"analysis": ANALYSIS, "peak": PEAK})
    assert ctx["entity"] == "COUNTRY:IDN" and len(ctx["months"]) == 7
    assert ctx["summary"]["direction"] == va.ABOVE and ctx["summary"]["peak_month"] == "2015-10" and ctx["summary"]["pct_of_normal"] == pytest.approx(350.0)


def test_crosscheck_ignores_product_years_before_the_baseline_period():
    aq = _aqua_series()
    prod = _product_from(aq)
    prod = pd.concat([prod, pd.DataFrame([{"year": 2002, "month": m, "estimate": 1e6, "baseline_median": np.nan} for m in range(7, 13)])])
    assert va.crosscheck_aqua_baseline(prod, aq)["baseline_2003_2011"]["max_rel_diff"] == 0.0
