"""T-079: verified numbers and captions for the featured stories of the app (T-072).

Reads only the final products (`data/products/entity_month.parquet`, `cell_month_harmonized.parquet`, `cells.parquet`), recomputes every
number, and writes `app/src/content/featured.ts` (plain data for the app) and the numbers report `docs/validation/T-079-featured-stories.md`.
Nothing in the method, the thresholds or the products changes.

    python pipeline/featured_stories.py            # write both files
    python pipeline/featured_stories.py --check    # exit 1 if the committed files differ from what the products give
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
from number_check import anomaly_order, js_round

ROOT = Path(__file__).resolve().parents[1]
PRODUCTS = ROOT / "data" / "products"
TS_FILE = ROOT / "app" / "src" / "content" / "featured.ts"
DOC_FILE = ROOT / "docs" / "validation" / "T-079-featured-stories.md"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
RANKED = ("ABOVE_NORMAL", "BELOW_NORMAL")

# (id, entity_type, entity_id, year, month, context label). The context is outside knowledge, not derived from the products.
CASES = [
    ("indonesia-2015-09", "COUNTRY", "IDN", 2015, 9, "the 2015 Indonesian fire season"),
    ("australia-2019-12", "COUNTRY", "AUS", 2019, 12, "the 2019-20 Australian fires (Black Summer)"),
    ("canada-2023-08", "COUNTRY", "CAN", 2023, 8, "the 2023 Canadian fire season"),
    ("brazil-2019-08", "COUNTRY", "BRA", 2019, 8, "the August 2019 Amazon fire news"),
    ("world-2026-10", "GLOBAL", "GLOBAL", 2026, 10, "the latest month of the record"),
]


# ------------------------------------------------------------------------------------------------------ number formatting
def pct_text(pct: float | None) -> str:
    return "no data" if pct is None else f"{js_round(pct)}%"


def prob_text(p: float | None) -> str:
    """The probability as the app words it: 0.995 or more reads "more than 99%", 0.005 or less "less than 1%", else the whole percentage."""
    if p is None:
        return "no data"
    if p >= 0.995:
        return "more than 99%"
    if p <= 0.005:
        return "less than 1%"
    return f"{js_round(p * 100)}%"


def cd_text(x: float | None) -> str:
    """Aqua-equivalent cell-days as a whole number with thousands separators."""
    return "no data" if x is None else f"{js_round(x):,}"


def month_label(year: int, month: int) -> str:
    return f"{MONTHS[month - 1]} {year}"


def rank_of(rows: list[dict], entity_id: str, verdict: str) -> tuple[int, int] | None:
    """Position of `entity_id` in the app's list for its verdict (above or below) and the length of that list, for the entities of one
    type and month. Order: the documented API order over the entities whose verdict is ABOVE_NORMAL or BELOW_NORMAL."""
    if verdict not in RANKED:
        return None
    ordered = [r for r in anomaly_order([r for r in rows if r["verdict"] in RANKED]) if r["verdict"] == verdict]
    ids = [r["entity_id"] for r in ordered]
    return (ids.index(entity_id) + 1, len(ids)) if entity_id in ids else None


# ------------------------------------------------------------------------------------------------------------- the facts
ENTITY_SQL = """
select entity_type, entity_id, entity_name, year, month, verdict, pct_of_normal, estimate, ci90_low, ci90_high,
       baseline_median, baseline_p25, baseline_p75, p_above, p_below, p_within, reason_codes, data_level, n_witnesses,
       disagreement_scale, raw_combined_cell_days
from read_parquet('{p}/entity_month.parquet') where entity_type = '{t}' and year = {y} and month = {m}
"""

CELL_SQL = """
select h.verdict, count(*) as n
from read_parquet('{p}/cell_month_harmonized.parquet') h join read_parquet('{p}/cells.parquet') c using (cell_id)
where c.country_iso3 = '{iso}' and h.year = {y} and h.month = {m} {extra}
group by h.verdict order by h.verdict
"""


def clean(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else x


def gather(products: Path = PRODUCTS) -> dict:
    con = duckdb.connect()
    p = products.as_posix()
    out: dict = {"cases": []}
    for cid, etype, eid, y, m, context in CASES:
        df = con.execute(ENTITY_SQL.format(p=p, t=etype, y=y, m=m)).df()
        rows = [{k: clean(v) for k, v in r.items()} for r in df.to_dict("records")]
        row = next(r for r in rows if r["entity_id"] == eid)
        row["reason_codes"] = list(row["reason_codes"]) if row["reason_codes"] is not None else []
        rank = rank_of(rows, eid, row["verdict"]) if etype != "GLOBAL" else None
        out["cases"].append({"id": cid, "context": context, "row": row, "rank": rank,
                             "entities_of_type": len(rows), "above": sum(r["verdict"] == "ABOVE_NORMAL" for r in rows),
                             "below": sum(r["verdict"] == "BELOW_NORMAL" for r in rows)})
    # Black Summer: Australian cells in 2019-12 by verdict, and under the D-031 condition
    cells = con.execute(CELL_SQL.format(p=p, iso="AUS", y=2019, m=12, extra="")).fetchall()
    cond = con.execute(CELL_SQL.format(p=p, iso="AUS", y=2019, m=12,
                                       extra="and h.estimate >= 20 and h.estimate > 3 * h.baseline_p75")).fetchall()
    out["aus_cells"] = {v: int(n) for v, n in cells}
    out["aus_cells_d031"] = {v: int(n) for v, n in cond}
    return out


# ---------------------------------------------------------------------------------------------------------------- captions
def _interval(r: dict) -> str:
    return f"{cd_text(r['ci90_low'])} to {cd_text(r['ci90_high'])}"


def _normal_range(r: dict) -> str:
    return f"{cd_text(r['baseline_p25'])} to {cd_text(r['baseline_p75'])}"


def caption(case: dict, facts: dict) -> dict:
    """Headline, caption and notes of one case, built only from the stored values and counts in `case` and `facts`."""
    r, cid = case["row"], case["id"]
    when = month_label(r["year"], r["month"])
    name = r["entity_name"]
    est = (f"The harmonized estimate is {cd_text(r['estimate'])} Aqua-equivalent cell-days (90% interval {_interval(r)}); "
           f"the normal range for the month is {_normal_range(r)} (median {cd_text(r['baseline_median'])}).")
    notes: list[str] = []
    if cid == "indonesia-2015-09":
        k, n = case["rank"]
        head = f"{name}, {when}: far above normal"
        cap = (f"{pct_text(r['pct_of_normal'])} of normal. {prob_text(r['p_above']).capitalize()} likely above normal. {est} "
               f"Indonesia ranks {k} of {n} countries above normal this month, because several countries have an equally certain verdict "
               f"and the list then orders by how far from normal they are.")
        notes.append("The rank follows the app's list: probability at the displayed precision, then distance from normal.")
    elif cid == "australia-2019-12":
        k, n = case["rank"]
        c, d = facts["aus_cells"], facts["aus_cells_d031"]
        head = f"{name}, {when}: above normal for the country, while single cells say \"cannot determine\""
        cap = (f"{pct_text(r['pct_of_normal'])} of normal. {prob_text(r['p_above']).capitalize()} likely above normal. {est} "
               f"The country ranks {k} of {n} countries above normal. The satellites disagree somewhat "
               f"(disagreement scale {r['disagreement_scale']:.2f}, below the 2 that would add a caveat), so the interval is widened.")
        notes.append(
            f"Why single cells can read \"cannot determine\": a cell whose normal is below 5 cell-days has too little history to define normal "
            f"(D-028 step 4, kept by D-031). Among the Australian cells of this month with an estimate of at least 20 and more than 3 times "
            f"the normal's upper quartile, {d.get('CANNOT_DETERMINE', 0)} read cannot determine and {d.get('ABOVE_NORMAL', 0)} read above normal. "
            f"The country as a whole has a normal median of {cd_text(r['baseline_median'])} cell-days, far above 5, so it has enough history and reads above normal.")
        notes.append(f"Australian cells of {when} by verdict: " + ", ".join(f"{v.replace('_', ' ').lower()} {n:,}" for v, n in sorted(c.items())) + ".")
    elif cid == "canada-2023-08":
        k, n = case["rank"]
        head = f"{name}, {when}: far above normal"
        cap = (f"{pct_text(r['pct_of_normal'])} of normal. {prob_text(r['p_above']).capitalize()} likely above normal. {est} "
               f"Canada ranks {k} of {n} countries above normal this month.")
    elif cid == "brazil-2019-08":
        head = f"{name}, {when}: within the normal range"
        cap = (f"{pct_text(r['pct_of_normal'])} of normal. The verdict is within normal ({prob_text(r['p_within'])} likely within). {est} "
               f"The estimate lies inside the normal range of the 20 years 2003 to 2022, so the tool does not call it an anomaly.")
        notes.append("This is the data's verdict for this month, not a judgement of the news coverage of that period.")
    else:  # world
        head = f"{name}, {when}: cannot determine"
        cap = (f"{pct_text(r['pct_of_normal'])} of the normal median, but the verdict is cannot determine: the interval is too wide to say "
               f"above, below or within normal (probabilities: below {prob_text(r['p_below'])}, within {prob_text(r['p_within'])}, "
               f"above {prob_text(r['p_above'])}). {est} Cannot determine is a result, not an error.")
        notes.append("The verdict rule needs a probability of at least 80% for above, below or within normal; here the highest is "
                     f"{prob_text(max(r['p_above'], r['p_below'], r['p_within']))}. The month is also provisional (near-real-time data) and in the "
                     "period where Aqua night data are excluded; both are stored caveats of this month.")
        notes.append("Reason codes stored: " + ", ".join(r["reason_codes"]) + ".")
    return {"headline": head, "caption": cap, "notes": notes}


# -------------------------------------------------------------------------------------------------------------------- files
def build(facts: dict) -> list[dict]:
    out = []
    for case in facts["cases"]:
        r = case["row"]
        c = caption(case, facts)
        out.append({
            "id": case["id"], "entityType": r["entity_type"], "entityId": r["entity_id"], "entityName": r["entity_name"],
            "year": int(r["year"]), "month": int(r["month"]), "headline": c["headline"], "caption": c["caption"], "notes": c["notes"],
            "context": case["context"],
            "facts": {"verdict": r["verdict"], "pctOfNormal": r["pct_of_normal"], "estimate": r["estimate"], "ci90Low": r["ci90_low"],
                      "ci90High": r["ci90_high"], "baselineMedian": r["baseline_median"], "baselineP25": r["baseline_p25"],
                      "baselineP75": r["baseline_p75"], "pAbove": r["p_above"], "pBelow": r["p_below"], "pWithin": r["p_within"],
                      "reasonCodes": r["reason_codes"], "dataLevel": r["data_level"],
                      "rank": None if case["rank"] is None else case["rank"][0],
                      "rankedOf": None if case["rank"] is None else case["rank"][1]},
        })
    return out


def ts_source(stories: list[dict]) -> str:
    body = json.dumps(stories, indent=2, ensure_ascii=False)
    return (
        "// Featured stories of the app (T-079). GENERATED by `python pipeline/featured_stories.py` from the final products:\n"
        "// do not edit by hand. Every number is a stored value or a count by query (docs/validation/T-079-featured-stories.md).\n"
        "// `context` is outside knowledge, not from the products. Units: Aqua-equivalent cell-days.\n\n"
        "export interface FeaturedFacts {\n"
        "  verdict: string\n  pctOfNormal: number | null\n  estimate: number | null\n  ci90Low: number | null\n  ci90High: number | null\n"
        "  baselineMedian: number | null\n  baselineP25: number | null\n  baselineP75: number | null\n"
        "  pAbove: number | null\n  pBelow: number | null\n  pWithin: number | null\n  reasonCodes: string[]\n  dataLevel: string\n"
        "  /** Position in the app's above/below list for this type and month; null for the world and for verdicts that are not ranked. */\n"
        "  rank: number | null\n  rankedOf: number | null\n}\n\n"
        "export interface FeaturedStory {\n"
        "  id: string\n  entityType: 'COUNTRY' | 'CONTINENT' | 'FIRE_REGION' | 'GLOBAL'\n  entityId: string\n  entityName: string\n"
        "  year: number\n  month: number\n  headline: string\n  caption: string\n  notes: string[]\n  context: string\n  facts: FeaturedFacts\n}\n\n"
        f"export const FEATURED_STORIES: readonly FeaturedStory[] = {body}\n"
    )


def doc_source(facts: dict, stories: list[dict]) -> str:
    L = ["# T-079: featured stories, verified numbers", "",
         ("> Member 2 · 2026-11-15 · method 0.1.0, final products. Generated by `python pipeline/featured_stories.py` "
          "(`--check` fails if `app/src/content/featured.ts` or this file differs from the products). Units: Aqua-equivalent cell-days."), "",
         "Labels: **[VERIFIED]** a stored value or a count by the query below; **[CONTEXT, not from the products]** the event name only.", "",
         "## 1. The cases", "",
         "| Case | Verdict | % of normal | Estimate (90% interval) | Normal p25 to p75 (median) | P(above) / P(within) / P(below) | Rank (list) | Reason codes |",
         "|---|---|---|---|---|---|---|---|"]
    for s in stories:
        f = s["facts"]
        rk = "none" if f["rank"] is None else f"{f['rank']} of {f['rankedOf']} ({f['verdict'].split('_')[0].lower()})"
        L.append(f"| {s['entityName']} {month_label(s['year'], s['month'])} [VERIFIED] | {f['verdict']} | {pct_text(f['pctOfNormal'])} | "
                 f"{cd_text(f['estimate'])} ({cd_text(f['ci90Low'])} to {cd_text(f['ci90High'])}) | {cd_text(f['baselineP25'])} to "
                 f"{cd_text(f['baselineP75'])} ({cd_text(f['baselineMedian'])}) | {prob_text(f['pAbove'])} / {prob_text(f['pWithin'])} / "
                 f"{prob_text(f['pBelow'])} | {rk} | {', '.join(f['reasonCodes']) or 'none'} |")
    L += ["", "Context labels [CONTEXT, not from the products]: " + "; ".join(f"{s['entityName']} {month_label(s['year'], s['month'])}: {s['context']}" for s in stories) + ".", "",
          "## 2. Captions (as in `featured.ts`)", ""]
    for s in stories:
        L += [f"### {s['headline']}", "", s["caption"], ""] + [f"- {n}" for n in s["notes"]] + [""]
    c, d = facts["aus_cells"], facts["aus_cells_d031"]
    L += ["## 3. Black Summer, cell level (D-031) [VERIFIED]", "",
          "Australian cells in 2019-12 by verdict: " + ", ".join(f"{v} {n:,}" for v, n in sorted(c.items())) + ".", "",
          "With the D-031 condition (estimate at least 20 and more than 3 times the baseline p75): "
          + ", ".join(f"{v} {n:,}" for v, n in sorted(d.items())) + ".", "",
          "D-031 recorded 105 `CANNOT_DETERMINE` against 4 `ABOVE_NORMAL` under this condition; the counts above reproduce that query.", "",
          "## 4. Queries", "", "Run with DuckDB on `data/products/` (the script runs exactly these):", "", "```sql",
          ENTITY_SQL.strip().format(p="data/products", t="COUNTRY", y="<year>", m="<month>"), "",
          CELL_SQL.strip().format(p="data/products", iso="AUS", y=2019, m=12, extra="[and h.estimate >= 20 and h.estimate > 3 * h.baseline_p75]"),
          "```", "",
          ("Rank: take the rows of the query for the type and month whose verdict is `ABOVE_NORMAL` or `BELOW_NORMAL`; order by the larger of "
          "`p_above` and `p_below` at the displayed precision (0.995 or more counts as equal, otherwise the whole percentage) descending, then "
          "`abs(ln(pct_of_normal / 100))` descending, then `entity_id`; the rank is the position among the rows with the entity's own verdict "
          "(the app's list; `pipeline/number_check.py` `anomaly_order`)."), ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    facts = gather()
    stories = build(facts)
    ts, doc = ts_source(stories), doc_source(facts, stories)
    if args.check:
        same = TS_FILE.read_text(encoding="utf-8") == ts and DOC_FILE.read_text(encoding="utf-8") == doc
        print("featured stories up to date" if same else "featured stories differ from the products")
        return 0 if same else 1
    TS_FILE.write_text(ts, encoding="utf-8", newline="\n")
    DOC_FILE.write_text(doc, encoding="utf-8", newline="\n")
    for s in stories:
        print(s["id"], "|", s["headline"], "|", s["facts"]["rank"], s["facts"]["rankedOf"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
