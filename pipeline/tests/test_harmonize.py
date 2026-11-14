"""Tests for pipeline/harmonize.py on SYNTHETIC data with answers known by hand (T-013).

    python -m pytest pipeline/tests/test_harmonize.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import contract_check as cc
import harmonize as hz

SEASONS = ["DJF", "MAM", "JJA", "SON"]
CELLS = {"A1": "S1", "A2": "S1", "B1": "S2", "C1": "S3"}          # cell -> stratum
# calibration: stratum -> (ratio D, sd D, ratio N, sd N), the same for every season and for both VIIRS witnesses
RATIOS = {"S1": (0.5, 0.05, 0.1, 0.01), "S2": (0.25, 0.02, 0.05, 0.005), "S3": (0.5, 0.05, 0.1, 0.01)}


def make(tmp: Path, rows: list[tuple]) -> hz.Paths:
    """rows: (cell, year, month, witness, daynight, cell_days, days_available, days_in_month, data_level)."""
    pq.write_table(pa.table({"cell_id": list(CELLS), "stratum_id": list(CELLS.values())}), tmp / "cells.parquet")
    cal = [(s, w, dn, season, r, sd, 12, "x", "LOCAL") for s, (rd, sdd, rn, sdn) in RATIOS.items() for w in ("SNPP_VIIRS", "NOAA20_VIIRS")
           for dn, r, sd in (("D", rd, sdd), ("N", rn, sdn)) for season in SEASONS]
    pq.write_table(pa.Table.from_pandas(pd.DataFrame(cal, columns=["stratum_id", "witness", "daynight", "season", "ratio", "ratio_sd",
                                                                   "n_overlap_months", "fit_period", "pooling_level"]), preserve_index=False),
                   tmp / "calibration.parquet")
    df = pd.DataFrame([r[:5] + (r[5], r[5], 0.0) + r[6:] for r in rows],
                      columns=["cell_id", "year", "month", "witness", "daynight", "detections", "cell_days", "frp_sum_mw",
                               "days_available", "days_in_month", "data_level"])
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), tmp / "cell_month_witness.parquet")
    return hz.Paths(products=tmp, tmp=tmp / "dbtmp")


def month_rows(year, month, spec, dim=31, avail=None, level="SP"):
    """spec: {(cell, witness, daynight): cell_days}; avail: {witness: days_available}."""
    avail = avail or {}
    return [(c, year, month, w, dn, n, avail.get(w, dim), dim, level) for (c, w, dn), n in spec.items()]


# A1 + A2 in S1, B1 in S2 (see RATIOS)
SNPP = {("A1", "SNPP_VIIRS", "D"): 60, ("A2", "SNPP_VIIRS", "D"): 40, ("A1", "SNPP_VIIRS", "N"): 50,
        ("B1", "SNPP_VIIRS", "D"): 80, ("B1", "SNPP_VIIRS", "N"): 20}


# -------------------------------------------------------------------------------------------- the combination
def test_precision_weighted_mean_and_disagreement_scale_by_hand():
    c = hz.combine(np.array([[100.0, 200.0, np.nan]]), np.array([[1.0, 4.0, np.nan]]), np.array([[True, True, False]]))
    assert c["estimate"][0] == pytest.approx(120.0)                       # (100/1 + 200/4) / (1 + 1/4)
    assert c["chi2"][0] == pytest.approx(2000.0)                          # 20^2/1 + 80^2/4
    assert c["scale"][0] == pytest.approx(np.sqrt(2000.0)) and bool(c["inflated"][0])
    assert c["sd"][0] == pytest.approx(np.sqrt(1 / 1.25) * np.sqrt(2000.0))


def test_equal_witnesses_get_no_inflation_and_a_single_witness_has_no_scale():
    c = hz.combine(np.array([[50.0, 50.0], [50.0, 70.0]]), np.array([[4.0, 4.0], [4.0, 4.0]]), np.array([[True, True], [True, False]]))
    assert c["chi2"][0] == 0.0 and c["scale"][0] == 1.0 and not c["inflated"][0]
    assert c["sd"][0] == pytest.approx(np.sqrt(1 / 0.5))                  # two witnesses of variance 4: variance 2
    assert np.isnan(c["scale"][1]) and c["n"][1] == 1 and c["estimate"][1] == 50.0 and c["sd"][1] == pytest.approx(2.0)


def test_no_usable_witness_gives_nothing():
    c = hz.combine(np.array([[np.nan, 5.0]]), np.array([[np.nan, 1.0]]), np.array([[False, False]]))
    assert c["n"][0] == 0 and np.isnan(c["estimate"][0]) and np.isnan(c["sd"][0]) and np.isnan(c["scale"][0])


def test_interval_has_a_floor_at_zero():
    lo, hi = hz.interval(2.0, 5.0)
    assert lo == 0.0 and hi == pytest.approx(2.0 + hz.Z90 * 5.0)


# --------------------------------------------------------------------------------------------- harmonize_area
def test_stratum_first_conversion_and_variance_by_hand(tmp_path):
    paths = make(tmp_path, month_rows(2020, 1, SNPP))
    (rec,) = hz.harmonize_area(["A1", "A2", "B1"], paths=paths)
    # S1: D 100 x 0.5 + N 50 x 0.1 = 55; S2: D 80 x 0.25 + N 20 x 0.05 = 21 (a single pooled ratio would give something else)
    assert rec["estimate"] == pytest.approx(76.0)
    pooled = (0.5 * 100 + 0.1 * 50 + 0.25 * 80 + 0.05 * 20)
    assert pooled == 76.0 and 76.0 != pytest.approx((0.5 + 0.25) / 2 * 150 + (0.1 + 0.05) / 2 * 70)
    # variance per stratum and day/night: r^2 x cd + cd^2 x sd^2, then added: 50 + 0.75 + 7.56 + 0.06
    assert rec["sd"] == pytest.approx(np.sqrt(58.37))
    assert rec["n_witnesses"] == 1 and rec["witnesses_used"] == ["SNPP_VIIRS"] and rec["reason_codes"] == ["SINGLE_WITNESS"]
    assert rec["disagreement_scale"] is None and rec["n_cells"] == 3
    assert json.loads(rec["raw_by_witness"]) == {"SNPP_VIIRS": 250} and rec["raw_combined_cell_days"] == 250


def test_equal_witnesses_are_not_inflated_and_conflicting_ones_are(tmp_path):
    aqua = {("A1", "AQUA_MODIS", "D"): 25, ("A1", "AQUA_MODIS", "N"): 5}                  # E = 25 + 5 = 30 (ratio 1)
    snpp_equal = {("A1", "SNPP_VIIRS", "D"): 50, ("A1", "SNPP_VIIRS", "N"): 50}           # E = 25 + 5 = 30
    snpp_high = {("A1", "SNPP_VIIRS", "D"): 200, ("A1", "SNPP_VIIRS", "N"): 200}          # E = 100 + 20 = 120
    paths = make(tmp_path, month_rows(2020, 1, {**aqua, **snpp_equal}) + month_rows(2020, 2, {**aqua, **snpp_high}))
    jan, feb = hz.harmonize_area(["A1"], paths=paths)
    assert jan["estimate"] == pytest.approx(30.0) and jan["disagreement_scale"] == 1.0 and "WITNESS_DISAGREEMENT" not in jan["reason_codes"]
    assert jan["n_witnesses"] == 2 and jan["witnesses_used"] == ["AQUA_MODIS", "SNPP_VIIRS"]
    assert feb["disagreement_scale"] > 1.0 and "WITNESS_DISAGREEMENT" in feb["reason_codes"] and "SINGLE_WITNESS" not in feb["reason_codes"]
    # the inflated sd is the plain combined sd times the scale
    v_aqua, v_snpp = 30.0 + 0.0, (0.25 * 200 + 40000 * 0.0025) + (0.01 * 200 + 40000 * 0.0001)
    plain = np.sqrt(1 / (1 / v_aqua + 1 / v_snpp))
    assert feb["sd"] == pytest.approx(plain * feb["disagreement_scale"]) and feb["ci90_low"] < feb["estimate"] < feb["ci90_high"]
    assert feb["estimate"] == pytest.approx((30 / v_aqua + 120 / v_snpp) / (1 / v_aqua + 1 / v_snpp))


def test_a_partial_month_witness_is_not_used_and_a_month_without_one_has_no_estimate(tmp_path):
    aqua = {("A1", "AQUA_MODIS", "D"): 25, ("A1", "AQUA_MODIS", "N"): 5}
    snpp = {("A1", "SNPP_VIIRS", "D"): 50, ("A1", "SNPP_VIIRS", "N"): 50}
    rows = (month_rows(2020, 1, {**aqua, **snpp}, avail={"SNPP_VIIRS": 20})                  # S-NPP has 20 of 31 days
            + month_rows(2020, 2, snpp, dim=29, avail={"SNPP_VIIRS": 2}))                      # only a partial S-NPP month
    paths = make(tmp_path, rows)
    jan, feb = hz.harmonize_area(["A1"], paths=paths)
    assert jan["witnesses_used"] == ["AQUA_MODIS"] and jan["reason_codes"] == ["SINGLE_WITNESS"] and jan["estimate"] == pytest.approx(30.0)
    assert json.loads(jan["raw_by_witness"]) == {"AQUA_MODIS": 30, "SNPP_VIIRS": 100}          # the raw view still shows it
    assert feb["estimate"] is None and feb["sd"] is None and feb["ci90_low"] is None and feb["n_witnesses"] == 0
    assert feb["witnesses_used"] == [] and feb["verdict"] == "CANNOT_DETERMINE" and feb["raw_combined_cell_days"] == 100


def test_the_aqua_cutoff_removes_aqua_after_it(tmp_path):
    aqua = {("A1", "AQUA_MODIS", "D"): 25, ("A1", "AQUA_MODIS", "N"): 5}
    snpp = {("A1", "SNPP_VIIRS", "D"): 50, ("A1", "SNPP_VIIRS", "N"): 50}
    paths = make(tmp_path, month_rows(2020, 1, {**aqua, **snpp}) + month_rows(2020, 2, {**aqua, **snpp}))
    both = hz.harmonize_area(["A1"], paths=paths)
    cut = hz.harmonize_area(["A1"], paths=paths, aqua_cutoff=(2020, 1))
    assert [r["witnesses_used"] for r in both] == [["AQUA_MODIS", "SNPP_VIIRS"]] * 2
    assert cut[0]["witnesses_used"] == ["AQUA_MODIS", "SNPP_VIIRS"] and "AQUA_DRIFT_ERA" not in cut[0]["reason_codes"]
    assert cut[1]["witnesses_used"] == ["SNPP_VIIRS"] and {"AQUA_DRIFT_ERA", "SINGLE_WITNESS"} <= set(cut[1]["reason_codes"])
    assert cut[1]["raw_combined_cell_days"] == both[1]["raw_combined_cell_days"]              # the raw view keeps Aqua


def test_nrt_months_are_flagged_and_terra_never_enters_the_estimate(tmp_path):
    spec = {("A1", "AQUA_MODIS", "D"): 25, ("A1", "AQUA_MODIS", "N"): 5, ("A1", "TERRA_MODIS", "D"): 1000, ("A1", "TERRA_MODIS", "N"): 1000}
    paths = make(tmp_path, month_rows(2020, 1, spec, level="NRT"))
    (rec,) = hz.harmonize_area(["A1"], paths=paths)
    assert rec["estimate"] == pytest.approx(30.0) and rec["witnesses_used"] == ["AQUA_MODIS"]
    assert rec["data_level"] == "NRT" and "PROVISIONAL_NRT" in rec["reason_codes"]
    assert json.loads(rec["raw_by_witness"]) == {"AQUA_MODIS": 30, "TERRA_MODIS": 2000} and rec["raw_combined_cell_days"] == 2030


def test_a_zero_count_keeps_a_variance_and_the_season_picks_the_ratio(tmp_path):
    zero = {("A1", "AQUA_MODIS", "D"): 0, ("A1", "AQUA_MODIS", "N"): 0, ("A1", "SNPP_VIIRS", "D"): 0, ("A1", "SNPP_VIIRS", "N"): 0}
    paths = make(tmp_path, month_rows(2020, 1, zero))
    (rec,) = hz.harmonize_area(["A1"], paths=paths)
    assert rec["estimate"] == 0.0 and rec["sd"] > 0 and rec["ci90_low"] == 0.0 and rec["ci90_high"] > 0
    # a seasonal ratio: change the SON ratio of S1 only; a September month must use it, a January month must not
    cal = pq.read_table(paths.products / "calibration.parquet").to_pandas()
    cal.loc[(cal.stratum_id == "S1") & (cal.season == "SON") & (cal.witness == "SNPP_VIIRS") & (cal.daynight == "D"), "ratio"] = 2.0
    pq.write_table(pa.Table.from_pandas(cal, preserve_index=False), paths.products / "calibration.parquet")
    snpp = {("A1", "SNPP_VIIRS", "D"): 10}
    paths = make(tmp_path, month_rows(2020, 1, snpp) + month_rows(2020, 9, snpp))
    cal.to_parquet(paths.products / "calibration.parquet")
    jan, sep = hz.harmonize_area(["A1"], paths=paths)
    assert jan["estimate"] == pytest.approx(5.0) and sep["estimate"] == pytest.approx(20.0)


def test_months_filter_order_determinism_and_bad_input(tmp_path):
    rows = []
    for m in (3, 1, 2):
        rows += month_rows(2020, m, SNPP)
    paths = make(tmp_path, rows)
    all_months = hz.harmonize_area(["B1", "A1", "A2"], paths=paths)
    assert [r["month"] for r in all_months] == [1, 2, 3]
    assert [r["month"] for r in hz.harmonize_area(["A1", "A2", "B1"], months=[(2020, 3), (2020, 1)], paths=paths)] == [1, 3]
    assert all_months == hz.harmonize_area(["A1", "B1", "A2", "A1"], paths=paths)               # order and duplicates do not matter
    assert hz.harmonize_area([], paths=paths) == []
    with pytest.raises(ValueError, match="not in cells.parquet"):
        hz.harmonize_area(["A1", "NOPE"], paths=paths)


def test_records_have_the_contract_shape(tmp_path):
    aqua = {("A1", "AQUA_MODIS", "D"): 25, ("A1", "AQUA_MODIS", "N"): 5}
    snpp = {("A1", "SNPP_VIIRS", "D"): 200, ("A1", "SNPP_VIIRS", "N"): 200}
    paths = make(tmp_path, month_rows(2020, 1, {**aqua, **snpp}) + month_rows(2020, 2, snpp, dim=29, avail={"SNPP_VIIRS": 3}))
    recs = hz.harmonize_area(["A1"], paths=paths)
    want = set(cc.SPEC["entity_month"])
    assert all(set(r) == want for r in recs)
    df = pd.DataFrame(recs)
    for col in ("estimate", "ci90_low", "ci90_high", "sd", "disagreement_scale", "baseline_median", "baseline_p25", "baseline_p75",
                "pct_of_normal", "p_above", "p_below", "p_within"):
        df[col] = df[col].astype(float)
    errors: list[str] = []
    cc.check_harmonized_rows("entity_month", df, errors)
    assert errors == []
    assert (df.method_version == hz.METHOD_VERSION).all() and df.baseline_median.isna().all() and (df.verdict == "CANNOT_DETERMINE").all()
