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
S1, S2, S3 = "NHAF_b001_001", "NHAF_b001_002", "SHAF_b001_001"      # S1 and S2 lie in one fire region, S3 in another
CELLS = {"A1": S1, "A2": S1, "B1": S2, "C1": S3}                    # cell -> stratum
# calibration: stratum -> (ratio D, sd D, ratio N, sd N), the same for every season and for both VIIRS witnesses
RATIOS = {S1: (0.5, 0.05, 0.1, 0.01), S2: (0.25, 0.02, 0.05, 0.005), S3: (0.5, 0.05, 0.1, 0.01)}
PHI1 = {"D": 1.0, "N": 1.0}                                         # Poisson, unless a test says otherwise
K0 = {"D": 0.0, "N": 0.0}                                           # no size-dependent term, unless a test says otherwise


def make(tmp: Path, rows: list[tuple], levels: dict | None = None) -> hz.Paths:
    """rows: (cell, year, month, witness, daynight, cell_days, days_available, days_in_month, data_level)."""
    pq.write_table(pa.table({"cell_id": list(CELLS), "stratum_id": list(CELLS.values())}), tmp / "cells.parquet")
    levels = levels or {}
    cal = [(s, w, dn, season, r, sd, 12, "x", levels.get(s, "LOCAL")) for s, (rd, sdd, rn, sdn) in RATIOS.items() for w in ("SNPP_VIIRS", "NOAA20_VIIRS")
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
    (rec,) = hz.harmonize_area(["A1", "A2", "B1"], paths=paths, phi=PHI1, kappa=K0)
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
    jan, feb = hz.harmonize_area(["A1"], paths=paths, phi=PHI1, kappa=K0)
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
    jan, feb = hz.harmonize_area(["A1"], paths=paths, phi=PHI1, kappa=K0)
    assert jan["witnesses_used"] == ["AQUA_MODIS"] and jan["reason_codes"] == ["SINGLE_WITNESS"] and jan["estimate"] == pytest.approx(30.0)
    assert json.loads(jan["raw_by_witness"]) == {"AQUA_MODIS": 30, "SNPP_VIIRS": 100}          # the raw view still shows it
    assert feb["estimate"] is None and feb["sd"] is None and feb["ci90_low"] is None and feb["n_witnesses"] == 0
    assert feb["witnesses_used"] == [] and feb["verdict"] == "CANNOT_DETERMINE" and feb["raw_combined_cell_days"] == 100


def test_the_aqua_cutoff_removes_aqua_after_it(tmp_path):
    aqua = {("A1", "AQUA_MODIS", "D"): 25, ("A1", "AQUA_MODIS", "N"): 5}
    snpp = {("A1", "SNPP_VIIRS", "D"): 50, ("A1", "SNPP_VIIRS", "N"): 50}
    paths = make(tmp_path, month_rows(2020, 1, {**aqua, **snpp}) + month_rows(2020, 2, {**aqua, **snpp}))
    both = hz.harmonize_area(["A1"], paths=paths, phi=PHI1, kappa=K0)
    cut = hz.harmonize_area(["A1"], paths=paths, aqua_from={"D": (2020, 2), "N": (2020, 2)}, phi=PHI1, kappa=K0)
    assert [r["witnesses_used"] for r in both] == [["AQUA_MODIS", "SNPP_VIIRS"]] * 2
    assert cut[0]["witnesses_used"] == ["AQUA_MODIS", "SNPP_VIIRS"] and "AQUA_DRIFT_ERA" not in cut[0]["reason_codes"]
    assert cut[1]["witnesses_used"] == ["SNPP_VIIRS"] and {"AQUA_DRIFT_ERA", "SINGLE_WITNESS"} <= set(cut[1]["reason_codes"])
    assert cut[1]["raw_combined_cell_days"] == both[1]["raw_combined_cell_days"]              # the raw view keeps Aqua


def test_nrt_months_are_flagged_and_terra_never_enters_the_estimate(tmp_path):
    spec = {("A1", "AQUA_MODIS", "D"): 25, ("A1", "AQUA_MODIS", "N"): 5, ("A1", "TERRA_MODIS", "D"): 1000, ("A1", "TERRA_MODIS", "N"): 1000}
    paths = make(tmp_path, month_rows(2020, 1, spec, level="NRT"))
    (rec,) = hz.harmonize_area(["A1"], paths=paths, phi=PHI1, kappa=K0)
    assert rec["estimate"] == pytest.approx(30.0) and rec["witnesses_used"] == ["AQUA_MODIS"]
    assert rec["data_level"] == "NRT" and "PROVISIONAL_NRT" in rec["reason_codes"]
    assert json.loads(rec["raw_by_witness"]) == {"AQUA_MODIS": 30, "TERRA_MODIS": 2000} and rec["raw_combined_cell_days"] == 2030


def test_a_zero_count_keeps_a_variance_and_the_season_picks_the_ratio(tmp_path):
    zero = {("A1", "AQUA_MODIS", "D"): 0, ("A1", "AQUA_MODIS", "N"): 0, ("A1", "SNPP_VIIRS", "D"): 0, ("A1", "SNPP_VIIRS", "N"): 0}
    paths = make(tmp_path, month_rows(2020, 1, zero))
    (rec,) = hz.harmonize_area(["A1"], paths=paths, phi=PHI1, kappa=K0)
    assert rec["estimate"] == 0.0 and rec["sd"] > 0 and rec["ci90_low"] == 0.0 and rec["ci90_high"] > 0
    # a seasonal ratio: change the SON ratio of S1 only; a September month must use it, a January month must not
    cal = pq.read_table(paths.products / "calibration.parquet").to_pandas()
    cal.loc[(cal.stratum_id == S1) & (cal.season == "SON") & (cal.witness == "SNPP_VIIRS") & (cal.daynight == "D"), "ratio"] = 2.0
    pq.write_table(pa.Table.from_pandas(cal, preserve_index=False), paths.products / "calibration.parquet")
    snpp = {("A1", "SNPP_VIIRS", "D"): 10}
    paths = make(tmp_path, month_rows(2020, 1, snpp) + month_rows(2020, 9, snpp))
    cal.to_parquet(paths.products / "calibration.parquet")
    jan, sep = hz.harmonize_area(["A1"], paths=paths, phi=PHI1, kappa=K0)
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
    recs = hz.harmonize_area(["A1"], paths=paths, phi=PHI1, kappa=K0)
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


# ------------------------------------------------------------------------- shared ratio errors (Lead review, PR #43)
def test_strata_on_the_same_pooled_ratio_share_one_error_and_local_strata_do_not(tmp_path):
    # variance parts by hand (phi = 1). Counting: sum r^2 cd = 30 (D) + 0.55 (N). Ratio error per group = (sum cd x ratio_sd)^2.
    independent = 30.55 + (100 * 0.05) ** 2 + (80 * 0.02) ** 2 + (50 * 0.01) ** 2 + (20 * 0.005) ** 2           # 58.37: two LOCAL strata
    correlated = 30.55 + (100 * 0.05 + 80 * 0.02) ** 2 + (50 * 0.01 + 20 * 0.005) ** 2                          # 74.47: one REGION source
    rows = month_rows(2020, 1, SNPP)
    sd = {}
    for name, levels in (("local", {}), ("region", {S1: "REGION", S2: "REGION"}), ("mixed", {S1: "REGION"})):
        (tmp_path / name).mkdir()
        paths = make(tmp_path / name, rows, levels)
        (rec,) = hz.harmonize_area(["A1", "A2", "B1"], paths=paths, phi=PHI1, kappa=K0)
        sd[name] = rec["sd"]
    assert sd["local"] == pytest.approx(np.sqrt(independent)) and sd["mixed"] == pytest.approx(np.sqrt(independent))
    assert sd["region"] == pytest.approx(np.sqrt(correlated)) and sd["region"] > sd["local"]
    assert correlated == pytest.approx(74.47) and independent == pytest.approx(58.37)


def test_the_global_estimate_is_one_source_across_regions_but_regions_are_separate(tmp_path):
    rows = month_rows(2020, 1, {("A1", "SNPP_VIIRS", "D"): 100, ("C1", "SNPP_VIIRS", "D"): 60})       # S1 in NHAF, S3 in SHAF
    out = {}
    for name, level in (("global", "GLOBAL"), ("region", "REGION"), ("local", "LOCAL")):
        (tmp_path / name).mkdir()
        paths = make(tmp_path / name, rows, {S1: level, S3: level})
        (rec,) = hz.harmonize_area(["A1", "C1"], paths=paths, phi=PHI1, kappa=K0)
        out[name] = rec["sd"] ** 2
    counting = 0.25 * 100 + 0.25 * 60
    assert out["global"] == pytest.approx(counting + (100 * 0.05 + 60 * 0.05) ** 2)      # both on the global ratio: one group
    assert out["region"] == pytest.approx(counting + (100 * 0.05) ** 2 + (60 * 0.05) ** 2)   # two regions: two groups
    assert out["local"] == pytest.approx(out["region"])


# ------------------------------------------------------------------------------------------ overdispersion
def test_phi_scales_the_counting_variance_of_every_witness_including_a_single_one(tmp_path):
    aqua = {("A1", "AQUA_MODIS", "D"): 25, ("A1", "AQUA_MODIS", "N"): 5}
    paths = make(tmp_path, month_rows(2020, 1, aqua))
    phi = {"D": 4.0, "N": 2.0}
    (rec,) = hz.harmonize_area(["A1"], paths=paths, phi=phi, kappa=K0)
    assert rec["witnesses_used"] == ["AQUA_MODIS"] and rec["sd"] == pytest.approx(np.sqrt(4.0 * 25 + 2.0 * 5))     # ratio 1, no ratio error
    (plain,) = hz.harmonize_area(["A1"], paths=paths, phi=PHI1, kappa=K0)
    assert plain["sd"] == pytest.approx(np.sqrt(30.0)) and rec["sd"] > plain["sd"] and rec["estimate"] == plain["estimate"]


def test_the_default_phi_is_the_module_estimate(tmp_path, monkeypatch):
    paths = make(tmp_path, month_rows(2020, 1, {("A1", "AQUA_MODIS", "D"): 25, ("A1", "AQUA_MODIS", "N"): 5}))
    monkeypatch.setattr(hz, "PHI", {"D": 9.0, "N": 9.0})
    monkeypatch.setattr(hz, "KAPPA", K0)
    (rec,) = hz.harmonize_area(["A1"], paths=paths)
    assert rec["sd"] == pytest.approx(np.sqrt(9.0 * 30))


def test_solve_phi_recovers_a_planted_overdispersion_and_ignores_outliers():
    rng = np.random.default_rng(3)
    n = 4000
    vc, vr = rng.uniform(50, 500, n), rng.uniform(0, 100, n)
    for phi in (1.0, 3.0, 8.0):
        d = rng.normal(0.0, np.sqrt(phi * vc + vr))
        assert hz.solve_phi(d, vc, vr) == pytest.approx(phi, rel=0.12)
    d = rng.normal(0.0, np.sqrt(3.0 * vc + vr))
    d[:200] = 1e5                                                         # 5% of the units differ for other reasons
    assert hz.solve_phi(d, vc, vr) == pytest.approx(3.0, rel=0.25)
    assert np.isnan(hz.solve_phi(d[:5], vc[:5], vr[:5]))                   # too few units


def estimate_world(tmp: Path, phi_true: float, holdout_outlier: bool = False):
    """20 countries x 5 cells (one stratum each), Aqua and S-NPP counts negative binomial with variance phi x mean."""
    rng = np.random.default_rng(11)
    cells, rows, ratio = [], [], 0.5
    for c in range(20):
        for k in range(5):
            cells.append((f"c{c}k{k}", f"NHAF_b{c:03d}_{k:03d}", f"C{c:02d}"))

    def draw(mean):
        if phi_true == 1.0:
            return int(rng.poisson(mean))
        return int(rng.negative_binomial(mean / (phi_true - 1.0), 1.0 / phi_true))

    for y in range(2012, 2020):
        for m in range(1, 13):
            for cid, _, _ in cells:
                for w in ("AQUA_MODIS", "SNPP_VIIRS"):
                    mean = 60.0 if w == "AQUA_MODIS" else 60.0 / ratio
                    for dn in ("D", "N"):
                        n = draw(mean)
                        if holdout_outlier and w == "SNPP_VIIRS" and y >= 2017:
                            n += 5000
                        rows.append((cid, y, m, w, dn, n, n, 0.0, 28, 28, "SP"))
    pq.write_table(pa.table({"cell_id": [c[0] for c in cells], "stratum_id": [c[1] for c in cells], "country_iso3": [c[2] for c in cells]}),
                   tmp / "cells.parquet")
    cal = [(c[1], "SNPP_VIIRS", dn, season, ratio, 0.001, 12, "x", "LOCAL") for c in cells for dn in ("D", "N") for season in SEASONS]
    pq.write_table(pa.Table.from_pandas(pd.DataFrame(cal, columns=["stratum_id", "witness", "daynight", "season", "ratio", "ratio_sd",
                                                                   "n_overlap_months", "fit_period", "pooling_level"]), preserve_index=False),
                   tmp / "calibration.parquet")
    df = pd.DataFrame(rows, columns=["cell_id", "year", "month", "witness", "daynight", "detections", "cell_days", "frp_sum_mw",
                                     "days_available", "days_in_month", "data_level"])
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), tmp / "cell_month_witness.parquet")
    return hz.Paths(products=tmp, tmp=tmp / "dbtmp")


FIT_SNPP = {"SNPP_VIIRS": ((2012, 1), (2016, 12))}


def test_estimate_phi_recovers_the_planted_value_on_synthetic_country_months(tmp_path):
    for phi_true in (1.0, 4.0):
        (tmp_path / str(phi_true)).mkdir()
        paths = estimate_world(tmp_path / str(phi_true), phi_true)
        res = hz.estimate_phi(paths, fits=FIT_SNPP)
        assert res["pairs"]["SNPP_VIIRS"]["D"]["units"] > 1000
        assert res["phi_estimate"]["D"] == pytest.approx(phi_true, rel=0.2) and res["phi_estimate"]["N"] == pytest.approx(phi_true, rel=0.2)
        assert res["phi"]["D"] >= 1.0


def test_estimate_phi_never_reads_the_holdout_years(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    clean = hz.estimate_phi(estimate_world(tmp_path / "a", 4.0), fits=FIT_SNPP)
    spoiled = hz.estimate_phi(estimate_world(tmp_path / "b", 4.0, holdout_outlier=True), fits=FIT_SNPP)   # S-NPP + 5000 from 2017
    assert spoiled["phi_estimate"] == clean["phi_estimate"] and spoiled["pairs"] == clean["pairs"]


# ------------------------------------------------------------------------------------------ the disagreement code
def test_witness_disagreement_is_given_only_above_two_but_the_sd_is_inflated_above_one(tmp_path):
    aqua = {("A1", "AQUA_MODIS", "D"): 25}
    jan = {**aqua, ("A1", "SNPP_VIIRS", "D"): 70}       # E = 25 and 35: S about 1.35
    feb = {**aqua, ("A1", "SNPP_VIIRS", "D"): 100}      # E = 25 and 50: S about 2.9
    paths = make(tmp_path, month_rows(2020, 1, jan) + month_rows(2020, 2, feb))
    a, b = hz.harmonize_area(["A1"], paths=paths, phi=PHI1, kappa=K0)
    s_jan = np.sqrt(100.0 / (25.0 + (0.25 * 70 + (70 * 0.05) ** 2)))
    s_feb = np.sqrt(625.0 / (25.0 + (0.25 * 100 + (100 * 0.05) ** 2)))
    assert 1.0 < s_jan < 2.0 < s_feb
    assert a["disagreement_scale"] == pytest.approx(s_jan) and "WITNESS_DISAGREEMENT" not in a["reason_codes"]
    assert b["disagreement_scale"] == pytest.approx(s_feb) and "WITNESS_DISAGREEMENT" in b["reason_codes"]
    plain_sd = np.sqrt(1.0 / (1 / 25.0 + 1 / (0.25 * 70 + (70 * 0.05) ** 2)))
    assert a["sd"] == pytest.approx(plain_sd * s_jan)                      # inflated although the code is not given


# ------------------------------------------------------------------ size-dependent variance (Lead review, PR #43)
def test_kappa_adds_a_relative_error_to_the_estimate_of_every_witness(tmp_path):
    aqua = {("A1", "AQUA_MODIS", "D"): 25, ("A1", "AQUA_MODIS", "N"): 5}
    snpp = {("A1", "SNPP_VIIRS", "D"): 100}                                  # S1 is LOCAL: E = 50, counting 25, ratio error 25
    paths = make(tmp_path, month_rows(2020, 1, aqua) + month_rows(2020, 2, snpp))
    kappa = {"D": 0.1, "N": 0.2}
    jan, feb = hz.harmonize_area(["A1"], paths=paths, phi=PHI1, kappa=kappa)
    assert jan["sd"] == pytest.approx(np.sqrt(25 + 0.1 * 25 ** 2 + 5 + 0.2 * 5 ** 2))      # a single witness, ratio 1
    assert feb["sd"] == pytest.approx(np.sqrt(0.25 * 100 + (100 * 0.05) ** 2 + 0.1 * 50 ** 2))
    plain_jan, plain_feb = hz.harmonize_area(["A1"], paths=paths, phi=PHI1, kappa=K0)
    assert jan["sd"] > plain_jan["sd"] and feb["sd"] > plain_feb["sd"]
    assert jan["estimate"] == plain_jan["estimate"] and feb["estimate"] == plain_feb["estimate"]


def test_kappa_zero_gives_back_the_phi_only_model_and_the_default_is_the_module_value(tmp_path, monkeypatch):
    paths = make(tmp_path, month_rows(2020, 1, {("A1", "AQUA_MODIS", "D"): 25, ("A1", "AQUA_MODIS", "N"): 5}))
    phi = {"D": 4.0, "N": 2.0}
    (zero,) = hz.harmonize_area(["A1"], paths=paths, phi=phi, kappa=K0)
    assert zero["sd"] == pytest.approx(np.sqrt(4.0 * 25 + 2.0 * 5))                            # the phi-only variance
    monkeypatch.setattr(hz, "KAPPA", {"D": 0.5, "N": 0.5})
    (default,) = hz.harmonize_area(["A1"], paths=paths, phi=phi)
    assert default["sd"] == pytest.approx(np.sqrt(4.0 * 25 + 2.0 * 5 + 0.5 * 25 ** 2 + 0.5 * 5 ** 2))


def planted(rng, n, phi, kappa):
    size = np.exp(rng.uniform(np.log(5), np.log(3000), n))                   # country-months from 5 to 3,000 cell-days
    vc, vr = 2.0 * size, rng.uniform(0.0, 0.01, n) * size ** 2 * 0 + 1.0     # two witnesses of this size; a small ratio variance
    s2 = 2.0 * size ** 2
    d = rng.normal(0.0, np.sqrt(phi * vc + vr + kappa * s2))
    return d, vc, vr, s2, size


def assert_variance_close(phi_hat, kappa_hat, phi, kappa, tol=0.25):
    """phi and kappa are negatively correlated in a fit, so what must be right is the variance they give at each size."""
    for size in (10.0, 100.0, 1000.0):
        fitted, true = phi_hat * 2 * size + kappa_hat * 2 * size ** 2, phi * 2 * size + kappa * 2 * size ** 2
        assert fitted == pytest.approx(true, rel=tol), (size, fitted, true)


def test_solve_dispersion_recovers_planted_phi_and_kappa():
    rng = np.random.default_rng(5)
    for phi, kappa in ((3.0, 0.02), (6.0, 0.005), (2.0, 0.05)):
        phi_hat, kappa_hat = hz.solve_dispersion(*planted(rng, 6000, phi, kappa))
        assert phi_hat == pytest.approx(phi, rel=0.4) and kappa_hat == pytest.approx(kappa, rel=0.4), (phi, kappa, phi_hat, kappa_hat)
        assert_variance_close(phi_hat, kappa_hat, phi, kappa)


def test_solve_dispersion_gives_kappa_zero_when_there_is_no_size_effect():
    rng = np.random.default_rng(6)
    phi_hat, kappa_hat = hz.solve_dispersion(*planted(rng, 6000, 4.0, 0.0))
    assert kappa_hat < 0.003 and phi_hat == pytest.approx(4.0, rel=0.15)
    assert np.isnan(hz.solve_dispersion(*(a[:5] for a in planted(rng, 5, 4.0, 0.0)))[0])


def test_the_band_medians_are_near_the_chi_square_median_with_kappa_and_not_without_it():
    rng = np.random.default_rng(7)
    d, vc, vr, s2, size = planted(rng, 8000, 3.0, 0.03)
    phi, kappa = hz.solve_dispersion(d, vc, vr, s2, size)
    with_k = hz.band_medians(d, vc, vr, s2, size, phi, kappa)
    only_phi = hz.band_medians(d, vc, vr, s2, size, hz.solve_phi(d, vc, vr), 0.0)
    assert [b["from"] for b in with_k] == [5.0, 20.0, 100.0, 500.0] and with_k[-1]["to"] is None
    assert all(abs(b["median"] - hz.CHI2_1DF_MEDIAN) < 0.08 for b in with_k)                    # near 0.455 in every band
    assert only_phi[0]["median"] < 0.3 and only_phi[-1]["median"] > 0.8                          # phi alone: too wide small, too narrow large


def dispersion_world(tmp: Path, phi_true: float, kappa_true: float, holdout_outlier: bool = False):
    """20 countries of growing size x 5 cells; Aqua and S-NPP counts negative binomial (variance phi x mean) times a relative error."""
    rng = np.random.default_rng(21)
    cells, rows, ratio = [], [], 0.5
    for c in range(20):
        for k in range(5):
            cells.append((f"c{c}k{k}", f"NHAF_b{c:03d}_{k:03d}", f"C{c:02d}"))

    def draw(mean):
        return int(rng.poisson(mean)) if phi_true == 1.0 else int(rng.negative_binomial(mean / (phi_true - 1.0), 1.0 / phi_true))

    for y in range(2012, 2020):
        for m in range(1, 13):
            for c in range(20):
                for w in ("AQUA_MODIS", "SNPP_VIIRS"):
                    for dn in ("D", "N"):
                        factor = 1.0 + rng.normal(0.0, np.sqrt(kappa_true))
                        for k in range(5):
                            mean = 1.5 * 1.4 ** c * (1.0 if w == "AQUA_MODIS" else 1.0 / ratio)
                            n = max(0, round(draw(mean) * factor))
                            if holdout_outlier and w == "SNPP_VIIRS" and y >= 2017:
                                n += 5000
                            rows.append((f"c{c}k{k}", y, m, w, dn, n, n, 0.0, 28, 28, "SP"))
    pq.write_table(pa.table({"cell_id": [c[0] for c in cells], "stratum_id": [c[1] for c in cells], "country_iso3": [c[2] for c in cells]}),
                   tmp / "cells.parquet")
    cal = [(c[1], "SNPP_VIIRS", dn, season, ratio, 0.001, 12, "x", "LOCAL") for c in cells for dn in ("D", "N") for season in SEASONS]
    pq.write_table(pa.Table.from_pandas(pd.DataFrame(cal, columns=["stratum_id", "witness", "daynight", "season", "ratio", "ratio_sd",
                                                                   "n_overlap_months", "fit_period", "pooling_level"]), preserve_index=False),
                   tmp / "calibration.parquet")
    df = pd.DataFrame(rows, columns=["cell_id", "year", "month", "witness", "daynight", "detections", "cell_days", "frp_sum_mw",
                                     "days_available", "days_in_month", "data_level"])
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), tmp / "cell_month_witness.parquet")
    return hz.Paths(products=tmp, tmp=tmp / "dbtmp")


def test_estimate_dispersion_recovers_phi_and_kappa_on_synthetic_country_months(tmp_path):
    paths = dispersion_world(tmp_path, 3.0, 0.02)
    res = hz.estimate_dispersion(paths, fits=FIT_SNPP)
    for dn in ("D", "N"):
        assert res["phi"][dn] == pytest.approx(3.0, rel=0.5) and res["kappa"][dn] == pytest.approx(0.02, rel=0.5), (dn, res["phi"], res["kappa"])
        assert_variance_close(res["phi"][dn], res["kappa"][dn], 3.0, 0.02, tol=0.35)     # 1,200 units per day/night: the fit scatters by about 30%
        bands = res["bands_phi_kappa"][dn]
        assert all(abs(b["median"] - hz.CHI2_1DF_MEDIAN) < 0.2 for b in bands if b["units"] >= 30)       # about 150 to 400 units per band
    # the phi-only model, with the factor of the whole sample, misses the size bands
    only = res["bands_phi_only"]["D"]
    assert abs(only[-1]["median"] - hz.CHI2_1DF_MEDIAN) > abs(res["bands_phi_kappa"]["D"][-1]["median"] - hz.CHI2_1DF_MEDIAN)


def test_estimate_dispersion_gives_kappa_zero_without_a_size_effect_and_never_reads_the_holdout_years(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "c").mkdir()
    flat = hz.estimate_dispersion(dispersion_world(tmp_path / "a", 3.0, 0.0), fits=FIT_SNPP)
    assert flat["kappa"]["D"] < 0.006 and flat["phi"]["D"] == pytest.approx(3.0, rel=0.3)
    clean = hz.estimate_dispersion(dispersion_world(tmp_path / "b", 3.0, 0.02), fits=FIT_SNPP)
    spoiled = hz.estimate_dispersion(dispersion_world(tmp_path / "c", 3.0, 0.02, holdout_outlier=True), fits=FIT_SNPP)   # S-NPP + 5000 from 2017
    assert spoiled["phi"] == clean["phi"] and spoiled["kappa"] == clean["kappa"] and spoiled["bands_phi_kappa"] == clean["bands_phi_kappa"]


# ------------------------------------------------------------- the Aqua night cutoff (D-005, approved by the Lead 2026-11-14)
NO_CUT = {"D": None, "N": None}
AQUA_WORLD = {("A1", "AQUA_MODIS", "D"): 25, ("A1", "AQUA_MODIS", "N"): 5}
SNPP_WORLD = {("A1", "SNPP_VIIRS", "D"): 50, ("A1", "SNPP_VIIRS", "N"): 50}      # converted: D 25 (variance 18.75), N 5 (variance 0.75)


def test_the_default_cutoff_is_night_from_2024_05_and_day_has_none():
    assert hz.AQUA_FROM == {"D": None, "N": (2024, 5)}


def test_aqua_night_is_excluded_from_2024_05_and_aqua_day_stays_with_the_code(tmp_path):
    spec = {**AQUA_WORLD, **SNPP_WORLD}
    paths = make(tmp_path, month_rows(2024, 4, spec) + month_rows(2024, 5, spec))
    april, may = hz.harmonize_area(["A1"], paths=paths, phi=PHI1, kappa=K0)               # the module default cutoff
    # a month before 2024-05 is unchanged: the same record as with no cutoff at all
    assert april == hz.harmonize_area(["A1"], months=[(2024, 4)], paths=paths, aqua_from=NO_CUT, phi=PHI1, kappa=K0)[0]
    assert "AQUA_DRIFT_ERA" not in april["reason_codes"] and april["witnesses_used"] == ["AQUA_MODIS", "SNPP_VIIRS"]
    # May: day combines Aqua (25, variance 25) and S-NPP (25, variance 18.75); night is S-NPP alone (5, variance 0.75)
    assert "AQUA_DRIFT_ERA" in may["reason_codes"] and may["witnesses_used"] == ["AQUA_MODIS", "SNPP_VIIRS"]
    assert may["estimate"] == pytest.approx(30.0)
    assert may["sd"] == pytest.approx(np.sqrt(1.0 / (1 / 25.0 + 1 / 18.75) + 0.75))
    assert may["disagreement_scale"] == 1.0 and "SINGLE_WITNESS" not in may["reason_codes"]


def test_aqua_day_still_counts_in_the_day_part_after_the_cutoff(tmp_path):
    aqua = {("A1", "AQUA_MODIS", "D"): 25, ("A1", "AQUA_MODIS", "N"): 500}               # Aqua night would pull the total up: E = 500
    snpp = {("A1", "SNPP_VIIRS", "D"): 100, ("A1", "SNPP_VIIRS", "N"): 50}                # D: E = 50 (variance 25 + 25), N: E = 5
    paths = make(tmp_path, month_rows(2024, 6, {**aqua, **snpp}))
    (cut,) = hz.harmonize_area(["A1"], paths=paths, phi=PHI1, kappa=K0)
    v_aqua_d, v_snpp_d = 25.0, 0.25 * 100 + (100 * 0.05) ** 2
    day = (25 / v_aqua_d + 50 / v_snpp_d) / (1 / v_aqua_d + 1 / v_snpp_d)
    assert cut["estimate"] == pytest.approx(day + 5.0)                                     # night: S-NPP only, Aqua's 500 is not used
    (kept,) = hz.harmonize_area(["A1"], paths=paths, aqua_from=NO_CUT, phi=PHI1, kappa=K0)
    assert kept["estimate"] > cut["estimate"] + 50                                        # without the cutoff Aqua night would dominate
    # excluding day as well removes Aqua entirely, as the first T-013 version did after a cutoff
    (both,) = hz.harmonize_area(["A1"], paths=paths, aqua_from={"D": (2024, 5), "N": (2024, 5)}, phi=PHI1, kappa=K0)
    assert both["witnesses_used"] == ["SNPP_VIIRS"] and both["estimate"] == pytest.approx(55.0)


def test_a_night_part_with_no_other_witness_gives_no_estimate_after_the_cutoff(tmp_path):
    paths = make(tmp_path, month_rows(2024, 4, AQUA_WORLD) + month_rows(2024, 6, AQUA_WORLD))
    april, june = hz.harmonize_area(["A1"], paths=paths, phi=PHI1, kappa=K0)
    assert april["estimate"] == pytest.approx(30.0) and april["witnesses_used"] == ["AQUA_MODIS"]
    assert june["estimate"] is None and june["n_witnesses"] == 0 and june["witnesses_used"] == []
    assert june["verdict"] == "CANNOT_DETERMINE" and "AQUA_DRIFT_ERA" in june["reason_codes"]


def test_the_disagreement_is_pooled_over_day_and_night_after_the_cutoff(tmp_path):
    spec = {("A1", "AQUA_MODIS", "D"): 25, ("A1", "SNPP_VIIRS", "D"): 100, ("A1", "SNPP_VIIRS", "N"): 50, ("A1", "AQUA_MODIS", "N"): 5}
    paths = make(tmp_path, month_rows(2024, 7, spec))
    (rec,) = hz.harmonize_area(["A1"], paths=paths, phi=PHI1, kappa=K0)
    v_a, v_s = 25.0, 0.25 * 100 + (100 * 0.05) ** 2                                           # day: E = 25 and 50
    chi2 = (25 - 50) ** 2 / (v_a + v_s)                                                       # one degree of freedom; night has one witness
    assert rec["disagreement_scale"] == pytest.approx(max(np.sqrt(chi2), 1.0))
    assert ("WITNESS_DISAGREEMENT" in rec["reason_codes"]) == (np.sqrt(chi2) > 2.0)
    assert set(rec) == set(cc.SPEC["entity_month"])
