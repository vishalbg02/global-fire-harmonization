"""Tests for pipeline/saturation.py on SYNTHETIC data with known answers (T-020b).

    python -m pytest pipeline/tests/test_saturation.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import saturation as sat


def test_bin_assignment_at_the_edges():
    x = np.array([0.0, 0.049, 0.05, 0.149, 0.15, 0.5, 1.49, 1.5, 4.99, 5.0, 14.9, 15.0, 49.9, 50.0, 1e6])
    assert sat.bin_index(x).tolist() == [0, 0, 1, 1, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7]


def world(rng, slope=0.0, n_months=36, n_units=400, noise=0.05):
    """Units with a planted ratio: Aqua / witness = 0.3 x (activity / 1)^slope, with small noise."""
    month = np.repeat(np.arange(n_months), n_units)
    activity = np.exp(rng.uniform(np.log(0.02), np.log(80.0), month.size))
    ratio = 0.3 * activity**slope * np.exp(rng.normal(0.0, noise, month.size))
    a = activity * 20.0
    w = a / ratio
    return month, activity, a, w, n_months


def test_a_ratio_that_rises_with_activity_gives_a_positive_slope_that_excludes_zero():
    rng = np.random.default_rng(1)
    month, activity, a, w, nm = world(rng, slope=0.25)
    res = sat.analyse(month, activity, a, w, nm, boot=200)
    assert res["slope"] == pytest.approx(0.25, abs=0.04) and res["positive_and_excludes_zero"]
    lo, hi = res["slope_ci90"]
    assert lo < 0.25 < hi or abs(lo - 0.25) < 0.05
    used = [b for b in res["bins"] if b["used_in_slope"]]
    assert len(used) >= 6 and used[-1]["ratio"] > used[0]["ratio"] * 2          # the ratio rises across the bins


def test_a_constant_ratio_gives_a_slope_near_zero_and_is_not_called_positive():
    rng = np.random.default_rng(2)
    month, activity, a, w, nm = world(rng, slope=0.0)
    res = sat.analyse(month, activity, a, w, nm, boot=200)
    assert abs(res["slope"]) < 0.03 and not res["positive_and_excludes_zero"]


def test_bins_with_too_few_units_are_shown_but_not_used():
    rng = np.random.default_rng(3)
    month, activity, a, w, nm = world(rng, slope=0.2, n_units=60)
    activity = np.where(np.arange(activity.size) % 500 == 0, 70.0, np.minimum(activity, 14.0))       # a handful of units in the top bin
    res = sat.analyse(month, activity, a, w, nm, boot=50, min_units=50)
    top = res["bins"][-1]
    assert top["units"] < 50 and not top["used_in_slope"] and top["ratio"] is not None


def test_the_bootstrap_is_reproducible_and_the_interval_narrows_with_more_data():
    rng = np.random.default_rng(4)
    month, activity, a, w, nm = world(rng, slope=0.2, n_months=12, n_units=100)
    r1 = sat.analyse(month, activity, a, w, nm, boot=100, seed=7)
    r2 = sat.analyse(month, activity, a, w, nm, boot=100, seed=7)
    assert r1["slope_ci90"] == r2["slope_ci90"]
    big = world(np.random.default_rng(4), slope=0.2, n_months=60, n_units=400)
    rb = sat.analyse(big[0], big[1], big[2], big[3], big[4], boot=100, seed=7)
    assert rb["slope_ci90"][1] - rb["slope_ci90"][0] < r1["slope_ci90"][1] - r1["slope_ci90"][0]


def test_the_decision_rule_needs_two_binnings_with_three_of_four_combinations():
    def entry(positive):
        return {"positive_and_excludes_zero": positive}
    def results(counts):
        out = {}
        for binning, n in counts.items():
            for i, key in enumerate((("SNPP_VIIRS", "D"), ("SNPP_VIIRS", "N"), ("NOAA20_VIIRS", "D"), ("NOAA20_VIIRS", "N"))):
                out[f"{binning}|{key[0]}|{key[1]}"] = entry(i < n)
        return out
    d = sat.decide(results({"aqua_month": 4, "symmetric_proxy": 3, "typical_stratum": 0}))
    assert d["confirmed"] and d["binnings_passing"] == ["aqua_month", "symmetric_proxy"]
    assert not sat.decide(results({"aqua_month": 4, "symmetric_proxy": 2, "typical_stratum": 2}))["confirmed"]         # only one binning passes
    assert not sat.decide(results({"aqua_month": 4, "symmetric_proxy": 0, "typical_stratum": 0}))["confirmed"]        # binning (a) alone never decides
    assert sat.decide(results({"aqua_month": 3, "symmetric_proxy": 3, "typical_stratum": 3}))["confirmed"]


def test_the_activity_variables_and_the_typical_stratum_value():
    u = {"a": np.array([2.0, 4.0, 6.0, 10.0]), "w": np.array([10.0, 10.0, 10.0, 10.0]), "cells": np.array([2.0, 2.0, 2.0, 5.0]),
         "stratum": np.array(["s", "s", "s", "t"])}
    v = sat.activity_variables(u)
    assert v["aqua_month"].tolist() == [1.0, 2.0, 3.0, 2.0]
    assert v["typical_stratum"].tolist() == [2.0, 2.0, 2.0, 2.0]                          # the median of 1, 2, 3 for s and 2 for t
    g = 22.0 / 40.0
    assert v["symmetric_proxy"][0] == pytest.approx(0.5 * (1.0 + g * 5.0))


def test_the_units_use_only_the_fit_periods(tmp_path):
    import calibration as cal
    # the S-NPP fit period ends in 2016-12 and NOAA-20's starts in 2018-04: no month of 2017 is ever a fit month for S-NPP
    assert cal.fit_months("SNPP_VIIRS") == (201201, 201612) and cal.fit_months("NOAA20_VIIRS") == (201804, 202112)
    assert set(sat.WITNESSES) == set(cal.FITS)


def test_the_slope_needs_three_eligible_bins():
    sa, sw, n = np.array([10.0, 20.0, 0.0]), np.array([20.0, 20.0, 0.0]), np.array([100, 100, 0])
    assert np.isnan(sat.slope_from(sa, sw, n, np.array([0.1, 1.0, 10.0])))
    sa3, sw3, n3 = np.array([1.0, 2.0, 4.0]), np.array([4.0, 4.0, 4.0]), np.array([100, 100, 100])
    assert sat.slope_from(sa3, sw3, n3, np.array([1.0, 2.0, 4.0])) == pytest.approx(1.0)       # ratio doubles when activity doubles
