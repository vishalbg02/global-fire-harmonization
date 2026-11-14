"""Validation tests B2 (planted sensor jump), C1 (cross-satellite agreement) and CTRL (control box C8) (T-024).

Criteria and thresholds come only from docs/VALIDATION_PLAN.md section 3 and D-028 (locked at G1, 2026-11-14). Everything the plan
leaves open is fixed in docs/task-prompts/T-024-test-b2-c1-ctrl.md section 15 BEFORE any real run; the constants below are those
choices. Nothing is tuned on a result.

B2. A jump (factor 1.5 to 3, up or down, log-uniform) is planted in ONE witness of a random entity (a fire region or a single cell)
from a random month on, in the in-memory aggregated table only (the products on disk are never touched). PASS when the jump is
flagged (`WITNESS_DISAGREEMENT`, or a disagreement scale of at least 1.5, i.e. an interval widened by at least 50%) in the jump
month or the two after it in at least 90% of 200 trials, AND at most (strictly under) 5% of the unplanted twins (same entity, same
three months, no jump) are flagged by the same rule.

C1. Converted S-NPP against converted NOAA-20, fire-region-months 2018-2021, both estimates at least 5 Aqua-equivalent cell-days:
agreement means |difference| <= 1.645 x sqrt(sd_S^2 + sd_N^2); PASS at 85% or more. 2018-2021 is in sample for NOAA-20 (its calibration
is 2018-04 to 2021-12) and out of sample for S-NPP (fit 2012-2016); a supplementary entry repeats it for 2022-01 to 2024-04, out of
sample for both.

CTRL. Box C8, the 25 months around 2012-01 and 2018-04: no harmonized ABOVE/BELOW verdict that the Aqua-only series does not have.

    python pipeline/validation_b2_c1_ctrl.py all            # needs the heavy-job lock; caches in data/interim/T-024
    python pipeline/validation_b2_c1_ctrl.py b2 | c1 | ctrl
    python pipeline/validation_b2_c1_ctrl.py all --fresh     # recompute the cached aggregations
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harmonize as hz
import validation_a1 as a1
import validation_e1_s1 as e1

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "data" / "interim" / "qa"
WORK = ROOT / "data" / "interim" / "T-024"
CONTRACT_VERSION = "0.1.1"
SEED = 20261115                      # the calibration seed 20261114 plus one
Z90 = hz.Z90
UNASSIGNED = "UNASSIGNED"
STATUSES = ("PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN")

# ------------------------------------------------------------------------------------------------ B2: locked and chosen
B2_DETECTION_MIN = 0.90              # locked (plan): flagged within 3 months in at least 90% of trials
B2_FALSE_MAX = 0.05                  # locked (plan): false flags in under 5% of unplanted series
B2_MIN_TRIALS = 50                   # locked (plan): at least 50 trials
B2_TRIALS = {"REGION": 100, "CELL": 100}     # [ASSUMPTION 1]
B2_FACTOR = (1.5, 3.0)               # [ASSUMPTION 1] |ln f| uniform on [ln 1.5, ln 3], up or down
B2_WIDEN_SCALE = 1.5                 # [ASSUMPTION 2] a widened interval: disagreement_scale >= 1.5
B2_MIN_ESTIMATE = 5.0                # [ASSUMPTION 4] Aqua-equivalent cell-days (D-028 step 4)
B2_LAG = 3                           # the jump month and the two after it
B2_FIRST, B2_LAST = (2012, 1), (2021, 12)    # aggregated period; jumps start 2012-01 to 2021-10
B2_POOL = 2000                       # single cells drawn for the cell trials
DISAGREEMENT_CODE = "WITNESS_DISAGREEMENT"

# ------------------------------------------------------------------------------------------------ C1
C1_THRESHOLD = 0.85                  # locked (plan)
C1_MIN_ESTIMATE = 5.0                # [ASSUMPTION 6]
C1_MIN_UNITS = 100                   # [ASSUMPTION 6] fewer units: INCONCLUSIVE
C1_WINDOW = ((2018, 1), (2021, 12))  # locked (plan: 2018-2021)
C1_OOS_WINDOW = ((2022, 1), (2024, 4))   # [ASSUMPTION 7] out of sample for both fits, before the VIIRS night drift onsets
C1_FIRST, C1_LAST = (2018, 1), (2024, 4)

# ------------------------------------------------------------------------------------------------ CTRL
C8_BOX = (20.0, -20.0, 35.0, -8.0)   # W, S, E, N (VALIDATION_PLAN 2a)
CTRL_DATES = ((2012, 1), (2018, 4))
CTRL_HALF_WINDOW = 12                # months either side
CTRL_ANALYSIS_WINDOWS = (((2011, 1), (2013, 12)), ((2017, 4), (2019, 4)))
CTRL_MIN_DETERMINABLE = 12           # [ASSUMPTION 9]
CTRL_FIRST, CTRL_LAST = (2003, 1), (2022, 12)
BASE_YEARS = (2003, 2022)
DIRECTIONAL = ("ABOVE_NORMAL", "BELOW_NORMAL")
NORMAL = ("ABOVE_NORMAL", "BELOW_NORMAL", "WITHIN_NORMAL")


# ============================================================================================================ small helpers
def midx(year: int, month: int) -> int:
    return int(year) * 12 + int(month) - 1


def label(i: int) -> str:
    return f"{i // 12}-{i % 12 + 1:02d}"


def months_between(first: tuple[int, int], last: tuple[int, int]) -> list[tuple[int, int]]:
    return a1.month_range(first, last)


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    """Wilson 95% interval of a share k/n."""
    if n <= 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def share(k: int, n: int) -> dict:
    lo, hi = wilson(k, n)
    return {"k": int(k), "n": int(n), "share": (k / n) if n else None, "wilson95": [lo, hi]}


# ============================================================================================================ data access
def connect(tmp: Path) -> duckdb.DuckDBPyConnection:
    """A DuckDB connection with the settings of the heavy-job protocol (5 GB, 20 GiB of temp space, 4 threads, a private temp dir)."""
    tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{tmp.as_posix()}'")
    con.execute("SET memory_limit='5GB'")
    con.execute("SET max_temp_directory_size='20GiB'")
    con.execute("SET preserve_insertion_order=false")
    con.execute("SET threads=4")
    return con


def aggregate_entities(members: pd.DataFrame, months: list[tuple[int, int]], paths: hz.Paths, tmp: Path, chunk: int | None = None) -> pd.DataFrame:
    """`harmonize.aggregate` for a members table (entity_type, entity_id, entity_name, cell_id). The (small) members are joined to the
    cells first inside `aggregate`; `chunk` runs the entities in groups of that many to bound memory."""
    ids = list(dict.fromkeys(members.entity_id))
    groups = [ids] if not chunk else [ids[i:i + chunk] for i in range(0, len(ids), chunk)]
    out = []
    for g in groups:
        con = connect(tmp)
        con.register("members_df", members[members.entity_id.isin(g)])
        con.execute("CREATE TEMP TABLE members AS SELECT * FROM members_df")
        out.append(hz.aggregate(con, paths, "members", months))
        con.close()
    return pd.concat(out, ignore_index=True)


def cached(path: Path, build, fresh: bool) -> pd.DataFrame:
    """The parquet cache of a stage: read it when it exists (and `fresh` is false), otherwise build it and write it."""
    if path.exists() and not fresh:
        return pd.read_parquet(path)
    df = build()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return df


def regions_members(cells: pd.DataFrame) -> pd.DataFrame:
    sel = cells[cells.fire_region.notna() & (cells.fire_region != UNASSIGNED)]
    return pd.DataFrame({"entity_type": "REGION", "entity_id": sel.fire_region.to_numpy(), "entity_name": sel.fire_region.to_numpy(),
                         "cell_id": sel.cell_id.to_numpy()})


def draw_cell_pool(cells: pd.DataFrame, n: int = B2_POOL, seed: int = SEED) -> list[str]:
    """`n` cells drawn uniformly without replacement from the cells of a real fire region (sorted ids, seeded)."""
    ids = sorted(cells.loc[cells.fire_region.notna() & (cells.fire_region != UNASSIGNED), "cell_id"])
    rng = np.random.default_rng(seed)
    pick = rng.choice(len(ids), size=min(n, len(ids)), replace=False)
    return sorted(ids[i] for i in pick)


def cells_members(pool: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"entity_type": "CELL", "entity_id": pool, "entity_name": pool, "cell_id": pool})


def only_witnesses(agg: pd.DataFrame) -> pd.DataFrame:
    """The rows of the witnesses that enter the estimate (Terra, the raw-view witness, is dropped)."""
    return agg[agg.witness.isin(hz.WITNESSES)].reset_index(drop=True)


def frame(records: list[dict]) -> pd.DataFrame:
    """Records as a frame with numeric estimate/sd, a used-witness set and a month index."""
    df = a1.records_frame(records)
    if df.empty:
        return df
    df["idx"] = df.year.astype(int) * 12 + df.month.astype(int) - 1
    df["used"] = df.witnesses_used.map(frozenset)
    df["codes"] = df.reason_codes.map(frozenset)
    return df


# ============================================================================================================ B2
def plant_jump(agg: pd.DataFrame, entity_id: str, witness: str, start: int, factor: float) -> pd.DataFrame:
    """A COPY of the aggregated table in which the rows of `entity_id` and `witness` from month index `start` on are scaled by a sensor
    jump: raw cell-days and the converted estimate x factor, the counting variance x factor (it follows the count), the ratio variance
    x factor^2. The input table is not changed."""
    out = agg.copy()
    sel = (out.entity_id == entity_id) & (out.witness == witness) & ((out.year * 12 + out.month - 1) >= start)
    out.loc[sel, "raw"] = out.loc[sel, "raw"] * factor
    out.loc[sel, "e"] = out.loc[sel, "e"] * factor
    out.loc[sel, "vc"] = out.loc[sel, "vc"] * factor
    out.loc[sel, "vr"] = out.loc[sel, "vr"] * factor ** 2
    return out


def flagged(rec: pd.Series | dict, widen: float = B2_WIDEN_SCALE, code_only: bool = False) -> bool:
    """The B2 flag of one record: `WITNESS_DISAGREEMENT` among its codes, or (unless `code_only`) a disagreement scale of at least `widen`."""
    codes = rec["codes"] if "codes" in rec else frozenset(rec["reason_codes"])
    if DISAGREEMENT_CODE in codes:
        return True
    if code_only:
        return False
    s = rec["disagreement_scale"]
    return bool(s is not None and np.isfinite(s) and s >= widen)


def keep_possible(agg: pd.DataFrame, min_estimate: float = B2_MIN_ESTIMATE) -> pd.DataFrame:
    """Only the entity-months whose upper bound (sum over day/night of the largest witness estimate) reaches `min_estimate`. A combined
    estimate is a weighted mean per day/night part, so it never exceeds this bound: no month that could be eligible is lost."""
    a = only_witnesses(agg)
    mx = a.groupby(["entity_type", "entity_id", "year", "month", "daynight"], as_index=False).e.max()
    bound = mx.groupby(["entity_type", "entity_id", "year", "month"], as_index=False).e.sum().rename(columns={"e": "bound"})
    ok = bound[bound.bound >= min_estimate][["entity_type", "entity_id", "year", "month"]]
    return a.merge(ok, on=["entity_type", "entity_id", "year", "month"])


def eligible_pairs(rec: pd.DataFrame, first: int, last: int, min_estimate: float = B2_MIN_ESTIMATE, lag: int = B2_LAG) -> dict[str, list[tuple[int, str]]]:
    """For each entity, the eligible (start month index d, witness w): in each of the months d .. d+lag-1 there is an estimate of at least
    `min_estimate`, w is used and at least one other witness is used. d runs from `first` to `last - lag + 1`."""
    out: dict[str, list[tuple[int, str]]] = {}
    for eid, g in rec.groupby("entity_id", sort=True):
        ok = {int(r.idx): r.used for r in g.itertuples() if r.estimate is not None and np.isfinite(r.estimate) and r.estimate >= min_estimate and len(r.used) >= 2}
        pairs = []
        for d in range(first, last - lag + 2):
            sets = [ok.get(d + k) for k in range(lag)]
            if any(s is None for s in sets):
                continue
            for w in hz.WITNESSES:
                if all(w in s for s in sets):
                    pairs.append((d, w))
        if pairs:
            out[str(eid)] = pairs
    return out


def draw_trials(pairs_by_type: dict[str, dict[str, list[tuple[int, str]]]], n_by_type: dict[str, int] = B2_TRIALS,
                factor: tuple[float, float] = B2_FACTOR, seed: int = SEED) -> list[dict]:
    """Seeded trials: per entity type, an entity uniformly among those with an eligible pair, a pair uniformly among that entity's pairs,
    then |ln f| uniform on [ln lo, ln hi] with a random direction. Same inputs and seed give the same trials."""
    rng = np.random.default_rng(seed)
    trials = []
    for etype in sorted(pairs_by_type):
        pairs = pairs_by_type[etype]
        ents = sorted(pairs)
        if not ents:
            continue
        for i in range(n_by_type.get(etype, 0)):
            eid = ents[int(rng.integers(len(ents)))]
            d, w = pairs[eid][int(rng.integers(len(pairs[eid])))]
            lnf = float(rng.uniform(math.log(factor[0]), math.log(factor[1])))
            sign = 1.0 if rng.integers(2) == 0 else -1.0
            trials.append({"trial": len(trials), "entity_type": etype, "entity_id": eid, "witness": w, "start_idx": d,
                           "start": label(d), "factor": math.exp(sign * lnf), "abs_ln_f": lnf})
    return trials


def run_trial(trial: dict, agg: pd.DataFrame, rec: pd.DataFrame, n_cells: dict, lag: int = B2_LAG) -> dict:
    """Plant the jump in the entity's rows (in memory), recompute the records of the jump month and the lag-1 months after it, and flag
    them; the unplanted twin is read from `rec` (the unperturbed records of the same months)."""
    d = trial["start_idx"]
    sub = agg[(agg.entity_id == trial["entity_id"]) & (agg.entity_type == trial["entity_type"])]
    window = sub[(sub.year * 12 + sub.month - 1).between(d, d + lag - 1)]
    planted = plant_jump(window, trial["entity_id"], trial["witness"], d, trial["factor"])
    key = (trial["entity_type"], trial["entity_id"])
    recs = frame(hz.records_from(planted, {key: n_cells[key]}))
    twin = rec[(rec.entity_id == trial["entity_id"]) & rec.idx.between(d, d + lag - 1)]
    fl = [flagged(r) for _, r in recs.iterrows()]
    fc = [flagged(r, code_only=True) for _, r in recs.iterrows()]
    tf = [flagged(r) for _, r in twin.iterrows()]
    tc = [flagged(r, code_only=True) for _, r in twin.iterrows()]
    first = next((int(r.idx) - d for (_, r), f in zip(recs.iterrows(), fl, strict=True) if f), None)
    scales = [float(s) for s in recs.disagreement_scale if s is not None and np.isfinite(s)]
    return {**trial, "months_checked": len(recs), "detected": any(fl), "detected_code": any(fc), "first_flag_month": first,
            "twin_flagged": any(tf), "twin_flagged_code": any(tc), "max_scale_planted": max(scales) if scales else None}


def b2_status(detection: float | None, false_rate: float | None, trials: int) -> str:
    """PASS: detection >= 90% and false flags < 5%. FAIL: either violated. INCONCLUSIVE: fewer than the 50 trials of the plan."""
    if trials < B2_MIN_TRIALS or detection is None or false_rate is None:
        return "INCONCLUSIVE"
    return "PASS" if detection >= B2_DETECTION_MIN and false_rate < B2_FALSE_MAX else "FAIL"


def summarise_trials(rows: list[dict]) -> dict:
    """Rates of a set of trial results (detection, detection by the code alone, false flags of the twins)."""
    n = len(rows)
    det = sum(r["detected"] for r in rows)
    detc = sum(r["detected_code"] for r in rows)
    fl = sum(r["twin_flagged"] for r in rows)
    flc = sum(r["twin_flagged_code"] for r in rows)
    net = sum(r["detected"] and not r["twin_flagged"] for r in rows)
    return {"trials": n, "detected": share(det, n), "detected_by_code": share(detc, n), "false_flags_twin": share(fl, n),
            "false_flags_twin_by_code": share(flc, n), "detected_and_twin_not_flagged": share(net, n)}


def breakdowns(rows: list[dict]) -> dict:
    """Detection by entity type, witness, size of the jump (terciles of |ln f|) and direction: information only, no status."""
    df = pd.DataFrame(rows)
    if df.empty:
        return {}
    out: dict = {}
    for col in ("entity_type", "witness"):
        out[col] = {str(k): share(int(g.detected.sum()), len(g)) for k, g in df.groupby(col)}
    q = df.abs_ln_f.quantile([1 / 3, 2 / 3]).to_numpy()
    tercile = np.digitize(df.abs_ln_f, q)
    out["jump_size_tercile"] = {f"T{int(k) + 1}": {"factor_range": [float(math.exp(g.abs_ln_f.min())), float(math.exp(g.abs_ln_f.max()))],
                                                  **share(int(g.detected.sum()), len(g))} for k, g in df.groupby(tercile)}
    out["direction"] = {("up" if up else "down"): share(int(g.detected.sum()), len(g)) for up, g in df.groupby(df.factor > 1)}
    out["year"] = {str(int(k)): share(int(g.detected.sum()), len(g)) for k, g in df.groupby(df.start_idx // 12)}
    return out


def monthly_false_flags(rec: pd.DataFrame, min_estimate: float = B2_MIN_ESTIMATE) -> dict:
    """The unplanted rate per entity-month and per entity: among the entity-months with an estimate of at least `min_estimate` and at
    least two witnesses, the share flagged (union rule and code alone), and the share of entities flagged in any such month."""
    ok = rec[rec.estimate.notna() & (rec.estimate >= min_estimate) & (rec.used.map(len) >= 2)]
    if ok.empty:
        return {"entity_months": 0}
    f = np.array([flagged(r) for _, r in ok.iterrows()])
    c = np.array([flagged(r, code_only=True) for _, r in ok.iterrows()])
    per_entity = ok.assign(f=f, c=c).groupby("entity_id")[["f", "c"]].any()
    out = {"entity_months": len(ok), "entities": len(per_entity), "flagged_union": share(int(f.sum()), len(ok)),
           "flagged_code": share(int(c.sum()), len(ok)),
           "entities_flagged_anywhere_union": share(int(per_entity.f.sum()), len(per_entity)),
           "entities_flagged_anywhere_code": share(int(per_entity.c.sum()), len(per_entity))}
    for et, g in ok.assign(f=f, c=c).groupby("entity_type"):
        out[f"by_type_{et}"] = {"entity_months": len(g), "flagged_union": share(int(g.f.sum()), len(g)), "flagged_code": share(int(g.c.sum()), len(g))}
    return out


def run_b2(agg_regions: pd.DataFrame, agg_cells: pd.DataFrame, n_cells: dict, seed: int = SEED, n_by_type: dict[str, int] = B2_TRIALS) -> dict:
    """The whole of B2 from the aggregated tables of the regions and of the cell pool (both 2012-01 to 2021-12)."""
    first, last = midx(*B2_FIRST), midx(*B2_LAST)
    lo = lambda a: a[(a.year * 12 + a.month - 1).between(first, last)]
    parts = [lo(only_witnesses(agg_regions)), lo(only_witnesses(agg_cells))]
    agg = pd.concat(parts, ignore_index=True)
    rec = frame(hz.records_from(keep_possible(agg), n_cells))
    pairs = {t: eligible_pairs(rec[rec.entity_type == t], first, last) for t in ("REGION", "CELL")}
    trials = draw_trials(pairs, n_by_type, B2_FACTOR, seed)
    rows = [run_trial(t, agg, rec, n_cells) for t in trials]
    summ = summarise_trials(rows)
    det, fp = summ["detected"]["share"], summ["false_flags_twin"]["share"]
    code_status = b2_status(summ["detected_by_code"]["share"], summ["false_flags_twin_by_code"]["share"], len(rows))
    monthly = monthly_false_flags(rec)
    return {"seed": seed, "trials": rows, "summary": summ, "status": b2_status(det, fp, len(rows)), "status_code_only": code_status,
            "by_type": {t: summarise_trials([r for r in rows if r["entity_type"] == t]) for t in ("REGION", "CELL")},
            "breakdowns": breakdowns(rows), "monthly": monthly,
            "eligible_entities": {t: len(p) for t, p in pairs.items()}, "eligible_pairs": {t: int(sum(len(v) for v in p.values())) for t, p in pairs.items()},
            "entities_aggregated": {"REGION": int(agg_regions.entity_id.nunique()), "CELL": int(agg_cells.entity_id.nunique())},
            "rates": {"detection": det, "false_flag_twin": fp}}


# ============================================================================================================ C1
def c1_units(snpp: pd.DataFrame, noaa: pd.DataFrame, window: tuple[tuple[int, int], tuple[int, int]] = C1_WINDOW,
             min_estimate: float = C1_MIN_ESTIMATE) -> pd.DataFrame:
    """One row per fire-region-month with an estimate from both single-witness paths (both at least `min_estimate`), with the agreement
    on the interval of the difference (`agree`) and on overlapping 90% intervals (`overlap`)."""
    lo, hi = midx(*window[0]), midx(*window[1])
    cols = ["entity_id", "year", "month", "estimate", "sd", "ci90_low", "ci90_high"]
    m = snpp[cols].merge(noaa[cols], on=["entity_id", "year", "month"], suffixes=("_s", "_n"))
    m = m[m.estimate_s.notna() & m.estimate_n.notna() & (m.estimate_s >= min_estimate) & (m.estimate_n >= min_estimate)]
    m = m[(m.year * 12 + m.month - 1).between(lo, hi)].copy()
    m["diff"] = m.estimate_s - m.estimate_n
    m["combined_sd"] = np.sqrt(m.sd_s ** 2 + m.sd_n ** 2)
    m["agree"] = m["diff"].abs() <= Z90 * m.combined_sd
    m["overlap"] = (m.ci90_low_s <= m.ci90_high_n) & (m.ci90_low_n <= m.ci90_high_s)
    return m.reset_index(drop=True)


def c1_status(share_agree: float | None, units: int, threshold: float = C1_THRESHOLD, min_units: int = C1_MIN_UNITS) -> str:
    """PASS at or above the threshold, FAIL below, INCONCLUSIVE with fewer than `min_units` units."""
    if units < min_units or share_agree is None:
        return "INCONCLUSIVE"
    return "PASS" if share_agree >= threshold - 1e-12 else "FAIL"


def c1_summary(units: pd.DataFrame) -> dict:
    n = len(units)
    out = {"units": n, "agree": share(int(units.agree.sum()), n), "overlap": share(int(units.overlap.sum()), n),
           "status": c1_status(float(units.agree.mean()) if n else None, n),
           "status_overlap": c1_status(float(units.overlap.mean()) if n else None, n), "per_region": {}}
    if n:
        out["median_ratio_snpp_over_noaa20"] = float(np.exp(np.log(units.estimate_s / units.estimate_n).median()))
        out["median_abs_log_ratio"] = float(np.abs(np.log(units.estimate_s / units.estimate_n)).median())
        out["median_z"] = float((units["diff"].abs() / units.combined_sd).median())
    for r, g in units.groupby("entity_id"):
        out["per_region"][str(r)] = {"units": len(g), "agree": float(g.agree.mean()), "overlap": float(g.overlap.mean()),
                                     "median_ratio_snpp_over_noaa20": float(np.exp(np.log(g.estimate_s / g.estimate_n).median()))}
    return out


def run_c1(agg_regions: pd.DataFrame, n_cells: dict) -> dict:
    """C1 from the aggregated table of the 14 fire regions (2018-01 to 2024-04)."""
    lo, hi = midx(*C1_FIRST), midx(*C1_LAST)
    agg = only_witnesses(agg_regions)
    agg = agg[(agg.year * 12 + agg.month - 1).between(lo, hi)]
    paths = {w: a1.records_frame(hz.records_from(a1.restrict_witness(agg, w), n_cells)) for w in ("SNPP_VIIRS", "NOAA20_VIIRS")}
    official = c1_units(paths["SNPP_VIIRS"], paths["NOAA20_VIIRS"], C1_WINDOW)
    oos = c1_units(paths["SNPP_VIIRS"], paths["NOAA20_VIIRS"], C1_OOS_WINDOW)
    sens = {f"min_estimate_{m}": c1_summary(c1_units(paths["SNPP_VIIRS"], paths["NOAA20_VIIRS"], C1_WINDOW, m))["agree"]
            for m in (0.0, 20.0)}
    first_noaa = paths["NOAA20_VIIRS"][paths["NOAA20_VIIRS"].estimate.notna()]
    return {"official": c1_summary(official), "out_of_sample_both": c1_summary(oos), "sensitivity_min_estimate": sens,
            "first_noaa20_estimate_month": label(int((first_noaa.year * 12 + first_noaa.month - 1).min())) if len(first_noaa) else None,
            "in_sample": {"SNPP_VIIRS": "2012-01 to 2016-12 fit: 2018-2021 and 2022-2024 are out of sample",
                          "NOAA20_VIIRS": "2018-04 to 2021-12 fit: the plan window is IN sample, 2022-01 on is out of sample"}}


# ============================================================================================================ CTRL
def judge(records: pd.DataFrame, base: pd.DataFrame, raw: dict[tuple[int, int], float]) -> pd.DataFrame:
    """D-028 verdicts of a record series against a baseline table (`e1.baselines` output); `raw` gives the raw combined cell-days of a
    month (all witnesses) for the step-3 refinement of amendment A. One row per month of `records`."""
    bmap = {(int(r.month)): r for r in base.itertuples()}
    rows = []
    for r in records.itertuples():
        b = bmap.get(int(r.month))
        est = None if pd.isna(r.estimate) else float(r.estimate)
        sd = None if pd.isna(r.sd) else float(r.sd)
        v, code = e1.verdict_for(est, sd, 0 if b is None else int(b.n_years), np.nan if b is None else b.p25, np.nan if b is None else b.p50,
                                 np.nan if b is None else b.p75, raw.get((int(r.year), int(r.month)), 0.0))
        rows.append({"year": int(r.year), "month": int(r.month), "estimate": est, "sd": sd, "verdict": v, "reason": code,
                     "p50": None if b is None else float(b.p50)})
    return pd.DataFrame(rows)


def explain_months(harm: pd.DataFrame, aqua: pd.DataFrame, base_h: pd.DataFrame, base_a: pd.DataFrame, months: list[dict]) -> list[dict]:
    """Diagnostic only (no status): for each listed {'month': 'YYYY-MM'} the estimates and sds of both series, the baseline percentiles used
    for each, and the D-028 probabilities p_above / p_below of each series, so that a verdict that differs can be traced to the number that
    crossed the 0.8 line. The harmonized series is read against `base_h`, the Aqua-only series against `base_a`."""
    out = []
    for m in months:
        y, mo = int(m["month"][:4]), int(m["month"][5:])
        row = {"month": m["month"], "date": m.get("date")}
        for name, rec, base in (("harmonized", harm, base_h), ("aqua_only", aqua, base_a)):
            r = rec[(rec.year == y) & (rec.month == mo)]
            b = base[base.month == mo]
            if r.empty or b.empty or pd.isna(r.estimate.iloc[0]):
                row[name] = None
                continue
            est, sd, bb = float(r.estimate.iloc[0]), float(r.sd.iloc[0]), b.iloc[0]
            above, below, within = e1.probabilities(est, sd, float(bb.p25), float(bb.p75))
            row[name] = {"estimate": est, "sd": sd, "p25": float(bb.p25), "p50": float(bb.p50), "p75": float(bb.p75), "p_above": above, "p_below": below, "p_within": within}
        out.append(row)
    return out


def eval_months(dates=CTRL_DATES, half: int = CTRL_HALF_WINDOW) -> dict[str, list[int]]:
    """The month indices from `half` before to `half` after each change date, keyed by the date."""
    return {label(midx(*d)): list(range(midx(*d) - half, midx(*d) + half + 1)) for d in dates}


def ctrl_compare(v_h: pd.DataFrame, v_a: pd.DataFrame, months: dict[str, list[int]]) -> dict:
    """Spurious = a harmonized ABOVE/BELOW verdict that the Aqua-only series does not give in the same month. Returns counts per date,
    the spurious months and the whole list of verdicts in the evaluated months."""
    h = v_h.assign(idx=v_h.year * 12 + v_h.month - 1).set_index("idx")
    a = v_a.assign(idx=v_a.year * 12 + v_a.month - 1).set_index("idx")
    per, spurious, rows = {}, [], []
    for date, idxs in months.items():
        counts = {k: 0 for k in ("ABOVE_NORMAL", "BELOW_NORMAL", "WITHIN_NORMAL", "NO_DETECTED_ACTIVITY", "CANNOT_DETERMINE", "missing")}
        counts_a = dict.fromkeys(counts, 0)
        n_spur = 0
        for i in idxs:
            vh = h.verdict.get(i, "missing")
            va = a.verdict.get(i, "missing")
            counts[vh] += 1
            counts_a[va] += 1
            bad = vh in DIRECTIONAL and va != vh
            n_spur += int(bad)
            rows.append({"date": date, "month": label(i), "harmonized": vh, "aqua_only": va, "spurious": bool(bad),
                         "estimate_harmonized": None if i not in h.index else h.estimate.get(i), "estimate_aqua_only": None if i not in a.index else a.estimate.get(i)})
            if bad:
                spurious.append({"date": date, "month": label(i), "harmonized": vh, "aqua_only": va})
        per[date] = {"months": len(idxs), "spurious": n_spur, "harmonized_verdicts": counts, "aqua_only_verdicts": counts_a,
                     "determinable_harmonized": int(sum(counts[k] for k in NORMAL))}
    return {"per_date": per, "spurious": spurious, "spurious_total": len(spurious),
            "determinable_harmonized": int(sum(p["determinable_harmonized"] for p in per.values())), "rows": rows}


def ctrl_status(spurious: int, determinable: int, min_determinable: int = CTRL_MIN_DETERMINABLE) -> str:
    """FAIL with any spurious verdict; INCONCLUSIVE when fewer than `min_determinable` months had a determinable harmonized verdict;
    else PASS."""
    if spurious > 0:
        return "FAIL"
    return "PASS" if determinable >= min_determinable else "INCONCLUSIVE"


def run_ctrl(agg_box: pd.DataFrame, n_cells: dict) -> dict:
    """CTRL from the aggregated table of the C8 cells (2003-01 to 2022-12, every witness incl. Terra for the raw cell-days)."""
    key = next(iter(n_cells))
    harm = a1.records_frame(hz.records_from(agg_box, n_cells))
    aqua = a1.records_frame(hz.records_from(agg_box[agg_box.witness == "AQUA_MODIS"].reset_index(drop=True), n_cells, aqua_from={"D": None, "N": None}))
    raw = {(int(r.year), int(r.month)): float(r.raw_combined_cell_days) for r in harm.itertuples()}
    series = lambda df: df[["entity_type", "entity_id", "year", "month", "estimate"]]
    base_h, base_a = e1.baselines(series(harm), BASE_YEARS), e1.baselines(series(aqua), BASE_YEARS)
    months = eval_months()
    official = ctrl_compare(judge(harm, base_h, raw), judge(aqua, base_a, raw), months)
    shared = ctrl_compare(judge(harm, base_a, raw), judge(aqua, base_a, raw), months)
    whole = {}
    for i, (a, b) in enumerate(CTRL_ANALYSIS_WINDOWS):
        idxs = {f"analysis_window_{i + 1}": list(range(midx(*a), midx(*b) + 1))}
        whole.update(ctrl_compare(judge(harm, base_h, raw), judge(aqua, base_a, raw), idxs)["per_date"])
    detail = {"official": explain_months(harm, aqua, base_h, base_a, official["spurious"]),
              "shared_baseline": explain_months(harm, aqua, base_a, base_a, shared["spurious"])}
    return {"key": list(key), "n_cells": n_cells[key], "spurious_detail": detail, "official": {**official, "status": ctrl_status(official["spurious_total"], official["determinable_harmonized"])},
            "shared_baseline": {**shared, "status": ctrl_status(shared["spurious_total"], shared["determinable_harmonized"])},
            "analysis_windows_whole": whole, "baseline_years": list(BASE_YEARS),
            "baseline_months_harmonized": len(base_h), "baseline_months_aqua": len(base_a)}


# ============================================================================================================ stages and entries
def stage_inputs(paths: hz.Paths, fresh: bool = False) -> dict:
    """The cached aggregations (data/interim/T-024): fire regions 2012-01 to 2024-04, the cell pool 2012-2021, box C8 2003-2022."""
    tmp = ROOT / "data" / "interim" / "_tmp_T-024"
    cells = pd.read_parquet(paths.products / "cells.parquet")
    reg = regions_members(cells)
    pool = draw_cell_pool(cells)
    box = pd.DataFrame({"entity_type": "CUSTOM", "entity_id": "C8", "entity_name": "C8", "cell_id": e1.box_cells(cells, C8_BOX)})
    n_cells = {("REGION", r): int(n) for r, n in reg.groupby("entity_id").size().items()}
    n_cells.update({("CELL", c): 1 for c in pool})
    n_box = {("CUSTOM", "C8"): len(box)}
    WORK.mkdir(parents=True, exist_ok=True)
    out = {"n_cells": n_cells, "n_box": n_box, "pool": pool}
    out["regions"] = cached(WORK / "agg_regions.parquet", lambda: aggregate_entities(reg, months_between(B2_FIRST, C1_LAST), paths, tmp, chunk=1), fresh)
    out["cells"] = cached(WORK / "agg_cells.parquet", lambda: aggregate_entities(cells_members(pool), months_between(B2_FIRST, B2_LAST), paths, tmp, chunk=500), fresh)
    out["box"] = cached(WORK / "agg_c8.parquet", lambda: aggregate_entities(box, months_between(CTRL_FIRST, CTRL_LAST), paths, tmp), fresh)
    shutil.rmtree(tmp, ignore_errors=True)
    return out


def _entry(test_id: str, family: str, title: str, case: str, criterion: str, threshold: str, measured: dict, status: str, notes: str) -> dict:
    return {"test_id": test_id, "family": family, "title": title, "case": case, "criterion": criterion, "threshold": threshold,
            "measured": measured, "status": status, "notes": notes}


def pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def build_entries(b2: dict | None, c1: dict | None, ctrl: dict | None) -> list[dict]:
    """Contract section 6 entries (the official test ids B2, C1, CTRL and clearly named supplementary ones)."""
    out = []
    if b2 is not None:
        s = b2["summary"]
        out.append(_entry(
            "B2", "B", "Planted sensor jump detected",
            f"{s['trials']} trials: a jump (factor 1.5 to 3, up or down) in one witness of a random fire region or a random single cell from a random month in 2012-2021, "
            "planted in the in-memory aggregated table", "Flagged (WITNESS_DISAGREEMENT or a disagreement scale of at least 1.5) in the jump month or the two after in at least 90% of trials, and false flags in under 5% of unplanted series",
            "detection >= 90% and false flags < 5% (locked at G1, D-028)",
            {"trials": s["trials"], "detection": s["detected"], "false_flags_unplanted_twin_window": s["false_flags_twin"],
             "by_type": {t: {"trials": v["trials"], "detection": v["detected"]["share"], "false_flags": v["false_flags_twin"]["share"]} for t, v in b2["by_type"].items()},
             "seed": b2["seed"]},
            b2["status"], "Readings of the plan [ASSUMPTION], task prompt section 15 items 1 to 5. False flag = the same rule on the unplanted twin of each trial (same three months): the rate under pure chance for two witnesses is about 13% over three months. See docs/validation/T-024-results.md."))
        out.append(_entry(
            "B2-CODE-ONLY", "B", "Planted sensor jump detected: reason code only (supplementary)",
            "Same 200 trials", "Flagged = WITNESS_DISAGREEMENT only (S > 2)", "detection >= 90% and false flags < 5%",
            {"detection": s["detected_by_code"], "false_flags_unplanted_twin_window": s["false_flags_twin_by_code"]}, b2["status_code_only"],
            "Supplementary reading; the official entry is B2."))
        m = b2["monthly"]
        fm = m.get("flagged_union", {}).get("share")
        out.append(_entry(
            "B2-FALSE-FLAG-MONTHLY", "B", "False flags of unplanted series per month and per series (supplementary)",
            f"{m.get('entity_months', 0)} unplanted entity-months (regions and cell pool, 2012-2021, two or more witnesses, estimate >= 5)",
            "Share of unplanted entity-months flagged; share of entities flagged in any month", "< 5% (the plan's false-flag threshold, applied per month)",
            {"entity_months": m.get("entity_months"), "flagged_per_month_union": m.get("flagged_union"), "flagged_per_month_code": m.get("flagged_code"),
             "entities_flagged_anywhere_union": m.get("entities_flagged_anywhere_union"), "entities_flagged_anywhere_code": m.get("entities_flagged_anywhere_code")},
            "INCONCLUSIVE" if fm is None else ("PASS" if fm < B2_FALSE_MAX else "FAIL"),
            "Supplementary: the plan does not say what a false flag per series means; the status here applies the 5% threshold to the monthly union-rule rate."))
    if c1 is not None:
        o = c1["official"]
        out.append(_entry(
            "C1", "C", "Cross-satellite agreement (S-NPP against NOAA-20)",
            f"Fire-region-months 2018-01 to 2021-12, both converted estimates >= 5 Aqua-equivalent cell-days ({o['units']} units)",
            "Share of region-months where converted S-NPP and converted NOAA-20 agree within the combined 90% intervals", ">= 85% (locked at G1, D-028)",
            {"units": o["units"], "agree": o["agree"], "overlap_reading": o["overlap"], "median_ratio_snpp_over_noaa20": o.get("median_ratio_snpp_over_noaa20"),
             "per_region_agree": {r: v["agree"] for r, v in o["per_region"].items()}, "in_sample": c1["in_sample"]},
            o["status"], "Agreement = the difference within 1.645 x sqrt(sd_S^2 + sd_N^2) [ASSUMPTION 6]. The whole window is IN sample for NOAA-20 (calibration 2018-04 to 2021-12) and out of sample for S-NPP; no month is out of sample for both: see C1-OUT-OF-SAMPLE-2022-2024."))
        out.append(_entry(
            "C1-OVERLAP", "C", "Cross-satellite agreement: overlapping intervals (supplementary)", "Same units as C1",
            "Share of region-months where the two 90% intervals overlap", ">= 85%", {"units": o["units"], "overlap": o["overlap"]}, o["status_overlap"],
            "A more lenient reading than the official one; supplementary."))
        p = c1["out_of_sample_both"]
        out.append(_entry(
            "C1-OUT-OF-SAMPLE-2022-2024", "C", "Cross-satellite agreement in months out of sample for both witnesses (supplementary)",
            f"Fire-region-months 2022-01 to 2024-04 ({p['units']} units)", "Same as C1", ">= 85% (the plan's threshold, applied to months outside the plan window)",
            {"units": p["units"], "agree": p["agree"], "overlap_reading": p["overlap"], "per_region_agree": {r: v["agree"] for r, v in p["per_region"].items()}},
            p["status"], "Outside the plan's 2018-2021 window; ends before the earliest VIIRS night drift onset (2024-05). Supplementary only."))
    if ctrl is not None:
        o = ctrl["official"]
        out.append(_entry(
            "CTRL", "CTRL", "Control: no spurious verdicts at the satellite-change dates (box C8)",
            f"Southern African savanna box C8 (20, -20, 35, -8; {ctrl['n_cells']} cells), the 25 months around 2012-01 and 2018-04",
            "No ABOVE/BELOW verdict of the harmonized series that the Aqua-only series does not give in the same month", "0 spurious verdicts (locked at G1, D-028)",
            {"spurious_total": o["spurious_total"], "spurious": o["spurious"], "determinable_harmonized_months": o["determinable_harmonized"],
             "per_date": {d: {k: v for k, v in x.items()} for d, x in o["per_date"].items()}},
            o["status"], "Harmonized series against its harmonized baseline, Aqua-only series against the Aqua-measured baseline, both 2003-2022 [ASSUMPTION 8]. INCONCLUSIVE would mean fewer than 12 determinable months."))
        s = ctrl["shared_baseline"]
        out.append(_entry(
            "CTRL-SHARED-BASELINE", "CTRL", "Control with one shared Aqua-measured baseline (supplementary, the form of D-029)", "Same months as CTRL",
            "Same rule, both series judged against the Aqua-measured 2003-2022 baseline", "0 spurious verdicts",
            {"spurious_total": s["spurious_total"], "spurious": s["spurious"], "determinable_harmonized_months": s["determinable_harmonized"]}, s["status"],
            "Supplementary reading; the official entry is CTRL."))
    return out


def write_outputs(reports: dict[str, dict | None]) -> Path:
    """Write each report that ran now, then the entries file from every report on disk."""
    QA.mkdir(parents=True, exist_ok=True)
    for name, rep in reports.items():
        if rep is not None:
            (QA / f"T-024_{name}_report.json").write_text(json.dumps(rep, indent=1, default=str), encoding="utf-8")
    load = lambda n: json.loads((QA / f"T-024_{n}_report.json").read_text(encoding="utf-8")) if (QA / f"T-024_{n}_report.json").exists() else None
    entries = build_entries(load("b2"), load("c1"), load("ctrl"))
    doc = {"contract_version": CONTRACT_VERSION, "method_version": hz.METHOD_VERSION, "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
           "synthetic": False, "tests": entries}
    path = QA / "T-024_validation_entries.json"
    path.write_text(json.dumps(doc, indent=1, default=str), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("which", choices=["all", "b2", "c1", "ctrl", "entries"], nargs="?", default="all")
    ap.add_argument("--fresh", action="store_true", help="recompute the cached aggregations")
    args = ap.parse_args(argv)
    reports: dict[str, dict | None] = {"b2": None, "c1": None, "ctrl": None}
    if args.which != "entries":
        st = stage_inputs(hz.Paths(), args.fresh)
        if args.which in ("all", "b2"):
            reports["b2"] = run_b2(st["regions"], st["cells"], st["n_cells"])
            print("B2", reports["b2"]["status"], reports["b2"]["rates"])
        if args.which in ("all", "c1"):
            reports["c1"] = run_c1(st["regions"], st["n_cells"])
            print("C1", reports["c1"]["official"]["status"], reports["c1"]["official"]["agree"])
        if args.which in ("all", "ctrl"):
            reports["ctrl"] = run_ctrl(st["box"], st["n_box"])
            print("CTRL", reports["ctrl"]["official"]["status"], reports["ctrl"]["official"]["spurious_total"])
    print(write_outputs(reports))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
