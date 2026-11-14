"""Tests for pipeline/holdout.py on SYNTHETIC data with answers known by hand (T-012, part A).

    python -m pytest pipeline/tests/test_holdout.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import holdout as ho

PHI1 = {"D": 1.0, "N": 1.0}
K0 = {"D": 0.0, "N": 0.0}


def agg_rows(entity, year, month, dn, aqua, snpp, ratio, ok_a=True, ok_s=True, etype="REGION"):
    """Two rows of harmonize.aggregate() (Aqua and S-NPP) for one entity-month; counting variance = converted count, ratio sd 10%."""
    base = {"entity_type": etype, "entity_id": entity, "year": year, "month": month, "daynight": dn}
    return [{**base, "witness": "AQUA_MODIS", "raw": aqua, "e": float(aqua), "vc": float(aqua), "vr": 0.0, "complete": ok_a},
            {**base, "witness": "SNPP_VIIRS", "raw": snpp, "e": snpp * ratio, "vc": snpp * ratio**2, "vr": (0.1 * ratio * snpp) ** 2, "complete": ok_s}]


def agg_frame(rows):
    return pd.DataFrame(rows)


def glob_rows(year, month, aqua, snpp, dn="D", complete=True):
    return [{"year": year, "month": month, "daynight": dn, "witness": "AQUA_MODIS", "raw": aqua, "complete": complete},
            {"year": year, "month": month, "daynight": dn, "witness": "SNPP_VIIRS", "raw": snpp, "complete": complete}]


# ------------------------------------------------------------------------------------------------ metrics
def test_metrics_on_planted_errors_by_hand():
    u = pd.DataFrame({"actual": [100.0, 100.0, 100.0, 100.0], "pred_ours": [100.0, 200.0, 50.0, 100.0],
                      "year": [2017, 2017, 2018, 2018]})
    m = ho.metrics(u, "ours")
    assert m["units"] == 4
    assert m["median_ratio"] == pytest.approx(1.0)                         # ratios 1, 2, 0.5, 1
    assert m["p05_ratio"] == pytest.approx(np.percentile([1, 2, 0.5, 1], 5))
    assert m["p95_ratio"] == pytest.approx(np.percentile([1, 2, 0.5, 1], 95))
    # |log| errors: 0, ln2, ln2, 0 -> median ln2 / 2
    assert m["median_abs_log_error"] == pytest.approx(np.log(2) / 2)
    assert m["bias_by_year"][2017] == pytest.approx(np.log(2) / 2)         # median of 0 and ln 2
    assert m["bias_by_year"][2018] == pytest.approx(-np.log(2) / 2)        # median of ln 0.5 and 0


def test_zero_prediction_uses_a_one_cell_day_floor():
    u = pd.DataFrame({"actual": [100.0], "pred_raw": [0.0], "year": [2017]})
    assert ho.metrics(u, "raw")["median_abs_log_error"] == pytest.approx(np.log(100.0))


# ------------------------------------------------------------------------------------------------ coverage
def test_coverage_counts_planted_intervals():
    pred = np.full(10, 100.0)
    var = np.full(10, 100.0)                                               # sd 10 -> half width 16.45
    actual = np.array([100, 105, 90, 115, 85, 110, 100, 120, 80, 150], float)   # last three: 20, 20, 50 away -> outside
    assert ho.coverage(actual, pred, var) == pytest.approx(0.7)            # 120 and 80 and 150 are outside (|d| 20, 20, 50)
    assert ho.coverage(actual[:8], pred[:8], var[:8]) == pytest.approx(0.875)   # only 120 is outside
    in8 = np.array([100, 105, 90, 115, 85, 110, 100, 100, 120, 150], float)
    assert ho.coverage(in8, pred, var) == pytest.approx(0.8)               # 8 of 10 inside


def test_coverage_adds_the_aqua_variance():
    # difference 20: outside for var_pred = 100 (half 16.45), inside once var_aqua = 100 is added (half 23.3)
    assert ho.coverage([120.0], [100.0], [100.0]) == 0.0
    assert ho.coverage([120.0], [100.0], [100.0], [100.0]) == 1.0


def test_variance_with_phi_kappa_and_the_other_variants():
    agg = agg_frame(agg_rows("R1", 2017, 3, "D", 100, 400, 0.25))
    u = ho.add_predictions(ho.units_from_agg(agg), {("D", "MAM"): 0.3}, {"D": 4.0, "N": 1.0}, {"D": 0.05, "N": 0.0})
    vc_s, vr_s = 400 * 0.25**2, (0.1 * 0.25 * 400) ** 2
    # S-NPP: 4 x 100 + 0.05 x 100^2 + vr ; Aqua: 4 x 100 + 0.05 x 100^2 (kappa x actual^2, the Aqua value is an estimate)
    assert u.var_ours[0] == pytest.approx(4.0 * vc_s + 0.05 * 100**2 + vr_s + 4.0 * 100 + 0.05 * 100**2)
    harm_p = ho.hz.PHI_ONLY["D"]
    assert u.var_phionly[0] == pytest.approx(harm_p * vc_s + vr_s + harm_p * 100)
    assert u.var_pois[0] == pytest.approx(vc_s + vr_s + 100)
    assert u.pred_ours[0] == pytest.approx(100.0) and u.pred_raw[0] == 400 and u.pred_glob[0] == pytest.approx(120.0)


def test_kappa_enters_both_sides_and_zero_kappa_gives_the_old_numbers():
    agg = agg_frame(agg_rows("R1", 2017, 3, "D", 100, 400, 0.25))
    base = ho.units_from_agg(agg)
    r = {("D", "MAM"): 0.3}
    k0 = ho.add_predictions(base, r, {"D": 4.0, "N": 1.0}, K0)
    kk = ho.add_predictions(base, r, {"D": 4.0, "N": 1.0}, {"D": 0.1, "N": 0.0})
    vc_s, vr_s = 400 * 0.25**2, (0.1 * 0.25 * 400) ** 2
    assert k0.var_ours[0] == pytest.approx(4.0 * vc_s + vr_s + 4.0 * 100)               # the previous model: phi x vc + vr
    assert kk.var_ours[0] - k0.var_ours[0] == pytest.approx(0.1 * 100**2 + 0.1 * 100**2)  # S-NPP e = 100 and Aqua actual = 100
    # a different Aqua value and S-NPP estimate: the two terms are not interchangeable
    u2 = ho.add_predictions(ho.units_from_agg(agg_frame(agg_rows("R1", 2017, 3, "D", 200, 400, 0.25))), r, PHI1, {"D": 0.1, "N": 0.0})
    assert u2.var_ours[0] == pytest.approx(400 * 0.25**2 + 0.1 * 100**2 + (0.1 * 100) ** 2 + 200 + 0.1 * 200**2)


def test_defaults_come_from_harmonize():
    u = ho.add_predictions(ho.units_from_agg(agg_frame(agg_rows("R1", 2017, 3, "N", 100, 400, 0.25))), {("N", "MAM"): 0.3})
    vc_s, vr_s = 400 * 0.25**2, (0.1 * 0.25 * 400) ** 2
    p, k = ho.hz.PHI["N"], ho.hz.KAPPA["N"]
    assert u.var_ours[0] == pytest.approx(p * vc_s + k * 100**2 + vr_s + p * 100 + k * 100**2)


def test_total_sums_day_and_night_and_needs_both():
    rows = agg_rows("R1", 2017, 3, "D", 100, 400, 0.25) + agg_rows("R1", 2017, 3, "N", 50, 100, 0.5) + agg_rows("R2", 2017, 3, "D", 100, 400, 0.25)
    ratios = {("D", "MAM"): 0.25, ("N", "MAM"): 0.5}
    u = ho.add_predictions(ho.units_from_agg(agg_frame(rows)), ratios, PHI1, K0)
    t = ho.total_units(u)
    assert list(t.entity_id) == ["R1"]                                      # R2 has no night unit
    assert t.actual[0] == 150 and t.pred_ours[0] == pytest.approx(150.0)
    assert t.var_ours[0] == pytest.approx(u.var_ours.iloc[:2].sum())
    assert t.var_phionly[0] == pytest.approx(u.var_phionly.iloc[:2].sum())


# ------------------------------------------------------------------------------------------------ the global-ratio baseline
def test_global_ratio_by_hand_and_per_season():
    g = glob_rows(2012, 3, 100, 400) + glob_rows(2013, 4, 300, 600) + glob_rows(2012, 7, 100, 100)   # MAM: 400 / 1000; JJA: 1
    r = ho.fit_global_ratios(pd.DataFrame(g))
    assert r[("D", "MAM")] == pytest.approx(0.4)
    assert r[("D", "JJA")] == pytest.approx(1.0)


def test_global_ratio_is_fitted_only_on_the_fit_period_and_complete_months():
    base = glob_rows(2012, 3, 100, 400) + glob_rows(2016, 5, 300, 600)
    clean = ho.fit_global_ratios(pd.DataFrame(base))
    outlier = glob_rows(2017, 3, 1e9, 1.0) + glob_rows(2020, 4, 1e9, 1.0) + glob_rows(2011, 3, 1e9, 1.0) + glob_rows(2013, 3, 1e9, 1.0, complete=False)
    dirty = ho.fit_global_ratios(pd.DataFrame(base + outlier))
    assert dirty == clean
    assert clean[("D", "MAM")] == pytest.approx(400 / 1000)


# ------------------------------------------------------------------------------------------------ windows and filters
def test_window_and_complete_month_and_min_cell_days_filters():
    rows = []
    for y, m, aq, ok in [(2016, 12, 100, True), (2017, 1, 100, True), (2021, 12, 100, True), (2022, 1, 100, True),   # window
                         (2018, 5, 19, True), (2018, 6, 20, True),                                                     # threshold: >= 20
                         (2019, 5, 100, False)]:                                                                       # incomplete Aqua
        rows += agg_rows("R1", y, m, "D", aq, 200, 0.5, ok_a=ok)
    rows += agg_rows("R1", 2019, 6, "D", 100, 200, 0.5, ok_s=False)                                                    # incomplete S-NPP
    u = ho.units_from_agg(agg_frame(rows))
    assert sorted(zip(u.year, u.month, strict=True)) == [(2017, 1), (2018, 6), (2021, 12)]
    assert len(ho.units_from_agg(agg_frame(rows), min_cell_days=5)) == 4
    assert len(ho.units_from_agg(agg_frame(rows), min_cell_days=100)) == 2


# ------------------------------------------------------------------------------------------------ which method wins
def _world(true_ratio_by_region, fit_ratio=None, noise=0.0, seed=1):
    """Aqua = S-NPP raw x true ratio per region; `ours` uses the regional ratio (what the calibration would have), glob a single ratio."""
    rng = np.random.default_rng(seed)
    rows, glob = [], []
    for region, true_r in true_ratio_by_region.items():
        used = (fit_ratio or true_ratio_by_region)[region]
        for y in range(2017, 2022):
            for m in range(1, 13):
                snpp = int(rng.integers(200, 400))
                aqua = snpp * true_r * float(np.exp(rng.normal(0, noise)))
                rows += agg_rows(region, y, m, "D", aqua, snpp, used)
    for m in range(1, 13):    # the global fit period: the average of the regional truths
        glob += glob_rows(2012 + m % 5, m, 100 * np.mean(list(true_ratio_by_region.values())), 100)
    return agg_frame(rows), pd.DataFrame(glob)


def test_ours_beats_both_baselines_when_the_ratio_differs_by_region():
    agg, glob = _world({"R1": 0.2, "R2": 0.8}, noise=0.05)
    s = ho.evaluate(agg, glob, "REGION", 20.0, PHI1, K0)
    e = {m: s["all"][m]["median_abs_log_error"] for m in ho.METHODS}
    assert e["ours"] < 0.1 < e["glob"] < e["raw"]
    assert s["losses"] == []


def test_a_world_where_the_conversion_is_wrong_is_not_hidden():
    # the true ratio is the one global ratio (0.5) everywhere, but the regional conversion says 0.2 and 0.8: ours loses to glob
    agg, glob = _world({"R1": 0.5, "R2": 0.5}, fit_ratio={"R1": 0.2, "R2": 0.8}, noise=0.05)
    s = ho.evaluate(agg, glob, "REGION", 20.0, PHI1, K0)
    e = {m: s["all"][m]["median_abs_log_error"] for m in ho.METHODS}
    assert e["glob"] < e["ours"]
    assert {x["group"] for x in s["losses"]} == {"R1|D", "R2|D"}
    assert all("glob" in x["worse_than"] for x in s["losses"])


def test_coverage_of_a_calibrated_world_is_near_90_percent():
    rng = np.random.default_rng(7)
    actual = rng.poisson(100, 5000).astype(float)                          # the truth is Poisson(100); the prediction is exact
    c = ho.coverage(actual, np.full(5000, 100.0), np.zeros(5000), np.full(5000, 100.0))
    assert 0.85 < c < 0.97


# ------------------------------------------------------------------------------------------------ summary shape
def test_summary_has_regions_daynight_total_and_both_coverages():
    rows = agg_rows("R1", 2017, 3, "D", 100, 400, 0.25) + agg_rows("R1", 2017, 3, "N", 50, 100, 0.5)
    glob = pd.DataFrame(glob_rows(2012, 3, 100, 400) + glob_rows(2012, 3, 50, 100, dn="N"))
    s = ho.evaluate(agg_frame(rows), glob, "REGION", 20.0, PHI1, K0)
    assert set(s["by_group"]) == {"R1|D", "R1|N", "R1|T"}
    assert set(s["coverage"]) == {"with_phi_kappa", "with_phi_only", "poisson_only"}
    assert s["coverage"]["with_phi_kappa"]["total"]["units"] == 1
    assert s["by_daynight"]["T"]["ours"]["units"] == 1


# ---------------------------------------------------- the Lead's coverage checks (PR #43): 50% interval, bands, widening factor
def test_coverage_of_the_50_percent_interval_and_the_widening_factor_by_hand():
    actual = np.array([0.0] * 10)
    pred = np.array([float(x) for x in (0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0)])   # errors 0.2 ... 2.0, sd 1
    var = np.ones(10)
    assert ho.coverage(actual, pred, var, z=ho.Z50) == 0.3                      # |error| <= 0.6745: 0.2, 0.4, 0.6
    assert ho.coverage(actual, pred, var) == 0.8                                # |error| <= 1.645: up to 1.6
    c = ho.widening_factor(actual, pred, var)                                   # 90% needs 9 of 10 inside: |error| 1.8 <= 1.645 c
    assert c == pytest.approx(1.8 / ho.Z90, abs=1e-6) and ho.coverage(actual, pred, var, c=c) == 0.9
    assert ho.widening_factor(actual, actual, var) < 1e-6                         # already covered: the smallest c is 0
    assert np.isnan(ho.widening_factor([], [], []))


def units_for_check(n_per_cell, widths):
    rows = []
    for year, dn, actual, pred, var in widths:
        rows += [{"year": year, "daynight": dn, "actual": actual, "pred_ours": pred, "var_ours": var} for _ in range(n_per_cell)]
    return pd.DataFrame(rows)


def test_lead_check_splits_by_band_period_and_fits_c_on_2017_2018_only():
    early = [(2017 + i % 2, "D", 50.0, 50.0 + 5.0 * (i - 5), 9.0) for i in range(11)]          # errors -25 .. 25, sd 3
    late = [(2019 + i % 3, "D", 600.0, 600.0, 1.0) for i in range(10)] + [(2020, "N", 30.0, 90.0, 1.0)]
    u = pd.concat([units_for_check(1, early), units_for_check(1, late)], ignore_index=True)
    out = ho.lead_check(u, u.iloc[0:0].assign(daynight="T"))
    assert out["by_period"]["2017-2018"]["units"] == 11 and out["by_period"]["2019-2021"]["units"] == 11
    assert out["by_band"]["D|20-100"]["units"] == 11 and out["by_band"]["D|500-"]["units"] == 10 and out["by_band"]["N|20-100"]["units"] == 1
    w = out["widening"]
    assert w["fitted_on"] == "2017-2018 only" and w["applied"] is False and w["c_for_90"] > 1.0
    # c is the one that gives 90% coverage on 2017-2018 and nothing in 2019-2021 influences it
    early_only = u[u.year < 2019]
    assert ho.coverage(early_only.actual, early_only.pred_ours, early_only.var_ours, c=w["c_for_90"]) >= 0.9
    changed = u.copy()
    changed.loc[changed.year >= 2019, "pred_ours"] = 0.0
    assert ho.lead_check(changed, u.iloc[0:0].assign(daynight="T"))["widening"]["c_for_90"] == w["c_for_90"]
    assert out["all"]["coverage_50"] <= out["all"]["coverage_90"]
