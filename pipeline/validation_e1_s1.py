"""Validation tests E1 (leave one fire region out) and S1 (sensitivity of the verdicts to the baseline), T-025.

E1, generalization. For each GFED fire region R in cells.fire_region (UNASSIGNED is not a region) the S-NPP calibration is fitted again
WITHOUT R: the cells of R are removed from cells.parquet and from the cell-month table handed to `calibration.calibrate`, so no stratum
of R enters any fit (strata, season sums, region level, global level, tau^2, bootstrap). R is then converted the way an unseen region is:
its strata take the global ratio of the fit without R (a phantom stratum without data is added to the fit input; the pooling gives it
exactly the global ratio and the global ratio_sd). The fit uses S-NPP 2012-01 to 2016-12 only, nothing from 2017 on. The converted S-NPP
series of R in 2017-01 to 2021-12 is compared with its Aqua series in the units of the T-012 holdout (`holdout.units_from_agg`:
fire-region-months, complete months of both witnesses, at least 20 Aqua cell-days, day and night separately, plus the day+night total).

Predictions: ours (the leave-one-out conversion), raw (the naive raw merge), glob (one global ratio per day/night and season fitted on the whole
globe, R included, as in T-012) and gloo (the same global ratio fitted without R). Pre-registered here before any result:

  * a region WINS when the median absolute log error of ours is below that of raw, in day and in night, for each of the two that has at
    least MIN_UNITS units (a part with fewer units is not evaluated; a region with no evaluable part is "not evaluable");
  * E1 PASSES when at least REQUIRED_WINS of the regions win (11 of 14, locked at G1, D-028); it FAILS when even counting every not-evaluable
    region as a win the count is below REQUIRED_WINS; otherwise it is INCONCLUSIVE. All regions are reported with their numbers.

S1, sensitivity. The plan re-runs A1 and B1 without the confidence filter and with the Aqua-measured baseline (2003-2021). Here only the
baseline half can run on what exists now: the verdicts of D-028 are applied to the harmonized estimate series of fire regions, Canada and the
six case boxes C1-C6 (docs/VALIDATION_PLAN.md 2a) with (a) the harmonized baseline 2003-2022 and (b) the Aqua-measured baseline 2003-2021,
the estimate being judged held fixed. `compare_baselines` takes entity_month-shaped frames, so it also runs on the T-014 products. The part
without the confidence filter needs the raw archive regridded without the T-005 filter, and the A1 and B1 tests it re-runs do not exist
yet: it is reported as NOT_RUN.

    python pipeline/validation_e1_s1.py all          # writes data/interim/qa/T-025_*.json (git-ignored)
    python pipeline/validation_e1_s1.py e1 --boot 200
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import time
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))

import calibration as cal
import harmonize as hz
import holdout as ho

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "interim" / "_e1_tmp"
WORK_S1 = ROOT / "data" / "interim" / "_s1_tmp"
QA = ROOT / "data" / "interim" / "qa"
WITNESS = "SNPP_VIIRS"
FIT_WINDOW = cal.FITS[WITNESS]                 # ((2012, 1), (2016, 12))
MIN_CELL_DAYS = ho.MIN_CELL_DAYS               # 20 Aqua cell-days per unit, as in T-012
MIN_UNITS = 12                                 # units needed in day (or night) for that part to count in a region's outcome
REQUIRED_WINS = 11                             # of 14 regions (VALIDATION_PLAN.md, locked at G1)
METHODS = ("ours", "raw", "glob", "gloo")
PHANTOM_CELL = "PHANTOM_UNSEEN_REGION"

# S1: constants of the verdict rules (D-028) and of the baselines
BASE_HARMONIZED = (2003, 2022)
BASE_AQUA = (2003, 2021)
MIN_BASE_YEARS = 15
MIN_P50 = 5.0
NO_ACTIVITY_P75 = 1.0
PROB = 0.8
S1_WINDOW = ((2012, 1), (2021, 12))            # months whose verdicts are compared (the VIIRS era inside the Aqua baseline years)
# case boxes (W, S, E, N), peak window (first, last) -- docs/VALIDATION_PLAN.md 2a (approved by the Lead 2026-11-14)
CASES = {"C1": ((95.0, -6.0, 119.0, 4.0), (2015, 9), (2015, 10)), "C2": ((-70.0, -12.0, -45.0, 0.0), (2019, 8), (2019, 9)),
         "C3": ((-59.0, -22.0, -54.0, -15.0), (2020, 8), (2020, 10)), "C4": ((145.0, -39.0, 154.0, -28.0), (2019, 12), (2020, 1)),
         "C5": ((-124.5, 32.5, -114.0, 42.0), (2020, 8), (2020, 9)), "C6": ((105.0, 58.0, 150.0, 72.0), (2021, 7), (2021, 8))}
CASE_CANADA = ("CAN", (2023, 6), (2023, 7))   # C7: entity CAN, peak window 2023-06 to 2023-07 (outside S1_WINDOW: informational)


# ============================================================================================================ E1: building blocks
def regions_of(cells: pd.DataFrame) -> list[str]:
    """The fire regions of the analysis cells (UNASSIGNED is not a region)."""
    return sorted(r for r in cells.fire_region.dropna().unique() if r != cal.UNASSIGNED)


def strata_of(cells: pd.DataFrame) -> list[str]:
    """The distinct stratum ids (2.5 degree blocks) of a table of cells."""
    return sorted(set(cal.assign_strata({"fire_region": list(cells.fire_region), "lat_c": list(cells.lat_c), "lon_c": list(cells.lon_c)})))


def phantom_location(kept_cells: pd.DataFrame) -> tuple[float, float, str]:
    """Centre of a free 2.5 degree block near the pole for the data-less phantom stratum (UNASSIGNED, so it pools to the global ratio)."""
    used = set(strata_of(kept_cells))
    for k in range(144):
        lat, lon = 89.75, -179.75 + 2.5 * k
        sid = cal.stratum_id(cal.UNASSIGNED, lat, lon)
        if sid not in used:
            return lat, lon, sid
    raise RuntimeError("no free block for the phantom stratum")


def prepare_fit_products(src: Path, region: str, dst: Path, fit_end: tuple[int, int] = FIT_WINDOW[1]) -> dict:
    """Write the products handed to the calibration for the fit without `region`: cells.parquet minus the region's cells plus one data-less
    phantom cell (UNASSIGNED), and a cell_month_witness.parquet restricted to Aqua and S-NPP, to cells that are not the region's, and to
    years up to the end of the fit period. Returns what was removed and the phantom stratum."""
    dst.mkdir(parents=True, exist_ok=True)
    tbl = pq.read_table(src / "cells.parquet")
    cells = tbl.to_pandas()
    if region not in set(cells.fire_region):
        raise ValueError(f"unknown fire region {region!r}")
    kept = cells[cells.fire_region != region].copy()
    lat, lon, sid = phantom_location(kept)
    row = kept.iloc[0].copy()
    row["cell_id"], row["lat_c"], row["lon_c"], row["fire_region"], row["stratum_id"] = PHANTOM_CELL, lat, lon, cal.UNASSIGNED, sid
    for col in ("lat_min", "lat_max"):
        row[col] = lat - 0.25 if col == "lat_min" else lat + 0.25
    row["lon_min"], row["lon_max"] = lon - 0.25, lon + 0.25
    for col in ("country_iso3", "continent"):
        if col in row.index:
            row[col] = None
    kept = pd.concat([kept, row.to_frame().T.astype(kept.dtypes.to_dict(), errors="ignore")], ignore_index=True)
    pq.write_table(pa.Table.from_pandas(kept, schema=tbl.schema, preserve_index=False), dst / "cells.parquet", compression="zstd")
    con = duckdb.connect()
    src_cmw = (src / "cell_month_witness.parquet").as_posix()
    con.execute(f"""COPY (SELECT * FROM read_parquet('{src_cmw}') WHERE witness IN ('AQUA_MODIS', '{WITNESS}')
                    AND year <= {fit_end[0]} AND cell_id IN (SELECT cell_id FROM read_parquet('{(dst / 'cells.parquet').as_posix()}')))
                    TO '{(dst / 'cell_month_witness.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)""")
    return {"region": region, "cells_removed": int((cells.fire_region == region).sum()), "phantom_stratum": sid, "phantom_cell": PHANTOM_CELL}


def audit_fit_products(dst: Path, region: str, fit_end: tuple[int, int] = FIT_WINDOW[1]) -> dict:
    """Check the files that are handed to the calibration: no cell of the region, no year after the fit period, no witness but Aqua and S-NPP."""
    con = duckdb.connect()
    cells = f"read_parquet('{(dst / 'cells.parquet').as_posix()}')"
    cmw = f"read_parquet('{(dst / 'cell_month_witness.parquet').as_posix()}')"
    n_region_cells = con.execute(f"SELECT count(*) FROM {cells} WHERE fire_region = ?", [region]).fetchone()[0]
    ymax, witnesses, n_rows = con.execute(f"SELECT max(year), list(DISTINCT witness), count(*) FROM {cmw}").fetchone()
    orphan = con.execute(f"SELECT count(*) FROM {cmw} WHERE cell_id NOT IN (SELECT cell_id FROM {cells})").fetchone()[0]
    out = {"region_cells_in_cells": int(n_region_cells), "cmw_rows_of_cells_not_in_fit_cells": int(orphan), "max_year": int(ymax), "witnesses": sorted(witnesses), "rows": int(n_rows)}
    if n_region_cells or orphan or ymax > fit_end[0] or set(witnesses) - {"AQUA_MODIS", WITNESS}:
        raise AssertionError(f"fit input of the leave-one-out for {region} is not clean: {out}")
    return out


def fit_without_region(src: Path, region: str, work: Path, boot: int = cal.BOOTSTRAP, seed: int = cal.SEED) -> tuple[pd.DataFrame, dict, dict]:
    """Re-fit the S-NPP calibration without `region`. Returns (calibration rows, calibration report, audit)."""
    fit_dir = work / f"fit_{region}"
    info = prepare_fit_products(src, region, fit_dir)
    audit = audit_fit_products(fit_dir, region)
    audit.update(info)
    saved = cal.FITS
    cal.FITS = {WITNESS: saved[WITNESS]}                       # only S-NPP: NOAA-20's fit period (2018-2021) lies in the holdout window
    try:
        table, report = cal.calibrate(cal.Paths(products=fit_dir, tmp=fit_dir / "duck"), boot=boot, seed=seed)
    finally:
        cal.FITS = saved
    df = pd.DataFrame(table)
    if df.stratum_id.str.startswith(f"{region}_b").any():
        raise AssertionError(f"a stratum of {region} entered the fit")
    shutil.rmtree(fit_dir, ignore_errors=True)
    return df, report, audit


def unseen_ratios(loo: pd.DataFrame, phantom_stratum: str, region_strata: list[str]) -> pd.DataFrame:
    """Calibration rows for the strata of a region the fit did not see: each takes the ratio and ratio_sd of the phantom stratum, which the
    pooling gives the global estimate of the fit (day, night and all; each season)."""
    ph = loo[loo.stratum_id == phantom_stratum]
    if ph.empty:
        raise ValueError("no phantom rows in the leave-one-out calibration")
    rows = []
    for s in region_strata:
        r = ph.copy()
        r["stratum_id"], r["pooling_level"], r["n_overlap_months"] = s, "GLOBAL", 0
        rows.append(r)
    return pd.concat(rows, ignore_index=True)[[f.name for f in cal.SCHEMA]]


def write_calibration(df: pd.DataFrame, path: Path) -> None:
    pq.write_table(pa.Table.from_pandas(df, schema=cal.SCHEMA, preserve_index=False), path, compression="zstd")


def prepare_predict_products(src: Path, dst: Path) -> Path:
    """Products for the prediction: the real cells and cell-month table (linked, not copied) and a calibration written per region."""
    dst.mkdir(parents=True, exist_ok=True)
    t = pq.read_table(src / "cells.parquet")
    c = t.to_pandas()
    c["stratum_id"] = cal.assign_strata({"fire_region": list(c.fire_region), "lat_c": list(c.lat_c), "lon_c": list(c.lon_c)})   # the calibration's own rule
    pq.write_table(pa.Table.from_pandas(c, schema=t.schema, preserve_index=False), dst / "cells.parquet", compression="zstd")
    link = dst / "cell_month_witness.parquet"
    if not link.exists():
        try:
            os.link(src / "cell_month_witness.parquet", link)
        except OSError:
            shutil.copyfile(src / "cell_month_witness.parquet", link)
    return dst


def aggregate_region(paths: hz.Paths, cells: pd.DataFrame, region: str, months: list[tuple[int, int]]) -> pd.DataFrame:
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    ids = sorted(cells.loc[cells.fire_region == region, "cell_id"])
    con.register("members_df", pd.DataFrame({"entity_type": "REGION", "entity_id": region, "entity_name": region, "cell_id": ids}))
    con.execute("CREATE TEMP TABLE members AS SELECT * FROM members_df")
    agg = hz.aggregate(con, paths, "members", months)
    return agg[agg.witness.isin(["AQUA_MODIS", WITNESS])].reset_index(drop=True)


def region_sums(src: Path) -> pd.DataFrame:
    """Raw cell-days of Aqua and S-NPP per fire region, month, day/night in S-NPP's fit period, with the completeness of the month: the input
    of the global ratios (T-012 `fit_global_ratios`), kept per region so that a region can be left out."""
    (y0, m0), (y1, m1) = FIT_WINDOW
    con = duckdb.connect()
    cmw = f"read_parquet('{(src / 'cell_month_witness.parquet').as_posix()}')"
    cells = f"read_parquet('{(src / 'cells.parquet').as_posix()}')"
    return con.execute(f"""SELECT coalesce(c.fire_region, 'NONE') AS fire_region, w.year, w.month, w.daynight, w.witness,
                                  sum(w.cell_days) AS raw, bool_and(w.days_available = w.days_in_month) AS complete
        FROM {cmw} w JOIN {cells} c USING (cell_id)
        WHERE w.witness IN ('AQUA_MODIS', '{WITNESS}') AND w.daynight IN ('D', 'N') AND w.year * 100 + w.month BETWEEN {y0 * 100 + m0} AND {y1 * 100 + m1}
        GROUP BY ALL""").df()


def global_frame(by_region: pd.DataFrame, exclude: str | None = None) -> pd.DataFrame:
    """The input of holdout.fit_global_ratios: sums over the globe (without `exclude`); a month is complete if it is complete everywhere."""
    d = by_region if exclude is None else by_region[by_region.fire_region != exclude]
    g = d.groupby(["year", "month", "daynight", "witness"], as_index=False).agg(raw=("raw", "sum"), complete=("complete", "all"))
    return g


# ============================================================================================================ E1: evaluation
def _totals(u: pd.DataFrame) -> pd.DataFrame:
    keys = ["entity_type", "entity_id", "year", "month"]
    cols = ["actual", "pred_ours", "pred_raw", "pred_glob", "pred_gloo", "var_ours", "var_phionly", "var_pois"]
    g = u.groupby(keys)
    t = g[cols].sum()
    t = t[g.daynight.nunique() == 2].reset_index()
    t["daynight"] = "T"
    return t


def evaluate_region(agg: pd.DataFrame, ratios_incl: dict, ratios_loo: dict, min_cell_days: float = MIN_CELL_DAYS) -> dict:
    """Numbers of one region: metrics of the four predictions by day, night and total, and the 90% coverage of ours (T-013 variance)."""
    u = ho.add_predictions(ho.units_from_agg(agg, min_cell_days), ratios_incl)
    r = np.array([ratios_loo.get((d, s), np.nan) for d, s in zip(u.daynight, u.season, strict=True)])
    u["pred_gloo"] = u.raw * r
    u = u[np.isfinite(u.pred_gloo)].reset_index(drop=True)
    t = _totals(u)
    out: dict = {"units": {"D": int((u.daynight == "D").sum()), "N": int((u.daynight == "N").sum()), "T": len(t)}}
    for dn, x in (("D", u[u.daynight == "D"]), ("N", u[u.daynight == "N"]), ("T", t)):
        out[dn] = {m: ho.metrics(x, m) for m in METHODS}
    out["coverage_90"] = {"D": ho.coverage_of(u[u.daynight == "D"], "var_ours"), "N": ho.coverage_of(u[u.daynight == "N"], "var_ours"),
                          "T": ho.coverage_of(t, "var_ours")}
    return out


def region_outcome(res: dict, min_units: int = MIN_UNITS) -> dict:
    """The win rule: ours beats raw on the median absolute log error in every part (day, night) that has at least `min_units` units."""
    parts = {}
    for dn in ("D", "N"):
        m = res[dn]
        if m["ours"].get("units", 0) < min_units or m["raw"].get("units", 0) < min_units:
            parts[dn] = None
        else:
            parts[dn] = bool(m["ours"]["median_abs_log_error"] < m["raw"]["median_abs_log_error"])
    ev = [v for v in parts.values() if v is not None]
    return {"parts": parts, "evaluable": bool(ev), "win": bool(ev) and all(ev)}


def e1_status(outcomes: dict[str, dict], required: int = REQUIRED_WINS) -> dict:
    """PASS: at least `required` wins; FAIL: even all not-evaluable regions as wins would leave fewer; otherwise INCONCLUSIVE."""
    wins = sum(1 for o in outcomes.values() if o["win"])
    not_eval = sum(1 for o in outcomes.values() if not o["evaluable"])
    losses = len(outcomes) - wins - not_eval
    if wins >= required:
        status = "PASS"
    elif wins + not_eval < required:
        status = "FAIL"
    else:
        status = "INCONCLUSIVE"
    return {"status": status, "wins": wins, "losses": losses, "not_evaluable": not_eval, "regions": len(outcomes), "required": required}


def run_e1(src: Path | None = None, work: Path | None = None, boot: int = cal.BOOTSTRAP, seed: int = cal.SEED,
           regions: list[str] | None = None, required: int = REQUIRED_WINS, keep_work: bool = False) -> dict:
    """The whole of E1 on the products in `src` (default data/products)."""
    src = src or ROOT / "data" / "products"
    work = work or WORK
    t0 = time.time()
    cells = pq.read_table(src / "cells.parquet").to_pandas()
    regions = regions or regions_of(cells)
    by_region = region_sums(src)
    ratios_incl = ho.fit_global_ratios(global_frame(by_region))
    predict_dir = prepare_predict_products(src, work / "predict")
    paths = hz.Paths(products=predict_dir, tmp=work / "duck")
    months = [(y, m) for y in range(ho.START[0], ho.END[0] + 1) for m in range(1, 13)]
    out: dict = {"fit_window": [list(FIT_WINDOW[0]), list(FIT_WINDOW[1])], "holdout": "2017-01..2021-12", "min_cell_days": MIN_CELL_DAYS,
                 "min_units": MIN_UNITS, "required_wins": required, "boot": boot, "seed": seed, "global_ratios_incl": {f"{d}|{s}": v for (d, s), v in sorted(ratios_incl.items())},
                 "regions": {}}
    outcomes = {}
    for region in regions:
        loo, _report, audit = fit_without_region(src, region, work, boot, seed)
        strata = strata_of(cells[cells.fire_region == region])
        write_calibration(unseen_ratios(loo, audit["phantom_stratum"], strata), predict_dir / "calibration.parquet")
        agg = aggregate_region(paths, cells, region, months)
        if int(agg.loc[agg.witness == WITNESS, "missing"].sum()):
            raise AssertionError(f"{region}: S-NPP strata without a ratio")
        ratios_loo = ho.fit_global_ratios(global_frame(by_region, exclude=region))
        res = evaluate_region(agg, ratios_incl, ratios_loo)
        res["audit"] = audit
        res["global_ratio_fit_without_region"] = {f"{d}|{s}": v for (d, s), v in sorted(ratios_loo.items())}
        ph = loo[(loo.stratum_id == audit["phantom_stratum"]) & loo.daynight.isin(["D", "N"])].set_index(["daynight", "season"]).ratio.to_dict()
        res["max_rel_diff_ours_ratio_vs_gloo"] = float(max(abs(ph[k] / v - 1.0) for k, v in ratios_loo.items() if k in ph))
        res["outcome"] = region_outcome(res)
        outcomes[region] = res["outcome"]
        out["regions"][region] = res
        o = res["outcome"]
        print(f"  {region}: units D {res['units']['D']} N {res['units']['N']}  win={o['win']} parts={o['parts']}  ({time.time() - t0:.0f}s)", flush=True)
    out["summary"] = e1_status(outcomes, required)
    if not keep_work:
        shutil.rmtree(work, ignore_errors=True)
    return out


# ============================================================================================================ S1
def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def probabilities(estimate: float, sd: float, p25: float, p75: float) -> tuple[float, float, float]:
    """p_above, p_below, p_within for Normal(estimate, sd) truncated at 0 (D-028 section 2): p_above = P(X > p75), p_below = P(X < p25)."""
    if not sd > 0:
        above, below = float(estimate > p75), float(estimate < p25)
        return above, below, 1.0 - above - below
    z0 = _phi((0.0 - estimate) / sd)
    mass = 1.0 - z0
    if mass <= 1e-300:                      # an estimate far below 0 cannot occur (estimates are >= 0); stay defined anyway
        return 0.0, 1.0, 0.0
    above = min(max((1.0 - _phi((p75 - estimate) / sd)) / mass, 0.0), 1.0)
    below = min(max((_phi((p25 - estimate) / sd) - z0) / mass, 0.0), 1.0)
    return above, below, 1.0 - above - below


def verdict_for(estimate: float | None, sd: float | None, n_years: int, p25: float, p50: float, p75: float,
                raw: float | None = None) -> tuple[str, str]:
    """The verdict rules of D-028 in their fixed order. Returns (verdict, reason code or '').

    `raw` (raw combined cell-days of the month, every witness): when given, step 3 also requires raw == 0, the refinement used by the T-014
    product (verdicts.py); with None only the estimate is looked at (D-028 as written)."""
    if estimate is None or sd is None or not np.isfinite(estimate) or not np.isfinite(sd):
        return "CANNOT_DETERMINE", "OUTAGE"
    if n_years < MIN_BASE_YEARS or not np.isfinite(p50):
        return "CANNOT_DETERMINE", "INSUFFICIENT_BASELINE"
    if estimate == 0 and p75 <= NO_ACTIVITY_P75 and (raw is None or raw == 0):
        return "NO_DETECTED_ACTIVITY", ""
    if p50 < MIN_P50:
        return "CANNOT_DETERMINE", "INSUFFICIENT_BASELINE"
    above, below, within = probabilities(estimate, sd, p25, p75)
    if above >= PROB:
        return "ABOVE_NORMAL", ""
    if below >= PROB:
        return "BELOW_NORMAL", ""
    if within >= PROB:
        return "WITHIN_NORMAL", ""
    return "CANNOT_DETERMINE", "WIDE_INTERVAL"


def baselines(series: pd.DataFrame, years: tuple[int, int]) -> pd.DataFrame:
    """Percentiles p25, p50, p75 (linear interpolation between order statistics) of the estimate of the same calendar month over `years`
    (inclusive), per entity, over the years that have an estimate; n_years counts them. `series`: entity_type, entity_id, year, month, estimate."""
    s = series[(series.year >= years[0]) & (series.year <= years[1]) & series.estimate.notna()]
    rows = []
    for (et, eid, month), g in s.groupby(["entity_type", "entity_id", "month"]):
        x = g.estimate.to_numpy(float)
        rows.append({"entity_type": et, "entity_id": eid, "month": int(month), "n_years": len(x), "p25": float(np.percentile(x, 25)),
                     "p50": float(np.percentile(x, 50)), "p75": float(np.percentile(x, 75))})
    return pd.DataFrame(rows, columns=["entity_type", "entity_id", "month", "n_years", "p25", "p50", "p75"])


def compare_baselines(harmonized: pd.DataFrame, aqua_only: pd.DataFrame, window=S1_WINDOW, years_h=BASE_HARMONIZED, years_a=BASE_AQUA) -> pd.DataFrame:
    """Verdicts of the same estimate under two baselines: the harmonized one (`harmonized` series, years_h) and the Aqua-measured one
    (`aqua_only` series, years_a). Both frames are entity_month-shaped: entity_type, entity_id, year, month, estimate, sd. The estimate judged is
    the harmonized one, in the months of `window`; only the baseline changes. One row per entity-month with both verdicts."""
    bh, ba = baselines(harmonized, years_h), baselines(aqua_only, years_a)
    ym = harmonized.year * 100 + harmonized.month
    cur = harmonized[(ym >= window[0][0] * 100 + window[0][1]) & (ym <= window[1][0] * 100 + window[1][1])]
    cur = cur[["entity_type", "entity_id", "year", "month", "estimate", "sd"]]
    key = ["entity_type", "entity_id", "month"]
    m = cur.merge(bh, on=key, how="left").merge(ba, on=key, how="left", suffixes=("_h", "_a"))
    vh, va, rh, ra = [], [], [], []
    for r in m.itertuples():
        est = None if pd.isna(r.estimate) else float(r.estimate)
        sd = None if pd.isna(r.sd) else float(r.sd)
        a = verdict_for(est, sd, 0 if pd.isna(r.n_years_h) else int(r.n_years_h), r.p25_h, r.p50_h, r.p75_h)
        b = verdict_for(est, sd, 0 if pd.isna(r.n_years_a) else int(r.n_years_a), r.p25_a, r.p50_a, r.p75_a)
        vh.append(a[0]), rh.append(a[1]), va.append(b[0]), ra.append(b[1])
    m["verdict_h"], m["reason_h"], m["verdict_a"], m["reason_a"] = vh, rh, va, ra
    m["agree"] = m.verdict_h == m.verdict_a
    return m


def crosscheck_with_t014(entity_month: pd.DataFrame, use_raw: bool = True) -> dict:
    """Compare this module's verdict rules with the `verdict` column of the T-014 `entity_month` product.

    The baseline is recomputed here from the product's own `estimate` column (same calendar month, 2003-2022, `baselines`), the verdict with
    `verdict_for` from estimate, sd, the recomputed baseline and, if `use_raw`, `raw_combined_cell_days` (the refinement of step 3 in the
    product). Rows are compared on the verdict and the three baseline percentiles of the product. Returns counts and every mismatch."""
    em = entity_month
    bh = baselines(em, BASE_HARMONIZED)
    m = em.merge(bh, on=["entity_type", "entity_id", "month"], how="left")
    verd, reason = [], []
    for r in m.itertuples():
        est = None if pd.isna(r.estimate) else float(r.estimate)
        sd = None if pd.isna(r.sd) else float(r.sd)
        raw = float(r.raw_combined_cell_days) if use_raw and "raw_combined_cell_days" in m.columns else None
        vv, rc = verdict_for(est, sd, 0 if pd.isna(r.n_years) else int(r.n_years), r.p25, r.p50, r.p75, raw)
        verd.append(vv), reason.append(rc)
    m["my_verdict"], m["my_reason"] = verd, reason
    bad = m[m.my_verdict != m.verdict]
    out = {"compared": len(m), "mismatches": len(bad), "use_raw": use_raw,
           "by_entity_type": {k: int(n) for k, n in m.groupby("entity_type").size().items()},
           "mismatch_by_pair": {f"{a} (mine) vs {b} (product)": int(n) for (a, b), n in bad.groupby(["my_verdict", "verdict"]).size().items()},
           "mismatch_rows": [{"entity_type": r.entity_type, "entity_id": r.entity_id, "year": int(r.year), "month": int(r.month),
                              "mine": r.my_verdict, "product": r.verdict, "estimate": None if pd.isna(r.estimate) else float(r.estimate),
                              "raw": int(r.raw_combined_cell_days)} for r in bad.head(50).itertuples()]}
    if "baseline_median" in m.columns:
        have = m[m.baseline_median.notna() & m.p50.notna()]
        both_nan = int((m.baseline_median.isna() != m.p50.isna()).sum())
        out["baseline_columns"] = {"rows_with_baseline": len(have), "presence_differs": both_nan,
                                   "max_abs_rel_diff_p50": float(((have.p50 - have.baseline_median).abs() / have.baseline_median.where(have.baseline_median > 0)).max()),
                                   "max_abs_diff_p25_p75": float(max((have.p25 - have.baseline_p25).abs().max(), (have.p75 - have.baseline_p75).abs().max()))}
    return out


PRODUCT_CASES = {"C1": ("IDN", (2015, 9), (2015, 10)), "C2": ("BRA", (2019, 8), (2019, 9)), "C3": ("BRA", (2020, 8), (2020, 10)),
                 "C4": ("AUS", (2019, 12), (2020, 1)), "C5": ("USA", (2020, 8), (2020, 9)), "C6": ("RUS", (2021, 7), (2021, 8))}
PRODUCT_ENTITIES = [("COUNTRY", c) for c in ("IDN", "BRA", "AUS", "USA", "RUS", "CAN")] + [("GLOBAL", "GLOBAL")]


def run_s1_product(src: Path | None = None, work: Path | None = None) -> dict:
    """Supplementary S1-BASELINE on the T-014 product: the harmonized series and baseline of the product (`entity_month`) against an
    Aqua-measured baseline (2003-2021) built from the Aqua rows of the same aggregation, for the product entities IDN, BRA, AUS, USA, RUS, CAN
    and GLOBAL. The product has no fire regions or case boxes: the peak windows of C1 to C6 are taken on the country that contains the box
    (a coarser area than the box, so this is a supplement, not a replacement)."""
    src = src or ROOT / "data" / "products"
    work = work or WORK_S1
    em = pq.read_table(src / "entity_month.parquet").to_pandas()
    cells = pq.read_table(src / "cells.parquet").to_pandas()
    parts = [pd.DataFrame({"entity_type": et, "entity_id": eid, "entity_name": eid,
                           "cell_id": sorted(cells.cell_id if et == "GLOBAL" else cells.loc[cells.country_iso3 == eid, "cell_id"])})
             for et, eid in PRODUCT_ENTITIES]
    members = pd.concat(parts, ignore_index=True)
    n_cells = {(et, eid): int(n) for (et, eid), n in members.groupby(["entity_type", "entity_id"]).size().items()}
    paths = hz.Paths(products=src, tmp=work / "duck_p")
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    con.register("members_df", members)
    con.execute("CREATE TEMP TABLE members AS SELECT * FROM members_df")
    agg = hz.aggregate(con, paths, "members", None)
    aqua = records_frame(hz.records_from(agg[agg.witness == "AQUA_MODIS"].reset_index(drop=True), n_cells, aqua_from={"D": None, "N": None}))
    keys = set(PRODUCT_ENTITIES)
    prod = em[[(a, b) in keys for a, b in zip(em.entity_type, em.entity_id, strict=True)]][["entity_type", "entity_id", "year", "month", "estimate", "sd"]]
    cmp = compare_baselines(prod, aqua, window=((2012, 1), (2023, 12)))
    cases = {cid: (eid, first, last) for cid, (eid, first, last) in PRODUCT_CASES.items()}
    rows = case_changes(cmp, cases)
    rows7 = case_changes(cmp, {"C7": ("CAN", (2023, 6), (2023, 7))})
    win = cmp[(cmp.year * 100 + cmp.month) <= 202112]
    shutil.rmtree(work, ignore_errors=True)
    return {"entities": [f"{a}:{b}" for a, b in PRODUCT_ENTITIES], "window_2012_2021": summarise_s1(win), "case_peak_months": rows,
            "c7_canada_informational": rows7, "status_baseline": s1_status(rows)}


def case_changes(cmp: pd.DataFrame, cases: dict) -> list[dict]:
    """For each case, the verdict of every month of its peak window under both baselines."""
    out = []
    for cid, (eid, first, last) in cases.items():
        ym = cmp.year * 100 + cmp.month
        g = cmp[(cmp.entity_id == eid) & (ym >= first[0] * 100 + first[1]) & (ym <= last[0] * 100 + last[1])]
        for r in g.itertuples():
            out.append({"case": cid, "entity": eid, "year": int(r.year), "month": int(r.month), "estimate": None if pd.isna(r.estimate) else float(r.estimate),
                        "verdict_harmonized_baseline": r.verdict_h, "verdict_aqua_baseline": r.verdict_a, "reason_h": r.reason_h, "reason_a": r.reason_a,
                        "p50_h": None if pd.isna(r.p50_h) else float(r.p50_h), "p50_a": None if pd.isna(r.p50_a) else float(r.p50_a),
                        "unchanged": bool(r.agree)})
    return out


def s1_status(case_rows: list[dict]) -> str:
    """Baseline half of S1: PASS when every peak-window month of the cases has the same verdict under both baselines; FAIL otherwise;
    INCONCLUSIVE when there is no peak-window month to compare."""
    if not case_rows:
        return "INCONCLUSIVE"
    return "PASS" if all(r["unchanged"] for r in case_rows) else "FAIL"


def summarise_s1(cmp: pd.DataFrame) -> dict:
    out: dict = {}
    for et, g in cmp.groupby("entity_type"):
        both = g[g.p50_h.notna() & g.p50_a.notna()]
        rel = (both.p50_a / both.p50_h - 1.0).replace([np.inf, -np.inf], np.nan).dropna()
        out[et] = {"entity_months": len(g), "agree": float(g.agree.mean()) if len(g) else None, "changed": int((~g.agree).sum()),
                   "median_rel_diff_p50_aqua_vs_harmonized": float(rel.median()) if len(rel) else None,
                   "p95_abs_rel_diff_p50": float(rel.abs().quantile(0.95)) if len(rel) else None,
                   "transitions": {f"{a} -> {b}": int(n) for (a, b), n in g[~g.agree].groupby(["verdict_h", "verdict_a"]).size().items()}}
    return out


def box_cells(cells: pd.DataFrame, box: tuple[float, float, float, float]) -> list[str]:
    w, s, e, n = box
    sel = cells[(cells.lon_c >= w) & (cells.lon_c <= e) & (cells.lat_c >= s) & (cells.lat_c <= n)]
    return sorted(sel.cell_id)


def s1_members(cells: pd.DataFrame) -> pd.DataFrame:
    parts = [pd.DataFrame({"entity_type": "REGION", "entity_id": r, "entity_name": r, "cell_id": sorted(cells.loc[cells.fire_region == r, "cell_id"])})
             for r in regions_of(cells)]
    parts.append(pd.DataFrame({"entity_type": "COUNTRY", "entity_id": "CAN", "entity_name": "CAN", "cell_id": sorted(cells.loc[cells.country_iso3 == "CAN", "cell_id"])}))
    for cid, (box, _, _) in CASES.items():
        parts.append(pd.DataFrame({"entity_type": "CASE", "entity_id": cid, "entity_name": cid, "cell_id": box_cells(cells, box)}))
    return pd.concat(parts, ignore_index=True)


def records_frame(records: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(records)
    return df[["entity_type", "entity_id", "year", "month", "estimate", "sd"]]


def run_s1(src: Path | None = None, work: Path | None = None) -> dict:
    src = src or ROOT / "data" / "products"
    work = work or WORK_S1
    cells = pq.read_table(src / "cells.parquet").to_pandas()
    members = s1_members(cells)
    n_cells = {(et, eid): int(n) for (et, eid), n in members.groupby(["entity_type", "entity_id"]).size().items()}
    paths = hz.Paths(products=src, tmp=work / "duck_s1")
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    con.register("members_df", members)
    con.execute("CREATE TEMP TABLE members AS SELECT * FROM members_df")
    agg = hz.aggregate(con, paths, "members", None)
    harm = records_frame(hz.records_from(agg, n_cells))
    aqua = records_frame(hz.records_from(agg[agg.witness == "AQUA_MODIS"].reset_index(drop=True), n_cells, aqua_from={"D": None, "N": None}))
    cmp = compare_baselines(harm, aqua)
    cases = {cid: (cid, first, last) for cid, (_, first, last) in CASES.items()}
    rows = case_changes(cmp, cases)
    canada = case_changes(compare_baselines(harm, aqua, window=((2012, 1), (2023, 12))), {"C7": CASE_CANADA})
    out = {"window": [list(S1_WINDOW[0]), list(S1_WINDOW[1])], "baseline_harmonized_years": list(BASE_HARMONIZED), "baseline_aqua_years": list(BASE_AQUA),
           "entities": {"REGION": 14, "COUNTRY": ["CAN"], "CASE": list(CASES)}, "summary": summarise_s1(cmp), "case_peak_months": rows,
           "c7_canada_informational": canada, "status_baseline": s1_status(rows)}
    shutil.rmtree(work, ignore_errors=True)
    return out


# ============================================================================================================ entries
def region_table(e1: dict) -> str:
    """The per-region table in Markdown (median absolute log error, MALE, of ours / raw / glob / gloo; ratio = median predicted / actual)."""
    head = ("| Region | D units | N units | D ours | D raw | D glob | D gloo | N ours | N raw | N glob | N gloo | Result |\n"
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    lines = [head]
    for r, res in e1["regions"].items():
        def f(dn, m, res=res):
            v = res[dn][m].get("median_abs_log_error")
            return "n/a" if v is None else f"{v:.3f}"
        o = res["outcome"]
        tag = "not evaluable" if not o["evaluable"] else ("WIN" if o["win"] else "LOSS")
        lines.append(f"| {r} | {res['units']['D']} | {res['units']['N']} | " + " | ".join(f(dn, m) for dn in ("D", "N") for m in METHODS) + f" | {tag} |")
    return "\n".join(lines)


def build_entries(e1: dict | None, s1: dict | None, t014: dict | None = None) -> list[dict]:
    """Entries in the shape of DATA_CONTRACT.md section 6."""
    entries = []
    if e1 is not None:
        s = e1["summary"]
        entries.append({
            "test_id": "E1", "family": "E", "title": "Generalization (leave one fire region out)",
            "case": f"{s['regions']} GFED fire regions, 2017-2021 Aqua series predicted from S-NPP converted with a calibration fitted without the region",
            "criterion": f"Our method beats the naive raw merge (lower median absolute log error, day and night) in at least {s['required']} of {s['regions']} regions; all regions reported",
            "threshold": f">= {s['required']} of {s['regions']} regions (locked at G1, D-028)",
            "measured": {"wins": s["wins"], "losses": s["losses"], "not_evaluable": s["not_evaluable"],
                         "per_region": {r: {"win": v["outcome"]["win"], "evaluable": v["outcome"]["evaluable"], "parts": v["outcome"]["parts"],
                                            "units": v["units"],
                                            "median_abs_log_error": {dn: {m: v[dn][m].get("median_abs_log_error") for m in METHODS} for dn in ("D", "N", "T")}}
                                        for r, v in e1["regions"].items()}},
            "status": s["status"], "notes": "S-NPP fit 2012-01 to 2016-12 only; a region left out is converted with the global ratio of the fit without it. See docs/validation/T-025-results.md."})
    if s1 is not None:
        rows = s1["case_peak_months"]
        entries.append({
            "test_id": "S1-BASELINE", "family": "S", "title": "Sensitivity: Aqua-measured baseline (2003-2021) instead of the harmonized baseline (2003-2022)",
            "case": "Verdicts (D-028 rules) of fire regions, Canada and case boxes C1-C6, months 2012-01 to 2021-12; peak windows of C1-C6",
            "criterion": "Verdict unchanged in every peak-window month of C1-C6 (any change is reported)",
            "threshold": "no change in any C1-C6 peak-window month",
            "measured": {"peak_months": len(rows), "changed": sum(1 for r in rows if not r["unchanged"]), "summary": s1["summary"]},
            "status": s1["status_baseline"], "notes": "The estimate judged is the harmonized one in both runs; only the baseline changes."})
        entries.append({
            "test_id": "S1-CONFIDENCE-FILTER", "family": "S", "title": "Sensitivity: A1 and B1 without the confidence filter",
            "case": "C1-C6 (A1) and all fire regions (B1)", "criterion": "Conclusions unchanged (report any that change)", "threshold": "pre-registered at G1",
            "measured": None, "status": "NOT_RUN",
            "notes": "Needs the raw archive regridded without the T-005 confidence filter, and the A1 and B1 tests it re-runs; neither exists yet."})
        entries.append({
            "test_id": "S1", "family": "S", "title": "Sensitivity (A1 and B1 without the confidence filter, and with the Aqua-measured baseline)",
            "case": "C1-C6", "criterion": "Conclusions unchanged (report any that change)", "threshold": "pre-registered at G1",
            "measured": {"baseline_half": s1["status_baseline"], "confidence_filter_half": "NOT_RUN"}, "status": "NOT_RUN",
            "notes": "Overall NOT_RUN: half of S1 cannot run yet. The baseline half ran and is reported as S1-BASELINE; its verdict-agreement check against the T-014 verdict column is also NOT_RUN until T-014 products exist."})
    if t014 is not None:
        x = t014["crosscheck"]
        entries.append({
            "test_id": "S1-T014-CROSSCHECK", "family": "S", "title": "Verdict rules of this task against the verdict column of the T-014 entity_month product",
            "case": "every COUNTRY, CONTINENT and GLOBAL entity-month of the product", "criterion": "same verdict in every row (baseline recomputed from the product estimates)",
            "threshold": "0 mismatches", "measured": {"compared": x["compared"], "mismatches": x["mismatches"], "baseline_columns": x.get("baseline_columns"),
                                                      "without_raw_refinement_mismatches": t014["crosscheck_without_raw"]["mismatches"]},
            "status": "PASS" if x["mismatches"] == 0 else "FAIL", "notes": "Supplementary. The product's step 3 also requires raw combined cell-days = 0 (a refinement of D-028 as written)."})
        sp = t014["s1_product"]
        entries.append({
            "test_id": "S1-BASELINE-PRODUCT", "family": "S", "title": "Sensitivity (supplementary): product baseline against Aqua-measured baseline, country level",
            "case": "IDN, BRA, AUS, USA, RUS, CAN, GLOBAL in the T-014 product; peak windows of C1-C6 taken on the containing country",
            "criterion": "Verdict unchanged in every peak-window month", "threshold": "no change in any peak-window month",
            "measured": {"peak_months": len(sp["case_peak_months"]), "changed": sum(1 for r in sp["case_peak_months"] if not r["unchanged"]), "summary": sp["window_2012_2021"]},
            "status": sp["status_baseline"], "notes": "Supplementary to S1-BASELINE (case boxes); countries are coarser than the boxes. Does not replace it."})
    return entries


def write_outputs(e1: dict | None, s1: dict | None, qa: Path | None = None) -> list[Path]:
    """Write the report of each test that ran now; the entries file is built from both reports (a report written by an earlier run is used for
    a test that did not run now)."""
    qa = qa or QA
    qa.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, rep in (("T-025_e1_report.json", e1), ("T-025_s1_report.json", s1)):
        if rep is not None:
            (qa / name).write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
            paths.append(qa / name)
    t014 = _load(qa / "T-025_t014_report.json")
    e1 = e1 if e1 is not None else _load(qa / "T-025_e1_report.json")
    s1 = s1 if s1 is not None else _load(qa / "T-025_s1_report.json")
    paths.append(qa / "T-025_validation_entries.json")
    paths[-1].write_text(json.dumps(build_entries(e1, s1, t014), indent=1, default=str), encoding="utf-8")
    return paths


def _load(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("which", choices=["e1", "s1", "all", "entries", "t014"], nargs="?", default="all")
    ap.add_argument("--boot", type=int, default=cal.BOOTSTRAP)
    args = ap.parse_args(argv)
    e1 = s1 = None
    if args.which in ("e1", "all"):
        print("E1: leave one fire region out")
        e1 = run_e1(boot=args.boot)
        print(e1["summary"])
    if args.which in ("s1", "all"):
        print("S1: baseline sensitivity")
        s1 = run_s1()
        print(s1["status_baseline"], json.dumps(s1["summary"], indent=1))
    if args.which == "t014":
        em = pq.read_table(ROOT / "data" / "products" / "entity_month.parquet").to_pandas()
        rep = {"crosscheck": crosscheck_with_t014(em), "crosscheck_without_raw": crosscheck_with_t014(em, use_raw=False), "s1_product": run_s1_product()}
        rep["crosscheck_without_raw"].pop("mismatch_rows")
        QA.mkdir(parents=True, exist_ok=True)
        (QA / "T-025_t014_report.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
        print(rep["crosscheck"]["mismatches"], rep["s1_product"]["status_baseline"])
    if args.which == "entries":
        print("entries from the reports already written")
    print([str(p) for p in write_outputs(e1, s1)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
