"""Calibration ratios with partial pooling and a monthly block bootstrap (T-011).

Converts each VIIRS witness to the Aqua-equivalent scale. For every stratum x witness x daynight x season:

    ratio = (sum of Aqua cell_days) / (sum of witness cell_days)   over the fit months

Fit periods (never the held-out years): S-NPP 2012-01 to 2016-12, NOAA-20 2018-04 to 2021-12.
Only months in which both Aqua and the witness had every day available enter the fit.

Partial pooling (proposals for the Lead's approval): a local stratum is a 2.5 degree block inside a GFED
fire region. The log-ratio of a stratum is shrunk toward its fire region, and that toward the global
ratio, with precision weights: weight on the local estimate = tau^2 / (tau^2 + v), where v is the
bootstrap variance of the local log-ratio, never below its counting-noise floor 1/sum(Aqua) + 1/sum(witness),
and tau^2 the between-stratum variance (DerSimonian-Laird estimate from the data). Cells in the UNASSIGNED fire region pool directly to the global ratio.
`pooling_level` is the level with the largest weight in the final estimate.

Uncertainty: the months of a season are resampled with replacement (whole months), the whole procedure
including tau^2 is repeated per replicate, and `ratio_sd` is the standard deviation of the final ratio.

    python pipeline/calibration.py      # writes data/products/calibration.parquet and regenerates cells.parquet
"""
from __future__ import annotations

import json
import time
import warnings
from dataclasses import dataclass
from pathlib import Path

import duckdb
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
BLOCK_DEG = 2.5
BOOTSTRAP = 200
SEED = 20261114
SEASONS = ["DJF", "MAM", "JJA", "SON"]
SEASON_OF = {12: "DJF", 1: "DJF", 2: "DJF", 3: "MAM", 4: "MAM", 5: "MAM", 6: "JJA", 7: "JJA", 8: "JJA", 9: "SON", 10: "SON", 11: "SON"}
FITS = {"SNPP_VIIRS": ((2012, 1), (2016, 12)), "NOAA20_VIIRS": ((2018, 4), (2021, 12))}
DAYNIGHTS = ["D", "N", "ALL"]
LEVELS = ["LOCAL", "REGION", "GLOBAL"]
UNASSIGNED = "UNASSIGNED"
MIN_FINITE = 20  # bootstrap replicates with a defined local ratio needed to estimate its variance


@dataclass
class Paths:
    products: Path = ROOT / "data" / "products"
    tmp: Path = ROOT / "data" / "interim" / "_duckdb_tmp"


def stratum_id(fire_region: str, lat_c: float, lon_c: float, block: float = BLOCK_DEG) -> str:
    """A 2.5 degree block inside a fire region: {region}_b{row}_{col}, row from the south, column from -180."""
    r, c = int(np.floor((lat_c + 90.0) / block)), int(np.floor((lon_c + 180.0) / block))
    return f"{fire_region}_b{r:03d}_{c:03d}"


def assign_strata(cells: dict[str, list]) -> list[str]:
    return [stratum_id(f, la, lo) for f, la, lo in zip(cells["fire_region"], cells["lat_c"], cells["lon_c"], strict=True)]


def fit_months(witness: str) -> tuple[int, int]:
    (y0, m0), (y1, m1) = FITS[witness]
    return y0 * 100 + m0, y1 * 100 + m1


# ----------------------------------------------------------------------------- the estimator
def dl_tau2(theta: np.ndarray, v: np.ndarray, group: np.ndarray) -> float:
    """DerSimonian-Laird between-unit variance of log-ratios theta (variances v) around their group means."""
    ok = np.isfinite(theta) & np.isfinite(v) & (v > 0)
    if ok.sum() < 3:
        return 0.0
    th, w, g = theta[ok], 1.0 / v[ok], group[ok]
    q, c, n_groups = 0.0, w.sum(), 0
    for key in np.unique(g):
        sel = g == key
        sw = w[sel].sum()
        mu = (w[sel] * th[sel]).sum() / sw
        q += (w[sel] * (th[sel] - mu) ** 2).sum()
        c -= (w[sel] ** 2).sum() / sw
        n_groups += 1
    df = ok.sum() - n_groups
    return float(max(0.0, (q - df) / c)) if c > 0 and df > 0 else 0.0


def shrink_weight(tau2: float, v: np.ndarray, theta: np.ndarray) -> np.ndarray:
    """Weight on the local estimate: tau^2 / (tau^2 + v); zero where the estimate or its variance is undefined."""
    with np.errstate(invalid="ignore", divide="ignore"):
        lam = np.where(np.isfinite(theta) & np.isfinite(v), tau2 / (tau2 + v), 0.0)
    return np.nan_to_num(lam, nan=0.0)


def pool(theta_s, theta_r, theta_g, v_s, v_r, region_of, has_region):
    """One pooling pass. theta_s (S,), theta_r (R,), theta_g scalar; region_of (S,) region index; has_region (S,) bool.

    Returns the final log-ratio per stratum and the weights on (local, region, global).
    """
    tau2_r = dl_tau2(theta_r, v_r, np.zeros(len(theta_r), dtype=int)) if len(theta_r) > 1 else 0.0
    lam_r = shrink_weight(tau2_r, v_r, theta_r)
    rho = np.where(np.isfinite(theta_r), lam_r * np.nan_to_num(theta_r) + (1 - lam_r) * theta_g, theta_g)  # region after shrinkage
    tau2_l = dl_tau2(theta_s, v_s, np.where(has_region, region_of, -1))
    lam = shrink_weight(tau2_l, v_s, theta_s)
    parent = np.where(has_region, rho[np.clip(region_of, 0, None)], theta_g)
    final = lam * np.nan_to_num(theta_s) + (1 - lam) * parent
    w_region = np.where(has_region, (1 - lam) * lam_r[np.clip(region_of, 0, None)], 0.0)
    weights = np.stack([lam, w_region, 1.0 - lam - w_region], axis=1)
    return final, weights, tau2_l, tau2_r


def log_ratio(a: np.ndarray, w: np.ndarray) -> np.ndarray:
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where((a > 0) & (w > 0), np.log(a / w), np.nan)


def boot_var(theta: np.ndarray) -> np.ndarray:
    """Variance of a log-ratio over bootstrap replicates (rows 1..B of theta); inf if too few are defined."""
    rep = theta[1:]
    fin = np.isfinite(rep).sum(axis=0)
    with np.errstate(invalid="ignore"), warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-undefined columns give nan, which becomes inf below
        var = np.nanvar(rep, axis=0, ddof=1)
    return np.where(fin >= MIN_FINITE, var, np.inf)


def poisson_floor(a: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Counting-noise variance of log(sum a / sum w): 1/sum a + 1/sum w (inf where a total is 0).

    The bootstrap understates the variance of sparse strata (with activity in one or two months most
    replicates repeat the same value), so the variance used for pooling is never below this floor.
    """
    with np.errstate(divide="ignore"):
        return np.where((a > 0) & (w > 0), 1.0 / np.where(a > 0, a, 1) + 1.0 / np.where(w > 0, w, 1), np.inf)


def fit_season(a_m: np.ndarray, w_m: np.ndarray, region_of: np.ndarray, has_region: np.ndarray, n_regions: int,
               rng: np.random.Generator, boot: int = BOOTSTRAP) -> dict:
    """Fit one witness x daynight x season. a_m, w_m: (months, strata) cell_days of Aqua and of the witness."""
    n_m, n_s = a_m.shape
    counts = np.ones((boot + 1, n_m))
    for b in range(1, boot + 1):  # row 0 is the full sample; the others resample whole months with replacement
        counts[b] = np.bincount(rng.integers(0, n_m, n_m), minlength=n_m)
    ta, tw = counts @ a_m, counts @ w_m                       # (boot + 1, strata)
    onehot = np.zeros((n_s, n_regions))
    onehot[np.where(has_region)[0], region_of[has_region]] = 1.0
    ra, rw = ta @ onehot, tw @ onehot                         # (boot + 1, regions)
    ga, gw = ta.sum(axis=1), tw.sum(axis=1)
    th_s, th_r, th_g = log_ratio(ta, tw), log_ratio(ra, rw), log_ratio(ga, gw)
    v_s = np.maximum(boot_var(th_s), poisson_floor(ta[0], tw[0]))
    v_r = np.maximum(boot_var(th_r), poisson_floor(ra[0], rw[0]))
    final, weights, tau2_l, tau2_r = pool(th_s[0], th_r[0], th_g[0], v_s, v_r, region_of, has_region)
    finals = np.empty((boot, n_s))
    for b in range(boot):  # the whole procedure per replicate, with tau^2 re-estimated
        finals[b] = pool(th_s[b + 1], th_r[b + 1], th_g[b + 1], v_s, v_r, region_of, has_region)[0]
    with np.errstate(over="ignore", invalid="ignore"):
        sd = np.nanstd(np.exp(finals), axis=0, ddof=1)
    used = ((a_m > 0) & (w_m > 0)).sum(axis=0)
    return {"theta": final, "ratio": np.exp(final), "sd": sd, "weights": weights, "tau2_local": tau2_l, "tau2_region": tau2_r,
            "n_overlap": used, "global_ratio": float(np.exp(th_g[0])) if np.isfinite(th_g[0]) else float("nan"),
            "region_ratio": np.exp(th_r[0]), "local_ratio_observed": np.exp(th_s[0])}


def pooling_level(weights: np.ndarray) -> np.ndarray:
    """The level with the largest weight; ties go to the more local level."""
    return np.argmax(weights, axis=1)


# ----------------------------------------------------------------------------- data access
def load_cells(paths: Paths) -> dict[str, list]:
    t = pq.read_table(paths.products / "cells.parquet")
    return {k: t.column(k).to_pylist() for k in t.column_names}


def monthly_sums(con, paths: Paths, witness: str, strata_by_cell: dict[str, str]) -> tuple[list[tuple[int, int]], dict, list[tuple]]:
    """Cell-days per fit month, stratum and daynight for Aqua and the witness, complete months only.

    Returns (months used, sums[(witness, daynight)] -> {(month_index, stratum): cell_days}, excluded months).
    """
    lo, hi = fit_months(witness)
    cmw = f"read_parquet('{(paths.products / 'cell_month_witness.parquet').as_posix()}')"
    con.execute("DROP TABLE IF EXISTS smap")
    con.execute("CREATE TEMP TABLE smap (cell_id VARCHAR, stratum VARCHAR)")
    con.executemany("INSERT INTO smap VALUES (?, ?)", list(strata_by_cell.items()))
    wm = con.execute(f"""SELECT year, month, count(*) AS n, bool_and(da = dim) AS complete FROM
        (SELECT witness, year, month, any_value(days_available) AS da, any_value(days_in_month) AS dim FROM {cmw}
         WHERE witness IN ('AQUA_MODIS', '{witness}') AND year * 100 + month BETWEEN {lo} AND {hi} GROUP BY ALL)
        GROUP BY year, month ORDER BY year, month""").fetchall()
    months = [(y, m) for y, m, n, ok in wm if n == 2 and ok]
    excluded = [(y, m, "partial" if n == 2 else "one witness only") for y, m, n, ok in wm if not (n == 2 and ok)]
    idx = {ym: i for i, ym in enumerate(months)}
    sums: dict = {}
    rows = con.execute(f"""SELECT s.stratum, c.year, c.month, c.witness, c.daynight, sum(c.cell_days) FROM {cmw} c JOIN smap s USING (cell_id)
        WHERE c.witness IN ('AQUA_MODIS', '{witness}') AND c.year * 100 + c.month BETWEEN {lo} AND {hi} AND c.daynight IN ('D', 'N', 'ALL')
        GROUP BY ALL""").fetchall()
    for stratum, y, m, w, dn, n in rows:
        if (y, m) in idx:
            sums.setdefault((w, dn), {})[(idx[(y, m)], stratum)] = int(n)
    return months, sums, excluded


# ---------------------------------------------------------------------------------- the run
def calibrate(paths: Paths | None = None, boot: int = BOOTSTRAP, seed: int = SEED) -> tuple[dict[str, list], dict]:
    paths = paths or Paths()
    t0 = time.time()
    cells = load_cells(paths)
    strata_of_cell = dict(zip(cells["cell_id"], assign_strata(cells), strict=True))
    region_of_stratum = {s: s.split("_b")[0] for s in strata_of_cell.values()}
    strata = sorted(set(strata_of_cell.values()))
    s_idx = {s: i for i, s in enumerate(strata)}
    regions = sorted({r for r in region_of_stratum.values() if r != UNASSIGNED})
    r_idx = {r: i for i, r in enumerate(regions)}
    has_region = np.array([region_of_stratum[s] != UNASSIGNED for s in strata])
    region_of = np.array([r_idx.get(region_of_stratum[s], 0) for s in strata])
    con = duckdb.connect()
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    con.execute("SET memory_limit='4GB'")
    out: dict[str, list] = {k: [] for k in ["stratum_id", "witness", "daynight", "season", "ratio", "ratio_sd", "n_overlap_months",
                                              "fit_period", "pooling_level"]}
    report: dict = {"strata": len(strata), "regions": regions, "months": {}, "excluded": {}, "global": [], "tau2": [], "levels": {}}
    rng = np.random.default_rng(seed)
    for witness, ((y0, m0), (y1, m1)) in FITS.items():
        months, sums, excluded = monthly_sums(con, paths, witness, strata_of_cell)
        fit_period = f"{y0}-{m0:02d}/{y1}-{m1:02d}"
        report["months"][witness], report["excluded"][witness] = len(months), excluded
        for dn in DAYNIGHTS:
            a = np.zeros((len(months), len(strata)))
            w = np.zeros((len(months), len(strata)))
            for (mi, s), n in sums.get(("AQUA_MODIS", dn), {}).items():
                a[mi, s_idx[s]] = n
            for (mi, s), n in sums.get((witness, dn), {}).items():
                w[mi, s_idx[s]] = n
            for season in SEASONS:
                sel = np.array([SEASON_OF[m] == season for _, m in months])
                if sel.sum() < 2:
                    continue
                res = fit_season(a[sel], w[sel], region_of, has_region, len(regions), rng, boot)
                if not np.isfinite(res["global_ratio"]):  # no overlap data at any level: no ratio can be given
                    report.setdefault("undefined", []).append({"witness": witness, "daynight": dn, "season": season})
                    continue
                lvl = pooling_level(res["weights"])
                for i, s in enumerate(strata):
                    out["stratum_id"].append(s)
                    out["witness"].append(witness)
                    out["daynight"].append(dn)
                    out["season"].append(season)
                    out["ratio"].append(float(res["ratio"][i]))
                    out["ratio_sd"].append(float(res["sd"][i]))
                    out["n_overlap_months"].append(int(res["n_overlap"][i]))
                    out["fit_period"].append(fit_period)
                    out["pooling_level"].append(LEVELS[lvl[i]])
                report["global"].append({"witness": witness, "daynight": dn, "season": season, "ratio": res["global_ratio"],
                                         "months": int(sel.sum())})
                report["tau2"].append({"witness": witness, "daynight": dn, "season": season, "tau2_local": res["tau2_local"],
                                       "tau2_region": res["tau2_region"]})
                key = f"{witness}|{dn}"
                for L, n in zip(*np.unique(lvl, return_counts=True), strict=True):
                    report["levels"].setdefault(key, {}).setdefault(LEVELS[L], 0)
                    report["levels"][key][LEVELS[L]] += int(n)
        print(f"{witness} done ({time.time() - t0:.0f}s)", flush=True)
    report["rows"] = len(out["ratio"])
    report["seconds"] = round(time.time() - t0)
    return out, report


SCHEMA = pa.schema([("stratum_id", pa.string()), ("witness", pa.string()), ("daynight", pa.string()), ("season", pa.string()),
                    ("ratio", pa.float64()), ("ratio_sd", pa.float64()), ("n_overlap_months", pa.int32()), ("fit_period", pa.string()),
                    ("pooling_level", pa.string())])


def write(paths: Paths, table: dict[str, list]) -> Path:
    path = paths.products / "calibration.parquet"
    pq.write_table(pa.table(table, schema=SCHEMA), path, compression="zstd")
    return path


def regenerate_cells(paths: Paths) -> int:
    """Rewrite cells.parquet with the final stratum_id (a 2.5 degree block inside a fire region)."""
    t = pq.read_table(paths.products / "cells.parquet")
    cells = {k: t.column(k).to_pylist() for k in t.column_names}
    cells["stratum_id"] = assign_strata(cells)
    pq.write_table(pa.table(cells, schema=t.schema), paths.products / "cells.parquet", compression="zstd")
    return len(set(cells["stratum_id"]))


def validate(paths: Paths | None = None) -> list[str]:
    """Contract checks on calibration.parquet, and completeness against cells.parquet."""
    import contract_check as cc
    paths = paths or Paths()
    errors: list[str] = []
    df = cc.check_table("calibration", paths.products / "calibration.parquet", errors)
    if df is None:
        return errors
    for col, allowed in (("witness", set(FITS)), ("daynight", set(DAYNIGHTS)), ("season", set(SEASONS)), ("pooling_level", set(LEVELS))):
        bad = set(df[col].unique()) - allowed
        if bad:
            errors.append(f"{col}: values outside the expected set: {sorted(bad)}")
    if not (df.ratio > 0).all() or not np.isfinite(df.ratio).all():
        errors.append("ratio must be positive and finite")
    if not (df.ratio_sd >= 0).all() or df.ratio_sd.isna().any():
        errors.append("ratio_sd must be defined and non-negative")
    if (df.n_overlap_months < 0).any():
        errors.append("n_overlap_months must not be negative")
    cells = load_cells(paths)
    need = set(cells["stratum_id"])
    if set(df.stratum_id) != need:
        errors.append(f"strata differ from cells.parquet ({len(set(df.stratum_id) ^ need)} not in both)")
    expected = len(need) * len(FITS) * len(DAYNIGHTS) * len(SEASONS)
    if len(df) != expected:
        errors.append(f"expected {expected} rows (every stratum x witness x daynight x season), found {len(df)}")
    return errors


def main() -> int:
    paths = Paths()
    table, report = calibrate(paths)
    path = write(paths, table)
    n_strata = regenerate_cells(paths)
    (paths.products.parent / "interim" / "qa" / "calibration_report.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
    print(path, report["rows"], "rows,", n_strata, "strata")
    problems = validate(paths)
    print("\n".join(problems) if problems else "calibration validates against the contract")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
