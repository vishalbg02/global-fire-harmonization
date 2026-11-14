"""Check a folder of products against docs/DATA_CONTRACT.md (fixtures 0.1.0 or 0.1.1; real products 0.1.1).

Checks field names and types, enumerations, key uniqueness, null rules and the
SYNTHETIC labelling. Returns a list of problems (empty means the folder conforms).

    python pipeline/contract_check.py                    # data/fixtures/v0.1.0
    python pipeline/contract_check.py path/to/products
    python pipeline/contract_check.py path/to/products --real    # real products: synthetic must be false (T-014a)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = ROOT / "data" / "fixtures" / "v0.1.0"

ENUMS = {
    "witness": {"AQUA_MODIS", "TERRA_MODIS", "SNPP_VIIRS", "NOAA20_VIIRS", "NOAA21_VIIRS"},
    "daynight": {"D", "N", "ALL"},
    "data_level": {"SP", "NRT", "MIXED"},
    "verdict": {"ABOVE_NORMAL", "BELOW_NORMAL", "WITHIN_NORMAL", "CANNOT_DETERMINE", "NO_DETECTED_ACTIVITY"},
    "reason_code": {"OUTAGE", "INSUFFICIENT_BASELINE", "INSUFFICIENT_OVERLAP", "WITNESS_DISAGREEMENT", "WIDE_INTERVAL",
                    "PROVISIONAL_NRT", "AQUA_DRIFT_ERA", "SINGLE_WITNESS", "POOLED_CALIBRATION", "DIURNAL_CAVEAT",
                    "NOT_HARMONIZED"},
    "entity_type": {"CELL", "COUNTRY", "CONTINENT", "GLOBAL", "CUSTOM"},
    "pooling_level": {"LOCAL", "REGION", "GLOBAL"},
    "test_status": {"PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN"},
    "season": {"DJF", "MAM", "JJA", "SON"},
}

STR, INT, FLT, LST = "string", "int", "float", "list<string>"
# field -> (type, nullable)
HARM_VALUES = {
    "estimate": (FLT, True), "ci90_low": (FLT, True), "ci90_high": (FLT, True), "sd": (FLT, True),
    "raw_combined_cell_days": (INT, False), "witnesses_used": (LST, False), "n_witnesses": (INT, False),
    "disagreement_scale": (FLT, True), "baseline_median": (FLT, True), "baseline_p25": (FLT, True),
    "baseline_p75": (FLT, True), "pct_of_normal": (FLT, True), "p_above": (FLT, True), "p_below": (FLT, True),
    "p_within": (FLT, True), "verdict": (STR, False), "reason_codes": (LST, False), "data_level": (STR, False),
    "method_version": (STR, False),
}
SPEC = {
    "cells": {
        "cell_id": (STR, False), "lat_min": (FLT, False), "lat_max": (FLT, False), "lon_min": (FLT, False),
        "lon_max": (FLT, False), "lat_c": (FLT, False), "lon_c": (FLT, False), "area_km2": (FLT, False),
        "country_iso3": (STR, True), "continent": (STR, True), "fire_region": (STR, False), "stratum_id": (STR, False),
    },
    "cell_month_witness": {
        "cell_id": (STR, False), "year": (INT, False), "month": (INT, False), "witness": (STR, False),
        "daynight": (STR, False), "detections": (INT, False), "cell_days": (INT, False), "frp_sum_mw": (FLT, False),
        "days_available": (INT, False), "days_in_month": (INT, False), "data_level": (STR, False),
    },
    "cell_month_harmonized": {"cell_id": (STR, False), "year": (INT, False), "month": (INT, False), **HARM_VALUES},
    "entity_month": {
        "entity_type": (STR, False), "entity_id": (STR, False), "entity_name": (STR, False),
        "year": (INT, False), "month": (INT, False), **HARM_VALUES, "n_cells": (INT, False), "raw_by_witness": (STR, False),
    },
    "calibration": {
        "stratum_id": (STR, False), "witness": (STR, False), "daynight": (STR, False), "season": (STR, False),
        "ratio": (FLT, False), "ratio_sd": (FLT, False), "n_overlap_months": (INT, False), "fit_period": (STR, False),
        "pooling_level": (STR, False),
    },
}
KEYS = {
    "cells": ["cell_id"],
    "cell_month_witness": ["cell_id", "year", "month", "witness", "daynight"],
    "cell_month_harmonized": ["cell_id", "year", "month"],
    "entity_month": ["entity_type", "entity_id", "year", "month"],
    "calibration": ["stratum_id", "witness", "daynight", "season"],
}
CELL_ID = re.compile(r"^g\d{3}_r\d{4}_c\d{4}$")
MONTH_STR = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def _type_ok(arrow_type: pa.DataType, want: str) -> bool:
    return {
        STR: pa.types.is_string(arrow_type) or pa.types.is_large_string(arrow_type),
        INT: pa.types.is_integer(arrow_type),
        FLT: pa.types.is_floating(arrow_type),
        LST: pa.types.is_list(arrow_type) and pa.types.is_string(arrow_type.value_type),
    }[want]


def check_table(name: str, path: Path, errors: list[str]) -> pd.DataFrame | None:
    if not path.exists():
        errors.append(f"{name}: file {path.name} is missing")
        return None
    table = pq.read_table(path)
    spec = SPEC[name]
    have = {f.name: f.type for f in table.schema}
    for col, (want, nullable) in spec.items():
        if col not in have:
            errors.append(f"{name}: missing field {col}")
        elif not _type_ok(have[col], want):
            errors.append(f"{name}.{col}: type {have[col]} is not {want}")
        elif not nullable and table.column(col).null_count:
            errors.append(f"{name}.{col}: {table.column(col).null_count} nulls in a non-nullable field")
    for col in have:
        if col not in spec:
            errors.append(f"{name}: unexpected field {col}")
    df = table.to_pandas()
    keys = KEYS[name]
    if all(k in df for k in keys) and df.duplicated(keys).any():
        errors.append(f"{name}: duplicate keys {keys}")
    return df


def _enum(errors, name, col, series, allowed):
    bad = set(series.dropna().unique()) - allowed
    if bad:
        errors.append(f"{name}.{col}: values outside the enumeration: {sorted(bad)}")


def _enum_list(errors, name, col, series, allowed):
    bad = {v for row in series for v in row} - allowed
    if bad:
        errors.append(f"{name}.{col}: values outside the enumeration: {sorted(bad)}")


def check_harmonized_rows(name: str, df: pd.DataFrame, errors: list[str], real: bool = False) -> None:
    _enum(errors, name, "verdict", df.verdict, ENUMS["verdict"])
    _enum(errors, name, "data_level", df.data_level, ENUMS["data_level"])
    _enum_list(errors, name, "witnesses_used", df.witnesses_used, ENUMS["witness"])
    _enum_list(errors, name, "reason_codes", df.reason_codes, ENUMS["reason_code"])
    if not df.month.between(1, 12).all():
        errors.append(f"{name}: month outside 1-12")
    if (df.n_witnesses != df.witnesses_used.map(len)).any():
        errors.append(f"{name}: n_witnesses does not match witnesses_used")
    null_est = df.estimate.isna()
    if (null_est != (df.n_witnesses == 0)).any():
        errors.append(f"{name}: estimate must be null exactly when no witness had usable data")
    for col in ("ci90_low", "ci90_high", "sd"):
        if (df[col].isna() != null_est).any():
            errors.append(f"{name}.{col}: null pattern differs from estimate")
    ok = ~null_est
    if ((df.ci90_low[ok] > df.estimate[ok]) | (df.estimate[ok] > df.ci90_high[ok])).any():
        errors.append(f"{name}: estimate outside its 90% interval")
    if (df.estimate[ok] < 0).any() or (df.sd[ok] < 0).any():
        errors.append(f"{name}: negative estimate or sd")
    for col in ("p_above", "p_below", "p_within"):
        v = df[col].dropna()
        if ((v < 0) | (v > 1)).any():
            errors.append(f"{name}.{col}: probability outside [0, 1]")
    both = df[["p_above", "p_below", "p_within"]].dropna()
    if ((both.sum(axis=1) - 1).abs() > 0.01).any():
        errors.append(f"{name}: probabilities do not sum to 1")
    scale = df.disagreement_scale.dropna()
    if (scale < 1).any():
        errors.append(f"{name}: disagreement_scale below 1")
    if df.disagreement_scale[df.n_witnesses < 2].notna().any():
        errors.append(f"{name}: disagreement_scale set with fewer than 2 witnesses")
    pct_should_be_null = df.baseline_median.isna() | (df.baseline_median == 0) | null_est
    if (df.pct_of_normal.isna() != pct_should_be_null).any():
        errors.append(f"{name}: pct_of_normal must be null exactly when the baseline median is 0 or null (or no estimate)")
    nd = df.verdict == "NO_DETECTED_ACTIVITY"
    if (df.raw_combined_cell_days[nd] != 0).any():
        errors.append(f"{name}: NO_DETECTED_ACTIVITY with detections present")
    if (df.verdict[null_est] != "CANNOT_DETERMINE").any():
        errors.append(f"{name}: a null estimate must have verdict CANNOT_DETERMINE")
    if real:  # D-026: a raw-only row must say so
        raw_only = df.method_version.str.endswith("-raw-only")
        wrong = raw_only & ~df.reason_codes.map(lambda r: list(r) == ["NOT_HARMONIZED"])
        if wrong.any():
            errors.append(f"{name}: {int(wrong.sum())} raw-only rows do not have reason_codes = [NOT_HARMONIZED]")
        if (~raw_only & df.reason_codes.map(lambda r: "NOT_HARMONIZED" in list(r))).any():
            errors.append(f"{name}: NOT_HARMONIZED on rows that are not raw-only")
    if df[["baseline_median", "baseline_p25", "baseline_p75"]].isna().any(axis=1).ne(df.baseline_median.isna()).any():
        errors.append(f"{name}: baseline fields are not null together")
    if (df.verdict[df.baseline_median.isna()] != "CANNOT_DETERMINE").any():
        errors.append(f"{name}: no baseline must give CANNOT_DETERMINE")


def _guard(label: str, errors: list[str], fn) -> None:
    """Run one group of checks; a missing field is reported, never a crash."""
    try:
        fn()
    except (KeyError, AttributeError) as e:
        errors.append(f"{label}: checks skipped because a required field is missing or unreadable ({e})")


def check_dir(folder: Path = DEFAULT_DIR, real: bool = False, only: tuple[str, ...] | None = None) -> list[str]:
    """`real`: the folder holds real products (synthetic must be false). `only`: check just these tables."""
    folder = Path(folder)
    errors: list[str] = []
    frames = {n: check_table(n, folder / f"{n}.parquet", errors) if only is None or n in only else None for n in SPEC}
    cells, cmw, harm, ent, cal = (frames[n] for n in ("cells", "cell_month_witness", "cell_month_harmonized",
                                                       "entity_month", "calibration"))
    if cells is not None:
        _guard("cells", errors, lambda: _check_cells(cells, errors))
    if cmw is not None:
        _guard("cell_month_witness", errors, lambda: _check_witness(cmw, cells, errors))
    if harm is not None:
        _guard("cell_month_harmonized", errors, lambda: _check_harm(harm, cells, errors, real))
    if ent is not None:
        _guard("entity_month", errors, lambda: _check_entity(ent, errors, real))
    if cal is not None:
        _guard("calibration", errors, lambda: _check_calibration(cal, cells, errors))
    _guard("json files", errors, lambda: check_json(folder, errors, real))
    return errors


def _check_cells(cells: pd.DataFrame, errors: list[str]) -> None:
    if not cells.cell_id.map(lambda c: bool(CELL_ID.match(c))).all():
        errors.append("cells: cell_id does not match g{RRR}_r{row}_c{col}")
    if not (cells.lat_min.between(-90, 90).all() and cells.lat_max.between(-90, 90).all()):
        errors.append("cells: latitude outside [-90, 90]")
    if not (cells.lon_min.between(-180, 180).all() and cells.lon_max.between(-180, 180).all()):
        errors.append("cells: longitude outside [-180, 180]")
    if (cells.lat_min >= cells.lat_max).any() or (cells.lon_min >= cells.lon_max).any():
        errors.append("cells: lower bound is not below upper bound")
    if (cells.area_km2 <= 0).any():
        errors.append("cells: non-positive area_km2")


def _check_witness(cmw: pd.DataFrame, cells: pd.DataFrame | None, errors: list[str]) -> None:
    _enum(errors, "cell_month_witness", "witness", cmw.witness, ENUMS["witness"])
    _enum(errors, "cell_month_witness", "daynight", cmw.daynight, ENUMS["daynight"])
    _enum(errors, "cell_month_witness", "data_level", cmw.data_level, ENUMS["data_level"])
    if (cmw.days_available > cmw.days_in_month).any() or (cmw.days_available <= 0).any():
        errors.append("cell_month_witness: days_available must be in 1..days_in_month (rows exist only when operating)")
    if (cmw[["detections", "cell_days"]] < 0).any().any() or (cmw.frp_sum_mw < 0).any():
        errors.append("cell_month_witness: negative counts or FRP")
    if (cmw.detections < cmw.cell_days).any():
        errors.append("cell_month_witness: fewer detections than cell_days")
    pivot = cmw.pivot_table(index=["cell_id", "year", "month", "witness"], columns="daynight", values="cell_days")
    if "ALL" in pivot and ((pivot["ALL"] - (pivot["D"] + pivot["N"])).abs() > 0).any():
        errors.append("cell_month_witness: ALL is not D + N")
    if cells is not None and not set(cmw.cell_id) <= set(cells.cell_id):
        errors.append("cell_month_witness: cell_id not in cells")


def _check_harm(harm: pd.DataFrame, cells: pd.DataFrame | None, errors: list[str], real: bool = False) -> None:
    check_harmonized_rows("cell_month_harmonized", harm, errors, real)
    if cells is not None and not set(harm.cell_id) <= set(cells.cell_id):
        errors.append("cell_month_harmonized: cell_id not in cells")


def _check_entity(ent: pd.DataFrame, errors: list[str], real: bool = False) -> None:
    check_harmonized_rows("entity_month", ent, errors, real)
    _enum(errors, "entity_month", "entity_type", ent.entity_type, ENUMS["entity_type"])
    for raw in ent.raw_by_witness:
        try:
            d = json.loads(raw)
            if not (isinstance(d, dict) and set(d) <= ENUMS["witness"]):
                raise ValueError
        except ValueError:
            errors.append("entity_month: raw_by_witness is not a JSON map of witness to cell_days")
            break


def _check_calibration(cal: pd.DataFrame, cells: pd.DataFrame | None, errors: list[str]) -> None:
    _enum(errors, "calibration", "witness", cal.witness, ENUMS["witness"])
    _enum(errors, "calibration", "daynight", cal.daynight, ENUMS["daynight"])
    _enum(errors, "calibration", "season", cal.season, ENUMS["season"])
    _enum(errors, "calibration", "pooling_level", cal.pooling_level, ENUMS["pooling_level"])
    if (pd.to_numeric(cal.ratio, errors="coerce") <= 0).any():
        errors.append("calibration: non-positive ratio")
    if cells is not None and not set(cells.stratum_id) <= set(cal.stratum_id):
        errors.append("calibration: a stratum_id used by cells has no calibration rows")


def check_json(folder: Path, errors: list[str], real: bool = False) -> None:
    for name in ("metadata.json", "validation_results.json"):
        if not (folder / name).exists():
            errors.append(f"{name} is missing")
    if not (folder / "metadata.json").exists() or not (folder / "validation_results.json").exists():
        return
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    for k in ("contract_version", "method_version", "synthetic", "generated_at", "grid", "baseline_years", "first_month",
              "latest_month", "provisional_months", "witnesses", "data_snapshot", "citation"):
        if k not in meta:
            errors.append(f"metadata.json: missing {k}")
    allowed = {"0.1.1"} if real else {"0.1.0", "0.1.1"}
    if meta.get("contract_version") not in allowed:
        errors.append(f"metadata.json: contract_version is not {' or '.join(sorted(allowed))}")
    if meta.get("synthetic") is not (not real):
        errors.append(f"metadata.json: synthetic must be {'false' if real else 'true'}" + ("" if real else " in fixtures"))
    for k in ("first_month", "latest_month"):
        if not MONTH_STR.match(str(meta.get(k, ""))):
            errors.append(f"metadata.json: {k} is not YYYY-MM")
    if not all(MONTH_STR.match(str(m)) for m in meta.get("provisional_months", [])):
        errors.append("metadata.json: provisional_months must be YYYY-MM strings")
    if not set(meta.get("witnesses", [])) <= ENUMS["witness"]:
        errors.append("metadata.json: witnesses outside the enumeration")
    val = json.loads((folder / "validation_results.json").read_text(encoding="utf-8"))
    if val.get("synthetic") is not (not real) or val.get("contract_version") not in allowed:
        errors.append(f"validation_results.json: needs synthetic {'false' if real else 'true'} and contract_version {' or '.join(sorted(allowed))}")
    for t in val.get("tests", []):
        for k in ("test_id", "family", "title", "case", "criterion", "threshold", "measured", "status", "notes"):
            if k not in t:
                errors.append(f"validation_results.json: test missing {k}")
        if t.get("status") not in ENUMS["test_status"]:
            errors.append(f"validation_results.json: bad status {t.get('status')}")
        if not real and not str(t.get("test_id", "")).startswith("SYNTHETIC-"):
            errors.append("validation_results.json: test_id must start with SYNTHETIC-")
        if not real and "SYNTHETIC EXAMPLE" not in str(t.get("notes", "")):
            errors.append("validation_results.json: notes must say SYNTHETIC EXAMPLE")


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--real"]
    real = "--real" in sys.argv[1:]
    folder = Path(args[0]) if args else DEFAULT_DIR
    errors = check_dir(folder, real=real)
    for e in errors:
        print("FAIL", e)
    print(f"{folder}: {'conforms to the contract' if not errors else f'{len(errors)} problem(s)'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
