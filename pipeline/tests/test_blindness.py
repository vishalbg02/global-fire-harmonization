"""Tests for pipeline/blindness.py on SYNTHETIC data with known answers (T-016).

    python -m pytest pipeline/tests/test_blindness.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import blindness as bl

SEASONS_36 = np.array(["DJF", "MAM", "JJA", "SON"] * 9)  # 36 SYNTHETIC months


def world(rng, b_true=(2.0, 4.0), n_months=36, level=60.0, noise=0.03):
    """SYNTHETIC: Aqua cell-days per month and region; the witness is Aqua times a planted B per region."""
    a = level * rng.uniform(0.7, 1.3, (n_months, len(b_true)))
    w = a * np.array(b_true) * np.exp(rng.normal(0.0, noise, a.shape))
    return a, w


def pick(rows, region, season="ALL"):
    return next(r for r in rows if r["region"] == region and r["season"] == season)


def test_a_planted_ratio_is_recovered_and_the_interval_covers_it():
    a, w = world(np.random.default_rng(1))
    rows = bl.indicator_rows(a, w, ["R1", "R2"], SEASONS_36, boot=300)
    for region, truth in (("R1", 2.0), ("R2", 4.0)):
        r = pick(rows, region)
        assert r["status"] == "OK"
        assert r["B"] == pytest.approx(truth, rel=0.03)
        assert r["B_lo90"] <= truth <= r["B_hi90"] or abs(r["B"] - truth) / truth < 0.02
        assert r["extra_share"] == pytest.approx(1 - 1 / r["B"])


def test_extra_share_formula_and_sign():
    assert bl.extra_share(4.0) == pytest.approx(0.75)
    assert bl.extra_share(1.0) == pytest.approx(0.0)
    assert bl.extra_share(0.5) == pytest.approx(-1.0)
    assert np.isnan(bl.extra_share(float("nan")))


def test_too_little_data_cannot_be_determined():
    a, w = world(np.random.default_rng(2), level=1.0)  # about 36 Aqua cell-days in total, below 100
    rows = bl.indicator_rows(a, w, ["R1", "R2"], SEASONS_36, boot=50)
    r = pick(rows, "R1")
    assert r["status"] == "CANNOT_DETERMINE" and np.isnan(r["B"])
    assert np.isnan(r["B_lo90"]) and np.isnan(r["B_hi90"])


def test_fewer_than_six_overlap_months_cannot_be_determined():
    a, w = world(np.random.default_rng(3), n_months=36, level=500.0)
    a[:, 0] = 0.0
    a[:5, 0] = 5000.0  # large sums but only 5 months with Aqua
    w[:, 0] = a[:, 0] * 2
    rows = bl.indicator_rows(a, w, ["R1", "R2"], SEASONS_36, boot=50)
    assert pick(rows, "R1")["status"] == "CANNOT_DETERMINE"
    assert pick(rows, "R2")["status"] == "OK"


def test_a_one_month_burst_is_flagged_but_still_shown():
    a, w = world(np.random.default_rng(4), level=20.0)
    a[7, 0], w[7, 0] = 5000.0, 9000.0
    rows = bl.indicator_rows(a, w, ["R1", "R2"], SEASONS_36, boot=50)
    r = pick(rows, "R1")
    assert r["status"] == "BURST" and np.isfinite(r["B"])
    assert pick(rows, "R2")["status"] == "OK"


def test_bootstrap_is_reproducible_with_a_fixed_seed():
    a, w = world(np.random.default_rng(5))
    r1 = bl.indicator_rows(a, w, ["R1", "R2"], SEASONS_36, boot=100, seed=7)
    r2 = bl.indicator_rows(a, w, ["R1", "R2"], SEASONS_36, boot=100, seed=7)
    assert r1 == r2 or all(
        (x[k] == y[k]) or (isinstance(x[k], float) and np.isnan(x[k]) and np.isnan(y[k])) for x, y in zip(r1, r2, strict=True) for k in x
    )


def test_only_the_months_of_the_season_are_used():
    a, w = world(np.random.default_rng(6), b_true=(2.0, 2.0))
    djf = SEASONS_36 == "DJF"
    w[djf, 0] = a[djf, 0] * 10.0  # DJF in R1 has B = 10, the rest 2
    rows = bl.indicator_rows(a, w, ["R1", "R2"], SEASONS_36, boot=50)
    assert pick(rows, "R1", "DJF")["B"] == pytest.approx(10.0, rel=0.05)
    assert pick(rows, "R1", "JJA")["B"] == pytest.approx(2.0, rel=0.05)
    assert pick(rows, "R2", "DJF")["B"] == pytest.approx(2.0, rel=0.05)


def test_regional_sums_equal_the_global_sums():
    a, w = world(np.random.default_rng(8), b_true=(1.5, 3.0, 5.0))
    rows = bl.indicator_rows(a, w, ["R1", "R2", "R3"], SEASONS_36, boot=30)
    reg = [pick(rows, r) for r in ("R1", "R2", "R3")]
    g = pick(rows, bl.GLOBAL)
    assert sum(r["sum_aqua"] for r in reg) == pytest.approx(g["sum_aqua"]) == pytest.approx(a.sum())
    assert sum(r["sum_viirs"] for r in reg) == pytest.approx(g["sum_viirs"]) == pytest.approx(w.sum())
    assert g["B"] == pytest.approx(w.sum() / a.sum())


def test_more_months_give_a_narrower_interval():
    a, w = world(np.random.default_rng(9), n_months=48, noise=0.3)
    seasons = np.array(["DJF", "MAM", "JJA", "SON"] * 12)
    rows = bl.indicator_rows(a, w, ["R1", "R2"], seasons, boot=400)
    wide = pick(rows, "R1", "DJF")  # 12 months
    narrow = pick(rows, "R1", "ALL")  # 48 months
    assert (narrow["B_hi90"] - narrow["B_lo90"]) < (wide["B_hi90"] - wide["B_lo90"])


def test_comparison_with_the_global_value_uses_the_interval():
    a, w = world(np.random.default_rng(10), b_true=(1.0, 6.0, 3.0), level=80.0, noise=0.02)
    rows = bl.indicator_rows(a, w, ["R1", "R2", "R3"], SEASONS_36, boot=200)
    assert pick(rows, "R1")["vs_global"] == "lower"
    assert pick(rows, "R2")["vs_global"] == "higher"
    assert pick(rows, bl.GLOBAL)["vs_global"] == ""


def test_caveat_text_is_in_every_row_and_says_what_it_is_not():
    a, w = world(np.random.default_rng(11))
    rows = bl.indicator_rows(a, w, ["R1", "R2"], SEASONS_36, boot=20)
    assert all("not a fire count" in r["caveat"] and "not burned area" in r["caveat"] for r in rows)


def test_fit_months_are_inside_the_fit_periods():
    for witness, ((y0, m0), (y1, m1)) in bl.cal.FITS.items():
        lo, hi = bl.cal.fit_months(witness)
        assert lo == y0 * 100 + m0 and hi == y1 * 100 + m1
        assert hi < 202201 or witness == "NOAA20_VIIRS"
    assert bl.cal.fit_months("SNPP_VIIRS")[1] == 201612  # S-NPP 2017 onwards is never used
    assert bl.cal.fit_months("NOAA20_VIIRS")[1] == 202112
