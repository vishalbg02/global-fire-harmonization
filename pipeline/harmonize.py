"""Witness combination with disagreement inflation, and `harmonize_area()` (T-013).

For any area (a list of analysis cells) and month, each witness gives an Aqua-equivalent estimate

    E_w = sum over strata s and day/night d of  ratio(s, w, d, season) x cell_days(s, w, d)

(Aqua has ratio 1 and no ratio uncertainty; Terra is raw view only and never enters the estimate). The variance is, per
stratum and day/night,

    ratio^2 x var(cell_days) + cell_days^2 x ratio_sd^2,     var(cell_days) = cell_days   (Poisson approximation)

and the raw cell-days are summed per witness and stratum BEFORE they are converted, so the ratio error is shared inside a
stratum (docs/SCIENTIFIC_METHODOLOGY.md 4.5). Strata are treated as independent of each other.

The witnesses of a month are combined with a precision-weighted mean. If they disagree more than their variances allow, the
combined sd is multiplied by S = sqrt(chi^2 / (N - 1)) (only when S > 1; the Birge ratio, the usual rule for discordant
measurements). Baseline, probabilities and verdicts belong to T-014: here the baseline fields are null and the verdict is
CANNOT_DETERMINE, as the contract requires without a baseline.

    from harmonize import harmonize_area
    records = harmonize_area(cell_ids, months=None)       # list of dicts in the shape of DATA_CONTRACT.md section 4

PROPOSALS for the Lead (see docs/DATA_SOURCES.md): day and night converted separately and added; a variance floor of one
cell-day for a zero count; only complete witness-months count; strata independent; a 90% normal interval.
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
    return {"estimate": mean, "sd": sd, "n": n, "chi2": chi2, "scale": scale, "inflated": (n >= 2) & (s > 1.0)}


def interval(estimate: float, sd: float) -> tuple[float, float]:
    """90% normal interval, with the lower bound at 0."""
    return max(0.0, estimate - Z90 * sd), estimate + Z90 * sd


# ------------------------------------------------------------------------------------------------ data access
def aggregate(con, paths: Paths, members: str, months: list[tuple[int, int]] | None) -> pd.DataFrame:
    """One row per entity x month x witness: converted estimate, its variance, raw cell-days and data levels.

    `members` is a table (entity_type, entity_id, entity_name, cell_id). Raw cell-days are summed per stratum first.
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
               CASE WHEN b.witness = 'AQUA_MODIS' THEN 0.0 ELSE k.ratio_sd END AS rsd
        FROM base b LEFT JOIN {cal} k ON k.stratum_id = b.stratum_id AND k.witness = b.witness AND k.daynight = b.daynight
             AND k.season = {SEASON_SQL.replace('w.month', 'b.month')})
    SELECT entity_type, entity_id, any_value(entity_name) AS entity_name, year, month, witness,
           sum(cd) AS raw, bool_and(complete) AS complete, min(lo) AS lo, max(hi) AS hi,
           sum(r * cd) AS e, sum(r * r * cd + cd * cd * rsd * rsd) AS v0, avg(r) AS rbar, count(*) FILTER (WHERE r IS NULL) AS missing
    FROM conv GROUP BY entity_type, entity_id, year, month, witness ORDER BY entity_type, entity_id, year, month, witness"""
    return con.execute(sql).df()


def _level(lo: str, hi: str) -> str:
    return lo if lo == hi else "MIXED"


def records_from(agg: pd.DataFrame, n_cells: dict[tuple[str, str], int], aqua_cutoff: tuple[int, int] | None = None) -> list[dict]:
    """Contract-shaped records from the aggregated table."""
    out: list[dict] = []
    for (etype, eid, year, month), g in agg.groupby(["entity_type", "entity_id", "year", "month"], sort=True):
        by = g.set_index("witness")
        raw_by = {w: int(by.loc[w, "raw"]) for w in RAW_WITNESSES if w in by.index}
        miss = by.loc[[w for w in WITNESSES if w in by.index], "missing"].sum()
        if miss:
            raise ValueError(f"{etype} {eid} {year}-{month:02d}: {int(miss)} stratum rows have no calibration ratio")
        est = np.full((1, len(WITNESSES)), np.nan)
        var = np.full((1, len(WITNESSES)), np.nan)
        use = np.zeros((1, len(WITNESSES)), dtype=bool)
        cutoff_hit = False
        for j, w in enumerate(WITNESSES):
            if w not in by.index:
                continue
            row = by.loc[w]
            est[0, j] = row["e"]
            var[0, j] = max(float(row["v0"]), float(row["rbar"]) ** 2)       # a zero count still carries one cell-day of variance
            use[0, j] = bool(row["complete"])
            if w == "AQUA_MODIS" and aqua_cutoff is not None and (year, month) > aqua_cutoff:
                cutoff_hit = cutoff_hit or use[0, j]
                use[0, j] = False
        c = combine(est, var, use)
        n = int(c["n"][0])
        used = [w for j, w in enumerate(WITNESSES) if use[0, j] and np.isfinite(est[0, j])]
        levels = by.loc[used if used else list(by.index)]
        reasons = []
        if n == 1:
            reasons.append("SINGLE_WITNESS")
        if bool(c["inflated"][0]):
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
                   aqua_cutoff: tuple[int, int] | None = None, entity_id: str = "CUSTOM", entity_name: str = "Custom area") -> list[dict]:
    """The single implementation of the science for an area: `entity_month` records (DATA_CONTRACT.md section 4, 8).

    `cell_ids` are analysis cells of cells.parquet; `months` is a list of (year, month) or None for every month with data.
    `aqua_cutoff` (year, month): Aqua is not combined after it (the value comes from T-012; none by default).
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
    return records_from(agg, {("CUSTOM", entity_id): len(ids)}, aqua_cutoff)


# ------------------------------------------------------------------------------------------------ real-data report
def report(paths: Paths | None = None, aqua_cutoff: tuple[int, int] | None = None) -> dict:
    """Run the combination over every country and over two named areas; summarise how the witnesses agree.

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
    recs = pd.DataFrame(records_from(agg, {("COUNTRY", k): v for k, v in counts.items()}, aqua_cutoff))
    two = recs[recs.n_witnesses >= 2]
    s = two.disagreement_scale.astype(float)
    # per witness: converted estimate against the Aqua estimate of the same country-month, where both are well above zero
    wide = agg.pivot_table(index=["entity_id", "year", "month"], columns="witness", values="e")
    rel = {}
    for w in ("SNPP_VIIRS", "NOAA20_VIIRS"):
        both = wide[["AQUA_MODIS", w]].dropna()
        both = both[(both.AQUA_MODIS >= 100) & (both[w] >= 100)]
        lr = np.log(both[w] / both.AQUA_MODIS)
        rel[w] = {"country_months": len(lr), "median_ratio": float(np.exp(lr.median())),
                  "p05_ratio": float(np.exp(lr.quantile(0.05))), "p95_ratio": float(np.exp(lr.quantile(0.95)))}
    out = {"country_months": len(recs), "with_estimate": int(recs.estimate.notna().sum()),
           "n_witnesses": {int(k): int(v) for k, v in recs.n_witnesses.value_counts().sort_index().items()},
           "scale_quantiles": {str(q): float(s.quantile(q)) for q in (0.05, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99)},
           "share_scale_gt": {str(t): float((s > t).mean()) for t in (1.0, 1.5, 2.0, 3.0, 5.0)}, "two_plus_witness_months": len(s),
           "converted_over_aqua": rel, "no_estimate_months": sorted({f"{r.year}-{r.month:02d}" for r in recs[recs.estimate.isna()].itertuples()})}
    (paths.products.parent / "interim" / "qa" / "harmonize_report.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    print(json.dumps(report(), indent=1))
