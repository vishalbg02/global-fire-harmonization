"""Validation tests D1 (coverage: are the 90% intervals honest) and D2 (gaps) (T-022).

D1 (docs/VALIDATION_PLAN.md section 3): holdout 2017-2021, share of actual Aqua values inside the predicted 90% intervals; PASS when
between 80% and 97% (locked at G1, D-028). It reuses pipeline/holdout.py (units, predictions, variances, coverage). Reading of the
criterion [ASSUMPTION]: "All fire regions" names the population, the criterion is ONE share, so the status is decided on the share
pooled over all fire-region day/night units. Per-region shares, night units alone, the day+night totals, the 50% interval and the
country level are reported as supplementary entries; the strict per-region reading is reported too, as its own entry.

D2: every month without a complete witness has no estimate (estimate level, runs on the real products now) and every row without
an estimate is CANNOT_DETERMINE with OUTAGE (verdict level, needs the T-014 table: NOT_RUN until then).

    python pipeline/validation_d.py                              # D1 and D2 at estimate level; writes data/interim/qa/T-022_validation_entries.json
    python pipeline/validation_d.py verdicts <entity_month.parquet>   # D2 at verdict level, once T-014 has produced the table
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harmonize as hz
import holdout as ho

ROOT = Path(__file__).resolve().parents[1]
TARGET = ho.COVERAGE_TARGET            # (0.80, 0.97), locked (D-028)
MIN_UNITS = 30                         # a group with fewer units is not judged on its own (the same rule as the T-012 report)
EPS = 1e-12
DETERMINABLE = ("ABOVE_NORMAL", "BELOW_NORMAL", "WITHIN_NORMAL", "NO_DETECTED_ACTIVITY")
QA = ROOT / "data" / "interim" / "qa"


# ------------------------------------------------------------------------------------------------ D1
def status_from_coverage(cov: float, units: int, target: tuple[float, float] = TARGET, min_units: int = 1) -> str:
    """PASS inside [lo, hi] (both ends included), FAIL outside, INCONCLUSIVE with no coverage or fewer than `min_units` units."""
    if units < min_units or cov is None or not np.isfinite(cov):
        return "INCONCLUSIVE"
    return "PASS" if target[0] - EPS <= cov <= target[1] + EPS else "FAIL"


def coverage_pair(x: pd.DataFrame, var_col: str = "var_ours") -> dict:
    """Units and coverage of the 90% and 50% intervals of a set of units (columns actual, pred_ours and `var_col`)."""
    if len(x) == 0:
        return {"units": 0, "coverage_90": None, "coverage_50": None}
    return {"units": len(x), "coverage_90": ho.coverage(x.actual, x.pred_ours, x[var_col]),
            "coverage_50": ho.coverage(x.actual, x.pred_ours, x[var_col], z=ho.Z50)}


def by_region(x: pd.DataFrame, var_col: str = "var_ours", min_units: int = MIN_UNITS) -> dict:
    """Per entity: units, both coverages and the status of the 90% coverage against the target (INCONCLUSIVE below `min_units`)."""
    out = {}
    for eid, g in x.groupby("entity_id"):
        p = coverage_pair(g, var_col)
        p["status"] = status_from_coverage(p["coverage_90"], p["units"], min_units=min_units)
        out[str(eid)] = p
    return out


def regions_inside(per: dict) -> dict:
    """How many of the judged groups (status PASS or FAIL) are inside the target, and which are not."""
    judged = {k: v for k, v in per.items() if v["status"] in ("PASS", "FAIL")}
    out_ = sorted(k for k, v in judged.items() if v["status"] == "FAIL")
    return {"judged": len(judged), "inside": len(judged) - len(out_), "outside": out_,
            "min": min((v["coverage_90"] for v in judged.values()), default=None),
            "max": max((v["coverage_90"] for v in judged.values()), default=None)}


def d1_level(u: pd.DataFrame, t: pd.DataFrame, var_col: str = "var_ours") -> dict:
    """Everything D1 reports for one entity level: pooled D/N units (the status), day, night, totals, per group."""
    pooled = coverage_pair(u, var_col)
    pooled["status"] = status_from_coverage(pooled["coverage_90"], pooled["units"])
    out = {"pooled": pooled, "by_daynight": {}, "total": coverage_pair(t, var_col)}
    for dn in ("D", "N"):
        p = coverage_pair(u[u.daynight == dn], var_col)
        p["status"] = status_from_coverage(p["coverage_90"], p["units"])
        out["by_daynight"][dn] = p
    out["total"]["status"] = status_from_coverage(out["total"]["coverage_90"], out["total"]["units"])
    out["by_group_daynight_units"] = by_region(u, var_col)
    out["by_group_total"] = by_region(t, var_col)
    out["inside_daynight_units"] = regions_inside(out["by_group_daynight_units"])
    out["inside_total"] = regions_inside(out["by_group_total"])
    return out


def build_units(agg: pd.DataFrame, glob: pd.DataFrame, entity_type: str, min_cell_days: float = ho.MIN_CELL_DAYS) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The D/N units with predictions and the day+night totals for one entity type (the T-012 construction, unchanged)."""
    ratios = ho.fit_global_ratios(glob)
    u = ho.add_predictions(ho.units_from_agg(agg[agg.entity_type == entity_type], min_cell_days), ratios)
    return u, ho.total_units(u)


def d1_entries(region: dict, country: dict, widening: dict | None = None) -> list[dict]:
    """Contract section 6 entries for D1 from the results of `d1_level` for fire regions and countries."""
    crit = "Holdout 2017-2021: share of actual Aqua values inside the predicted 90% intervals"
    thr = "between 80% and 97% (locked at G1, D-028)"
    r = region
    ins, ins_t = r["inside_daynight_units"], r["inside_total"]
    n_night = r["by_daynight"]["N"]
    entries = [
        {"test_id": "D1-REGIONS", "family": "D", "title": "Uncertainty honest (coverage), pooled over all fire regions",
         "case": "Fire-region-months 2017-2021, Aqua against converted S-NPP, day/night units with at least 20 Aqua cell-days",
         "criterion": crit + " (pooled over all fire-region day/night units)", "threshold": thr,
         "measured": {"units": r["pooled"]["units"], "coverage_90": r["pooled"]["coverage_90"], "coverage_50": r["pooled"]["coverage_50"],
                      "day": r["by_daynight"]["D"]["coverage_90"], "night": n_night["coverage_90"],
                      "day_night_total": r["total"]["coverage_90"], "widening_factor_reported_not_applied": widening},
         "status": r["pooled"]["status"],
         "notes": "Pooled reading of the criterion [ASSUMPTION]. Not a clean out-of-sample test: phi and kappa were fitted on fit-period "
                  "months and the NOAA-20 pair overlaps these months on the Aqua side. No widening factor applied (Lead decision). "
                  "The 50% interval covers less than 50%: the intervals are slightly too narrow in the middle. Known limits in D1-NIGHT and D1-REGIONS-EACH (risk S16)."},
        {"test_id": "D1-REGIONS-TOTAL", "family": "D", "title": "Coverage, fire-region day+night totals (supplementary)",
         "case": "Fire-region-months 2017-2021, day+night total", "criterion": crit + " (day+night totals)", "threshold": thr,
         "measured": {"units": r["total"]["units"], "coverage_90": r["total"]["coverage_90"], "coverage_50": r["total"]["coverage_50"],
                      "regions_judged": ins_t["judged"], "regions_inside": ins_t["inside"], "regions_outside": ins_t["outside"]},
         "status": r["total"]["status"], "notes": "Supplementary; the status uses the same range as the locked criterion."},
        {"test_id": "D1-NIGHT", "family": "D", "title": "Coverage, night units alone, fire regions (supplementary, known limit)",
         "case": "Fire-region-months 2017-2021, night units", "criterion": crit + " (night units only)", "threshold": thr,
         "measured": {"units": n_night["units"], "coverage_90": n_night["coverage_90"], "coverage_50": n_night["coverage_50"]},
         "status": n_night["status"],
         "notes": "Not part of the locked criterion; reported because night intervals are too narrow. Recorded as a known limit (risk S16)."},
        {"test_id": "D1-REGIONS-EACH", "family": "D", "title": "Coverage in each fire region separately (supplementary, stricter reading)",
         "case": f"Fire regions with at least {MIN_UNITS} D/N units, 2017-2021",
         "criterion": "Every judged fire region has 90% coverage inside 80% to 97%",
         "threshold": "each judged region between 80% and 97% (a stricter reading than the locked criterion)",
         "measured": {"regions_judged": ins["judged"], "regions_inside": ins["inside"], "regions_outside": ins["outside"],
                      "lowest": ins["min"], "highest": ins["max"]},
         "status": "PASS" if ins["judged"] and not ins["outside"] else ("FAIL" if ins["judged"] else "INCONCLUSIVE"),
         "notes": "Not the locked criterion. Shown so the pooled PASS cannot hide that regions are below 80%."},
        {"test_id": "D1-COUNTRIES", "family": "D", "title": "Coverage, pooled over all countries (supplementary)",
         "case": "Country-months 2017-2021, day/night units with at least 20 Aqua cell-days",
         "criterion": crit + " (pooled over country day/night units)", "threshold": thr,
         "measured": {"units": country["pooled"]["units"], "coverage_90": country["pooled"]["coverage_90"],
                      "coverage_50": country["pooled"]["coverage_50"], "day": country["by_daynight"]["D"]["coverage_90"],
                      "night": country["by_daynight"]["N"]["coverage_90"], "day_night_total": country["total"]["coverage_90"],
                      "countries_judged": country["inside_daynight_units"]["judged"], "countries_inside": country["inside_daynight_units"]["inside"]},
         "status": country["pooled"]["status"], "notes": "Supplementary: the criterion names fire regions; countries are the T-012 second level."},
    ]
    return entries


# ------------------------------------------------------------------------------------------------ D2, estimate level
def _usable(g: pd.DataFrame, aqua_from: dict) -> dict[str, set[str]]:
    """For one entity-month: per day/night part present, the witnesses that may count (complete month, Aqua part not excluded)."""
    year, month = int(g.year.iloc[0]), int(g.month.iloc[0])
    excluded = hz._excluded_daynights(aqua_from, year, month)
    out: dict[str, set[str]] = {}
    for dn, gd in g.groupby("daynight"):
        ok = {w for w, c in zip(gd.witness, gd.complete, strict=True) if bool(c) and w in hz.WITNESSES}
        if dn in excluded:
            ok.discard("AQUA_MODIS")
        out[str(dn)] = ok
    return out


def check_estimates(agg: pd.DataFrame, records: list[dict], aqua_from: dict | None = None, sample: int = 10) -> dict:
    """D2 at estimate level. `agg` is harmonize.aggregate() output and `records` the records of harmonize.records_from() for it.

    Expected: a month has an estimate if and only if every day/night part with data has at least one witness that counts (complete
    month). Violations: an estimate without such a witness; no estimate although every part has one; an estimate that lists a
    witness with no complete row in the month. Also counts the months in which a witness was partial."""
    aqua_from = hz.AQUA_FROM if aqua_from is None else aqua_from
    recs = {(r["entity_type"], r["entity_id"], r["year"], r["month"]): r for r in records}
    est_without, missing_despite, uses_partial = [], [], []
    n, expected_none, partial_months = 0, 0, 0
    for key, g in agg.groupby(["entity_type", "entity_id", "year", "month"], sort=True):
        k = (key[0], key[1], int(key[2]), int(key[3]))
        r = recs.get(k)
        if r is None:
            continue
        n += 1
        usable = _usable(g, aqua_from)
        expect_estimate = bool(usable) and all(len(v) > 0 for v in usable.values())
        has_estimate = r["estimate"] is not None
        if not expect_estimate:
            expected_none += 1
        if has_estimate and not expect_estimate:
            est_without.append(k)
        if expect_estimate and not has_estimate:
            missing_despite.append(k)
        if not bool(g[g.witness.isin(hz.WITNESSES)].complete.all()):
            partial_months += 1
        for w in r["witnesses_used"]:
            rows = g[g.witness == w]
            if rows.empty or not bool(rows.complete.any()):
                uses_partial.append((*k, w))
    viol = len(est_without) + len(missing_despite) + len(uses_partial)
    return {"entity_months": n, "months_expected_without_estimate": expected_none, "months_with_a_partial_witness": partial_months,
            "estimate_without_usable_witness": len(est_without), "missing_estimate_despite_usable_witness": len(missing_despite),
            "uses_witness_without_complete_month": len(uses_partial), "violations": viol,
            "examples": {"estimate_without_usable_witness": est_without[:sample], "missing_estimate": missing_despite[:sample],
                         "uses_partial": uses_partial[:sample]}}


def perturb_incomplete(agg: pd.DataFrame, factor: float = 1000.0) -> pd.DataFrame:
    """A copy of `agg` in which every row of an incomplete witness-month is made absurd (counts and variances times `factor`)."""
    out = agg.copy()
    bad = ~out.complete.astype(bool)
    for c in ("raw", "e", "vc", "vr"):
        out.loc[bad, c] = out.loc[bad, c] * factor
    return out


def perturbation_check(agg: pd.DataFrame, n_cells: dict, aqua_from: dict | None = None) -> dict:
    """D2: partial witnesses must not enter the estimate. Make the incomplete rows absurd and compare the estimates, sd, witnesses
    used and disagreement scale of the entity-months that have an incomplete row: they must not move."""
    keys = ["entity_type", "entity_id", "year", "month"]
    partial = agg[~agg.complete.astype(bool)][keys].drop_duplicates()
    sub = agg.merge(partial, on=keys)
    base = pd.DataFrame(hz.records_from(sub, n_cells, aqua_from))
    pert = pd.DataFrame(hz.records_from(perturb_incomplete(sub), n_cells, aqua_from))
    if base.empty:
        return {"entity_months_with_incomplete_row": 0, "changed": 0}
    cols = ["estimate", "sd", "disagreement_scale"]
    same = np.ones(len(base), dtype=bool)
    for c in cols:
        a, b = base[c].astype(float).to_numpy(), pert[c].astype(float).to_numpy()
        same &= (np.isnan(a) & np.isnan(b)) | np.isclose(a, b, rtol=1e-9, atol=1e-9, equal_nan=False)
    same &= (base.witnesses_used.map(tuple) == pert.witnesses_used.map(tuple)).to_numpy()
    return {"entity_months_with_incomplete_row": len(base), "changed": int((~same).sum()),
            "with_estimate": int(base.estimate.notna().sum()), "without_estimate": int(base.estimate.isna().sum())}


def d2_estimate_status(chk: dict, pert: dict) -> str:
    if chk["entity_months"] == 0 or (chk["months_expected_without_estimate"] == 0 and chk["months_with_a_partial_witness"] == 0):
        return "INCONCLUSIVE"                  # no gap month was tested: nothing to show
    return "PASS" if chk["violations"] == 0 and pert.get("changed", 0) == 0 else "FAIL"


# ------------------------------------------------------------------------------------------------ D2, verdict level
def _codes(x) -> list[str]:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return []
    if isinstance(x, str):
        try:
            return list(json.loads(x))
        except ValueError:
            return [x]
    return [str(c) for c in x]


def check_verdicts(em: pd.DataFrame) -> dict:
    """D2 at verdict level on an `entity_month`-shaped table (DATA_CONTRACT section 4; also works on the cell-level table).

    Rules (D-028 section 3): a row without an estimate is CANNOT_DETERMINE with OUTAGE; OUTAGE appears only without an estimate;
    INSUFFICIENT_BASELINE and WIDE_INTERVAL rows are CANNOT_DETERMINE (NO_DETECTED_ACTIVITY has an estimate of 0 and no such code).
    Reports the share of rows with a determinable verdict."""
    codes = em.reason_codes.map(_codes)
    no_est = em.estimate.isna()
    verdict = em.verdict
    cannot = verdict == "CANNOT_DETERMINE"
    has = lambda c: codes.map(lambda x: c in x)
    outage = has("OUTAGE")
    bad_outage = no_est & ~(cannot & outage)
    bad_code = outage & ~no_est
    bad_insufficient = (has("INSUFFICIENT_BASELINE") | has("WIDE_INTERVAL")) & ~cannot
    bad_nda = (verdict == "NO_DETECTED_ACTIVITY") & ~((em.estimate == 0) & ~no_est)
    n = len(em)
    determinable = verdict.isin(DETERMINABLE)
    return {"rows": n, "rows_without_estimate": int(no_est.sum()), "rows_with_outage_code": int(outage.sum()),
            "outage_rows_ok": int((no_est & cannot & outage).sum()),
            "violations": {"no_estimate_but_not_cannot_determine_outage": int(bad_outage.sum()),
                           "outage_code_with_an_estimate": int(bad_code.sum()),
                           "insufficient_or_wide_but_determinable": int(bad_insufficient.sum()),
                           "no_detected_activity_without_zero_estimate": int(bad_nda.sum())},
            "determinable_rows": int(determinable.sum()), "determinable_share": float(determinable.mean()) if n else None}


def d2_verdict_status(res: dict) -> str:
    """PASS: at least one outage row was checked and no rule is broken. INCONCLUSIVE: no row without an estimate to check."""
    if res["rows_without_estimate"] == 0:
        return "INCONCLUSIVE"
    cell = sum(v["outage_rule_violations"] for v in res.get("cell_level", {}).values())
    return "FAIL" if sum(res["violations"].values()) + cell else "PASS"


def d2_entries(chk: dict, pert: dict, verdict_res: dict | None = None) -> list[dict]:
    measured = {**{k: v for k, v in chk.items() if k != "examples"}, "perturbation": pert}
    entries = [{"test_id": "D2-ESTIMATES", "family": "D", "title": "Gaps: outage months have no estimate (estimate level, a part of D2)",
                "case": "Every country, fire region and the globe, every month 2002-07 to the latest",
                "criterion": "A month without a complete witness has no estimate; a partial witness does not enter an estimate",
                "threshold": "100% (0 violations)", "measured": measured, "status": d2_estimate_status(chk, pert),
                "notes": "Estimate-level part only; the verdict part needs T-014 (D2-VERDICTS). Examples of violations, if any, are in the run output."}]
    if verdict_res is None:
        entries.append({"test_id": "D2-VERDICTS", "family": "D", "title": "Gaps and insufficiency: verdicts CANNOT_DETERMINE with OUTAGE",
                        "case": "entity_month table of T-014", "criterion": "Outage months and cells below the data thresholds: 100% CANNOT_DETERMINE / NO_DETECTED_ACTIVITY; report the share of land cells with a determinable verdict",
                        "threshold": "100%", "measured": {"rows_checked": None, "determinable_share": None}, "status": "NOT_RUN",
                        "notes": "NOT_RUN: the baseline, probabilities and verdicts (T-014) are not merged. Run `python pipeline/validation_d.py verdicts <entity_month.parquet>` after T-014."})
    else:
        entries.append({"test_id": "D2-VERDICTS", "family": "D", "title": "Gaps and insufficiency: verdicts CANNOT_DETERMINE with OUTAGE",
                        "case": "entity_month table of T-014", "criterion": "Outage months and cells below the data thresholds: 100% CANNOT_DETERMINE / NO_DETECTED_ACTIVITY; report the share determinable",
                        "threshold": "100%", "measured": verdict_res, "status": d2_verdict_status(verdict_res), "notes": ""})
    return entries


# ------------------------------------------------------------------------------------------------ data access (thin)
def read_estimate_inputs(paths: hz.Paths | None = None) -> tuple[pd.DataFrame, dict]:
    """harmonize.aggregate() for every country, fire region and the globe, all months, and the cell counts per entity."""
    paths = paths or hz.Paths()
    paths.tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{paths.tmp.as_posix()}'")
    con.execute("SET memory_limit='4GB'")
    cells = f"read_parquet('{(paths.products / 'cells.parquet').as_posix()}')"
    con.execute(f"""CREATE TEMP TABLE members AS
        SELECT 'REGION' AS entity_type, fire_region AS entity_id, fire_region AS entity_name, cell_id FROM {cells} WHERE fire_region IS NOT NULL
        UNION ALL SELECT 'COUNTRY', country_iso3, country_iso3, cell_id FROM {cells} WHERE country_iso3 IS NOT NULL
        UNION ALL SELECT 'GLOBAL', 'WORLD', 'World', cell_id FROM {cells}""")
    counts = {(a, b): int(c) for a, b, c in con.execute("SELECT entity_type, entity_id, count(*) FROM members GROUP BY 1, 2").fetchall()}
    return hz.aggregate(con, paths, "members", None), counts


def run_d1(paths: hz.Paths | None = None) -> tuple[dict, dict, dict]:
    agg, glob, _ = ho.read_inputs(paths)
    res = {}
    for et in ("REGION", "COUNTRY"):
        u, t = build_units(agg, glob, et)
        res[et] = d1_level(u, t)
        if et == "REGION":
            early = u[u.year < ho.SPLIT_YEAR]
            c90 = ho.widening_factor(early.actual, early.pred_ours, early.var_ours)
            late = u[u.year >= ho.SPLIT_YEAR]
            widening = {"fitted_on": "2017-2018 only", "c_for_90": c90, "applied": False,
                        "coverage_2019_2021_unchanged": ho.coverage(late.actual, late.pred_ours, late.var_ours),
                        "coverage_2019_2021_with_c": ho.coverage(late.actual, late.pred_ours, late.var_ours, c=c90)}
    return res["REGION"], res["COUNTRY"], widening


def run(paths: hz.Paths | None = None) -> dict:
    paths = paths or hz.Paths()
    region, country, widening = run_d1(paths)
    agg, counts = read_estimate_inputs(paths)
    recs = hz.records_from(agg, counts)
    chk = check_estimates(agg, recs)
    pert = perturbation_check(agg, counts)
    entries = d1_entries(region, country, widening) + d2_entries(chk, pert)
    QA.mkdir(parents=True, exist_ok=True)
    (QA / "T-022_validation_entries.json").write_text(json.dumps(
        {"method_version": hz.METHOD_VERSION, "synthetic": False, "tests": entries,
         "details": {"d1_regions": region, "d1_countries": country, "d2_examples": chk["examples"]}}, indent=1, default=str), encoding="utf-8")
    return {"entries": entries, "d1_regions": region, "d1_countries": country, "d2": chk, "perturbation": pert}


def cell_determinable_shares(harmonized: str | Path, cells: str | Path) -> dict:
    """D2: the share of cell-months and of cells with a determinable verdict, for all cells and for land cells (a country_iso3 in cells).

    `normal`: ABOVE, BELOW or WITHIN_NORMAL. `not_cannot_determine`: any verdict but CANNOT_DETERMINE (includes NO_DETECTED_ACTIVITY).
    Also the outage rule on the cell table: a row without an estimate must be CANNOT_DETERMINE with OUTAGE."""
    con = duckdb.connect()
    h, c = f"read_parquet('{Path(harmonized).as_posix()}')", f"read_parquet('{Path(cells).as_posix()}')"
    norm = "verdict IN ('ABOVE_NORMAL', 'BELOW_NORMAL', 'WITHIN_NORMAL')"
    df = con.execute(f"""WITH j AS (SELECT h.cell_id, h.verdict, h.estimate, h.reason_codes, (c.country_iso3 IS NOT NULL) AS land
                                    FROM {h} h JOIN {c} c USING (cell_id)),
        pc AS (SELECT cell_id, land, max(({norm})::int) AS any_norm, max((verdict <> 'CANNOT_DETERMINE')::int) AS any_det FROM j GROUP BY 1, 2)
        SELECT 'all' AS scope, count(*) AS cells, avg(any_norm) AS cells_any_normal, avg(any_det) AS cells_any_not_cd,
               NULL::DOUBLE AS months, NULL::DOUBLE AS m_normal, NULL::DOUBLE AS m_not_cd, NULL::DOUBLE AS m_noest, NULL::DOUBLE AS m_bad FROM pc
        UNION ALL
        SELECT 'land', count(*), avg(any_norm), avg(any_det), NULL, NULL, NULL, NULL, NULL FROM pc WHERE land""").df()
    mm = con.execute(f"""WITH j AS (SELECT h.verdict, h.estimate, h.reason_codes, (c.country_iso3 IS NOT NULL) AS land
                                    FROM {h} h JOIN {c} c USING (cell_id))
        SELECT land, count(*) AS months, avg(({norm})::int) AS m_normal, avg((verdict <> 'CANNOT_DETERMINE')::int) AS m_not_cd,
               sum((estimate IS NULL)::int) AS m_noest,
               sum((estimate IS NULL AND NOT (verdict = 'CANNOT_DETERMINE' AND list_contains(reason_codes, 'OUTAGE')))::int) AS m_bad,
               sum((list_contains(reason_codes, 'OUTAGE') AND estimate IS NOT NULL)::int) AS outage_with_estimate
        FROM j GROUP BY land""").df()
    out: dict = {}
    for scope, sel in (("all", mm), ("land", mm[mm.land])):
        n = float(sel.months.sum())
        out[scope] = {"cell_months": int(n), "cells": int(df[df.scope == scope].cells.iloc[0]),
                      "cell_months_normal_share": float((sel.m_normal * sel.months).sum() / n),
                      "cell_months_not_cannot_determine_share": float((sel.m_not_cd * sel.months).sum() / n),
                      "cells_with_any_normal_verdict": float(df[df.scope == scope].cells_any_normal.iloc[0]),
                      "cells_with_any_not_cd_verdict": float(df[df.scope == scope].cells_any_not_cd.iloc[0]),
                      "cell_months_without_estimate": int(sel.m_noest.sum()),
                      "outage_rule_violations": int(sel.m_bad.sum() + sel.outage_with_estimate.sum())}
    return out


def run_verdicts(path: str) -> dict:
    em = pd.read_parquet(path)
    res = check_verdicts(em)
    prod = Path(path).parent
    if (prod / "cell_month_harmonized.parquet").exists() and (prod / "cells.parquet").exists():
        res["cell_level"] = cell_determinable_shares(prod / "cell_month_harmonized.parquet", prod / "cells.parquet")
    entries = d2_entries({"entity_months": 0, "months_expected_without_estimate": 0, "months_with_a_partial_witness": 0, "violations": 0}, {}, res)
    out = QA / "T-022_verdict_check.json"
    QA.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"entry": entries[-1], "result": res}, indent=1, default=str), encoding="utf-8")
    merged = _merge_entries(entries[-1])
    return {"entry": entries[-1], "d2_overall": merged, "result": res}


def d2_overall(estimates: dict, verdicts: dict) -> dict:
    """The D2 entry of the plan: PASS only when both halves PASS; FAIL if either fails; otherwise the weaker of the two."""
    st = {estimates["status"], verdicts["status"]}
    status = "FAIL" if "FAIL" in st else ("NOT_RUN" if "NOT_RUN" in st else ("INCONCLUSIVE" if "INCONCLUSIVE" in st else "PASS"))
    return {"test_id": "D2", "family": "D", "title": "Gaps and insufficiency", "case": "Outage months; cells below the data thresholds",
            "criterion": "100% shown as CANNOT_DETERMINE / NO_DETECTED_ACTIVITY; report % of land cells with a determinable verdict",
            "threshold": "100%", "measured": {"estimates": estimates["status"], "verdicts": verdicts["status"]}, "status": status,
            "notes": "Both halves: D2-ESTIMATES (no estimate without a complete witness) and D2-VERDICTS (CANNOT_DETERMINE with OUTAGE)."}


def _merge_entries(verdict_entry: dict) -> dict | None:
    """Replace D2-VERDICTS in the entries file of the main run and add the D2 entry; returns the D2 entry (None without the file)."""
    f = QA / "T-022_validation_entries.json"
    if not f.exists():
        return None
    doc = json.loads(f.read_text(encoding="utf-8"))
    tests = [t for t in doc["tests"] if t["test_id"] not in ("D2-VERDICTS", "D2")]
    est = next(t for t in tests if t["test_id"] == "D2-ESTIMATES")
    overall = d2_overall(est, verdict_entry)
    doc["tests"] = [*tests, verdict_entry, overall]
    f.write_text(json.dumps(doc, indent=1, default=str), encoding="utf-8")
    return overall


if __name__ == "__main__":
    if sys.argv[1:2] == ["verdicts"]:
        print(json.dumps(run_verdicts(sys.argv[2]), indent=1, default=str))
    else:
        out = run()
        for e in out["entries"]:
            m = e["measured"]
            print(e["test_id"], e["status"], {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items() if not isinstance(v, (dict, list))})
