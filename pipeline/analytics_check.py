"""T-083: recompute the analytics panel's numbers from the products, independently, and compare them with the panel's own functions.

The panel's pure functions (`app/src/components/analytics/compute.ts`) are run in Node on the stored records; the same quantities are computed
here in pandas and DuckDB from `entity_month.parquet`, `cells.parquet` and `cell_month_harmonized.parquet`. Any difference is reported.

    python pipeline/analytics_check.py            # prints the comparison for two areas
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = ROOT / "data" / "products"
NODE_SCRIPT = ROOT / "pipeline" / "analytics_check_app.mjs"
# The first two keep the T-083 comparison (Indonesia against the world); India and Asia are added for the exact coverage of T-090.
AREAS = [("COUNTRY", "IDN"), ("GLOBAL", "GLOBAL"), ("COUNTRY", "IND"), ("CONTINENT", "AS")]
SELECTED = (2015, 9)
COVERAGE_MONTH = (2019, 12)


def nan_to_none(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else x


def load_series(con: duckdb.DuckDBPyConnection, products: Path, etype: str, eid: str) -> list[dict]:
    df = con.execute(
        "select year, month, estimate, raw_combined_cell_days, data_level, baseline_p25, baseline_median, baseline_p75, pct_of_normal "
        f"from read_parquet('{products.as_posix()}/entity_month.parquet') where entity_type = ? and entity_id = ? order by year, month",
        [etype, eid],
    ).df()
    return [{k: nan_to_none(v) for k, v in r.items()} for r in df.to_dict("records")]


# ---------------------------------------------------------------------------------------------------------- independent (pandas) side
def expected(rows: list[dict], year: int, month: int) -> dict:
    df = pd.DataFrame(rows)
    est = df[df.estimate.notna()]
    annual = est.groupby("year").agg(monthsUsed=("estimate", "size"), harmonizedSum=("estimate", "sum"), rawSum=("raw_combined_cell_days", "sum"))
    annual = {int(y): {"monthsUsed": int(r.monthsUsed), "harmonizedSum": float(r.harmonizedSum), "rawSum": float(r.rawSum)} for y, r in annual.iterrows()}
    season = []
    for m in range(1, 13):
        base = df[(df.month == m) & df.baseline_median.notna()]
        base = base[base.year == year] if (base.year == year).any() else base.head(1)
        sel = df[(df.month == m) & (df.year == year)].estimate
        season.append({"month": m, "p25": nan_to_none(base.baseline_p25.iloc[0]) if len(base) else None,
                       "median": nan_to_none(base.baseline_median.iloc[0]) if len(base) else None,
                       "p75": nan_to_none(base.baseline_p75.iloc[0]) if len(base) else None,
                       "selected": nan_to_none(sel.iloc[0]) if len(sel) else None})
    same = est[est.month == month]
    mine = same[same.year == year].estimate.iloc[0]
    rank = {"rank": int((same.estimate > mine).sum()) + 1, "of": len(same), "tiedWith": sorted(int(y) for y in same[(same.estimate == mine) & (same.year != year)].year)}
    return {"annual": annual, "season": season, "rank": rank}


def expected_coverage(con: duckdb.DuckDBPyConnection, products: Path, etype: str, eid: str, year: int, month: int) -> dict:
    """The cells stored for the area (country_iso3 or continent of cells.parquet; every cell for the world) counted by verdict in the month."""
    p = products.as_posix()
    where = {"GLOBAL": "true", "COUNTRY": "c.country_iso3 = ?", "CONTINENT": "c.continent = ?"}[etype]
    params = [year, month] + ([] if etype == "GLOBAL" else [eid])
    rows = con.execute(
        f"select h.verdict, count(*) from read_parquet('{p}/cell_month_harmonized.parquet') h join read_parquet('{p}/cells.parquet') c using (cell_id) "
        f"where h.year = ? and h.month = ? and {where} group by h.verdict",
        params,
    ).fetchall()
    by = {v: int(n) for v, n in rows}
    total = sum(by.values())
    return {"cells": total, "determinable": total - by.get("CANNOT_DETERMINE", 0), "byVerdict": by}


# --------------------------------------------------------------------------------------------------------------- the panel's own side
def run_panel_functions(payload: dict) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "in.json"
        src.write_text(json.dumps(payload), encoding="utf-8")
        out = subprocess.run(["node", str(NODE_SCRIPT), str(src)], capture_output=True, text=True, check=True, encoding="utf-8")
    return json.loads(out.stdout)


def close(a, b, tol=1e-6) -> bool:
    if a is None or b is None:
        return a is b
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def compare(products: Path = PRODUCTS) -> dict:
    con = duckdb.connect()
    year, month = SELECTED
    report: dict = {"areas": {}, "mismatches": []}
    series = {a: load_series(con, products, *a) for a in AREAS}
    # What the panel receives: the month's cells (id and verdict) and, from the cell list of GET /api/map/cells, each cell's country and continent.
    month_cells = con.execute(
        f"select h.cell_id, h.verdict from read_parquet('{products.as_posix()}/cell_month_harmonized.parquet') h where h.year = ? and h.month = ?", [*COVERAGE_MONTH]).df()
    cells = [{"cell_id": r.cell_id, "verdict": r.verdict} for r in month_cells.itertuples()]
    listed = con.execute(f"select cell_id, country_iso3, continent from read_parquet('{products.as_posix()}/cells.parquet') order by cell_id").df()
    areas = {"cell_id": listed.cell_id.tolist(), "country_iso3": [nan_to_none(v) for v in listed.country_iso3], "continent": [nan_to_none(v) for v in listed.continent]}
    covs = {a: expected_coverage(con, products, *a, *COVERAGE_MONTH) for a in AREAS}
    payload = {"series": {f"{a[0]}:{a[1]}": rows for a, rows in series.items()}, "year": year, "month": month, "cells": cells, "areas": areas,
               "types": {f"{a[0]}:{a[1]}": [a[0], a[1]] for a in AREAS},
               "compare": [f"{AREAS[0][0]}:{AREAS[0][1]}", f"{AREAS[1][0]}:{AREAS[1][1]}"]}
    got = run_panel_functions(payload)
    for a in AREAS:
        key = f"{a[0]}:{a[1]}"
        exp, g = expected(series[a], year, month), got["areas"][key]
        for y, e in exp["annual"].items():
            p = next((x for x in g["annual"] if x["year"] == y), None)
            ok = p is not None and p["monthsUsed"] == e["monthsUsed"] and close(p["harmonizedSum"], e["harmonizedSum"]) and close(p["rawSum"], e["rawSum"])
            if not ok:
                report["mismatches"].append({"area": key, "check": "annual", "year": y, "expected": e, "panel": p})
        if len(g["annual"]) != len(exp["annual"]):
            report["mismatches"].append({"area": key, "check": "annual years", "expected": len(exp["annual"]), "panel": len(g["annual"])})
        for e, p in zip(exp["season"], g["season"], strict=True):
            if not all(close(e[k], p[k]) for k in ("p25", "median", "p75", "selected")):
                report["mismatches"].append({"area": key, "check": "season", "month": e["month"], "expected": e, "panel": p})
        r = g["rank"]
        if r is None or (r["rank"], r["of"], r["tiedWith"]) != (exp["rank"]["rank"], exp["rank"]["of"], exp["rank"]["tiedWith"]):
            report["mismatches"].append({"area": key, "check": "rank", "expected": exp["rank"], "panel": r})
        c, ec = g["coverage"], covs[a]
        if c is None or (c["cells"], c["determinable"], c["byVerdict"]) != (ec["cells"], ec["determinable"], ec["byVerdict"]):
            report["mismatches"].append({"area": key, "check": "coverage", "expected": ec, "panel": c})
        report["areas"][key] = {"rank": exp["rank"], "annual_years": len(exp["annual"]), "coverage": {k: ec[k] for k in ("cells", "determinable")},
                                "annual_2012": exp["annual"].get(2012), "annual_2011": exp["annual"].get(2011)}
    # compare: the panel aligns the second area's % of normal by month
    a_rows, b_rows = series[AREAS[0]], series[AREAS[1]]
    b_by = {(r["year"], r["month"]): r["pct_of_normal"] for r in b_rows}
    exp_cmp = [{"label": f"{r['year']}-{r['month']:02d}", "a": r["pct_of_normal"], "b": b_by.get((r["year"], r["month"]))} for r in a_rows]
    if len(exp_cmp) != len(got["compare"]) or not all(close(e["a"], p["a"]) and close(e["b"], p["b"]) and e["label"] == p["label"] for e, p in zip(exp_cmp, got["compare"], strict=False)):
        report["mismatches"].append({"check": "compare", "months": len(exp_cmp), "panel_months": len(got["compare"])})
    return report


if __name__ == "__main__":
    rep = compare()
    print(json.dumps(rep, indent=1, default=str))
    sys.exit(1 if rep["mismatches"] else 0)
