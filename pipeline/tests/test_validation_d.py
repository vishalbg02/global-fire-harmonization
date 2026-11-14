"""Tests for pipeline/validation_d.py (T-022: validation tests D1 and D2) on SYNTHETIC data with answers known by hand.

    python -m pytest pipeline/tests/test_validation_d.py -q -p no:cacheprovider
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import harmonize as hz
import validation_d as vd

NO_CUTOFF = {"D": None, "N": None}


def units(entity, actual, pred, var, dn="D", year=2019):
    """D/N units of one entity: arrays of actual, predicted and variance (var_ours)."""
    return pd.DataFrame({"entity_type": "REGION", "entity_id": entity, "year": year, "month": 1, "daynight": dn,
                         "actual": np.asarray(actual, float), "pred_ours": np.asarray(pred, float),
                         "var_ours": np.asarray(var, float)})


# ------------------------------------------------------------------------------------------------ D1: counting and status
def test_coverage_pair_counts_planted_intervals():
    # sd 10 -> half width 16.45; errors 0, 10, 16, 17, 30 -> 3 of 5 inside the 90% interval
    x = units("A", [100, 110, 116, 117, 130], [100] * 5, [100.0] * 5)
    p = vd.coverage_pair(x)
    assert p["units"] == 5 and p["coverage_90"] == pytest.approx(0.6)
    # 50% half width 0.6745 x 10 = 6.745 -> only the error 0 is inside
    assert p["coverage_50"] == pytest.approx(0.2)


def test_coverage_pair_empty():
    p = vd.coverage_pair(units("A", [], [], []))
    assert p["units"] == 0 and p["coverage_90"] is None


@pytest.mark.parametrize("cov, expected", [(0.80, "PASS"), (0.7999, "FAIL"), (0.97, "PASS"), (0.9701, "FAIL"), (0.90, "PASS"),
                                           (0.0, "FAIL"), (1.0, "FAIL")])
def test_status_boundaries_are_inclusive(cov, expected):
    assert vd.status_from_coverage(cov, units=100) == expected


def test_status_inconclusive_without_units_or_value():
    assert vd.status_from_coverage(None, 10) == "INCONCLUSIVE"
    assert vd.status_from_coverage(float("nan"), 10) == "INCONCLUSIVE"
    assert vd.status_from_coverage(0.9, units=29, min_units=30) == "INCONCLUSIVE"
    assert vd.status_from_coverage(0.9, units=30, min_units=30) == "PASS"


def test_exactly_eighty_percent_of_planted_units_passes():
    x = units("A", [100] * 4 + [1000], [100] * 5, [100.0] * 5)      # 4 of 5 inside = 0.8 exactly
    c = vd.coverage_pair(x)["coverage_90"]
    assert c == 0.8 and vd.status_from_coverage(c, 5) == "PASS"


def test_exactly_ninety_seven_percent_of_planted_units_passes():
    x = units("A", [100] * 97 + [1000] * 3, [100] * 100, [100.0] * 100)
    c = vd.coverage_pair(x)["coverage_90"]
    assert c == pytest.approx(0.97) and vd.status_from_coverage(c, 100) == "PASS"


# ------------------------------------------------------------------------------------------------ D1: pooled against per region
def planted_two_regions():
    """Region A: 40 units, all inside (coverage 1.0). Region B: 40 units, 28 inside (0.70). Pooled: 68 / 80 = 0.85."""
    a = units("A", [100] * 40, [100] * 40, [100.0] * 40)
    b = units("B", [100] * 28 + [1000] * 12, [100] * 40, [100.0] * 40)
    return pd.concat([a, b], ignore_index=True)


def test_pooled_passes_while_one_region_is_below_target():
    u = planted_two_regions()
    lvl = vd.d1_level(u, u.assign(daynight="T"))
    assert lvl["pooled"]["coverage_90"] == pytest.approx(0.85) and lvl["pooled"]["status"] == "PASS"
    assert lvl["by_group_daynight_units"]["A"]["status"] == "FAIL"        # 1.0 is above 0.97
    assert lvl["by_group_daynight_units"]["B"]["coverage_90"] == pytest.approx(0.70)
    assert lvl["by_group_daynight_units"]["B"]["status"] == "FAIL"
    ins = lvl["inside_daynight_units"]
    assert (ins["judged"], ins["inside"], ins["outside"]) == (2, 0, ["A", "B"])


def test_small_regions_are_not_judged_on_their_own():
    u = pd.concat([planted_two_regions(), units("C", [1000] * 5, [100] * 5, [100.0] * 5)], ignore_index=True)
    per = vd.by_region(u)
    assert per["C"]["status"] == "INCONCLUSIVE" and per["C"]["units"] == 5
    assert vd.regions_inside(per)["judged"] == 2


def test_night_units_alone_are_reported_and_can_fail_while_pooled_passes():
    day = units("A", [100] * 60, [100] * 60, [100.0] * 60, dn="D")
    night = units("A", [100] * 12 + [1000] * 8, [100] * 20, [100.0] * 20, dn="N")           # 12/20 = 0.60
    u = pd.concat([day, night], ignore_index=True)
    lvl = vd.d1_level(u, u.assign(daynight="T"))
    assert lvl["pooled"]["coverage_90"] == pytest.approx(72 / 80) and lvl["pooled"]["status"] == "PASS"
    assert lvl["by_daynight"]["N"]["coverage_90"] == pytest.approx(0.6) and lvl["by_daynight"]["N"]["status"] == "FAIL"
    assert lvl["by_daynight"]["D"]["status"] == "FAIL"                    # all 60 inside = 1.0, above 0.97


def level_with(inside_a, inside_b):
    """Two regions of 40 units each with `inside_a` and `inside_b` units inside their interval."""
    a = units("A", [100] * inside_a + [1000] * (40 - inside_a), [100] * 40, [100.0] * 40)
    b = units("B", [100] * inside_b + [1000] * (40 - inside_b), [100] * 40, [100.0] * 40)
    u = pd.concat([a, b], ignore_index=True)
    return vd.d1_level(u, u.assign(daynight="T"))


def test_entries_use_the_pooled_status_and_the_strict_reading_separately():
    r = level_with(38, 26)                       # A 0.95, B 0.65, pooled 64 / 80 = 0.80 exactly
    e = {x["test_id"]: x for x in vd.d1_entries(r, r)}
    assert e["D1-REGIONS"]["status"] == "PASS" and e["D1-REGIONS-EACH"]["status"] == "FAIL"
    assert e["D1-REGIONS-EACH"]["measured"]["regions_outside"] == ["B"]
    assert e["D1-REGIONS"]["threshold"].startswith("between 80% and 97%")
    for x in e.values():
        assert set(x) == {"test_id", "family", "title", "case", "criterion", "threshold", "measured", "status", "notes"}
        assert x["status"] in ("PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN")
    bad = level_with(20, 20)                     # pooled 0.5
    assert {x["test_id"]: x for x in vd.d1_entries(bad, bad)}["D1-REGIONS"]["status"] == "FAIL"
    good = level_with(35, 35)                    # both 0.875
    g = {x["test_id"]: x for x in vd.d1_entries(good, good)}
    assert g["D1-REGIONS"]["status"] == "PASS" and g["D1-REGIONS-EACH"]["status"] == "PASS"


def test_widening_factor_is_reported_not_applied():
    r = level_with(35, 35)
    e = vd.d1_entries(r, r, widening={"c_for_90": 1.26, "applied": False})[0]
    assert e["measured"]["widening_factor_reported_not_applied"]["applied"] is False
    assert e["measured"]["coverage_90"] == r["pooled"]["coverage_90"]       # coverage without c


def test_d1_is_reproducible():
    u = planted_two_regions()
    assert vd.d1_level(u, u.assign(daynight="T")) == vd.d1_level(u.copy(), u.assign(daynight="T"))


# ------------------------------------------------------------------------------------------------ D2: estimate level
def rows(entity, year, month, dn, witness, e, complete=True, ratio=1.0):
    return {"entity_type": "COUNTRY", "entity_id": entity, "entity_name": entity, "year": year, "month": month, "daynight": dn,
            "witness": witness, "raw": e / ratio, "complete": complete, "lo": "SP", "hi": "SP", "e": float(e), "vc": float(e) * ratio,
            "vr": 0.0, "rbar": ratio, "missing": 0}


def month(entity, year, mo, aqua_ok=True, snpp_ok=True, aqua=100.0, snpp=105.0):
    out = []
    for dn in ("D", "N"):
        out.append(rows(entity, year, mo, dn, "AQUA_MODIS", aqua, aqua_ok))
        out.append(rows(entity, year, mo, dn, "SNPP_VIIRS", snpp, snpp_ok))
    return out


def planted_agg():
    r = []
    r += month("AAA", 2019, 1)                                    # both complete
    r += month("AAA", 2019, 2, aqua_ok=False)                     # Aqua partial, S-NPP complete -> estimate from S-NPP only
    r += month("AAA", 2019, 3, aqua_ok=False, snpp_ok=False)      # outage: nobody complete -> no estimate
    r += month("AAA", 2019, 4, snpp_ok=False, snpp=5000.0)        # S-NPP partial (absurd value) -> Aqua only
    return pd.DataFrame(r)


def recs_of(agg):
    return hz.records_from(agg, {("COUNTRY", "AAA"): 4}, NO_CUTOFF)


def test_outage_month_has_no_estimate_and_partial_witness_is_not_used():
    agg = planted_agg()
    recs = {r["month"]: r for r in recs_of(agg)}
    assert recs[3]["estimate"] is None and recs[3]["n_witnesses"] == 0
    assert recs[2]["witnesses_used"] == ["SNPP_VIIRS"] and recs[2]["estimate"] == pytest.approx(210.0)
    assert recs[4]["witnesses_used"] == ["AQUA_MODIS"] and recs[4]["estimate"] == pytest.approx(200.0)   # the 5000 is not used
    assert recs[1]["n_witnesses"] == 2


def test_check_estimates_passes_on_the_real_rules():
    agg = planted_agg()
    chk = vd.check_estimates(agg, recs_of(agg), NO_CUTOFF)
    assert chk["entity_months"] == 4 and chk["months_expected_without_estimate"] == 1 and chk["months_with_a_partial_witness"] == 3
    assert chk["violations"] == 0
    pert = vd.perturbation_check(agg, {("COUNTRY", "AAA"): 4}, NO_CUTOFF)
    assert pert["entity_months_with_incomplete_row"] == 3 and pert["changed"] == 0 and pert["without_estimate"] == 1
    assert vd.d2_estimate_status(chk, pert) == "PASS"


def test_check_estimates_catches_an_estimate_in_an_outage_month():
    agg = planted_agg()
    recs = recs_of(agg)
    for r in recs:
        if r["month"] == 3:
            r.update(estimate=100.0, sd=10.0, n_witnesses=1, witnesses_used=["AQUA_MODIS"])      # planted bad: an estimate from a partial witness
    chk = vd.check_estimates(agg, recs, NO_CUTOFF)
    assert chk["estimate_without_usable_witness"] == 1 and chk["violations"] >= 1
    assert chk["uses_witness_without_complete_month"] == 1
    assert vd.d2_estimate_status(chk, {"changed": 0}) == "FAIL"


def test_check_estimates_catches_a_dropped_good_month():
    agg = planted_agg()
    recs = recs_of(agg)
    for r in recs:
        if r["month"] == 1:
            r.update(estimate=None, witnesses_used=[], n_witnesses=0)
    chk = vd.check_estimates(agg, recs, NO_CUTOFF)
    assert chk["missing_estimate_despite_usable_witness"] == 1
    assert vd.d2_estimate_status(chk, {"changed": 0}) == "FAIL"


def test_perturbation_check_detects_a_method_that_uses_partial_rows(monkeypatch):
    agg = planted_agg()
    real = hz.records_from

    def leaky(a, n_cells, aqua_from=None, *args, **kw):
        return real(a.assign(complete=True), n_cells, aqua_from, *args, **kw)      # a method that ignores the completeness flag
    monkeypatch.setattr(hz, "records_from", leaky)
    pert = vd.perturbation_check(agg, {("COUNTRY", "AAA"): 4}, NO_CUTOFF)
    assert pert["changed"] > 0


def test_aqua_night_cutoff_part_is_not_counted_as_usable():
    agg = pd.DataFrame(month("AAA", 2024, 6, snpp_ok=False))        # S-NPP partial; Aqua complete but its night part is excluded (D-005)
    recs = hz.records_from(agg, {("COUNTRY", "AAA"): 4})            # default cutoff: Aqua night from 2024-05
    chk = vd.check_estimates(agg, recs)
    assert recs[0]["estimate"] is None and chk["months_expected_without_estimate"] == 1 and chk["violations"] == 0


def test_estimate_check_is_reproducible():
    agg = planted_agg()
    assert vd.check_estimates(agg, recs_of(agg), NO_CUTOFF) == vd.check_estimates(agg.copy(), recs_of(agg.copy()), NO_CUTOFF)


def test_d2_estimate_inconclusive_when_no_gap_was_tested():
    agg = pd.DataFrame(month("AAA", 2019, 1))
    chk = vd.check_estimates(agg, recs_of(agg), NO_CUTOFF)
    assert vd.d2_estimate_status(chk, {"changed": 0}) == "INCONCLUSIVE"


# ------------------------------------------------------------------------------------------------ D2: verdict level
def em_table(rows_):
    return pd.DataFrame(rows_, columns=["estimate", "verdict", "reason_codes"])


GOOD = [(120.0, "ABOVE_NORMAL", []), (80.0, "WITHIN_NORMAL", ["SINGLE_WITNESS"]), (None, "CANNOT_DETERMINE", ["OUTAGE"]),
        (50.0, "CANNOT_DETERMINE", ["INSUFFICIENT_BASELINE"]), (0.0, "NO_DETECTED_ACTIVITY", []), (None, "CANNOT_DETERMINE", ["OUTAGE"])]


def test_verdict_check_passes_a_planted_good_table():
    res = vd.check_verdicts(em_table(GOOD))
    assert res["rows"] == 6 and res["rows_without_estimate"] == 2 and res["outage_rows_ok"] == 2
    assert sum(res["violations"].values()) == 0
    assert res["determinable_rows"] == 3 and res["determinable_share"] == pytest.approx(0.5)
    assert vd.d2_verdict_status(res) == "PASS"


@pytest.mark.parametrize("bad_row, key", [
    ((None, "WITHIN_NORMAL", []), "no_estimate_but_not_cannot_determine_outage"),
    ((None, "CANNOT_DETERMINE", []), "no_estimate_but_not_cannot_determine_outage"),
    ((None, "CANNOT_DETERMINE", ["INSUFFICIENT_BASELINE"]), "no_estimate_but_not_cannot_determine_outage"),
    ((90.0, "CANNOT_DETERMINE", ["OUTAGE"]), "outage_code_with_an_estimate"),
    ((90.0, "ABOVE_NORMAL", ["INSUFFICIENT_BASELINE"]), "insufficient_or_wide_but_determinable"),
    ((90.0, "WITHIN_NORMAL", ["WIDE_INTERVAL"]), "insufficient_or_wide_but_determinable"),
    ((7.0, "NO_DETECTED_ACTIVITY", []), "no_detected_activity_without_zero_estimate"),
])
def test_verdict_check_fails_each_planted_bad_row(bad_row, key):
    res = vd.check_verdicts(em_table([*GOOD, bad_row]))
    assert res["violations"][key] >= 1
    assert vd.d2_verdict_status(res) == "FAIL"


def test_verdict_check_reads_json_string_codes_and_is_reproducible():
    t = em_table([(None, "CANNOT_DETERMINE", '["OUTAGE"]'), (10.0, "WITHIN_NORMAL", "[]")])
    assert vd.check_verdicts(t) == vd.check_verdicts(t.copy())
    assert vd.d2_verdict_status(vd.check_verdicts(t)) == "PASS"


def test_verdict_check_inconclusive_without_outage_rows():
    res = vd.check_verdicts(em_table([(10.0, "WITHIN_NORMAL", [])]))
    assert vd.d2_verdict_status(res) == "INCONCLUSIVE"


def test_verdict_level_is_not_run_until_a_table_exists():
    agg = planted_agg()
    chk = vd.check_estimates(agg, recs_of(agg), NO_CUTOFF)
    e = {x["test_id"]: x for x in vd.d2_entries(chk, {"changed": 0})}
    assert e["D2-VERDICTS"]["status"] == "NOT_RUN" and e["D2-ESTIMATES"]["status"] == "PASS"
    e2 = {x["test_id"]: x for x in vd.d2_entries(chk, {"changed": 0}, vd.check_verdicts(em_table(GOOD)))}
    assert e2["D2-VERDICTS"]["status"] == "PASS"


def cell_files(tmp_path, bad=False):
    cells = pd.DataFrame({"cell_id": ["c1", "c2", "c3"], "country_iso3": ["AAA", "AAA", None]})
    cmw = pd.DataFrame({
        "cell_id": ["c1", "c1", "c1", "c2", "c2", "c2", "c3", "c3"],
        "estimate": [10.0, 5.0, None, 0.0, 0.0, 0.0, 0.0, None],
        "verdict": ["ABOVE_NORMAL", "CANNOT_DETERMINE", "CANNOT_DETERMINE", "NO_DETECTED_ACTIVITY", "NO_DETECTED_ACTIVITY",
                    "NO_DETECTED_ACTIVITY", "NO_DETECTED_ACTIVITY", "CANNOT_DETERMINE"],
        "reason_codes": [[], ["INSUFFICIENT_BASELINE"], ["OUTAGE"], [], [], [], [], [] if bad else ["OUTAGE"]]})
    cells.to_parquet(tmp_path / "cells.parquet")
    cmw.to_parquet(tmp_path / "h.parquet")
    return tmp_path / "h.parquet", tmp_path / "cells.parquet"


def test_cell_determinable_shares_by_hand(tmp_path):
    out = vd.cell_determinable_shares(*cell_files(tmp_path))
    land, allc = out["land"], out["all"]
    assert (land["cells"], land["cell_months"], allc["cells"], allc["cell_months"]) == (2, 6, 3, 8)
    assert land["cell_months_normal_share"] == pytest.approx(1 / 6)           # one ABOVE_NORMAL
    assert land["cell_months_not_cannot_determine_share"] == pytest.approx(4 / 6)
    assert land["cells_with_any_normal_verdict"] == pytest.approx(0.5) and land["cells_with_any_not_cd_verdict"] == 1.0
    assert allc["cell_months_not_cannot_determine_share"] == pytest.approx(5 / 8)
    assert land["cell_months_without_estimate"] == 1 and out["all"]["outage_rule_violations"] == 0


def test_cell_outage_rule_violation_is_counted(tmp_path):
    out = vd.cell_determinable_shares(*cell_files(tmp_path, bad=True))
    assert out["all"]["outage_rule_violations"] == 1 and out["land"]["outage_rule_violations"] == 0
    res = vd.check_verdicts(em_table(GOOD))
    res["cell_level"] = out
    assert vd.d2_verdict_status(res) == "FAIL"


def test_d2_overall_needs_both_halves():
    p, f, n = {"status": "PASS"}, {"status": "FAIL"}, {"status": "NOT_RUN"}
    assert vd.d2_overall(p, p)["status"] == "PASS"
    assert vd.d2_overall(p, f)["status"] == "FAIL" and vd.d2_overall(f, p)["status"] == "FAIL"
    assert vd.d2_overall(p, n)["status"] == "NOT_RUN"
