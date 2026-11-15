"""Tests for pipeline/large_fire.py on SYNTHETIC data with known answers (T-015).

    python -m pytest pipeline/tests/test_large_fire.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import large_fire as lf


def series(witness="SNPP_VIIRS", entity="XXX", n_ref=12, cell_days=200, det=400, frp=2000.0, start=(2012, 1)):
    """SYNTHETIC rows of consecutive months: S = det / cell_days, F = frp / cell_days."""
    rows, (y, m) = [], start
    for _ in range(n_ref):
        rows.append({"entity_type": "COUNTRY", "entity_id": entity, "year": y, "month": m, "witness": witness, "detections": det,
                     "cell_days": cell_days, "frp_sum_mw": frp, "active_cells": 5})
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return pd.DataFrame(rows)


def one_row(df, year, month, witness="SNPP_VIIRS", entity="XXX"):
    d = df[(df.year == year) & (df.month == month) & (df.witness == witness) & (df.entity_id == entity)]
    assert len(d) == 1
    return d.iloc[0]


def test_s_and_f_planted():
    d = lf.add_indices(series(cell_days=200, det=500, frp=3000.0))
    assert np.allclose(d["S"], 2.5) and np.allclose(d["F"], 15.0)


def test_zero_cell_days_has_no_s():
    d = lf.add_indices(series(cell_days=0, det=0, frp=0.0))
    assert d["S"].isna().all() and d["F"].isna().all() and (d["status"] == "LOW_COUNT").all()


def test_low_count_rows_are_shown_but_not_judged():
    ref = series(n_ref=12)
    low = series(n_ref=1, start=(2014, 1), cell_days=99, det=990).assign(year=2020)         # one low-count month outside the reference
    d = lf.add_indices(pd.concat([ref, low], ignore_index=True))
    r = one_row(d, 2020, 1)
    assert r["status"] == "LOW_COUNT" and r["S"] == 10.0
    assert np.isnan(r["s_index"]) and not r["flag_high"] and np.isnan(r["s_rel"])


def test_reference_median_and_index():
    ref = series(n_ref=12, det=400)                                                          # S = 2 in every reference month
    spike = series(n_ref=1, start=(2013, 1), det=1000).assign(year=2019, month=3)           # S = 5, outside the reference period
    d = lf.add_indices(pd.concat([ref, spike], ignore_index=True))
    r = one_row(d, 2019, 3)
    assert r["s_ref"] == 2.0 and r["s_index"] == 2.5 and r["flag_high"] and r["flag_high_2x"]
    assert np.isclose(r["f_index"], 1.0)                                                      # FRP per cell-day unchanged in the spike


def test_flag_boundary_at_the_factor():
    ref = series(n_ref=12, det=400)                                                          # S_ref = 2
    exact = series(n_ref=1, det=600).assign(year=2019, month=1)                              # S = 3 = 1.5 x 2 -> flagged
    below = series(n_ref=1, det=598).assign(year=2019, month=2)                              # S = 2.99 -> not flagged
    d = lf.add_indices(pd.concat([ref, exact, below], ignore_index=True))
    assert one_row(d, 2019, 1)["flag_high"] and not one_row(d, 2019, 1)["flag_high_2x"]
    assert not one_row(d, 2019, 2)["flag_high"]


def test_no_reference_with_too_few_months():
    d = lf.add_indices(series(n_ref=lf.MIN_REF_MONTHS - 1))
    assert (d["status"] == "NO_REFERENCE").all() and d["s_index"].isna().all() and not d["flag_high"].any()


def test_reference_period_differs_by_witness():
    n20 = series(witness="NOAA20_VIIRS", n_ref=12, start=(2012, 1))                          # all outside the NOAA-20 reference period
    d = lf.add_indices(n20)
    assert (d["status"] == "NO_REFERENCE").all()


def test_s_rel_against_aqua():
    aq = series(witness="AQUA_MODIS", det=300)                                               # S = 1.5
    vi = series(witness="SNPP_VIIRS", det=600)                                               # S = 3
    d = lf.add_indices(pd.concat([aq, vi], ignore_index=True))
    assert np.allclose(d.loc[d.witness == "SNPP_VIIRS", "s_rel"], 2.0)
    assert d.loc[d.witness == "AQUA_MODIS", "s_rel"].isna().all()


def test_aggregate_on_a_tiny_product(tmp_path):
    cells = pd.DataFrame({"cell_id": ["a", "b", "c"], "country_iso3": ["AAA", "AAA", None], "fire_region": ["R1", "R2", "R1"]})
    rows = []
    for cid, det, cd, frp in (("a", 10, 5, 100.0), ("b", 6, 2, 40.0), ("c", 3, 3, 30.0)):
        base = {"cell_id": cid, "year": 2013, "month": 5, "witness": "AQUA_MODIS"}
        rows.append({**base, "daynight": "ALL", "detections": det, "cell_days": cd, "frp_sum_mw": frp})
        rows.append({**base, "daynight": "D", "detections": 999, "cell_days": 999, "frp_sum_mw": 9e9})
    cells.to_parquet(tmp_path / "cells.parquet")
    pd.DataFrame(rows).to_parquet(tmp_path / "cell_month_witness.parquet")
    agg = lf.aggregate(duckdb.connect(), tmp_path).set_index(["entity_type", "entity_id"])
    assert agg.loc[("COUNTRY", "AAA"), "detections"] == 16 and agg.loc[("COUNTRY", "AAA"), "cell_days"] == 7
    assert ("COUNTRY", "None") not in agg.index and len(agg.loc["COUNTRY"]) == 1                # the cell without a country is in no country
    assert agg.loc[("FIRE_REGION", "R1"), "cell_days"] == 8 and agg.loc[("FIRE_REGION", "R2"), "detections"] == 6
    w = agg.loc[("GLOBAL", "WORLD")]
    assert w["detections"] == 19 and w["cell_days"] == 10 and w["active_cells"] == 3 and np.isclose(w["frp_sum_mw"], 170.0)   # D rows ignored
