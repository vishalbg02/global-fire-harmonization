"""Tests for pipeline/number_check.py on SYNTHETIC values with known answers (T-026).

    python -m pytest pipeline/tests/test_number_check.py -q
"""
from __future__ import annotations

import csv
import io
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import number_check as nc

NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed")


def test_javascript_rounding_is_half_up_and_exact():
    assert [nc.js_round(x) for x in (0.5, 1.5, 2.5, 264.5, -0.5, -1.5, -2.5, 0.49999999999999994, 0.0, 99.4999)] == [1, 2, 3, 265, 0, -1, -2, 0, 0, 99]


def test_to_fixed_rounds_the_exact_binary_value_half_up_on_the_magnitude():
    assert nc.js_to_fixed(0.25, 1) == "0.3"            # an exact tie goes to the larger number
    assert nc.js_to_fixed(1.45, 1) == "1.4"            # 1.45 is stored a little below
    assert nc.js_to_fixed(2.5, 0) == "3" and nc.js_to_fixed(-2.5, 0) == "-3"
    assert nc.js_to_fixed(12.34, 1) == "12.3" and nc.js_to_fixed(0.0, 1) == "0.0" and nc.js_to_fixed(1e21 / 1e20, 1) == "10.0"


@needs_node
def test_the_python_port_equals_javascript_on_many_values():
    values = [0.25, 0.35, 1.45, 2.5, 264.5, 0.05, 0.15, 0.995, 0.005, 1234.55, 8.345, 0.1 + 0.2, 99.95, 5e-324, 123456.789, -0.5, 3.0000001]
    values += [i / 20 for i in range(400)] + [i / 8 for i in range(200)]
    code = ("const v = JSON.parse(process.argv[1]); console.log(JSON.stringify(v.map(x => [Math.round(x), x.toFixed(1)])))")
    out = json.loads(subprocess.run([NODE, "-e", code, json.dumps(values)], capture_output=True, text=True, check=True).stdout)
    for x, (r, f) in zip(values, out, strict=True):
        assert nc.js_round(x) == r, x
        assert nc.js_to_fixed(x, 1) == f, x


def test_probability_wording_thresholds():
    assert nc.fmt_probability(0.995) == "more than 99%" and nc.fmt_probability(0.9949999999) == "99%"
    assert nc.fmt_probability(0.9999999999999996) == "more than 99%" and nc.fmt_probability(1.0) == "more than 99%"
    assert nc.fmt_probability(0.005) == "less than 1%" and nc.fmt_probability(0.0050001) == "1%" and nc.fmt_probability(0.0) == "less than 1%"
    assert nc.fmt_probability(0.824) == "82%" and nc.fmt_probability(0.5) == "50%"


def test_texts_of_the_inventory_by_hand():
    assert nc.fmt_pct(264.8615747270596) == "265% of normal" and nc.fmt_pct(None) == "no data" and nc.fmt_pct(0.0) == "0% of normal"
    assert nc.fmt_estimate(19068.709072474652, 17320.2, 20817.2) == "19068.7 (90% interval 17320.2 to 20817.2)"
    assert nc.fmt_estimate(None, 1.0, 2.0) == "no data" and nc.fmt_estimate(5.0, None, 2.0) == "5.0 (interval not available)"
    assert nc.fmt_verdict_probability("ABOVE_NORMAL", 0.824, 0.0, 0.176) == "82% likely above normal"
    assert nc.fmt_verdict_probability("CANNOT_DETERMINE", 1.0, 0.0, 0.0) is None
    assert nc.fmt_verdict_probability("WITHIN_NORMAL", None, None, None) is None
    assert nc.fmt_anomaly_probability("BELOW_NORMAL", 0.0, 0.9) == "90% likely below normal"


def test_anomaly_order_by_score_then_distance_from_normal_then_id():
    def r(i, pa, pb, pct):
        return {"entity_type": "COUNTRY", "entity_id": i, "p_above": pa, "p_below": pb, "pct_of_normal": pct}
    rows = [r("B", 1.0, 0.0, 200.0), r("A", 1.0, 0.0, 200.0), r("C", 1.0, 0.0, 800.0), r("D", 0.0, 1.0, 10.0), r("E", 1.0, 0.0, None),
            r("F", 1.0, 0.0, 0.0), r("G", 0.9, 0.0, 5000.0), r("H", 1.0, 0.0, -5.0)]
    got = [x["entity_id"] for x in nc.anomaly_order(rows)]
    # score 1.0 first; distance: D |ln 0.1| = 2.30 and C |ln 8| = 2.08 and A, B |ln 2| = 0.69; missing, zero and negative last by id; then G
    assert got == ["D", "C", "A", "B", "E", "F", "H", "G"]


def test_a_planted_wrong_number_and_a_null_shown_as_zero_are_defects():
    rep = nc.Report()
    stored = {"estimate": 10.5, "ci90_low": None, "verdict": "X", "witnesses_used": ["A", "B"]}
    nc.compare_record(rep, "t", "v", {"estimate": 10.5, "ci90_low": None, "verdict": "X", "witnesses_used": ["A", "B"]}, stored, list(stored))
    assert rep.checks["t"]["mismatch"] == 0
    nc.compare_record(rep, "t", "v", {"estimate": 10.6, "ci90_low": 0, "verdict": "X", "witnesses_used": ["A"]}, stored, list(stored))
    assert rep.checks["t"]["mismatch"] == 3 and {m["field"] for m in rep.mismatches} == {"estimate", "ci90_low", "witnesses_used"}


def test_nan_in_the_product_is_a_null_and_numpy_values_compare_equal():
    assert nc.same(float("nan"), None) and nc.same(1, 1.0) and not nc.same(0, None) and not nc.same(0.0, None)


class FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content


def csv_bytes(rows: list[dict], columns: list[str]) -> bytes:
    buf = io.StringIO()
    buf.write("# data_status: REAL\n# area: COUNTRY IDN\n# method_version: 0.1.0\n# contract_version: 0.1.1\n# generated_at: x\n# citation: y\n")
    w = csv.DictWriter(buf, fieldnames=columns)
    w.writeheader()
    w.writerows(rows)
    return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")


def idn_frame() -> pd.DataFrame:
    rows = []
    for m in (1, 2):
        rows.append({"entity_type": "COUNTRY", "entity_id": "IDN", "entity_name": "Indonesia", "year": 2015, "month": m, "estimate": 12.5 + m,
                     "ci90_low": 10.0, "ci90_high": None, "sd": 1.0, "raw_combined_cell_days": 20 + m, "witnesses_used": ["AQUA_MODIS"], "n_witnesses": 1,
                     "disagreement_scale": None, "baseline_median": 9.0, "baseline_p25": 6.0, "baseline_p75": 12.0, "pct_of_normal": 150.0,
                     "p_above": 0.9, "p_below": 0.0, "p_within": 0.1, "verdict": "ABOVE_NORMAL", "reason_codes": ["SINGLE_WITNESS"], "data_level": "SP",
                     "method_version": "0.1.0", "n_cells": 3, "raw_by_witness": json.dumps({"AQUA_MODIS": 20 + m})})
    return pd.DataFrame(rows)


def csv_rows(em: pd.DataFrame) -> tuple[list[dict], list[str]]:
    cols = [c for c in nc.ENTITY_COLUMNS if c != "raw_by_witness"] + [f"raw_{w}" for w in nc.WITNESS_COLUMNS]
    out = []
    for r in em.to_dict(orient="records"):
        raw = json.loads(r["raw_by_witness"])
        row = {c: ("" if r.get(c) is None or (isinstance(r.get(c), float) and math.isnan(r[c])) else r[c]) for c in cols if c[4:] not in nc.WITNESS_COLUMNS}
        row["witnesses_used"], row["reason_codes"] = ";".join(r["witnesses_used"]), ";".join(r["reason_codes"])
        for w in nc.WITNESS_COLUMNS:
            row[f"raw_{w}"] = raw.get(w, "")
        out.append(row)
    return out, cols


class FakeApi:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def get(self, path: str, **params) -> FakeResponse:
        return FakeResponse(self.content)


def test_the_csv_check_accepts_the_stored_rows_and_catches_a_changed_cell_and_a_null_written_as_zero():
    em = idn_frame()
    rows, cols = csv_rows(em)
    rep = nc.Report()
    nc.check_csv(rep, FakeApi(csv_bytes(rows, cols)), em)
    assert sum(c["mismatch"] for c in rep.checks.values()) == 0 and rep.checks["D csv values"]["checked"] == 2 * len(cols)
    bad = [dict(r) for r in rows]
    bad[1]["estimate"] = 99.0
    bad[0]["ci90_high"] = 0
    rep2 = nc.Report()
    nc.check_csv(rep2, FakeApi(csv_bytes(bad, cols)), em)
    assert {(m["field"]) for m in rep2.mismatches} == {"estimate", "ci90_high"}


def test_the_csv_check_catches_a_missing_row_and_a_wrong_column_order():
    em = idn_frame()
    rows, cols = csv_rows(em)
    rep = nc.Report()
    nc.check_csv(rep, FakeApi(csv_bytes(rows[:1], cols)), em)
    assert rep.checks["D csv rows"]["mismatch"] == 1
    swapped = [*cols]
    swapped[5], swapped[6] = swapped[6], swapped[5]
    rep2 = nc.Report()
    nc.check_csv(rep2, FakeApi(csv_bytes(rows, swapped)), em)
    assert rep2.checks["D csv columns"]["mismatch"] == 1


@needs_node
def test_the_apps_own_functions_run_through_node_and_agree_with_the_port():
    out = nc.run_app({"probability": [0.9999999, 0.994, 0.005, 0.0051], "pct": [264.5, None],
                      "estimate": [{"estimate": 1.25, "ci90_low": 1.0, "ci90_high": 2.0}],
                      "verdictProbability": [{"verdict": "ABOVE_NORMAL", "p_above": 0.824, "p_below": 0.0, "p_within": 0.176}],
                      "statuses": [{"status": "FAIL"}, {"status": "PASS"}, {"status": "FAIL"}]})
    assert out["probability"] == ["more than 99%", "99%", "less than 1%", "1%"]
    assert out["pct"] == ["265% of normal", "no data"] and out["estimate"] == [nc.fmt_estimate(1.25, 1.0, 2.0)]
    assert out["verdictProbability"] == ["82% likely above normal"] and out["statuses"] == {"FAIL": 2, "INCONCLUSIVE": 0, "PASS": 1, "NOT_RUN": 0}
