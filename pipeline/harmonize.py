"""Witness combination with disagreement inflation, and `harmonize_area()` (T-013).

For any area (a list of analysis cells) and month, each witness gives an Aqua-equivalent estimate

    E_w = sum over strata s and day/night d of  ratio(s, w, d, season) x cell_days(s, w, d)

(Aqua has ratio 1 and no ratio uncertainty; Terra is raw view only and never enters the estimate). Raw cell-days are summed per
witness and stratum BEFORE they are converted (docs/SCIENTIFIC_METHODOLOGY.md 4.5). The variance of E_w has two parts:

  * counting noise, per stratum and day/night:  phi_d x ratio^2 x cell_days, plus a term that grows with the size of the
    estimate, kappa_d x E_d^2 (E_d: the witness estimate of the area for that day/night). phi_d is an overdispersion factor
    (phi = 1 is Poisson) and kappa_d a relative error. Both are estimated once on the calibration fit periods only
    (`estimate_dispersion`) and applied to every witness;
  * ratio error, shared: strata that take the same ratio share the same error, so their errors are added fully correlated.
    The groups are the ratio sources: each LOCAL stratum, each fire region's pooled estimate (strata with pooling level REGION)
    and the global estimate (GLOBAL), per witness, day/night and season:   (sum over the group of cell_days x ratio_sd)^2.

The witnesses of a month are combined with a precision-weighted mean. If they disagree more than their variances allow, the
combined sd is multiplied by S = sqrt(chi^2 / (N - 1)) (only when S > 1; the Birge ratio, the usual rule for discordant
measurements); the reason code WITNESS_DISAGREEMENT is given when S > 2. Baseline, probabilities and verdicts belong to T-014:
here the baseline fields are null and the verdict is CANNOT_DETERMINE, as the contract requires without a baseline.

    from harmonize import harmonize_area
    records = harmonize_area(cell_ids, months=None)       # list of dicts in the shape of DATA_CONTRACT.md section 4
    python pipeline/harmonize.py phi                       # re-estimate phi and kappa
    python pipeline/harmonize.py                           # the real-data diagnostic

Approved by the Lead 2026-11-14 (PR #43): the size-dependent term kappa x E^2 next to phi x count; day and night converted separately and added; a variance floor of one cell-day for
a zero count; only complete witness-months count; a 90% normal interval with the lower bound at 0; no estimate for the
2002-07 to 2002-09 outage months. Strata that share no ratio source are treated as independent (limitation).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
METHOD_VERSION = "0.1.0-combined-no-baseline"
DISAGREEMENT_CODE = 2.0   # WITNESS_DISAGREEMENT is given when S exceeds it (Lead, 2026-11-14); the sd is inflated whenever S > 1
CHI2_1DF_MEDIAN = 0.45493642311957283   # the median of a chi-square variable with one degree of freedom
WITNESSES = ["AQUA_MODIS", "SNPP_VIIRS", "NOAA20_VIIRS"]      # the witnesses that enter the estimate, in a fixed order
RAW_WITNESSES = ["AQUA_MODIS", "TERRA_MODIS", "SNPP_VIIRS", "NOAA20_VIIRS"]
Z90 = 1.6448536269514722
SEASON_SQL = ("CASE WHEN w.month IN (12, 1, 2) THEN 'DJF' WHEN w.month IN (3, 4, 5) THEN 'MAM' "
              "WHEN w.month IN (6, 7, 8) THEN 'JJA' ELSE 'SON' END")
HARMONIZED_NULLS = ["baseline_median", "baseline_p25", "baseline_p75", "pct_of_normal", "p_above", "p_below", "p_within"]


@dataclass
class Paths:
    products: Path = ROOT / "data" / "products"
    tmp: Path = ROOT / "data" / "interim" / "_duckdb_tmp"


# --------------------------------------------------------------------------------------------- the estimator
def combine(est: np.ndarray, var: np.ndarray, usable: np.ndarray) -> dict[str, np.ndarray]:
    """Combine witnesses. est, var, usable: (groups, witnesses); usable is False where a witness does not count.

    Returns the combined estimate and sd (nan where no witness counts), the number of witnesses, chi^2 and the
    disagreement scale (nan with fewer than 2 witnesses, otherwise max(S, 1)).
    """
    usable = usable & np.isfinite(est) & np.isfinite(var) & (var > 0)
    w = np.where(usable, 1.0 / np.where(var > 0, var, 1.0), 0.0)
    n = usable.sum(axis=1)
    sw = w.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = np.where(n > 0, (w * np.where(usable, est, 0.0)).sum(axis=1) / np.where(sw > 0, sw, 1.0), np.nan)
        chi2 = (w * np.where(usable, est - mean[:, None], 0.0) ** 2).sum(axis=1)
        s = np.where(n >= 2, np.sqrt(chi2 / np.maximum(n - 1, 1)), np.nan)
        scale = np.where(n >= 2, np.maximum(s, 1.0), np.nan)
        sd = np.where(n > 0, np.sqrt(1.0 / np.where(sw > 0, sw, 1.0)) * np.where(n >= 2, scale, 1.0), np.nan)
    return {"estimate": mean, "sd": sd, "n": n, "chi2": chi2, "scale": scale, "s": s, "inflated": (n >= 2) & (s > 1.0), "disagree": (n >= 2) & (s > DISAGREEMENT_CODE)}


def interval(estimate: float, sd: float) -> tuple[float, float]:
    """90% normal interval, with the lower bound at 0."""
    return max(0.0, estimate - Z90 * sd), estimate + Z90 * sd


# ------------------------------------------------------------------------------------------------ overdispersion
# phi per day/night, estimated on the fit periods only by `estimate_phi` (python pipeline/harmonize.py phi); see docs/DATA_SOURCES.md
PHI = {"D": 2.25, "N": 2.47}      # `python pipeline/harmonize.py phi` on the T-011 products, 2026-11-14 (see PHI_ONLY for the first version)
KAPPA = {"D": 0.0084, "N": 0.0164}
KAPPA0 = {"D": 0.0, "N": 0.0}
PHI_ONLY = {"D": 7.72, "N": 6.53}  # phi alone, units of at least 20 cell-days (the first PR #43 version), kept for comparison
# D-005 (approved by the Lead 2026-11-14, a documented deviation from the registered day-only rule): Aqua night is not combined from
# 2024-05 on (night drift detected in both witnesses: S-NPP onset 2024-05, NOAA-20 2024-09; the earlier onset is used); Aqua day stays.
AQUA_FROM = {"D": None, "N": (2024, 5)}
SIZE_BANDS = (5.0, 20.0, 100.0, 500.0)   # lower edges of the size bands of a country-month, in cell-days


def solve_phi(d: np.ndarray, vc: np.ndarray, vr: np.ndarray) -> float:
    """phi such that the median of d^2 / (phi x vc + vr) equals the median of a chi-square variable with 1 degree of freedom.

    d: difference between a converted witness and Aqua; vc: its counting variance at phi = 1 (both witnesses); vr: the ratio
    variance. The median is robust to the few units where the difference is large for other reasons.
    """
    ok = np.isfinite(d) & np.isfinite(vc) & np.isfinite(vr) & (vc > 0)
    d2, vc, vr = d[ok] ** 2, vc[ok], vr[ok]
    if len(d2) < 10:
        return float("nan")
    lo, hi = 1e-3, 1e4
    for _ in range(100):                                    # the median of d2 / (phi vc + vr) falls as phi grows: bisect on a log scale
        mid = np.sqrt(lo * hi)
        if np.median(d2 / (mid * vc + vr)) > CHI2_1DF_MEDIAN:
            lo = mid
        else:
            hi = mid
    return float(np.sqrt(lo * hi))


def fit_units(paths: Paths, min_cell_days: float, fits: dict | None = None, factors: pd.DataFrame | None = None) -> tuple[dict, dict]:
    """Country-month units of the calibration fit periods only: arrays per day/night pooled over the pairs.

    Each pair is Aqua against one VIIRS witness inside that witness's fit period (S-NPP 2012-01 to 2016-12; NOAA-20 2018-04 to
    2021-12: S-NPP is not used after 2016, the held-out years are never read). A unit is a country-month where both converted
    estimates are at least `min_cell_days`. Per unit: d (VIIRS minus Aqua), vc (counting variance of both at phi = 1), vr (ratio
    variance), s2 (the squares of the two estimates, for the kappa term) and size (their mean).
    """
    import calibration as cal
    fits = fits or cal.FITS
    con = duckdb.connect()
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    cells = f"read_parquet('{(paths.products / 'cells.parquet').as_posix()}')"
    con.execute(f"""CREATE TEMP TABLE members AS SELECT 'COUNTRY' AS entity_type, country_iso3 AS entity_id, country_iso3 AS entity_name, cell_id
                    FROM {cells} WHERE country_iso3 IS NOT NULL""")
    agg = aggregate(con, paths, "members", None, factors)
    pooled: dict[str, list] = {"D": [], "N": []}
    pairs: dict = {}
    for w, ((y0, m0), (y1, m1)) in fits.items():
        ym = agg.year * 100 + agg.month
        sub = agg[(ym >= y0 * 100 + m0) & (ym <= y1 * 100 + m1) & agg.complete]
        a = sub[sub.witness == "AQUA_MODIS"].set_index(["entity_id", "year", "month", "daynight"])
        v = sub[sub.witness == w].set_index(["entity_id", "year", "month", "daynight"])
        j = a.join(v, lsuffix="_a", rsuffix="_w", how="inner")
        j = j[(j.e_a >= min_cell_days) & (j.e_w >= min_cell_days)]
        pairs[w] = {}
        for dn in ("D", "N"):
            jd = j[j.index.get_level_values("daynight") == dn]
            arrays = ((jd.e_w - jd.e_a).to_numpy(), (jd.vc_a + jd.vc_w).to_numpy(), jd.vr_w.to_numpy(),
                      (jd.e_a ** 2 + jd.e_w ** 2).to_numpy(), ((jd.e_a + jd.e_w) / 2).to_numpy())
            pairs[w][dn] = arrays
            pooled[dn].append(arrays)
    units = {dn: tuple(np.concatenate(x) for x in zip(*pooled[dn], strict=True)) for dn in pooled}
    return units, pairs


def estimate_phi(paths: Paths | None = None, min_cell_days: float = 20.0, fits: dict | None = None) -> dict:
    """The overdispersion factor alone (kappa = 0) per day/night from country-months of the fit periods only.

    The first version of the estimator (PR #43); `estimate_dispersion` supersedes it. The ratios were fitted on these months,
    so the differences are smaller than out of sample and phi is a lower bound (test D1 checks the coverage).
    """
    units, pairs = fit_units(paths or Paths(), min_cell_days, fits)
    out: dict = {"pairs": {}, "min_cell_days": min_cell_days}
    for w, per in pairs.items():
        out["pairs"][w] = {dn: {"units": len(a[0]), "phi": solve_phi(a[0], a[1], a[2])} for dn, a in per.items()}
    out["phi_estimate"] = {dn: solve_phi(u[0], u[1], u[2]) for dn, u in units.items()}
    out["phi"] = {dn: max(1.0, v) for dn, v in out["phi_estimate"].items()}      # never below Poisson
    return out


def band_medians(d, vc, vr, s2, size, phi: float, kappa: float, bands=SIZE_BANDS) -> list[dict]:
    """Median of d^2 / expected variance per size band; near the chi-square(1) median (0.455) everywhere means a good fit."""
    ok = np.isfinite(d) & (vc > 0)
    expected = phi * vc + vr + kappa * s2
    z = np.where(ok, d ** 2 / np.where(expected > 0, expected, np.nan), np.nan)
    edges = list(bands) + [np.inf]
    rows = []
    for lo, hi in pairwise(edges):
        sel = ok & (size >= lo) & (size < hi)
        rows.append({"from": lo, "to": None if np.isinf(hi) else hi, "units": int(sel.sum()),
                     "median": float(np.nanmedian(z[sel])) if sel.sum() else float("nan")})
    return rows


def solve_dispersion(d, vc, vr, s2, size, bands=SIZE_BANDS) -> tuple[float, float]:
    """phi and kappa >= 0 for the variance  phi x vc + vr + kappa x s2  (jointly, chi-square(1) median criterion).

    For each phi on a log grid, kappa is the value that puts the median of d^2 / expected over all units at the chi-square(1)
    median (kappa = 0 if the median is already below it); phi is then the grid value whose size bands are closest to the target
    (sum of squared log-medians). With kappa fixed at 0 this is `solve_phi`. Nan if there are too few units.
    """
    ok = np.isfinite(d) & np.isfinite(vc) & np.isfinite(vr) & np.isfinite(s2) & (vc > 0) & (s2 > 0)
    d, vc, vr, s2, size = d[ok], vc[ok], vr[ok], s2[ok], size[ok]
    if len(d) < 20:
        return float("nan"), float("nan")
    d2 = d ** 2
    target = np.log(CHI2_1DF_MEDIAN)
    edges = list(bands) + [np.inf]
    masks = [(size >= lo) & (size < hi) for lo, hi in pairwise(edges)]
    masks = [m for m in masks if m.sum() >= 10]

    def kappa_for(phi: float) -> float:
        if np.median(d2 / (phi * vc + vr)) <= CHI2_1DF_MEDIAN:
            return 0.0
        lo, hi = 0.0, 1e3
        for _ in range(80):
            mid = 0.5 * (lo + hi)
            if np.median(d2 / (phi * vc + vr + mid * s2)) > CHI2_1DF_MEDIAN:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)

    def loss(phi: float) -> float:
        k = kappa_for(phi)
        e = phi * vc + vr + k * s2
        return float(sum((np.log(np.median(d2[m] / e[m])) - target) ** 2 for m in masks))

    grid = np.exp(np.linspace(np.log(0.5), np.log(60.0), 90))
    best = min(grid, key=loss)
    fine = best * np.exp(np.linspace(-0.12, 0.12, 49))
    best = min(fine, key=loss)
    return float(best), float(kappa_for(best))


def estimate_dispersion(paths: Paths | None = None, min_cell_days: float = SIZE_BANDS[0], fits: dict | None = None,
                        factors: pd.DataFrame | None = None) -> dict:
    """phi and kappa per day/night from country-months of the fit periods only, with the fit by size band.

    Units are country-months where both converted estimates are at least `min_cell_days` (default 5 cell-days, the lowest band).
    Returns the estimates, the number of units, and the median of d^2 / expected per size band for the phi-only model (the first
    PR #43 version) and for the phi + kappa model: near 0.455 in every band means the size dependence is captured.
    """
    units, _ = fit_units(paths or Paths(), min_cell_days, fits, factors)
    out: dict = {"min_cell_days": min_cell_days, "method": "phi and kappa jointly, chi-square(1) median per size band",
                 "phi": {}, "kappa": {}, "units": {}, "bands_phi_only": {}, "bands_phi_kappa": {}}
    for dn, (d, vc, vr, s2, size) in units.items():
        phi, kappa = solve_dispersion(d, vc, vr, s2, size)
        out["phi"][dn], out["kappa"][dn], out["units"][dn] = max(1.0, phi), kappa, len(d)
        out["bands_phi_only"][dn] = band_medians(d, vc, vr, s2, size, PHI_ONLY[dn], 0.0)
        out["bands_phi_kappa"][dn] = band_medians(d, vc, vr, s2, size, phi, kappa)
    return out


# ------------------------------------------------------------------------------------------------ data access
def aggregate(con, paths: Paths, members: str, months: list[tuple[int, int]] | None, factors: pd.DataFrame | None = None) -> pd.DataFrame:
    """One row per entity x month x witness x day/night: converted estimate and the two parts of its variance.

    `members` is a table (entity_type, entity_id, entity_name, cell_id). Raw cell-days are summed per stratum first.
    e: sum of ratio x cell_days. vc: counting variance at phi = 1 (sum of ratio^2 x cell_days). vr: ratio variance, each ratio
    source (a LOCAL stratum, a region's pooled estimate, the global estimate) counted as one fully correlated group.

    `factors` (method 0.2, T-020c; None = method 0.1, and the SQL is then exactly the earlier one): activity factors with the columns
    witness, daynight, lo, hi, f, f_sd (one row per witness x day/night x activity bin). The ratio of a VIIRS stratum-month becomes
    ratio x f(bin), the bin of its converted activity (ratio x witness cell-days of the whole stratum-month / cells of the stratum);
    the stratum ratio error is scaled by f and the factor error is one extra fully correlated group per witness, day/night and bin.
    """
    cmw = f"read_parquet('{(paths.products / 'cell_month_witness.parquet').as_posix()}')"
    cells = f"read_parquet('{(paths.products / 'cells.parquet').as_posix()}')"
    cal = f"read_parquet('{(paths.products / 'calibration.parquet').as_posix()}')"
    when = "" if months is None else " AND w.year * 100 + w.month IN (" + ", ".join(str(y * 100 + m) for y, m in months) + ")"
    wit = ", ".join(f"'{x}'" for x in RAW_WITNESSES)
    # join the (small) members to the cells first: joined the other way round, the engine joins all rows of cmw with cells before
    # filtering and a country takes minutes instead of a second
    con.execute(f"CREATE OR REPLACE TEMP TABLE mem AS SELECT m.*, c.stratum_id FROM {members} m JOIN {cells} c USING (cell_id)")
    if factors is not None:
        return _aggregate_v02(con, members, when, wit, cmw, cells, cal, factors)
    sql = f"""
    WITH base AS (
        SELECT m.entity_type, m.entity_id, any_value(m.entity_name) AS entity_name, m.stratum_id, w.year, w.month, w.witness, w.daynight,
               sum(w.cell_days) AS cd, bool_and(w.days_available = w.days_in_month) AS complete,
               min(w.data_level) AS lo, max(w.data_level) AS hi
        FROM {cmw} w JOIN mem m USING (cell_id)
        WHERE w.daynight IN ('D', 'N') AND w.witness IN ({wit}){when}
        GROUP BY m.entity_type, m.entity_id, m.stratum_id, w.year, w.month, w.witness, w.daynight),
    conv AS (
        SELECT b.*, CASE WHEN b.witness = 'AQUA_MODIS' THEN 1.0 ELSE k.ratio END AS r,
               CASE WHEN b.witness = 'AQUA_MODIS' THEN 0.0 ELSE k.ratio_sd END AS rsd,
               CASE WHEN b.witness <> 'AQUA_MODIS' AND k.pooling_level <> 'LOCAL' THEN 1 ELSE 0 END AS pooled,
               CASE WHEN b.witness = 'AQUA_MODIS' THEN 'AQUA' WHEN k.pooling_level = 'LOCAL' THEN b.stratum_id
                    WHEN k.pooling_level = 'REGION' THEN split_part(b.stratum_id, '_b', 1) ELSE 'GLOBAL' END AS src
        FROM base b LEFT JOIN {cal} k ON k.stratum_id = b.stratum_id AND k.witness = b.witness AND k.daynight = b.daynight
             AND k.season = {SEASON_SQL.replace('w.month', 'b.month')}),
    grp AS (
        SELECT entity_type, entity_id, any_value(entity_name) AS entity_name, year, month, witness, daynight, src,
               sum(cd) AS raw, bool_and(complete) AS complete, min(lo) AS lo, max(hi) AS hi,
               sum(r * cd) AS e, sum(r * r * cd) AS vc, power(sum(cd * rsd), 2) AS vr, sum(r) AS sr, count(*) AS nr,
               sum(pooled * r * cd) AS e_pooled,
               count(*) FILTER (WHERE r IS NULL) AS missing
        FROM conv GROUP BY entity_type, entity_id, year, month, witness, daynight, src)
    SELECT entity_type, entity_id, any_value(entity_name) AS entity_name, year, month, witness, daynight,
           sum(raw) AS raw, bool_and(complete) AS complete, min(lo) AS lo, max(hi) AS hi,
           sum(e) AS e, sum(vc) AS vc, sum(vr) AS vr, sum(sr) / sum(nr) AS rbar, sum(missing) AS missing, sum(e_pooled) AS e_pooled
    FROM grp GROUP BY entity_type, entity_id, year, month, witness, daynight
    ORDER BY entity_type, entity_id, year, month, witness, daynight"""
    return con.execute(sql).df()


def _aggregate_v02(con, members: str, when: str, wit: str, cmw: str, cells: str, cal: str, factors: pd.DataFrame) -> pd.DataFrame:
    """`aggregate` for method 0.2: the same table with ratio x f(activity bin); see `aggregate`."""
    need = ["witness", "daynight", "lo", "hi", "f", "f_sd"]
    if not set(need) <= set(factors.columns):
        raise ValueError(f"factors needs the columns {need}")
    con.register("factors_df", factors[need])
    con.execute("CREATE OR REPLACE TEMP TABLE fac AS SELECT * FROM factors_df")
    # Converted activity per analysis cell of every stratum-month of the strata of the members (whole strata, not only the members' cells).
    # Two materialised steps: with the ratio join in the same query the planner reordered the joins and spilled tens of GB on large boxes.
    con.execute(f"""CREATE OR REPLACE TEMP TABLE act0 AS
        WITH strata AS (SELECT DISTINCT stratum_id FROM mem),
             cs AS (SELECT c.cell_id, c.stratum_id FROM {cells} c JOIN strata USING (stratum_id))
        SELECT c.stratum_id, w.year, w.month, w.witness, w.daynight, sum(w.cell_days) AS cd
        FROM {cmw} w JOIN cs c USING (cell_id)
        WHERE w.daynight IN ('D', 'N') AND w.witness IN ('SNPP_VIIRS', 'NOAA20_VIIRS'){when}
        GROUP BY c.stratum_id, w.year, w.month, w.witness, w.daynight""")
    con.execute(f"""CREATE OR REPLACE TEMP TABLE act AS
        WITH ncell AS (SELECT stratum_id, count(*) AS n FROM {cells} GROUP BY stratum_id)
        SELECT a.stratum_id, a.year, a.month, a.witness, a.daynight, a.cd * k.ratio / n.n AS x
        FROM act0 a JOIN ncell n USING (stratum_id)
             JOIN {cal} k ON k.stratum_id = a.stratum_id AND k.witness = a.witness AND k.daynight = a.daynight
                  AND k.season = {SEASON_SQL.replace('w.month', 'a.month')}""")
    sql = f"""
    WITH base AS (
        SELECT m.entity_type, m.entity_id, any_value(m.entity_name) AS entity_name, m.stratum_id, w.year, w.month, w.witness, w.daynight,
               sum(w.cell_days) AS cd, bool_and(w.days_available = w.days_in_month) AS complete,
               min(w.data_level) AS lo, max(w.data_level) AS hi
        FROM {cmw} w JOIN mem m USING (cell_id)
        WHERE w.daynight IN ('D', 'N') AND w.witness IN ({wit}){when}
        GROUP BY m.entity_type, m.entity_id, m.stratum_id, w.year, w.month, w.witness, w.daynight),
    conv0 AS (
        SELECT b.*, CASE WHEN b.witness = 'AQUA_MODIS' THEN 1.0 ELSE k.ratio END AS r0,
               CASE WHEN b.witness = 'AQUA_MODIS' THEN 0.0 ELSE k.ratio_sd END AS rsd0,
               CASE WHEN b.witness <> 'AQUA_MODIS' AND k.pooling_level <> 'LOCAL' THEN 1 ELSE 0 END AS pooled,
               CASE WHEN b.witness = 'AQUA_MODIS' THEN 'AQUA' WHEN k.pooling_level = 'LOCAL' THEN b.stratum_id
                    WHEN k.pooling_level = 'REGION' THEN split_part(b.stratum_id, '_b', 1) ELSE 'GLOBAL' END AS src
        FROM base b LEFT JOIN {cal} k ON k.stratum_id = b.stratum_id AND k.witness = b.witness AND k.daynight = b.daynight
             AND k.season = {SEASON_SQL.replace('w.month', 'b.month')}),
    conv AS (
        SELECT c.*, CASE WHEN c.witness = 'AQUA_MODIS' THEN 1.0 ELSE f.f END AS fac,
               CASE WHEN c.witness = 'AQUA_MODIS' THEN 0.0 ELSE f.f_sd END AS fac_sd,
               CASE WHEN c.witness = 'AQUA_MODIS' THEN NULL ELSE c.witness || '|' || c.daynight || '|' || CAST(f.lo AS VARCHAR) END AS fsrc
        FROM conv0 c LEFT JOIN act a ON a.stratum_id = c.stratum_id AND a.year = c.year AND a.month = c.month
             AND a.witness = c.witness AND a.daynight = c.daynight
             LEFT JOIN fac f ON f.witness = c.witness AND f.daynight = c.daynight AND a.x >= f.lo AND a.x < f.hi),
    conv2 AS (
        SELECT *, r0 * fac AS r, rsd0 * fac AS rsd FROM conv),
    grp AS (
        SELECT entity_type, entity_id, any_value(entity_name) AS entity_name, year, month, witness, daynight, src,
               sum(cd) AS raw, bool_and(complete) AS complete, min(lo) AS lo, max(hi) AS hi,
               sum(r * cd) AS e, sum(r * r * cd) AS vc, power(sum(cd * rsd), 2) AS vr, sum(r) AS sr, count(*) AS nr,
               sum(pooled * r * cd) AS e_pooled,
               count(*) FILTER (WHERE r IS NULL) AS missing
        FROM conv2 GROUP BY entity_type, entity_id, year, month, witness, daynight, src),
    grpf AS (
        SELECT entity_type, entity_id, any_value(entity_name) AS entity_name, year, month, witness, daynight, fsrc AS src,
               CAST(0 AS DOUBLE) AS raw, true AS complete, min(lo) AS lo, max(hi) AS hi,
               CAST(0 AS DOUBLE) AS e, CAST(0 AS DOUBLE) AS vc, power(sum(cd * r0 * fac_sd), 2) AS vr, CAST(0 AS DOUBLE) AS sr,
               CAST(0 AS BIGINT) AS nr, CAST(0 AS DOUBLE) AS e_pooled, CAST(0 AS BIGINT) AS missing
        FROM conv2 WHERE fsrc IS NOT NULL AND fac_sd IS NOT NULL GROUP BY entity_type, entity_id, year, month, witness, daynight, fsrc),
    allg AS (SELECT * FROM grp UNION ALL SELECT * FROM grpf)
    SELECT entity_type, entity_id, any_value(entity_name) AS entity_name, year, month, witness, daynight,
           sum(raw) AS raw, bool_and(complete) AS complete, min(lo) AS lo, max(hi) AS hi,
           sum(e) AS e, sum(vc) AS vc, sum(vr) AS vr, sum(sr) / sum(nr) AS rbar, sum(missing) AS missing, sum(e_pooled) AS e_pooled
    FROM allg GROUP BY entity_type, entity_id, year, month, witness, daynight
    ORDER BY entity_type, entity_id, year, month, witness, daynight"""
    df = con.execute(sql).df()
    bad = df[df.witness.isin(["SNPP_VIIRS", "NOAA20_VIIRS"]) & (df.e.isna() | (df.missing > 0))]    # Terra has no ratio in either method
    if len(bad):
        raise ValueError(f"{len(bad)} VIIRS rows have no activity factor or no calibration ratio")
    return df


def _level(lo: str, hi: str) -> str:
    return lo if lo == hi else "MIXED"


def _excluded_daynights(aqua_from: dict[str, tuple[int, int] | None], year: int, month: int) -> set[str]:
    """The day/night parts for which Aqua is not combined in this month (from the start month of its exclusion on)."""
    return {dn for dn, start in aqua_from.items() if start is not None and (year, month) >= tuple(start)}


def _combine_witnesses(g: pd.DataFrame, phi: dict[str, float], kappa: dict[str, float], excluded: set[str], separate: bool = True) -> dict:
    """Combine the witnesses of one entity-month: separately for day and for night, then add the two combined estimates (their
    variances add; the disagreement `S` is pooled over both parts). One method for every month, so that excluding Aqua night from
    2024-05 (D-005) creates no step in the method. `separate=False` is the earlier way (sum day and night per witness, then
    combine the witnesses), kept only to measure how much the two differ (`seam_check`)."""
    n_w = len(WITNESSES)
    if not excluded and not separate:
        est, var, use = np.full((1, n_w), np.nan), np.full((1, n_w), np.nan), np.zeros((1, n_w), dtype=bool)
        for j, w in enumerate(WITNESSES):
            rows = g[g.witness == w]
            if rows.empty:
                continue
            if rows["missing"].sum():
                raise ValueError(f"{int(rows['missing'].sum())} stratum rows have no calibration ratio")
            est[0, j] = rows["e"].sum()
            counting = sum(phi[r.daynight] * r.vc + kappa[r.daynight] * r.e ** 2 for r in rows.itertuples())
            floor = float(rows["rbar"].mean()) ** 2
            var[0, j] = max(counting + float(rows["vr"].sum()), floor)       # a zero count still carries one cell-day of variance
            use[0, j] = bool(rows["complete"].all())
        c = combine(est, var, use)
        used = [w for j, w in enumerate(WITNESSES) if use[0, j] and np.isfinite(est[0, j])]
        return {"n": int(c["n"][0]), "used": used, "parts": {(w, dn) for w in used for dn in ("D", "N")}, "estimate": float(c["estimate"][0]),
                "sd": float(c["sd"][0]), "scale": float(c["scale"][0]), "disagree": bool(c["disagree"][0]), "aqua_excluded": False}
    total, plain_var, chi2, dof, used, parts, hit, complete = 0.0, 0.0, 0.0, 0, set(), set(), False, True
    for dn in ("D", "N"):
        est, var, use = np.full((1, n_w), np.nan), np.full((1, n_w), np.nan), np.zeros((1, n_w), dtype=bool)
        for j, w in enumerate(WITNESSES):
            rows = g[(g.witness == w) & (g.daynight == dn)]
            if rows.empty:
                continue
            r = rows.iloc[0]
            if r["missing"]:
                raise ValueError(f"{int(r['missing'])} stratum rows have no calibration ratio")
            est[0, j] = float(r.e)
            var[0, j] = max(phi[dn] * float(r.vc) + kappa[dn] * float(r.e) ** 2 + float(r.vr), float(r.rbar) ** 2)
            use[0, j] = bool(r.complete)
            if w == "AQUA_MODIS" and dn in excluded:
                hit = hit or use[0, j]
                use[0, j] = False
        if not (g.daynight == dn).any():
            continue                              # no data at all for this part (not possible in the real products): nothing to add
        c = combine(est, var, use)
        if int(c["n"][0]) == 0:
            complete = False                      # a day/night part with data but no witness that counts: no total
            continue
        n_dn = int(c["n"][0])
        total += float(c["estimate"][0])
        plain_var += float(c["sd"][0]) ** 2 / (float(c["scale"][0]) ** 2 if n_dn >= 2 else 1.0)
        chi2 += float(c["chi2"][0])
        dof += n_dn - 1
        used_dn = {w for j, w in enumerate(WITNESSES) if use[0, j] and np.isfinite(est[0, j])}
        used |= used_dn
        parts |= {(w, dn) for w in used_dn}
    if not complete:
        return {"n": 0, "used": [], "parts": set(), "estimate": float("nan"), "sd": float("nan"), "scale": float("nan"), "disagree": False,
                "aqua_excluded": hit}
    s = float(np.sqrt(chi2 / dof)) if dof > 0 else float("nan")
    # two witnesses overall but never two for the same part (for example S-NPP by day and NOAA-20 by night): nothing to cross-check,
    # so the scale is 1 (the contract wants a scale of at least 1 with 2 or more witnesses); one witness overall: no scale
    scale = max(s, 1.0) if dof > 0 else (1.0 if len(used) >= 2 else float("nan"))
    return {"n": len(used), "used": [w for w in WITNESSES if w in used], "parts": parts, "estimate": total,
            "sd": float(np.sqrt(plain_var)) * (scale if dof > 0 else 1.0), "scale": scale, "disagree": bool(dof > 0 and s > DISAGREEMENT_CODE),
            "aqua_excluded": hit}


def records_from(agg: pd.DataFrame, n_cells: dict[tuple[str, str], int], aqua_from: dict[str, tuple[int, int] | None] | None = None,
                 phi: dict[str, float] | None = None, kappa: dict[str, float] | None = None, separate: bool = True) -> list[dict]:
    """Contract-shaped records from the aggregated table (`separate`: combine day and night separately, the default; False: the earlier method)."""
    phi = phi or PHI
    kappa = KAPPA if kappa is None else kappa
    aqua_from = AQUA_FROM if aqua_from is None else aqua_from
    out: list[dict] = []
    for (etype, eid, year, month), g in agg.groupby(["entity_type", "entity_id", "year", "month"], sort=True):
        raw_by = {w: int(g.loc[g.witness == w, "raw"].sum()) for w in RAW_WITNESSES if (g.witness == w).any()}
        try:
            c = _combine_witnesses(g, phi, kappa, _excluded_daynights(aqua_from, int(year), int(month)), separate)
        except ValueError as e:
            raise ValueError(f"{etype} {eid} {year}-{month:02d}: {e}") from e
        n, used = c["n"], c["used"]
        levels = g[[(w, d) in c["parts"] for w, d in zip(g.witness, g.daynight, strict=True)]] if used else g       # the rows that were used
        reasons = []
        if n == 1:
            reasons.append("SINGLE_WITNESS")
        if c["disagree"]:
            reasons.append("WITNESS_DISAGREEMENT")
        if c["aqua_excluded"]:
            reasons.append("AQUA_DRIFT_ERA")
        level = _level(levels["lo"].min(), levels["hi"].max())
        if level in ("NRT", "MIXED"):
            reasons.append("PROVISIONAL_NRT")
        rec = {"entity_type": etype, "entity_id": eid, "entity_name": g["entity_name"].iloc[0], "year": int(year), "month": int(month),
               "estimate": None, "ci90_low": None, "ci90_high": None, "sd": None,
               "raw_combined_cell_days": int(sum(raw_by.values())), "witnesses_used": used, "n_witnesses": n,
               "disagreement_scale": None if np.isnan(c["scale"]) else float(c["scale"])}
        if n > 0:
            rec["estimate"], rec["sd"] = float(c["estimate"]), float(c["sd"])
            rec["ci90_low"], rec["ci90_high"] = interval(rec["estimate"], rec["sd"])
        rec.update({k: None for k in HARMONIZED_NULLS})
        rec.update({"verdict": "CANNOT_DETERMINE", "reason_codes": sorted(reasons), "data_level": level,
                    "method_version": METHOD_VERSION, "n_cells": n_cells[(etype, eid)],
                    "raw_by_witness": json.dumps(raw_by)})
        out.append(rec)
    return out


def harmonize_area(cell_ids: list[str], months: list[tuple[int, int]] | None = None, paths: Paths | None = None,
                   aqua_from: dict[str, tuple[int, int] | None] | None = None, entity_id: str = "CUSTOM", entity_name: str = "Custom area",
                   phi: dict[str, float] | None = None, kappa: dict[str, float] | None = None, separate: bool = True) -> list[dict]:
    """The single implementation of the science for an area: `entity_month` records (DATA_CONTRACT.md section 4, 8).

    `cell_ids` are analysis cells of cells.parquet; `months` is a list of (year, month) or None for every month with data.
    `aqua_from`: per day/night, the month from which Aqua is not combined (default `AQUA_FROM`: night from 2024-05, D-005; pass
    {"D": None, "N": None} to keep Aqua everywhere). `separate`: combine day and night separately in every month (the default,
    one method for all months; False is the earlier totals method, kept for the seam check).
    `phi`, `kappa`: overdispersion and relative error per day/night (default: the estimates on the fit periods, `PHI`, `KAPPA`).
    Deterministic for the same inputs and method_version; records are ordered by year and month.
    """
    paths = paths or Paths()
    ids = sorted(set(cell_ids))
    if not ids:
        return []
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    known = {r[0] for r in con.execute(f"SELECT cell_id FROM read_parquet('{(paths.products / 'cells.parquet').as_posix()}')").fetchall()}
    unknown = [c for c in ids if c not in known]
    if unknown:
        raise ValueError(f"{len(unknown)} cell_ids are not in cells.parquet, for example {unknown[:3]}")
    members = pd.DataFrame({"entity_type": "CUSTOM", "entity_id": entity_id, "entity_name": entity_name, "cell_id": ids})
    con.register("members_df", members)
    con.execute("CREATE TEMP TABLE members AS SELECT * FROM members_df")
    agg = aggregate(con, paths, "members", months)
    return records_from(agg, {("CUSTOM", entity_id): len(ids)}, aqua_from, phi, kappa, separate)


# --------------------------------------------------------------------------------------------- the seam at the cutoff
def seam_check(paths: Paths | None = None, first: tuple[int, int] = (2012, 1), last: tuple[int, int] = (2024, 4)) -> dict:
    """How much the two ways of combining differ before the cutoff month: day+night totals combined (the method before 2024-05)
    against day and night combined separately and added (the method from 2024-05), with no Aqua exclusion in either, for every
    country-month and fire-region-month from `first` to `last`. Decision rule fixed by the Lead (PR #45): median |log(separate / totals)|
    of the estimate at most 1% and its 95th percentile at most 5%: no visible seam.
    """
    paths = paths or Paths()
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    cells = f"read_parquet('{(paths.products / 'cells.parquet').as_posix()}')"
    con.execute(f"""CREATE TEMP TABLE members AS
        SELECT 'COUNTRY' AS entity_type, country_iso3 AS entity_id, country_iso3 AS entity_name, cell_id FROM {cells} WHERE country_iso3 IS NOT NULL
        UNION ALL
        SELECT 'REGION', fire_region, fire_region, cell_id FROM {cells} WHERE fire_region IS NOT NULL""")
    counts = {(t, e): n for t, e, n in con.execute("SELECT entity_type, entity_id, count(*) FROM members GROUP BY 1, 2").fetchall()}
    months = [(y, m) for y in range(first[0], last[0] + 1) for m in range(1, 13) if first <= (y, m) <= last]
    agg = aggregate(con, paths, "members", months)
    none = {"D": None, "N": None}
    a = pd.DataFrame(records_from(agg, counts, none, separate=False))
    b = pd.DataFrame(records_from(agg, counts, none, separate=True))
    keys = ["entity_type", "entity_id", "year", "month"]
    m = a.merge(b, on=keys, suffixes=("_tot", "_sep"))
    both = m[m.estimate_tot.notna() & m.estimate_sep.notna() & (m.estimate_tot > 0) & (m.estimate_sep > 0)].copy()
    both["dlog"] = np.abs(np.log(both.estimate_sep / both.estimate_tot))
    both["sd_ratio"] = both.sd_sep / both.sd_tot

    def summarise(x: pd.DataFrame) -> dict:
        return {"entity_months": len(x), "median_abs_log_diff": float(x.dlog.median()), "p95_abs_log_diff": float(x.dlog.quantile(0.95)),
                "p99_abs_log_diff": float(x.dlog.quantile(0.99)), "max_abs_log_diff": float(x.dlog.max()),
                "median_sd_ratio": float(x.sd_ratio.median()), "p05_sd_ratio": float(x.sd_ratio.quantile(0.05)),
                "p95_sd_ratio": float(x.sd_ratio.quantile(0.95))}
    out = {"window": f"{first[0]}-{first[1]:02d} to {last[0]}-{last[1]:02d}", "rule": "median <= 1% and p95 <= 5%", "all": summarise(both),
           "two_plus_witnesses": summarise(both[both.n_witnesses_tot >= 2]), "by_type": {t: summarise(g) for t, g in both.groupby("entity_type")}}
    out["no_seam"] = bool(out["two_plus_witnesses"]["median_abs_log_diff"] <= 0.01 and out["two_plus_witnesses"]["p95_abs_log_diff"] <= 0.05
                          and out["all"]["median_abs_log_diff"] <= 0.01 and out["all"]["p95_abs_log_diff"] <= 0.05)
    (paths.products.parent / "interim" / "qa").mkdir(parents=True, exist_ok=True)
    (paths.products.parent / "interim" / "qa" / "harmonize_seam.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


# ------------------------------------------------------------------------------------------------ real-data report
def report(paths: Paths | None = None, aqua_from: dict[str, tuple[int, int] | None] | None = None, phi: dict[str, float] | None = None,
           kappa: dict[str, float] | None = None) -> dict:
    """Run the combination over every country; summarise how the witnesses agree.

    A diagnostic for the T-013 review, not a product: it writes data/interim/qa/harmonize_report.json.
    """
    paths = paths or Paths()
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    cells = f"read_parquet('{(paths.products / 'cells.parquet').as_posix()}')"
    con.execute(f"""CREATE TEMP TABLE members AS SELECT 'COUNTRY' AS entity_type, country_iso3 AS entity_id, country_iso3 AS entity_name, cell_id
                    FROM {cells} WHERE country_iso3 IS NOT NULL""")
    counts = dict(con.execute("SELECT entity_id, count(*) FROM members GROUP BY 1").fetchall())
    agg = aggregate(con, paths, "members", None)
    n_cells = {("COUNTRY", k): v for k, v in counts.items()}
    out: dict = {"phi": phi or PHI, "kappa": KAPPA if kappa is None else kappa}
    variants = (("phi_only", PHI_ONLY, KAPPA0), ("phi_and_kappa", phi or PHI, KAPPA if kappa is None else kappa))
    for label, ph, ka in variants:
        recs = pd.DataFrame(records_from(agg, n_cells, aqua_from, ph, ka))
        two = recs[recs.n_witnesses >= 2]
        s = two.disagreement_scale.astype(float)
        rel_sd = (recs.sd / recs.estimate).replace([np.inf, -np.inf], np.nan)
        out[label] = {"country_months": len(recs), "with_estimate": int(recs.estimate.notna().sum()),
                      "n_witnesses": {int(k): int(v) for k, v in recs.n_witnesses.value_counts().sort_index().items()},
                      "two_plus_witness_months": len(s),
                      "scale_quantiles": {str(q): float(s.quantile(q)) for q in (0.05, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99)},
                      "share_scale_gt": {str(t): float((s > t).mean()) for t in (1.0, 1.5, 2.0, 3.0, 5.0)},
                      "relative_sd_median": float(rel_sd.median()),
                      "indonesia_share_scale_gt": {str(t): float((recs[(recs.entity_id == "IDN") & (recs.n_witnesses >= 2)].disagreement_scale > t).mean())
                                                   for t in (1.0, 2.0)},
                      "no_estimate_months": sorted({f"{r.year}-{r.month:02d}" for r in recs[recs.estimate.isna()].itertuples()})}
    wide = agg.groupby(["entity_id", "year", "month", "witness"]).e.sum().unstack()
    rel = {}
    for w in ("SNPP_VIIRS", "NOAA20_VIIRS"):
        both = wide[["AQUA_MODIS", w]].dropna()
        both = both[(both.AQUA_MODIS >= 100) & (both[w] >= 100)]
        lr = np.log(both[w] / both.AQUA_MODIS)
        rel[w] = {"country_months": len(lr), "median_ratio": float(np.exp(lr.median())),
                  "p05_ratio": float(np.exp(lr.quantile(0.05))), "p95_ratio": float(np.exp(lr.quantile(0.95)))}
    out["converted_over_aqua"] = rel
    (paths.products.parent / "interim" / "qa" / "harmonize_report.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["seam"]:
        print(json.dumps(seam_check(), indent=1))
    elif sys.argv[1:] == ["phi"]:
        res = estimate_dispersion()
        (Paths().products.parent / "interim" / "qa" / "harmonize_dispersion.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        print(json.dumps(res, indent=1))
    else:
        print(json.dumps(report(), indent=1))
