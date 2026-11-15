"""Baseline, probabilities, verdicts and the real harmonized products (T-014), per docs/DECISION_LOG.md D-028.

Reads cell_month_witness, cells and calibration (T-011), combines the witnesses with the method of harmonize.py (T-013, D-005) for
every cell and every entity, and writes cell_month_harmonized.parquet, entity_month.parquet and metadata.json (contract 0.1.1).

For each area and month:
  * baseline: the same calendar month over 2003 to 2022, empirical p25, p50 and p75 of the harmonized estimates of the years that
    have one (linear interpolation between order statistics); fewer than 15 of the 20 years: no verdict;
  * probabilities: the estimate is Normal(estimate, sd) truncated at 0; p_above = P(X > p75), p_below = P(X < p25);
  * verdict, in the order of D-028 section 3, and the caveat codes of section 4.

    python pipeline/verdicts.py        # real products into data/products/
"""
from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harmonize as hz

ROOT = Path(__file__).resolve().parents[1]
METHOD_VERSION = "0.1.0"
CONTRACT_VERSION = "0.1.1"
BASELINE_YEARS = (2003, 2022)
MIN_BASELINE_YEARS = 15          # of the 20 baseline years (D-028 step 2)
MIN_P50 = 5.0                    # Aqua-equivalent cell-days (D-028 step 4)
ZERO_P75 = 1.0                   # estimate 0 and baseline p75 at most this: NO_DETECTED_ACTIVITY (step 3)
VERDICT_LEVEL = 0.8              # steps 5 to 7
POOLED_SHARE = 0.5               # POOLED_CALIBRATION: more than this share of the converted cell-days uses a REGION or GLOBAL ratio
WITNESSES = hz.WITNESSES         # AQUA_MODIS, SNPP_VIIRS, NOAA20_VIIRS
VERDICTS = ["ABOVE_NORMAL", "BELOW_NORMAL", "WITHIN_NORMAL", "CANNOT_DETERMINE", "NO_DETECTED_ACTIVITY"]
# reason codes in alphabetical order (the order in the output lists)
CODES = ["AQUA_DRIFT_ERA", "DIURNAL_CAVEAT", "INSUFFICIENT_BASELINE", "OUTAGE", "POOLED_CALIBRATION", "PROVISIONAL_NRT",
         "SINGLE_WITNESS", "WIDE_INTERVAL", "WITNESS_DISAGREEMENT"]
LEVEL_CODE = {"SP": 0, "NRT": 1, "MIXED": 2}
LEVEL_NAME = np.array(["SP", "NRT", "MIXED"])
DIURNAL_BOX = (29.5, 32.5, 73.8, 77.5)   # lat_min, lat_max, lon_min, lon_max: Punjab and Haryana (D-028 section 4)
DIURNAL_FROM = 2020


@dataclass
class Paths:
    products: Path = ROOT / "data" / "products"
    tmp: Path = ROOT / "data" / "interim" / "_duckdb_tmp"
    raw: Path = ROOT / "data" / "raw"
    country_map: Path = ROOT / "pipeline" / "country_map.csv"

    def hz(self) -> hz.Paths:
        return hz.Paths(products=self.products, tmp=self.tmp)


# --------------------------------------------------------------------------------------------------- numeric pieces
_erf = np.frompyfunc(math.erf, 1, 1)


def norm_cdf(x: np.ndarray) -> np.ndarray:
    """Standard normal cumulative distribution function, vectorised (math.erf: no SciPy needed)."""
    x = np.asarray(x, dtype=float)
    out = 0.5 * (1.0 + _erf(x / math.sqrt(2.0)).astype(float))
    return np.where(np.isnan(x), np.nan, out)


def truncated_probabilities(est: np.ndarray, sd: np.ndarray, p25: np.ndarray, p75: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """p_above, p_below, p_within of X ~ Normal(est, sd) truncated at 0 (D-028 section 2). Nan where an input is nan.

    P(X > a) = (1 - F((a - est) / sd)) / (1 - F((0 - est) / sd)); P(X < a) = (F((a - est) / sd) - F((0 - est) / sd)) / (1 - F((0 - est) / sd)).
    """
    est, sd, p25, p75 = (np.asarray(x, dtype=float) for x in (est, sd, p25, p75))
    with np.errstate(invalid="ignore", divide="ignore"):
        f0 = norm_cdf(-est / sd)
        keep = 1.0 - f0
        above = (1.0 - norm_cdf((p75 - est) / sd)) / keep
        below = (norm_cdf((p25 - est) / sd) - f0) / keep
    above, below = np.clip(above, 0.0, 1.0), np.clip(below, 0.0, 1.0)
    return above, below, np.clip(1.0 - above - below, 0.0, 1.0)


def baseline_percentiles(est: np.ndarray, years: np.ndarray, months: np.ndarray, n_keys: int,
                         baseline: tuple[int, int] = BASELINE_YEARS) -> dict[str, np.ndarray]:
    """Per key and calendar month: p25, p50, p75 and the number of years with an estimate, over the baseline years.

    est: (keys, time) harmonized estimates (nan: none); years, months: (time,) the year and month of each column.
    Returns arrays of shape (keys, 12), calendar month 1 at index 0. Linear interpolation between order statistics.
    """
    y0, y1 = baseline
    out = {k: np.full((n_keys, 12), np.nan) for k in ("p25", "p50", "p75")}
    out["n_years"] = np.zeros((n_keys, 12), dtype=np.int16)
    for m in range(1, 13):
        cols = np.where((months == m) & (years >= y0) & (years <= y1))[0]
        if len(cols) == 0:
            continue
        sub = est[:, cols]
        n = np.isfinite(sub).sum(axis=1)
        out["n_years"][:, m - 1] = n
        ok = n > 0
        if ok.any():
            q = np.nanpercentile(sub[ok], [25, 50, 75], axis=1)
            for i, k in enumerate(("p25", "p50", "p75")):
                out[k][ok, m - 1] = q[i]
    return out


def verdicts_from(est: np.ndarray, sd: np.ndarray, n_baseline: np.ndarray, p25: np.ndarray, p50: np.ndarray, p75: np.ndarray,
                  raw: np.ndarray | None = None) -> dict:
    """The verdict of each row by the order of D-028 section 3. Returns integer verdict codes (index into VERDICTS), the
    probabilities and the reason flags (outage, insufficient_baseline, wide_interval), all arrays.

    `raw` is the raw combined cell-days of the row (every witness, Terra included). Step 3 (NO_DETECTED_ACTIVITY) also requires raw = 0:
    the contract does not allow that verdict where any witness detected something (a refinement of D-028 step 3 for the Lead to confirm);
    such a row goes on to step 4 (baseline p50 below 5: INSUFFICIENT_BASELINE). With raw = None only the estimate is looked at."""
    has_est = np.isfinite(est)
    p_above, p_below, p_within = truncated_probabilities(est, sd, p25, p75)
    has_base = np.isfinite(p50) & (n_baseline >= MIN_BASELINE_YEARS)
    v = np.full(len(est), VERDICTS.index("CANNOT_DETERMINE"), dtype=np.int8)
    outage = ~has_est
    step2 = has_est & ~has_base
    step3 = has_est & has_base & (est == 0) & (p75 <= ZERO_P75) & (True if raw is None else raw == 0)
    step4 = has_est & has_base & ~step3 & (p50 < MIN_P50)
    judge = has_est & has_base & ~step3 & ~step4
    with np.errstate(invalid="ignore"):
        above, below, within = judge & (p_above >= VERDICT_LEVEL), judge & (p_below >= VERDICT_LEVEL), judge & (p_within >= VERDICT_LEVEL)
    v[step3] = VERDICTS.index("NO_DETECTED_ACTIVITY")
    v[above] = VERDICTS.index("ABOVE_NORMAL")
    v[below & ~above] = VERDICTS.index("BELOW_NORMAL")
    v[within & ~above & ~below] = VERDICTS.index("WITHIN_NORMAL")
    wide = judge & ~above & ~below & ~within
    with np.errstate(invalid="ignore", divide="ignore"):
        pct = np.where(has_est & np.isfinite(p50) & (p50 > 0), est / p50 * 100.0, np.nan)
    keep = has_est & has_base
    return {"verdict": v, "p_above": np.where(keep, p_above, np.nan), "p_below": np.where(keep, p_below, np.nan),
            "p_within": np.where(keep, p_within, np.nan), "pct_of_normal": np.where(keep, pct, np.nan),
            "outage": outage, "insufficient_baseline": step2 | step4, "wide_interval": wide}


# ----------------------------------------------------------------------------------------- the combination, vectorised
def excluded_by_month(years: np.ndarray, months: np.ndarray, aqua_from: dict) -> np.ndarray:
    """(time, 2) booleans: Aqua is not combined for day (index 0) and night (index 1) in this month (D-005)."""
    out = np.zeros((len(years), 2), dtype=bool)
    for j, dn in enumerate(("D", "N")):
        start = aqua_from.get(dn)
        if start is not None:
            out[:, j] = years * 100 + months >= start[0] * 100 + start[1]
    return out


def combine_wide(e, vc, vr, rbar, complete, has_row, level, e_pooled, excluded, phi=None, kappa=None) -> dict:
    """The T-013 combination for many areas at once. Arrays are (N, 3 witnesses, 2 day/night) (level and e_pooled too);
    `excluded` is (N, 2): Aqua is not combined for that part. Returns estimate, sd, counts, flags (see harmonize._combine_witnesses)."""
    phi = phi or hz.PHI
    kappa = hz.KAPPA if kappa is None else kappa
    n = e.shape[0]
    total, plain_var, chi2, dof = np.zeros(n), np.zeros(n), np.zeros(n), np.zeros(n, dtype=int)
    used = np.zeros((n, 3), dtype=bool)
    used_part = np.zeros((n, 3, 2), dtype=bool)
    hit = np.zeros(n, dtype=bool)
    incomplete = np.zeros(n, dtype=bool)
    for j, dn in enumerate(("D", "N")):
        est = np.where(has_row[:, :, j], e[:, :, j], np.nan)
        var = np.maximum(phi[dn] * vc[:, :, j] + kappa[dn] * e[:, :, j] ** 2 + vr[:, :, j], rbar[:, :, j] ** 2)
        var = np.where(has_row[:, :, j], var, np.nan)
        use = complete[:, :, j] & has_row[:, :, j]
        aqua_complete = use[:, 0].copy()
        use[:, 0] &= ~excluded[:, j]
        hit |= aqua_complete & excluded[:, j]
        use = use & np.isfinite(est) & np.isfinite(var) & (var > 0)
        c = hz.combine(est, var, use)
        n_dn = c["n"]
        some = n_dn > 0
        incomplete |= has_row[:, :, j].any(axis=1) & ~some          # a part with data but no witness that counts: no total
        scale_dn = np.where(n_dn >= 2, c["scale"], 1.0)
        with np.errstate(invalid="ignore", divide="ignore"):
            total += np.where(some, c["estimate"], 0.0)
            plain_var += np.where(some, (c["sd"] / scale_dn) ** 2, 0.0)
        chi2 += np.where(some, c["chi2"], 0.0)
        dof += np.where(some, n_dn - 1, 0)
        used |= use
        used_part[:, :, j] = use
    n_w = used.sum(axis=1)
    ok = (n_w > 0) & ~incomplete
    with np.errstate(invalid="ignore", divide="ignore"):
        s = np.where(dof > 0, np.sqrt(chi2 / np.maximum(dof, 1)), np.nan)
    scale = np.where(dof > 0, np.maximum(s, 1.0), np.where(n_w >= 2, 1.0, np.nan))
    sd = np.sqrt(plain_var) * np.where(dof > 0, scale, 1.0)
    est = np.where(ok, total, np.nan)
    sd = np.where(ok, sd, np.nan)
    used = np.where(ok[:, None], used, False)
    used_part = np.where(ok[:, None, None], used_part, False)
    # data level of the rows that were used (all rows when none was)
    lv_rows = np.where(used_part.any(axis=(1, 2))[:, None, None], used_part, has_row)
    lv_min = np.where(lv_rows, level, 9).reshape(n, -1).min(axis=1)
    lv_max = np.where(lv_rows, level, -1).reshape(n, -1).max(axis=1)
    data_level = np.where(lv_max < 0, 0, np.where(lv_min == lv_max, lv_min, 2)).clip(0, 2).astype(np.int8)       # no row at all: SP
    e_used = np.where(used_part, e, 0.0).reshape(n, -1).sum(axis=1)
    e_pool = np.where(used_part, e_pooled, 0.0).reshape(n, -1).sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        pooled = np.where(e_used > 0, e_pool / e_used, 0.0) > POOLED_SHARE
    return {"estimate": est, "sd": np.where(np.isfinite(est), np.maximum(sd, 0.0), np.nan), "n_witnesses": np.where(ok, n_w, 0), "used": used,
            "scale": np.where(ok, scale, np.nan), "disagree": ok & (dof > 0) & (s > hz.DISAGREEMENT_CODE), "aqua_hit": hit,
            "data_level": data_level, "pooled": ok & pooled}


# -------------------------------------------------------------------------------------------------- caveat codes
def diurnal_mask(year: np.ndarray, month: np.ndarray, is_india: np.ndarray, in_box: np.ndarray) -> np.ndarray:
    """DIURNAL_CAVEAT (D-028 section 4): India and the cells of Punjab and Haryana, October and November, from 2020."""
    return (is_india | in_box) & (year >= DIURNAL_FROM) & ((month == 10) | (month == 11))


def reason_flags(c: dict, v: dict, diurnal: np.ndarray) -> np.ndarray:
    """(N, len(CODES)) booleans of the reason codes: the verdict reasons and the caveats."""
    n = len(c["estimate"])
    f = np.zeros((n, len(CODES)), dtype=bool)
    idx = {k: i for i, k in enumerate(CODES)}
    f[:, idx["AQUA_DRIFT_ERA"]] = c["aqua_hit"]
    f[:, idx["DIURNAL_CAVEAT"]] = diurnal
    f[:, idx["INSUFFICIENT_BASELINE"]] = v["insufficient_baseline"]
    f[:, idx["OUTAGE"]] = v["outage"]
    f[:, idx["POOLED_CALIBRATION"]] = c["pooled"]
    f[:, idx["PROVISIONAL_NRT"]] = c["data_level"] >= 1
    f[:, idx["SINGLE_WITNESS"]] = c["n_witnesses"] == 1
    f[:, idx["WIDE_INTERVAL"]] = v["wide_interval"]
    f[:, idx["WITNESS_DISAGREEMENT"]] = c["disagree"]
    return f


def list_column(flags: np.ndarray, names: list[str]) -> pa.Array:
    """A list<string> Arrow column from a boolean matrix (row i lists the names where flags[i] is true)."""
    counts = flags.sum(axis=1)
    offsets = np.concatenate([[0], np.cumsum(counts)]).astype(np.int32)
    flat = np.nonzero(flags)[1]                      # np.nonzero is row-major: the names of row 0 first, in column order
    values = pa.array(names, type=pa.string()).take(pa.array(flat, type=pa.int64()))
    return pa.ListArray.from_arrays(pa.array(offsets, type=pa.int32()), values)


def float_column(x: np.ndarray) -> pa.Array:
    return pa.array(x, type=pa.float64(), mask=~np.isfinite(x))


# ------------------------------------------------------------------------------------------------- long table to arrays
W_INDEX = {"AQUA_MODIS": 0, "SNPP_VIIRS": 1, "NOAA20_VIIRS": 2}
DN_INDEX = {"D": 0, "N": 1}


def empty_wide(k: int, t: int) -> dict:
    shape = (k, t, 3, 2)
    return {"e": np.zeros(shape), "vc": np.zeros(shape), "vr": np.zeros(shape), "rbar": np.zeros(shape), "complete": np.zeros(shape, bool),
            "has_row": np.zeros(shape, bool), "level": np.zeros(shape, np.int8), "e_pooled": np.zeros(shape), "raw": np.zeros((k, t)),
            "raw_w": np.zeros((k, t, 4)), "has_w": np.zeros((k, t, 4), bool)}


def fill_wide(w: dict, key: np.ndarray, t: np.ndarray, witness: np.ndarray, dn: np.ndarray, raw: np.ndarray, e, vc, vr, rbar, complete,
              level, e_pooled) -> None:
    """Put rows of a long table into the arrays. witness: index into W_INDEX, or -1 for Terra (raw only); dn: 0 or 1."""
    k_n, t_n = w["raw"].shape
    w["raw"] += np.bincount(key * t_n + t, weights=raw, minlength=k_n * t_n).reshape(k_n, t_n)
    rw = np.where(witness == -1, 1, witness + (witness >= 1))           # RAW order: AQUA, TERRA, SNPP, NOAA20 -> 0, 1, 2, 3
    rw = np.where(witness == 0, 0, rw)
    for j in range(4):
        sel = rw == j
        if sel.any():
            w["raw_w"][:, :, j] += np.bincount(key[sel] * t_n + t[sel], weights=raw[sel], minlength=k_n * t_n).reshape(k_n, t_n)
            w["has_w"][key[sel], t[sel], j] = True
    m = witness >= 0
    ix = (key[m], t[m], witness[m], dn[m])
    for name, arr in (("e", e), ("vc", vc), ("vr", vr), ("rbar", rbar), ("complete", complete), ("level", level), ("e_pooled", e_pooled)):
        w[name][ix] = np.asarray(arr)[m]
    w["has_row"][ix] = True


def harmonize_wide(w: dict, years: np.ndarray, months: np.ndarray, aqua_from: dict | None = None, phi=None, kappa=None) -> dict:
    """The T-013 combination for every (key, month) of the arrays; results have shape (keys, time) (used: keys, time, 3)."""
    k_n, t_n = w["raw"].shape
    n = k_n * t_n
    ex = np.tile(excluded_by_month(years, months, hz.AQUA_FROM if aqua_from is None else aqua_from), (k_n, 1))
    flat = {name: w[name].reshape(n, 3, 2) for name in ("e", "vc", "vr", "rbar", "complete", "has_row", "level", "e_pooled")}
    c = combine_wide(flat["e"], flat["vc"], flat["vr"], flat["rbar"], flat["complete"], flat["has_row"], flat["level"], flat["e_pooled"], ex, phi, kappa)
    out = {k: (v.reshape(k_n, t_n, 3) if v.ndim == 2 else v.reshape(k_n, t_n)) for k, v in c.items()}
    out["present"] = w["has_row"].any(axis=(2, 3)) | w["has_w"].any(axis=2)
    out["raw"] = w["raw"]
    return out


def with_verdicts(res: dict, years: np.ndarray, months: np.ndarray, diurnal: np.ndarray | None = None) -> dict:
    """Add the baseline, probabilities, verdicts and reason flags to the combination results (arrays (keys, time))."""
    k_n, t_n = res["estimate"].shape
    base = baseline_percentiles(res["estimate"], years, months, k_n)
    idx = months - 1
    p25, p50, p75, nb = (base[k][:, idx] for k in ("p25", "p50", "p75", "n_years"))
    flat = lambda a: a.reshape(-1)
    v = verdicts_from(flat(res["estimate"]), flat(res["sd"]), flat(nb), flat(p25), flat(p50), flat(p75), flat(res["raw"]))
    keep = flat(np.isfinite(res["estimate"]) & (nb >= MIN_BASELINE_YEARS))
    base_cols = {"baseline_p25": np.where(keep, flat(p25), np.nan), "baseline_median": np.where(keep, flat(p50), np.nan),
                 "baseline_p75": np.where(keep, flat(p75), np.nan)}
    dm = np.zeros(k_n * t_n, bool) if diurnal is None else flat(diurnal)
    flags = reason_flags({k: flat(res[k]) for k in ("estimate", "aqua_hit", "pooled", "data_level", "n_witnesses", "disagree")}, v, dm)
    out = {"verdict": v["verdict"], "flags": flags, **{k: v[k] for k in ("p_above", "p_below", "p_within", "pct_of_normal")}, **base_cols}
    out["n_baseline_years"] = flat(nb)
    return out


# ----------------------------------------------------------------------------------------------------- Arrow output
def table_from(res: dict, ver: dict, t_slice: slice, years: np.ndarray, months: np.ndarray, key_cols: dict, extra: dict | None = None) -> pa.Table:
    """An Arrow table (contract section 3 or 4 columns) for the months in `t_slice` of the results; rows where nothing is present are left out."""
    k_n, t_n = res["estimate"].shape
    cols = np.arange(t_n)[t_slice]
    sel = res["present"][:, t_slice]
    flat_sel = sel.reshape(-1)
    pick = lambda a: a.reshape(k_n, t_n, *a.shape[2:])[:, t_slice].reshape(-1, *a.shape[2:])[flat_sel]
    est, sd = res["estimate"][:, t_slice].reshape(-1)[flat_sel], res["sd"][:, t_slice].reshape(-1)[flat_sel]
    ci_lo = np.where(np.isfinite(est), np.maximum(0.0, est - hz.Z90 * sd), np.nan)
    ci_hi = np.where(np.isfinite(est), est + hz.Z90 * sd, np.nan)
    kk, tt = np.nonzero(sel)
    v = {k: pick(ver[k]) for k in ("verdict", "p_above", "p_below", "p_within", "pct_of_normal", "baseline_p25", "baseline_median", "baseline_p75")}
    ver_flat = ver["flags"].reshape(k_n, t_n, -1)[:, t_slice].reshape(-1, ver["flags"].shape[1])[flat_sel]
    used = res["used"][:, t_slice].reshape(-1, 3)[flat_sel]
    arrays: dict[str, pa.Array] = {}
    for name, values in key_cols.items():
        arrays[name] = pa.array(np.asarray(values)[kk])
    arrays["year"] = pa.array(years[cols][tt].astype(np.int32))
    arrays["month"] = pa.array(months[cols][tt].astype(np.int32))
    scale = res["scale"][:, t_slice].reshape(-1)[flat_sel]
    arrays.update({"estimate": float_column(est), "ci90_low": float_column(ci_lo), "ci90_high": float_column(ci_hi), "sd": float_column(sd),
                   "raw_combined_cell_days": pa.array(np.rint(res["raw"][:, t_slice].reshape(-1)[flat_sel]).astype(np.int64)),
                   "witnesses_used": list_column(used, WITNESSES), "n_witnesses": pa.array(res["n_witnesses"][:, t_slice].reshape(-1)[flat_sel].astype(np.int64)),
                   "disagreement_scale": float_column(scale), "baseline_median": float_column(v["baseline_median"]),
                   "baseline_p25": float_column(v["baseline_p25"]), "baseline_p75": float_column(v["baseline_p75"]),
                   "pct_of_normal": float_column(v["pct_of_normal"]), "p_above": float_column(v["p_above"]), "p_below": float_column(v["p_below"]),
                   "p_within": float_column(v["p_within"]), "verdict": pa.array(np.array(VERDICTS)[v["verdict"]]),
                   "reason_codes": list_column(ver_flat, CODES), "data_level": pa.array(LEVEL_NAME[res["data_level"][:, t_slice].reshape(-1)[flat_sel]]),
                   "method_version": pa.array(np.full(len(est), METHOD_VERSION))})
    for name, values in (extra or {}).items():
        arrays[name] = values(kk, tt) if callable(values) else pa.array(np.asarray(values)[kk])
    return pa.table(arrays)


# ------------------------------------------------------------------------------------------------------ the real run
def _months_axis(con, cmw: str) -> tuple[np.ndarray, np.ndarray]:
    ym = con.execute(f"SELECT DISTINCT year, month FROM {cmw} ORDER BY 1, 2").fetchall()
    return np.array([y for y, _ in ym]), np.array([m for _, m in ym])


def _level_code(lo: pd.Series, hi: pd.Series) -> np.ndarray:
    lo_c, hi_c = lo.map(LEVEL_CODE).to_numpy(), hi.map(LEVEL_CODE).to_numpy()
    return np.where(lo_c == hi_c, lo_c, 2).astype(np.int8)


def _wide_from_agg(agg: pd.DataFrame, key_of: dict, t_of: dict, k_n: int, t_n: int) -> dict:
    """Arrays from the long table of harmonize.aggregate() (entity level)."""
    if (agg[agg.witness.isin(WITNESSES)]["missing"] > 0).any():
        raise ValueError("some stratum rows have no calibration ratio")
    w = empty_wide(k_n, t_n)
    key = np.array([key_of[(a, b)] for a, b in zip(agg.entity_type, agg.entity_id, strict=True)])
    t = np.array([t_of[(y, m)] for y, m in zip(agg.year, agg.month, strict=True)])
    witness = agg.witness.map({**W_INDEX, "TERRA_MODIS": -1}).to_numpy()
    dn = agg.daynight.map(DN_INDEX).to_numpy()
    fill_wide(w, key, t, witness, dn, agg.raw.to_numpy(float), agg.e.to_numpy(float), agg.vc.to_numpy(float), agg.vr.to_numpy(float),
              agg.rbar.to_numpy(float), agg.complete.to_numpy(bool), _level_code(agg.lo, agg.hi), agg.e_pooled.to_numpy(float))
    return w


def _raw_by_witness(w: dict):
    """A function (rows k, t) -> Arrow string column of the JSON map {witness: cell_days} of the witnesses with rows."""
    names = hz.RAW_WITNESSES

    def make(kk: np.ndarray, tt: np.ndarray) -> pa.Array:
        out = []
        for k, t in zip(kk, tt, strict=True):
            out.append(json.dumps({n: round(w["raw_w"][k, t, j]) for j, n in enumerate(names) if w["has_w"][k, t, j]}))
        return pa.array(out)
    return make


def entity_month(con, paths: Paths, years, months, writer_path: Path) -> dict:
    """entity_month.parquet: countries, continents and the world; returns the arrays for the summary."""
    import raw_only
    cells = f"read_parquet('{(paths.products / 'cells.parquet').as_posix()}')"
    names = f"read_csv('{paths.country_map.as_posix()}', header=true)"
    cont = ", ".join(f"('{k}', '{v}')" for k, v in raw_only.CONTINENT_NAMES.items())
    con.execute(f"CREATE OR REPLACE TEMP TABLE continents AS SELECT * FROM (VALUES {cont}) t(code, name)")
    con.execute(f"""CREATE OR REPLACE TEMP TABLE members AS
        SELECT 'COUNTRY' AS entity_type, c.country_iso3 AS entity_id, any_value(n.firms_name) AS entity_name, c.cell_id
          FROM {cells} c JOIN {names} n ON n.iso3 = c.country_iso3 WHERE c.country_iso3 IS NOT NULL GROUP BY c.country_iso3, c.cell_id
        UNION ALL SELECT 'CONTINENT', c.continent, k.name, c.cell_id FROM {cells} c JOIN continents k ON k.code = c.continent
        UNION ALL SELECT 'GLOBAL', 'GLOBAL', 'World', c.cell_id FROM {cells} c""")
    ents = con.execute("""SELECT entity_type, entity_id, any_value(entity_name), count(*) FROM members GROUP BY 1, 2
                          ORDER BY CASE entity_type WHEN 'COUNTRY' THEN 0 WHEN 'CONTINENT' THEN 1 ELSE 2 END, 2""").fetchall()
    key_of = {(t, i): k for k, (t, i, _, _) in enumerate(ents)}
    t_of = {(int(y), int(m)): i for i, (y, m) in enumerate(zip(years, months, strict=True))}
    agg = hz.aggregate(con, paths.hz(), "members", None)
    w = _wide_from_agg(agg, key_of, t_of, len(ents), len(years))
    res = harmonize_wide(w, years, months)
    is_india = np.array([t == "COUNTRY" and i == "IND" for t, i, _, _ in ents])
    ver = with_verdicts(res, years, months, diurnal_mask(years[None, :], months[None, :], is_india[:, None], False))
    n_cells = np.array([n for *_, n in ents])
    table = table_from(res, ver, slice(None), years, months,
                       {"entity_type": [e[0] for e in ents], "entity_id": [e[1] for e in ents], "entity_name": [e[2] for e in ents]},
                       {"n_cells": n_cells, "raw_by_witness": _raw_by_witness(w)})
    pq.write_table(table, writer_path, compression="zstd")
    return {"ents": ents, "res": res, "ver": ver, "table": table}


def cell_month(con, paths: Paths, years, months, writer_path: Path, log=print) -> dict:
    """cell_month_harmonized.parquet, one row group per year; returns the arrays for the summary."""
    cmw = f"read_parquet('{(paths.products / 'cell_month_witness.parquet').as_posix()}')"
    cells = f"read_parquet('{(paths.products / 'cells.parquet').as_posix()}')"
    cal = f"read_parquet('{(paths.products / 'calibration.parquet').as_posix()}')"
    cdf = con.execute(f"SELECT cell_id, lat_c, lon_c, country_iso3 FROM {cells} ORDER BY cell_id").df()
    k_n = len(cdf)
    con.execute(f"CREATE OR REPLACE TEMP TABLE cidx AS SELECT cell_id, row_number() OVER (ORDER BY cell_id) - 1 AS k FROM {cells}")
    keys = ("estimate", "sd", "n_witnesses", "scale", "disagree", "aqua_hit", "data_level", "pooled", "present", "raw")
    parts: dict[str, list] = {k: [] for k in (*keys, "used")}
    t0 = time.time()
    for y in sorted(set(years.tolist())):
        sel = np.where(years == y)[0]
        season = hz.SEASON_SQL.replace("w.month", "w.month")
        df = con.execute(f"""SELECT i.k, w.month, w.witness, w.daynight, w.cell_days AS cd, (w.days_available = w.days_in_month) AS complete,
                    w.data_level AS lvl, CASE WHEN w.witness = 'AQUA_MODIS' THEN 1.0 ELSE k.ratio END AS r,
                    CASE WHEN w.witness = 'AQUA_MODIS' THEN 0.0 ELSE k.ratio_sd END AS rsd,
                    CASE WHEN w.witness NOT IN ('AQUA_MODIS', 'TERRA_MODIS') AND k.pooling_level <> 'LOCAL' THEN 1.0 ELSE 0.0 END AS pooled
                FROM {cmw} w JOIN cidx i USING (cell_id) JOIN {cells} c USING (cell_id)
                LEFT JOIN {cal} k ON k.stratum_id = c.stratum_id AND k.witness = w.witness AND k.daynight = w.daynight AND k.season = {season}
                WHERE w.year = {y} AND w.daynight IN ('D', 'N')""").df()
        viirs = df.witness.isin(WITNESSES)
        if df.loc[viirs, "r"].isna().any():
            raise ValueError(f"{y}: cell rows without a calibration ratio")
        w = empty_wide(k_n, len(sel))
        cd, r = df.cd.to_numpy(float), df.r.to_numpy(float)
        e = np.nan_to_num(r * cd)
        t_local = df.month.to_numpy() - months[sel[0]]
        lvl = df.lvl.map(LEVEL_CODE).to_numpy().astype(np.int8)
        fill_wide(w, df.k.to_numpy(), t_local, df.witness.map({**W_INDEX, "TERRA_MODIS": -1}).to_numpy(), df.daynight.map(DN_INDEX).to_numpy(),
                  cd, e, np.nan_to_num(r * r * cd), np.nan_to_num((cd * df.rsd.to_numpy(float)) ** 2), np.nan_to_num(r),
                  df.complete.to_numpy(bool), lvl, df.pooled.to_numpy(float) * e)
        res = harmonize_wide(w, years[sel], months[sel])
        for k in keys:
            parts[k].append(res[k])
        parts["used"].append(res["used"])
        log(f"  cells {y}: {len(df):,} rows, {time.time() - t0:.0f}s")
        del df, w
    res = {k: np.concatenate(v, axis=1) for k, v in parts.items()}
    in_box = ((cdf.lat_c >= DIURNAL_BOX[0]) & (cdf.lat_c <= DIURNAL_BOX[1]) & (cdf.lon_c >= DIURNAL_BOX[2]) & (cdf.lon_c <= DIURNAL_BOX[3])).to_numpy()
    is_india = (cdf.country_iso3 == "IND").to_numpy()
    ver = with_verdicts(res, years, months, diurnal_mask(years[None, :], months[None, :], is_india[:, None], in_box[:, None]))
    log(f"  cells: verdicts done, {time.time() - t0:.0f}s")
    writer = None
    for y in sorted(set(years.tolist())):
        sel = np.where(years == y)[0]
        tab = table_from(res, ver, slice(int(sel[0]), int(sel[-1]) + 1), years, months, {"cell_id": cdf.cell_id.to_numpy()})
        writer = writer or pq.ParquetWriter(writer_path, tab.schema, compression="zstd")
        writer.write_table(tab)
    writer.close()
    return {"cells": cdf, "res": res, "ver": ver}


def check_products(paths: Paths) -> list[str]:
    """Contract checks on the written tables, a row group (a year) at a time for the cell table (16 million rows)."""
    import contract_check as cc
    errors: list[str] = []
    for name in ("cell_month_harmonized", "entity_month"):
        f = pq.ParquetFile(paths.products / f"{name}.parquet")
        spec = cc.SPEC[name]
        for col, (want, _nullable) in spec.items():
            if col not in f.schema_arrow.names:
                errors.append(f"{name}: missing field {col}")
            elif not cc._type_ok(f.schema_arrow.field(col).type, want):
                errors.append(f"{name}.{col}: type {f.schema_arrow.field(col).type} is not {want}")
        for g in range(f.num_row_groups):
            df = f.read_row_group(g).to_pandas()
            for col, (_, nullable) in spec.items():
                if col in df and not nullable and df[col].isna().any():
                    errors.append(f"{name} row group {g}: nulls in {col}")
            cc.check_harmonized_rows(name, df, errors, real=True)
    return errors


def summarise(ent: dict, cel: dict) -> dict:
    """Verdict counts and the shares that can be judged, by level."""
    out: dict = {}

    def shares(verdict: np.ndarray, label: str) -> None:
        n = len(verdict)
        counts = {VERDICTS[i]: int((verdict == i).sum()) for i in range(len(VERDICTS))}
        det = sum(counts[k] for k in ("ABOVE_NORMAL", "BELOW_NORMAL", "WITHIN_NORMAL"))
        out[label] = {"rows": n, "counts": counts, "share_above_below_within": det / n if n else None,
                      "share_not_cannot_determine": 1 - counts["CANNOT_DETERMINE"] / n if n else None}
    ents = ent["ents"]
    et = np.array([e[0] for e in ents])
    present = ent["res"]["present"]
    v = ent["ver"]["verdict"].reshape(len(ents), -1)
    for typ in ("COUNTRY", "CONTINENT", "GLOBAL"):
        shares(v[(et == typ)[:, None] & present], typ)
    shares(cel["ver"]["verdict"][cel["res"]["present"].reshape(-1)], "CELL")
    return out


def write_metadata(con, paths: Paths, years, months, ent: dict) -> dict:
    import datetime as dt

    import raw_only
    cells = f"read_parquet('{(paths.products / 'cells.parquet').as_posix()}')"
    lat0, lat1 = con.execute(f"SELECT lat_min, lat_max FROM {cells} LIMIT 1").fetchone()
    g = next(i for i, e in enumerate(ent["ents"]) if e[0] == "GLOBAL")
    lvl = ent["res"]["data_level"][g]

    def ym(i: int) -> str:
        return f"{int(years[i])}-{int(months[i]):02d}"
    snapshot = raw_only.snapshot_dates(paths.raw)
    previous = paths.products / "metadata.json"
    if not any(snapshot.values()) and previous.exists():           # no raw folder here (a worktree): keep the dates already recorded
        snapshot = json.loads(previous.read_text(encoding="utf-8")).get("data_snapshot", snapshot)
    meta = {"contract_version": CONTRACT_VERSION, "method_version": METHOD_VERSION, "synthetic": False,
            "generated_at": dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "grid": {"analysis_deg": round(float(lat1 - lat0), 6), "fine_deg": 0.05}, "baseline_years": list(BASELINE_YEARS),
            "first_month": ym(0), "latest_month": ym(len(years) - 1), "provisional_months": [ym(i) for i in range(len(years)) if lvl[i] >= 1],
            "witnesses": WITNESSES, "data_snapshot": snapshot, "citation": raw_only.CITATION.split(" These files")[0]}
    (paths.products / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (paths.products / "validation_results.json").write_text(json.dumps(
        {"contract_version": CONTRACT_VERSION, "method_version": METHOD_VERSION, "generated_at": meta["generated_at"], "synthetic": False, "tests": []},
        indent=2), encoding="utf-8")
    return meta


def build(paths: Paths | None = None, log=print) -> dict:
    """Write the real products and return the summary (about 20 minutes)."""
    paths = paths or Paths()
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    con.execute("SET memory_limit='6GB'")
    cmw = f"read_parquet('{(paths.products / 'cell_month_witness.parquet').as_posix()}')"
    years, months = _months_axis(con, cmw)
    t0 = time.time()
    log("entities ...")
    ent = entity_month(con, paths, years, months, paths.products / "entity_month.parquet")
    log(f"  entity_month: {ent['table'].num_rows:,} rows, {time.time() - t0:.0f}s")
    log("cells ...")
    cel = cell_month(con, paths, years, months, paths.products / "cell_month_harmonized.parquet", log)
    log("checking ...")
    errors = check_products(paths)
    meta = write_metadata(con, paths, years, months, ent)
    summary = summarise(ent, cel)
    summary["contract_errors"] = errors[:20]
    summary["contract_error_count"] = len(errors)
    summary["metadata"] = meta
    qa = paths.products.parent / "interim" / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    (qa / "verdicts_summary.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    return summary


def refresh_snapshot(paths: Paths) -> dict:
    """Set the data snapshot dates of metadata.json from the modification times of the saved raw files (needs the raw folder)."""
    import raw_only
    snapshot = raw_only.snapshot_dates(paths.raw)
    if not all(snapshot.values()):
        raise FileNotFoundError(f"no raw files under {paths.raw}")
    f = paths.products / "metadata.json"
    meta = json.loads(f.read_text(encoding="utf-8"))
    meta["data_snapshot"] = snapshot
    f.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return snapshot


if __name__ == "__main__":
    args = sys.argv[1:]
    raw = Path(args[args.index("--raw") + 1]) if "--raw" in args else ROOT / "data" / "raw"
    if args[:1] == ["snapshot"]:
        print(refresh_snapshot(Paths(raw=raw)))
    else:
        out = build(Paths(raw=raw))
        print(json.dumps({k: v for k, v in out.items() if k != "metadata"}, indent=1, default=float))
