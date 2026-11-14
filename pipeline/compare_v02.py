"""Method 0.2 against method 0.1: holdout error, D1 coverage and the A1 gap, and the adoption rule (T-020c, D-030 PROPOSED).

The rule was fixed by the Lead on PR #58 and recorded in D-030 before any v0.2 result existed. Adopt v0.2 only if ALL hold:
  1. the T-012 holdout median absolute log error of `ours` (day+night total) is no worse than v0.1 for regions AND countries;
  2. the D1 pooled 90% coverage (T-022: pooled day/night units of the fire regions) stays within 80 to 97%;
  3. the A1 gap |ln(S-NPP-only / Aqua-only peak-window estimate)| is strictly smaller in at least 3 of the 4 failed cases C3 to C6.
Everything is computed from the same functions as the earlier tasks (holdout.py, validation_d.py, validation_a1.py); v0.2 differs only
by the factors and by phi and kappa re-estimated on the fit periods with the factors.

    python pipeline/compare_v02.py        # needs data/interim/v02/activity_factors.parquet (python pipeline/conversion_v02.py)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conversion_v02 as cv
import harmonize as hz
import holdout as ho
import validation_a1 as va
import validation_d as vd

ROOT = Path(__file__).resolve().parents[1]
FAILED_CASES = ("C3", "C4", "C5", "C6")
MIN_FAILED_IMPROVED = 3
COVERAGE_TARGET = ho.COVERAGE_TARGET        # (0.80, 0.97)


# ------------------------------------------------------------------------------------------------ the decision (pure)
def decide(holdout_v01: dict, holdout_v02: dict, d1_coverage_v02: float, gaps_v01: dict, gaps_v02: dict) -> dict:
    """The adoption rule. holdout_*: {entity_type: median absolute log error of the day+night total}; gaps_*: {case: gap or None}.

    A gap that is missing (a case that cannot be judged) is not an improvement.
    """
    c1 = {et: {"v01": holdout_v01[et], "v02": holdout_v02[et], "no_worse": bool(holdout_v02[et] <= holdout_v01[et])} for et in holdout_v01}
    c1["passes"] = all(v["no_worse"] for k, v in c1.items() if k != "passes")
    c2 = {"coverage": d1_coverage_v02, "target": list(COVERAGE_TARGET),
          "passes": bool(d1_coverage_v02 is not None and np.isfinite(d1_coverage_v02)
                         and COVERAGE_TARGET[0] <= d1_coverage_v02 <= COVERAGE_TARGET[1])}
    cases = {}
    for c in FAILED_CASES:
        a, b = gaps_v01.get(c), gaps_v02.get(c)
        smaller = bool(a is not None and b is not None and np.isfinite(a) and np.isfinite(b) and b < a)
        cases[c] = {"gap_v01": a, "gap_v02": b, "smaller": smaller}
    n = sum(v["smaller"] for v in cases.values())
    c3 = {"cases": cases, "improved": n, "needed": MIN_FAILED_IMPROVED, "passes": n >= MIN_FAILED_IMPROVED}
    adopt = bool(c1["passes"] and c2["passes"] and c3["passes"])
    return {"condition_1_holdout": c1, "condition_2_d1": c2, "condition_3_a1_gap": c3, "adopt_v02": adopt,
            "outcome": "ADOPT_PROPOSAL" if adopt else "KEEP_V01"}


# ------------------------------------------------------------------------------------------------ holdout and D1
def read_holdout_inputs(paths: hz.Paths, factors: pd.DataFrame | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """`holdout.read_inputs` with optional activity factors (the global-ratio baseline `glob` does not depend on them)."""
    if factors is None:
        agg, glob, _ = ho.read_inputs(paths)
        return agg, glob
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    con.execute("SET memory_limit='4GB'")
    cells = f"read_parquet('{(paths.products / 'cells.parquet').as_posix()}')"
    con.execute(f"""CREATE TEMP TABLE members AS
        SELECT 'REGION' AS entity_type, fire_region AS entity_id, fire_region AS entity_name, cell_id FROM {cells} WHERE fire_region IS NOT NULL
        UNION ALL
        SELECT 'COUNTRY', country_iso3, country_iso3, cell_id FROM {cells} WHERE country_iso3 IS NOT NULL""")
    months = [(y, m) for y in range(ho.START[0], ho.END[0] + 1) for m in range(1, 13)]
    agg = hz.aggregate(con, paths, "members", months, factors)
    agg = agg[agg.witness.isin(["AQUA_MODIS", "SNPP_VIIRS"])].reset_index(drop=True)
    return agg, _glob(paths)


def _glob(paths: hz.Paths) -> pd.DataFrame:
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    cmw = f"read_parquet('{(paths.products / 'cell_month_witness.parquet').as_posix()}')"
    (y0, m0), (y1, m1) = ho.FITS["SNPP_VIIRS"]
    return con.execute(f"""SELECT year, month, daynight, witness, sum(cell_days) AS raw, bool_and(days_available = days_in_month) AS complete
        FROM {cmw} WHERE witness IN ('AQUA_MODIS', 'SNPP_VIIRS') AND daynight IN ('D', 'N')
          AND year * 100 + month BETWEEN {y0 * 100 + m0} AND {y1 * 100 + m1} GROUP BY year, month, daynight, witness""").df()


def holdout_and_d1(paths: hz.Paths, factors: pd.DataFrame | None, phi: dict | None, kappa: dict | None) -> dict:
    """The T-012 evaluation and the D1 pooled coverage for one method (factors None = v0.1 with the default phi and kappa)."""
    agg, glob = read_holdout_inputs(paths, factors)
    out: dict = {"phi": phi or hz.PHI, "kappa": kappa or hz.KAPPA, "holdout": {}}
    for et in ("REGION", "COUNTRY"):
        s = ho.evaluate(agg, glob, et, ho.MIN_CELL_DAYS, phi, kappa)
        u, t = _units(agg, glob, et, phi, kappa)
        out["holdout"][et] = {
            "male": {k: s["by_daynight"][k]["ours"].get("median_abs_log_error") for k in ("D", "N", "T")},
            "male_all_units": s["all"]["ours"].get("median_abs_log_error"),
            "median_ratio": {k: s["by_daynight"][k]["ours"].get("median_ratio") for k in ("D", "N", "T")},
            "units": {k: s["by_daynight"][k]["ours"].get("units") for k in ("D", "N", "T")},
            "baselines_male_T": {m: s["by_daynight"]["T"][m].get("median_abs_log_error") for m in ("raw", "glob")},
            "d1": vd.d1_level(u, t)}
    return out


def _units(agg, glob, entity_type, phi, kappa):
    ratios = ho.fit_global_ratios(glob)
    u = ho.add_predictions(ho.units_from_agg(agg[agg.entity_type == entity_type], ho.MIN_CELL_DAYS), ratios, phi, kappa)
    return u, ho.total_units(u)


# ------------------------------------------------------------------------------------------------ the A1 gap
def case_estimates(case: dict, paths: hz.Paths, factors: pd.DataFrame | None, phi: dict | None, kappa: dict | None) -> dict[str, pd.DataFrame]:
    """The Aqua-only and the S-NPP-only path records of a case (the T-020 construction, with optional factors)."""
    cells = pd.read_parquet(paths.products / "cells.parquet", columns=["cell_id", "lat_c", "lon_c"])
    ids = va.box_cells(cells, case["box"])
    analysis = va.month_range(*case["analysis"])
    cal_months = sorted({m for _, m in analysis})
    months = sorted(set(analysis) | {(y, m) for y in range(va.BASELINE_YEARS[0], va.BASELINE_YEARS[1] + 1) for m in cal_months})
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    con.register("members_df", pd.DataFrame({"entity_type": "CUSTOM", "entity_id": "A1", "entity_name": "A1 box", "cell_id": ids}))
    con.execute("CREATE TEMP TABLE members AS SELECT * FROM members_df")
    agg = hz.aggregate(con, paths, "members", months, factors)
    return {w: va.records_frame(hz.records_from(va.restrict_witness(agg, w), {("CUSTOM", "A1"): len(ids)}, None, phi, kappa))
            for w in ("AQUA_MODIS", "SNPP_VIIRS")}


def peak_sum(df: pd.DataFrame, peak) -> float | None:
    win = va._window(df, peak)
    need = va.month_range(*peak)
    have = {(int(y), int(m)) for y, m in zip(win.year, win.month, strict=True)}
    if not set(need) <= have or win.estimate.isna().any():
        return None
    return float(win.estimate.sum())


def a1_gap(rec: dict[str, pd.DataFrame], case: dict) -> dict:
    """gap = |ln(S-NPP-only / Aqua-only)| over the peak window, with both sums; also the shared-baseline A1 status (information only)."""
    a, s = peak_sum(rec["AQUA_MODIS"], case["peak"]), peak_sum(rec["SNPP_VIIRS"], case["peak"])
    gap = abs(float(np.log(s / a))) if a and s and a > 0 and s > 0 else None
    aq_w = va._window(rec["AQUA_MODIS"], case["analysis"])
    sn_w = va._window(rec["SNPP_VIIRS"], case["analysis"])
    aq_f = va.attach_baseline(aq_w, rec["AQUA_MODIS"])
    shared = va.compare_paths(aq_f, va.attach_baseline(sn_w, rec["AQUA_MODIS"]), case["analysis"], case["peak"])
    return {"aqua_peak": a, "snpp_peak": s, "ratio_snpp_over_aqua": (s / a if a and s else None), "gap": gap,
            "a1_status_shared_baseline": shared["status"], "a1_reasons": shared["reasons"]}


# ------------------------------------------------------------------------------------------------ the run
def run(paths: hz.Paths | None = None) -> dict:
    paths = paths or hz.Paths()
    factors = cv.load_factors()
    disp = hz.estimate_dispersion(paths, factors=factors)
    phi2, kappa2 = disp["phi"], disp["kappa"]
    print("v0.2 phi", phi2, "kappa", kappa2, flush=True)
    res: dict = {"factors": factors.to_dict(orient="records"), "dispersion_v02": disp}
    res["v01"] = holdout_and_d1(paths, None, None, None)
    print("v0.1 holdout done", flush=True)
    res["v02"] = holdout_and_d1(paths, factors, phi2, kappa2)
    print("v0.2 holdout done", flush=True)
    res["a1"] = {"v01": {}, "v02": {}}
    for cid in sorted(va.CASES):
        for key, f, ph, ka in (("v01", None, None, None), ("v02", factors, phi2, kappa2)):
            res["a1"][key][cid] = a1_gap(case_estimates(va.CASES[cid], paths, f, ph, ka), va.CASES[cid])
        print(cid, "gap v0.1", res["a1"]["v01"][cid]["gap"], "v0.2", res["a1"]["v02"][cid]["gap"], flush=True)
    res["decision"] = decide({et: res["v01"]["holdout"][et]["male"]["T"] for et in ("REGION", "COUNTRY")},
                             {et: res["v02"]["holdout"][et]["male"]["T"] for et in ("REGION", "COUNTRY")},
                             res["v02"]["holdout"]["REGION"]["d1"]["pooled"]["coverage_90"],
                             {c: res["a1"]["v01"][c]["gap"] for c in va.CASES}, {c: res["a1"]["v02"][c]["gap"] for c in va.CASES})
    cv.V02_DIR.mkdir(parents=True, exist_ok=True)
    (cv.V02_DIR / "compare_report.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    return res


if __name__ == "__main__":
    out = run()
    print(json.dumps(out["decision"], indent=1, default=str))
