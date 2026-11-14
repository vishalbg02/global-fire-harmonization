"""Diagnostic (T-020b): does the Aqua / VIIRS ratio rise with activity (cell-day saturation)?

Uses only the calibration fit periods (S-NPP 2012-01 to 2016-12, NOAA-20 2018-04 to 2021-12, complete months, exactly as
`calibration.monthly_sums`). A unit is a stratum-month, day and night apart. Three binnings by activity (cell-days per analysis
cell and month, fixed edges): the Aqua activity of the month, a symmetric proxy, and the typical activity of the stratum. The ratio per
bin is sum(Aqua) / sum(witness), with a 90% interval from a bootstrap over whole months, and a log-log slope. The decision rule is in
docs/task-prompts/T-020b-extreme-months.md and was fixed before any result was seen.

    python pipeline/saturation.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calibration as cal

ROOT = Path(__file__).resolve().parents[1]
EDGES = np.array([0.0, 0.05, 0.15, 0.5, 1.5, 5.0, 15.0, 50.0, np.inf])   # cell-days per analysis cell and month
MIN_UNITS = 50              # bins with fewer units are shown, not used in the slope
BOOT = 1000
SEED = 20261115
BINNINGS = ("aqua_month", "symmetric_proxy", "typical_stratum")
WITNESSES = ("SNPP_VIIRS", "NOAA20_VIIRS")
DAYNIGHT = ("D", "N")


def bin_index(x: np.ndarray, edges: np.ndarray = EDGES) -> np.ndarray:
    """Index of the bin of each value: bin i holds edges[i] <= x < edges[i + 1] (the last bin is open to the right)."""
    return np.clip(np.searchsorted(edges, x, side="right") - 1, 0, len(edges) - 2)


def month_bin_sums(month: np.ndarray, bins: np.ndarray, a: np.ndarray, w: np.ndarray, n_months: int, n_bins: int) -> tuple[np.ndarray, ...]:
    """Per month and bin: sum of Aqua, sum of the witness and the number of units. Arrays (months, bins)."""
    flat = month * n_bins + bins
    size = n_months * n_bins
    sa = np.bincount(flat, weights=a, minlength=size).reshape(n_months, n_bins)
    sw = np.bincount(flat, weights=w, minlength=size).reshape(n_months, n_bins)
    n = np.bincount(flat, minlength=size).reshape(n_months, n_bins)
    return sa, sw, n


def slope_from(sa: np.ndarray, sw: np.ndarray, n: np.ndarray, centre: np.ndarray, min_units: int = MIN_UNITS) -> float:
    """OLS slope of log(ratio) on log(centre) over the bins with at least `min_units` units and positive sums (nan if fewer than 3)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = sa / sw
    ok = (n >= min_units) & (sa > 0) & (sw > 0) & np.isfinite(centre) & (centre > 0)
    if ok.sum() < 3:
        return float("nan")
    x, y = np.log(centre[ok]), np.log(ratio[ok])
    xc = x - x.mean()
    return float((xc * (y - y.mean())).sum() / (xc**2).sum())


def analyse(month: np.ndarray, activity: np.ndarray, a: np.ndarray, w: np.ndarray, n_months: int, boot: int = BOOT, seed: int = SEED,
            min_units: int = MIN_UNITS) -> dict:
    """The ratio per bin and the slope with 90% month-block bootstrap intervals for one binning of one witness and day/night."""
    n_bins = len(EDGES) - 1
    bins = bin_index(activity)
    sa, sw, n = month_bin_sums(month, bins, a, w, n_months, n_bins)
    centre = np.array([activity[bins == b].mean() if (bins == b).any() else np.nan for b in range(n_bins)])
    tot_a, tot_w, tot_n = sa.sum(0), sw.sum(0), n.sum(0)
    rng = np.random.default_rng(seed)
    counts = np.zeros((boot, n_months))
    for b in range(boot):
        counts[b] = np.bincount(rng.integers(0, n_months, n_months), minlength=n_months)
    ba, bw, bn = counts @ sa, counts @ sw, counts @ n                 # (boot, bins): whole months resampled
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = tot_a / tot_w
        ratio_boot = ba / bw
    slopes = np.array([slope_from(ba[i], bw[i], bn[i], centre, min_units) for i in range(boot)])
    slope = slope_from(tot_a, tot_w, tot_n, centre, min_units)
    ok = np.isfinite(slopes)
    lo, hi = (float(np.percentile(slopes[ok], 5)), float(np.percentile(slopes[ok], 95))) if ok.sum() > 20 else (float("nan"), float("nan"))
    rows = []
    for b in range(n_bins):
        r = ratio_boot[:, b]
        r = r[np.isfinite(r)]
        rows.append({"from": float(EDGES[b]), "to": None if np.isinf(EDGES[b + 1]) else float(EDGES[b + 1]), "units": int(tot_n[b]),
                     "activity": None if np.isnan(centre[b]) else float(centre[b]),
                     "ratio": None if not np.isfinite(ratio[b]) else float(ratio[b]),
                     "ci90": None if len(r) < 20 else [float(np.percentile(r, 5)), float(np.percentile(r, 95))],
                     "used_in_slope": bool(tot_n[b] >= min_units and np.isfinite(ratio[b]))})
    return {"bins": rows, "slope": slope, "slope_ci90": [lo, hi], "positive_and_excludes_zero": bool(np.isfinite(lo) and lo > 0)}


def decide(results: dict) -> dict:
    """The rule of the task prompt: confirmed if, in at least two of the three binnings, the slope is positive with a 90% interval that
    excludes 0 in at least three of the four combinations (witness x day/night). Binning (a) alone never decides."""
    per_binning = {}
    for binning in BINNINGS:
        hits = [k for k, v in results.items() if k.startswith(binning + "|") and v["positive_and_excludes_zero"]]
        per_binning[binning] = {"combinations_positive": len(hits), "passes": len(hits) >= 3}
    passing = [b for b, v in per_binning.items() if v["passes"]]
    return {"per_binning": per_binning, "binnings_passing": passing, "confirmed": len(passing) >= 2}


# ---------------------------------------------------------------------------------------------------- the real data
def load_units(paths: cal.Paths | None = None) -> dict:
    """Per witness and day/night: month index, stratum, Aqua and witness cell-days, cells of the stratum (fit periods, complete months)."""
    paths = paths or cal.Paths()
    cells = cal.load_cells(paths)
    strata_of_cell = dict(zip(cells["cell_id"], cal.assign_strata(cells), strict=True))
    n_cells: dict[str, int] = {}
    for s in strata_of_cell.values():
        n_cells[s] = n_cells.get(s, 0) + 1
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    out: dict = {}
    for witness in WITNESSES:
        months, sums, _ = cal.monthly_sums(con, paths, witness, strata_of_cell)
        for dn in DAYNIGHT:
            a_map, w_map = sums.get(("AQUA_MODIS", dn), {}), sums.get((witness, dn), {})
            keys = sorted(set(a_map) | set(w_map))
            mi = np.array([k[0] for k in keys])
            st = [k[1] for k in keys]
            a = np.array([a_map.get(k, 0) for k in keys], dtype=float)
            w = np.array([w_map.get(k, 0) for k in keys], dtype=float)
            cells_n = np.array([n_cells[s] for s in st], dtype=float)
            out[(witness, dn)] = {"month": mi, "stratum": np.array(st), "a": a, "w": w, "cells": cells_n, "months": months}
    return out


def activity_variables(u: dict) -> dict[str, np.ndarray]:
    """The three activity variables (cell-days per analysis cell and month) of the units of one witness and day/night."""
    a_pc, w_pc = u["a"] / u["cells"], u["w"] / u["cells"]
    g = u["a"].sum() / max(u["w"].sum(), 1.0)                                   # the stratum-wide ratio of this witness and day/night
    proxy = 0.5 * (a_pc + g * w_pc)
    typical = np.zeros(len(a_pc))
    for s in np.unique(u["stratum"]):
        sel = u["stratum"] == s
        typical[sel] = np.median(a_pc[sel])
    return {"aqua_month": a_pc, "symmetric_proxy": proxy, "typical_stratum": typical}


def run(paths: cal.Paths | None = None, boot: int = BOOT) -> dict:
    units = load_units(paths)
    results: dict = {}
    for (witness, dn), u in units.items():
        n_months = len(u["months"])
        for binning, activity in zip(BINNINGS, activity_variables(u).values(), strict=True):
            results[f"{binning}|{witness}|{dn}"] = analyse(u["month"], activity, u["a"], u["w"], n_months, boot)
    out = {"decision": decide(results), "results": results, "bin_edges": [float(e) if np.isfinite(e) else None for e in EDGES],
           "fit_periods": {w: list(cal.FITS[w]) for w in WITNESSES}, "min_units": MIN_UNITS, "bootstrap": boot, "seed": SEED,
           "units": {f"{w}|{d}": len(u["a"]) for (w, d), u in units.items()}}
    qa = (paths or cal.Paths()).products.parent / "interim" / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    (qa / "saturation_report.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    res = run()
    print(json.dumps(res["decision"], indent=1))
    for key, v in res["results"].items():
        print(key, "slope", round(v["slope"], 3), "ci90", [round(x, 3) for x in v["slope_ci90"]], "positive:", v["positive_and_excludes_zero"])
