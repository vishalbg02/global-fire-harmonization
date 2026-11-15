"""Merge the validation entries of the merged harnesses into `validation_results.json` (the integration PR).

The four harnesses (`validation_a1.py`, `validation_b.py`, `validation_d.py`, `validation_e1_s1.py`) each write an entries file under
`data/interim/qa/` in the shape of DATA_CONTRACT.md section 6. This module only collects, orders and checks them; it computes no
result. Plan tests that nobody has run (A2, B2, C1, CTRL) are written as `NOT_RUN` entries with no numbers, never left out.

    python pipeline/validation_integrate.py            # writes data/products/validation_results.json after the checks pass
    python pipeline/validation_integrate.py --check    # checks the file that is there
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "data" / "interim" / "qa"
PRODUCTS = ROOT / "data" / "products"
# Order matters: when two files carry the same test_id the later one wins (T-025b ran the half of S1 that T-025 recorded as NOT_RUN).
ENTRY_FILES = ("T-020_validation_entries.json", "T-021_validation_entries.json", "T-022_validation_entries.json",
               "T-023_validation_entries.json", "T-024_validation_entries.json", "T-025_validation_entries.json",
               "T-025b_validation_entries.json")
STATUSES = ("PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN")
FIELDS = ("test_id", "family", "title", "case", "criterion", "threshold", "measured", "status", "notes")
PLAN_ORDER = ("A1", "A2", "B1", "B2", "B3", "C1", "CTRL", "D1", "D2", "E1", "S1")
FAMILY_OF = {"A1": "A", "A2": "A", "B1": "B", "B2": "B", "B3": "B", "C1": "C", "CTRL": "C", "D1": "D", "D2": "D", "E1": "E", "S1": "S"}
PLAN_REF = "docs/VALIDATION_PLAN.md section 3"

# Plan tests that no task has run. Text copied from VALIDATION_PLAN.md section 3; P1 tests (T-023, T-024) are not assigned.
NOT_RUN_TESTS = {
    "A2": {"title": "Same fire, two eras", "case": "C1, C4, C6",
           "criterion": "Harmonized peaks overlap within 90% intervals and the raw record shows a mismatch (otherwise INCONCLUSIVE)",
           "threshold": "pre-registered at G1 (D-028)", "task": "T-023 (P1, not assigned)"},
    "B2": {"title": "Planted sensor jump detected", "case": "Random cells and regions",
           "criterion": "Flagged within 3 months in at least 90% of at least 50 trials; false flags in under 5% of unplanted series",
           "threshold": "pre-registered at G1 (D-028)", "task": "T-024 (P1, not assigned)"},
    "C1": {"title": "Cross-satellite agreement", "case": "All fire regions, 2018 to 2021",
           "criterion": "At least 85% of region-months agree within the combined 90% intervals (converted S-NPP against converted NOAA-20)",
           "threshold": "pre-registered at G1 (D-028)", "task": "T-024 (P1, not assigned)"},
    "CTRL": {"title": "Control", "case": "C8 (southern African savanna), satellite-change dates",
             "criterion": "No ABOVE or BELOW verdict at the change dates that is absent from the Aqua-only series",
             "threshold": "pre-registered at G1 (D-028)", "task": "T-024 (P1, not assigned)"},
}


def plan_test(test_id: str) -> str:
    """The plan test an entry belongs to: 'A1-C3' and 'A1-FAMILY' are A1, 'B1-2012-01' is B1, 'S1-BASELINE' is S1, 'D2' is D2."""
    return test_id.split("-")[0]


def not_run_entry(plan_id: str) -> dict:
    spec = NOT_RUN_TESTS[plan_id]
    return {"test_id": plan_id, "family": FAMILY_OF[plan_id], "title": spec["title"], "case": spec["case"], "criterion": spec["criterion"],
            "threshold": spec["threshold"], "measured": {}, "status": "NOT_RUN",
            "notes": f"Not run: {spec['task']}. No number is reported. Listed so that the plan is complete ({PLAN_REF})."}


def load_entries(qa: Path = QA, files: tuple[str, ...] = ENTRY_FILES) -> tuple[list[dict], dict]:
    """All entries of the harness files (file order kept) and their metadata. A missing file is an error, not a silent gap."""
    entries: list[dict] = []
    meta: dict = {}
    for name in files:
        f = qa / name
        if not f.exists():
            raise FileNotFoundError(f"{f} is missing: run the harness first (see docs/task-prompts/validation-integration.md)")
        doc = json.loads(f.read_text(encoding="utf-8"))
        if isinstance(doc, list):                      # the T-025 harness writes the bare list of entries
            doc = {"tests": doc, "synthetic": False}
        meta[name] = {k: doc.get(k) for k in ("contract_version", "method_version", "generated_at", "synthetic")}
        entries.extend(doc["tests"])
    return entries, meta


def resolve_s1(entries: list[dict]) -> list[dict]:
    """The overall S1 entry once both halves have a verdict.

    S1 (VALIDATION_PLAN section 3) is "conclusions unchanged" for two re-runs: the Aqua-measured baseline (S1-BASELINE) and no confidence filter
    (S1-CONFIDENCE-FILTER). [ASSUMPTION] Overall: FAIL if either half FAILs, PASS if both PASS, otherwise INCONCLUSIVE; while a half is NOT_RUN
    the overall entry stays as the harness wrote it (NOT_RUN).
    """
    by_id = {e["test_id"]: e for e in entries}
    base, conf, overall = by_id.get("S1-BASELINE"), by_id.get("S1-CONFIDENCE-FILTER"), by_id.get("S1")
    if not (base and conf and overall) or "NOT_RUN" in (base["status"], conf["status"]):
        return entries
    verdicts = (base["status"], conf["status"])
    status = "FAIL" if "FAIL" in verdicts else ("PASS" if verdicts == ("PASS", "PASS") else "INCONCLUSIVE")
    resolved = {**overall, "status": status, "measured": {"baseline_half": base["status"], "confidence_filter_half": conf["status"]},
                "notes": (f"Both halves ran: S1-BASELINE {base['status']} (T-025) and S1-CONFIDENCE-FILTER {conf['status']} (T-025b). Overall by the "
                          "rule: FAIL if either half FAILs, PASS if both PASS [ASSUMPTION, flagged for the Lead]. S1-CONFIDENCE-FILTER PASS means the "
                          "conclusions do not depend on the filter, not that A1 passes (A1 is FAIL with and without it).")}
    return [resolved if e["test_id"] == "S1" else e for e in entries]


def merge(entries: list[dict]) -> list[dict]:
    """Harness entries in plan order (A1 ... S1), the plan tests nobody ran appended as NOT_RUN entries in their place.

    A test_id present in more than one file keeps its last occurrence in the position of its first; the overall S1 is resolved from its halves."""
    seen: dict[str, dict] = {}
    for e in entries:
        seen[e["test_id"]] = e
    entries = resolve_s1(list(seen.values()))
    by_plan: dict[str, list[dict]] = {p: [] for p in PLAN_ORDER}
    for e in entries:
        e = {**e, "measured": flatten_measured(e.get("measured"))}      # null becomes {}, nested values become flat keys
        p = plan_test(e["test_id"])
        if p not in by_plan:
            raise ValueError(f"entry {e['test_id']} belongs to no test of the plan {PLAN_ORDER}")
        by_plan[p].append(e)
    out: list[dict] = []
    for p in PLAN_ORDER:
        if by_plan[p]:
            out.extend(by_plan[p])
        elif p in NOT_RUN_TESTS:
            out.append(not_run_entry(p))
    return out


def flatten_measured(measured: dict | None) -> dict:
    """`measured` as the API and the app accept it: only numbers, text, true/false and null (DATA_CONTRACT.md section 6; the API model
    `ValidationTest.measured` and the app's `parseMeasured` reject anything nested). A nested object becomes dotted keys
    ("control.rows_product"); a list becomes its JSON text ("[]", '["C3"]'), so nothing is dropped."""
    out: dict = {}

    def walk(prefix: str, value) -> None:
        if isinstance(value, dict):
            if not value and prefix:
                out[prefix] = "{}"
            for k, v in value.items():
                walk(f"{prefix}.{k}" if prefix else str(k), v)
        elif isinstance(value, (list, tuple)):
            out[prefix] = json.dumps(list(value), default=str)
        else:
            out[prefix] = value
    walk("", measured or {})
    return out


def _is_scalar(v) -> bool:
    return v is None or isinstance(v, (bool, int, float, str))


def _has_number(x) -> bool:
    """True if a measured value holds a number anywhere (a status string or a boolean is not a measurement)."""
    if isinstance(x, bool) or x is None:
        return False
    if isinstance(x, (int, float)):
        return True
    if isinstance(x, dict):
        return any(_has_number(v) for v in x.values())
    if isinstance(x, (list, tuple)):
        return any(_has_number(v) for v in x)
    return False


def check(doc: dict) -> list[str]:
    """Problems of a validation_results document; an empty list means it passes."""
    problems: list[str] = []
    for k in ("contract_version", "method_version", "generated_at", "synthetic", "tests"):
        if k not in doc:
            problems.append(f"missing top-level field {k}")
    if doc.get("synthetic") is not False:
        problems.append("synthetic must be false")
    tests = doc.get("tests", [])
    ids = [t.get("test_id") for t in tests]
    for i in sorted({x for x in ids if ids.count(x) > 1}):
        problems.append(f"duplicate test_id {i}")
    for t in tests:
        missing = [f for f in FIELDS if f not in t]
        if missing:
            problems.append(f"{t.get('test_id')}: missing fields {missing}")
            continue
        if t["status"] not in STATUSES:
            problems.append(f"{t['test_id']}: status {t['status']!r} is not one of {STATUSES}")
        if t["status"] == "NOT_RUN" and _has_number(t["measured"]):
            problems.append(f"{t['test_id']}: a NOT_RUN entry must carry no measured numbers")
        if not isinstance(t["measured"], dict):
            problems.append(f"{t['test_id']}: measured must be an object")
        else:
            nested = [k for k, v in t["measured"].items() if not _is_scalar(v)]
            if nested:
                problems.append(f"{t['test_id']}: measured values must be numbers, text, true/false or null (the API and the app refuse more): {nested[:3]}")
        if not t["notes"] and t["status"] in ("FAIL", "INCONCLUSIVE", "NOT_RUN"):
            problems.append(f"{t['test_id']}: a {t['status']} entry needs a note that says why")
    present = {plan_test(str(i)) for i in ids}
    for p in PLAN_ORDER:
        if p not in present:
            problems.append(f"plan test {p} has no entry")
    return problems


# The entry whose status is THE status of a plan test in docs/VALIDATION_PLAN.md section 4 (the Lead's readings: D1 is the pooled share,
# A1 the family, S1 the overall; the per-region and night D1 entries are separate rows in the results file).
HEADLINE = {"A1": "A1-FAMILY", "A2": "A2", "B1": "B1", "B2": "B2", "B3": "B3", "C1": "C1", "CTRL": "CTRL", "D1": "D1-REGIONS",
            "D2": "D2", "E1": "E1", "S1": "S1"}


def plan_statuses(doc: dict) -> dict[str, str]:
    """The status of each plan test as section 4 of the plan must show it (headline entry of the results document)."""
    by_id = {t["test_id"]: t["status"] for t in doc["tests"]}
    return {p: by_id[h] for p, h in HEADLINE.items() if h in by_id}


def check_plan_table(markdown: str, doc: dict) -> list[str]:
    """Problems between the section 4 table of VALIDATION_PLAN.md and the results document: a status that differs, a row with no run date
    although it ran, a NOT_RUN row with an actual result, a test without a row. Only the rows of the plan tests are read."""
    problems: list[str] = []
    want = plan_statuses(doc)
    rows: dict[str, list[str]] = {}
    for line in markdown.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 6 and cells[0] in HEADLINE:
            rows[cells[0]] = cells
    for p, status in want.items():
        if p not in rows:
            problems.append(f"{p}: no row in section 4")
            continue
        _, _, actual, shown, run_date, _ = rows[p][:6]
        shown = shown.replace("*", "").strip()
        if not shown.startswith(status):
            problems.append(f"{p}: section 4 shows {shown!r}, the results file has {status}")
        if status == "NOT_RUN" and actual not in ("", "—", "-"):
            problems.append(f"{p}: a NOT_RUN row must not show an actual result")
        if status != "NOT_RUN" and run_date in ("", "—", "-"):
            problems.append(f"{p}: ran ({status}) but has no run date")
    return problems


def build(qa: Path = QA, products: Path = PRODUCTS, now: datetime | None = None) -> dict:
    entries, meta = load_entries(qa)
    product_meta = json.loads((products / "metadata.json").read_text(encoding="utf-8"))
    if any(m["synthetic"] for m in meta.values()):
        raise ValueError("a harness file is marked synthetic")
    return {"contract_version": product_meta["contract_version"], "method_version": product_meta["method_version"],
            "generated_at": (now or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ"), "synthetic": False, "tests": merge(entries)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="only check data/products/validation_results.json")
    args = ap.parse_args(argv)
    target = PRODUCTS / "validation_results.json"
    doc = json.loads(target.read_text(encoding="utf-8")) if args.check else build()
    problems = check(doc)
    plan = ROOT / "docs" / "VALIDATION_PLAN.md"
    if plan.exists() and not problems:
        problems = check_plan_table(plan.read_text(encoding="utf-8"), doc)
    if problems:
        print("\n".join(problems))
        return 1
    if not args.check:
        target.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    counts: dict[str, int] = {}
    for t in doc["tests"]:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    print(f"{len(doc['tests'])} entries, {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
