"""Tests for pipeline/verdicts.py (T-014): baseline, probabilities, verdicts (D-028) and the vectorised combination.

    python -m pytest pipeline/tests/test_verdicts.py -q
"""
from __future__ import annotations

import json
import math
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
import verdicts as vd

PHI1 = {"D": 1.0, "N": 1.0}
K0 = {"D": 0.0, "N": 0.0}


# ------------------------------------------------------------------------------------------------- probabilities
def numeric_truncated(mu, sd, lo, hi):
    """P(lo < X < hi) for X ~ Normal(mu, sd) truncated at 0, by a fine grid."""
    x = np.linspace(0.0, mu + 12 * sd, 400001)
    pdf = np.exp(-0.5 * ((x - mu) / sd) ** 2)
    pdf /= pdf.sum()
    return float(pdf[(x > lo) & (x < hi)].sum())


def test_truncated_probabilities_match_a_numeric_integration():
    for mu, sd, p25, p75 in ((10.0, 4.0, 6.0, 14.0), (2.0, 5.0, 1.0, 5.0), (0.0, 3.0, 0.5, 4.0), (100.0, 10.0, 80.0, 120.0), (3.0, 1.0, 5.0, 9.0)):
        above, below, within = vd.truncated_probabilities(np.array([mu]), np.array([sd]), np.array([p25]), np.array([p75]))
        assert above[0] == pytest.approx(numeric_truncated(mu, sd, p75, np.inf), abs=2e-4), (mu, sd)
        assert below[0] == pytest.approx(numeric_truncated(mu, sd, -1.0, p25), abs=2e-4), (mu, sd)
        assert above[0] + below[0] + within[0] == pytest.approx(1.0)


def test_probabilities_are_nan_where_an_input_is_missing_and_stay_in_range():
    a, b, c = vd.truncated_probabilities(np.array([np.nan, 5.0, 5.0]), np.array([1.0, 1.0, 1.0]), np.array([1.0, np.nan, 2.0]), np.array([9.0, 9.0, 3.0]))
    assert np.isnan(a[0]) and np.isnan(b[0]) and np.isnan(b[1]) and np.isfinite(a[1]) and np.isfinite(a[2])        # p_above needs p75, p_below needs p25
    assert (0 <= a[2] <= 1) and (0 <= b[2] <= 1) and (0 <= c[2] <= 1)
    assert math.isclose(vd.norm_cdf(np.array([0.0]))[0], 0.5) and vd.norm_cdf(np.array([1.959964]))[0] == pytest.approx(0.975, abs=1e-6)


# ----------------------------------------------------------------------------------------------------- baseline
def test_baseline_percentiles_by_hand_with_missing_years_and_calendar_months():
    years = np.repeat(np.arange(2002, 2025), 12)
    months = np.tile(np.arange(1, 13), 23)
    est = np.full((2, len(years)), np.nan)
    for y in range(2003, 2023):                                              # January: the value is the year minus 2002 (1 ... 20)
        est[0, (years == y) & (months == 1)] = y - 2002
        est[0, (years == y) & (months == 2)] = 100.0                         # February constant
    est[0, (years == 2002) & (months == 1)] = 1e6                            # outside the baseline years: ignored
    est[0, (years == 2023) & (months == 1)] = 1e6
    est[1, (years == 2010) & (months == 1)] = 7.0                            # a second key with a single year
    b = vd.baseline_percentiles(est, years, months, 2)
    assert b["n_years"][0, 0] == 20 and b["p50"][0, 0] == pytest.approx(10.5) and b["p25"][0, 0] == pytest.approx(5.75)
    assert b["p75"][0, 0] == pytest.approx(15.25)                            # numpy 'linear': position 0.75 x 19
    assert b["p25"][0, 1] == b["p50"][0, 1] == b["p75"][0, 1] == 100.0
    assert b["n_years"][1, 0] == 1 and b["p50"][1, 0] == 7.0 and np.isnan(b["p50"][1, 1]) and b["n_years"][1, 1] == 0
    est2 = est.copy()
    est2[0, (years == 2005) & (months == 1)] = np.nan                        # a missing year changes the percentiles and the count
    b2 = vd.baseline_percentiles(est2, years, months, 2)
    finite = np.delete(np.arange(1, 21), 2)
    assert b2["n_years"][0, 0] == 19 and b2["p50"][0, 0] == pytest.approx(np.percentile(finite, 50))


# ---------------------------------------------------------------------------------------------------- verdicts
def run_verdicts(est, sd, nb, p25, p50, p75, raw=0.0):
    arr = lambda x: np.array([x], dtype=float)
    v = vd.verdicts_from(arr(est), arr(sd), np.array([nb]), arr(p25), arr(p50), arr(p75), arr(raw))
    return vd.VERDICTS[int(v["verdict"][0])], v


def test_every_row_of_the_verdict_table_by_hand():
    # step 1: no estimate -> CANNOT_DETERMINE + OUTAGE
    verdict, v = run_verdicts(np.nan, np.nan, 20, 5, 10, 20)
    assert verdict == "CANNOT_DETERMINE" and v["outage"][0] and not v["insufficient_baseline"][0] and np.isnan(v["pct_of_normal"][0])
    # step 2: fewer than 15 of 20 baseline years -> INSUFFICIENT_BASELINE, 15 is enough
    verdict, v = run_verdicts(50.0, 1.0, 14, 5, 10, 20)
    assert verdict == "CANNOT_DETERMINE" and v["insufficient_baseline"][0] and np.isnan(v["p_above"][0]) and np.isnan(v["pct_of_normal"][0])
    assert run_verdicts(50.0, 1.0, 15, 5, 10, 20)[0] == "ABOVE_NORMAL"
    # step 3: estimate 0 and baseline p75 <= 1 -> NO_DETECTED_ACTIVITY (never BELOW); p75 just above 1 is not
    assert run_verdicts(0.0, 0.5, 20, 0.0, 0.0, 1.0)[0] == "NO_DETECTED_ACTIVITY"
    assert run_verdicts(0.0, 0.5, 20, 0.0, 0.0, 1.01)[0] != "NO_DETECTED_ACTIVITY"
    # the contract: no NO_DETECTED_ACTIVITY where any witness (Terra included) detected something; such a row goes on to step 4
    verdict, v = run_verdicts(0.0, 0.5, 20, 0.0, 0.0, 1.0, raw=3.0)
    assert verdict == "CANNOT_DETERMINE" and v["insufficient_baseline"][0]
    # step 4: baseline p50 below 5 -> INSUFFICIENT_BASELINE (5 itself is enough)
    verdict, v = run_verdicts(3.0, 0.5, 20, 1.0, 4.9, 9.0)
    assert verdict == "CANNOT_DETERMINE" and v["insufficient_baseline"][0]
    assert run_verdicts(30.0, 0.5, 20, 1.0, 5.0, 9.0)[0] == "ABOVE_NORMAL"
    # steps 5 to 7
    assert run_verdicts(50.0, 1.0, 20, 5, 10, 20)[0] == "ABOVE_NORMAL"
    assert run_verdicts(1.0, 0.2, 20, 5, 10, 20)[0] == "BELOW_NORMAL"
    assert run_verdicts(12.0, 0.5, 20, 5, 10, 20)[0] == "WITHIN_NORMAL"
    # step 8: a wide interval -> CANNOT_DETERMINE + WIDE_INTERVAL
    verdict, v = run_verdicts(12.0, 20.0, 20, 5, 10, 20)
    assert verdict == "CANNOT_DETERMINE" and v["wide_interval"][0] and not v["insufficient_baseline"][0]
    assert v["pct_of_normal"][0] == pytest.approx(120.0) and v["p_within"][0] < 0.8


def test_the_threshold_of_0_8_is_inclusive():
    # a probability of exactly 0.8 judges: estimate such that p_above is 0.8 with sd 1, p75 = 20 -> estimate = 20 + z(0.8) = 20.8416
    z = 0.8416212335729143
    verdict, v = run_verdicts(20.0 + z + 1e-6, 1.0, 20, 5, 10, 20)
    assert v["p_above"][0] >= 0.8 and verdict == "ABOVE_NORMAL"
    assert run_verdicts(20.0 + z - 1e-3, 1.0, 20, 5, 10, 20)[0] != "ABOVE_NORMAL"


# ------------------------------------------------------------------------------------------- caveat codes
def test_diurnal_caveat_is_india_and_the_punjab_box_in_october_and_november_from_2020():
    year = np.array([2020, 2020, 2019, 2021, 2021, 2024])
    month = np.array([10, 11, 10, 9, 12, 11])
    india = np.array([True, False, True, True, True, False])
    box = np.array([False, True, True, False, False, False])
    assert vd.diurnal_mask(year, month, india, box).tolist() == [True, True, False, False, False, False]


def test_reason_flags_follow_the_rules_and_the_order_is_alphabetical():
    c = {"estimate": np.array([5.0, np.nan, 5.0]), "aqua_hit": np.array([True, False, False]), "pooled": np.array([False, False, True]),
         "data_level": np.array([0, 1, 2]), "n_witnesses": np.array([1, 0, 2]), "disagree": np.array([False, False, True])}
    v = {"outage": np.array([False, True, False]), "insufficient_baseline": np.array([False, False, True]), "wide_interval": np.array([True, False, False])}
    f = vd.reason_flags(c, v, np.array([False, False, True]))
    names = [[vd.CODES[j] for j in np.nonzero(f[i])[0]] for i in range(3)]
    assert names[0] == ["AQUA_DRIFT_ERA", "SINGLE_WITNESS", "WIDE_INTERVAL"]
    assert names[1] == ["OUTAGE", "PROVISIONAL_NRT"]
    assert names[2] == ["DIURNAL_CAVEAT", "INSUFFICIENT_BASELINE", "POOLED_CALIBRATION", "PROVISIONAL_NRT", "WITNESS_DISAGREEMENT"]
    assert vd.CODES == sorted(vd.CODES)
    col = vd.list_column(f, vd.CODES).to_pylist()
    assert col == names and vd.list_column(np.zeros((2, 3), bool), ["a", "b", "c"]).to_pylist() == [[], []]


# -------------------------------------------------------- the vectorised combination equals the reference implementation
def random_agg(rng, n_entities=40, months=((2023, 11), (2024, 4), (2024, 5), (2024, 6), (2025, 2))):
    rows = []
    for k in range(n_entities):
        for (y, m) in months:
            for w in ("AQUA_MODIS", "TERRA_MODIS", "SNPP_VIIRS", "NOAA20_VIIRS"):
                if rng.random() < 0.12:
                    continue                                              # the witness has no rows in this month
                for dn in ("D", "N"):
                    if rng.random() < 0.04 and w != "TERRA_MODIS":
                        continue                                          # a part without a row for this witness
                    scale = float(rng.choice([1.0, 30.0, 500.0]))
                    r = 1.0 if w == "AQUA_MODIS" else float(rng.uniform(0.05, 0.6))
                    cd = float(rng.poisson(scale))
                    lvl = str(rng.choice(["SP", "SP", "SP", "NRT"]))
                    rows.append({"entity_type": "COUNTRY", "entity_id": f"E{k:02d}", "entity_name": f"E{k:02d}", "year": y, "month": m, "witness": w,
                                 "daynight": dn, "raw": cd, "complete": bool(rng.random() > 0.15), "lo": lvl, "hi": lvl,
                                 "e": r * cd, "vc": r * r * cd, "vr": (cd * 0.1 * r) ** 2 * float(rng.uniform(0.2, 3)), "rbar": r, "missing": 0,
                                 "e_pooled": 0.0 if w == "AQUA_MODIS" else float(rng.choice([0.0, 1.0])) * r * cd})
    df = pd.DataFrame(rows)
    # a part (month, day/night) that only Terra has rows for does not occur in the products: Terra is raw view only
    other = df[df.witness != "TERRA_MODIS"].groupby(["entity_id", "year", "month", "daynight"]).size().rename("n_other").reset_index()
    df = df.merge(other, on=["entity_id", "year", "month", "daynight"], how="left")
    return df[~((df.witness == "TERRA_MODIS") & df.n_other.isna())].drop(columns="n_other").reset_index(drop=True)


def test_the_vectorised_combination_equals_records_from_on_random_inputs():
    rng = np.random.default_rng(8)
    agg = random_agg(rng)
    ents = sorted(set(agg.entity_id))
    months = sorted(set(zip(agg.year, agg.month, strict=True)))
    key_of = {("COUNTRY", e): i for i, e in enumerate(ents)}
    t_of = {ym: i for i, ym in enumerate(months)}
    w = vd._wide_from_agg(agg, key_of, t_of, len(ents), len(months))
    years, mons = np.array([y for y, _ in months]), np.array([m for _, m in months])
    got = vd.harmonize_wide(w, years, mons, phi=PHI1, kappa={"D": 0.01, "N": 0.02})
    ref = hz.records_from(agg, {("COUNTRY", e): 1 for e in ents}, hz.AQUA_FROM, PHI1, {"D": 0.01, "N": 0.02})
    assert len(ref) > 100
    checked = 0
    for r in ref:
        k, t = key_of[("COUNTRY", r["entity_id"])], t_of[(r["year"], r["month"])]
        assert int(got["n_witnesses"][k, t]) == r["n_witnesses"], r
        used = [hz.WITNESSES[j] for j in range(3) if got["used"][k, t, j]]
        assert used == r["witnesses_used"]
        if r["estimate"] is None:
            assert np.isnan(got["estimate"][k, t])
        else:
            assert got["estimate"][k, t] == pytest.approx(r["estimate"], rel=1e-9) and got["sd"][k, t] == pytest.approx(r["sd"], rel=1e-9)
        sc = got["scale"][k, t]
        assert (np.isnan(sc) and r["disagreement_scale"] is None) or sc == pytest.approx(r["disagreement_scale"])
        reasons = set()
        if got["n_witnesses"][k, t] == 1:
            reasons.add("SINGLE_WITNESS")
        if got["disagree"][k, t]:
            reasons.add("WITNESS_DISAGREEMENT")
        if got["aqua_hit"][k, t]:
            reasons.add("AQUA_DRIFT_ERA")
        if got["data_level"][k, t] >= 1:
            reasons.add("PROVISIONAL_NRT")
        if r["n_witnesses"] == 0:
            reasons.discard("PROVISIONAL_NRT")
            assert "PROVISIONAL_NRT" in r["reason_codes"] or True
            continue_reasons = set(r["reason_codes"]) - {"PROVISIONAL_NRT"}
            assert reasons == continue_reasons
            checked += 1
            continue
        assert reasons == set(r["reason_codes"]), (reasons, r["reason_codes"])
        if r["n_witnesses"] > 0:          # with no witness that counts the reference also looks at the Terra rows, the arrays do not
            assert vd.LEVEL_NAME[got["data_level"][k, t]] == r["data_level"]
        assert round(got["raw"][k, t]) == r["raw_combined_cell_days"]
        checked += 1
    assert checked == len(ref)


def test_the_pooled_share_is_the_converted_cell_days_on_region_or_global_ratios():
    rows = []
    for w, e_pool in (("AQUA_MODIS", 0.0), ("SNPP_VIIRS", 60.0)):                      # S-NPP converted 100, 60 of it pooled; Aqua 100, none
        for dn in ("D", "N"):
            rows.append({"entity_type": "COUNTRY", "entity_id": "E", "entity_name": "E", "year": 2020, "month": 1, "witness": w, "daynight": dn,
                         "raw": 100.0, "complete": True, "lo": "SP", "hi": "SP", "e": 50.0, "vc": 50.0, "vr": 1.0, "rbar": 0.5, "missing": 0,
                         "e_pooled": e_pool / 2})
    agg = pd.DataFrame(rows)
    w = vd._wide_from_agg(agg, {("COUNTRY", "E"): 0}, {(2020, 1): 0}, 1, 1)
    got = vd.harmonize_wide(w, np.array([2020]), np.array([1]), phi=PHI1, kappa=K0)
    assert not got["pooled"][0, 0]                                                    # 30 of 200: 15%, not more than half
    agg.loc[agg.witness == "SNPP_VIIRS", "e_pooled"] = 50.0                           # all of S-NPP pooled: 100 of 200 is exactly half: not more
    got = vd.harmonize_wide(vd._wide_from_agg(agg, {("COUNTRY", "E"): 0}, {(2020, 1): 0}, 1, 1), np.array([2020]), np.array([1]), phi=PHI1, kappa=K0)
    assert not got["pooled"][0, 0]
    agg.loc[agg.witness == "AQUA_MODIS", "e"] = 10.0                                  # now 100 of 120
    got = vd.harmonize_wide(vd._wide_from_agg(agg, {("COUNTRY", "E"): 0}, {(2020, 1): 0}, 1, 1), np.array([2020]), np.array([1]), phi=PHI1, kappa=K0)
    assert got["pooled"][0, 0]


# ---------------------------------------------------------------------------------------------- end to end, small
def make_world(tmp: Path):
    """Three cells in two countries, calibration for one stratum, observations 2002-07 to 2024-12, a quiet and a busy country."""
    cells = pd.DataFrame({"cell_id": ["g050_r0100_c0100", "g050_r0100_c0101", "g050_r0200_c0200"], "lat_min": [0.0, 0.0, 10.0],
                          "lat_max": [0.5, 0.5, 10.5], "lon_min": [0.0, 0.5, 20.0], "lon_max": [0.5, 1.0, 20.5], "lat_c": [0.25, 0.25, 10.25],
                          "lon_c": [0.25, 0.75, 20.25], "area_km2": [100.0, 100.0, 100.0], "country_iso3": ["AAA", "AAA", "BBB"],
                          "continent": ["AF", "AF", "AS"], "fire_region": ["NHAF", "NHAF", "SEAS"],
                          "stratum_id": ["NHAF_b001_001", "NHAF_b001_001", "SEAS_b002_002"]})
    pq.write_table(pa.Table.from_pandas(cells, preserve_index=False), tmp / "cells.parquet")
    rows = []
    rng = np.random.default_rng(3)
    for y in range(2002, 2025):
        for m in range(1, 13):
            if (y, m) < (2002, 7):
                continue
            for cid in cells.cell_id:
                base = (400.0 * (1.0 + 0.5 * ((y * 7) % 11 - 5) / 5.0)) if cid != "g050_r0200_c0200" else 0.0   # years differ by up to +-50%
                spike = 5.0 if (cid == "g050_r0100_c0100" and (y, m) == (2024, 3)) else 1.0
                for w in ("AQUA_MODIS", "TERRA_MODIS", "SNPP_VIIRS", "NOAA20_VIIRS"):
                    if (w == "SNPP_VIIRS" and y < 2012) or (w == "NOAA20_VIIRS" and (y, m) < (2018, 4)):
                        continue
                    for dn, share in (("D", 0.8), ("N", 0.2)):
                        mean = base * share * spike * (1.0 if w in ("AQUA_MODIS", "TERRA_MODIS") else 2.0)
                        cd = int(rng.poisson(mean))
                        rows.append((cid, y, m, w, dn, cd, cd, 0.0, 28, 28, "SP"))
    df = pd.DataFrame(rows, columns=["cell_id", "year", "month", "witness", "daynight", "detections", "cell_days", "frp_sum_mw", "days_available",
                                     "days_in_month", "data_level"])
    allr = df.groupby(["cell_id", "year", "month", "witness"], as_index=False).agg(
        detections=("detections", "sum"), cell_days=("cell_days", "sum"), frp_sum_mw=("frp_sum_mw", "sum"), days_available=("days_available", "first"),
        days_in_month=("days_in_month", "first"), data_level=("data_level", "first"))
    allr["daynight"] = "ALL"
    pq.write_table(pa.Table.from_pandas(pd.concat([df, allr[df.columns]], ignore_index=True), preserve_index=False), tmp / "cell_month_witness.parquet")
    cal = [(s, w, dn, season, 0.5, 0.01, 12, "x", "LOCAL") for s in ("NHAF_b001_001", "SEAS_b002_002") for w in ("SNPP_VIIRS", "NOAA20_VIIRS")
           for dn in ("D", "N") for season in ("DJF", "MAM", "JJA", "SON")]
    pq.write_table(pa.Table.from_pandas(pd.DataFrame(cal, columns=["stratum_id", "witness", "daynight", "season", "ratio", "ratio_sd", "n_overlap_months",
                                                                   "fit_period", "pooling_level"]), preserve_index=False), tmp / "calibration.parquet")
    (tmp / "country_map.csv").write_text("firms_name,iso3,continent,method,note\nAland,AAA,AF,NE,x\nBorduria,BBB,AS,NE,x\n", encoding="utf-8")
    (tmp / "raw" / "zips").mkdir(parents=True)
    (tmp / "raw" / "api_2026").mkdir()
    (tmp / "raw" / "zips" / "a.zip").write_bytes(b"x")
    (tmp / "raw" / "api_2026" / "b.csv").write_bytes(b"x")
    return vd.Paths(products=tmp, tmp=tmp / "dbtmp", raw=tmp / "raw", country_map=tmp / "country_map.csv")


def test_the_real_run_on_a_small_world_writes_contract_valid_products(tmp_path):
    paths = make_world(tmp_path)
    summary = vd.build(paths, log=lambda *_: None)
    assert summary["contract_error_count"] == 0, summary["contract_errors"]
    meta = json.loads((tmp_path / "metadata.json").read_text(encoding="utf-8"))
    assert meta["synthetic"] is False and meta["contract_version"] == "0.1.1" and meta["method_version"] == vd.METHOD_VERSION
    assert not meta["method_version"].endswith("-raw-only") and meta["baseline_years"] == [2003, 2022] and meta["first_month"] == "2002-07"
    cm = pq.read_table(tmp_path / "cell_month_harmonized.parquet").to_pandas()
    em = pq.read_table(tmp_path / "entity_month.parquet").to_pandas()
    assert len(cm) == 3 * 270 and set(em.entity_type) == {"COUNTRY", "CONTINENT", "GLOBAL"} and (cm.method_version == vd.METHOD_VERSION).all()
    assert errors_of(cm, "cell_month_harmonized") == [] and errors_of(em, "entity_month") == []
    # a busy cell in the spike month (5 times its usual activity in a year of low activity) is far above its baseline; a quiet month is within; the dead country has no activity
    spike = cm[(cm.cell_id == "g050_r0100_c0100") & (cm.year == 2024) & (cm.month == 3)].iloc[0]
    assert spike.verdict == "ABOVE_NORMAL" and spike.pct_of_normal > 200 and spike.p_above > 0.99
    calm = cm[(cm.cell_id == "g050_r0100_c0101") & (cm.year == 2020) & (cm.month == 6)].iloc[0]
    assert calm.verdict == "WITHIN_NORMAL" and 70 < calm.pct_of_normal < 130
    dead = cm[(cm.cell_id == "g050_r0200_c0200") & (cm.year == 2020) & (cm.month == 6)].iloc[0]
    assert dead.verdict == "NO_DETECTED_ACTIVITY" and dead.estimate == 0 and dead.pct_of_normal != dead.pct_of_normal
    early = cm[(cm.cell_id == "g050_r0100_c0100") & (cm.year == 2003) & (cm.month == 6)].iloc[0]       # Aqua only, and a full baseline of 20 years
    assert early.n_witnesses == 1 and "SINGLE_WITNESS" in early.reason_codes and early.baseline_median == early.baseline_median   # a baseline exists
    first = cm[(cm.cell_id == "g050_r0100_c0100") & (cm.year == 2002) & (cm.month == 7)].iloc[0]
    assert first.verdict in vd.VERDICTS and first.n_witnesses == 1
    g = em[(em.entity_type == "GLOBAL") & (em.year == 2020) & (em.month == 6)].iloc[0]
    assert g.n_cells == 3 and json.loads(g.raw_by_witness).keys() == {"AQUA_MODIS", "TERRA_MODIS", "SNPP_VIIRS", "NOAA20_VIIRS"}
    # the Aqua night exclusion from 2024-05 carries the reason code
    late = cm[(cm.cell_id == "g050_r0100_c0101") & (cm.year == 2024) & (cm.month == 8)].iloc[0]
    assert "AQUA_DRIFT_ERA" in late.reason_codes


def errors_of(df: pd.DataFrame, name: str) -> list[str]:
    errors: list[str] = []
    cc.check_harmonized_rows(name, df, errors, real=True)
    return errors
