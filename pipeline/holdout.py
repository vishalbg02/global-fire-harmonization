"""Holdout evaluation 2017-2021: predict Aqua cell-days from S-NPP (T-012, part A).

Units are fire-region-months and country-months in 2017-01 to 2021-12 where Aqua and S-NPP both have a complete month, day and
night separately. The actual value is the Aqua cell-day count. Three predictions are compared:

  ours  the converted S-NPP estimate (T-011 ratios, T-013 aggregation);
  raw   the naive raw merge: the raw S-NPP cell-days;
  glob  one global ratio per day/night and season (sum Aqua / sum S-NPP raw over the globe), fitted ONLY on S-NPP's fit period
        2012-01 to 2016-12 and applied to the raw S-NPP cell-days.

Nothing is fitted on 2017-2021. The 90% interval of `ours` is  pred +/- 1.645 x sqrt(var_pred + var_aqua)  with
var_pred = phi x vc + kappa x e^2 + vr of the S-NPP row (vc: counting variance at phi = 1, e: the converted estimate, vr: shared
ratio variance) and var_aqua = phi x vc + kappa x actual^2 of the Aqua row (an estimate with ratio 1). Coverage is counted per
day/night unit and for the day+night total (variances summed), for three variance variants: with_phi_kappa (the T-013 model,
harmonize.PHI and KAPPA), with_phi_only (harmonize.PHI_ONLY, kappa 0) and poisson_only (phi 1, kappa 0). Units need at least `min_cell_days` Aqua cell-days (20 by default; sensitivity at 5 and 100). Where a prediction
is 0 the log error uses a floor of 1 cell-day (assumption, the same floor as the variance floor of T-013).

    python pipeline/holdout.py     # writes data/interim/qa/holdout_report.json and prints a summary
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harmonize as hz
from calibration import FITS, SEASON_OF

ROOT = Path(__file__).resolve().parents[1]
Z90 = hz.Z90
START, END = (2017, 1), (2021, 12)
MIN_CELL_DAYS = 20.0
SENSITIVITY = (5.0, 100.0)
FLOOR = 1.0
METHODS = ("ours", "raw", "glob")
LABEL = {"ours": "converted S-NPP (T-011/T-013)", "raw": "naive raw merge", "glob": "one global ratio"}
COVERAGE_TARGET = (0.80, 0.97)
ONE = {"D": 1.0, "N": 1.0}
VARIANTS = {"with_phi_kappa": "var_ours", "with_phi_only": "var_phionly", "poisson_only": "var_pois"}


# ------------------------------------------------------------------------------------------------ pure numeric parts
def _ym(year, month):
    return np.asarray(year) * 100 + np.asarray(month)


def units_from_agg(agg: pd.DataFrame, min_cell_days: float = MIN_CELL_DAYS, start=START, end=END) -> pd.DataFrame:
    """One row per entity x month x day/night inside [start, end] where Aqua and S-NPP are both complete and Aqua has enough cell-days.

    `agg` is the output of harmonize.aggregate(). Columns: actual (Aqua cell-days, ratio 1), vc_a, raw, e, vc_s, vr_s (S-NPP).
    """
    a = agg[agg.witness == "AQUA_MODIS"]
    s = agg[agg.witness == "SNPP_VIIRS"]
    keys = ["entity_type", "entity_id", "year", "month", "daynight"]
    a = a[keys + ["e", "vc", "complete"]].rename(columns={"e": "actual", "vc": "vc_a", "complete": "ok_a"})
    s = s[keys + ["raw", "e", "vc", "vr", "complete"]].rename(columns={"vc": "vc_s", "vr": "vr_s", "complete": "ok_s"})
    u = a.merge(s, on=keys, how="inner")
    ym = _ym(u.year, u.month)
    keep = u.ok_a.astype(bool) & u.ok_s.astype(bool) & (ym >= _ym(*start)) & (ym <= _ym(*end)) & (u.actual >= min_cell_days)
    u = u[keep].drop(columns=["ok_a", "ok_s"]).copy()
    u["season"] = u.month.map(SEASON_OF)
    return u.reset_index(drop=True)


def fit_global_ratios(glob: pd.DataFrame, fit=FITS["SNPP_VIIRS"]) -> dict[tuple[str, str], float]:
    """One ratio per (day/night, season): sum Aqua / sum S-NPP raw over the globe, complete months of S-NPP's fit period only.

    `glob`: year, month, daynight, witness, raw, complete (globally summed). Rows outside the fit period are ignored.
    """
    (y0, m0), (y1, m1) = fit
    ym = _ym(glob.year, glob.month)
    g = glob[(ym >= _ym(y0, m0)) & (ym <= _ym(y1, m1)) & glob.complete.astype(bool)]
    w = g.pivot_table(index=["year", "month", "daynight"], columns="witness", values="raw", aggfunc="sum")
    w = w.dropna(subset=["AQUA_MODIS", "SNPP_VIIRS"]).reset_index()
    w["season"] = w.month.map(SEASON_OF)
    out = {}
    for (dn, season), grp in w.groupby(["daynight", "season"]):
        if grp.SNPP_VIIRS.sum() > 0:
            out[(dn, season)] = float(grp.AQUA_MODIS.sum() / grp.SNPP_VIIRS.sum())
    return out


def _var_ours(u: pd.DataFrame, phi: dict[str, float], kappa: dict[str, float]) -> pd.Series:
    """var_pred + var_aqua per day/night unit: phi x vc_s + kappa x e_s^2 + vr_s  plus  phi x vc_a + kappa x actual^2."""
    p, k = u.daynight.map(phi).astype(float), u.daynight.map(kappa).astype(float)
    return p * u.vc_s + k * u.e**2 + u.vr_s + p * u.vc_a + k * u.actual**2


def add_predictions(u: pd.DataFrame, ratios: dict[tuple[str, str], float], phi: dict[str, float] | None = None,
                    kappa: dict[str, float] | None = None) -> pd.DataFrame:
    """Predictions of the three methods and the variances of ours for the three variants (with_phi_kappa: `phi`/`kappa`, default
    harmonize.PHI/KAPPA; with_phi_only: harmonize.PHI_ONLY, kappa 0; poisson_only: phi 1, kappa 0). Units without a global ratio drop out."""
    phi = phi or hz.PHI
    kappa = hz.KAPPA if kappa is None else kappa
    u = u.copy()
    r = np.array([ratios.get((d, s), np.nan) for d, s in zip(u.daynight, u.season, strict=True)])
    u["pred_ours"], u["pred_raw"], u["pred_glob"] = u.e, u.raw.astype(float), u.raw * r
    u["var_ours"] = _var_ours(u, phi, kappa)
    u["var_phionly"] = _var_ours(u, hz.PHI_ONLY, hz.KAPPA0)
    u["var_pois"] = _var_ours(u, ONE, hz.KAPPA0)
    return u[np.isfinite(u.pred_glob)].reset_index(drop=True)


def total_units(u: pd.DataFrame) -> pd.DataFrame:
    """Day + night total: estimates and variances summed, for entity-months where both day and night units exist (D and N independent)."""
    keys = ["entity_type", "entity_id", "year", "month"]
    cols = ["actual", "pred_ours", "pred_raw", "pred_glob", "var_ours", "var_phionly", "var_pois"]
    g = u.groupby(keys)
    t = g[cols].sum()
    t = t[g.daynight.nunique() == 2].reset_index()
    t["daynight"] = "T"
    return t


def log_err(pred, actual) -> np.ndarray:
    return np.log(np.maximum(np.asarray(pred, float), FLOOR) / np.asarray(actual, float))


def metrics(u: pd.DataFrame, method: str) -> dict:
    """Units, median and 5th/95th percentile of predicted/actual, median absolute log error, bias by year (median log(pred/actual))."""
    if len(u) == 0:
        return {"units": 0}
    pred, act = u[f"pred_{method}"].to_numpy(float), u.actual.to_numpy(float)
    ratio, le = pred / act, log_err(pred, act)
    by_year = {int(y): float(np.median(le[(u.year == y).to_numpy()])) for y in sorted(u.year.unique())}
    return {"units": len(u), "median_ratio": float(np.median(ratio)), "p05_ratio": float(np.percentile(ratio, 5)),
            "p95_ratio": float(np.percentile(ratio, 95)), "median_abs_log_error": float(np.median(np.abs(le))),
            "bias_by_year": by_year}


def coverage(actual, pred, var_pred, var_aqua=0.0) -> float:
    """Share of actual values inside pred +/- 1.645 x sqrt(var_pred + var_aqua)."""
    actual, pred = np.asarray(actual, float), np.asarray(pred, float)
    half = Z90 * np.sqrt(np.asarray(var_pred, float) + np.asarray(var_aqua, float))
    return float(np.mean(np.abs(actual - pred) <= half)) if len(actual) else float("nan")


def coverage_of(u: pd.DataFrame, var_col: str) -> dict:
    if len(u) == 0:
        return {"units": 0}
    c = coverage(u.actual, u.pred_ours, u[var_col])
    return {"units": len(u), "coverage": c, "within_target": bool(COVERAGE_TARGET[0] <= c <= COVERAGE_TARGET[1])}


def summarise(u: pd.DataFrame, t: pd.DataFrame) -> dict:
    """Metrics of the three methods and coverage, for a set of D/N units `u` and their totals `t`."""
    out = {"all": {}, "by_daynight": {}, "by_group": {}, "coverage": {}}
    out["all"] = {m: metrics(u, m) for m in METHODS}
    for dn in ("D", "N"):
        out["by_daynight"][dn] = {m: metrics(u[u.daynight == dn], m) for m in METHODS}
    for (eid, dn), g in u.groupby(["entity_id", "daynight"]):
        out["by_group"][f"{eid}|{dn}"] = {m: metrics(g, m) for m in METHODS}
    for eid, g in t.groupby("entity_id"):
        out["by_group"][f"{eid}|T"] = {m: metrics(g, m) for m in METHODS}
    out["by_daynight"]["T"] = {m: metrics(t, m) for m in METHODS}
    for label, col in VARIANTS.items():
        c = {"all_daynight_units": coverage_of(u, col), "total": coverage_of(t, col), "by_daynight": {}, "by_region": {}}
        for dn in ("D", "N"):
            c["by_daynight"][dn] = coverage_of(u[u.daynight == dn], col)
        for eid, g in u.groupby("entity_id"):
            c["by_region"][eid] = coverage_of(g, col)
        c["by_region_total"] = {eid: coverage_of(g, col) for eid, g in t.groupby("entity_id")}
        out["coverage"][label] = c
    return out


def losses(summary: dict, min_units: int = 30) -> list[dict]:
    """Groups where `ours` has a larger median absolute log error than a baseline."""
    out = []
    for key, mm in summary["by_group"].items():
        if mm["ours"].get("units", 0) < min_units:
            continue
        e = {m: mm[m]["median_abs_log_error"] for m in METHODS}
        worse = [m for m in ("raw", "glob") if e["ours"] > e[m]]
        if worse:
            out.append({"group": key, "units": mm["ours"]["units"], "worse_than": worse, **{f"mae_{m}": e[m] for m in METHODS}})
    return out


def evaluate(agg: pd.DataFrame, glob: pd.DataFrame, entity_type: str, min_cell_days: float, phi: dict[str, float] | None = None,
             kappa: dict[str, float] | None = None) -> dict:
    """The whole evaluation for one entity type and one threshold, from DataFrames."""
    ratios = fit_global_ratios(glob)
    u = add_predictions(units_from_agg(agg[agg.entity_type == entity_type], min_cell_days), ratios, phi, kappa)
    t = total_units(u)
    # day+night totals need Aqua >= threshold in total (each D/N unit already has it); keep the units as selected
    s = summarise(u, t)
    s["min_cell_days"] = min_cell_days
    s["entity_type"] = entity_type
    s["losses"] = losses(s)
    return s


# ------------------------------------------------------------------------------------------------ data access (thin)
def read_inputs(paths: hz.Paths | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Aggregated S-NPP and Aqua rows for fire regions and countries in 2017-2021, and the global monthly sums for the fit period."""
    paths = paths or hz.Paths()
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    con.execute("SET memory_limit='4GB'")
    cells = f"read_parquet('{(paths.products / 'cells.parquet').as_posix()}')"
    cmw = f"read_parquet('{(paths.products / 'cell_month_witness.parquet').as_posix()}')"
    con.execute(f"""CREATE TEMP TABLE members AS
        SELECT 'REGION' AS entity_type, fire_region AS entity_id, fire_region AS entity_name, cell_id FROM {cells} WHERE fire_region IS NOT NULL
        UNION ALL
        SELECT 'COUNTRY', country_iso3, country_iso3, cell_id FROM {cells} WHERE country_iso3 IS NOT NULL""")
    months = [(y, m) for y in range(START[0], END[0] + 1) for m in range(1, 13)]
    agg = hz.aggregate(con, paths, "members", months)
    agg = agg[agg.witness.isin(["AQUA_MODIS", "SNPP_VIIRS"])].reset_index(drop=True)
    (y0, m0), (y1, m1) = FITS["SNPP_VIIRS"]
    glob = con.execute(f"""SELECT year, month, daynight, witness, sum(cell_days) AS raw, bool_and(days_available = days_in_month) AS complete
        FROM {cmw} WHERE witness IN ('AQUA_MODIS', 'SNPP_VIIRS') AND daynight IN ('D', 'N')
          AND year * 100 + month BETWEEN {y0 * 100 + m0} AND {y1 * 100 + m1}
        GROUP BY year, month, daynight, witness""").df()
    return agg, glob, fit_global_ratios(glob)


def run(paths: hz.Paths | None = None, phi: dict[str, float] | None = None, kappa: dict[str, float] | None = None) -> dict:
    paths = paths or hz.Paths()
    phi = phi or hz.PHI
    kappa = hz.KAPPA if kappa is None else kappa
    agg, glob, ratios = read_inputs(paths)
    out: dict = {"phi": phi, "kappa": kappa, "phi_only": hz.PHI_ONLY, "window": "2017-01..2021-12", "min_cell_days": MIN_CELL_DAYS, "sensitivity_min_cell_days": list(SENSITIVITY),
                 "global_ratios_fit_2012_2016": {f"{d}|{s}": v for (d, s), v in sorted(ratios.items())},
                 "coverage_target": list(COVERAGE_TARGET), "units": {}}
    for et in ("REGION", "COUNTRY"):
        res = {"main": evaluate(agg, glob, et, MIN_CELL_DAYS, phi, kappa), "sensitivity": {}}
        for thr in SENSITIVITY:
            s = evaluate(agg, glob, et, thr, phi, kappa)
            res["sensitivity"][str(int(thr))] = {k: s[k] for k in ("all", "by_daynight", "coverage", "losses")}
        out["units"][et] = res
    (paths.products.parent / "interim" / "qa").mkdir(parents=True, exist_ok=True)
    (paths.products.parent / "interim" / "qa" / "holdout_report.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


def _fmt(m: dict) -> str:
    return (f"n={m['units']:>5} med={m['median_ratio']:.3f} p05={m['p05_ratio']:.3f} p95={m['p95_ratio']:.3f} "
            f"MALE={m['median_abs_log_error']:.3f}") if m.get("units") else "n=0"


def print_summary(out: dict) -> None:
    for et, res in out["units"].items():
        s = res["main"]
        print(f"== {et}-months, Aqua >= {s['min_cell_days']:g} cell-days")
        for dn in ("D", "N", "T"):
            for m in METHODS:
                print(f"  {dn} {m:<5} {_fmt(s['by_daynight'][dn][m])}")
        for label in VARIANTS:
            c = s["coverage"][label]
            print(f"  coverage {label:<14}: D/N units {c['all_daynight_units'].get('coverage', float('nan')):.3f}, "
                  f"D {c['by_daynight']['D'].get('coverage', float('nan')):.3f}, N {c['by_daynight']['N'].get('coverage', float('nan')):.3f}, "
                  f"total {c['total'].get('coverage', float('nan')):.3f}")
        print(f"  groups where ours loses to a baseline: {len(s['losses'])}")


if __name__ == "__main__":
    print_summary(run())
