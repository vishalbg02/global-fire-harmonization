"""Tests for pipeline/conversion_v02.py and the `factors` path of harmonize.aggregate on SYNTHETIC data with known answers (T-020c).

    python -m pytest pipeline/tests/test_conversion_v02.py -q
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import calibration as cal
import conversion_v02 as cv
import harmonize as hz
import saturation as sat

SEASONS = ["DJF", "MAM", "JJA", "SON"]
S1, S2 = "NHAF_b001_001", "NHAF_b001_002"
CELLS = {"A1": S1, "A2": S1, "B1": S2}                      # S1 has two analysis cells, S2 one
RATIOS = {S1: (0.5, 0.05, 0.1, 0.01), S2: (0.25, 0.02, 0.05, 0.005)}   # ratio D, sd D, ratio N, sd N (every season, both witnesses)


# ------------------------------------------------------------------------------------------------ the factor fit
def planted(n_months=40, per_month=300, gain=lambda x: 1.0, seed=1):
    """Units with a known Aqua/converted relation: aqua = conv x gain(x) (exactly), activity x log-uniform over the bins."""
    rng = np.random.default_rng(seed)
    month = np.repeat(np.arange(n_months), per_month)
    x = np.exp(rng.uniform(np.log(0.02), np.log(80.0), len(month)))
    conv = x * 4.0                                        # a stratum of 4 cells
    aqua = conv * gain(x)
    return month, x, aqua, conv, n_months


def test_a_planted_ratio_that_rises_with_activity_is_recovered_by_bin():
    month, x, aqua, conv, n = planted(gain=lambda x: 0.5 + 0.1 * np.log10(x + 1.0) * 5)
    out = cv.fit_bins(month, x, aqua, conv, n, boot=200)
    bins = sat.bin_index(x)
    for b in range(len(cv.EDGES) - 1):
        sel = bins == b
        if sel.sum() >= cv.MIN_UNITS:
            assert out["f"][b] == pytest.approx(aqua[sel].sum() / conv[sel].sum(), rel=1e-12)
    ok = np.where(out["units"] >= cv.MIN_UNITS)[0]
    assert np.all(np.diff(out["f"][ok]) > 0)                  # the planted rise shows in the factors
    assert not out["filled"][ok].any()


def test_a_constant_ratio_gives_factors_of_one_and_zero_spread():
    month, x, aqua, conv, n = planted(gain=lambda x: 1.0)
    out = cv.fit_bins(month, x, aqua, conv, n, boot=100)
    assert np.allclose(out["f"], 1.0) and np.allclose(out["f_sd"], 0.0, atol=1e-12)


def test_units_without_a_witness_count_do_not_enter_the_fit():
    month, x, aqua, conv, n = planted(gain=lambda x: 2.0)
    conv2 = conv.copy()
    conv2[:500] = 0.0                                           # an unscalable unit with Aqua activity: ignored
    a = cv.fit_bins(month, x, aqua, conv2, n, boot=50)
    keep = conv2 > 0
    b = cv.fit_bins(month[keep], x[keep], aqua[keep], conv2[keep], n, boot=50)
    assert np.allclose(a["f"], b["f"], equal_nan=True) and np.array_equal(a["units"], b["units"])


def test_a_bin_with_too_few_units_takes_the_nearest_eligible_bin_and_its_error():
    month, x, aqua, conv, n = planted(gain=lambda x: np.where(x > 30, 3.0, 1.0), per_month=300)
    keep = (x < 15) | (x >= 50) | (np.arange(len(x)) % 5000 == 0)   # thin out the 15 to 50 bin (bin 6)
    out = cv.fit_bins(month[keep], x[keep], aqua[keep], conv[keep], n, boot=100, min_units=50)
    thin = np.where(out["units"] < 50)[0]
    assert len(thin) >= 1 and out["filled"][thin].all()
    for j in thin:
        eligible = np.where(out["units"] >= 50)[0]
        near = eligible[np.argmin(np.abs(eligible - j))]
        assert out["f"][j] == out["f"][near] and out["f_sd"][j] == out["f_sd"][near]
    assert not out["filled"][out["units"] >= 50].any()


def test_the_bootstrap_is_reproducible_and_depends_on_the_seed():
    month, x, aqua, conv, n = planted(gain=lambda x: 1.0 + 0.2 * np.sin(x), per_month=100)
    a, b = cv.fit_bins(month, x, aqua, conv, n, boot=100, seed=7), cv.fit_bins(month, x, aqua, conv, n, boot=100, seed=7)
    c = cv.fit_bins(month, x, aqua, conv, n, boot=100, seed=8)
    assert np.array_equal(a["f_sd"], b["f_sd"], equal_nan=True) and not np.array_equal(a["f_sd"], c["f_sd"], equal_nan=True)
    assert np.all(a["f_sd"][a["units"] >= 50] > 0)


def test_the_bin_edges_are_those_of_the_saturation_diagnostic():
    assert np.array_equal(cv.EDGES, sat.EDGES)
    x = np.array([0.0, 0.0499, 0.05, 0.1499, 0.15, 14.99, 15.0, 49.9, 50.0, 1e6])
    assert list(sat.bin_index(x)) == [0, 0, 1, 1, 2, 5, 6, 6, 7, 7]


def test_factor_table_has_one_row_per_witness_daynight_and_bin():
    month, x, aqua, conv, n = planted(gain=lambda x: 1.5)
    r = cv.fit_bins(month, x, aqua, conv, n, boot=50)
    t = cv.factor_table({("SNPP_VIIRS", "D"): r, ("SNPP_VIIRS", "N"): r})
    assert len(t) == 2 * (len(cv.EDGES) - 1) and np.isinf(t.hi.iloc[-1]) and t.lo.iloc[0] == 0.0
    assert set(t.columns) >= {"witness", "daynight", "lo", "hi", "f", "f_sd"}


def test_the_fit_reads_only_the_calibration_fit_periods():
    """`fit_factors` takes its units from saturation.load_units, which is calibration.monthly_sums: the T-011 fit months only."""
    assert "monthly_sums" in inspect.getsource(sat.load_units)
    assert cal.FITS["SNPP_VIIRS"] == ((2012, 1), (2016, 12)) and cal.FITS["NOAA20_VIIRS"] == ((2018, 4), (2021, 12))


# ---------------------------------------------------------------------------------- aggregate with and without factors
def make(tmp: Path, rows: list[tuple]) -> hz.Paths:
    pq.write_table(pa.table({"cell_id": list(CELLS), "stratum_id": list(CELLS.values())}), tmp / "cells.parquet")
    cal = [(s, w, dn, season, r, sd, 12, "x", "LOCAL") for s, (rd, sdd, rn, sdn) in RATIOS.items() for w in ("SNPP_VIIRS", "NOAA20_VIIRS")
           for dn, r, sd in (("D", rd, sdd), ("N", rn, sdn)) for season in SEASONS]
    pq.write_table(pa.Table.from_pandas(pd.DataFrame(cal, columns=["stratum_id", "witness", "daynight", "season", "ratio", "ratio_sd",
                                                                   "n_overlap_months", "fit_period", "pooling_level"]), preserve_index=False),
                   tmp / "calibration.parquet")
    df = pd.DataFrame([(c, 2020, 7, w, dn, n, n, 0.0, 31, 31, "SP") for (c, w, dn), n in rows],
                      columns=["cell_id", "year", "month", "witness", "daynight", "detections", "cell_days", "frp_sum_mw",
                               "days_available", "days_in_month", "data_level"])
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), tmp / "cell_month_witness.parquet")
    return hz.Paths(products=tmp, tmp=tmp / "dbtmp")


ROWS = [(("A1", "SNPP_VIIRS", "D"), 60), (("A2", "SNPP_VIIRS", "D"), 40), (("B1", "SNPP_VIIRS", "D"), 80),
        (("A1", "SNPP_VIIRS", "N"), 50), (("A1", "AQUA_MODIS", "D"), 70), (("B1", "AQUA_MODIS", "D"), 30)]


def run_aggregate(paths: hz.Paths, factors=None) -> pd.DataFrame:
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    members = pd.DataFrame({"entity_type": "CUSTOM", "entity_id": "X", "entity_name": "x", "cell_id": list(CELLS)})
    con.register("members_df", members)
    con.execute("CREATE TEMP TABLE members AS SELECT * FROM members_df")
    return hz.aggregate(con, paths, "members", None, factors)


def factor_rows(value_by_bin: dict[int, tuple[float, float]], default=(1.0, 0.0)) -> pd.DataFrame:
    rows = []
    for w in ("SNPP_VIIRS", "NOAA20_VIIRS"):
        for dn in ("D", "N"):
            for b in range(len(cv.EDGES) - 1):
                f, sd = value_by_bin.get(b, default)
                rows.append({"witness": w, "daynight": dn, "lo": float(cv.EDGES[b]),
                             "hi": float(cv.EDGES[b + 1]) if np.isfinite(cv.EDGES[b + 1]) else float("inf"), "f": f, "f_sd": sd})
    return pd.DataFrame(rows)


def row(agg, witness, dn):
    return agg[(agg.witness == witness) & (agg.daynight == dn)].iloc[0]


def test_without_factors_the_result_is_the_method_0_1_result_by_hand(tmp_path):
    agg = run_aggregate(make(tmp_path, ROWS))
    d = row(agg, "SNPP_VIIRS", "D")
    assert d.e == pytest.approx(0.5 * 100 + 0.25 * 80) and d.vc == pytest.approx(0.25 * 100 + 0.0625 * 80)
    assert d.vr == pytest.approx((100 * 0.05) ** 2 + (80 * 0.02) ** 2)


def test_factors_of_one_with_no_error_give_the_method_0_1_table_exactly(tmp_path):
    paths = make(tmp_path, ROWS)
    a, b = run_aggregate(paths), run_aggregate(paths, factor_rows({}))
    pd.testing.assert_frame_equal(a, b)


def test_a_factor_scales_the_estimate_the_counting_variance_and_the_ratio_error_by_hand(tmp_path):
    # S1 day: 100 cell-days x ratio 0.5 / 2 cells = 25 -> bin 6 (15 to 50); S2 day: 80 x 0.25 / 1 = 20 -> bin 6. f = 2, f_sd = 0.1
    agg = run_aggregate(make(tmp_path, ROWS), factor_rows({6: (2.0, 0.1)}))
    d = row(agg, "SNPP_VIIRS", "D")
    assert d.e == pytest.approx(2 * (0.5 * 100 + 0.25 * 80))
    assert d.vc == pytest.approx(1.0 * 100 + 0.25 * 80)                       # (r f)^2 x cell-days
    own = (100 * 0.05 * 2) ** 2 + (80 * 0.02 * 2) ** 2                       # stratum ratio errors scaled by f, one group per stratum
    shared = (100 * 0.5 * 0.1 + 80 * 0.25 * 0.1) ** 2                         # the factor error: one fully correlated group per bin
    assert d.vr == pytest.approx(own + shared)
    assert d.rbar == pytest.approx((1.0 + 0.5) / 2)


def test_the_factor_error_of_a_bin_is_fully_correlated_across_strata_and_independent_across_bins(tmp_path):
    # night: A1 only, S1: 50 x 0.1 / 2 = 2.5 -> bin 4 (1.5 to 5); day strata are in bin 6
    agg = run_aggregate(make(tmp_path, ROWS), factor_rows({6: (2.0, 0.1), 4: (1.5, 0.2)}))
    n = row(agg, "SNPP_VIIRS", "N")
    assert n.e == pytest.approx(1.5 * 0.1 * 50)
    assert n.vr == pytest.approx((50 * 0.01 * 1.5) ** 2 + (50 * 0.1 * 0.2) ** 2)


def test_aqua_is_never_scaled_and_has_no_factor_error(tmp_path):
    paths = make(tmp_path, ROWS)
    a, b = run_aggregate(paths), run_aggregate(paths, factor_rows({6: (2.0, 0.1)}))
    pd.testing.assert_frame_equal(a[a.witness == "AQUA_MODIS"].reset_index(drop=True), b[b.witness == "AQUA_MODIS"].reset_index(drop=True))


def test_activity_comes_from_the_whole_stratum_not_only_the_cells_of_the_entity(tmp_path):
    """An entity holding only cell A1 still bins on the stratum activity (A1 + A2) / 2 cells, so its factor is the bin of 25."""
    paths = make(tmp_path, ROWS)
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.register("members_df", pd.DataFrame({"entity_type": "CUSTOM", "entity_id": "X", "entity_name": "x", "cell_id": ["A1"]}))
    con.execute("CREATE TEMP TABLE members AS SELECT * FROM members_df")
    agg = hz.aggregate(con, paths, "members", None, factor_rows({6: (2.0, 0.0)}))
    assert row(agg, "SNPP_VIIRS", "D").e == pytest.approx(2.0 * 0.5 * 60)       # A1 alone has 60 cell-days; its stratum has 100


def test_a_viirs_row_without_a_factor_is_an_error_not_a_silent_one(tmp_path):
    f = factor_rows({6: (2.0, 0.1)})
    f = f[~((f.lo == 15.0) & (f.witness == "SNPP_VIIRS") & (f.daynight == "D"))]
    with pytest.raises(ValueError, match="no activity factor"):
        run_aggregate(make(tmp_path, ROWS), f)


def test_factors_need_their_columns(tmp_path):
    with pytest.raises(ValueError, match="columns"):
        run_aggregate(make(tmp_path, ROWS), factor_rows({}).drop(columns=["f_sd"]))
