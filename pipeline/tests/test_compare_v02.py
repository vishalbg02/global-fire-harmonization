"""Tests for the adoption rule of pipeline/compare_v02.py on constructed inputs (T-020c).

    python -m pytest pipeline/tests/test_compare_v02.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import compare_v02 as cmp

OLD = {"REGION": 0.30, "COUNTRY": 0.40}
GAPS1 = {"C3": 0.5, "C4": 0.6, "C5": 0.3, "C6": 0.4}
BETTER = {"C3": 0.3, "C4": 0.4, "C5": 0.2, "C6": 0.45}      # smaller in 3 of 4


def test_all_three_conditions_met_gives_the_adoption_proposal():
    d = cmp.decide(OLD, {"REGION": 0.30, "COUNTRY": 0.39}, 0.85, GAPS1, BETTER)
    assert d["adopt_v02"] and d["outcome"] == "ADOPT_PROPOSAL"
    assert d["condition_1_holdout"]["passes"] and d["condition_2_d1"]["passes"] and d["condition_3_a1_gap"]["improved"] == 3


def test_equal_holdout_error_is_no_worse_and_a_worse_one_in_either_entity_type_fails():
    assert cmp.decide(OLD, OLD, 0.85, GAPS1, BETTER)["condition_1_holdout"]["passes"]
    for worse in ({"REGION": 0.31, "COUNTRY": 0.40}, {"REGION": 0.30, "COUNTRY": 0.41}):
        d = cmp.decide(OLD, worse, 0.85, GAPS1, BETTER)
        assert not d["condition_1_holdout"]["passes"] and d["outcome"] == "KEEP_V01"


def test_d1_must_be_inside_80_to_97_with_both_ends_included():
    for cov, ok in ((0.80, True), (0.97, True), (0.7999, False), (0.9701, False), (float("nan"), False), (None, False)):
        assert cmp.decide(OLD, OLD, cov, GAPS1, BETTER)["condition_2_d1"]["passes"] is ok


def test_the_a1_gap_must_be_strictly_smaller_in_at_least_three_of_four_cases():
    two = {"C3": 0.3, "C4": 0.4, "C5": 0.35, "C6": 0.45}                # smaller in 2 only
    assert not cmp.decide(OLD, OLD, 0.85, GAPS1, two)["condition_3_a1_gap"]["passes"]
    tie = {"C3": 0.5, "C4": 0.4, "C5": 0.2, "C6": 0.3}                  # C3 equal: not smaller; C4, C5, C6 smaller: 3
    d = cmp.decide(OLD, OLD, 0.85, GAPS1, tie)
    assert d["condition_3_a1_gap"]["improved"] == 3 and not d["condition_3_a1_gap"]["cases"]["C3"]["smaller"]
    all4 = {"C3": 0.1, "C4": 0.1, "C5": 0.1, "C6": 0.1}
    assert cmp.decide(OLD, OLD, 0.85, GAPS1, all4)["condition_3_a1_gap"]["improved"] == 4


def test_a_case_that_cannot_be_judged_is_not_an_improvement():
    d = cmp.decide(OLD, OLD, 0.85, GAPS1, {"C3": None, "C4": 0.4, "C5": 0.2, "C6": float("nan")})
    assert d["condition_3_a1_gap"]["improved"] == 2 and not d["adopt_v02"]


def test_one_failed_condition_is_enough_to_keep_v01():
    assert cmp.decide(OLD, OLD, 0.85, GAPS1, BETTER)["adopt_v02"]
    assert not cmp.decide(OLD, OLD, 0.99, GAPS1, BETTER)["adopt_v02"]
    assert not cmp.decide(OLD, {"REGION": 0.5, "COUNTRY": 0.4}, 0.85, GAPS1, BETTER)["adopt_v02"]


def test_only_the_failed_cases_c3_to_c6_count():
    assert cmp.FAILED_CASES == ("C3", "C4", "C5", "C6") and cmp.MIN_FAILED_IMPROVED == 3
    d = cmp.decide(OLD, OLD, 0.85, {**GAPS1, "C1": 1.0, "C2": 1.0}, {**BETTER, "C1": 0.1, "C2": 0.1})
    assert set(d["condition_3_a1_gap"]["cases"]) == set(cmp.FAILED_CASES)


def test_peak_sum_needs_every_month_of_the_peak_window_with_an_estimate():
    df = pd.DataFrame({"year": [2020, 2020, 2020], "month": [8, 9, 10], "estimate": [10.0, 20.0, np.nan]})
    assert cmp.peak_sum(df, ((2020, 8), (2020, 9))) == pytest.approx(30.0)
    assert cmp.peak_sum(df, ((2020, 8), (2020, 10))) is None             # October has no estimate
    assert cmp.peak_sum(df, ((2020, 7), (2020, 9))) is None              # July is missing
