"""Validation test A1: a real anomaly is preserved by two independent paths (T-020).

Test A1 (docs/VALIDATION_PLAN.md section 3): `pct_of_normal` computed from Aqua alone and from converted S-NPP alone must have the
same direction (both above or both below normal), peak months at most 1 month apart, and overlapping 90% intervals. Thresholds are
locked (D-028); nothing here is tuned on a case.

The two paths are made from `harmonize.aggregate()` and `harmonize.records_from()` WITHOUT editing harmonize.py: the aggregated table
is filtered to one witness before the records are built (`restrict_witness`). The baseline is the D-028 baseline built in this module
from each path's own estimates. It is a STAND-IN for the T-014 products: `compare_paths()` takes two `entity_month`-shaped frames, so
the same criterion re-runs unchanged on the T-014 products.

Definitions (each is an [ASSUMPTION] where the plan is silent; see docs/validation/T-020-results.md):
  * baseline: same calendar month, years 2003-2022, empirical p25/p50/p75 (linear interpolation) over the years that have an estimate;
    fewer than 15 of the 20 years, or a median below 5 Aqua-equivalent cell-days, gives no baseline (D-028 steps 2 and 4);
  * peak month of a path: the month of the largest `pct_of_normal` in the analysis window (the earliest on a tie);
  * direction of a path: peak-window estimate (sum over the months) against the summed p75 (ABOVE) and the summed p25 (BELOW);
  * interval of a path: the peak-window estimate +/- 1.645 x sqrt(sum of the monthly sd squared), floored at 0, over the summed
    baseline medians (the baseline's own uncertainty is not propagated, D-028). Intervals that touch overlap.

    python pipeline/validation_a1.py [--case C1]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harmonize as hz

ROOT = Path(__file__).resolve().parents[1]
QA_DIR = ROOT / "data" / "interim" / "qa"
CONTRACT_VERSION = "0.1.1"
TEST_FAMILY = "A"
BASELINE_YEARS = (2003, 2022)
MIN_BASELINE_YEARS = 15        # D-028 step 2: fewer than 15 of the 20 baseline years gives no baseline
MIN_BASELINE_MEDIAN = 5.0      # D-028 step 4: below 5 Aqua-equivalent cell-days there is too little normal activity to judge
PEAK_MONTH_TOLERANCE = 1       # A1: peak months within +/- 1 month
PATH_WITNESS = {"aqua": "AQUA_MODIS", "snpp": "SNPP_VIIRS"}
ABOVE, BELOW, WITHIN = "ABOVE", "BELOW", "WITHIN"
Month = tuple[int, int]

# VALIDATION_PLAN.md section 2a (approved by the Lead 2026-11-14): box (W, S, E, N), analysis window, peak window (inclusive)
CASES: dict[str, dict] = {
    "C1": {"name": "Indonesia (Sumatra + Kalimantan)", "label": "Indonesia Sep-Oct 2015", "box": (95.0, -6.0, 119.0, 4.0),
           "analysis": ((2015, 6), (2015, 12)), "peak": ((2015, 9), (2015, 10)), "context_entity": ("COUNTRY", "IDN")},
    "C2": {"name": "Brazilian Amazon", "label": "Brazilian Amazon Aug 2019", "box": (-70.0, -12.0, -45.0, 0.0),
           "analysis": ((2019, 5), (2019, 11)), "peak": ((2019, 8), (2019, 9))},
    "C3": {"name": "Pantanal", "label": "Pantanal 2020", "box": (-59.0, -22.0, -54.0, -15.0),
           "analysis": ((2020, 6), (2020, 11)), "peak": ((2020, 8), (2020, 10))},
    "C4": {"name": "SE Australia", "label": "SE Australia Dec 2019-Jan 2020", "box": (145.0, -39.0, 154.0, -28.0),
           "analysis": ((2019, 9), (2020, 3)), "peak": ((2019, 12), (2020, 1))},
    "C5": {"name": "California", "label": "California Aug-Sep 2020", "box": (-124.5, 32.5, -114.0, 42.0),
           "analysis": ((2020, 6), (2020, 11)), "peak": ((2020, 8), (2020, 9))},
    "C6": {"name": "Sakha/Yakutia", "label": "Siberia (Sakha/Yakutia) 2021", "box": (105.0, 58.0, 150.0, 72.0),
           "analysis": ((2021, 5), (2021, 9)), "peak": ((2021, 7), (2021, 8))},
}


# ------------------------------------------------------------------------------------------------ months
def month_range(first: Month, last: Month) -> list[Month]:
    """Every (year, month) from `first` to `last`, both included."""
    out, (y, m) = [], first
    while (y, m) <= last:
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def month_index(year: int, month: int) -> int:
    return int(year) * 12 + int(month) - 1


# ------------------------------------------------------------------------------------------------ the paths
def restrict_witness(agg: pd.DataFrame, witness: str) -> pd.DataFrame:
    """The `aggregate()` table with only one witness left: the other witnesses (and Terra) are removed before the records are built."""
    if witness not in hz.WITNESSES:
        raise ValueError(f"{witness} is not one of the witnesses that enter the estimate: {hz.WITNESSES}")
    return agg[agg["witness"] == witness].copy()


def records_frame(records: list[dict]) -> pd.DataFrame:
    """`records_from()` output as an entity_month-shaped frame (numbers as floats, missing as NaN), sorted by month."""
    df = pd.DataFrame(records)
    if df.empty:
        return df
    for col in ("estimate", "sd", "ci90_low", "ci90_high"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values(["year", "month"]).reset_index(drop=True)


def path_records(cell_ids: list[str], months: list[Month], paths: hz.Paths, witnesses: tuple[str, ...] = ("AQUA_MODIS", "SNPP_VIIRS"),
                 entity_id: str = "A1", entity_name: str = "A1 box") -> dict[str, pd.DataFrame]:
    """Aggregate the cells once and return the single-witness record frames, keyed by witness (the two independent paths)."""
    ids = sorted(set(cell_ids))
    if not ids:
        raise ValueError("no cells in the box")
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    members = pd.DataFrame({"entity_type": "CUSTOM", "entity_id": entity_id, "entity_name": entity_name, "cell_id": ids})
    con.register("members_df", members)
    con.execute("CREATE TEMP TABLE members AS SELECT * FROM members_df")
    agg = hz.aggregate(con, paths, "members", months)
    out = {}
    for w in witnesses:
        recs = hz.records_from(restrict_witness(agg, w), {("CUSTOM", entity_id): len(ids)})
        out[w] = records_frame(recs)
    return out


def box_cells(cells: pd.DataFrame, box: tuple[float, float, float, float]) -> list[str]:
    """Analysis cells whose centre lies in the box (W, S, E, N), edges included."""
    w, s, e, n = box
    sel = cells[(cells.lon_c >= w) & (cells.lon_c <= e) & (cells.lat_c >= s) & (cells.lat_c <= n)]
    return sorted(sel["cell_id"])


# ------------------------------------------------------------------------------------------------ the baseline
def baseline_stats(values: list[float] | np.ndarray, years: tuple[int, int] = BASELINE_YEARS, min_years: int = MIN_BASELINE_YEARS,
                   min_median: float = MIN_BASELINE_MEDIAN) -> dict | None:
    """D-028 baseline from the yearly values of one calendar month (only the years that have an estimate are passed in).

    Empirical p25, p50, p75, linear interpolation between order statistics (numpy default). None if fewer than `min_years` values
    or if the median is below `min_median`.
    """
    v = np.asarray([x for x in values if x is not None and np.isfinite(x)], dtype=float)
    if len(v) < min_years:
        return None
    p25, p50, p75 = (float(x) for x in np.percentile(v, [25, 50, 75]))
    if p50 < min_median:
        return None
    return {"baseline_p25": p25, "baseline_median": p50, "baseline_p75": p75, "n_baseline_years": len(v)}


def attach_baseline(numer: pd.DataFrame, base: pd.DataFrame, years: tuple[int, int] = BASELINE_YEARS, min_years: int = MIN_BASELINE_YEARS,
                    min_median: float = MIN_BASELINE_MEDIAN) -> pd.DataFrame:
    """`numer` (the months to judge) with baseline_p25/median/p75, n_baseline_years and pct_of_normal added.

    The baseline of a calendar month is built from the rows of `base` of that calendar month in `years` that have an estimate
    (`base` is the path's own record frame for the normal case; any other frame is an explicit variant). pct_of_normal is
    estimate / baseline median x 100; NaN where there is no baseline or no estimate.
    """
    out = numer.copy().reset_index(drop=True)
    cols = ["baseline_p25", "baseline_median", "baseline_p75", "n_baseline_years"]
    for c in cols:
        out[c] = np.nan
    in_years = base[(base.year >= years[0]) & (base.year <= years[1]) & base.estimate.notna()]
    cache: dict[int, dict | None] = {}
    for i, r in out.iterrows():
        m = int(r["month"])
        if m not in cache:
            cache[m] = baseline_stats(in_years.loc[in_years.month == m, "estimate"].tolist(), years, min_years, min_median)
        st = cache[m]
        if st:
            for c in cols:
                out.at[i, c] = st[c]
    out["n_baseline_years"] = out["n_baseline_years"].fillna(0).astype(int) if len(out) else out["n_baseline_years"]
    with np.errstate(invalid="ignore", divide="ignore"):
        out["pct_of_normal"] = out["estimate"] / out["baseline_median"] * 100.0
    return out


# ------------------------------------------------------------------------------------------------ the criterion
def _window(df: pd.DataFrame, window: tuple[Month, Month]) -> pd.DataFrame:
    lo, hi = month_index(*window[0]), month_index(*window[1])
    idx = df["year"].astype(int) * 12 + df["month"].astype(int) - 1
    return df[(idx >= lo) & (idx <= hi)]


def summarize_path(df: pd.DataFrame, analysis: tuple[Month, Month], peak: tuple[Month, Month]) -> dict:
    """The A1 quantities of one path: peak month, and the peak-window direction, pct_of_normal and 90% interval.

    `ok` is False (with `reason`) when the path cannot be judged: no baseline in the analysis window, or a peak window with a month
    that has no estimate or no baseline.
    """
    res: dict = {"ok": False, "reason": None, "peak_month": None, "direction": None, "pct_of_normal": None, "pct_low": None, "pct_high": None,
                 "estimate": None, "baseline_median": None}
    if df is None or df.empty:
        res["reason"] = "no records"
        return res
    win = _window(df, analysis)
    judged = win[win["pct_of_normal"].notna()]
    if judged.empty:
        res["reason"] = "no month of the analysis window has a pct_of_normal (no estimate or no baseline)"
        return res
    top = judged.loc[judged["pct_of_normal"].idxmax()]      # idxmax takes the first maximum: the earliest month on a tie
    res["peak_month"] = f"{int(top['year'])}-{int(top['month']):02d}"
    res["peak_month_pct_of_normal"] = float(top["pct_of_normal"])
    need = month_range(*peak)
    pk = _window(df, peak)
    have = {(int(y), int(m)) for y, m in zip(pk.year, pk.month, strict=True)}
    cols = ["estimate", "sd", "baseline_median", "baseline_p25", "baseline_p75"]
    if not set(need) <= have or pk[cols].isna().any().any() or len(pk) != len(need):
        res["reason"] = "the peak window has a month with no estimate or no baseline"
        return res
    est = float(pk["estimate"].sum())
    med = float(pk["baseline_median"].sum())
    sd = float(np.sqrt((pk["sd"] ** 2).sum()))
    p25, p75 = float(pk["baseline_p25"].sum()), float(pk["baseline_p75"].sum())
    lo, hi = max(0.0, est - hz.Z90 * sd), est + hz.Z90 * sd
    res.update({"ok": True, "estimate": est, "baseline_median": med, "pct_of_normal": est / med * 100.0, "pct_low": lo / med * 100.0,
                "pct_high": hi / med * 100.0, "direction": ABOVE if est > p75 else (BELOW if est < p25 else WITHIN)})
    return res


def compare_paths(aqua: pd.DataFrame, snpp: pd.DataFrame, analysis: tuple[Month, Month], peak: tuple[Month, Month],
                  tolerance: int = PEAK_MONTH_TOLERANCE) -> dict:
    """The A1 criterion on two entity_month-shaped frames (one entity each): the Aqua-only and the S-NPP-only path.

    Needs year, month, estimate, sd, baseline_median, baseline_p25, baseline_p75, pct_of_normal (contract section 4 names; the T-014
    products have them). Returns the criteria and a status:
      PASS          both paths ABOVE or both BELOW, peak months at most `tolerance` apart, 90% intervals overlap;
      FAIL          both paths judged and at least one condition fails;
      INCONCLUSIVE  a path cannot be judged (no baseline, incomplete peak window), or both paths are WITHIN normal (nothing to preserve).
    """
    a, s = summarize_path(aqua, analysis, peak), summarize_path(snpp, analysis, peak)
    out: dict = {"aqua": a, "snpp": s, "same_direction": None, "peak_within_tolerance": None, "intervals_overlap": None,
                 "peak_month_distance": None, "status": "INCONCLUSIVE", "reasons": []}
    for name, p in (("Aqua-only", a), ("S-NPP-only", s)):
        if not p["ok"]:
            out["reasons"].append(f"{name} path cannot be judged: {p['reason']}")
    if not (a["ok"] and s["ok"]):
        return out
    out["same_direction"] = a["direction"] == s["direction"] and a["direction"] in (ABOVE, BELOW)
    ya, ma = a["peak_month"].split("-")
    ys, ms = s["peak_month"].split("-")
    out["peak_month_distance"] = abs(month_index(int(ya), int(ma)) - month_index(int(ys), int(ms)))
    out["peak_within_tolerance"] = out["peak_month_distance"] <= tolerance
    out["intervals_overlap"] = bool(a["pct_low"] <= s["pct_high"] and s["pct_low"] <= a["pct_high"])
    if a["direction"] == WITHIN and s["direction"] == WITHIN:
        out["reasons"].append("both paths are within normal: there is no anomaly to preserve")
        return out
    if out["same_direction"] and out["peak_within_tolerance"] and out["intervals_overlap"]:
        out["status"] = "PASS"
    else:
        out["status"] = "FAIL"
        for flag, text in (("same_direction", "directions differ or one path is within normal"),
                           ("peak_within_tolerance", f"peak months are {out['peak_month_distance']} months apart (limit {tolerance})"),
                           ("intervals_overlap", "the 90% intervals do not overlap")):
            if not out[flag]:
                out["reasons"].append(text)
    return out


# ------------------------------------------------------------------------------------------------ the case
def build_case_frames(case: dict, paths: hz.Paths | None = None) -> tuple[dict[str, tuple[pd.DataFrame, pd.DataFrame]], int]:
    """The (Aqua-only, S-NPP-only) frames of a case and the number of cells in its box, for the formal reading and two exploratory variants (all from the data).

    formal                the D-028 baseline built from each path's own estimates (the S-NPP-only path has 11 baseline years at most,
                          so it has no baseline: fewer than 15 of 20);
    shared_aqua_baseline  [exploratory] the S-NPP-only estimates against the Aqua-only path's baseline (the converted S-NPP is on the
                          Aqua-equivalent scale, D-005);
    snpp_own_min10        [exploratory] the S-NPP-only path against its own 2012-2022 baseline with the minimum lowered from 15 to 10.
    """
    paths = paths or hz.Paths()
    cells = pd.read_parquet(paths.products / "cells.parquet", columns=["cell_id", "lat_c", "lon_c"])
    ids = box_cells(cells, case["box"])
    analysis = month_range(*case["analysis"])
    cal_months = sorted({m for _, m in analysis})
    months = sorted(set(analysis) | {(y, m) for y in range(BASELINE_YEARS[0], BASELINE_YEARS[1] + 1) for m in cal_months})
    rec = path_records(ids, months, paths)
    aq, sn = rec["AQUA_MODIS"], rec["SNPP_VIIRS"]
    aq_win = _window(aq, case["analysis"]) if not aq.empty else aq
    sn_win = _window(sn, case["analysis"]) if not sn.empty else sn
    aq_f = attach_baseline(aq_win, aq)
    return ({"formal": (aq_f, attach_baseline(sn_win, sn)),
             "shared_aqua_baseline": (aq_f, attach_baseline(sn_win, aq)),
             "snpp_own_min10": (aq_f, attach_baseline(sn_win, sn, min_years=10))}, len(ids))


def _r(x, nd: int = 1):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), nd)


# ------------------------------------------------------------------------------------------------ the T-014 product
def product_frame(product: pd.DataFrame, entity_type: str, entity_id: str) -> pd.DataFrame:
    """The rows of one entity of the T-014 `entity_month` product, sorted by month, numbers as floats."""
    df = product[(product.entity_type == entity_type) & (product.entity_id == entity_id)].copy()
    for col in ("estimate", "sd", "ci90_low", "ci90_high", "baseline_median", "baseline_p25", "baseline_p75", "pct_of_normal", "p_above"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values(["year", "month"]).reset_index(drop=True)


def product_context(product: pd.DataFrame, entity_type: str, entity_id: str, case: dict) -> dict:
    """The COMBINED series of the T-014 product over the case window, with the A1 quantities of `summarize_path` (context, not a path)."""
    df = _window(product_frame(product, entity_type, entity_id), case["analysis"])
    summary = summarize_path(df, case["analysis"], case["peak"])
    months = [{"year": int(r.year), "month": int(r.month), "estimate": _r(r.estimate), "pct_of_normal": _r(r.pct_of_normal),
               "p_above": _r(r.p_above, 4), "verdict": r.verdict, "reason_codes": list(r.reason_codes), "witnesses_used": list(r.witnesses_used)}
              for r in df.itertuples()]
    return {"entity": f"{entity_type}:{entity_id}", "summary": {k: (_r(v) if isinstance(v, float) else v) for k, v in summary.items()}, "months": months}


def crosscheck_aqua_baseline(product: pd.DataFrame, aqua: pd.DataFrame, years: tuple[int, int] = BASELINE_YEARS, aqua_only_until: int = 2011) -> dict:
    """Does the Aqua-only stand-in reproduce the T-014 baseline where only Aqua contributes?

    `product` and `aqua` are frames of the SAME entity (the product's combined series, and the Aqua-only path from this module).
      * `estimates_2003_2011`: Aqua-only against the product's estimate, same month (both are Aqua-only there, so equal up to rounding);
      * `baseline_2003_2011`: p25/p50/p75 built from the two series over 2003-2011 only (the years where only Aqua contributes);
      * `baseline_2003_2022`: the stand-in's median (Aqua-only, all 20 years) against the product's `baseline_median` (combined series
        from 2012): they differ by construction after 2011, reported as a ratio.
    """
    def rel(a: float, b: float) -> float:
        return abs(a - b) / b if b else (0.0 if a == 0 else float("inf"))
    p = product[product.estimate.notna()]
    a = aqua[aqua.estimate.notna()]
    both = p.merge(a, on=["year", "month"], suffixes=("_p", "_a"))
    early = both[both.year <= aqua_only_until]
    d = [rel(x, y) for x, y in zip(early.estimate_a, early.estimate_p, strict=True)]
    out: dict = {"estimates_2003_2011": {"n": len(d), "max_rel_diff": max(d) if d else None, "median_rel_diff": float(np.median(d)) if d else None}}
    b_rel, per_month = [], []
    for m in range(1, 13):
        ep = p[(p.month == m) & (p.year >= years[0]) & (p.year <= aqua_only_until)].estimate
        ea = a[(a.month == m) & (a.year >= years[0]) & (a.year <= aqua_only_until)].estimate
        sp, sa = baseline_stats(ep.tolist(), years, 1, 0.0), baseline_stats(ea.tolist(), years, 1, 0.0)
        if sp and sa:
            b_rel.append(max(rel(sa[k], sp[k]) for k in ("baseline_p25", "baseline_median", "baseline_p75")))
    out["baseline_2003_2011"] = {"n_months": len(b_rel), "max_rel_diff": max(b_rel) if b_rel else None}
    prod_base = p[(p.year >= years[0]) & (p.year <= years[1])].groupby("month")["baseline_median"].first()
    stand = attach_baseline(pd.DataFrame({"year": 2015, "month": list(range(1, 13)), "estimate": 1.0}), a, years, MIN_BASELINE_YEARS, 0.0)
    for r in stand.itertuples():
        pb = prod_base.get(r.month)
        if pb is not None and pd.notna(pb) and pd.notna(r.baseline_median):
            per_month.append({"month": int(r.month), "aqua_only_median": _r(r.baseline_median), "product_median": _r(pb), "ratio": _r(r.baseline_median / pb, 3)})
    ratios = [x["ratio"] for x in per_month]
    out["baseline_2003_2022"] = {"n_months": len(ratios), "ratio_min": min(ratios) if ratios else None, "ratio_max": max(ratios) if ratios else None,
                                 "ratio_median": float(np.median(ratios)) if ratios else None, "per_month": per_month}
    return out


def entry_for(case_id: str, case: dict, frames: dict[str, tuple[pd.DataFrame, pd.DataFrame]], t014: dict | None = None) -> dict:
    """The contract section 6 test entry. `status` is NOT_RUN: the formal status needs the T-014 products (see `provisional_status`)."""
    results = {k: compare_paths(a, s, case["analysis"], case["peak"]) for k, (a, s) in frames.items() }
    formal = results["formal"]

    def block(r: dict) -> dict:
        return {"status": r["status"], "same_direction": r["same_direction"], "peak_within_tolerance": r["peak_within_tolerance"],
                "intervals_overlap": r["intervals_overlap"], "peak_month_distance": r["peak_month_distance"],
                "aqua_direction": r["aqua"]["direction"], "snpp_direction": r["snpp"]["direction"],
                "aqua_pct_of_normal": _r(r["aqua"]["pct_of_normal"]), "aqua_pct_90": [_r(r["aqua"]["pct_low"]), _r(r["aqua"]["pct_high"])],
                "snpp_pct_of_normal": _r(r["snpp"]["pct_of_normal"]), "snpp_pct_90": [_r(r["snpp"]["pct_low"]), _r(r["snpp"]["pct_high"])],
                "aqua_peak_month": r["aqua"]["peak_month"], "snpp_peak_month": r["snpp"]["peak_month"], "reasons": r["reasons"]}

    return {
        "test_id": f"A1-{case_id}",
        "family": TEST_FAMILY,
        "title": "Real anomaly preserved (two independent paths)",
        "case": case["label"],
        "criterion": "Same direction (both above or both below normal); peak month within +-1; 90% intervals overlap",
        "threshold": "pre-registered at G1 (D-028): same direction; peak month +-1; 90% intervals overlap; family pass >= 5 of 6 cases C1-C6",
        "measured": {"aqua_only_pct_of_normal": _r(formal["aqua"]["pct_of_normal"]), "snpp_only_pct_of_normal": _r(formal["snpp"]["pct_of_normal"]),
                     "aqua_only_peak_month": formal["aqua"]["peak_month"], "snpp_only_peak_month": formal["snpp"]["peak_month"],
                     "provisional_status": formal["status"], "baseline": "built in pipeline/validation_a1.py per path (D-028 rules); the T-014 product has no single-witness series",
                     "formal_reading": block(formal),
                     "exploratory": {k: block(v) for k, v in results.items() if k != "formal"},
                     **({"t014_product": t014} if t014 else {})},
        "status": "NOT_RUN",
        "notes": ("The two single-witness paths and their baselines are built in this module (the T-014 product holds only the combined "
                  "series); the combined T-014 product is used as context and to cross-check the Aqua-only baseline. The formal status stays "
                  "NOT_RUN until the Lead decides how the S-NPP-only path gets a baseline. See docs/validation/T-020-results.md."),
    }


def table(frame: pd.DataFrame) -> list[dict]:
    keep = ["year", "month", "estimate", "sd", "baseline_p25", "baseline_median", "baseline_p75", "n_baseline_years", "pct_of_normal"]
    return [{k: (None if pd.isna(r[k]) else (int(r[k]) if k in ("year", "month", "n_baseline_years") else float(r[k]))) for k in keep}
            for _, r in frame.iterrows()]


def t014_check(case: dict, paths: hz.Paths | None = None) -> dict | None:
    """Context and baseline cross-check against the T-014 `entity_month` product (None if the product has no harmonized estimates)."""
    paths = paths or hz.Paths()
    f = paths.products / "entity_month.parquet"
    ent = case.get("context_entity")
    if not f.exists() or not ent:
        return None
    product = pd.read_parquet(f)
    if product["estimate"].notna().sum() == 0:
        return None
    meta = json.loads((paths.products / "metadata.json").read_text(encoding="utf-8"))
    out = {"product_method_version": meta.get("method_version"), "context_combined_series": product_context(product, ent[0], ent[1], case)}
    cells = pd.read_parquet(paths.products / "cells.parquet", columns=["cell_id", "country_iso3"])
    ids = sorted(cells.loc[cells.country_iso3 == ent[1], "cell_id"])
    months = [(y, m) for y in range(BASELINE_YEARS[0], BASELINE_YEARS[1] + 1) for m in range(1, 13)]
    aqua = path_records(ids, months, paths, ("AQUA_MODIS",), ent[1], ent[1])["AQUA_MODIS"]
    out["crosscheck_aqua_only_baseline"] = {"entity": f"{ent[0]}:{ent[1]}", "n_cells": len(ids), **crosscheck_aqua_baseline(product_frame(product, *ent), aqua)}
    return out


def run(case_id: str = "C1", paths: hz.Paths | None = None, out_dir: Path = QA_DIR) -> dict:
    case = CASES[case_id]
    frames, n_cells = build_case_frames(case, paths)
    entry = entry_for(case_id, case, frames, t014_check(case, paths))
    out_dir.mkdir(parents=True, exist_ok=True)
    doc = {"contract_version": CONTRACT_VERSION, "method_version": hz.METHOD_VERSION + "+a1-provisional-baseline",
           "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "synthetic": False, "tests": [entry]}
    (out_dir / "T-020_validation_entries.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")
    tables = {k: {"aqua": table(a), "snpp": table(s)} for k, (a, s) in frames.items()}
    tables["n_cells"] = n_cells
    (out_dir / "T-020_a1_tables.json").write_text(json.dumps(tables, indent=2), encoding="utf-8")
    return entry


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--case", default="C1", choices=sorted(CASES))
    args = ap.parse_args()
    entry = run(args.case)
    m = entry["measured"]
    print(json.dumps({"test_id": entry["test_id"], "status": entry["status"], "provisional_status": m["provisional_status"],
                      "aqua_only_pct_of_normal": m["aqua_only_pct_of_normal"], "snpp_only_pct_of_normal": m["snpp_only_pct_of_normal"],
                      "formal_reading": m["formal_reading"], "exploratory": m["exploratory"]}, indent=2))


if __name__ == "__main__":
    main()
