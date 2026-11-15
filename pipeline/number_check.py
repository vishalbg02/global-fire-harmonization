"""T-026: verify every number the app displays against the products.

For a fixed list of views and for the rows of the products this checks, without changing the app, the API or any product:

  A  the API serves exactly the stored values (every number the same double, every null a null, never 0);
  B  the app's own formatting code (`app/src/components/map/format.ts`, `rankings.ts`, called through node) shows what the
     inventory (`docs/NUMBER_INVENTORY.md`) says, compared with an independent Python port of the inventory rules;
  C  the numbers the app computes itself: the split of the anomaly list, "N of M areas in neither ranking", test-status counts;
  D  the CSV export equals the stored rows;
  E  the figures written by hand in the methods page equal the document or product they cite.

Classes: MATCH, DEFECT (a served or displayed number differs from the product), DOC (hand-written text differs from its source),
NOTE (a limit to know about). Design and rules: docs/task-prompts/T-026-number-check.md (fixed before any result).

    python pipeline/number_check.py [--validation-extra PATH_TO_ANOTHER_validation_results.json]
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = ROOT / "data" / "products"
QA = ROOT / "data" / "interim" / "qa"
APP_SCRIPT = ROOT / "pipeline" / "number_check_app.mjs"
SEED = 20261115
CELL_SAMPLE = 300_000
P_HIGH, P_LOW = 0.995, 0.005
VERDICTS_RANKED = ("ABOVE_NORMAL", "BELOW_NORMAL")
DEMO_VIEWS = [("COUNTRY", "IDN", 2015, 9), ("COUNTRY", "IDN", 2015, 10), ("COUNTRY", "BRA", 2019, 8), ("COUNTRY", "CAN", 2023, 7),
              ("GLOBAL", "GLOBAL", None, None)]
ANOMALY_MONTHS = [(2015, 9), (2023, 8)]
ENTITY_COLUMNS = ["entity_type", "entity_id", "entity_name", "year", "month", "estimate", "ci90_low", "ci90_high", "sd",
                  "raw_combined_cell_days", "witnesses_used", "n_witnesses", "disagreement_scale", "baseline_median", "baseline_p25",
                  "baseline_p75", "pct_of_normal", "p_above", "p_below", "p_within", "verdict", "reason_codes", "data_level",
                  "method_version", "n_cells", "raw_by_witness"]
WITNESS_COLUMNS = ["AQUA_MODIS", "TERRA_MODIS", "SNPP_VIIRS", "NOAA20_VIIRS", "NOAA21_VIIRS"]


# --------------------------------------------------------------------------------------- JavaScript number formatting
def js_round(x: float) -> int:
    """JavaScript Math.round: half rounds up (towards +infinity), exactly, with no x + 0.5 rounding error."""
    f = math.floor(x)
    return int(f + 1) if x - f >= 0.5 else int(f)


def js_to_fixed(x: float, digits: int) -> str:
    """JavaScript Number.prototype.toFixed: the exact binary value is rounded half up on its magnitude; the sign is kept."""
    mag = abs(Decimal(x)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)
    s = format(mag, "f")
    return "-" + s if x < 0 else s


def fmt_probability(p: float) -> str:
    if p >= P_HIGH:
        return "more than 99%"
    if p <= P_LOW:
        return "less than 1%"
    return f"{js_round(p * 100)}%"


def fmt_pct(v: float | None) -> str:
    return "no data" if v is None else f"{js_round(v)}% of normal"


def fmt_estimate(estimate: float | None, low: float | None, high: float | None) -> str:
    if estimate is None:
        return "no data"
    if low is None or high is None:
        return f"{js_to_fixed(estimate, 1)} (interval not available)"
    return f"{js_to_fixed(estimate, 1)} (90% interval {js_to_fixed(low, 1)} to {js_to_fixed(high, 1)})"


def fmt_verdict_probability(verdict: str, p_above, p_below, p_within) -> str | None:
    wording = {"ABOVE_NORMAL": (p_above, "above normal"), "BELOW_NORMAL": (p_below, "below normal"), "WITHIN_NORMAL": (p_within, "within normal")}
    entry = wording.get(verdict)
    if entry is None or entry[0] is None:
        return None
    return f"{fmt_probability(entry[0])} likely {entry[1]}"


def fmt_anomaly_probability(verdict: str, p_above, p_below) -> str | None:
    p = p_above if verdict == "ABOVE_NORMAL" else p_below
    if p is None:
        return None
    return f"{fmt_probability(p)} likely {'above' if verdict == 'ABOVE_NORMAL' else 'below'} normal"


def display_score(p: float) -> int:
    """The probability at the precision the app shows (PR #62, api/README.md): every value of 0.995 or more reads "more than 99%" and counts as
    equal (1000); below that the whole percentage counts (0.991 and 0.986 are both 99)."""
    return 1000 if p >= P_HIGH else js_round(p * 100)


def anomaly_order(rows: list[dict]) -> list[dict]:
    """The documented API order: the larger of p_above and p_below at the displayed precision first, then the distance from normal
    abs(ln(pct / 100)) (missing or non-positive last), then entity_id, then entity_type (api/README.md; recomputed here independently
    from the stored rows)."""
    def key(r: dict):
        score = display_score(max(r["p_above"] or 0.0, r["p_below"] or 0.0))
        pct = r["pct_of_normal"]
        dist = abs(math.log(pct / 100.0)) if pct is not None and pct > 0 else None
        return (-score, 1 if dist is None else 0, -(dist or 0.0), r["entity_id"], r["entity_type"])
    return sorted(rows, key=key)


# ------------------------------------------------------------------------------------------------------------ report
class Report:
    def __init__(self) -> None:
        self.checks: dict[str, dict] = {}
        self.mismatches: list[dict] = []
        self.notes: list[dict] = []

    def add(self, check: str, ok: bool, cls: str = "DEFECT", **detail) -> None:
        c = self.checks.setdefault(check, {"checked": 0, "match": 0, "mismatch": 0})
        c["checked"] += 1
        if ok:
            c["match"] += 1
        else:
            c["mismatch"] += 1
            if len(self.mismatches) < 2000:
                self.mismatches.append({"check": check, "class": cls, **detail})

    def note(self, check: str, text: str, **detail) -> None:
        self.notes.append({"check": check, "class": "NOTE", "text": text, **detail})

    def as_dict(self) -> dict:
        return {"checks": self.checks, "mismatches": self.mismatches, "notes": self.notes}


def clean(v):
    """A stored value as the API sends it: NaN and NaT are None, numpy scalars are Python numbers, arrays are lists."""
    if v is None:
        return None
    if hasattr(v, "tolist"):
        v = v.tolist()
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, list):
        return [clean(x) for x in v]
    return v


def same(a, b) -> bool:
    a, b = clean(a), clean(b)
    if isinstance(a, float) or isinstance(b, float):
        return a is not None and b is not None and float(a) == float(b)
    return a == b


# ---------------------------------------------------------------------------------------------------- node (the app)
def run_app(payload: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        fin, fout = Path(tmp) / "in.json", Path(tmp) / "out.json"
        fin.write_text(json.dumps(payload, allow_nan=False), encoding="utf-8")
        subprocess.run(["node", str(APP_SCRIPT), str(fin), str(fout)], check=True, cwd=ROOT)
        return json.loads(fout.read_text(encoding="utf-8"))


def none_if_nan(df: pd.DataFrame) -> list[dict]:
    return [{k: clean(v) for k, v in r.items()} for r in df.to_dict(orient="records")]


# --------------------------------------------------------------------------------------------------------- products
def read_entity_month(products: Path = PRODUCTS) -> pd.DataFrame:
    return pd.read_parquet(products / "entity_month.parquet")


def connect(products: Path) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect()
    tmp = ROOT / "data" / "interim" / "_tmp_T-026"
    tmp.mkdir(parents=True, exist_ok=True)
    con.execute(f"SET temp_directory='{tmp.as_posix()}'")
    con.execute("SET memory_limit='5GB'")
    con.execute("SET max_temp_directory_size='20GiB'")
    con.execute("SET preserve_insertion_order=false")
    con.execute("SET threads=4")
    return con


def harmonized_view(products: Path) -> str:
    return f"read_parquet('{(products / 'cell_month_harmonized.parquet').as_posix()}')"


# ------------------------------------------------------------------------------------------------------- check B
def check_formatting(rep: Report, em: pd.DataFrame, cells: pd.DataFrame, label: str) -> None:
    """The app's formatting functions against the Python port of the inventory rules, for every row of `em` and `cells`."""
    for name, df in ((f"{label}:entity_month", em), (f"{label}:cell_month_harmonized", cells)):
        probs: list[float] = []
        for col in ("p_above", "p_below", "p_within"):
            probs += [float(v) for v in df[col].dropna()]
        pct = [clean(v) for v in df["pct_of_normal"]]
        est = none_if_nan(df[["estimate", "ci90_low", "ci90_high"]])
        vp = none_if_nan(df[["verdict", "p_above", "p_below", "p_within"]])
        an = none_if_nan(df[df.verdict.isin(VERDICTS_RANKED)][["verdict", "p_above", "p_below", "pct_of_normal"]])
        for a in an:
            a["entity_type"] = "COUNTRY"
        out = run_app({"probability": probs, "pct": pct, "estimate": est, "verdictProbability": vp, "anomalyText": an})
        for p, shown in zip(probs, out["probability"], strict=True):
            exp = fmt_probability(p)
            rep.add("B probability wording", shown == exp, stored=p, shown=shown, expected=exp, source=name)
        for v, shown in zip(pct, out["pct"], strict=True):
            exp = fmt_pct(v)
            rep.add("B % of normal text", shown == exp, stored=v, shown=shown, expected=exp, source=name)
        for e, shown in zip(est, out["estimate"], strict=True):
            exp = fmt_estimate(e["estimate"], e["ci90_low"], e["ci90_high"])
            rep.add("B estimate and interval text", shown == exp, stored=e, shown=shown, expected=exp, source=name)
        for c, shown in zip(vp, out["verdictProbability"], strict=True):
            exp = fmt_verdict_probability(c["verdict"], c["p_above"], c["p_below"], c["p_within"])
            rep.add("B verdict probability text", shown == exp, stored=c, shown=shown, expected=exp, source=name)
        for a, shown in zip(an, out["anomalyText"], strict=True):
            rep.add("B anomaly row text", shown["pct"] == fmt_pct(a["pct_of_normal"])
                    and shown["probability"] == fmt_anomaly_probability(a["verdict"], a["p_above"], a["p_below"]), stored=a, shown=shown, source=name)


def cell_rows_for_format(products: Path, months: list[tuple[int, int]]) -> pd.DataFrame:
    """Every cell row of the demo months, a fixed random sample of the rest, and every row at a formatting edge (probability within
    1e-9 of 0.995 or 0.005; % of normal at a .5 boundary; an estimate or interval end at a 0.05 boundary)."""
    con = connect(products)
    src = harmonized_view(products)
    cols = "estimate, ci90_low, ci90_high, pct_of_normal, p_above, p_below, p_within, verdict"
    mon = " OR ".join(f"(year = {y} AND month = {m})" for y, m in months)
    edges = ("abs(p_above - 0.995) < 1e-9 OR abs(p_below - 0.995) < 1e-9 OR abs(p_within - 0.995) < 1e-9 OR abs(p_above - 0.005) < 1e-9 "
             "OR abs(p_below - 0.005) < 1e-9 OR abs(p_within - 0.005) < 1e-9 OR abs(pct_of_normal - floor(pct_of_normal) - 0.5) < 1e-9 "
             "OR abs(estimate * 10 - floor(estimate * 10) - 0.5) < 1e-6 OR abs(ci90_low * 10 - floor(ci90_low * 10) - 0.5) < 1e-6 "
             "OR abs(ci90_high * 10 - floor(ci90_high * 10) - 0.5) < 1e-6")
    a = con.execute(f"SELECT {cols} FROM {src} WHERE {mon}").df()
    b = con.execute(f"SELECT {cols} FROM {src} WHERE {edges}").df()
    c = con.execute(f"SELECT {cols} FROM {src} USING SAMPLE reservoir({CELL_SAMPLE} ROWS) REPEATABLE ({SEED})").df()
    return pd.concat([a, b, c], ignore_index=True)


# ------------------------------------------------------------------------------------------------------- check A, C, D
class Api:
    def __init__(self, products: Path) -> None:
        os.environ["PRODUCTS_DIR"] = str(products)
        sys.path.insert(0, str(ROOT / "api"))
        from fastapi.testclient import TestClient
        from fire_api.main import app
        self.client = TestClient(app)

    def get(self, path: str, **params):
        r = self.client.get(path, params=params)
        if r.status_code != 200:
            raise RuntimeError(f"{path} {params}: HTTP {r.status_code}")
        return r


def compare_record(rep: Report, check: str, view: str, api: dict, stored: dict, fields: list[str]) -> None:
    for f in fields:
        ok = same(api.get(f), stored.get(f))
        rep.add(check, ok, view=view, field=f, stored=clean(stored.get(f)), served=clean(api.get(f)))


def check_api(rep: Report, api: Api, em: pd.DataFrame, products: Path) -> dict:
    """A: the API against the stored rows for the fixed views. Returns the anomaly answers (for check C)."""
    meta = json.loads((products / "metadata.json").read_text(encoding="utf-8"))
    served_meta = api.get("/api/meta").json()
    rep.add("A metadata", served_meta == meta, view="/api/meta", field="metadata.json")
    served_val = api.get("/api/validation").json()
    stored_val = json.loads((products / "validation_results.json").read_text(encoding="utf-8"))
    rep.add("A validation file", served_val == stored_val, view="/api/validation", field="validation_results.json")
    latest = tuple(int(x) for x in meta["latest_month"].split("-"))
    views = [(t, i, y, m) if y else (t, i, *latest) for t, i, y, m in DEMO_VIEWS]
    by_key = {(r["entity_type"], r["entity_id"], r["year"], r["month"]): r for r in none_if_nan(em)}
    for et, eid, year, month in views:
        view = f"{et}:{eid} {year}-{month:02d}"
        ev = api.get("/api/evidence", entity_type=et, entity_id=eid, year=year, month=month).json()
        stored = by_key[(et, eid, year, month)]
        compare_record(rep, "A evidence record", view, ev, stored, [c for c in ENTITY_COLUMNS if c != "raw_by_witness"])
        rep.add("A evidence raw_by_witness", ev["raw_by_witness"] == json.loads(stored["raw_by_witness"]), view=view, field="raw_by_witness")
    for et, eid, _, _ in DEMO_VIEWS:
        series = api.get("/api/series", entity_type=et, entity_id=eid).json()
        stored_rows = em[(em.entity_type == et) & (em.entity_id == eid)].sort_values(["year", "month"])
        rep.add("A series length", len(series) == len(stored_rows), view=f"{et}:{eid}", field="rows", stored=len(stored_rows), served=len(series))
        rep.add("A series order", [(r["year"], r["month"]) for r in series] == sorted((r["year"], r["month"]) for r in series), view=f"{et}:{eid}", field="order")
        for served, stored in zip(series, none_if_nan(stored_rows), strict=False):
            compare_record(rep, "A series records", f"{et}:{eid} {stored['year']}-{stored['month']:02d}", served, stored, ENTITY_COLUMNS)
    anomalies: dict = {}
    for year, month in [*ANOMALY_MONTHS, latest]:
        got = api.get("/api/anomalies", year=year, month=month, limit=500).json()
        rows = [r for r in none_if_nan(em[(em.year == year) & (em.month == month)]) if r["verdict"] in VERDICTS_RANKED]
        expected = anomaly_order(rows)
        view = f"anomalies {year}-{month:02d}"
        types = sorted({r["entity_type"] for r in got})
        if "GLOBAL" in types:
            rep.note("A anomaly list", "The API answer contains the GLOBAL entity; the app leaves it out of the rankings.", view=view)
        rep.add("A anomaly set", sorted((r["entity_type"], r["entity_id"]) for r in got) == sorted((r["entity_type"], r["entity_id"]) for r in expected),
                view=view, field="entities", stored=len(expected), served=len(got))
        rep.add("A anomaly order", [(r["entity_type"], r["entity_id"]) for r in got] == [(r["entity_type"], r["entity_id"]) for r in expected],
                view=view, field="order")
        stored_by = {(r["entity_type"], r["entity_id"]): r for r in rows}
        for r in got:
            s = stored_by.get((r["entity_type"], r["entity_id"]))
            if s:
                compare_record(rep, "A anomaly values", f"{view} {r['entity_id']}", r, s, ["entity_name", "verdict", "p_above", "p_below", "pct_of_normal"])
        anomalies[(year, month)] = got
    check_map(rep, api, products, [(2015, 9), (2023, 7)])
    return anomalies


def check_map(rep: Report, api: Api, products: Path, months: list[tuple[int, int]]) -> None:
    con = connect(products)
    src = harmonized_view(products)
    cells = pd.read_parquet(products / "cells.parquet")
    bounds = {r["cell_id"]: r for r in none_if_nan(cells[["cell_id", "lat_min", "lat_max", "lon_min", "lon_max"]])}
    fields = ["estimate", "ci90_low", "ci90_high", "sd", "raw_combined_cell_days", "witnesses_used", "n_witnesses", "disagreement_scale",
              "baseline_median", "baseline_p25", "baseline_p75", "pct_of_normal", "p_above", "p_below", "p_within", "verdict",
              "reason_codes", "data_level", "method_version"]
    for year, month in months:
        stored = {r["cell_id"]: r for r in none_if_nan(con.execute(f"SELECT * FROM {src} WHERE year = {year} AND month = {month}").df())}
        for layer in ("verdict", "raw", "harmonized"):
            got = api.get("/api/map", year=year, month=month, layer=layer).json()
            view = f"map {year}-{month:02d} {layer}"
            rep.add("A map cell count", len(got) == len(stored), view=view, field="cells", stored=len(stored), served=len(got))
            if layer != "verdict":
                continue          # every layer returns the same fields (api/README.md); the fields are compared once, on the verdict layer
            for r in got:
                s = stored.get(r["cell_id"])
                rep.add("A map cell present", s is not None, view=view, field=r["cell_id"])
                if s is None:
                    continue
                compare_record(rep, "A map cell values", f"{view} {r['cell_id']}", r, s, fields)
                compare_record(rep, "A map cell bounds", f"{view} {r['cell_id']}", r, bounds[r["cell_id"]], ["lat_min", "lat_max", "lon_min", "lon_max"])


def api_accepts_validation(doc: dict) -> bool:
    """Does the API's own model take this validation_results document? If not, GET /api/validation answers 503 and the methods page shows
    no statuses (the model and the app's parseMeasured accept only scalar `measured` values)."""
    from fire_api.models import ValidationResults
    try:
        ValidationResults.model_validate(doc)
    except Exception:  # noqa: BLE001 - any validation error means the API would answer 503
        return False
    return True


def check_computed(rep: Report, api: Api, anomalies: dict, em: pd.DataFrame, validation_files: dict[str, Path]) -> None:
    """C: what the app computes itself."""
    for (year, month), got in anomalies.items():
        for tab in ("COUNTRY", "CONTINENT"):
            total = len(api.get("/api/entities", type=tab).json())
            out = run_app({"ranking": {"anomalies": got, "tab": tab, "total": total}})["ranking"]
            of_type = [r for r in got if r["entity_type"] == tab]
            view = f"{tab} {year}-{month:02d}"
            rep.add("C ranking split", out["above"] == [r["entity_id"] for r in of_type if r["verdict"] == "ABOVE_NORMAL"]
                    and out["below"] == [r["entity_id"] for r in of_type if r["verdict"] == "BELOW_NORMAL"], view=view, field="above/below order")
            rep.add("C not-ranked count", out["notRanked"] == total - len(of_type), view=view, field="N of M", stored=total - len(of_type), shown=out["notRanked"])
            with_record = em[(em.entity_type == tab) & (em.year == year) & (em.month == month)]
            if len(with_record) != total:
                rep.note("C not-ranked count", f"{view}: the app says {out['notRanked']} of {total} areas are in neither ranking, but only "
                         f"{len(with_record)} have a record that month, so {total - len(with_record)} of them have no record at all (not within normal).",
                         areas=total, with_record=len(with_record), ranked=len(of_type))
    for name, path in validation_files.items():
        doc = json.loads(path.read_text(encoding="utf-8"))
        rep.add("C validation file accepted by the API", api_accepts_validation(doc), view=name, field="ValidationResults model",
                stored="every measured value is a number, text, true/false or null (the API and the app refuse more)")
        shown = run_app({"statuses": doc["tests"]})["statuses"]
        tally = {s: sum(1 for t in doc["tests"] if t["status"] == s) for s in ("PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN")}
        rep.add("C test-status counts", shown == tally, view=name, field="counts", stored=tally, shown=shown)


def legend_label(max_value: float) -> str:
    """The top label of an activity legend (map/Legend.tsx and calendar/CalendarLegend.tsx): the maximum rounded, or "no data" when 0."""
    return str(js_round(max_value)) if max_value > 0 else "no data"


def check_legends(rep: Report, api: Api, em: pd.DataFrame, products: Path) -> None:
    """C: the maximum of the colour scales (the legend's top label) and the custom-area label, with the app's own helpers."""
    con = connect(products)
    src = harmonized_view(products)
    cell_sets, expected = [], []
    for year, month in [(2015, 9), (2023, 7)]:
        df = con.execute(f"SELECT raw_combined_cell_days, estimate FROM {src} WHERE year = {year} AND month = {month}").df()
        cell_sets.append(none_if_nan(df))
        expected.append((f"map {year}-{month:02d}", max(0.0, float(df.raw_combined_cell_days.max()), float(df.estimate.max()))))
    series_sets, expected_s = [], []
    for et, eid, _, _ in DEMO_VIEWS:
        rows = em[(em.entity_type == et) & (em.entity_id == eid)]
        series_sets.append(none_if_nan(rows[["raw_combined_cell_days", "estimate"]]))
        expected_s.append((f"calendar {et}:{eid}", max(0.0, float(rows.raw_combined_cell_days.max()), float(rows.estimate.max()))))
    boxes = [[100.0, 0.0, 101.0, 1.0], [-58.5, -35.0, -53.0, -30.0], [95.005, -6.125, 119.995, 4.555], [-0.004, 0.0049, 0.0051, 0.015]]
    out = run_app({"sharedMax": cell_sets, "maxActivity": series_sets, "bboxLabel": boxes})
    for (view, exp), got in zip(expected, out["sharedMax"], strict=True):
        rep.add("C legend maximum", got == exp and legend_label(got) == legend_label(exp), view=view, field="scale maximum", stored=exp, shown=got)
    for (view, exp), got in zip(expected_s, out["maxActivity"], strict=True):
        rep.add("C legend maximum", got == exp and legend_label(got) == legend_label(exp), view=view, field="scale maximum", stored=exp, shown=got)
    for b, got in zip(boxes, out["bboxLabel"], strict=True):
        shown = re.fullmatch(r"W (\S+), S (\S+), E (\S+), N (\S+)", got)
        for name, x, text in zip("WSEN", b, shown.groups() if shown else [], strict=False):
            d = Decimal(str(x))
            exp = format(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")      # the decimal as typed, half away from zero
            exp = exp[1:] if exp.startswith("-") and float(exp) == 0 else exp          # no negative zero
            tie = abs(d * 100 - (d * 100).to_integral_value(rounding="ROUND_FLOOR") - Decimal("0.5")) == 0
            if text != exp and tie and x < 0:
                rep.note("C custom-area label", f"A negative coordinate that ends in exactly 5 at the third decimal ({x}) is shown as {text}, "
                         f"not {exp}: the app rounds with Math.round, so a tie goes towards +infinity. Display and id only; the request uses the typed number.",
                         view=str(b), shown=text, expected=exp)
            else:
                rep.add("C custom-area label", text == exp, view=str(b), field=name, stored=exp, shown=text)


def check_csv(rep: Report, api: Api, em: pd.DataFrame) -> None:
    """D: the CSV export of Indonesia equals the stored rows."""
    r = api.get("/api/export.csv", entity_type="COUNTRY", entity_id="IDN")
    text = r.content.decode("utf-8-sig")
    lines = text.splitlines()
    header_lines = [ln for ln in lines if ln.startswith("#")]
    body = "\n".join(ln for ln in lines if not ln.startswith("#"))
    rows = list(csv.DictReader(io.StringIO(body)))
    want = [c for c in ENTITY_COLUMNS if c != "raw_by_witness"] + [f"raw_{w}" for w in WITNESS_COLUMNS]
    rep.add("D csv columns", list(rows[0].keys()) == want, view="CSV IDN", field="header row", stored=want, served=list(rows[0].keys()))
    for k in ("data_status", "area", "method_version", "contract_version", "generated_at", "citation"):
        rep.add("D csv header lines", any(ln.startswith(f"# {k}:") for ln in header_lines), view="CSV IDN", field=k)
    stored = none_if_nan(em[(em.entity_type == "COUNTRY") & (em.entity_id == "IDN")].sort_values(["year", "month"]))
    rep.add("D csv rows", len(rows) == len(stored), view="CSV IDN", field="rows", stored=len(stored), served=len(rows))
    for got, s in zip(rows, stored, strict=False):
        view = f"CSV IDN {s['year']}-{s['month']:02d}"
        raw = json.loads(s["raw_by_witness"])
        for col in want:
            cell = got[col]
            if col.startswith("raw_") and col[4:] in WITNESS_COLUMNS:
                exp = raw.get(col[4:])
            elif col in ("witnesses_used", "reason_codes"):
                exp = ";".join(s[col])
                rep.add("D csv values", cell == exp, view=view, field=col, stored=exp, served=cell)
                continue
            else:
                exp = s[col]
            if exp is None:
                rep.add("D csv values", cell == "", view=view, field=col, stored=None, served=cell)
            elif isinstance(exp, float):
                rep.add("D csv values", cell != "" and float(cell) == exp, view=view, field=col, stored=exp, served=cell)
            elif isinstance(exp, int):
                rep.add("D csv values", cell != "" and int(float(cell)) == exp, view=view, field=col, stored=exp, served=cell)
            else:
                rep.add("D csv values", cell == str(exp), view=view, field=col, stored=exp, served=cell)


# ----------------------------------------------------------------------------------------------------------- check E
def share_judgeable(products: Path) -> dict:
    """Share of entity-months (and cell-months) whose verdict is above, below or within normal, by entity type, from the products."""
    em = read_entity_month(products)
    judged = em.verdict.isin(["ABOVE_NORMAL", "BELOW_NORMAL", "WITHIN_NORMAL"])
    out = {t: float(judged[em.entity_type == t].mean()) for t in sorted(em.entity_type.unique())}
    con = connect(products)
    src = harmonized_view(products)
    r = con.execute(f"""SELECT avg(CASE WHEN verdict IN ('ABOVE_NORMAL','BELOW_NORMAL','WITHIN_NORMAL') THEN 1.0 ELSE 0.0 END),
                               avg(CASE WHEN verdict = 'NO_DETECTED_ACTIVITY' THEN 1.0 ELSE 0.0 END) FROM {src}""").fetchone()
    out["CELL"], out["CELL_NO_DETECTED_ACTIVITY"] = float(r[0]), float(r[1])
    world = em[em.entity_type == "GLOBAL"]
    out["WORLD_MONTHS"] = len(world)
    out["WORLD_CANNOT_DETERMINE"] = int((world.verdict == "CANNOT_DETERMINE").sum())
    out["WORLD_CANNOT_DETERMINE_WIDE_INTERVAL"] = int(((world.verdict == "CANNOT_DETERMINE") & world.reason_codes.map(lambda c: "WIDE_INTERVAL" in list(c))).sum())
    return out


def check_methods(rep: Report, products: Path, validation_path: Path) -> None:
    """E: the numbers written in app/src/content/methods.ts against their sources."""
    text = (ROOT / "app" / "src" / "content" / "methods.ts").read_text(encoding="utf-8")
    sys.path.insert(0, str(ROOT / "pipeline"))
    import harmonize as hz

    def has(claim: str) -> bool:
        return claim in text
    for claim, stored in (("phi is 2.25", hz.PHI["D"]), ("phi is 2.47", hz.PHI["N"]), ("kappa is 0.0084", hz.KAPPA["D"]), ("kappa is 0.0164", hz.KAPPA["N"])):
        num = float(claim.split()[-1])
        rep.add("E methods text", has(claim) and round(stored, 4) == num, cls="DOC", view="methods: " + claim, source="pipeline/harmonize.py", stored=stored)
    meta = json.loads((products / "metadata.json").read_text(encoding="utf-8"))
    rep.add("E methods text", meta["baseline_years"] == [2003, 2022] and has("2003 to 2022") and has("15 of the 20 years"), cls="DOC",
            view="methods: baseline 2003 to 2022, 15 of 20 years", source="metadata.json, D-028", stored=meta["baseline_years"])
    val = json.loads(validation_path.read_text(encoding="utf-8"))
    d1 = {t["test_id"]: t for t in val["tests"]}
    if "D1-REGIONS" in d1:
        m, c = d1["D1-REGIONS"]["measured"], d1["D1-COUNTRIES"]["measured"]
        for label, stored in (("0.818 for regions", round(m["coverage_90"], 3)), ("0.811 for countries", round(c["coverage_90"], 3)),
                              ("0.847 for regions", round(m["day_night_total"], 3)), ("0.826 for countries", round(c["day_night_total"], 3)),
                              ("(1,466 units)", m["units"]), ("(6,409 units)", c["units"])):
            claim_ok = has(label) and (str(stored) in label or f"{stored:,}" in label)
            rep.add("E methods text", claim_ok, cls="DOC", view="methods: D1 " + label, source="validation_results.json", stored=stored)
    else:
        rep.note("E methods text", "The D1 coverage figures cannot be checked against this validation_results.json (it holds no D1 entry); "
                 "pass the T-027 file with --validation-extra.")
    shares = share_judgeable(products)
    claims = (("29.6% for countries", shares.get("COUNTRY")), ("52.7% for continents", shares.get("CONTINENT")), ("34.1% for the world", shares.get("GLOBAL")),
              ("2.9% for grid cells", shares.get("CELL")), ("65% of cell-months have no detected activity", shares.get("CELL_NO_DETECTED_ACTIVITY")))
    for claim, stored in claims:
        pct = float(claim.split("%")[0])
        digits = 0 if pct == 65 else 1
        rep.add("E methods text", has(claim) and stored is not None and round(stored * 100, digits) == pct, cls="DOC",
                view="methods: " + claim, source="products (share of months with an above/below/within verdict)", stored=stored)
    rep.add("E methods text", has("189 of the 293 world months are CANNOT_DETERMINE with WIDE_INTERVAL") and shares["WORLD_MONTHS"] == 293
            and shares["WORLD_CANNOT_DETERMINE_WIDE_INTERVAL"] == 189, cls="DOC",
            view="methods: 189 of the 293 world months are CANNOT_DETERMINE with WIDE_INTERVAL", source="products",
            stored=(shares["WORLD_CANNOT_DETERMINE_WIDE_INTERVAL"], shares["WORLD_MONTHS"]))
    rep.note("E methods text", "Other numbers written in methods.ts (dates, doi, onset months, BIC, sizes) are text with their own labels and are listed "
             "in the inventory as hand-written; only the figures the inventory names are checked here.")


# ------------------------------------------------------------------------------------------------------------- run
def require_node() -> None:
    """The app's TypeScript helpers are imported by node's built-in type stripping (22.6 and later; the project requires 22.12+)."""
    try:
        out = subprocess.run(["node", "--version"], capture_output=True, text=True, check=True).stdout.strip().lstrip("v")
        major, minor = (int(x) for x in out.split(".")[:2])
    except (OSError, subprocess.CalledProcessError, ValueError) as e:
        raise SystemExit("number_check needs node 22.6 or later on the PATH (the project requires 22.12+)") from e
    if (major, minor) < (22, 6):
        raise SystemExit(f"number_check needs node 22.6 or later to import the app's TypeScript helpers; found {out}")


def run(products: Path = PRODUCTS, validation_extra: Path | None = None) -> dict:
    require_node()
    rep = Report()
    em = read_entity_month(products)
    api = Api(products)
    meta = json.loads((products / "metadata.json").read_text(encoding="utf-8"))
    latest = tuple(int(x) for x in meta["latest_month"].split("-"))
    print("A: API against the products", flush=True)
    anomalies = check_api(rep, api, em, products)
    print("B: the app's formatting on entity_month", flush=True)
    cells = cell_rows_for_format(products, [(2015, 9), (2015, 10), (2019, 8), (2023, 7), latest])
    check_formatting(rep, em, cells.iloc[:0], "entity")
    print("B: the app's formatting on cell rows", flush=True)
    check_formatting(rep, em.iloc[:0], cells, "cells")
    print("C: what the app computes", flush=True)
    files = {"validation_results.json of this branch": products / "validation_results.json"}
    if validation_extra:
        files[f"validation_results.json ({validation_extra})"] = validation_extra
    check_computed(rep, api, anomalies, em, files)
    check_legends(rep, api, em, products)
    print("D: CSV", flush=True)
    check_csv(rep, api, em)
    print("E: methods page text", flush=True)
    check_methods(rep, products, validation_extra or products / "validation_results.json")
    result = {"products": str(products), "latest_month": meta["latest_month"], "entity_month_rows": len(em), "cell_rows_checked": len(cells),
              **rep.as_dict()}
    QA.mkdir(parents=True, exist_ok=True)
    (QA / "T-026_number_check.json").write_text(json.dumps(result, indent=1, default=str), encoding="utf-8")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--validation-extra", type=Path, help="another validation_results.json (for example the T-027 file) to tally and check")
    args = ap.parse_args()
    res = run(validation_extra=args.validation_extra)
    for name, c in sorted(res["checks"].items()):
        print(f"{name:<36} checked {c['checked']:>9,}  match {c['match']:>9,}  mismatch {c['mismatch']:>6,}")
    print(f"{len(res['notes'])} notes; mismatches stored: {len(res['mismatches'])}")
    return 1 if any(c["mismatch"] for c in res["checks"].values()) else 0


if __name__ == "__main__":
    sys.exit(main())
