"""Validation test A2: the same fire in two eras (T-023).

Test A2 (docs/VALIDATION_PLAN.md section 3, cases C1, C4, C6): plant the event's real Aqua detections into a quiet pre-2012 month and its
real VIIRS detections into a quiet post-2022 month, harmonize both. PASS: the harmonized peaks overlap within their 90% intervals AND the
raw record shows a mismatch (otherwise the test is INCONCLUSIVE). The design is fixed in docs/task-prompts/T-023-test-a2.md before any run:

  * quiet month: the calendar month with the lowest median (2003-2022, at least 15 of 20 years) of the harmonized series of the case box,
    taken in 2010 and in 2023 (plan section 2a);
  * event month: the month of the peak window with the most raw Aqua cell-days in the box;
  * planting at the level of `cell_month_witness`: the quiet month's rows of the box cells are removed (every witness), the event month's
    real Aqua rows go into (2010, quiet month), the event month's real S-NPP rows into (2023, quiet month); detections, cell-days and FRP
    sums are the event's, `days_in_month` is the target month's, `days_available` equals it, `data_level` is the quiet month's;
  * harmonization: `harmonize.aggregate` + `harmonize.records_from`, pointed at a temporary copy of the tables under data/interim;
    the products on disk are never changed;
  * peak and overlap as in A1: the estimate of the planted month, +/- 1.645 sd, floored at 0; intervals that touch overlap;
  * raw mismatch: raw S-NPP cell-days (2023) over raw Aqua cell-days (2010) at least 1.5 or at most 1/1.5.

    python pipeline/validation_a2.py [--case C1] [--refresh]
"""
from __future__ import annotations

import argparse
import calendar
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harmonize as hz
import validation_a1 as va

ROOT = Path(__file__).resolve().parents[1]
QA_DIR = ROOT / "data" / "interim" / "qa"
WORK_DIR = ROOT / "data" / "interim" / "T-023"
CONTRACT_VERSION = "0.1.1"
TEST_FAMILY = "A"
CASE_IDS = ("C1", "C4", "C6")
CASES: dict[str, dict] = {k: va.CASES[k] for k in CASE_IDS}
OLD_YEAR, NEW_YEAR = 2010, 2023                 # plan section 2a: pre-2012 and post-2022
OLD_WITNESS, NEW_WITNESS = "AQUA_MODIS", "SNPP_VIIRS"
BASELINE_YEARS = va.BASELINE_YEARS              # 2003-2022
MIN_QUIET_YEARS = 15                            # D-028 step 2 (the 5 cell-day floor of step 4 is not applied to the quiet month)
RAW_MISMATCH = 1.5                              # fixed in advance: raw ratio at least 1.5 or at most 1/1.5
LARGE_INFLATION = 2.0                           # descriptive only
PLANT_COLS = ["cell_id", "year", "month", "witness", "daynight", "detections", "cell_days", "frp_sum_mw", "days_available", "days_in_month", "data_level"]
PASS, FAIL, INCONCLUSIVE, NOT_RUN = "PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN"
Month = tuple[int, int]


# ------------------------------------------------------------------------------------------------ quiet month and event month
def quiet_calendar_month(series: pd.DataFrame, years: tuple[int, int] = BASELINE_YEARS, min_years: int = MIN_QUIET_YEARS) -> dict | None:
    """The calendar month with the lowest median of `series` (columns year, month, estimate) over `years`.

    Only the years with an estimate count; a calendar month with fewer than `min_years` of them is not eligible. The earliest calendar
    month wins a tie. None if no calendar month is eligible.
    """
    medians: dict[int, float] = {}
    counts: dict[int, int] = {}
    inside = series[(series.year >= years[0]) & (series.year <= years[1]) & series.estimate.notna()]
    for m in range(1, 13):
        st = va.baseline_stats(inside.loc[inside.month == m, "estimate"].tolist(), years, min_years, 0.0)
        if st:
            medians[m], counts[m] = st["baseline_median"], st["n_baseline_years"]
    if not medians:
        return None
    best = min(sorted(medians), key=lambda m: medians[m])        # sorted: the earliest calendar month wins a tie
    return {"month": best, "median": medians[best], "n_years": counts[best], "medians": {str(m): medians[m] for m in sorted(medians)}}


def event_month(raw_aqua: dict[Month, float], peak: tuple[Month, Month]) -> Month | None:
    """The month of the peak window with the most raw Aqua cell-days (earliest on a tie); None if no month has a positive count."""
    months = va.month_range(*peak)
    have = [(m, float(raw_aqua[m])) for m in months if m in raw_aqua and raw_aqua[m] > 0]
    if not have:
        return None
    return max(have, key=lambda t: (t[1], -va.month_index(*t[0])))[0]


# ------------------------------------------------------------------------------------------------ planting
def month_days(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def plant_month(cmw: pd.DataFrame, cell_ids: list[str], event: Month, target: Month, witness: str) -> tuple[pd.DataFrame, dict]:
    """Plant the real `witness` rows of the event month into the target month of the box cells.

    `cmw` holds `cell_month_witness` rows (at least the event month and the target month). Returns (the table with the target month's
    rows of `cell_ids` replaced, an info dict). `info["ok"]` is False, with `info["reason"]`, if the record cannot be planted coherently;
    the table is then returned unchanged. Nothing is scaled or trimmed: detections, cell-days and FRP sums are those of the event.
    """
    ids = set(cell_ids)
    dim = month_days(*target)
    in_box = cmw["cell_id"].isin(ids)
    is_event = (cmw["year"] == event[0]) & (cmw["month"] == event[1])
    is_target = (cmw["year"] == target[0]) & (cmw["month"] == target[1])
    src = cmw[in_box & is_event & (cmw["witness"] == witness)].copy()
    info: dict = {"ok": False, "reason": None, "witness": witness, "event": f"{event[0]}-{event[1]:02d}", "target": f"{target[0]}-{target[1]:02d}",
                  "days_in_month": dim, "n_rows": len(src), "removed_rows": int((in_box & is_target).sum())}
    if src.empty:
        info["reason"] = f"the event month has no {witness} rows in the box"
        return cmw, info
    if (src["days_available"] != src["days_in_month"]).any():
        info["reason"] = f"the event month of {witness} is not complete in every cell (days_available below days_in_month)"
        return cmw, info
    own = cmw[in_box & is_target & (cmw["witness"] == witness) & cmw["data_level"].notna()]["data_level"]
    level = own.mode().iloc[0] if len(own) else None          # the quiet month's own level for this witness, else the event's
    event_dim = int(src["days_in_month"].iloc[0])
    src["year"], src["month"] = target
    src["days_in_month"] = dim
    src["days_available"] = dim
    if level is not None:
        src["data_level"] = level
    keep = cmw[~(in_box & is_target)]
    out = pd.concat([keep, src[cmw.columns]], ignore_index=True)
    info.update({"ok": True, "event_days_in_month": event_dim, "cell_days": int(src["cell_days"].sum()), "detections": int(src["detections"].sum()),
                 "frp_sum_mw": float(src["frp_sum_mw"].sum()), "data_level": str(src["data_level"].iloc[0]) if len(src) else None})
    return out, info


def plant_case(cmw: pd.DataFrame, cell_ids: list[str], event: Month, quiet_month: int) -> tuple[pd.DataFrame, dict]:
    """Both eras: Aqua rows of the event into (2010, quiet month), S-NPP rows of the event into (2023, quiet month)."""
    t_old, t_new = (OLD_YEAR, quiet_month), (NEW_YEAR, quiet_month)
    table, i_old = plant_month(cmw, cell_ids, event, t_old, OLD_WITNESS)
    table, i_new = plant_month(table, cell_ids, event, t_new, NEW_WITNESS)
    return table, {"old": i_old, "new": i_new}


def season_of(month: int) -> str:
    return "DJF" if month in (12, 1, 2) else "MAM" if month in (3, 4, 5) else "JJA" if month in (6, 7, 8) else "SON"


def calibration_with_season(cal: pd.DataFrame, from_season: str, to_season: str) -> pd.DataFrame:
    """Exploratory variant: the rows of `to_season` take ratio and ratio_sd of `from_season` (same stratum, witness, day/night)."""
    out = cal.copy()
    src = cal[cal.season == from_season].set_index(["stratum_id", "witness", "daynight"])[["ratio", "ratio_sd"]]
    idx = pd.MultiIndex.from_frame(out.loc[out.season == to_season, ["stratum_id", "witness", "daynight"]])
    for col in ("ratio", "ratio_sd"):
        vals = src[col].reindex(idx)
        sel = out.index[out.season == to_season]
        out.loc[sel, col] = np.where(vals.notna().to_numpy(), vals.to_numpy(), out.loc[sel, col].to_numpy())
    return out


# ------------------------------------------------------------------------------------------------ harmonization of the planted table
def connect(work: Path, memory: str = "5GB") -> duckdb.DuckDBPyConnection:
    """A DuckDB connection with the limits of the heavy-job protocol and a private temp directory."""
    tmp = work / "_tmp_T-023"
    tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{memory}'")
    con.execute("SET max_temp_directory_size='20GiB'")
    con.execute("SET preserve_insertion_order=false")
    con.execute("SET threads=4")
    con.execute(f"SET temp_directory='{tmp.as_posix()}'")
    return con


def harmonize_table(table: pd.DataFrame, cells: pd.DataFrame, cal: pd.DataFrame, cell_ids: list[str], months: list[Month], workdir: Path,
                    entity_id: str = "A2") -> dict:
    """`aggregate` + `records_from` on a planted `cell_month_witness` table (written, with `cells` and `calibration`, to `workdir`).

    The real products are not read or changed: `workdir` is a temporary product directory.
    """
    workdir.mkdir(parents=True, exist_ok=True)
    table[PLANT_COLS].to_parquet(workdir / "cell_month_witness.parquet", index=False)
    cells.to_parquet(workdir / "cells.parquet", index=False)
    cal.to_parquet(workdir / "calibration.parquet", index=False)
    paths = hz.Paths(products=workdir, tmp=workdir / "_dbtmp")
    ids = sorted(set(cell_ids))
    con = connect(workdir)
    try:
        members = pd.DataFrame({"entity_type": "CUSTOM", "entity_id": entity_id, "entity_name": "A2 box", "cell_id": ids})
        con.register("members_df", members)
        con.execute("CREATE TEMP TABLE members AS SELECT * FROM members_df")
        agg = hz.aggregate(con, paths, "members", months)
    finally:
        con.close()
    agg_by = {w: va.restrict_witness(agg, w) for w in (OLD_WITNESS, NEW_WITNESS)}
    recs = hz.records_from(agg, {("CUSTOM", entity_id): len(ids)})
    ctx = {w: va.records_frame(hz.records_from(a, {("CUSTOM", entity_id): len(ids)})) for w, a in agg_by.items()}
    return {"combined": recs, "single": ctx}


# ------------------------------------------------------------------------------------------------ the criterion
def interval90(estimate: float, sd: float) -> tuple[float, float]:
    return hz.interval(float(estimate), float(sd))


def intervals_overlap(a: tuple[float, float], b: tuple[float, float]) -> bool:
    """90% intervals overlap; intervals that touch overlap (as in A1)."""
    return bool(a[0] <= b[1] and b[0] <= a[1])


def raw_mismatch(raw_old: float, raw_new: float, threshold: float = RAW_MISMATCH) -> dict:
    """The raw-record mismatch between the eras: ratio = raw_new / raw_old (S-NPP 2023 over Aqua 2010)."""
    if not raw_old or not raw_new or raw_old <= 0 or raw_new <= 0:
        return {"ratio": None, "mismatch": None, "direction": None, "large_inflation": None}
    r = raw_new / raw_old
    return {"ratio": float(r), "mismatch": bool(max(r, 1.0 / r) >= threshold),
            "direction": "inflation" if r > 1 else ("deflation" if r < 1 else "none"), "large_inflation": bool(r >= LARGE_INFLATION)}


def case_status(info_old: dict, info_new: dict, old: dict | None, new: dict | None, raw: dict, quiet_ok: bool = True, event_ok: bool = True) -> dict:
    """The A2 status of a case. old / new: {"estimate", "sd"} of the harmonized planted month of each era, or None if it has no estimate.

    PASS: coherent planting, both estimates, raw mismatch AND overlapping 90% intervals. FAIL: the same preconditions and no overlap.
    INCONCLUSIVE: no quiet month or event month, an incoherent planting, a missing estimate, or no raw mismatch (the plan's own rule).
    """
    out: dict = {"status": INCONCLUSIVE, "reasons": [], "intervals_overlap": None, "interval_old": None, "interval_new": None}
    if not quiet_ok:
        out["reasons"].append("no calendar month has a baseline median (fewer than 15 years with an estimate): the quiet month cannot be fixed")
    if not event_ok:
        out["reasons"].append("the peak window has no month with raw Aqua cell-days: no event to plant")
    for name, info in (("Aqua / 2010", info_old), ("S-NPP / 2023", info_new)):
        if info is not None and not info.get("ok"):
            out["reasons"].append(f"planting {name}: {info.get('reason')}")
    if out["reasons"]:
        return out
    for name, rec in (("2010 (Aqua)", old), ("2023 (S-NPP)", new)):
        if rec is None or rec.get("estimate") is None or not np.isfinite(rec["estimate"]):
            out["reasons"].append(f"the planted {name} month has no harmonized estimate")
    if out["reasons"]:
        return out
    if raw["mismatch"] is None:
        out["reasons"].append("a planted month has zero raw cell-days: no record to compare")
        return out
    out["interval_old"], out["interval_new"] = interval90(old["estimate"], old["sd"]), interval90(new["estimate"], new["sd"])
    out["intervals_overlap"] = intervals_overlap(out["interval_old"], out["interval_new"])
    if not raw["mismatch"]:
        out["reasons"].append(f"the raw record shows no mismatch (raw ratio {raw['ratio']:.3f}, inside (1/{RAW_MISMATCH}, {RAW_MISMATCH})): the test cannot discriminate")
        return out
    if out["intervals_overlap"]:
        out["status"] = PASS
    else:
        out["status"] = FAIL
        out["reasons"].append("the 90% intervals of the harmonized peaks do not overlap")
    return out


def family_entry(entries: list[dict]) -> dict:
    """The A2 family entry. [ASSUMPTION] the plan gives no rule; literal reading: PASS only if all of C1, C4, C6 PASS.

    As in the A1 family entry: FAIL when "all three PASS" can no longer be reached (a decided case is FAIL or INCONCLUSIVE and no case is
    NOT_RUN); INCONCLUSIVE while a case is still NOT_RUN. An INCONCLUSIVE case does not count as a PASS.
    """
    by_case = {e["test_id"].removeprefix("A2-"): e["status"] for e in entries if e["test_id"] != "A2"}
    statuses = [by_case.get(c, NOT_RUN) for c in CASE_IDS]
    n_pass = statuses.count(PASS)
    if n_pass == len(CASE_IDS):
        status = PASS
    elif statuses.count(NOT_RUN):
        status = FAIL if (statuses.count(FAIL) or statuses.count(INCONCLUSIVE)) else INCONCLUSIVE
    else:
        status = FAIL
    return {"test_id": "A2", "family": TEST_FAMILY, "title": "Same fire, two eras: family result", "case": "C1, C4, C6",
            "criterion": "All three cases C1, C4, C6 PASS (the plan gives no family rule: [ASSUMPTION], the literal reading)",
            "threshold": "A2 as written in VALIDATION_PLAN section 3 per case; the family rule is an [ASSUMPTION] for the Lead; an INCONCLUSIVE case does not count as a PASS",
            "measured": {"case_status": dict(zip(CASE_IDS, statuses, strict=True)), "n_pass": n_pass, "n_fail": statuses.count(FAIL),
                         "n_inconclusive": statuses.count(INCONCLUSIVE), "n_not_run": statuses.count(NOT_RUN)},
            "status": status,
            "notes": "Family rule is an [ASSUMPTION] (all three must PASS; an INCONCLUSIVE case is not a PASS and, as in the A1 family entry, makes the family "
                     "FAIL once no case is left to run). The case statuses are listed so that an INCONCLUSIVE is not read as a failure of the method. "
                     "See docs/validation/T-023-results.md."}


# ------------------------------------------------------------------------------------------------ the real data (heavy: take the lock)
def stage_series(cells: pd.DataFrame, paths: hz.Paths, work: Path, refresh: bool = False) -> dict[str, pd.DataFrame]:
    """The harmonized series (all witnesses) of each case box, 2003-2022, cached in `work`. One aggregate over the three boxes."""
    files = {c: work / f"series_{c}.parquet" for c in CASE_IDS}
    if not refresh and all(f.exists() for f in files.values()):
        return {c: pd.read_parquet(f) for c, f in files.items()}
    work.mkdir(parents=True, exist_ok=True)
    ids = {c: va.box_cells(cells, CASES[c]["box"]) for c in CASE_IDS}
    members = pd.concat([pd.DataFrame({"entity_type": "CUSTOM", "entity_id": c, "entity_name": c, "cell_id": v}) for c, v in ids.items()])
    months = [(y, m) for y in range(BASELINE_YEARS[0], BASELINE_YEARS[1] + 1) for m in range(1, 13)]
    con = connect(work)
    try:
        con.register("members_df", members)
        con.execute("CREATE TEMP TABLE members AS SELECT * FROM members_df")
        agg = hz.aggregate(con, paths, "members", months)
    finally:
        con.close()
    recs = va.records_frame(hz.records_from(agg, {("CUSTOM", c): len(v) for c, v in ids.items()}))
    out = {}
    for c in CASE_IDS:
        df = recs[recs.entity_id == c][["year", "month", "estimate", "sd", "raw_combined_cell_days"]].reset_index(drop=True)
        df.to_parquet(files[c], index=False)
        out[c] = df
    return out


def extract_rows(cell_ids: list[str], months: list[Month], paths: hz.Paths, work: Path, tag: str, refresh: bool = False) -> pd.DataFrame:
    """The `cell_month_witness` rows of the box cells in `months`, cached in `work` (cells and months filtered first)."""
    f = work / f"rows_{tag}.parquet"
    if f.exists() and not refresh:
        return pd.read_parquet(f)
    cmw = f"read_parquet('{(paths.products / 'cell_month_witness.parquet').as_posix()}')"
    con = connect(work)
    try:
        con.register("ids_df", pd.DataFrame({"cell_id": sorted(set(cell_ids))}))
        con.execute("CREATE TEMP TABLE ids AS SELECT * FROM ids_df")
        keys = ", ".join(str(y * 100 + m) for y, m in months)
        df = con.execute(f"SELECT w.* FROM {cmw} w WHERE w.cell_id IN (SELECT cell_id FROM ids) AND w.year * 100 + w.month IN ({keys})").df()
    finally:
        con.close()
    df.to_parquet(f, index=False)
    return df


def raw_aqua_by_month(rows: pd.DataFrame, cell_ids: list[str]) -> dict[Month, float]:
    """Raw Aqua cell-days (day + night) summed over the box cells, per month."""
    r = rows[rows.cell_id.isin(set(cell_ids)) & (rows.witness == OLD_WITNESS) & rows.daynight.isin(["D", "N"])]
    return {(int(y), int(m)): float(v) for (y, m), v in r.groupby(["year", "month"])["cell_days"].sum().items()}


def _est(rec: dict | None) -> dict | None:
    return None if rec is None or rec.get("estimate") is None else {"estimate": float(rec["estimate"]), "sd": float(rec["sd"])}


def _find(recs: list[dict], year: int, month: int) -> dict | None:
    for r in recs:
        if r["year"] == year and r["month"] == month:
            return r
    return None


def run_case(case_id: str, series: pd.DataFrame, cells: pd.DataFrame, cal: pd.DataFrame, paths: hz.Paths, work: Path, refresh: bool = False) -> dict:
    """One case end to end; returns the entry. Reads the real products only through `extract_rows`."""
    case = CASES[case_id]
    ids = va.box_cells(cells, case["box"])
    quiet = quiet_calendar_month(series)
    measured: dict = {"n_cells": len(ids), "quiet_month_rule": "lowest median 2003-2022 of the box's harmonized series, >= 15 years, earliest on a tie"}
    if quiet is None:
        res = case_status({"ok": True}, {"ok": True}, None, None, raw_mismatch(0, 0), quiet_ok=False)
        return _entry(case_id, case, measured, res)
    qm = quiet["month"]
    measured["quiet_calendar_month"] = qm
    measured["quiet_month_baseline_median"] = quiet["median"]
    measured["baseline_medians_by_calendar_month"] = quiet["medians"]
    peak_months = va.month_range(*case["peak"])
    targets = [(OLD_YEAR, qm), (NEW_YEAR, qm)]
    rows = extract_rows(ids, sorted(set(peak_months) | set(targets)), paths, work, case_id, refresh)
    ev = event_month(raw_aqua_by_month(rows, ids), case["peak"])
    raw_peak = raw_aqua_by_month(rows, ids)
    measured["raw_aqua_cell_days_peak_window"] = {f"{y}-{m:02d}": raw_peak.get((y, m)) for y, m in peak_months}
    if ev is None:
        return _entry(case_id, case, measured, case_status({"ok": True}, {"ok": True}, None, None, raw_mismatch(0, 0), event_ok=False))
    measured["event_month"] = f"{ev[0]}-{ev[1]:02d}"
    ev_rows = rows[(rows.year == ev[0]) & (rows.month == ev[1])]
    table, info = plant_case(rows, ids, ev, qm)
    measured["planting"] = info
    if not (info["old"]["ok"] and info["new"]["ok"]):
        return _entry(case_id, case, measured, case_status(info["old"], info["new"], None, None, raw_mismatch(0, 0)))
    # totals preserved: the planted months hold the event's cell-days exactly
    for key, w, tgt in (("old", OLD_WITNESS, targets[0]), ("new", NEW_WITNESS, targets[1])):
        planted = table[(table.year == tgt[0]) & (table.month == tgt[1]) & (table.witness == w)]
        src = ev_rows[(ev_rows.witness == w)]
        info[key]["totals_preserved"] = bool(planted.cell_days.sum() == src.cell_days.sum() and planted.detections.sum() == src.detections.sum())
        info[key]["other_witnesses_in_planted_month"] = sorted(set(table[(table.year == tgt[0]) & (table.month == tgt[1])].witness) - {w})
    is_target = table.year.isin([OLD_YEAR, NEW_YEAR]) & (table.month == qm)
    keep = table[is_target | ((table.year == ev[0]) & (table.month == ev[1]))]
    months = sorted({(OLD_YEAR, qm), (NEW_YEAR, qm), ev})
    h = harmonize_table(keep, cells, cal, ids, months, work / f"planted_{case_id}")
    recs, single = h["combined"], h["single"]
    old, new = _find(recs, OLD_YEAR, qm), _find(recs, NEW_YEAR, qm)
    raw = raw_mismatch(old["raw_combined_cell_days"] if old else 0, new["raw_combined_cell_days"] if new else 0)
    res = case_status(info["old"], info["new"], _est(old), _est(new), raw)
    measured.update(_measured(old, new, raw, quiet, single, ev))
    # exploratory variant: the ratios of the event's season instead of the target month's season
    cal_event = calibration_with_season(cal, season_of(ev[1]), season_of(qm))
    h2 = harmonize_table(keep, cells, cal_event, ids, months, work / f"planted_{case_id}_eventseason")
    new2 = _find(h2["combined"], NEW_YEAR, qm)
    if new2 and new2.get("estimate") is not None and old and old.get("estimate") is not None:
        iv_o, iv_n = interval90(old["estimate"], old["sd"]), interval90(new2["estimate"], new2["sd"])
        measured["exploratory_event_season_ratios"] = {"season_of_event": season_of(ev[1]), "season_of_target": season_of(qm), "snpp_2023_estimate": float(new2["estimate"]),
                                                       "snpp_2023_sd": float(new2["sd"]), "snpp_2023_ci90": [iv_n[0], iv_n[1]],
                                                       "intervals_overlap": intervals_overlap(iv_o, iv_n), "ratio_new_over_old": float(new2["estimate"] / old["estimate"]) if old["estimate"] else None}
    return _entry(case_id, case, measured, res)


def _measured(old: dict | None, new: dict | None, raw: dict, quiet: dict, single: dict, ev: Month) -> dict:
    out: dict = {"raw": {"aqua_2010_cell_days": old["raw_combined_cell_days"] if old else None, "snpp_2023_cell_days": new["raw_combined_cell_days"] if new else None,
                         **raw, "threshold": RAW_MISMATCH}}
    for key, rec in (("harmonized_2010_aqua", old), ("harmonized_2023_snpp", new)):
        if rec and rec.get("estimate") is not None:
            out[key] = {"estimate": rec["estimate"], "sd": rec["sd"], "ci90": [rec["ci90_low"], rec["ci90_high"]], "witnesses_used": rec["witnesses_used"],
                        "reason_codes": rec["reason_codes"], "pct_of_normal_context": rec["estimate"] / quiet["median"] * 100.0 if quiet["median"] >= va.MIN_BASELINE_MEDIAN else None}      # None below the 5 cell-day floor of D-028: no meaningful percentage
    if old and new and old.get("estimate") and new.get("estimate") is not None:
        out["harmonized_ratio_new_over_old"] = new["estimate"] / old["estimate"]
        out["difference_in_sd"] = (new["estimate"] - old["estimate"]) / float(np.sqrt(old["sd"] ** 2 + new["sd"] ** 2))
    real = {w: _find(single[w].to_dict("records"), ev[0], ev[1]) for w in single}
    out["real_event_month_context"] = {w: (None if r is None or r.get("estimate") is None else {"estimate": float(r["estimate"]), "sd": float(r["sd"])}) for w, r in real.items()}
    ra = real.get(OLD_WITNESS)
    out["identity_check_aqua"] = {"planted_2010_estimate": old["estimate"] if old else None, "real_event_aqua_only_estimate": ra["estimate"] if ra else None,
                                  "equal": bool(old and ra and np.isclose(old["estimate"], ra["estimate"], rtol=0, atol=1e-9))}
    return out


def _entry(case_id: str, case: dict, measured: dict, res: dict) -> dict:
    measured = dict(measured)
    measured.update({"intervals_overlap": res["intervals_overlap"], "interval_2010": res["interval_old"], "interval_2023": res["interval_new"], "reasons": res["reasons"]})
    return {"test_id": f"A2-{case_id}", "family": TEST_FAMILY, "title": "Same fire, two eras (planted into quiet months)", "case": case["label"],
            "criterion": "Harmonized peaks overlap within 90% intervals AND the raw record shows a mismatch (otherwise INCONCLUSIVE)",
            "threshold": f"VALIDATION_PLAN section 3 (A2); raw mismatch fixed in advance: raw S-NPP 2023 / raw Aqua 2010 >= {RAW_MISMATCH} or <= 1/{RAW_MISMATCH}; "
                         "90% intervals (1.645 sd, floor 0) that touch overlap",
            "measured": measured, "status": res["status"],
            "notes": "Design fixed in docs/task-prompts/T-023-test-a2.md before any run. A planted month holds one witness (Aqua in 2010, S-NPP in 2023), so each is a "
                     "single-witness estimate. See docs/validation/T-023-results.md."}


def run(case_ids: list[str] | None = None, paths: hz.Paths | None = None, out_dir: Path = QA_DIR, work: Path = WORK_DIR, refresh: bool = False) -> list[dict]:
    """Run the cases (default C1, C4, C6), write the entries file (with the family entry when all three ran)."""
    case_ids = list(case_ids or CASE_IDS)
    paths = paths or hz.Paths()
    out_dir.mkdir(parents=True, exist_ok=True)
    cells = pd.read_parquet(paths.products / "cells.parquet")
    cal = pd.read_parquet(paths.products / "calibration.parquet")
    series = stage_series(cells, paths, work, refresh)
    entries = [run_case(c, series[c], cells, cal, paths, work, refresh) for c in case_ids]
    if set(case_ids) == set(CASE_IDS):
        entries.append(family_entry(entries))
    doc = {"contract_version": CONTRACT_VERSION, "method_version": hz.METHOD_VERSION + "+a2", "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "synthetic": False, "tests": entries}
    (out_dir / "T-023_validation_entries.json").write_text(json.dumps(doc, indent=2, default=float), encoding="utf-8")
    shutil.rmtree(work / "_tmp_T-023", ignore_errors=True)
    return entries


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--case", action="append", choices=list(CASE_IDS), help="a case to run (repeatable); default: C1, C4, C6")
    ap.add_argument("--refresh", action="store_true", help="recompute the cached series and rows in data/interim/T-023")
    args = ap.parse_args()
    for e in run(args.case, refresh=args.refresh):
        m = e["measured"]
        print(e["test_id"], e["status"], m.get("raw", {}).get("ratio") if "raw" in m else m.get("case_status") or m.get("reasons"))


if __name__ == "__main__":
    main()
