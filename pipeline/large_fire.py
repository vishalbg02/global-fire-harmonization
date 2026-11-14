"""Diagnostic (T-015): large-fire consistency check. Not a correction, not a validation test, not a contract product.

A fire-active fine cell-day counts once however many detections or how much FRP fall on it. For each entity (country, fire region, world),
witness and month this module computes detections per cell-day (S) and FRP per cell-day (F), their level against the entity's own
reference level in the witness's calibration fit period (S_index, F_index), a descriptive flag for months far above it, and the
cross-witness consistency S_rel = S_witness / S_Aqua. Definitions and thresholds are in docs/task-prompts/T-015-large-fire.md, fixed before
the real run.

    python pipeline/large_fire.py       # writes data/interim/qa/T-015_large_fire_series.parquet and T-015_large_fire_summary.json
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / "data" / "interim" / "qa"
MIN_CELL_DAYS = 100        # a row with fewer cell-days is LOW_COUNT: shown, not judged
MIN_REF_MONTHS = 12        # judged reference months needed for a reference level
FLAG_FACTOR = 1.5          # descriptive flag LARGE_FIRE_HIGH
FLAG_FACTOR_2 = 2.0        # second view
TOP_MIN_CELL_DAYS = 1000   # rows eligible for the top list
WITNESSES = ("AQUA_MODIS", "TERRA_MODIS", "SNPP_VIIRS", "NOAA20_VIIRS")
VIIRS = ("SNPP_VIIRS", "NOAA20_VIIRS")
REFERENCE = {                                    # inclusive (year, month) bounds: the calibration fit period of each witness (T-011)
    "AQUA_MODIS": ((2012, 1), (2016, 12)),
    "TERRA_MODIS": ((2012, 1), (2016, 12)),
    "SNPP_VIIRS": ((2012, 1), (2016, 12)),
    "NOAA20_VIIRS": ((2018, 4), (2021, 12)),
}
KEYS = ["entity_type", "entity_id", "witness"]
ENTITY_TYPES = ("COUNTRY", "FIRE_REGION", "GLOBAL")


def in_reference(year: pd.Series, month: pd.Series, witness: pd.Series) -> pd.Series:
    """True for rows inside the reference period of their witness."""
    ym = year.to_numpy() * 12 + month.to_numpy() - 1
    out = np.zeros(len(ym), dtype=bool)
    for w, ((y0, m0), (y1, m1)) in REFERENCE.items():
        sel = (witness == w).to_numpy()
        out |= sel & (ym >= y0 * 12 + m0 - 1) & (ym <= y1 * 12 + m1 - 1)
    return pd.Series(out, index=year.index)


def add_indices(df: pd.DataFrame) -> pd.DataFrame:
    """S, F, status, reference levels, indices, flags and S_rel for aggregated rows (one row per entity, year, month, witness).

    Rows with cell_days == 0 have no S or F (cannot be determined). Rows below MIN_CELL_DAYS are LOW_COUNT: S and F are shown but the
    index, flag and S_rel stay empty. The reference level is the median over the judged months of the reference period, and needs at
    least MIN_REF_MONTHS of them (else NO_REFERENCE)."""
    d = df.copy()
    cd = d["cell_days"].to_numpy(dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        d["S"] = np.where(cd > 0, d["detections"] / cd, np.nan)
        d["F"] = np.where(cd > 0, d["frp_sum_mw"] / cd, np.nan)
    judged = cd >= MIN_CELL_DAYS
    d["status"] = np.where(judged, "OK", "LOW_COUNT")
    ref_rows = judged & in_reference(d["year"], d["month"], d["witness"]).to_numpy()
    r = d[ref_rows].groupby(KEYS).agg(s_ref=("S", "median"), f_ref=("F", "median"), n_ref=("S", "size")).reset_index()
    r.loc[r["n_ref"] < MIN_REF_MONTHS, ["s_ref", "f_ref"]] = np.nan
    d = d.merge(r[KEYS + ["s_ref", "f_ref"]], on=KEYS, how="left")
    d.loc[d["s_ref"].isna() & judged, "status"] = "NO_REFERENCE"
    ok = d["status"] == "OK"
    d["s_index"] = np.where(ok, d["S"] / d["s_ref"], np.nan)
    d["f_index"] = np.where(ok, d["F"] / d["f_ref"], np.nan)
    d["flag_high"] = ok & (d["s_index"] >= FLAG_FACTOR)
    d["flag_high_2x"] = ok & (d["s_index"] >= FLAG_FACTOR_2)
    aqua = d[(d["witness"] == "AQUA_MODIS") & (d["status"] != "LOW_COUNT") & d["S"].notna()]
    aqua = aqua[["entity_type", "entity_id", "year", "month", "S"]].rename(columns={"S": "s_aqua"})
    d = d.merge(aqua, on=["entity_type", "entity_id", "year", "month"], how="left")
    both = judged & d["s_aqua"].notna() & (d["witness"] != "AQUA_MODIS")
    d["s_rel"] = np.where(both, d["S"] / d["s_aqua"], np.nan)
    return d.drop(columns=["s_aqua"]).sort_values(KEYS + ["year", "month"]).reset_index(drop=True)


def aggregate(con: duckdb.DuckDBPyConnection, products: Path) -> pd.DataFrame:
    """Sums of detections, cell-days and FRP and the number of active cells per entity, year, month and witness (rows daynight = ALL).

    The small cells table is joined first and the big witness table is only read for those rows (one pass per entity type)."""
    w = str(products / "cell_month_witness.parquet").replace("\\", "/")
    c = str(products / "cells.parquet").replace("\\", "/")
    base = f"""SELECT w.year, w.month, w.witness, w.detections, w.cell_days, w.frp_sum_mw, {{k}} AS entity_id
               FROM '{c}' c JOIN '{w}' w ON w.cell_id = c.cell_id WHERE w.daynight = 'ALL' AND {{cond}}"""
    parts = []
    for etype, key, cond in (("COUNTRY", "c.country_iso3", "c.country_iso3 IS NOT NULL"),
                             ("FIRE_REGION", "c.fire_region", "c.fire_region IS NOT NULL"),
                             ("GLOBAL", "'WORLD'", "TRUE")):
        q = base.format(k=key, cond=cond)
        parts.append(con.sql(f"""SELECT '{etype}' AS entity_type, entity_id, year, month, witness,
                                        sum(detections)::BIGINT AS detections, sum(cell_days)::BIGINT AS cell_days,
                                        sum(frp_sum_mw) AS frp_sum_mw, sum((cell_days > 0)::INT)::BIGINT AS active_cells
                                 FROM ({q}) GROUP BY ALL""").df())
    return pd.concat(parts, ignore_index=True)


def summarise(d: pd.DataFrame) -> dict:
    """The summaries of task prompt section 9.9 and 9.10 from the full series."""
    g = d[d["entity_type"] == "GLOBAL"]
    by_year = (g.groupby(["witness", "year"]).apply(
        lambda x: pd.Series({"S": x["detections"].sum() / x["cell_days"].sum() if x["cell_days"].sum() > 0 else np.nan,
                             "F": x["frp_sum_mw"].sum() / x["cell_days"].sum() if x["cell_days"].sum() > 0 else np.nan,
                             "months": len(x)}), include_groups=False).reset_index())
    slopes = {}
    for wname, x in by_year.groupby("witness"):
        x = x[x["months"] >= 12]                                   # complete operating years only
        slopes[wname] = float(np.polyfit(x["year"], x["S"], 1)[0]) if len(x) >= 3 else None
    ok = d[d["status"] == "OK"]
    flagged = (ok.groupby(["entity_type", "witness"])
               .agg(judged=("S", "size"), flagged=("flag_high", "sum"), flagged_2x=("flag_high_2x", "sum")).reset_index())
    flagged["share"] = flagged["flagged"] / flagged["judged"]
    flagged["share_2x"] = flagged["flagged_2x"] / flagged["judged"]
    top = (ok[ok["flag_high"] & (ok["cell_days"] >= TOP_MIN_CELL_DAYS)].sort_values("s_index", ascending=False).head(15)
           [["entity_type", "entity_id", "witness", "year", "month", "cell_days", "S", "s_ref", "s_index", "F", "f_index"]])
    inref = in_reference(d["year"], d["month"], d["witness"])
    rel = d[d["s_rel"].notna()].copy()
    rel["in_ref"] = inref[rel.index]
    rel_glob = rel[rel["entity_type"] == "GLOBAL"].groupby(["witness", "in_ref"])["s_rel"].median().reset_index()
    rel_reg = (rel[rel["entity_type"] == "FIRE_REGION"].groupby(["entity_id", "witness", "in_ref"])["s_rel"].median().unstack("in_ref"))
    activity = ok.groupby(["flag_high"])["cell_days"].median().to_dict()
    ok_ref = in_reference(ok["year"], ok["month"], ok["witness"])
    period = (ok.assign(inside_reference=ok_ref).groupby(["entity_type", "witness", "inside_reference"])
              .agg(judged=("S", "size"), flagged=("flag_high", "sum")).reset_index())
    period["share"] = period["flagged"] / period["judged"]
    return {"global_by_year": by_year.to_dict("records"), "global_S_slope_per_year": slopes,
            "flag_counts": flagged.to_dict("records"), "flag_by_period": period.to_dict("records"), "top_flagged": top.to_dict("records"),
            "s_rel_global": rel_glob.to_dict("records"),
            "s_rel_region": _region_rows(rel_reg),
            "median_cell_days_flagged_vs_not": {str(k): float(v) for k, v in activity.items()}}


def _f(x) -> float | None:
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else float(x)


def _region_rows(rel_reg: pd.DataFrame) -> list[dict]:
    out = []
    for (region, wname), row in rel_reg.iterrows():
        out.append({"region": region, "witness": wname, "inside_reference": _f(row.get(True)), "outside_reference": _f(row.get(False))})
    return out


def run(products: Path = ROOT / "data" / "products", qa: Path = QA) -> pd.DataFrame:
    qa.mkdir(parents=True, exist_ok=True)
    tmp = ROOT / "data" / "interim" / "_tmp_T-015"
    tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        con.sql("SET memory_limit='5GB'; SET max_temp_directory_size='20GiB'; SET preserve_insertion_order=false; SET threads=4")
        con.sql(f"SET temp_directory='{tmp.as_posix()}'")
        agg = aggregate(con, products)
    finally:
        con.close()
        shutil.rmtree(tmp, ignore_errors=True)
    d = add_indices(agg)
    d.to_parquet(qa / "T-015_large_fire_series.parquet", index=False)
    summary = summarise(d)
    (qa / "T-015_large_fire_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    return d


if __name__ == "__main__":
    if sys.argv[1:] == ["summary"]:                  # recompute only the summary from the series file (light)
        _d = pd.read_parquet(QA / "T-015_large_fire_series.parquet")
        (QA / "T-015_large_fire_summary.json").write_text(json.dumps(summarise(_d), indent=1, default=str), encoding="utf-8")
        sys.exit(0)
    out = run()
    print(f"{len(out):,} rows; statuses: {out['status'].value_counts().to_dict()}", file=sys.stderr)
