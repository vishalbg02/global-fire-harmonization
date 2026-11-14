"""Tests for pipeline/validation_integrate.py on SYNTHETIC entries (the checks, the order, the NOT_RUN entries).

    python -m pytest pipeline/tests/test_validation_integrate.py -q
"""
from __future__ import annotations

import copy
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import validation_integrate as vi


def entry(test_id: str, status: str = "PASS", measured=None, notes: str = "ok") -> dict:
    return {"test_id": test_id, "family": test_id[0], "title": "t", "case": "c", "criterion": "x", "threshold": "y",
            "measured": {"v": 1} if measured is None else measured, "status": status, "notes": notes}


def all_entries() -> list[dict]:
    ids = ["A1-C1", "A1-FAMILY", "B1-2012-01", "B1", "B3-DRIFT", "B3", "D1-REGIONS", "D1-NIGHT", "D2-ESTIMATES", "D2", "E1", "S1-BASELINE", "S1"]
    return [entry(i) for i in ids]


def doc_of(entries: list[dict]) -> dict:
    return {"contract_version": "0.1.1", "method_version": "0.1.0", "generated_at": "2026-11-15T00:00:00Z", "synthetic": False,
            "tests": vi.merge(entries)}


def test_the_plan_test_of_an_entry_is_the_part_before_the_first_dash():
    assert [vi.plan_test(x) for x in ("A1-C3", "A1-FAMILY", "B1-2012-01", "S1-BASELINE", "D2", "CTRL")] == ["A1", "A1", "B1", "S1", "D2", "CTRL"]


def test_merge_orders_by_plan_keeps_harness_order_and_adds_the_four_not_run_tests():
    out = vi.merge(list(reversed(all_entries())))
    plan = [vi.plan_test(t["test_id"]) for t in out]
    assert [p for i, p in enumerate(plan) if i == 0 or p != plan[i - 1]] == list(vi.PLAN_ORDER)
    assert {t["test_id"]: t["status"] for t in out if t["status"] == "NOT_RUN"} == {"A2": "NOT_RUN", "B2": "NOT_RUN", "C1": "NOT_RUN", "CTRL": "NOT_RUN"}
    assert all(t["measured"] == {} for t in out if t["status"] == "NOT_RUN")


def test_a_complete_merged_document_passes_the_checks():
    assert vi.check(doc_of(all_entries())) == []


def test_an_entry_of_an_unknown_test_is_an_error():
    with pytest.raises(ValueError, match="belongs to no test"):
        vi.merge([*all_entries(), entry("Z9")])


def test_a_missing_plan_test_is_reported():
    d = doc_of(all_entries())
    d["tests"] = [t for t in d["tests"] if vi.plan_test(t["test_id"]) != "E1"]
    assert "plan test E1 has no entry" in vi.check(d)


def test_a_duplicate_id_a_bad_status_a_missing_field_and_a_not_run_with_numbers_each_fail():
    d = doc_of(all_entries())
    dup = copy.deepcopy(d)
    dup["tests"].append(copy.deepcopy(dup["tests"][0]))
    assert any("duplicate test_id" in p for p in vi.check(dup))
    bad = copy.deepcopy(d)
    bad["tests"][0]["status"] = "MAYBE"
    assert any("is not one of" in p for p in vi.check(bad))
    miss = copy.deepcopy(d)
    del miss["tests"][1]["criterion"]
    assert any("missing fields" in p for p in vi.check(miss))
    nr = copy.deepcopy(d)
    nr["tests"][[t["test_id"] for t in nr["tests"]].index("A2")]["measured"] = {"pct": 120.0}
    assert any("NOT_RUN entry must carry no measured numbers" in p for p in vi.check(nr))


def test_a_fail_or_not_run_entry_needs_a_note_and_a_synthetic_document_is_refused():
    d = doc_of([*all_entries()[:-1], entry("S1", "FAIL", notes="")])
    assert any("needs a note" in p for p in vi.check(d))
    s = doc_of(all_entries())
    s["synthetic"] = True
    assert "synthetic must be false" in vi.check(s)


def test_the_not_run_texts_come_from_the_plan_and_say_who_would_run_them():
    for p in ("A2", "B2", "C1", "CTRL"):
        e = vi.not_run_entry(p)
        assert e["status"] == "NOT_RUN" and "not assigned" in e["notes"] and e["measured"] == {} and e["test_id"] == p


def test_build_reads_the_files_and_the_product_metadata_and_a_missing_file_is_an_error(tmp_path):
    qa, products = tmp_path / "qa", tmp_path / "products"
    qa.mkdir()
    products.mkdir()
    (products / "metadata.json").write_text(json.dumps({"contract_version": "0.1.1", "method_version": "0.1.0"}), encoding="utf-8")
    ents = all_entries()
    split = {"T-020_validation_entries.json": ents[:2], "T-021_validation_entries.json": ents[2:6],
             "T-022_validation_entries.json": ents[6:10], "T-025_validation_entries.json": ents[10:]}
    for name, tests in split.items():
        (qa / name).write_text(json.dumps({"contract_version": "0.1.1", "method_version": "x", "synthetic": False, "tests": tests}), encoding="utf-8")
    d = vi.build(qa, products, now=datetime(2026, 11, 15, 3, 0, tzinfo=UTC))
    assert d["method_version"] == "0.1.0" and d["generated_at"] == "2026-11-15T03:00:00Z" and vi.check(d) == []
    (qa / "T-025_validation_entries.json").unlink()
    with pytest.raises(FileNotFoundError):
        vi.build(qa, products)


TABLE = """| Test | Expected | Actual | Status | Run date | Notes |
|---|---|---|---|---|---|
| A1 | x | 0 of 6 | **FAIL** | 2026-11-15 | |
| A2 | x | — | NOT_RUN | — | |
| B1 | x | 13 of 14 | PASS | 2026-11-15 | |
| B2 | x | — | NOT_RUN | — | |
| B3 | x | ok | PASS | 2026-11-15 | |
| C1 | x | — | NOT_RUN | — | |
| CTRL | x | — | NOT_RUN | — | |
| D1 | x | 0.818 | PASS | 2026-11-15 | |
| D2 | x | ok | PASS | 2026-11-15 | |
| E1 | x | 14 of 14 | PASS | 2026-11-15 | |
| S1 | x | — | NOT_RUN | — | |
"""


def results_doc() -> dict:
    status = {"A1-FAMILY": "FAIL", "B1": "PASS", "B3": "PASS", "D1-REGIONS": "PASS", "D2": "PASS", "E1": "PASS", "S1": "NOT_RUN"}
    tests = [entry(i, s, notes="why") for i, s in status.items()]
    return {"contract_version": "0.1.1", "method_version": "0.1.0", "generated_at": "x", "synthetic": False, "tests": vi.merge(tests)}


def test_the_headline_status_of_each_plan_test_is_the_family_pooled_or_overall_entry():
    got = vi.plan_statuses(results_doc())
    assert got["A1"] == "FAIL" and got["D1"] == "PASS" and got["S1"] == "NOT_RUN" and got["A2"] == "NOT_RUN" and len(got) == 11


def test_a_plan_table_that_matches_the_results_has_no_problems():
    assert vi.check_plan_table(TABLE, results_doc()) == []


def test_a_wrong_status_a_missing_run_date_a_not_run_with_a_result_and_a_missing_row_are_found():
    d = results_doc()
    assert any("section 4 shows 'PASS'" in p for p in vi.check_plan_table(TABLE.replace("**FAIL**", "PASS"), d))
    assert any("no run date" in p for p in vi.check_plan_table(TABLE.replace("| 14 of 14 | PASS | 2026-11-15 |", "| 14 of 14 | PASS | — |"), d))
    assert any("must not show an actual result" in p for p in vi.check_plan_table(TABLE.replace("| A2 | x | — |", "| A2 | x | 50% |"), d))
    assert any("no row in section 4" in p for p in vi.check_plan_table(chr(10).join(x for x in TABLE.splitlines() if not x.startswith("| E1")), d))
