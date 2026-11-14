"""Tests for pipeline/calibration.py on synthetic data with known ratios (T-011).

    python -m pytest pipeline/tests/test_calibration.py -q
"""
from __future__ import annotations

import calendar
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import calibration as cal

REGIONS = {"NHAF": 0.60, "SHAF": 0.50, "EURO": 0.70}   # true witness-to-Aqua multiplier of the region: Aqua = ratio x witness
BLOCKS_PER_REGION = 8


def make_products(tmp: Path, sigma: float = 0.0, lam: float = 20.0, seed: int = 1, sparse_block: str | None = None,
                  partial: tuple = (), holdout_outlier: bool = False, unassigned_blocks: int = 0, spike_block: str | None = None):
    """Write cells.parquet and cell_month_witness.parquet. Aqua ~ Poisson(lam); witness ~ Poisson(lam / ratio)."""
    rng = np.random.default_rng(seed)
    cells, truth = [], {}
    for ri, (region, r_reg) in enumerate(REGIONS.items()):
        for b in range(BLOCKS_PER_REGION):
            lat0, lon0 = -40.0 + 2.5 * b + 0.01, -20.0 + 20.0 * ri + 0.01
            sid = cal.stratum_id(region, lat0 + 0.25, lon0 + 0.25)
            truth[sid] = r_reg * float(np.exp(sigma * rng.standard_normal()))
            for k in range(4):  # four 0.5 degree cells per 2.5 degree block (a 2 x 2 patch)
                cells.append((f"{sid}#{k}", region, lat0 + 0.5 * (k // 2) + 0.25, lon0 + 0.5 * (k % 2) + 0.25, sid))
    for b in range(unassigned_blocks):
        lat0, lon0 = 20.0 + 2.5 * b + 0.01, 60.0 + 0.01
        sid = cal.stratum_id(cal.UNASSIGNED, lat0 + 0.25, lon0 + 0.25)
        truth[sid] = 0.55
        for k in range(4):
            cells.append((f"{sid}#{k}", cal.UNASSIGNED, lat0 + 0.5 * (k // 2) + 0.25, lon0 + 0.5 * (k % 2) + 0.25, sid))
    cdf = pd.DataFrame(cells, columns=["cell_id", "fire_region", "lat_c", "lon_c", "stratum_true"])
    cells_tbl = pa.table({"cell_id": cdf.cell_id, "lat_min": cdf.lat_c - 0.25, "lat_max": cdf.lat_c + 0.25, "lon_min": cdf.lon_c - 0.25,
                          "lon_max": cdf.lon_c + 0.25, "lat_c": cdf.lat_c, "lon_c": cdf.lon_c, "area_km2": [3000.0] * len(cdf),
                          "country_iso3": ["XXX"] * len(cdf), "continent": ["AF"] * len(cdf), "fire_region": cdf.fire_region,
                          "stratum_id": ["old"] * len(cdf)})
    pq.write_table(cells_tbl, tmp / "cells.parquet")
    months = [(y, m) for y in range(2012, 2022) for m in range(1, 13)]
    rows = []
    for w, (lo, hi) in {"AQUA_MODIS": ((2012, 1), (2021, 12)), "SNPP_VIIRS": ((2012, 1), (2021, 12)),
                        "NOAA20_VIIRS": ((2018, 4), (2021, 12))}.items():
        for (y, m) in months:
            if not (lo <= (y, m) <= hi):
                continue
            dim = calendar.monthrange(y, m)[1]
            da = dim - 3 if (w == "SNPP_VIIRS" and (y, m) in partial) else dim
            for cid, sid_true, block_lam in zip(cdf.cell_id, cdf.stratum_true, [lam] * len(cdf), strict=True):
                lam_c = 0.05 if (sparse_block is not None and sid_true == sparse_block) else block_lam
                a = rng.poisson(lam_c)
                ratio = truth[sid_true]
                wv = rng.poisson(lam_c / ratio)
                if holdout_outlier and y >= 2017 and w != "AQUA_MODIS":
                    wv += 500
                if (y, m) in partial and w == "SNPP_VIIRS":
                    wv += 800
                a_n, w_n = rng.poisson(lam_c / 4), rng.poisson(lam_c / 4 / ratio)   # night: a quarter of the day activity
                if spike_block is not None and sid_true == spike_block:            # activity in one single month, wild ratio
                    a, wv, a_n, w_n = (4, 1, 0, 0) if (y, m) == (2013, 7) else (0, 0, 0, 0)
                for dn, n in (("D", a if w == "AQUA_MODIS" else wv), ("N", a_n if w == "AQUA_MODIS" else w_n)):
                    rows.append((cid, y, m, w, dn, n, n, 0.0, da, dim, "SP"))
    df = pd.DataFrame(rows, columns=["cell_id", "year", "month", "witness", "daynight", "detections", "cell_days", "frp_sum_mw",
                                     "days_available", "days_in_month", "data_level"])
    allrows = df.groupby(["cell_id", "year", "month", "witness"], as_index=False).agg(
        detections=("detections", "sum"), cell_days=("cell_days", "sum"), frp_sum_mw=("frp_sum_mw", "sum"),
        days_available=("days_available", "first"), days_in_month=("days_in_month", "first"), data_level=("data_level", "first"))
    allrows["daynight"] = "ALL"
    full = pd.concat([df, allrows[df.columns]], ignore_index=True)
    pq.write_table(pa.Table.from_pandas(full, preserve_index=False), tmp / "cell_month_witness.parquet")
    return cal.Paths(products=tmp, tmp=tmp / "dbtmp"), truth


def run(tmp, boot=60, **kw):
    paths, truth = make_products(tmp, **kw)
    table, report = cal.calibrate(paths, boot=boot, seed=5)
    return paths, pd.DataFrame(table), report, truth


def pick(df, witness="SNPP_VIIRS", dn="D", season="JJA"):
    d = df[(df.witness == witness) & (df.daynight == dn) & (df.season == season)].copy()
    return d.set_index("stratum_id")


# ----------------------------------------------------------------------------------- basics
def test_stratum_id_is_a_block_inside_a_fire_region():
    assert cal.stratum_id("NHAF", 10.1, 20.1) == "NHAF_b040_080"
    assert cal.stratum_id("NHAF", 11.2, 20.1) == "NHAF_b040_080"          # same 2.5 degree block
    assert cal.stratum_id("NHAF", 12.6, 20.1) == "NHAF_b041_080"          # next block to the north
    assert cal.stratum_id("SHAF", 10.1, 20.1) != cal.stratum_id("NHAF", 10.1, 20.1)   # another region: another stratum


def test_seasons():
    assert [cal.SEASON_OF[m] for m in (12, 1, 2)] == ["DJF"] * 3 and cal.SEASON_OF[6] == "JJA" and cal.SEASON_OF[11] == "SON"


def test_fit_windows():
    assert cal.fit_months("SNPP_VIIRS") == (201201, 201612) and cal.fit_months("NOAA20_VIIRS") == (201804, 202112)


def test_dl_tau2_is_zero_without_spread_and_positive_with_it():
    rng = np.random.default_rng(0)
    v = np.full(40, 0.01)
    g = np.zeros(40, dtype=int)
    assert cal.dl_tau2(np.full(40, 0.5) + rng.normal(0, 0.1, 40), v, g) < 0.01          # spread equals the noise: about zero
    spread = np.full(40, 0.5) + rng.normal(0, np.sqrt(0.01 + 0.09), 40)                 # true between-unit variance 0.09
    assert 0.05 < cal.dl_tau2(spread, v, g) < 0.15
    assert cal.dl_tau2(np.array([0.1, 0.2]), np.array([0.01, 0.01]), np.zeros(2, dtype=int)) == 0.0   # too few units


def test_pooling_level_picks_the_largest_weight_and_ties_go_local():
    w = np.array([[0.6, 0.3, 0.1], [0.1, 0.6, 0.3], [0.1, 0.2, 0.7], [0.4, 0.4, 0.2]])
    assert cal.pooling_level(w).tolist() == [0, 1, 2, 0]


# ---------------------------------------------------------------------------- the estimator
def test_planted_ratios_are_recovered_when_strata_do_not_differ(tmp_path):
    _, df, report, truth = run(tmp_path, sigma=0.0, lam=30.0)
    d = pick(df)
    assert len(d) == len(truth) and set(d.index) == set(truth)
    err = np.abs(d.ratio / pd.Series(truth)[d.index] - 1)
    assert err.max() < 0.06
    t2 = next(t for t in report["tau2"] if (t["witness"], t["daynight"], t["season"]) == ("SNPP_VIIRS", "D", "JJA"))
    assert t2["tau2_local"] < 0.01                         # no real difference between strata: pooling is strong
    assert (d.pooling_level != "LOCAL").mean() > 0.5


def test_data_rich_strata_stay_local_when_strata_differ(tmp_path):
    _, df, report, truth = run(tmp_path, sigma=0.35, lam=200.0)
    d = pick(df)
    err = np.abs(d.ratio / pd.Series(truth)[d.index] - 1)
    assert err.max() < 0.08
    assert (d.pooling_level == "LOCAL").mean() > 0.8
    t2 = next(t for t in report["tau2"] if (t["witness"], t["daynight"], t["season"]) == ("SNPP_VIIRS", "D", "JJA"))
    assert 0.03 < t2["tau2_local"] < 0.4                   # the planted between-stratum spread is 0.35^2 = 0.12


def test_a_sparse_stratum_shrinks_toward_its_region(tmp_path):
    sparse = cal.stratum_id("NHAF", -40.0 + 2.5 * 3 + 0.26, -20.0 + 0.26)
    _, df, _, truth = run(tmp_path, sigma=0.3, lam=100.0, sparse_block=sparse)
    d = pick(df)
    assert d.loc[sparse, "pooling_level"] != "LOCAL"
    assert d.loc[sparse, "n_overlap_months"] <= 15
    region_ratio = np.exp(np.mean(np.log([truth[s] for s in d.index if s.startswith("NHAF_") and s != sparse])))
    assert abs(np.log(d.loc[sparse, "ratio"] / region_ratio)) < 0.35      # pulled to the region, not left wild
    rich = d[(d.index != sparse) & d.index.str.startswith("NHAF_")]
    assert (rich.pooling_level == "LOCAL").all()


def test_unassigned_strata_pool_to_the_global_ratio(tmp_path):
    _, df, _, _ = run(tmp_path, sigma=0.0, lam=0.3, unassigned_blocks=3)
    d = pick(df)
    un = d[d.index.str.startswith("UNASSIGNED_")]
    assert len(un) == 3 and set(un.pooling_level) <= {"LOCAL", "GLOBAL"}   # never REGION: there is no region level for them


def test_the_holdout_years_and_partial_months_are_never_used(tmp_path):
    base_dir, clean_dir = tmp_path / "a", tmp_path / "b"
    base_dir.mkdir()
    clean_dir.mkdir()
    _, a, ra, _ = run(base_dir, sigma=0.2, lam=40.0, seed=3)
    _, b, rb, _ = run(clean_dir, sigma=0.2, lam=40.0, seed=3, holdout_outlier=True, partial=((2014, 5),))
    # S-NPP rows are unchanged except 2017 onward (held out) and one partial month (excluded)
    key = ["stratum_id", "witness", "daynight", "season"]
    sa = a[(a.witness == "SNPP_VIIRS") & (a.season != "MAM")].set_index(key).sort_index()
    sb = b[(b.witness == "SNPP_VIIRS") & (b.season != "MAM")].set_index(key).sort_index()
    # the ratios agree to within a few percent (the bootstrap stream shifts when a month is dropped); a leak of the planted
    # outliers (+500 per cell-month, or +800 in the partial month) would change them by orders of magnitude
    np.testing.assert_allclose(sa.ratio.to_numpy(), sb.ratio.to_numpy(), rtol=0.03)
    assert (sa.n_overlap_months == sb.n_overlap_months).mean() > 0.9
    assert [e for e in rb["excluded"]["SNPP_VIIRS"] if e[:2] == (2014, 5)] and rb["months"]["SNPP_VIIRS"] == ra["months"]["SNPP_VIIRS"] - 1


def test_the_fit_months_stay_inside_the_fit_period(tmp_path):
    paths, _ = make_products(tmp_path)
    con = cal.duckdb.connect()
    cells = cal.load_cells(paths)
    months, _, _ = cal.monthly_sums(con, paths, "SNPP_VIIRS", dict(zip(cells["cell_id"], cal.assign_strata(cells), strict=True)))
    assert months[0] == (2012, 1) and months[-1] == (2016, 12) and len(months) == 60
    months20, _, _ = cal.monthly_sums(con, paths, "NOAA20_VIIRS", dict(zip(cells["cell_id"], cal.assign_strata(cells), strict=True)))
    assert months20[0] == (2018, 4) and months20[-1] == (2021, 12) and len(months20) == 45


def test_the_bootstrap_is_reproducible_and_shrinks_with_more_data(tmp_path):
    d1, d2, d3 = tmp_path / "1", tmp_path / "2", tmp_path / "3"
    for d in (d1, d2, d3):
        d.mkdir()
    _, a, _, _ = run(d1, sigma=0.2, lam=20.0, seed=9)
    paths, _ = make_products(d2, sigma=0.2, lam=20.0, seed=9)
    again, _ = cal.calibrate(paths, boot=60, seed=5)
    pd.testing.assert_frame_equal(a.reset_index(drop=True), pd.DataFrame(again))                 # same seed, same result
    _, b, _, _ = run(d3, sigma=0.2, lam=120.0, seed=9)                                           # six times the counts
    assert pick(b).ratio_sd.median() < 0.6 * pick(a).ratio_sd.median()


def test_every_stratum_witness_daynight_season_has_a_row_and_the_table_validates(tmp_path):
    paths, df, _, truth = run(tmp_path, sigma=0.1, lam=30.0)
    assert len(df) == len(truth) * 2 * 3 * 4
    assert df.groupby("witness").fit_period.first().to_dict() == {"NOAA20_VIIRS": "2018-04/2021-12", "SNPP_VIIRS": "2012-01/2016-12"}
    cal.write(paths, df.to_dict("list"))
    cal.regenerate_cells(paths)
    assert cal.validate(paths) == []


def test_the_validator_rejects_a_bad_table(tmp_path):
    paths, df, _, _ = run(tmp_path, sigma=0.1, lam=30.0)
    bad = df.copy()
    bad.loc[0, "ratio"] = -1.0
    bad.loc[1, "pooling_level"] = "NATIONAL"
    bad = bad.iloc[:-5]
    cal.write(paths, bad.to_dict("list"))
    cal.regenerate_cells(paths)
    text = " | ".join(cal.validate(paths))
    assert "ratio must be positive" in text and "pooling_level" in text and "expected" in text


def test_regenerating_cells_writes_the_final_stratum_rule(tmp_path):
    paths, _ = make_products(tmp_path)
    n = cal.regenerate_cells(paths)
    t = pq.read_table(paths.products / "cells.parquet").to_pandas()
    assert n == len(REGIONS) * BLOCKS_PER_REGION and (t.stratum_id != "old").all()
    assert t.stratum_id.str.match(r"^[A-Z]+_b\d{3}_\d{3}$").all()


def test_a_stratum_with_one_active_month_does_not_keep_its_own_ratio(tmp_path):
    spike = cal.stratum_id("SHAF", -40.0 + 2.5 * 5 + 0.26, 0.26)
    _, df, _, _ = run(tmp_path, sigma=0.35, lam=100.0, spike_block=spike)
    d = pick(df)
    assert d.loc[spike, "n_overlap_months"] == 1
    assert d.loc[spike, "pooling_level"] != "LOCAL"           # its local ratio (4.0) rests on one month of a few counts
    assert d.loc[spike, "ratio"] < 1.5                        # pulled well toward the region (about 0.5), not left at 4
    # without the counting-noise floor its bootstrap variance is about 1e-30, which breaks the between-stratum variance
    # for the whole group; with the floor the data-rich strata of the same region still keep their own ratio
    rich = d[d.index.str.startswith("SHAF_") & (d.index != spike)]
    assert (rich.pooling_level == "LOCAL").mean() > 0.8
