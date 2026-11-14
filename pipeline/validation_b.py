"""Validation tests B1 (satellite-change steps) and B3 (known artifacts), T-021.

Criteria and thresholds come only from docs/VALIDATION_PLAN.md section 3 and D-028 (locked at G1, 2026-11-14); the choices the plan
leaves open are fixed below and in docs/task-prompts/T-021-test-b.md section 9 BEFORE any result was seen.

B1. For a fire region and a satellite-change date d (2012-01: S-NPP enters; 2018-04: NOAA-20 enters), with X the series under test and
A the Aqua-only series (Aqua cell-days, Aqua ratio 1):

    q(window) = sum X / sum A over the usable months of the window       (usable: an estimate exists and Aqua was used)
    step      = q(the 12 months from d) / q(the 12 months before d)

PASS at a date when the harmonized step is within +-10% of 1 in at least 80% of the regions with sufficient data, provided the raw
step (X = raw combined cell-days) is clearly present (outside +-10% of 1 in at least half of those regions), else INCONCLUSIVE.

B3. (a) the drift: the pre-registered T-012 detector on the global monthly Aqua / converted-VIIRS ratio, PASS when it fires for both
VIIRS witnesses in the same day/night part with a negative slope and an onset in 2021 or later; (b) outages, estimates: a month with
no complete witness has no estimate, and an incomplete witness-month is never used; (c) outages, verdicts: such months are 100%
CANNOT_DETERMINE (D-028 step 1), NOT_RUN until the verdict product of T-014 exists.

Everything takes entity_month-shaped DataFrames (docs/DATA_CONTRACT.md section 4), so the same code runs on the output of
harmonize.records_from today and on the T-014 product later.

    python pipeline/validation_b.py                       # real products; writes data/interim/qa/T-021_validation_entries.json
    python pipeline/validation_b.py --entity-month PATH   # the T-014 entity_month product for the verdict part
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

import aqua_drift as ad

# ---------------------------------------------------------------------------------------------------- locked / fixed choices
B1_DATES = [(2012, 1), (2018, 4)]       # VALIDATION_PLAN B1
WINDOW = 12                             # months after / before (VALIDATION_PLAN B1)
TOLERANCE = 0.10                        # harmonized step within +-10% of 1 (VALIDATION_PLAN B1)
PASS_FRACTION = 0.80                    # in at least 80% of the regions with sufficient data (VALIDATION_PLAN B1)
# open in the plan, fixed in the task prompt before any result [ASSUMPTION]:
MIN_USABLE_MONTHS = 10                  # per window
MIN_AQUA_CELL_DAYS = 60.0               # per window: 5 per month, as D-028 step 4
RAW_PRESENT_FRACTION = 0.5              # the raw step is "clearly present" if outside the tolerance in at least this share of regions
MIN_REGIONS = 5                         # fewer sufficient regions: INCONCLUSIVE
NOT_REGIONS = ("UNASSIGNED", "NONE")    # not fire regions
DRIFT_ONSET_FROM = (2021, 1)            # "visible after ~2021"
C8_BOX = (20.0, -20.0, 35.0, -8.0)      # W, S, E, N (VALIDATION_PLAN 2a)
WITNESSES = ["AQUA_MODIS", "SNPP_VIIRS", "NOAA20_VIIRS"]
STATUSES = ("PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN")


def month_idx(year, month):
    return np.asarray(year, dtype=int) * 12 + np.asarray(month, dtype=int) - 1


def label(year: int, month: int) -> str:
    return f"{year}-{month:02d}"


# -------------------------------------------------------------------------------------------------- entity_month-shaped frames
def _has(used, name: str) -> bool:
    if used is None:
        return False
    if isinstance(used, str):
        return name in used
    try:
        return name in list(used)
    except TypeError:
        return False


def _aqua_raw(raw_by) -> float:
    if raw_by is None or (isinstance(raw_by, float) and np.isnan(raw_by)):
        return 0.0
    d = json.loads(raw_by) if isinstance(raw_by, str) else dict(raw_by)
    return float(d.get("AQUA_MODIS", 0.0))


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    """Adds idx (month number), aqua (Aqua-only cell-days), has_est and has_aqua to an entity_month-shaped frame."""
    f = frame.copy()
    f["idx"] = month_idx(f["year"], f["month"])
    f["aqua"] = [_aqua_raw(r) for r in f["raw_by_witness"]]
    f["has_est"] = f["estimate"].notna()
    f["has_aqua"] = [_has(u, "AQUA_MODIS") for u in f["witnesses_used"]]
    return f


# ----------------------------------------------------------------------------------------------------------------------- B1
def step_ratio(df: pd.DataFrame, date: tuple[int, int], value: str = "estimate", ref: str = "aqua", ok: str | None = None,
               window: int = WINDOW) -> dict:
    """The B1 step of one entity. df has idx, `value`, `ref` and a boolean `ok` column (default: has_est and has_aqua).

    q = sum(value) / sum(ref) over the usable months of the 12 months from `date` (after) and of the 12 months before it (before);
    step = q_after / q_before (nan when either is undefined). `sufficient` applies the minimum months and Aqua cell-days.
    """
    mask = (df["has_est"] & df["has_aqua"]) if ok is None else df[ok]
    d = int(month_idx(*date))
    out: dict = {}
    for name, lo, hi in (("before", d - window, d - 1), ("after", d, d + window - 1)):
        s = df[mask & df["idx"].between(lo, hi)]
        r = float(s[ref].sum())
        out[f"n_{name}"] = len(s)
        out[f"ref_{name}"] = r
        out[f"q_{name}"] = float(s[value].sum()) / r if r > 0 else float("nan")
    qb, qa = out["q_before"], out["q_after"]
    out["step"] = qa / qb if np.isfinite(qa) and np.isfinite(qb) and qb > 0 else float("nan")
    out["sufficient"] = bool(out["n_before"] >= MIN_USABLE_MONTHS and out["n_after"] >= MIN_USABLE_MONTHS
                             and out["ref_before"] >= MIN_AQUA_CELL_DAYS and out["ref_after"] >= MIN_AQUA_CELL_DAYS
                             and np.isfinite(out["step"]))
    return out


def evaluate_b1(frame: pd.DataFrame, dates=B1_DATES, entity_type: str | None = "REGION", exclude=NOT_REGIONS) -> pd.DataFrame:
    """One row per entity and date: harmonized step, raw step (X = raw_combined_cell_days) and whether the data suffice."""
    f = prepare(frame)
    f["raw"] = f["raw_combined_cell_days"].astype(float)
    if entity_type is not None:
        f = f[f["entity_type"] == entity_type]
    rows = []
    for (etype, eid), g in f.groupby(["entity_type", "entity_id"], sort=True):
        if eid in exclude:
            continue
        for date in dates:
            h = step_ratio(g, date, "estimate")
            r = step_ratio(g, date, "raw")
            rows.append({"entity_type": etype, "entity_id": eid, "date": label(*date), "harmonized_step": h["step"], "raw_step": r["step"],
                         "n_before": h["n_before"], "n_after": h["n_after"], "aqua_before": h["ref_before"], "aqua_after": h["ref_after"],
                         "sufficient": h["sufficient"] and r["sufficient"]})
    return pd.DataFrame(rows, columns=["entity_type", "entity_id", "date", "harmonized_step", "raw_step", "n_before", "n_after",
                                       "aqua_before", "aqua_after", "sufficient"])


def b1_status(rows: pd.DataFrame, tol: float = TOLERANCE, pass_fraction: float = PASS_FRACTION) -> dict:
    """Status of B1 at one date from the rows of `evaluate_b1` for that date."""
    suff = rows[rows["sufficient"]]
    n = len(suff)
    out = {"regions_total": len(rows), "regions_sufficient": int(n), "regions_within_tolerance": None, "fraction_within": None,
           "raw_outside_fraction": None, "tolerance": tol, "pass_fraction": pass_fraction}
    if n:
        within = (suff["harmonized_step"] - 1.0).abs() <= tol + 1e-12
        raw_out = (suff["raw_step"] - 1.0).abs() > tol
        out.update({"regions_within_tolerance": int(within.sum()), "fraction_within": float(within.mean()),
                    "raw_outside_fraction": float(raw_out.mean()), "median_harmonized_step": float(suff["harmonized_step"].median()),
                    "median_raw_step": float(suff["raw_step"].median())})
    if n < MIN_REGIONS:
        out["status"], out["why"] = "INCONCLUSIVE", f"fewer than {MIN_REGIONS} regions with sufficient data"
    elif out["raw_outside_fraction"] < RAW_PRESENT_FRACTION:
        out["status"], out["why"] = "INCONCLUSIVE", "the raw step is not clearly present, so removing it cannot be shown"
    elif out["fraction_within"] >= pass_fraction:
        out["status"], out["why"] = "PASS", ""
    else:
        out["status"], out["why"] = "FAIL", ""
    return out


def pct_of_normal_shift(frame: pd.DataFrame, entity_id: str, date: tuple[int, int], window: int = WINDOW) -> dict:
    """Supplementary, for the T-014 product: median pct_of_normal in the 12 months from `date` minus that of the 12 months before
    (percentage points) for one entity. The plan sets no threshold for it, so it carries no status."""
    f = frame[(frame["entity_id"] == entity_id) & frame["pct_of_normal"].notna()].copy()
    f["idx"] = month_idx(f["year"], f["month"])
    d = int(month_idx(*date))
    b = f[f["idx"].between(d - window, d - 1)]["pct_of_normal"]
    a = f[f["idx"].between(d, d + window - 1)]["pct_of_normal"]
    if len(a) < MIN_USABLE_MONTHS or len(b) < MIN_USABLE_MONTHS:
        return {"n_before": len(b), "n_after": len(a), "shift": None}
    return {"n_before": len(b), "n_after": len(a), "median_before": float(b.median()), "median_after": float(a.median()),
            "shift": float(a.median() - b.median())}


# ----------------------------------------------------------------------------------------------------------------------- B3
def evaluate_b3_drift(series: pd.DataFrame, reps: int = ad.N_BOOT) -> dict:
    """Drift visible as a ratio trend. `series`: global rows of aqua_drift.build_series (daynight, witness, idx, R).

    The registered T-012 detector is run on each day/night x VIIRS witness (NOAA-20: first candidate 12 months after its first
    month, as in T-012). PASS if for some day/night part both witnesses are detected with a negative slope and an onset in 2021
    or later; FAIL if every part could be fitted and none qualifies; INCONCLUSIVE if no part has both series fitted.
    """
    first = int(month_idx(*DRIFT_ONSET_FROM)) - int(month_idx(*ad.FIRST_MONTH))      # in aqua_drift's month index
    per: dict[str, dict] = {}
    for (dn, w), s in series.groupby(["daynight", "witness"]):
        res = ad.run_series(s.sort_values("idx"), 12 if w == "NOAA20_VIIRS" else 0, reps)
        if res.get("status") != "ok":
            per[f"{dn}|{w}"] = {"status": res.get("status"), "n": res.get("n")}
            continue
        pub = ad.public(res)
        keep = ("onset_month", "onset_lo_month", "onset_hi_month", "slope_pct_per_year", "slope_lo_pct_per_year", "slope_hi_pct_per_year",
                "delta_bic", "detected", "n")
        entry = {k: pub[k] for k in keep}
        entry["status"] = "ok"
        entry["qualifies"] = bool(res["detected"] and res["slope"] < 0 and res["onset"] >= first)
        per[f"{dn}|{w}"] = entry
    parts: dict[str, dict] = {}
    for dn in ("D", "N"):
        ws = [per.get(f"{dn}|{w}") for w in ad.VIIRS]
        fitted = all(x is not None and x.get("status") == "ok" for x in ws)
        parts[dn] = {"fitted": fitted, "qualifies": bool(fitted and all(x["qualifies"] for x in ws))}
    if any(p["qualifies"] for p in parts.values()):
        status = "PASS"
    elif any(p["fitted"] for p in parts.values()):
        status = "FAIL"
    else:
        status = "INCONCLUSIVE"
    return {"status": status, "series": per, "parts": parts,
            "qualifying_parts": sorted(dn for dn, p in parts.items() if p["qualifies"])}


def incomplete_witness_months(paths=None) -> pd.DataFrame:
    """One row per month and witness (Aqua, S-NPP, NOAA-20) that has data: whether every day is available (read from
    cell_month_witness.parquet, independently of harmonize.py)."""
    import duckdb
    import harmonize as hz
    paths = paths or hz.Paths()
    con = duckdb.connect()
    wit = ", ".join(f"'{w}'" for w in WITNESSES)
    q = f"""SELECT year, month, witness, min(days_available) AS days_available, max(days_in_month) AS days_in_month,
                   bool_and(days_available = days_in_month) AS complete
            FROM read_parquet('{(paths.products / 'cell_month_witness.parquet').as_posix()}')
            WHERE daynight = 'ALL' AND witness IN ({wit}) GROUP BY year, month, witness ORDER BY year, month, witness"""
    return con.execute(q).df()


def outage_months(wm: pd.DataFrame) -> list[tuple[int, int]]:
    """Months with no complete witness (D-028 step 1): every witness with data is incomplete."""
    ok = wm.groupby(["year", "month"])["complete"].any()
    return sorted((int(y), int(m)) for (y, m), c in ok.items() if not c)


def _rows_in(frame: pd.DataFrame, months: list[tuple[int, int]]) -> pd.DataFrame:
    keys = set(months)
    return frame[[(int(y), int(m)) in keys for y, m in zip(frame["year"], frame["month"], strict=True)]]


def evaluate_outage_estimates(frame: pd.DataFrame, wm: pd.DataFrame) -> dict:
    """(1) every entity-month in an outage month (no complete witness) has no estimate: 100% required; (2) no incomplete witness-month
    appears in witnesses_used. INCONCLUSIVE if the frame holds no outage month."""
    out_m = outage_months(wm)
    rows = _rows_in(frame, out_m)
    inc = {(int(r.year), int(r.month), r.witness) for r in wm[~wm["complete"]].itertuples()}
    used_incomplete = 0
    months_checked = 0
    for y, m, u in zip(frame["year"], frame["month"], frame["witnesses_used"], strict=True):
        for w in WITNESSES:
            if (int(y), int(m), w) in inc:
                months_checked += 1
                used_incomplete += int(_has(u, w))
    n = len(rows)
    with_est = int(rows["estimate"].notna().sum())
    res = {"outage_months": [label(*x) for x in out_m], "entity_months_in_outage": int(n), "with_estimate": with_est,
           "share_without_estimate": None if n == 0 else 1.0 - with_est / n,
           "incomplete_witness_entity_months": int(months_checked), "incomplete_witness_used": int(used_incomplete),
           "incomplete_witness_months": sorted({label(y, m) + " " + w for y, m, w in inc})}
    if n == 0:
        res["status"] = "INCONCLUSIVE"
    else:
        res["status"] = "PASS" if with_est == 0 and used_incomplete == 0 else "FAIL"
    return res


def has_verdicts(frame: pd.DataFrame) -> bool:
    """True once the product carries the verdict logic of T-014 (baseline fields filled); the raw-only and the T-013 products do not."""
    return bool("baseline_median" in frame.columns and frame["baseline_median"].notna().any())


def evaluate_outage_verdicts(frame: pd.DataFrame | None, wm: pd.DataFrame) -> dict:
    """Outage months (no complete witness) are 100% CANNOT_DETERMINE (the share with reason OUTAGE is reported, D-028 step 1).
    NOT_RUN when there is no frame or it has no verdicts yet."""
    if frame is None or not has_verdicts(frame):
        return {"status": "NOT_RUN", "why": "the verdict product of T-014 does not exist yet (the entity_month product is raw-only or has no baseline)"}
    out_m = outage_months(wm)
    rows = _rows_in(frame, out_m)
    n = len(rows)
    if n == 0:
        return {"status": "INCONCLUSIVE", "why": "no outage month in the frame", "entity_months_in_outage": 0}
    cd = int((rows["verdict"] == "CANNOT_DETERMINE").sum())
    coded = int(sum("OUTAGE" in list(c) for c in rows["reason_codes"]))
    return {"status": "PASS" if cd == n else "FAIL", "outage_months": [label(*x) for x in out_m], "entity_months_in_outage": n,
            "cannot_determine": cd, "share_cannot_determine": cd / n, "with_outage_code": coded, "share_with_outage_code": coded / n}


def describe_snpp_end(wm: pd.DataFrame, frame: pd.DataFrame | None = None, end: tuple[int, int, int] = (2026, 11, 2)) -> dict:
    """Supplementary (no plan criterion): what the monthly availability shows about the S-NPP end (2026-11-02)."""
    s = wm[wm["witness"] == "SNPP_VIIRS"].sort_values(["year", "month"])
    done = s[s["complete"]]
    last_complete = None if done.empty else label(int(done.iloc[-1].year), int(done.iloc[-1].month))
    after = s[(s["year"] == end[0]) & (s["month"] == end[1])]
    res = {"documented_end": f"{end[0]}-{end[1]:02d}-{end[2]:02d}", "last_complete_month": last_complete,
           "days_available_in_end_month": None if after.empty else int(after.iloc[0].days_available),
           "consistent_with_end": bool(not after.empty and int(after.iloc[0].days_available) <= end[2])}
    if frame is not None:
        f = frame[(frame["year"] * 100 + frame["month"]) >= end[0] * 100 + end[1]]
        res["entity_months_from_end_month"] = len(f)
        res["entity_months_using_snpp_from_end_month"] = int(sum(_has(u, "SNPP_VIIRS") for u in f["witnesses_used"]))
    return res


# ---------------------------------------------------------------------------------------------------------------- family status
def family_status(parts: list[str]) -> str:
    """Any FAIL -> FAIL; else any NOT_RUN -> NOT_RUN; else any INCONCLUSIVE -> INCONCLUSIVE; else PASS (all parts ran)."""
    for s in ("FAIL", "NOT_RUN", "INCONCLUSIVE"):
        if s in parts:
            return s
    return "PASS"


# ------------------------------------------------------------------------------------------------------------ contract entries
def _clean(x):
    if isinstance(x, dict):
        return {str(k): _clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v) for v in x]
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        return None if not np.isfinite(x) else float(x)
    if isinstance(x, (np.bool_,)):
        return bool(x)
    return x


def entries_from(b1: dict[str, dict], b3: dict) -> list[dict]:
    """Test entries in the shape of DATA_CONTRACT.md section 6. b1: date label -> b1_status dict; b3: the B3 parts."""
    out = []
    crit_b1 = ("Step ratio (series / Aqua-only), 12 months after vs before: raw step clearly present; harmonized within +-10% of 1 "
               "in >=80% of the regions with sufficient data")
    for date, st in b1.items():
        out.append({"test_id": f"B1-{date}", "family": "B", "title": "Satellite-change step removed", "case": f"all fire regions, change date {date}",
                    "criterion": crit_b1, "threshold": "within +-10% of 1 in >=80% of regions (G1, D-028)",
                    "measured": {k: v for k, v in st.items() if k not in ("status", "why")}, "status": st["status"], "notes": st["why"]})
    out.append({"test_id": "B1", "family": "B", "title": "Satellite-change step removed (both dates)", "case": "all fire regions, 2012-01 and 2018-04",
                "criterion": crit_b1, "threshold": "both dates PASS", "measured": {d: s["status"] for d, s in b1.items()},
                "status": family_status([s["status"] for s in b1.values()]), "notes": ""})
    parts = {"B3-DRIFT": ("Aqua drift visible as a ratio trend", "global monthly Aqua / converted-VIIRS ratio, 2012-2026",
                          "drift visible as a ratio trend, reported with its onset estimate",
                          "T-012 detector fires for both VIIRS witnesses in one day/night part, negative slope, onset 2021 or later"),
             "B3-OUTAGE-ESTIMATE": ("Outage months have no estimate", "months with no complete witness",
                                    "outage months 100% without an estimate; an incomplete witness-month is never used", "100%"),
             "B3-OUTAGE-VERDICT": ("Outage months are CANNOT_DETERMINE", "months with no complete witness",
                                   "outage months 100% CANNOT_DETERMINE", "100%")}
    for tid, (title, case, crit, thr) in parts.items():
        p = b3[tid]
        out.append({"test_id": tid, "family": "B", "title": title, "case": case, "criterion": crit, "threshold": thr,
                    "measured": {k: v for k, v in p.items() if k not in ("status", "why")}, "status": p["status"], "notes": p.get("why", "")})
    out.append({"test_id": "B3", "family": "B", "title": "Known real artifacts surfaced", "case": "global",
                "criterion": "drift visible as a ratio trend; outage months 100% CANNOT_DETERMINE", "threshold": "all parts PASS",
                "measured": {t: b3[t]["status"] for t in parts}, "status": family_status([b3[t]["status"] for t in parts]),
                "notes": "NOT_RUN while any part is not run"})
    return _clean(out)


# ----------------------------------------------------------------------------------------------- real-data run (not unit-tested)
def _members(con, paths) -> None:
    cells = f"read_parquet('{(paths.products / 'cells.parquet').as_posix()}')"
    con.execute(f"""CREATE TEMP TABLE members AS SELECT 'REGION' AS entity_type, coalesce(fire_region, 'NONE') AS entity_id,
                    coalesce(fire_region, 'NONE') AS entity_name, cell_id FROM {cells}""")


def snpp_reference(agg: pd.DataFrame) -> pd.DataFrame:
    """Converted S-NPP estimate (day + night) per entity-month, only where both parts are complete: the continuous reference
    for the supplementary check at 2024-05."""
    s = agg[(agg.witness == "SNPP_VIIRS") & agg.complete]
    g = s.groupby(["entity_type", "entity_id", "year", "month"]).agg(snpp=("e", "sum"), parts=("daynight", "nunique")).reset_index()
    return g[g.parts == 2].drop(columns="parts")


def run(entity_month: Path | None = None, paths=None, out_dir: Path | None = None, reps: int = ad.N_BOOT) -> dict:
    import duckdb
    import harmonize as hz
    paths = paths or hz.Paths()
    out_dir = out_dir or ROOT / "data" / "interim" / "qa"
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    con.execute("SET memory_limit='6GB'")
    _members(con, paths)
    counts = {("REGION", e): n for e, n in con.execute("SELECT entity_id, count(*) FROM members GROUP BY 1").fetchall()}
    agg = hz.aggregate(con, paths, "members", None)
    frame = pd.DataFrame(hz.records_from(agg, counts))
    wm = incomplete_witness_months(paths)

    # B1 on the fire regions (and the C8 box as a supplementary row)
    rows = evaluate_b1(frame)
    cells = pd.read_parquet(paths.products / "cells.parquet")
    w, s, e, n = C8_BOX
    c8 = cells[(cells.lon_c > w) & (cells.lon_c < e) & (cells.lat_c > s) & (cells.lat_c < n)].cell_id.tolist()
    c8_frame = pd.DataFrame(hz.harmonize_area(c8, entity_id="C8", entity_name="Southern African savanna (control)"))
    c8_rows = evaluate_b1(c8_frame, entity_type="CUSTOM", exclude=())
    b1 = {d: b1_status(rows[rows["date"] == d]) for d in (label(*x) for x in B1_DATES)}

    # supplementary: step at the Aqua night exclusion (2024-05) against the continuous converted S-NPP series
    ref = snpp_reference(agg)
    f = prepare(frame).merge(ref, on=["entity_type", "entity_id", "year", "month"], how="left")
    f = f[~f.entity_id.isin(NOT_REGIONS)]
    f["ok"] = f.has_est & f.snpp.notna()
    s2024 = []
    for eid, g in f.groupby("entity_id"):
        r = step_ratio(g, (2024, 5), "estimate", "snpp", "ok")
        s2024.append({"entity_id": eid, **r})
    s2024 = pd.DataFrame(s2024)
    have = s2024[np.isfinite(s2024.step)]
    supp_2024 = {"reference": "converted S-NPP (day + night), months where S-NPP is complete in both parts",
                 "regions_sufficient": int(s2024.sufficient.sum()), "regions_with_a_step": len(have),
                 "fraction_within_10pct_of_those": None if have.empty else float(((have.step - 1).abs() <= TOLERANCE).mean()),
                 "median_step": None if have.empty else float(have.step.median()),
                 "usable_months_after_min_max": None if have.empty else [int(have.n_after.min()), int(have.n_after.max())],
                 "usable_months_before_min_max": None if have.empty else [int(have.n_before.min()), int(have.n_before.max())],
                 "steps": {r.entity_id: (None if not np.isfinite(r.step) else round(float(r.step), 4)) for r in s2024.itertuples()}}

    # B3
    glob = ad.build_series(agg[agg.year >= 2012])
    glob = glob[glob.entity_id == "GLOBAL"]
    drift = evaluate_b3_drift(glob, reps)
    outage_est = evaluate_outage_estimates(frame, wm)
    em = None
    if entity_month is None and (paths.products / "entity_month.parquet").exists():
        entity_month = paths.products / "entity_month.parquet"
    if entity_month is not None:
        em = pd.read_parquet(entity_month)
    outage_verd = evaluate_outage_verdicts(em, wm)
    snpp = describe_snpp_end(wm, frame)
    b3 = {"B3-DRIFT": drift, "B3-OUTAGE-ESTIMATE": outage_est, "B3-OUTAGE-VERDICT": outage_verd}
    entries = entries_from(b1, b3)
    pct_shift = None
    if em is not None and has_verdicts(em):
        pct_shift = {f"{eid}|{label(*d)}": pct_of_normal_shift(em, eid, d) for eid in ("ZAF", "AF") for d in B1_DATES}

    full = {"generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"), "b1_status": b1, "b1_rows": rows.to_dict("records"),
            "c8_rows": c8_rows.to_dict("records"), "c8_cells": len(c8), "supplementary_2024_05": supp_2024, "b3": b3,
            "snpp_end": snpp, "pct_of_normal_shift": pct_shift, "entity_month_input": None if entity_month is None else str(entity_month)}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "T-021_validation_entries.json").write_text(json.dumps(
        {"contract_version": "0.1.1", "method_version": hz.METHOD_VERSION, "generated_at": full["generated_at"], "synthetic": False,
         "tests": entries}, indent=1), encoding="utf-8")
    (out_dir / "T-021_full_results.json").write_text(json.dumps(_clean(full), indent=1), encoding="utf-8")
    return full


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entity-month", type=Path, default=None, help="the T-014 entity_month product (verdict part)")
    ap.add_argument("--reps", type=int, default=ad.N_BOOT)
    a = ap.parse_args()
    res = run(a.entity_month, reps=a.reps)
    for d, st in res["b1_status"].items():
        print(f"B1 {d}: {st['status']}  sufficient {st['regions_sufficient']}/{st['regions_total']}  within {st['fraction_within']}  raw outside {st['raw_outside_fraction']}")
    for k, v in res["b3"].items():
        print(f"{k}: {v['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
