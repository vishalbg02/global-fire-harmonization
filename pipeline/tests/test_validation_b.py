"""Tests for pipeline/validation_b.py on SYNTHETIC data with answers known by hand (T-021, tests B1 and B3).

    python -m pytest pipeline/tests/test_validation_b.py -q -p no:cacheprovider
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import aqua_drift as ad
import harmonize as hz
import validation_b as vb

D2012 = (2012, 1)


# ------------------------------------------------------------------------------------------------------------ builders
def months(first: tuple[int, int], last: tuple[int, int]) -> list[tuple[int, int]]:
    out, (y, m) = [], first
    while (y, m) <= last:
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def frame(entity="R1", etype="REGION", first=(2011, 1), last=(2012, 12), aqua=100.0, step_at=None, step=1.0, raw_step=3.0,
          est_missing=(), no_aqua=(), extra=None) -> pd.DataFrame:
    """An entity_month-shaped frame: Aqua constant at `aqua` cell-days, the harmonized estimate = Aqua x `step` from `step_at` on,
    the raw combined series = 1.4 x Aqua (Terra) before and 1.4 x Aqua x `raw_step` from `step_at` on."""
    rows = []
    for y, m in months(first, last):
        after = step_at is not None and (y, m) >= step_at
        est = aqua * (step if after else 1.0)
        raw = aqua * 1.4 * (raw_step if after else 1.0)
        used = [] if (y, m) in est_missing else ([] if (y, m) in no_aqua else ["AQUA_MODIS"]) + (["SNPP_VIIRS"] if after else [])
        rows.append({"entity_type": etype, "entity_id": entity, "entity_name": entity, "year": y, "month": m,
                     "estimate": None if (y, m) in est_missing else est, "sd": 5.0, "raw_combined_cell_days": int(raw),
                     "raw_by_witness": json.dumps({"AQUA_MODIS": aqua, "TERRA_MODIS": aqua * 0.4}), "witnesses_used": used,
                     "verdict": "CANNOT_DETERMINE", "reason_codes": [], "baseline_median": None, "pct_of_normal": None})
    f = pd.DataFrame(rows)
    return f if extra is None else pd.concat([f, extra], ignore_index=True)


def many(steps: list[float], raw_step=3.0, date=D2012) -> pd.DataFrame:
    """One region per harmonized step."""
    return pd.concat([frame(entity=f"R{i}", step_at=date, step=s, raw_step=raw_step) for i, s in enumerate(steps)], ignore_index=True)


# ------------------------------------------------------------------------------------------------------ B1: the statistic
def test_flat_series_has_step_one_and_a_planted_step_is_found_exactly():
    flat = vb.prepare(frame(step_at=D2012, step=1.0))
    assert vb.step_ratio(flat, D2012)["step"] == 1.0
    planted = vb.prepare(frame(step_at=D2012, step=1.30))
    r = vb.step_ratio(planted, D2012)
    assert abs(r["step"] - 1.30) < 1e-12 and r["n_before"] == 12 and r["n_after"] == 12 and r["sufficient"]


def test_the_ratio_is_to_the_aqua_only_series_not_to_the_level():
    # twice the activity everywhere (aqua and estimate both double after the date): no step in series / Aqua-only
    f = frame(step_at=D2012, step=1.0)
    g = vb.prepare(f)
    g.loc[g.idx >= vb.month_idx(2012, 1), ["estimate", "aqua"]] *= 2.0
    assert abs(vb.step_ratio(g, D2012)["step"] - 1.0) < 1e-12


def test_window_is_the_12_months_from_the_date_and_the_12_before():
    base = vb.prepare(frame(step_at=D2012, step=1.0, first=(2010, 6), last=(2013, 6)))
    ref = vb.step_ratio(base, D2012)["step"]
    assert ref == 1.0
    for ym, moves in [((2010, 12), False), ((2013, 1), False),            # month d-13 and d+12: outside both windows
                      ((2011, 1), True), ((2011, 12), True), ((2012, 1), True), ((2012, 12), True)]:   # first/last month of each window
        g = base.copy()
        g.loc[(g.year == ym[0]) & (g.month == ym[1]), "estimate"] *= 5.0
        assert (abs(vb.step_ratio(g, D2012)["step"] - ref) > 1e-9) == moves, ym


def test_months_without_an_estimate_or_without_aqua_are_not_used_and_too_few_months_are_insufficient():
    f = frame(step_at=D2012, step=1.0, est_missing=[(2012, 3)], no_aqua=[(2011, 5)])
    r = vb.step_ratio(vb.prepare(f), D2012)
    assert r["n_after"] == 11 and r["n_before"] == 11 and r["sufficient"]
    few = frame(step_at=D2012, step=1.0, est_missing=[(2012, 3), (2012, 4), (2012, 5)])        # 9 usable months after
    assert not vb.step_ratio(vb.prepare(few), D2012)["sufficient"]


def test_a_region_with_too_little_aqua_activity_is_insufficient():
    assert vb.step_ratio(vb.prepare(frame(aqua=4.0, step_at=D2012)), D2012)["sufficient"] is False        # 48 < 60 per window
    assert vb.step_ratio(vb.prepare(frame(aqua=5.0, step_at=D2012)), D2012)["sufficient"] is True         # 60 per window


def test_a_series_with_no_aqua_in_the_window_has_no_step():
    r = vb.step_ratio(vb.prepare(frame(aqua=0.0, step_at=D2012)), D2012)
    assert np.isnan(r["step"]) and not r["sufficient"]


# ---------------------------------------------------------------------------------------------------------- B1: the status
def status_of(steps, raw_step=3.0):
    rows = vb.evaluate_b1(many(steps, raw_step), dates=[D2012])
    return vb.b1_status(rows)


def test_status_pass_at_exactly_80_percent_and_fail_below():
    assert status_of([1.0, 1.02, 0.97, 1.05, 1.5])["status"] == "PASS"            # 4 of 5 within +-10%
    s = status_of([1.0, 1.02, 0.97, 1.5, 0.6])
    assert s["status"] == "FAIL" and s["regions_within_tolerance"] == 3 and abs(s["fraction_within"] - 0.6) < 1e-12


def test_tolerance_is_inclusive_at_plus_minus_10_percent_and_exclusive_beyond():
    edge = status_of([1.10, 0.90, 1.10, 0.90] + [1.0] * 6)             # four regions exactly on the boundary: all within (10 of 10)
    assert edge["status"] == "PASS" and edge["regions_within_tolerance"] == 10
    s = status_of([1.1001, 0.8999, 1.0, 1.0, 1.0])
    assert s["regions_within_tolerance"] == 3 and s["status"] == "FAIL"


def test_inconclusive_when_the_raw_step_is_not_clearly_present_or_regions_are_too_few():
    s = status_of([1.0] * 6, raw_step=1.05)                    # raw step 5%: not present
    assert s["status"] == "INCONCLUSIVE" and "raw step" in s["why"]
    assert status_of([1.0] * 4)["status"] == "INCONCLUSIVE"     # 4 regions only
    mixed = pd.concat([many([1.0] * 3, raw_step=3.0), many([1.0] * 3, raw_step=1.0).assign(entity_id=lambda d: "X" + d.entity_id)], ignore_index=True)
    assert vb.b1_status(vb.evaluate_b1(mixed, dates=[D2012]))["raw_outside_fraction"] == 0.5
    assert vb.b1_status(vb.evaluate_b1(mixed, dates=[D2012]))["status"] == "PASS"          # exactly half is "present"


def test_regions_without_sufficient_data_are_left_out_of_the_fraction():
    good = many([1.0] * 5)
    poor = frame(entity="P", step_at=D2012, step=2.0, est_missing=months((2012, 1), (2012, 6)))     # 6 usable months after: insufficient
    s = vb.b1_status(vb.evaluate_b1(pd.concat([good, poor], ignore_index=True), dates=[D2012]))
    assert s["regions_total"] == 6 and s["regions_sufficient"] == 5 and s["status"] == "PASS"


def test_evaluate_b1_keeps_only_fire_regions_and_skips_unassigned():
    f = pd.concat([many([1.0, 1.0]), frame(entity="UNASSIGNED", step_at=D2012), frame(entity="NONE", step_at=D2012),
                   frame(entity="FRA", etype="COUNTRY", step_at=D2012)], ignore_index=True)
    rows = vb.evaluate_b1(f, dates=[D2012])
    assert sorted(rows.entity_id) == ["R0", "R1"]
    assert sorted(vb.evaluate_b1(f, dates=[D2012], entity_type="COUNTRY", exclude=()).entity_id) == ["FRA"]


def test_two_dates_are_evaluated_independently():
    f = pd.concat([frame(entity=f"R{i}", first=(2011, 1), last=(2019, 12), aqua=100.0) for i in range(5)], ignore_index=True)
    f.loc[f.year * 100 + f.month >= 201804, "estimate"] = 135.0          # a step of 1.35 at 2018-04 only
    rows = vb.evaluate_b1(f)
    by = {d: vb.b1_status(g)["fraction_within"] for d, g in rows.groupby("date")}
    assert by == {"2012-01": 1.0, "2018-04": 0.0}


def test_pct_of_normal_shift_is_the_difference_of_the_two_window_medians():
    f = frame(first=(2011, 1), last=(2012, 12))
    f["pct_of_normal"] = np.where(f.year == 2011, 100.0, 130.0)
    r = vb.pct_of_normal_shift(f, "R1", D2012)
    assert r["shift"] == 30.0 and r["n_before"] == 12 and r["n_after"] == 12
    assert vb.pct_of_normal_shift(f.assign(pct_of_normal=np.nan), "R1", D2012)["shift"] is None


def test_prepare_reads_witnesses_used_given_as_list_array_or_text():
    for used in (["AQUA_MODIS"], np.array(["AQUA_MODIS"], dtype=object), "['AQUA_MODIS']"):
        f = frame(first=(2012, 1), last=(2012, 1))
        f["witnesses_used"] = [used]
        assert bool(vb.prepare(f).has_aqua.iloc[0])


# ------------------------------------------------------------------------------------------------------------- B3: the drift
def ratio_series(slope_per_month: float, onset_idx: int, daynights=("D", "N"), n_snpp=164, n_n20=99, noise=0.01, seed=3) -> pd.DataFrame:
    """Global R(t) = Aqua / converted VIIRS in the shape of aqua_drift.build_series: flat at 1, then falling by `slope_per_month` (log)."""
    rng = np.random.default_rng(seed)
    out = []
    for dn in daynights:
        for w, first, n in (("SNPP_VIIRS", 0, n_snpp), ("NOAA20_VIIRS", ad.month_index(2018, 4), n_n20)):
            idx = np.arange(first, first + n)
            y = -slope_per_month * np.maximum(0, idx - onset_idx)
            out.append(pd.DataFrame({"entity_id": "GLOBAL", "witness": w, "daynight": dn, "idx": idx, "R": np.exp(y + rng.normal(0, noise, n))}))
    return pd.concat(out, ignore_index=True)


FAST = 60       # bootstrap replicates, enough for planted effects


def test_a_planted_drift_in_both_witnesses_passes_and_reports_the_onset():
    onset = ad.month_index(2022, 6)
    res = vb.evaluate_b3_drift(ratio_series(0.01, onset), reps=FAST)
    assert res["status"] == "PASS" and res["qualifying_parts"] == ["D", "N"]
    assert res["series"]["N|SNPP_VIIRS"]["onset_month"] in ("2022-05", "2022-06", "2022-07")
    assert res["series"]["N|SNPP_VIIRS"]["slope_pct_per_year"] < 0


def test_a_flat_ratio_fails_the_drift_check():
    res = vb.evaluate_b3_drift(ratio_series(0.0, ad.month_index(2022, 6)), reps=FAST)
    assert res["status"] == "FAIL" and res["qualifying_parts"] == []


def test_drift_in_one_part_only_is_enough_when_both_witnesses_show_it():
    s = ratio_series(0.01, ad.month_index(2022, 6), daynights=("N",))
    flat_day = ratio_series(0.0, ad.month_index(2022, 6), daynights=("D",))
    res = vb.evaluate_b3_drift(pd.concat([s, flat_day], ignore_index=True), reps=FAST)
    assert res["status"] == "PASS" and res["qualifying_parts"] == ["N"]


def test_drift_seen_by_one_witness_only_does_not_pass():
    s = ratio_series(0.01, ad.month_index(2022, 6), daynights=("N",))
    flat = ratio_series(0.0, ad.month_index(2022, 6), daynights=("N",))
    mixed = pd.concat([s[s.witness == "SNPP_VIIRS"], flat[flat.witness == "NOAA20_VIIRS"]], ignore_index=True)
    assert vb.evaluate_b3_drift(mixed, reps=FAST)["status"] == "FAIL"


def test_a_rising_ratio_or_an_onset_before_2021_does_not_qualify():
    assert vb.evaluate_b3_drift(ratio_series(-0.01, ad.month_index(2022, 6)), reps=FAST)["status"] == "FAIL"       # R rising: positive slope
    early = vb.evaluate_b3_drift(ratio_series(0.01, ad.month_index(2019, 3)), reps=FAST)
    assert early["status"] == "FAIL"                                  # detected, but the onset is before 2021-01


def test_too_short_series_give_inconclusive_and_the_drift_check_is_reproducible():
    short = ratio_series(0.01, ad.month_index(2022, 6), n_snpp=40, n_n20=30)
    assert vb.evaluate_b3_drift(short, reps=FAST)["status"] == "INCONCLUSIVE"
    s = ratio_series(0.01, ad.month_index(2022, 6))
    a, b = vb.evaluate_b3_drift(s, reps=FAST), vb.evaluate_b3_drift(s, reps=FAST)
    assert json.dumps(a, sort_keys=True, default=float) == json.dumps(b, sort_keys=True, default=float)


# ---------------------------------------------------------------------------------------------------------- B3: the outages
def wm_frame(rows: list[tuple]) -> pd.DataFrame:
    """rows: (year, month, witness, days_available, days_in_month)."""
    return pd.DataFrame([{"year": y, "month": m, "witness": w, "days_available": a, "days_in_month": d, "complete": a == d} for y, m, w, a, d in rows])


WM = wm_frame([(2020, 1, "AQUA_MODIS", 31, 31), (2020, 2, "AQUA_MODIS", 20, 29), (2020, 3, "AQUA_MODIS", 31, 31),
               (2020, 2, "SNPP_VIIRS", 29, 29), (2020, 4, "AQUA_MODIS", 10, 30), (2020, 4, "SNPP_VIIRS", 12, 30)])


def test_an_outage_month_is_one_with_no_complete_witness():
    # 2020-02: Aqua incomplete but S-NPP complete, so not an outage; 2020-04: both incomplete
    assert vb.outage_months(WM) == [(2020, 4)]


def outage_frame(estimate_in_outage=None, used_in_outage=()):
    rows = []
    for y, m in ((2020, 1), (2020, 2), (2020, 3), (2020, 4)):
        outage = (y, m) == (2020, 4)
        est = (estimate_in_outage if outage else 50.0)
        rows.append({"entity_type": "REGION", "entity_id": "R1", "year": y, "month": m, "estimate": est,
                     "witnesses_used": list(used_in_outage) if outage else (["SNPP_VIIRS"] if m == 2 else ["AQUA_MODIS"]), "verdict": "CANNOT_DETERMINE",
                     "reason_codes": ["OUTAGE"] if outage else [], "baseline_median": 40.0})
    return pd.DataFrame(rows)


def test_outage_months_with_no_estimate_pass_and_one_estimate_fails():
    ok = vb.evaluate_outage_estimates(outage_frame(None), WM)
    assert ok["status"] == "PASS" and ok["entity_months_in_outage"] == 1 and ok["share_without_estimate"] == 1.0
    bad = vb.evaluate_outage_estimates(outage_frame(12.0), WM)
    assert bad["status"] == "FAIL" and bad["share_without_estimate"] == 0.0


def test_an_incomplete_witness_must_not_be_used_even_when_another_witness_gives_an_estimate():
    used_incomplete = outage_frame(None)
    used_incomplete["witnesses_used"] = [["AQUA_MODIS", "SNPP_VIIRS"] if m == 2 else u            # Aqua is incomplete in 2020-02
                                         for m, u in zip(used_incomplete.month, used_incomplete.witnesses_used, strict=True)]
    res = vb.evaluate_outage_estimates(used_incomplete, WM)
    assert res["status"] == "FAIL" and res["incomplete_witness_used"] == 1


def test_no_outage_month_in_the_frame_is_inconclusive_not_a_pass():
    f = outage_frame(None)
    f = f[f.month != 4]
    assert vb.evaluate_outage_estimates(f, WM)["status"] == "INCONCLUSIVE"


def test_outage_verdicts_are_not_run_without_the_verdict_product():
    raw_only = outage_frame(None).assign(baseline_median=np.nan, reason_codes=[["NOT_HARMONIZED"]] * 4)
    assert not vb.has_verdicts(raw_only)
    for f in (raw_only, None):
        res = vb.evaluate_outage_verdicts(f, WM)
        assert res["status"] == "NOT_RUN" and "T-014" in res["why"]


def test_outage_verdicts_pass_at_100_percent_cannot_determine_and_fail_otherwise():
    res = vb.evaluate_outage_verdicts(outage_frame(None), WM)
    assert res["status"] == "PASS" and res["share_cannot_determine"] == 1.0 and res["share_with_outage_code"] == 1.0
    bad = outage_frame(None)
    bad.loc[bad.month == 4, "verdict"] = "WITHIN_NORMAL"
    assert vb.evaluate_outage_verdicts(bad, WM)["status"] == "FAIL"
    no_code = outage_frame(None)
    no_code["reason_codes"] = [[] for _ in range(len(no_code))]
    r = vb.evaluate_outage_verdicts(no_code, WM)
    assert r["status"] == "PASS" and r["share_with_outage_code"] == 0.0          # the plan asks for CANNOT_DETERMINE; the code share is reported


def test_snpp_end_is_described_from_the_monthly_availability():
    wm = wm_frame([(2026, 10, "SNPP_VIIRS", 31, 31), (2026, 11, "SNPP_VIIRS", 2, 30), (2026, 11, "AQUA_MODIS", 14, 30)])
    f = pd.DataFrame({"year": [2026, 2026], "month": [10, 11], "witnesses_used": [["SNPP_VIIRS"], []]})
    d = vb.describe_snpp_end(wm, f)
    assert d["last_complete_month"] == "2026-10" and d["days_available_in_end_month"] == 2 and d["consistent_with_end"]
    assert d["entity_months_using_snpp_from_end_month"] == 0 and d["entity_months_from_end_month"] == 1


# ------------------------------------------------------------------- the outage rule on the real estimator (synthetic products)
def build_products(tmp: Path) -> hz.Paths:
    """One cell, Aqua only: 2020-01 and 2020-03 complete, 2020-02 has Aqua available on 20 of 29 days (an outage: no other witness)."""
    pq.write_table(pa.table({"cell_id": ["A1"], "stratum_id": ["NHAF_b001_001"]}), tmp / "cells.parquet")
    cal = pd.DataFrame([("NHAF_b001_001", w, dn, s, 0.5, 0.05, 12, "x", "LOCAL") for w in ("SNPP_VIIRS", "NOAA20_VIIRS") for dn in ("D", "N")
                        for s in ("DJF", "MAM", "JJA", "SON")],
                       columns=["stratum_id", "witness", "daynight", "season", "ratio", "ratio_sd", "n_overlap_months", "fit_period", "pooling_level"])
    pq.write_table(pa.Table.from_pandas(cal, preserve_index=False), tmp / "calibration.parquet")
    rows = []
    for m, dim, avail in ((1, 31, 31), (2, 29, 20), (3, 31, 31)):
        for dn, n in (("D", 40), ("N", 10), ("ALL", 50)):
            rows.append(("A1", 2020, m, "AQUA_MODIS", dn, n, n, 0.0, avail, dim, "SP"))
    df = pd.DataFrame(rows, columns=["cell_id", "year", "month", "witness", "daynight", "detections", "cell_days", "frp_sum_mw",
                                     "days_available", "days_in_month", "data_level"])
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), tmp / "cell_month_witness.parquet")
    return hz.Paths(products=tmp, tmp=tmp / "dbtmp")


def test_the_real_estimator_gives_no_estimate_in_an_outage_month(tmp_path):
    paths = build_products(tmp_path)
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("CREATE TEMP TABLE members AS SELECT 'REGION' AS entity_type, 'R1' AS entity_id, 'R1' AS entity_name, 'A1' AS cell_id")
    agg = hz.aggregate(con, paths, "members", None)
    f = pd.DataFrame(hz.records_from(agg, {("REGION", "R1"): 1}))
    wm = vb.incomplete_witness_months(paths)
    assert vb.outage_months(wm) == [(2020, 2)]
    res = vb.evaluate_outage_estimates(f, wm)
    assert res["status"] == "PASS" and res["entity_months_in_outage"] == 1 and res["with_estimate"] == 0
    assert f.set_index("month").estimate.notna().to_dict() == {1: True, 2: False, 3: True}


# -------------------------------------------------------------------------------------------------------- statuses and entries
def test_family_status_rules():
    assert vb.family_status(["PASS", "PASS"]) == "PASS"
    assert vb.family_status(["PASS", "NOT_RUN"]) == "NOT_RUN"
    assert vb.family_status(["PASS", "NOT_RUN", "FAIL"]) == "FAIL"
    assert vb.family_status(["PASS", "INCONCLUSIVE"]) == "INCONCLUSIVE"
    assert vb.family_status(["NOT_RUN", "INCONCLUSIVE"]) == "NOT_RUN"


def test_entries_have_the_contract_shape_valid_statuses_and_json():
    b1 = {"2012-01": status_of([1.0] * 5), "2018-04": status_of([1.0, 1.0, 1.0, 1.5, 1.6])}
    b3 = {"B3-DRIFT": {"status": "PASS", "qualifying_parts": ["N"]}, "B3-OUTAGE-ESTIMATE": {"status": "PASS", "share_without_estimate": 1.0},
          "B3-OUTAGE-VERDICT": {"status": "NOT_RUN", "why": "no T-014"}}
    entries = vb.entries_from(b1, b3)
    ids = [e["test_id"] for e in entries]
    assert ids == ["B1-2012-01", "B1-2018-04", "B1", "B3-DRIFT", "B3-OUTAGE-ESTIMATE", "B3-OUTAGE-VERDICT", "B3"]
    for e in entries:
        assert set(e) == {"test_id", "family", "title", "case", "criterion", "threshold", "measured", "status", "notes"}
        assert e["status"] in vb.STATUSES and e["family"] == "B"
    st = {e["test_id"]: e["status"] for e in entries}
    assert st["B1"] == "FAIL" and st["B3"] == "NOT_RUN"
    json.dumps(entries)


def test_entries_never_turn_a_not_run_part_into_a_pass():
    b1 = {"2012-01": status_of([1.0] * 5), "2018-04": status_of([1.0] * 5)}
    b3 = {"B3-DRIFT": {"status": "PASS"}, "B3-OUTAGE-ESTIMATE": {"status": "PASS"}, "B3-OUTAGE-VERDICT": {"status": "NOT_RUN", "why": "x"}}
    st = {e["test_id"]: e["status"] for e in vb.entries_from(b1, b3)}
    assert st["B1"] == "PASS" and st["B3"] == "NOT_RUN"


def test_the_b1_evaluation_is_deterministic():
    f = many([1.0, 1.04, 0.97, 1.3, 1.0])
    a = vb.evaluate_b1(f, dates=[D2012])
    assert a.equals(vb.evaluate_b1(f, dates=[D2012]))
    shuffled = vb.evaluate_b1(f.sample(frac=1.0, random_state=1), dates=[D2012])      # row order of the input does not matter
    assert a.equals(shuffled.reset_index(drop=True))


def test_the_locked_thresholds_are_those_of_the_plan():
    assert vb.B1_DATES == [(2012, 1), (2018, 4)] and vb.WINDOW == 12 and vb.TOLERANCE == 0.10 and vb.PASS_FRACTION == 0.80
