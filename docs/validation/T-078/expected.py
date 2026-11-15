"""T-078: the numbers the finished UI should show for five areas and months, computed from the products with DuckDB and the
formatting rules of docs/NUMBER_INVENTORY.md (JavaScript rounding emulated by pipeline/number_check.py). It writes
app/public/_t078/expected.json (a scratch file, never committed); `compare.js` then compares it, in the real app in the browser,
with what the page shows.

    python docs/validation/T-078/expected.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline"))
from number_check import js_round, js_to_fixed

PRODUCTS = (ROOT / "data" / "products").as_posix()
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
WITNESS = {"AQUA_MODIS": "Aqua MODIS", "TERRA_MODIS": "Terra MODIS (raw only)", "SNPP_VIIRS": "S-NPP VIIRS", "NOAA20_VIIRS": "NOAA-20 VIIRS",
           "NOAA21_VIIRS": "NOAA-21 VIIRS (reserved)"}
VERDICT = {"ABOVE_NORMAL": ("Above normal", "above"), "BELOW_NORMAL": ("Below normal", "below"), "WITHIN_NORMAL": ("Within normal", "within"),
           "CANNOT_DETERMINE": ("Cannot determine", None), "NO_DETECTED_ACTIVITY": ("No detected activity", None)}
CASES = [("COUNTRY", "IDN", 2015, 9), ("COUNTRY", "AUS", 2019, 12), ("COUNTRY", "CAN", 2023, 8), ("COUNTRY", "BRA", 2019, 8), ("GLOBAL", "GLOBAL", 2026, 10)]
FIRST, LATEST = (2002, 7), (2026, 11)


def one(x):
    return "no data" if x is None else js_to_fixed(x, 1)


def whole(x):
    return f"{js_round(x):,}"


def prob_text(p):
    if p >= 0.995:
        return "more than 99%"
    if p <= 0.005:
        return "less than 1%"
    return f"{js_round(p * 100)}%"


def ordinal(n):
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def window(sel):
    idx = lambda ym: ym[0] * 12 + ym[1] - 1
    back = lambda i: (i // 12, i % 12 + 1)
    end = min(idx(LATEST), idx(sel) + 3)
    start = end - 11
    if start < idx(FIRST):
        start = idx(FIRST)
        end = min(idx(LATEST), start + 11)
    return [back(i) for i in range(start, end + 1)]


def main():
    con = duckdb.connect()
    out = []
    for etype, eid, y, m in CASES:
        rows = con.execute(f"""select year, month, entity_name, verdict, pct_of_normal, estimate, ci90_low, ci90_high, baseline_p25, baseline_median,
            baseline_p75, p_above, p_below, p_within, witnesses_used, data_level, reason_codes, raw_combined_cell_days
            from read_parquet('{PRODUCTS}/entity_month.parquet') where entity_type='{etype}' and entity_id='{eid}' order by year, month""").fetchall()
        cols = ["year", "month", "name", "verdict", "pct", "est", "lo", "hi", "p25", "med", "p75", "pa", "pb", "pw", "wit", "level", "reasons", "raw"]
        recs = [dict(zip(cols, r, strict=True)) for r in rows]
        by = {(r["year"], r["month"]): r for r in recs}
        r = by[(y, m)]
        label, which = VERDICT[r["verdict"]]
        prob = None
        if which is not None:
            p = {"above": r["pa"], "below": r["pb"], "within": r["pw"]}[which]
            s = f"{prob_text(p)} likely {which} normal"
            prob = s[0].upper() + s[1:] + "."
        summary = {"title": f"{r['name']}, {MONTHS[m - 1]} {y}", "verdict": label, "prob": prob,
                   "big": None if r["pct"] is None else f"{js_round(r['pct'])}% of normal",
                   "estimate": one(r["est"]), "interval": f"{one(r['lo'])} to {one(r['hi'])}",
                   "satellites": ", ".join(WITNESS[w] for w in r["wit"]), "reasons": list(r["reasons"]), "level": r["level"]}
        spark = []
        for yy, mm in window((y, m)):
            q = by.get((yy, mm))
            est = None if q is None else q["est"]
            rng = "not available" if q is None or q["p25"] is None or q["p75"] is None else f"{one(q['p25'])} to {one(q['p75'])}"
            spark.append([f"{MONTHS[mm - 1]} {yy}", "no data" if est is None else one(est), rng])
        annual = {}
        for q in recs:
            if q["est"] is None:
                continue
            a = annual.setdefault(q["year"], [0, 0.0, 0.0])
            a[0] += 1
            a[1] += q["est"]
            a[2] += q["raw"]
        annual_rows = [[f"{yr}{' (partial)' if a[0] < 12 else ''}", str(a[0]), whole(a[2]), whole(a[1])] for yr, a in sorted(annual.items())]
        season = []
        for mm in range(1, 13):
            of = [q for q in recs if q["month"] == mm]
            sel = by.get((y, mm))
            base = sel if sel is not None and sel["med"] is not None else next((q for q in of if q["med"] is not None), None)
            cell = lambda v: "no data" if v is None else whole(v)
            season.append([MONTHS[mm - 1], cell(None if base is None else base["p25"]), cell(None if base is None else base["med"]),
                           cell(None if base is None else base["p75"]), cell(None if sel is None else sel["est"])])
        of_month = [q for q in recs if q["month"] == m and q["est"] is not None]
        rank = 1 + sum(q["est"] > r["est"] for q in of_month)
        have = {q["year"] for q in of_month}
        yrs = [q["year"] for q in recs]
        missing = [yy for yy in range(min(yrs), max(yrs) + 1) if yy not in have]
        tied = sorted(q["year"] for q in of_month if q["year"] != y and q["est"] == r["est"])
        ranks = [f"{MONTHS[m - 1]} {y} is the {ordinal(rank)} highest {MONTHS[m - 1]} of the record ({len(of_month)} years with an estimate)."]
        if tied:
            ranks.append(f"Tied with {', '.join(map(str, tied))}: the same estimate.")
        if missing:
            ranks.append(f"No estimate for {MONTHS[m - 1]} in {', '.join(map(str, missing))}.")
        if r["level"] != "SP":
            ranks.append("This month is provisional (near-real-time data) and may change.")
        coverage = None
        if etype == "GLOBAL":  # the panel counts every analysis cell of the month (exact only for the world, PR #85)
            n, determinable = con.execute(f"""select count(*), count(*) filter (where verdict <> 'CANNOT_DETERMINE')
                from read_parquet('{PRODUCTS}/cell_month_harmonized.parquet') where year={y} and month={m}""").fetchone()
            by_verdict = dict(con.execute(f"""select verdict, count(*) from read_parquet('{PRODUCTS}/cell_month_harmonized.parquet')
                where year={y} and month={m} group by 1""").fetchall())
            coverage = {"line": f"{js_round(determinable / n * 100)}% of {n:,} cells have a determinable verdict", "by_verdict": by_verdict}
        summary["raw"] = {"pct": r["pct"], "est": r["est"], "lo": r["lo"], "hi": r["hi"], "p_above": r["pa"], "p_below": r["pb"], "p_within": r["pw"]}
        out.append({"id": f"{etype}:{eid}", "area": f"{etype}:{eid}", "month": f"{y}-{m:02d}", "summary": summary, "spark": spark,
                    "annual": annual_rows, "season": season, "rank": ranks, "coverage": coverage})
    dest = ROOT / "app" / "public" / "_t078"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "expected.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", dest / "expected.json", [c["id"] for c in out])


if __name__ == "__main__":
    main()
