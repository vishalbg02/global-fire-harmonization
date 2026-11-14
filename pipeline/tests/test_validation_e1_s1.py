"""Tests for pipeline/validation_e1_s1.py on SYNTHETIC data with answers known by hand (T-025, tests E1 and S1).

    python -m pytest pipeline/tests/test_validation_e1_s1.py -q -p no:cacheprovider

The synthetic world is the one of test_calibration.py (Aqua ~ Poisson, witness ~ Poisson / ratio, 2012-2021), with a planted difference
between fire regions: the witness-to-Aqua multiplier is 0.6, 0.5 and 0.7 in three regions and 1.0 in a fourth (TENA, where the raw merge is
already right). Nothing here is a result on real data.
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

import calibration as cal
import test_calibration as tc
import validation_e1_s1 as v

WORLD = {"NHAF": 0.6, "SHAF": 0.5, "EURO": 0.7, "TENA": 1.0}   # SYNTHETIC multipliers: Aqua = ratio x witness
BOOT = 25


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    """Write the synthetic products once and share them (read-only) between the tests of this module."""
    tmp = tmp_path_factory.mktemp("world")
    old = tc.REGIONS
    tc.REGIONS = WORLD
    try:
        tc.make_products(tmp, sigma=0.0, lam=20.0, seed=11)
    finally:
        tc.REGIONS = old
    return tmp


@pytest.fixture(scope="module")
def e1_run(world, tmp_path_factory):
    return v.run_e1(src=world, work=tmp_path_factory.mktemp("e1work"), boot=BOOT, seed=5, required=3)


# ----------------------------------------------------------------------------------------------------- the planted world
def test_leaving_a_region_out_changes_its_ratio_and_the_metric_detects_it(e1_run, world):
    r = e1_run["regions"]
    # the global ratio of the other three regions is their harmonic mean (equal Aqua activity): TENA is not 1.0 for them
    others = {k: val for k, val in WORLD.items() if k != "TENA"}
    hm = len(others) / sum(1.0 / x for x in others.values())
    g = r["TENA"]["global_ratio_fit_without_region"]["D|JJA"]
    assert g == pytest.approx(hm, rel=0.08) and abs(g - 1.0) > 0.3
    # for TENA the raw merge is already right and the unseen-region conversion is wrong: a LOSS, detected by the metric
    t = r["TENA"]
    assert t["D"]["raw"]["median_abs_log_error"] < 0.1 < t["D"]["ours"]["median_abs_log_error"]
    assert t["outcome"]["win"] is False and t["outcome"]["parts"] == {"D": False, "N": False}
    # the other three regions win: their ratio is near the global one of the rest, the raw merge is not
    for k in ("NHAF", "SHAF", "EURO"):
        assert r[k]["outcome"]["win"] is True, k
        assert r[k]["D"]["ours"]["median_abs_log_error"] < r[k]["D"]["raw"]["median_abs_log_error"]
    assert e1_run["summary"] == {"status": "PASS", "wins": 3, "losses": 1, "not_evaluable": 0, "regions": 4, "required": 3}


def test_the_unseen_conversion_is_the_global_ratio_without_the_region(e1_run):
    for region, res in e1_run["regions"].items():
        assert res["max_rel_diff_ours_ratio_vs_gloo"] < 0.02, region     # the pooled phantom equals the global ratio of the fit without R


def test_a_full_fit_gets_the_region_right_but_the_leave_one_out_does_not(world):
    full, _ = cal.calibrate(cal.Paths(products=world, tmp=world / "dbtmp"), boot=BOOT, seed=5)
    df = pd.DataFrame(full)
    d = df[(df.witness == "SNPP_VIIRS") & (df.daynight == "D") & (df.season == "JJA") & df.stratum_id.str.startswith("TENA_")]
    assert d.ratio.median() == pytest.approx(1.0, rel=0.1)               # seen: the planted ratio is recovered


# ----------------------------------------------------------------------------------------------------- exclusion and leakage
def region_cell_ids(src: Path, region: str) -> set[str]:
    t = pq.read_table(src / "cells.parquet").to_pandas()
    return set(t.loc[t.fire_region == region, "cell_id"])


def test_the_region_is_really_excluded_from_every_fit_input(world, tmp_path):
    info = v.prepare_fit_products(world, "TENA", tmp_path / "fit")
    audit = v.audit_fit_products(tmp_path / "fit", "TENA")
    assert info["cells_removed"] == 32 and audit["region_cells_in_cells"] == 0 and audit["cmw_rows_of_cells_not_in_fit_cells"] == 0
    cells = pq.read_table(tmp_path / "fit" / "cells.parquet").to_pandas()
    gone = region_cell_ids(world, "TENA")
    assert not (set(cells.cell_id) & gone) and (cells.fire_region == "TENA").sum() == 0
    cmw = pq.read_table(tmp_path / "fit" / "cell_month_witness.parquet").to_pandas()
    assert not (set(cmw.cell_id) & gone) and PHANTOM not in set(cmw.cell_id)
    assert cmw.year.max() <= 2016 and set(cmw.witness) == {"AQUA_MODIS", "SNPP_VIIRS"}
    assert PHANTOM in set(cells.cell_id) and cells.loc[cells.cell_id == PHANTOM, "fire_region"].iloc[0] == cal.UNASSIGNED


PHANTOM = v.PHANTOM_CELL


def test_changing_the_left_out_region_does_not_change_the_fit(world, tmp_path):
    # tamper with TENA's data in a copy of the products: the fit without TENA must not notice (identical table, same seed)
    alt = tmp_path / "alt"
    alt.mkdir()
    pq.write_table(pq.read_table(world / "cells.parquet"), alt / "cells.parquet")
    cmw = pq.read_table(world / "cell_month_witness.parquet").to_pandas()
    mask = cmw.cell_id.isin(region_cell_ids(world, "TENA"))
    cmw.loc[mask, ["cell_days", "detections"]] = cmw.loc[mask, ["cell_days", "detections"]] * 3 + 7
    pq.write_table(pa.Table.from_pandas(cmw, preserve_index=False), alt / "cell_month_witness.parquet")
    a, _, _ = v.fit_without_region(world, "TENA", tmp_path / "wa", boot=BOOT, seed=5)
    b, _, _ = v.fit_without_region(alt, "TENA", tmp_path / "wb", boot=BOOT, seed=5)
    pd.testing.assert_frame_equal(a, b)
    # whereas leaving out a region that was NOT tampered with does see the difference
    c, _, _ = v.fit_without_region(world, "NHAF", tmp_path / "wc", boot=BOOT, seed=5)
    d, _, _ = v.fit_without_region(alt, "NHAF", tmp_path / "wd", boot=BOOT, seed=5)
    assert not a.equals(c) and not c.equals(d)


def test_nothing_from_2017_on_enters_any_fit(tmp_path):
    clean, dirty = tmp_path / "clean", tmp_path / "dirty"
    clean.mkdir()
    dirty.mkdir()
    old = tc.REGIONS
    tc.REGIONS = WORLD
    try:
        tc.make_products(clean, sigma=0.0, lam=20.0, seed=11)
        tc.make_products(dirty, sigma=0.0, lam=20.0, seed=11, holdout_outlier=True)      # +500 per cell-month for the VIIRS witnesses from 2017
    finally:
        tc.REGIONS = old
    a, ra, audit_a = v.fit_without_region(clean, "TENA", tmp_path / "wa", boot=BOOT, seed=5)
    b, rb, audit_b = v.fit_without_region(dirty, "TENA", tmp_path / "wb", boot=BOOT, seed=5)
    pd.testing.assert_frame_equal(a, b)
    assert audit_a["max_year"] <= 2016 and audit_b["max_year"] <= 2016
    assert set(a.witness) == {"SNPP_VIIRS"} and set(a.fit_period) == {"2012-01/2016-12"}
    assert ra["months"]["SNPP_VIIRS"] == rb["months"]["SNPP_VIIRS"] == 60


def test_the_audit_rejects_a_dirty_fit_input(world, tmp_path):
    v.prepare_fit_products(world, "TENA", tmp_path / "fit")
    cmw = pq.read_table(tmp_path / "fit" / "cell_month_witness.parquet").to_pandas()
    late = cmw.iloc[[0]].copy()
    late["year"] = 2017
    pq.write_table(pa.Table.from_pandas(pd.concat([cmw, late]), preserve_index=False), tmp_path / "fit" / "cell_month_witness.parquet")
    with pytest.raises(AssertionError):
        v.audit_fit_products(tmp_path / "fit", "TENA")
    v.prepare_fit_products(world, "TENA", tmp_path / "fit2")
    cmw = pq.read_table(tmp_path / "fit2" / "cell_month_witness.parquet").to_pandas()
    back = pq.read_table(world / "cell_month_witness.parquet").to_pandas()
    back = back[back.cell_id.isin(region_cell_ids(world, "TENA")) & (back.year == 2014)].head(3)
    pq.write_table(pa.Table.from_pandas(pd.concat([cmw, back]), preserve_index=False), tmp_path / "fit2" / "cell_month_witness.parquet")
    with pytest.raises(AssertionError):
        v.audit_fit_products(tmp_path / "fit2", "TENA")


def test_an_unknown_region_is_refused(world, tmp_path):
    with pytest.raises(ValueError):
        v.prepare_fit_products(world, "XXXX", tmp_path / "fit")


def test_regions_exclude_unassigned():
    cells = pd.DataFrame({"fire_region": ["EURO", "UNASSIGNED", "BOAS", None, "EURO"]})
    assert v.regions_of(cells) == ["BOAS", "EURO"]


def test_unseen_ratios_copy_the_phantom_rows_to_every_stratum_of_the_region():
    rows = []
    for stratum, ratio in (("PH", 0.55), ("OTHER", 0.9)):
        for dn in ("D", "N", "ALL"):
            for season in cal.SEASONS:
                rows.append((stratum, "SNPP_VIIRS", dn, season, ratio, 0.01, 7, "2012-01/2016-12", "LOCAL"))
    loo = pd.DataFrame(rows, columns=[f.name for f in cal.SCHEMA])
    out = v.unseen_ratios(loo, "PH", ["X_b001_001", "X_b001_002"])
    assert len(out) == 2 * 12 and set(out.stratum_id) == {"X_b001_001", "X_b001_002"}
    assert (out.ratio == 0.55).all() and (out.pooling_level == "GLOBAL").all() and (out.n_overlap_months == 0).all()
    with pytest.raises(ValueError):
        v.unseen_ratios(loo, "MISSING", ["X_b001_001"])


def test_the_global_frame_leaves_a_region_out_and_a_month_is_complete_only_if_complete_everywhere():
    rows = []
    for region, raw, ok in (("A", 10, True), ("B", 30, True), ("C", 5, False)):
        for wit, mult in (("AQUA_MODIS", 1), ("SNPP_VIIRS", 2)):
            rows.append({"fire_region": region, "year": 2013, "month": 5, "daynight": "D", "witness": wit, "raw": raw * mult, "complete": ok})
    d = pd.DataFrame(rows)
    full = v.global_frame(d).set_index("witness")
    assert full.loc["AQUA_MODIS", "raw"] == 45 and not full.loc["AQUA_MODIS", "complete"]
    loo = v.global_frame(d, exclude="C").set_index("witness")
    assert loo.loc["AQUA_MODIS", "raw"] == 40 and loo.loc["SNPP_VIIRS", "raw"] == 80 and loo.loc["AQUA_MODIS", "complete"]


# ----------------------------------------------------------------------------------------------------- counting and status
def outcome(win=None, evaluable=True):
    return {"win": bool(win), "evaluable": evaluable, "parts": {}}


def outcomes(wins, losses, not_eval):
    d = {f"W{i}": outcome(True) for i in range(wins)}
    d.update({f"L{i}": outcome(False) for i in range(losses)})
    d.update({f"N{i}": outcome(False, evaluable=False) for i in range(not_eval)})
    return d


def test_eleven_of_fourteen_passes_and_ten_does_not():
    assert v.e1_status(outcomes(11, 3, 0))["status"] == "PASS"
    assert v.e1_status(outcomes(14, 0, 0))["status"] == "PASS"
    s = v.e1_status(outcomes(10, 4, 0))
    assert s["status"] == "FAIL" and s["wins"] == 10 and s["losses"] == 4 and s["regions"] == 14 and s["required"] == 11


def test_not_evaluable_regions_make_the_result_inconclusive_only_when_they_could_change_it():
    assert v.e1_status(outcomes(10, 2, 2))["status"] == "INCONCLUSIVE"      # 10 wins + 2 unknown could reach 11
    assert v.e1_status(outcomes(9, 3, 2))["status"] == "INCONCLUSIVE"       # 9 + 2 = 11 reaches the threshold exactly
    assert v.e1_status(outcomes(9, 4, 1))["status"] == "FAIL"               # even 9 + 1 = 10 < 11
    assert v.e1_status(outcomes(11, 0, 3))["status"] == "PASS"


def metrics_stub(units, ours, raw):
    return {"ours": {"units": units, "median_abs_log_error": ours}, "raw": {"units": units, "median_abs_log_error": raw}}


def test_a_region_wins_only_if_ours_beats_raw_in_every_evaluable_part():
    both = {"D": metrics_stub(30, 0.1, 0.5), "N": metrics_stub(30, 0.2, 0.6)}
    assert v.region_outcome(both) == {"parts": {"D": True, "N": True}, "evaluable": True, "win": True}
    night_loss = {"D": metrics_stub(30, 0.1, 0.5), "N": metrics_stub(30, 0.7, 0.6)}
    assert v.region_outcome(night_loss)["win"] is False
    tie = {"D": metrics_stub(30, 0.5, 0.5), "N": metrics_stub(30, 0.1, 0.6)}
    assert v.region_outcome(tie)["parts"]["D"] is False and v.region_outcome(tie)["win"] is False
    few_night = {"D": metrics_stub(30, 0.1, 0.5), "N": metrics_stub(11, 0.9, 0.1)}      # night has 11 < 12 units: not evaluated
    assert v.region_outcome(few_night) == {"parts": {"D": True, "N": None}, "evaluable": True, "win": True}
    nothing = {"D": {"ours": {"units": 0}, "raw": {"units": 0}}, "N": metrics_stub(5, 0.1, 0.2)}
    assert v.region_outcome(nothing) == {"parts": {"D": None, "N": None}, "evaluable": False, "win": False}


# ----------------------------------------------------------------------------------------------------- reproducibility
def test_the_run_is_reproducible(world, tmp_path):
    a = v.run_e1(src=world, work=tmp_path / "a", boot=BOOT, seed=5, regions=["TENA", "EURO"], required=1)
    b = v.run_e1(src=world, work=tmp_path / "b", boot=BOOT, seed=5, regions=["TENA", "EURO"], required=1)
    for res in (a, b):
        for r in res["regions"].values():
            r.pop("audit")
    same(a, b)


def same(x, y, path=""):
    """Equal up to rounding at the 1e-9 level: DuckDB sums in parallel, so the last digit of a float sum can differ between runs."""
    if isinstance(x, dict):
        assert x.keys() == y.keys(), path
        for k in x:
            same(x[k], y[k], f"{path}/{k}")
    elif isinstance(x, float):
        assert x == pytest.approx(y, rel=1e-9, nan_ok=True), path
    else:
        assert x == y, path


# ----------------------------------------------------------------------------------------------------- S1: verdict rules (D-028)
def test_probabilities_of_a_normal_truncated_at_zero_by_hand():
    above, below, within = v.probabilities(100.0, 10.0, 50.0, 80.0)
    assert above == pytest.approx(0.97725, abs=1e-4) and below == pytest.approx(0.0, abs=1e-6) and above + below + within == pytest.approx(1.0)
    # estimate 0, sd 1: the mass above 0 is 0.5; P(X > 1) = (1 - Phi(1)) / 0.5 = 0.31731
    above, below, _ = v.probabilities(0.0, 1.0, 0.0, 1.0)
    assert above == pytest.approx(0.31731, abs=1e-4) and below == 0.0
    assert v.probabilities(10.0, 0.0, 5.0, 8.0) == (1.0, 0.0, 0.0)          # no uncertainty: a point


def test_verdict_steps_apply_in_the_fixed_order():
    f = v.verdict_for
    assert f(None, None, 20, 10, 20, 30) == ("CANNOT_DETERMINE", "OUTAGE")
    assert f(0.0, 1.0, 14, 0, 0, 1) == ("CANNOT_DETERMINE", "INSUFFICIENT_BASELINE")      # step 2 before step 3
    assert f(0.0, 1.0, 20, 0, 0, 1) == ("NO_DETECTED_ACTIVITY", "")                       # step 3: zero and p75 <= 1
    assert f(0.0, 1.0, 20, 0, 2, 3) == ("CANNOT_DETERMINE", "INSUFFICIENT_BASELINE")      # p75 > 1 and p50 < 5: step 4
    assert f(100.0, 5.0, 20, 40, 60, 80) == ("ABOVE_NORMAL", "")
    assert f(10.0, 2.0, 20, 40, 60, 80) == ("BELOW_NORMAL", "")
    assert f(60.0, 2.0, 20, 40, 60, 80) == ("WITHIN_NORMAL", "")
    assert f(70.0, 30.0, 20, 50, 60, 80) == ("CANNOT_DETERMINE", "WIDE_INTERVAL")
    assert f(0.0, 0.5, 20, 6, 10, 15)[0] == "BELOW_NORMAL"                                 # zero with real baseline activity is below normal


def test_a_baseline_median_under_five_cannot_be_judged():
    assert v.verdict_for(500.0, 5.0, 20, 1, 4.9, 20) == ("CANNOT_DETERMINE", "INSUFFICIENT_BASELINE")
    assert v.verdict_for(500.0, 5.0, 20, 1, 5.0, 20)[0] == "ABOVE_NORMAL"


# ----------------------------------------------------------------------------------------------------- S1: baselines
def series(values: dict[int, float | None], eid="E", month=1, sd=1.0, etype="REGION") -> pd.DataFrame:
    return pd.DataFrame([{"entity_type": etype, "entity_id": eid, "year": y, "month": month, "estimate": x, "sd": sd} for y, x in values.items()])


def test_baseline_percentiles_by_hand_and_years_without_an_estimate_are_skipped():
    s = series({2002 + k: float(k) for k in range(1, 21)})                      # 2003..2022 -> 1..20
    b = v.baselines(s, (2003, 2022)).iloc[0]
    assert (b.n_years, b.p25, b.p50, b.p75) == (20, pytest.approx(5.75), pytest.approx(10.5), pytest.approx(15.25))
    s2 = series({**{2002 + k: float(k) for k in range(1, 21)}, 2010: None})
    assert v.baselines(s2, (2003, 2022)).iloc[0].n_years == 19
    assert v.baselines(s, (2003, 2021)).iloc[0].n_years == 19                    # the Aqua-measured window ends in 2021
    assert v.baselines(s, (2023, 2024)).empty


def planted(aqua_scale: float) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Harmonized series 90..110 (4 years each); the Aqua-only series equals it up to 2011 and is `aqua_scale` x it from 2012 on."""
    harm = {y: 90.0 + 5.0 * ((y - 2003) % 5) for y in range(2003, 2023)}
    aqua = {y: (x if y <= 2011 else x * aqua_scale) for y, x in harm.items()}
    return series(harm), series(aqua)


def test_a_different_aqua_baseline_changes_a_verdict_and_it_is_found():
    harm, aqua = planted(0.4)
    cmp = v.compare_baselines(harm, aqua)
    row = cmp[cmp.year == 2015].iloc[0]                                          # estimate 100: inside 95..105 of the harmonized baseline
    assert row.verdict_h == "WITHIN_NORMAL"
    # the Aqua baseline mixes 9 years near 100 and 10 years near 40: its p75 is 97.5, and 100 (sd 1) is above it
    assert row.p75_a == pytest.approx(97.5) and row.verdict_a == "ABOVE_NORMAL" and not row.agree
    assert row.p25_h == pytest.approx(95.0) and row.p75_h == pytest.approx(105.0)


def test_identical_baselines_agree_everywhere():
    harm, aqua = planted(1.0)
    cmp = v.compare_baselines(harm, aqua)
    assert len(cmp) == 10 and cmp.agree.all()        # window 2012-2021, month 1 only
    assert set(cmp.year) == set(range(2012, 2022))


def test_the_summary_and_the_status_follow_the_peak_months():
    harm, aqua = planted(0.4)
    cmp = v.compare_baselines(harm, aqua)
    rows = v.case_changes(cmp, {"CX": ("E", (2015, 1), (2015, 1))})
    assert len(rows) == 1 and rows[0]["unchanged"] is False and rows[0]["verdict_aqua_baseline"] == "ABOVE_NORMAL"
    assert v.s1_status(rows) == "FAIL" and v.s1_status([]) == "INCONCLUSIVE"
    same = v.case_changes(v.compare_baselines(*planted(1.0)), {"CX": ("E", (2015, 1), (2016, 1))})
    assert len(same) == 2 and v.s1_status(same) == "PASS"
    summ = v.summarise_s1(cmp)["REGION"]
    assert summ["entity_months"] == 10 and summ["changed"] == int((~cmp.agree).sum()) and 0.0 < summ["agree"] < 1.0


def test_the_t014_crosscheck_compares_nothing_before_baseline_products_exist():
    em = pd.DataFrame({"entity_type": ["REGION"], "entity_id": ["E"], "year": [2015], "month": [1], "estimate": [100.0], "sd": [1.0], "verdict": ["CANNOT_DETERMINE"]})
    assert v.crosscheck_with_t014(em, planted(1.0)[0]) == {"compared": 0, "mismatches": 0}
    em["baseline_median"] = 100.0
    out = v.crosscheck_with_t014(em, planted(1.0)[0])
    assert out == {"compared": 1, "mismatches": 1}                                # the stored verdict is not what the rules give: found


# ----------------------------------------------------------------------------------------------------- entries
def test_entries_have_the_contract_shape_and_s1_is_not_run_as_a_whole(e1_run):
    s1 = {"case_peak_months": [{"unchanged": True}], "summary": {}, "status_baseline": "PASS"}
    entries = v.build_entries(e1_run, s1)
    ids = [e["test_id"] for e in entries]
    assert ids == ["E1", "S1-BASELINE", "S1-CONFIDENCE-FILTER", "S1"]
    for e in entries:
        assert set(e) == {"test_id", "family", "title", "case", "criterion", "threshold", "measured", "status", "notes"}
        assert e["status"] in {"PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN"}
    by = {e["test_id"]: e for e in entries}
    assert by["E1"]["status"] == e1_run["summary"]["status"] and set(by["E1"]["measured"]["per_region"]) == set(WORLD)
    assert by["S1-CONFIDENCE-FILTER"]["status"] == "NOT_RUN" and by["S1"]["status"] == "NOT_RUN" and by["S1-BASELINE"]["status"] == "PASS"


def test_the_region_table_lists_every_region(e1_run):
    t = v.region_table(e1_run)
    for r in WORLD:
        assert f"| {r} |" in t
    assert "LOSS" in t and "WIN" in t


def test_the_fit_window_is_the_t011_snpp_window():
    assert v.FIT_WINDOW == ((2012, 1), (2016, 12)) and v.REQUIRED_WINS == 11 and v.MIN_CELL_DAYS == 20.0
    assert not np.isnan(v.MIN_UNITS)


def test_entries_are_built_from_both_reports_even_when_the_tests_ran_separately(e1_run, tmp_path):
    s1 = {"case_peak_months": [{"unchanged": False}], "summary": {}, "status_baseline": "FAIL"}
    v.write_outputs(e1_run, None, qa=tmp_path)
    paths = v.write_outputs(None, s1, qa=tmp_path)
    entries = {e["test_id"]: e for e in json.loads((tmp_path / "T-025_validation_entries.json").read_text(encoding="utf-8"))}
    assert set(entries) == {"E1", "S1-BASELINE", "S1-CONFIDENCE-FILTER", "S1"} and entries["S1-BASELINE"]["status"] == "FAIL"
    assert (tmp_path / "T-025_e1_report.json").exists() and (tmp_path / "T-025_validation_entries.json") in paths
