"""Witness combination with disagreement inflation, and `harmonize_area()` (T-013).

For any area (a list of analysis cells) and month, each witness gives an Aqua-equivalent estimate

    E_w = sum over strata s and day/night d of  ratio(s, w, d, season) x cell_days(s, w, d)

(Aqua has ratio 1 and no ratio uncertainty; Terra is raw view only and never enters the estimate). Raw cell-days are summed per
witness and stratum BEFORE they are converted (docs/SCIENTIFIC_METHODOLOGY.md 4.5). The variance of E_w has two parts:

  * counting noise, per stratum and day/night:  phi_d x ratio^2 x cell_days.  phi_d is an overdispersion factor (phi = 1 is
    Poisson), estimated once on the calibration fit periods only (`estimate_phi`) and applied to every witness;
  * ratio error, shared: strata that take the same ratio share the same error, so their errors are added fully correlated.
    The groups are the ratio sources: each LOCAL stratum, each fire region's pooled estimate (strata with pooling level REGION)
    and the global estimate (GLOBAL), per witness, day/night and season:   (sum over the group of cell_days x ratio_sd)^2.

The witnesses of a month are combined with a precision-weighted mean. If they disagree more than their variances allow, the
combined sd is multiplied by S = sqrt(chi^2 / (N - 1)) (only when S > 1; the Birge ratio, the usual rule for discordant
measurements); the reason code WITNESS_DISAGREEMENT is given when S > 2. Baseline, probabilities and verdicts belong to T-014:
here the baseline fields are null and the verdict is CANNOT_DETERMINE, as the contract requires without a baseline.

    from harmonize import harmonize_area
    records = harmonize_area(cell_ids, months=None)       # list of dicts in the shape of DATA_CONTRACT.md section 4
    python pipeline/harmonize.py phi                       # re-estimate the overdispersion factors
    python pipeline/harmonize.py                           # the real-data diagnostic

Approved by the Lead 2026-11-14 (PR #43): day and night converted separately and added; a variance floor of one cell-day for
a zero count; only complete witness-months count; a 90% normal interval with the lower bound at 0; no estimate for the
2002-07 to 2002-09 outage months. Strata that share no ratio source are treated as independent (limitation).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
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
PHI = {"D": 7.72, "N": 6.53}   # `python pipeline/harmonize.py phi` on the T-011 products, 2026-11-14, units of at least 20 cell-days


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


def estimate_phi(paths: Paths | None = None, min_cell_days: float = 20.0, fits: dict | None = None) -> dict:
    """Estimate the overdispersion factor per day/night from country-months of the calibration fit periods only.

    Each pair is Aqua against one VIIRS witness inside that witness's fit period (S-NPP 2012-01 to 2016-12; NOAA-20 2018-04 to
    2021-12: S-NPP is not used after 2016, the held-out years are never read). Units are country-months where both converted
    estimates are at least `min_cell_days`, so the counts are not tiny. The ratios were fitted on these months, so the
    differences are smaller than out of sample and phi is a lower bound (test D1 checks the coverage).
    """
    import calibration as cal
    paths = paths or Paths()
    fits = fits or cal.FITS
    con = duckdb.connect()
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    cells = f"read_parquet('{(paths.products / 'cells.parquet').as_posix()}')"
    con.execute(f"""CREATE TEMP TABLE members AS SELECT 'COUNTRY' AS entity_type, country_iso3 AS entity_id, country_iso3 AS entity_name, cell_id
                    FROM {cells} WHERE country_iso3 IS NOT NULL""")
    agg = aggregate(con, paths, "members", None)
    out: dict = {"pairs": {}, "min_cell_days": min_cell_days}
    pooled: dict[str, list] = {"D": [], "N": []}
    for w, ((y0, m0), (y1, m1)) in fits.items():
        ym = agg.year * 100 + agg.month
        sub = agg[(ym >= y0 * 100 + m0) & (ym <= y1 * 100 + m1) & agg.complete]
        a = sub[sub.witness == "AQUA_MODIS"].set_index(["entity_id", "year", "month", "daynight"])
        v = sub[sub.witness == w].set_index(["entity_id", "year", "month", "daynight"])
        j = a.join(v, lsuffix="_a", rsuffix="_w", how="inner")
        j = j[(j.e_a >= min_cell_days) & (j.e_w >= min_cell_days)]
        out["pairs"][w] = {}
        for dn in ("D", "N"):
            jd = j[j.index.get_level_values("daynight") == dn]
            d, vc, vr = (jd.e_w - jd.e_a).to_numpy(), (jd.vc_a + jd.vc_w).to_numpy(), jd.vr_w.to_numpy()
            out["pairs"][w][dn] = {"units": len(jd), "phi": solve_phi(d, vc, vr)}
            pooled[dn].append((d, vc, vr))
    out["phi_estimate"] = {dn: solve_phi(*(np.concatenate(x) for x in zip(*pooled[dn], strict=True))) for dn in pooled}
    out["phi"] = {dn: max(1.0, v) for dn, v in out["phi_estimate"].items()}      # never below Poisson
    return out


# ------------------------------------------------------------------------------------------------ data access
def aggregate(con, paths: Paths, members: str, months: list[tuple[int, int]] | None) -> pd.DataFrame:
    """One row per entity x month x witness x day/night: converted estimate and the two parts of its variance.

    `members` is a table (entity_type, entity_id, entity_name, cell_id). Raw cell-days are summed per stratum first.
    e: sum of ratio x cell_days. vc: counting variance at phi = 1 (sum of ratio^2 x cell_days). vr: ratio variance, each ratio
    source (a LOCAL stratum, a region's pooled estimate, the global estimate) counted as one fully correlated group.
    """
    cmw = f"read_parquet('{(paths.products / 'cell_month_witness.parquet').as_posix()}')"
    cells = f"read_parquet('{(paths.products / 'cells.parquet').as_posix()}')"
    cal = f"read_parquet('{(paths.products / 'calibration.parquet').as_posix()}')"
    when = "" if months is None else " AND w.year * 100 + w.month IN (" + ", ".join(str(y * 100 + m) for y, m in months) + ")"
    wit = ", ".join(f"'{x}'" for x in RAW_WITNESSES)
    # join the (small) members to the cells first: joined the other way round, the engine joins all rows of cmw with cells before
    # filtering and a country takes minutes instead of a second
    con.execute(f"CREATE OR REPLACE TEMP TABLE mem AS SELECT m.*, c.stratum_id FROM {members} m JOIN {cells} c USING (cell_id)")
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
               CASE WHEN b.witness = 'AQUA_MODIS' THEN 'AQUA' WHEN k.pooling_level = 'LOCAL' THEN b.stratum_id
                    WHEN k.pooling_level = 'REGION' THEN split_part(b.stratum_id, '_b', 1) ELSE 'GLOBAL' END AS src
        FROM base b LEFT JOIN {cal} k ON k.stratum_id = b.stratum_id AND k.witness = b.witness AND k.daynight = b.daynight
             AND k.season = {SEASON_SQL.replace('w.month', 'b.month')}),
    grp AS (
        SELECT entity_type, entity_id, any_value(entity_name) AS entity_name, year, month, witness, daynight, src,
               sum(cd) AS raw, bool_and(complete) AS complete, min(lo) AS lo, max(hi) AS hi,
               sum(r * cd) AS e, sum(r * r * cd) AS vc, power(sum(cd * rsd), 2) AS vr, sum(r) AS sr, count(*) AS nr,
               count(*) FILTER (WHERE r IS NULL) AS missing
        FROM conv GROUP BY entity_type, entity_id, year, month, witness, daynight, src)
    SELECT entity_type, entity_id, any_value(entity_name) AS entity_name, year, month, witness, daynight,
           sum(raw) AS raw, bool_and(complete) AS complete, min(lo) AS lo, max(hi) AS hi,
           sum(e) AS e, sum(vc) AS vc, sum(vr) AS vr, sum(sr) / sum(nr) AS rbar, sum(missing) AS missing
    FROM grp GROUP BY entity_type, entity_id, year, month, witness, daynight
    ORDER BY entity_type, entity_id, year, month, witness, daynight"""
    return con.execute(sql).df()


def _level(lo: str, hi: str) -> str:
    return lo if lo == hi else "MIXED"


def records_from(agg: pd.DataFrame, n_cells: dict[tuple[str, str], int], aqua_cutoff: tuple[int, int] | None = None,
                 phi: dict[str, float] | None = None) -> list[dict]:
    """Contract-shaped records from the aggregated table."""
    phi = phi or PHI
    out: list[dict] = []
    for (etype, eid, year, month), g in agg.groupby(["entity_type", "entity_id", "year", "month"], sort=True):
        raw_by = {w: int(g.loc[g.witness == w, "raw"].sum()) for w in RAW_WITNESSES if (g.witness == w).any()}
        est = np.full((1, len(WITNESSES)), np.nan)
        var = np.full((1, len(WITNESSES)), np.nan)
        use = np.zeros((1, len(WITNESSES)), dtype=bool)
        cutoff_hit = False
        for j, w in enumerate(WITNESSES):
            rows = g[g.witness == w]
            if rows.empty:
                continue
            if rows["missing"].sum():
                raise ValueError(f"{etype} {eid} {year}-{month:02d}: {int(rows['missing'].sum())} stratum rows have no calibration ratio")
            est[0, j] = rows["e"].sum()
            counting = sum(phi[r.daynight] * r.vc for r in rows.itertuples())
            floor = float(rows["rbar"].mean()) ** 2
            var[0, j] = max(counting + float(rows["vr"].sum()), floor)       # a zero count still carries one cell-day of variance
            use[0, j] = bool(rows["complete"].all())
            if w == "AQUA_MODIS" and aqua_cutoff is not None and (year, month) > aqua_cutoff:
                cutoff_hit = cutoff_hit or use[0, j]
                use[0, j] = False
        c = combine(est, var, use)
        n = int(c["n"][0])
        used = [w for j, w in enumerate(WITNESSES) if use[0, j] and np.isfinite(est[0, j])]
        levels = g[g.witness.isin(used)] if used else g
        reasons = []
        if n == 1:
            reasons.append("SINGLE_WITNESS")
        if bool(c["disagree"][0]):
            reasons.append("WITNESS_DISAGREEMENT")
        if cutoff_hit:
            reasons.append("AQUA_DRIFT_ERA")
        level = _level(levels["lo"].min(), levels["hi"].max())
        if level in ("NRT", "MIXED"):
            reasons.append("PROVISIONAL_NRT")
        rec = {"entity_type": etype, "entity_id": eid, "entity_name": g["entity_name"].iloc[0], "year": int(year), "month": int(month),
               "estimate": None, "ci90_low": None, "ci90_high": None, "sd": None,
               "raw_combined_cell_days": int(sum(raw_by.values())), "witnesses_used": used, "n_witnesses": n,
               "disagreement_scale": None if np.isnan(c["scale"][0]) else float(c["scale"][0])}
        if n > 0:
            rec["estimate"], rec["sd"] = float(c["estimate"][0]), float(c["sd"][0])
            rec["ci90_low"], rec["ci90_high"] = interval(rec["estimate"], rec["sd"])
        rec.update({k: None for k in HARMONIZED_NULLS})
        rec.update({"verdict": "CANNOT_DETERMINE", "reason_codes": sorted(reasons), "data_level": level,
                    "method_version": METHOD_VERSION, "n_cells": n_cells[(etype, eid)],
                    "raw_by_witness": json.dumps(raw_by)})
        out.append(rec)
    return out


def harmonize_area(cell_ids: list[str], months: list[tuple[int, int]] | None = None, paths: Paths | None = None,
                   aqua_cutoff: tuple[int, int] | None = None, entity_id: str = "CUSTOM", entity_name: str = "Custom area",
                   phi: dict[str, float] | None = None) -> list[dict]:
    """The single implementation of the science for an area: `entity_month` records (DATA_CONTRACT.md section 4, 8).

    `cell_ids` are analysis cells of cells.parquet; `months` is a list of (year, month) or None for every month with data.
    `aqua_cutoff` (year, month): Aqua is not combined after it (the value comes from T-012; none by default).
    `phi`: overdispersion per day/night (default: the estimate on the fit periods, `PHI`).
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
    return records_from(agg, {("CUSTOM", entity_id): len(ids)}, aqua_cutoff, phi)


# ------------------------------------------------------------------------------------------------ real-data report
def report(paths: Paths | None = None, aqua_cutoff: tuple[int, int] | None = None, phi: dict[str, float] | None = None) -> dict:
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
    out: dict = {"phi": phi or PHI}
    for label, ph in (("poisson_only", {"D": 1.0, "N": 1.0}), ("with_phi", phi or PHI)):
        recs = pd.DataFrame(records_from(agg, n_cells, aqua_cutoff, ph))
        two = recs[recs.n_witnesses >= 2]
        s = two.disagreement_scale.astype(float)
        rel_sd = (recs.sd / recs.estimate).replace([np.inf, -np.inf], np.nan)
        out[label] = {"country_months": len(recs), "with_estimate": int(recs.estimate.notna().sum()),
                      "n_witnesses": {int(k): int(v) for k, v in recs.n_witnesses.value_counts().sort_index().items()},
                      "two_plus_witness_months": len(s),
                      "scale_quantiles": {str(q): float(s.quantile(q)) for q in (0.05, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99)},
                      "share_scale_gt": {str(t): float((s > t).mean()) for t in (1.0, 1.5, 2.0, 3.0, 5.0)},
                      "relative_sd_median": float(rel_sd.median()),
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
    if sys.argv[1:] == ["phi"]:
        res = estimate_phi()
        (Paths().products.parent / "interim" / "qa" / "harmonize_phi.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
        print(json.dumps(res, indent=1))
    else:
        print(json.dumps(report(), indent=1))
