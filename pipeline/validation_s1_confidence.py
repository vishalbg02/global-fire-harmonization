"""Validation test S1, confidence-filter half (T-025b): are the conclusions of A1 and B1 unchanged without the T-005 confidence filter?

docs/VALIDATION_PLAN.md section 3, S1: "Re-run A1 and B1 without the confidence filter [...]; conclusions unchanged (report any that change)".
T-025 ran the baseline half. This module runs the other half. The decision rule is fixed in docs/task-prompts/T-025b-s1-confidence.md
section 9 before any real run:

  * the detections are regridded as in `gridding.py` (T-006) but WITHOUT the confidence condition (the type filter and the D-025 static mask
    stay), only for the cells and months that A1 and B1 need, into a private directory (`data/interim/T-025b/`), never `data/products/`;
  * the T-011 ratios are NOT refitted [ASSUMPTION]: the filter is varied in the numerators only;
  * the cell set is the product's `cells.parquet` [ASSUMPTION];
  * validity gate: the same code WITH the filter (control) must reproduce the product rows of the selection exactly;
  * A1 (`validation_a1`), B1 (`validation_b`) and the peak-window verdicts (`validation_e1_s1`) are re-run unchanged on the private tables;
  * PASS: the A1 status of each of C1-C6, the A1 family status, the B1 status at 2012-01 and 2018-04 and the verdict of every peak-window
    month of C1-C6 are all unchanged; FAIL if any changes; INCONCLUSIVE if a part cannot be computed; NOT_RUN if the control fails.

    python pipeline/validation_s1_confidence.py            # regrid (cached), re-run, write entries and report
    python pipeline/validation_s1_confidence.py --force    # redo the regridding
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import gridding as gr
import harmonize as hz
import validation_a1 as va
import validation_b as vb
import validation_e1_s1 as s1

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "interim" / "T-025b"
TMP = ROOT / "data" / "interim" / "_tmp_T-025b"
QA = ROOT / "data" / "interim" / "qa"
PRODUCTS = ROOT / "data" / "products"
BOX_MARGIN = 0.6              # degrees added to each case box before the detections are cut (a 0.5 degree cell centred in the box reaches 0.25 beyond it)
B1_WINDOWS = {(2012, 1): ((2011, 1), (2012, 12)), (2018, 4): ((2017, 4), (2019, 3))}   # 12 months before and after each date
STATUSES = ("PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN")
CONTROL_FRP_RTOL = 1e-6


# ------------------------------------------------------------------------------------------------------------ selection
def ym(year: int, month: int) -> int:
    return year * 100 + month


def a1_months() -> list[va.Month]:
    """The months `validation_a1.build_case_frames` aggregates, over all cases."""
    out: set[va.Month] = set()
    for case in va.CASES.values():
        analysis = va.month_range(*case["analysis"])
        cal = sorted({m for _, m in analysis})
        out |= set(analysis) | {(y, m) for y in range(va.BASELINE_YEARS[0], va.BASELINE_YEARS[1] + 1) for m in cal}
    return sorted(out)


def b1_months() -> list[va.Month]:
    out: set[va.Month] = set()
    for first, last in B1_WINDOWS.values():
        out |= set(va.month_range(first, last))
    return sorted(out)


def a1_cells(cells: pd.DataFrame) -> list[str]:
    ids: set[str] = set()
    for case in va.CASES.values():
        ids |= set(va.box_cells(cells, case["box"]))
    return sorted(ids)


def box_sql(lat: str = "lat", lon: str = "lon") -> str:
    parts = []
    for case in va.CASES.values():
        w, s, e, n = case["box"]
        m = BOX_MARGIN
        parts.append(f"({lon} >= {w - m} AND {lon} <= {e + m} AND {lat} >= {s - m} AND {lat} <= {n + m})")
    return "(" + " OR ".join(parts) + ")"


def months_sql(months: list[va.Month], col: str = "ym") -> str:
    return f"{col} IN (" + ", ".join(str(ym(y, m)) for y, m in months) + ")" if months else "FALSE"


# ------------------------------------------------------------------------------------------------------------ regridding
def connect(tmp: Path = TMP) -> duckdb.DuckDBPyConnection:
    tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{tmp.as_posix()}'")
    con.execute("SET memory_limit='5GB'")
    con.execute("SET max_temp_directory_size='20GiB'")
    con.execute("SET preserve_insertion_order=false")
    con.execute("SET threads=4")
    return con


def kept_cut_sql(paths: gr.Paths, year: int, confidence: bool, cut: str) -> str:
    """The kept detections of `gridding.kept_sql`, with the confidence condition optional and `cut` (a condition on lat, lon, ym) added.

    Everything else is as in T-006: the witness map, the record start, SP rows of type 0 or NRT rows, the longitude wrap, the fine cell."""
    witness = "CASE satellite " + " ".join(f"WHEN '{k}' THEN '{v}'" for k, v in gr.WITNESS.items()) + " END"
    conf = "AND confidence_class IN ('NOMINAL', 'HIGH')" if confidence else ""
    fine = gr.FINE
    return f"""(SELECT {witness} AS witness, daynight, data_level, acq_date, frp_mw, confidence_class,
                       CAST(floor((lat + 90) / {fine}) AS INTEGER) AS fr,
                       CAST(floor((CASE WHEN lon >= 180 THEN lon - 360 ELSE lon END + 180) / {fine}) AS INTEGER) AS fc
                FROM (SELECT *, year(acq_date) * 100 + month(acq_date) AS ym FROM {gr.det_source(paths, year)})
                WHERE acq_date >= DATE '{gr.RECORD_START}' AND satellite IN ({', '.join(f"'{k}'" for k in gr.WITNESS)})
                  {conf} AND ((data_level = 'SP' AND type = 0) OR data_level = 'NRT') AND ({cut})) k"""


def regrid_year(con, paths: gr.Paths, year: int, confidence: bool, cut: str) -> pd.DataFrame:
    """Analysis cell-months of one year (witness, daynight, cell_id, month, cell_days, detections, frp_sum_mw), as `gridding.observe_year`."""
    mask = gr.MASK_JOIN.format(mask=paths.mask.as_posix())
    con.execute("DROP TABLE IF EXISTS kept")
    con.execute(f"CREATE TEMP TABLE kept AS SELECT k.* FROM {kept_cut_sql(paths, year, confidence, cut)} {mask} WHERE m.r IS NULL")
    df = con.execute(f"""SELECT witness, daynight, {gr.cell_id_sql(f'(fr // {gr.RATIO})', f'(fc // {gr.RATIO})')} AS cell_id, m AS month,
               count(*) AS cell_days, sum(det) AS detections, coalesce(sum(frp), 0.0) AS frp_sum_mw
        FROM (SELECT witness, daynight, fr, fc, month(acq_date) AS m, count(*) AS det, sum(frp_mw) FILTER (WHERE frp_mw >= 0) AS frp FROM kept
              GROUP BY witness, daynight, fr, fc, acq_date)
        GROUP BY ALL""").df()
    con.execute("DROP TABLE kept")
    return df


def assemble_year(con, skeleton: str, obs: pd.DataFrame, year: int) -> pd.DataFrame:
    """The private rows of one year: the skeleton (product rows of the selection, D and N) with the counts replaced by `obs`, zero where
    nothing was detected, and ALL = D + N. `skeleton` is a SQL relation with the product columns."""
    con.register("obs_df", obs)
    con.execute("CREATE OR REPLACE TEMP TABLE obs AS SELECT * FROM obs_df")
    con.unregister("obs_df")
    con.execute(f"""CREATE OR REPLACE TEMP TABLE dn AS
        SELECT s.cell_id, s.year, s.month, s.witness, s.daynight,
               CAST(coalesce(o.detections, 0) AS INTEGER) AS detections, CAST(coalesce(o.cell_days, 0) AS INTEGER) AS cell_days,
               coalesce(o.frp_sum_mw, 0.0) AS frp_sum_mw, s.days_available, s.days_in_month, s.data_level
        FROM (SELECT * FROM {skeleton} WHERE year = {year} AND daynight IN ('D', 'N')) s
        LEFT JOIN obs o ON o.cell_id = s.cell_id AND o.month = s.month AND o.witness = s.witness AND o.daynight = s.daynight""")
    out = con.execute(f"""SELECT {gr.CMW_COLUMNS} FROM (
          SELECT * FROM dn
          UNION ALL
          SELECT cell_id, year, month, witness, 'ALL', CAST(sum(detections) AS INTEGER), CAST(sum(cell_days) AS INTEGER), sum(frp_sum_mw),
                 any_value(days_available), any_value(days_in_month), any_value(data_level)
          FROM dn GROUP BY cell_id, year, month, witness)""").df()
    con.execute("DROP TABLE dn")
    con.execute("DROP TABLE obs")
    return out


def selection_sql(product: Path, a1_ids: list[str], months_a1: list[va.Month], months_b1: list[va.Month]) -> str:
    """The rows of the product `cell_month_witness` that A1 or B1 read: every cell in the B1 months, the case-box cells in the A1 months."""
    ids = ", ".join(f"'{c}'" for c in a1_ids)
    return (f"(SELECT * FROM read_parquet('{product.as_posix()}') WHERE "
            f"({months_sql(months_b1, 'year * 100 + month')}) OR (({months_sql(months_a1, 'year * 100 + month')}) AND cell_id IN ({ids})))")


def years_of(months: list[va.Month]) -> list[int]:
    return sorted({y for y, _ in months})


def build_tables(work: Path = WORK, products: Path = PRODUCTS, det_dir: Path | None = None, mask: Path | None = None,
                 log=print) -> dict:
    """Build the private `filtered` (the product rows of the selection), `control` (regridded WITH the filter) and `unfiltered` (regridded
    WITHOUT it) tables, plus copies of `cells.parquet` and `calibration.parquet` next to each for `harmonize.Paths`. Returns the counts."""
    t0 = time.time()
    paths = gr.Paths()
    if det_dir is not None:
        paths.detections = det_dir
    if mask is not None:
        paths.mask = mask
    cells = pd.read_parquet(products / "cells.parquet")
    ids_a1 = a1_cells(cells)
    ma, mb = a1_months(), b1_months()
    cut = f"({months_sql(mb)}) OR (({months_sql(ma)}) AND {box_sql()})"
    con = connect()
    skeleton = selection_sql(products / "cell_month_witness.parquet", ids_a1, ma, mb)
    for name in ("filtered", "control", "unfiltered"):
        (work / name).mkdir(parents=True, exist_ok=True)
        for f in ("cells.parquet", "calibration.parquet"):
            shutil.copyfile(products / f, work / name / f)
    n_outside = {"control": [0, 0], "unfiltered": [0, 0]}
    known = set(cells.cell_id)
    con.execute(f"COPY (SELECT {gr.CMW_COLUMNS} FROM {skeleton} ORDER BY cell_id, witness, daynight, year, month) "
                f"TO '{(work / 'filtered' / 'cell_month_witness.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
    log(f"filtered table written ({time.time() - t0:.0f}s)")
    for year in years_of(ma + mb):
        for name, confidence in (("control", True), ("unfiltered", False)):
            obs = regrid_year(con, paths, year, confidence, cut)
            outside = ~obs.cell_id.isin(known)
            n_outside[name][0] += int(obs.loc[outside, "detections"].sum())
            n_outside[name][1] += int(obs.loc[outside, "cell_id"].nunique())
            tab = assemble_year(con, skeleton, obs, year)
            tab.to_parquet(work / name / f"part_{year}.parquet", index=False)
        log(f"regridded {year} ({time.time() - t0:.0f}s)")
    for name in ("control", "unfiltered"):
        files = sorted((work / name).glob("part_*.parquet"))
        con.execute(f"COPY (SELECT * FROM read_parquet([{', '.join(repr(f.as_posix()) for f in files)}]) "
                    f"ORDER BY cell_id, witness, daynight, year, month) "
                    f"TO '{(work / name / 'cell_month_witness.parquet').as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
        for f in files:
            f.unlink()
    rows = {n: int(con.execute(f"SELECT count(*) FROM read_parquet('{(work / n / 'cell_month_witness.parquet').as_posix()}')").fetchone()[0])
            for n in ("filtered", "control", "unfiltered")}
    con.close()
    return {"rows": rows, "a1_cells": len(ids_a1), "a1_months": len(ma), "b1_months": len(mb), "seconds": round(time.time() - t0),
            "detections_in_cells_outside_the_product_cell_set": {k: {"detections": v[0], "cells": v[1]} for k, v in n_outside.items()}}


# ------------------------------------------------------------------------------------------------------------ control
def control_check(filtered: Path, control: Path) -> dict:
    """The control (regridded WITH the filter) must equal the product rows of the selection: same keys, equal cell_days and detections,
    frp_sum_mw within CONTROL_FRP_RTOL. Returns the counts of differences; `ok` is True only if there are none."""
    con = connect()
    a, b = f"read_parquet('{filtered.as_posix()}')", f"read_parquet('{control.as_posix()}')"
    key = "a.cell_id = b.cell_id AND a.year = b.year AND a.month = b.month AND a.witness = b.witness AND a.daynight = b.daynight"
    n_a, n_b = (con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in (a, b))
    j = con.execute(f"""SELECT count(*) AS joined,
        count(*) FILTER (WHERE a.cell_days <> b.cell_days) AS cell_days_diff, count(*) FILTER (WHERE a.detections <> b.detections) AS detections_diff,
        count(*) FILTER (WHERE abs(a.frp_sum_mw - b.frp_sum_mw) > {CONTROL_FRP_RTOL} * greatest(abs(a.frp_sum_mw), 1.0)) AS frp_diff,
        sum(a.cell_days) AS cell_days_product, sum(b.cell_days) AS cell_days_control
        FROM {a} a JOIN {b} b ON {key}""").fetchone()
    con.close()
    out = {"rows_product": int(n_a), "rows_control": int(n_b), "rows_joined": int(j[0]), "cell_days_differences": int(j[1]),
           "detections_differences": int(j[2]), "frp_differences": int(j[3]), "cell_days_sum_product": int(j[4] or 0), "cell_days_sum_control": int(j[5] or 0)}
    out["ok"] = bool(n_a == n_b == j[0] and not (j[1] or j[2] or j[3]))
    return out


# ------------------------------------------------------------------------------------------------------------ the re-run
def run_a1(paths: hz.Paths) -> dict:
    """A1 on one private table: the official status of each case (`FORMAL_READING`), the family status and the S-NPP-only path numbers."""
    entries, frames_by = [], {}
    for cid, case in va.CASES.items():
        frames, n_cells = va.build_case_frames(case, paths)
        entry = va.entry_for(cid, case, frames)
        entries.append(entry)
        frames_by[cid] = n_cells
    fam = va.family_entry(entries)
    return {"status": {e["test_id"].removeprefix("A1-"): e["status"] for e in entries}, "family": fam["status"],
            "family_measured": fam["measured"],
            "formal": {e["test_id"].removeprefix("A1-"): e["measured"]["formal_reading"] for e in entries},
            "pct_of_normal": {e["test_id"].removeprefix("A1-"): {"aqua": e["measured"]["aqua_only_pct_of_normal"], "snpp": e["measured"]["snpp_only_pct_of_normal"]}
                              for e in entries},
            "n_cells": frames_by}


def run_b1(paths: hz.Paths, work: Path) -> dict:
    """B1 on one private table, as `validation_b.run`: fire-region entities over the B1 months."""
    con = connect(work / "duck_b1")
    vb._members(con, paths)
    counts = {("REGION", e): n for e, n in con.execute("SELECT entity_id, count(*) FROM members GROUP BY 1").fetchall()}
    agg = hz.aggregate(con, paths, "members", b1_months())
    frame = pd.DataFrame(hz.records_from(agg, counts))
    rows = vb.evaluate_b1(frame)
    out = {}
    for d in (vb.label(*x) for x in vb.B1_DATES):
        st = vb.b1_status(rows[rows["date"] == d])
        out[d] = {k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in st.items()}
    con.close()
    return {"b1": out, "rows": rows.replace({np.nan: None}).to_dict("records")}


def run_verdicts(paths: hz.Paths, work: Path) -> dict:
    """Peak-window verdicts of C1-C6 on one private table: the harmonized box series against its own harmonized 2003-2022 baseline."""
    cells = pd.read_parquet(paths.products / "cells.parquet")
    parts = [pd.DataFrame({"entity_type": "CASE", "entity_id": cid, "entity_name": cid, "cell_id": s1.box_cells(cells, box)})
             for cid, (box, _, _) in s1.CASES.items()]
    members = pd.concat(parts, ignore_index=True)
    n_cells = {("CASE", cid): int(n) for cid, n in members.groupby("entity_id").size().items()}
    con = connect(work / "duck_v")
    con.register("members_df", members)
    con.execute("CREATE TEMP TABLE members AS SELECT * FROM members_df")
    agg = hz.aggregate(con, paths, "members", a1_months())
    series = s1.records_frame(hz.records_from(agg, n_cells))
    base = s1.baselines(series, s1.BASE_HARMONIZED)
    out = {}
    for cid, (_, first, last) in s1.CASES.items():
        for y, m in va.month_range(first, last):
            r = series[(series.entity_id == cid) & (series.year == y) & (series.month == m)]
            b = base[(base.entity_id == cid) & (base.month == m)]
            est = None if r.empty or pd.isna(r.estimate.iloc[0]) else float(r.estimate.iloc[0])
            sd = None if r.empty or pd.isna(r.sd.iloc[0]) else float(r.sd.iloc[0])
            if b.empty:
                v = s1.verdict_for(est, sd, 0, np.nan, np.nan, np.nan)
                p50 = None
            else:
                b0 = b.iloc[0]
                v = s1.verdict_for(est, sd, int(b0.n_years), b0.p25, b0.p50, b0.p75)
                p50 = float(b0.p50)
            out[f"{cid}|{y}-{m:02d}"] = {"verdict": v[0], "reason": v[1], "estimate": est, "sd": sd, "baseline_p50": p50}
    con.close()
    return out


def run_all(products_dir: Path, work: Path) -> dict:
    """A1, B1 and the verdicts on one table; a part that raises is recorded as None (the comparison then gives INCONCLUSIVE)."""
    paths = hz.Paths(products=products_dir, tmp=TMP / ("duck_" + products_dir.name))
    out: dict = {}
    for name, fn in (("a1", lambda: run_a1(paths)), ("b1", lambda: run_b1(paths, work)), ("verdicts", lambda: run_verdicts(paths, work))):
        try:
            out[name] = fn()
        except Exception as exc:  # noqa: BLE001 - recorded, never hidden
            out[name] = None
            out[name + "_error"] = f"{type(exc).__name__}: {exc}"
    return out


# ------------------------------------------------------------------------------------------------------------ the rule
def compare_runs(filtered: dict, unfiltered: dict, control_ok: bool = True) -> dict:
    """The pre-registered rule (task prompt section 9.8) on the results of the two runs. Each is the dict of `run_all`
    (a1: status per case + family; b1: status per date; verdicts: verdict per peak-window month). Returns the status and every change."""
    changes: list[dict] = []
    uncomputed: list[str] = []
    n_compared = 0

    def cmp(part: str, key: str, a, b):
        nonlocal n_compared
        n_compared += 1
        if a != b:
            changes.append({"part": part, "item": key, "filtered": a, "unfiltered": b})

    a1f, a1u = filtered.get("a1"), unfiltered.get("a1")
    if a1f is None or a1u is None:
        uncomputed.append("A1")
    else:
        for cid in sorted(a1f["status"]):
            cmp("A1 case status", cid, a1f["status"][cid], a1u["status"].get(cid))
        cmp("A1 family status", "A1-FAMILY", a1f["family"], a1u["family"])
    b1f, b1u = filtered.get("b1"), unfiltered.get("b1")
    if b1f is None or b1u is None:
        uncomputed.append("B1")
    else:
        for d in sorted(b1f["b1"]):
            cmp("B1 status", d, b1f["b1"][d]["status"], b1u["b1"].get(d, {}).get("status"))
    vf, vu = filtered.get("verdicts"), unfiltered.get("verdicts")
    if vf is None or vu is None:
        uncomputed.append("peak-window verdicts")
    else:
        for k in sorted(vf):
            cmp("peak-window verdict", k, vf[k]["verdict"], vu.get(k, {}).get("verdict"))
    if not control_ok:
        status, why = "NOT_RUN", "the control (same regridding with the confidence filter) did not reproduce the product rows"
    elif changes:
        status, why = "FAIL", f"{len(changes)} of {n_compared} compared conclusions change"
    elif uncomputed:
        status, why = "INCONCLUSIVE", "not computable in one of the runs: " + ", ".join(uncomputed)
    else:
        status, why = "PASS", f"all {n_compared} compared conclusions are unchanged"
    return {"status": status, "why": why, "n_compared": n_compared, "n_changed": len(changes), "changes": changes, "uncomputed": uncomputed}


def s1_overall(baseline: str | None, confidence: str) -> str:
    """S1 as a whole: PASS only if both halves PASS; FAIL if either FAILs; NOT_RUN if a half is missing; otherwise INCONCLUSIVE."""
    halves = [baseline or "NOT_RUN", confidence]
    if "FAIL" in halves:
        return "FAIL"
    if "NOT_RUN" in halves:
        return "NOT_RUN"
    if "INCONCLUSIVE" in halves:
        return "INCONCLUSIVE"
    return "PASS"


# ------------------------------------------------------------------------------------------------------------ entries
def entry(result: dict, control: dict | None, regrid: dict | None, filtered: dict | None, unfiltered: dict | None) -> dict:
    return {
        "test_id": "S1-CONFIDENCE-FILTER", "family": "S",
        "title": "Sensitivity: A1 and B1 without the confidence filter",
        "case": "A1 cases C1-C6 (official readings, family), B1 at 2012-01 and 2018-04, peak-window verdicts of C1-C6; regridded without the T-005 confidence filter, T-011 ratios unchanged",
        "criterion": "Conclusions unchanged: every A1 case status, the A1 family status, both B1 statuses and every peak-window verdict of C1-C6 equal in the filtered and unfiltered runs",
        "threshold": "S1 (VALIDATION_PLAN section 3): conclusions unchanged, any change reported; rule fixed in docs/task-prompts/T-025b-s1-confidence.md section 9",
        "measured": {"n_compared": result["n_compared"], "n_changed": result["n_changed"], "changes": result["changes"], "uncomputed": result["uncomputed"],
                     "control": control, "regridding": regrid,
                     "a1_status_filtered": None if not filtered or not filtered.get("a1") else filtered["a1"]["status"],
                     "a1_status_unfiltered": None if not unfiltered or not unfiltered.get("a1") else unfiltered["a1"]["status"],
                     "a1_family": [None if not filtered or not filtered.get("a1") else filtered["a1"]["family"],
                                   None if not unfiltered or not unfiltered.get("a1") else unfiltered["a1"]["family"]],
                     "b1_filtered": None if not filtered or not filtered.get("b1") else {d: v["status"] for d, v in filtered["b1"]["b1"].items()},
                     "b1_unfiltered": None if not unfiltered or not unfiltered.get("b1") else {d: v["status"] for d, v in unfiltered["b1"]["b1"].items()}},
        "status": result["status"],
        "notes": result["why"] + ". T-011 ratios not refitted [ASSUMPTION]; cell set of the product [ASSUMPTION]. See docs/validation/T-025b-results.md.",
    }


def write_entries(e: dict, report: dict, qa: Path = QA) -> None:
    qa.mkdir(parents=True, exist_ok=True)
    doc = {"contract_version": "0.1.1", "method_version": hz.METHOD_VERSION + "+s1-confidence", "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "synthetic": False, "tests": [e]}
    (qa / "T-025b_validation_entries.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    (qa / "T-025b_report.json").write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")


def baseline_status(qa: Path = QA) -> str | None:
    """The S1-BASELINE status recorded by T-025, if its entries file is on disk."""
    f = qa / "T-025_validation_entries.json"
    if not f.exists():
        return None
    for t in json.loads(f.read_text(encoding="utf-8"))["tests"]:
        if t["test_id"] == "S1-BASELINE":
            return t["status"]
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true", help="redo the regridding even if the private tables exist")
    args = ap.parse_args()
    t0 = time.time()
    regrid = None
    done = (WORK / "unfiltered" / "cell_month_witness.parquet").exists() and (WORK / "regrid.json").exists()
    if args.force or not done:
        regrid = build_tables()
        (WORK / "regrid.json").write_text(json.dumps(regrid, indent=1), encoding="utf-8")
    else:
        regrid = json.loads((WORK / "regrid.json").read_text(encoding="utf-8"))
    control = control_check(WORK / "filtered" / "cell_month_witness.parquet", WORK / "control" / "cell_month_witness.parquet")
    print("control:", control, flush=True)
    filtered = unfiltered = None
    if control["ok"]:
        filtered = run_all(WORK / "filtered", WORK)
        print(f"filtered run done ({time.time() - t0:.0f}s)", flush=True)
        unfiltered = run_all(WORK / "unfiltered", WORK)
        print(f"unfiltered run done ({time.time() - t0:.0f}s)", flush=True)
    result = compare_runs(filtered or {}, unfiltered or {}, control["ok"])
    e = entry(result, control, regrid, filtered, unfiltered)
    base = baseline_status()
    report = {"result": result, "overall_s1": s1_overall(base, result["status"]), "s1_baseline_status_from_T025": base, "control": control,
              "regridding": regrid, "filtered": filtered, "unfiltered": unfiltered}
    write_entries(e, report)
    print(result["status"], result["why"])
    for c in result["changes"]:
        print("  change:", c)
    shutil.rmtree(TMP, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
