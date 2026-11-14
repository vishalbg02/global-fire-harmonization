"""Tests of pipeline/validation_b2_c1_ctrl.py on SYNTHETIC data with known answers (T-024). Nothing here is a result."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import harmonize as hz
import validation_b2_c1_ctrl as v

# --------------------------------------------------------------------------------------------------- SYNTHETIC fixtures
VAR_CELL_DAYS = 1000.0


def make_agg(entity_id="R1", etype="REGION", first=(2012, 1), last=(2013, 12), witnesses=("AQUA_MODIS", "SNPP_VIIRS", "NOAA20_VIIRS"),
             e=1000.0, per_witness=None, scale=None) -> pd.DataFrame:
    """SYNTHETIC aggregated table: every witness has day and night rows of the same size, complete months, ratio 1."""
    rows = []
    for y, m in v.months_between(first, last):
        for w in witnesses:
            for dn in ("D", "N"):
                val = (per_witness or {}).get(w, e) * (1.0 if scale is None else scale(y, m))
                rows.append({"entity_type": etype, "entity_id": entity_id, "entity_name": entity_id, "year": y, "month": m, "witness": w,
                             "daynight": dn, "raw": val, "complete": True, "lo": "SP", "hi": "SP", "e": val, "vc": val, "vr": 100.0,
                             "rbar": 1.0, "missing": 0, "e_pooled": 0.0})
    return pd.DataFrame(rows)


def records(agg, n=1, etype="REGION", eid="R1"):
    return v.frame(hz.records_from(agg, {(etype, eid): n}))


# --------------------------------------------------------------------------------------------------- helpers
def test_wilson_and_share():
    lo, hi = v.wilson(90, 100)
    assert 0.82 < lo < 0.84 and 0.94 < hi < 0.96
    assert v.wilson(0, 0) == (None, None)
    s = v.share(3, 4)
    assert s["share"] == 0.75 and s["k"] == 3 and s["n"] == 4


def test_month_index_label_roundtrip():
    assert v.label(v.midx(2012, 1)) == "2012-01" and v.label(v.midx(2018, 4)) == "2018-04"


# --------------------------------------------------------------------------------------------------- B2
def test_plant_jump_scales_exactly_the_right_rows_and_keeps_the_input():
    agg = make_agg()
    other = make_agg(entity_id="R2")
    both = pd.concat([agg, other], ignore_index=True)
    before = both.copy()
    start = v.midx(2012, 6)
    out = v.plant_jump(both, "R1", "SNPP_VIIRS", start, 3.0)
    pd.testing.assert_frame_equal(both, before)                      # the input is not changed
    idx = out.year * 12 + out.month - 1
    hit = (out.entity_id == "R1") & (out.witness == "SNPP_VIIRS") & (idx >= start)
    assert hit.sum() == 2 * (24 - 5)
    assert np.allclose(out.loc[hit, ["raw", "e", "vc"]].to_numpy(), 3000.0)
    assert np.allclose(out.loc[hit, "vr"], 900.0)                    # ratio variance x factor^2
    assert out.loc[~hit].equals(both.loc[~hit])                      # nothing else moved (R1 before the jump, other witnesses, R2)


def test_flag_rule():
    base = {"codes": frozenset(), "disagreement_scale": 1.0}
    assert not v.flagged(base)
    assert v.flagged({**base, "disagreement_scale": 1.5})            # widened
    assert not v.flagged({**base, "disagreement_scale": 1.49})
    assert v.flagged({**base, "codes": frozenset({"WITNESS_DISAGREEMENT"})})
    assert not v.flagged({**base, "disagreement_scale": 1.9}, code_only=True)
    assert v.flagged({**base, "codes": frozenset({"WITNESS_DISAGREEMENT"}), "disagreement_scale": 2.5}, code_only=True)
    assert not v.flagged({"codes": frozenset(), "disagreement_scale": float("nan")})
    assert not v.flagged({"codes": frozenset(), "disagreement_scale": None})


def test_agreeing_witnesses_are_not_flagged_and_a_big_jump_is():
    agg = make_agg()
    rec = records(agg)
    assert not any(v.flagged(r) for _, r in rec.iterrows())          # identical witnesses: S = 0, scale 1
    trial = {"trial": 0, "entity_type": "REGION", "entity_id": "R1", "witness": "SNPP_VIIRS", "start_idx": v.midx(2012, 6), "factor": 3.0, "abs_ln_f": 1.0}
    res = v.run_trial(trial, agg, rec, {("REGION", "R1"): 1})
    assert res["detected"] and res["detected_code"] and res["first_flag_month"] == 0 and res["months_checked"] == 3
    assert not res["twin_flagged"] and not res["twin_flagged_code"]
    down = v.run_trial({**trial, "factor": 1 / 3}, agg, rec, {("REGION", "R1"): 1})
    assert down["detected"]


def test_a_tiny_jump_is_not_flagged():
    agg = make_agg()
    rec = records(agg)
    trial = {"trial": 0, "entity_type": "REGION", "entity_id": "R1", "witness": "SNPP_VIIRS", "start_idx": v.midx(2012, 6), "factor": 1.02, "abs_ln_f": 0.02}
    assert not v.run_trial(trial, agg, rec, {("REGION", "R1"): 1})["detected"]


def test_unplanted_twin_flag_is_read_from_the_unperturbed_records():
    per = {"SNPP_VIIRS": 3000.0}                                      # the data themselves disagree: the twin IS flagged
    agg = make_agg(per_witness=per)
    rec = records(agg)
    trial = {"trial": 0, "entity_type": "REGION", "entity_id": "R1", "witness": "AQUA_MODIS", "start_idx": v.midx(2012, 6), "factor": 1.5, "abs_ln_f": 0.4}
    res = v.run_trial(trial, agg, rec, {("REGION", "R1"): 1})
    assert res["twin_flagged"] and res["detected"]


def test_keep_possible_drops_months_that_cannot_reach_the_minimum():
    big = make_agg(e=1000.0)
    small = make_agg(entity_id="R2", e=1.0)                           # sum over day/night of the largest witness = 2 < 5
    kept = v.keep_possible(pd.concat([big, small], ignore_index=True))
    assert set(kept.entity_id) == {"R1"}
    assert set(v.keep_possible(small, min_estimate=2.0).entity_id) == {"R2"}


def test_eligible_pairs_rules():
    agg = make_agg(first=(2012, 1), last=(2012, 12))
    rec = records(agg)
    first, last = v.midx(2012, 1), v.midx(2012, 12)
    pairs = v.eligible_pairs(rec, first, last)["R1"]
    assert (first, "SNPP_VIIRS") in pairs and (last - 2, "AQUA_MODIS") in pairs and all(d <= last - 2 for d, _ in pairs)
    assert len(pairs) == 10 * 3                                       # 10 start months x 3 witnesses
    # a hole in one month removes every start month whose window contains it
    holed = agg[~(agg.month == 6)]
    p2 = v.eligible_pairs(records(holed), first, last)["R1"]
    assert all(not (d <= v.midx(2012, 6) <= d + 2) for d, _ in p2)
    # one witness only: nothing to compare with, nothing eligible
    solo = make_agg(first=(2012, 1), last=(2012, 12), witnesses=("AQUA_MODIS",))
    assert v.eligible_pairs(records(solo), first, last) == {}
    # estimates below the minimum are not eligible
    assert v.eligible_pairs(records(make_agg(first=(2012, 1), last=(2012, 12), e=1.0)), first, last) == {}
    # a witness missing in the window cannot be the planted one
    no20 = make_agg(first=(2012, 1), last=(2012, 12), witnesses=("AQUA_MODIS", "SNPP_VIIRS"))
    ws = {w for _, w in v.eligible_pairs(records(no20), first, last)["R1"]}
    assert ws == {"AQUA_MODIS", "SNPP_VIIRS"}


def test_draw_trials_is_reproducible_eligible_and_in_range():
    pairs = {"REGION": {"A": [(150, "AQUA_MODIS"), (151, "SNPP_VIIRS")], "B": [(160, "NOAA20_VIIRS")]}, "CELL": {"c": [(170, "AQUA_MODIS")]}}
    t1 = v.draw_trials(pairs, {"REGION": 30, "CELL": 20}, seed=5)
    t2 = v.draw_trials(pairs, {"REGION": 30, "CELL": 20}, seed=5)
    assert t1 == t2 and len(t1) == 50
    assert t1 != v.draw_trials(pairs, {"REGION": 30, "CELL": 20}, seed=6)
    for t in t1:
        assert (t["start_idx"], t["witness"]) in pairs[t["entity_type"]][t["entity_id"]]
        assert 1.5 - 1e-9 <= max(t["factor"], 1 / t["factor"]) <= 3.0 + 1e-9
    assert any(t["factor"] > 1 for t in t1) and any(t["factor"] < 1 for t in t1)
    assert v.draw_trials({"REGION": {}, "CELL": {}}, {"REGION": 5, "CELL": 5}) == []


def test_b2_status_logic():
    assert v.b2_status(0.90, 0.049, 200) == "PASS"
    assert v.b2_status(0.899, 0.01, 200) == "FAIL"
    assert v.b2_status(1.0, 0.05, 200) == "FAIL"                      # under 5%, not at 5%
    assert v.b2_status(1.0, 0.0, 49) == "INCONCLUSIVE"
    assert v.b2_status(None, 0.0, 200) == "INCONCLUSIVE"


def test_run_b2_end_to_end_on_a_synthetic_world_is_reproducible():
    regions = make_agg(entity_id="R1", etype="REGION", first=(2012, 1), last=(2021, 12))
    cells = make_agg(entity_id="c1", etype="CELL", first=(2012, 1), last=(2021, 12))
    n = {("REGION", "R1"): 1, ("CELL", "c1"): 1}
    a = v.run_b2(regions, cells, n, seed=11, n_by_type={"REGION": 30, "CELL": 30})
    b = v.run_b2(regions, cells, n, seed=11, n_by_type={"REGION": 30, "CELL": 30})
    assert a["trials"] == b["trials"] and a["summary"] == b["summary"]
    assert a["summary"]["trials"] == 60
    assert a["rates"]["detection"] == 1.0 and a["rates"]["false_flag_twin"] == 0.0     # identical witnesses; jumps of 1.5 to 3 times
    assert a["status"] == "PASS"
    assert a["monthly"]["flagged_union"]["share"] == 0.0 and a["monthly"]["entities"] == 2
    assert a["eligible_entities"] == {"REGION": 1, "CELL": 1}
    assert set(a["breakdowns"]) >= {"entity_type", "witness", "jump_size_tercile", "direction", "year"}


def test_run_b2_with_fewer_than_50_trials_is_inconclusive():
    regions = make_agg(entity_id="R1", etype="REGION", first=(2012, 1), last=(2021, 12))
    cells = make_agg(entity_id="c1", etype="CELL", first=(2012, 1), last=(2021, 12))
    out = v.run_b2(regions, cells, {("REGION", "R1"): 1, ("CELL", "c1"): 1}, seed=1, n_by_type={"REGION": 20, "CELL": 20})
    assert out["status"] == "INCONCLUSIVE" and out["rates"]["detection"] == 1.0


def test_run_b2_fails_when_the_data_flag_themselves():
    per = {"SNPP_VIIRS": 3000.0}                                       # witnesses disagree in the data: every twin is flagged
    regions = make_agg(entity_id="R1", etype="REGION", first=(2012, 1), last=(2021, 12), per_witness=per)
    cells = make_agg(entity_id="c1", etype="CELL", first=(2012, 1), last=(2021, 12), per_witness=per)
    out = v.run_b2(regions, cells, {("REGION", "R1"): 1, ("CELL", "c1"): 1}, seed=3, n_by_type={"REGION": 30, "CELL": 30})
    assert out["rates"]["false_flag_twin"] == 1.0 and out["status"] == "FAIL"
    assert out["monthly"]["entities_flagged_anywhere_union"]["share"] == 1.0


# --------------------------------------------------------------------------------------------------- C1
def c1_frame(rows):
    df = pd.DataFrame(rows, columns=["entity_id", "year", "month", "estimate", "sd"])
    df["ci90_low"] = (df.estimate - v.Z90 * df.sd).clip(lower=0)
    df["ci90_high"] = df.estimate + v.Z90 * df.sd
    return df


def test_c1_combined_interval_is_stricter_than_overlap():
    # difference 3.0 sd (each sd 1): combined sd = sqrt(2) = 1.414, 1.645 x 1.414 = 2.33 < 3.0 -> disagree; the intervals (+-1.645) still overlap (3.0 <= 3.29)
    s = c1_frame([("A", 2019, 1, 100.0, 1.0)])
    n = c1_frame([("A", 2019, 1, 103.0, 1.0)])
    u = v.c1_units(s, n)
    assert len(u) == 1 and not bool(u.agree[0]) and bool(u.overlap[0])
    n2 = c1_frame([("A", 2019, 1, 102.0, 1.0)])                      # difference 2.0 <= 2.33: agree
    assert bool(v.c1_units(s, n2).agree[0])
    n3 = c1_frame([("A", 2019, 1, 110.0, 1.0)])                      # far apart: neither
    u3 = v.c1_units(s, n3)
    assert not bool(u3.agree[0]) and not bool(u3.overlap[0])


def test_c1_units_filters_window_minimum_and_missing():
    s = c1_frame([("A", 2018, 1, 100.0, 5.0), ("A", 2019, 1, 100.0, 5.0), ("A", 2019, 2, 3.0, 1.0), ("A", 2022, 1, 100.0, 5.0), ("B", 2019, 1, 100.0, 5.0)])
    n = c1_frame([("A", 2018, 1, 100.0, 5.0), ("A", 2019, 1, 100.0, 5.0), ("A", 2019, 2, 3.0, 1.0), ("A", 2022, 1, 100.0, 5.0)])
    n.loc[len(n)] = ["B", 2019, 1, np.nan, np.nan, np.nan, np.nan]
    u = v.c1_units(s, n)
    assert sorted(zip(u.entity_id, u.year, u.month, strict=True)) == [("A", 2018, 1), ("A", 2019, 1)]       # 2022 outside, 3.0 < 5, B has no NOAA-20 estimate
    assert len(v.c1_units(s, n, v.C1_OOS_WINDOW)) == 1
    assert len(v.c1_units(s, n, v.C1_WINDOW, min_estimate=0.0)) == 3


def test_c1_status_and_summary():
    assert v.c1_status(0.85, 500) == "PASS" and v.c1_status(0.8499, 500) == "FAIL" and v.c1_status(1.0, 99) == "INCONCLUSIVE"
    rows_s = [("A", 2019, m, 100.0, 1.0) for m in range(1, 13)] + [("B", 2019, m, 100.0, 1.0) for m in range(1, 13)]
    rows_n = [("A", 2019, m, 100.0, 1.0) for m in range(1, 13)] + [("B", 2019, m, 150.0, 1.0) for m in range(1, 13)]
    summ = v.c1_summary(v.c1_units(c1_frame(rows_s), c1_frame(rows_n)))
    assert summ["units"] == 24 and summ["agree"]["share"] == 0.5 and summ["per_region"]["A"]["agree"] == 1.0 and summ["per_region"]["B"]["agree"] == 0.0
    assert summ["status"] == "INCONCLUSIVE"                          # 24 units < 100
    assert summ["per_region"]["B"]["median_ratio_snpp_over_noaa20"] == pytest.approx(100 / 150)


def test_run_c1_on_synthetic_regions():
    agg = make_agg(entity_id="R1", etype="REGION", first=(2018, 1), last=(2024, 4), witnesses=("SNPP_VIIRS", "NOAA20_VIIRS"))
    out = v.run_c1(agg, {("REGION", "R1"): 1})
    assert out["official"]["units"] == 48 and out["official"]["agree"]["share"] == 1.0
    assert out["out_of_sample_both"]["units"] == 28                   # 2022-01 to 2024-04
    assert out["first_noaa20_estimate_month"] == "2018-01"            # synthetic: no gap before 2018-04
    shifted = make_agg(entity_id="R1", etype="REGION", first=(2018, 1), last=(2021, 12), witnesses=("SNPP_VIIRS", "NOAA20_VIIRS"), per_witness={"NOAA20_VIIRS": 2000.0})
    assert v.run_c1(shifted, {("REGION", "R1"): 1})["official"]["agree"]["share"] == 0.0


# --------------------------------------------------------------------------------------------------- CTRL
def base_table(p25=10.0, p50=20.0, p75=30.0, n_years=20):
    return pd.DataFrame([{"entity_type": "CUSTOM", "entity_id": "C8", "month": m, "n_years": n_years, "p25": p25, "p50": p50, "p75": p75} for m in range(1, 13)])


def rec_series(values, year=2012, sd=1.0):
    return pd.DataFrame([{"year": year + (i // 12), "month": i % 12 + 1, "estimate": x, "sd": sd} for i, x in enumerate(values)])


def test_judge_known_verdicts_by_hand():
    recs = rec_series([100.0, 5.0, 20.0, 0.0, np.nan, 20.0])
    out = v.judge(recs, base_table(), {(2012, 4): 0.0})
    assert list(out.verdict[:3]) == ["ABOVE_NORMAL", "BELOW_NORMAL", "WITHIN_NORMAL"]
    assert out.verdict[4] == "CANNOT_DETERMINE" and out.reason[4] == "OUTAGE"
    assert out.verdict[3] == "BELOW_NORMAL"                           # estimate 0 but p75 = 30 > 1: not NO_DETECTED_ACTIVITY
    none = v.judge(recs, base_table(n_years=14), {})
    assert set(none.verdict) == {"CANNOT_DETERMINE"} and set(none.reason) == {"OUTAGE", "INSUFFICIENT_BASELINE"}
    quiet = v.judge(rec_series([0.0]), base_table(p25=0.0, p50=0.5, p75=0.9), {})
    assert quiet.verdict[0] == "NO_DETECTED_ACTIVITY"
    raw_seen = v.judge(rec_series([0.0]), base_table(p25=0.0, p50=0.5, p75=0.9), {(2012, 1): 4.0})       # amendment A: something was detected
    assert raw_seen.verdict[0] == "CANNOT_DETERMINE"


def test_eval_months_are_25_around_each_date():
    m = v.eval_months()
    assert list(m) == ["2012-01", "2018-04"] and all(len(x) == 25 for x in m.values())
    assert v.label(m["2012-01"][0]) == "2011-01" and v.label(m["2012-01"][-1]) == "2013-01"
    assert v.label(m["2018-04"][0]) == "2017-04" and v.label(m["2018-04"][-1]) == "2019-04"


def test_ctrl_compare_spurious_logic():
    def verdicts(vs, year=2011):
        return pd.DataFrame([{"year": year + i // 12, "month": i % 12 + 1, "estimate": 1.0, "verdict": x} for i, x in enumerate(vs)])
    months = {"2012-01": list(range(v.midx(2011, 1), v.midx(2011, 1) + 6))}
    harm = verdicts(["ABOVE_NORMAL", "ABOVE_NORMAL", "BELOW_NORMAL", "WITHIN_NORMAL", "CANNOT_DETERMINE", "BELOW_NORMAL"])
    aqua = verdicts(["ABOVE_NORMAL", "WITHIN_NORMAL", "ABOVE_NORMAL", "ABOVE_NORMAL", "BELOW_NORMAL", "BELOW_NORMAL"])
    res = v.ctrl_compare(harm, aqua, months)
    # month 1 shared ABOVE (not spurious); month 2 harmonized ABOVE, Aqua WITHIN (spurious); month 3 BELOW vs ABOVE (spurious, a different verdict);
    # month 4 harmonized WITHIN (never spurious); month 5 CANNOT_DETERMINE (never spurious); month 6 shared BELOW
    assert [s["month"] for s in res["spurious"]] == ["2011-02", "2011-03"] and res["spurious_total"] == 2
    assert res["determinable_harmonized"] == 5
    assert res["per_date"]["2012-01"]["harmonized_verdicts"]["ABOVE_NORMAL"] == 2
    miss = v.ctrl_compare(harm, aqua.iloc[:5], months)                # Aqua-only has no record for month 6: its verdict is absent
    assert miss["spurious_total"] == 3


def test_ctrl_status_logic():
    assert v.ctrl_status(1, 100) == "FAIL" and v.ctrl_status(0, 12) == "PASS" and v.ctrl_status(0, 11) == "INCONCLUSIVE"


def test_run_ctrl_synthetic_world_agrees_and_a_planted_step_is_spurious():
    wave = lambda y, m: 0.5 + 0.5 * (y % 4)                  # 0.5, 1, 1.5, 2: a different level every year, so that a baseline has a spread
    agg = make_agg(entity_id="C8", etype="CUSTOM", first=(2003, 1), last=(2022, 12), e=1000.0, scale=wave)
    ctrl = v.run_ctrl(agg, {("CUSTOM", "C8"): 4})
    assert ctrl["official"]["spurious_total"] == 0 and ctrl["official"]["status"] == "PASS"       # flat world, identical witnesses
    assert ctrl["official"]["determinable_harmonized"] >= v.CTRL_MIN_DETERMINABLE
    # Aqua misses the months of 2012 (incomplete) and the VIIRS witnesses read 20 times too high there: the harmonized series says ABOVE_NORMAL,
    # the Aqua-only series has no estimate (an outage), so the verdict is absent from it
    step = agg.copy()
    in_2012 = step.year == 2012
    step.loc[in_2012 & (step.witness == "AQUA_MODIS"), "complete"] = False
    for c in ("raw", "e", "vc"):
        step.loc[in_2012 & (step.witness != "AQUA_MODIS"), c] = step.loc[in_2012 & (step.witness != "AQUA_MODIS"), c] * 20.0
    ctrl2 = v.run_ctrl(step, {("CUSTOM", "C8"): 4})
    assert ctrl2["official"]["spurious_total"] >= 1 and ctrl2["official"]["status"] == "FAIL"
    assert {s["harmonized"] for s in ctrl2["official"]["spurious"]} <= {"ABOVE_NORMAL", "BELOW_NORMAL"}


# --------------------------------------------------------------------------------------------------- entries
def test_entries_have_the_contract_shape(tmp_path, monkeypatch):
    regions = make_agg(entity_id="R1", etype="REGION", first=(2012, 1), last=(2024, 4))
    cells = make_agg(entity_id="c1", etype="CELL", first=(2012, 1), last=(2021, 12))
    box = make_agg(entity_id="C8", etype="CUSTOM", first=(2003, 1), last=(2022, 12))
    n = {("REGION", "R1"): 1, ("CELL", "c1"): 1}
    b2 = v.run_b2(regions, cells, n, seed=2, n_by_type={"REGION": 5, "CELL": 5})
    c1 = v.run_c1(regions, n)
    ctrl = v.run_ctrl(box, {("CUSTOM", "C8"): 4})
    entries = v.build_entries(json.loads(json.dumps(b2, default=str)), json.loads(json.dumps(c1, default=str)), json.loads(json.dumps(ctrl, default=str)))
    ids = [e["test_id"] for e in entries]
    assert ids == ["B2", "B2-CODE-ONLY", "B2-FALSE-FLAG-MONTHLY", "C1", "C1-OVERLAP", "C1-OUT-OF-SAMPLE-2022-2024", "CTRL", "CTRL-SHARED-BASELINE"]
    for e in entries:
        assert set(e) == {"test_id", "family", "title", "case", "criterion", "threshold", "measured", "status", "notes"}
        assert e["status"] in v.STATUSES
        json.dumps(e)
    monkeypatch.setattr(v, "QA", tmp_path)
    path = v.write_outputs({"b2": b2, "c1": c1, "ctrl": ctrl})
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["synthetic"] is False and doc["contract_version"] == "0.1.1" and len(doc["tests"]) == 8
    assert (tmp_path / "T-024_b2_report.json").exists()
