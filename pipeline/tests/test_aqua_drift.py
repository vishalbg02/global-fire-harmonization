"""Tests for pipeline/aqua_drift.py on SYNTHETIC series with answers known by hand (T-012, part B).

    python -m pytest pipeline/tests/test_aqua_drift.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import aqua_drift as ad

B_TRUE = ad.month_index(2021, 6)
T = np.arange(0, ad.month_index(2026, 10) + 1, dtype=float)
CAND = ad.candidates(0)


def planted(slope=0.01, sd=0.02, b=B_TRUE, seed=1):
    rng = np.random.default_rng(seed)
    return np.maximum(0.0, T - b) * slope + rng.normal(0, sd, len(T))


def month_range(c):
    return ad.month_label(c[0]), ad.month_label(c[-1])


def test_month_index_and_label_round_trip():
    assert ad.month_index(2012, 1) == 0 and ad.month_index(2013, 3) == 14
    assert ad.month_label(14) == "2013-03" and ad.month_label(ad.month_index(2026, 10)) == "2026-10"


def test_scan_matches_a_direct_least_squares_fit_by_hand():
    t = np.arange(10.0)
    y = np.array([1, 1, 1, 1, 1, 2, 3, 4, 5, 6.0])          # flat at 1 up to t = 4, then +1 per step: exact for b = 4
    rss, slope = ad.scan(t, y, np.array([3, 4, 5]))
    assert rss[1] == pytest.approx(0.0, abs=1e-12) and slope[1] == pytest.approx(1.0)
    assert rss[0] > 0 and rss[2] > 0


def test_fit_finds_the_planted_break_and_slope():
    r = ad.detect(T, planted(), CAND)
    assert abs(r["onset"] - B_TRUE) <= 4
    assert r["slope"] == pytest.approx(0.01, abs=0.002)
    assert r["onset_lo"] <= r["onset"] <= r["onset_hi"] and r["onset_lo"] <= B_TRUE <= r["onset_hi"]
    assert r["slope_lo"] <= 0.01 <= r["slope_hi"]
    assert r["detected"] and r["break_beats_flat_by_bic"] and r["slope_interval_excludes_0"] and r["delta_bic"] > 10


def test_a_planted_decline_is_found_with_a_negative_slope():
    r = ad.detect(T, planted(slope=-0.01), CAND)
    assert r["detected"] and r["slope"] < 0 and r["slope_hi"] < 0


def test_flat_series_is_not_called_drift_and_bic_prefers_flat():
    for seed in range(5):
        r = ad.detect(T, planted(slope=0.0, seed=seed), CAND, reps=300)
        assert not r["detected"]
        assert r["bic_flat"] < r["bic_break"] and not r["break_beats_flat_by_bic"]


def test_a_very_small_slope_buried_in_noise_is_not_called():
    r = ad.detect(T, planted(slope=0.0005, sd=0.05), CAND, reps=300)
    assert not r["detected"]


def test_both_criteria_are_needed():
    # three high months at the very end of the range (a case the method may or may not call): whatever the two criteria say separately, the call is their conjunction
    rng = np.random.default_rng(3)
    y = rng.normal(0, 0.05, len(T))
    y[-3:] += 0.2
    r = ad.detect(T, y, CAND, reps=300)
    assert r["detected"] == (r["slope_interval_excludes_0"] and r["break_beats_flat_by_bic"])
    r2 = ad.detect(T, planted(), CAND, reps=300)
    assert r2["slope_interval_excludes_0"] and r2["break_beats_flat_by_bic"] and r2["detected"]


def test_bic_counts_the_parameters_by_hand():
    assert ad.bic(0.5, 100, 2) == pytest.approx(100 * np.log(0.005) + 2 * np.log(100))
    assert ad.K_BREAK - ad.K_FLAT == 2


def test_candidate_range_is_respected():
    assert month_range(ad.candidates(0)) == ("2018-01", "2025-06")
    assert month_range(ad.candidates(ad.month_index(2018, 4), 12)) == ("2019-04", "2025-06")
    # a break planted before the range: the onset and its interval still lie inside the candidates
    r = ad.detect(T, planted(b=ad.month_index(2015, 1)), CAND, reps=200)
    assert CAND[0] <= r["onset_lo"] <= r["onset"] <= r["onset_hi"] <= CAND[-1]


def test_block_bootstrap_is_reproducible_with_the_same_seed():
    y = planted()
    a = ad.bootstrap_break(T, y, CAND, reps=200, seed=7)
    b = ad.bootstrap_break(T, y, CAND, reps=200, seed=7)
    c = ad.bootstrap_break(T, y, CAND, reps=200, seed=8)
    assert np.array_equal(a[0], b[0]) and np.array_equal(a[1], b[1])
    assert not np.array_equal(a[1], c[1])


def test_block_indices_are_blocks_of_consecutive_positions():
    idx = ad.block_indices(20, 6, 5, np.random.default_rng(0))
    assert idx.shape == (5, 20) and idx.min() >= 0 and idx.max() <= 19
    assert np.all(np.diff(idx[:, :6], axis=1) == 1)           # the first block is six consecutive positions


def test_interval_widens_with_more_noise():
    lo = ad.detect(T, planted(sd=0.01), CAND, reps=300)
    hi = ad.detect(T, planted(sd=0.08), CAND, reps=300)
    assert (hi["slope_hi"] - hi["slope_lo"]) > 2 * (lo["slope_hi"] - lo["slope_lo"])
    assert (hi["onset_hi"] - hi["onset_lo"]) > (lo["onset_hi"] - lo["onset_lo"])


def test_null_bootstrap_gain_is_small_for_flat_and_large_for_a_break():
    flat = ad.null_pvalue(T, planted(slope=0.0), CAND, reps=300)
    brk = ad.null_pvalue(T, planted(), CAND, reps=300)
    assert flat["p_value"] > 0.05 and brk["p_value"] < 0.01 and brk["gain_observed"] > flat["gain_observed"]


# --------------------------------------------------------------------------------------------- the series builder
def agg_rows(rows):
    return pd.DataFrame(rows, columns=["entity_id", "year", "month", "witness", "daynight", "e", "complete"])


def test_series_builder_uses_complete_months_only_and_forms_the_ratio():
    rows = []
    for m, (ca, cv) in {1: (True, True), 2: (True, False), 3: (False, True), 4: (True, True)}.items():
        rows += [("R1", 2014, m, "AQUA_MODIS", "D", 90.0, ca), ("R1", 2014, m, "SNPP_VIIRS", "D", 100.0, cv),
                 ("R2", 2014, m, "AQUA_MODIS", "D", 10.0, True), ("R2", 2014, m, "SNPP_VIIRS", "D", 20.0, True)]
    s = ad.build_series(agg_rows(rows))
    r1 = s[(s.entity_id == "R1") & (s.witness == "SNPP_VIIRS")]
    assert r1.month.tolist() == [1, 4] and r1.R.tolist() == pytest.approx([0.9, 0.9])
    g = s[s.entity_id == "GLOBAL"]
    assert g.month.tolist() == [1, 4]                         # the global month needs every region complete in both witnesses
    assert g.R.tolist() == pytest.approx([(90 + 10) / (100 + 20)] * 2)
    assert g.aqua.tolist() == [100.0, 100.0] and not (s.witness == "NOAA20_VIIRS").any()


def test_series_builder_separates_witnesses_and_day_night_and_drops_tiny_months():
    rows = [("R1", 2019, 5, "AQUA_MODIS", "D", 50.0, True), ("R1", 2019, 5, "SNPP_VIIRS", "D", 100.0, True), ("R1", 2019, 5, "NOAA20_VIIRS", "D", 40.0, True),
            ("R1", 2019, 5, "AQUA_MODIS", "N", 5.0, True), ("R1", 2019, 5, "SNPP_VIIRS", "N", 10.0, True)]
    s = ad.build_series(agg_rows(rows), min_units=20.0)
    assert set(zip(s.witness, s.daynight, strict=True)) == {("SNPP_VIIRS", "D"), ("NOAA20_VIIRS", "D")}     # the night month has fewer than 20 cell-days
    assert s[s.witness == "NOAA20_VIIRS"].R.iloc[0] == pytest.approx(50 / 40)
    s0 = ad.build_series(agg_rows(rows))
    assert ("SNPP_VIIRS", "N") in set(zip(s0.witness, s0.daynight, strict=True))


def test_run_series_reports_a_short_series_as_insufficient_and_shifts_the_range_for_a_late_start():
    s = pd.DataFrame({"idx": np.arange(30), "R": 1.0})
    assert ad.run_series(s)["status"] == "insufficient data"
    t = np.arange(ad.month_index(2018, 4), ad.month_index(2026, 10) + 1)
    s = pd.DataFrame({"idx": t, "R": np.exp(planted(slope=0.0)[: len(t)])})
    r = ad.run_series(s, 12, reps=100)
    assert r["candidate_first"] == "2019-04" and r["candidate_last"] == "2025-06"


def test_registered_constants_are_the_preregistered_ones():
    assert (ad.N_BOOT, ad.BLOCK, ad.CAND_FIRST, ad.CAND_LAST) == (1000, 6, (2018, 1), (2025, 6))
    assert ad.PRIMARY == ("GLOBAL", "D", "SNPP_VIIRS")
