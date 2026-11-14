"""Tests for pipeline/raw_only.py on a small SYNTHETIC cell_month_witness with sums known by hand (T-014a).

    python -m pytest pipeline/tests/test_raw_only.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import contract_check as cc
import raw_only as ro

# cell -> (country, continent). C5 lies in the ocean: no country, no continent.
CELLS = {"g050_r0100_c0100": ("AUS", "OC"), "g050_r0100_c0101": ("AUS", "OC"), "g050_r0200_c0200": ("BRA", "SA"),
         "g050_r0300_c0300": ("IDN", "AS"), "g050_r0400_c0400": (None, None)}
# (cell, year, month, witness) -> (cell_days, data_level). Aqua and Terra from 2002-07; S-NPP only in 2026-11; 2026-11 is NRT.
ROWS = {
    ("g050_r0100_c0100", 2020, 1, "AQUA_MODIS"): (5, "SP"), ("g050_r0100_c0100", 2020, 1, "TERRA_MODIS"): (7, "SP"),
    ("g050_r0100_c0101", 2020, 1, "AQUA_MODIS"): (0, "SP"), ("g050_r0100_c0101", 2020, 1, "TERRA_MODIS"): (3, "SP"),
    ("g050_r0200_c0200", 2020, 1, "AQUA_MODIS"): (11, "SP"), ("g050_r0200_c0200", 2020, 1, "TERRA_MODIS"): (13, "SP"),
    ("g050_r0300_c0300", 2020, 1, "AQUA_MODIS"): (2, "SP"), ("g050_r0300_c0300", 2020, 1, "TERRA_MODIS"): (4, "SP"),
    ("g050_r0400_c0400", 2020, 1, "AQUA_MODIS"): (17, "SP"), ("g050_r0400_c0400", 2020, 1, "TERRA_MODIS"): (19, "SP"),
    ("g050_r0100_c0100", 2026, 11, "AQUA_MODIS"): (1, "NRT"), ("g050_r0100_c0100", 2026, 11, "SNPP_VIIRS"): (6, "NRT"),
    ("g050_r0200_c0200", 2026, 10, "AQUA_MODIS"): (8, "SP"), ("g050_r0200_c0200", 2026, 10, "SNPP_VIIRS"): (9, "NRT"),   # mixed month
}


def make_products(tmp: Path) -> ro.Paths:
    cells = pd.DataFrame([(cid, -90 + 0.5 * i, -89.5 + 0.5 * i, 0.0, 0.5, -89.75 + 0.5 * i, 0.25, 40.0, c, k, "NHAF", "NHAF_b000_072")
                          for i, (cid, (c, k)) in enumerate(CELLS.items())],
                         columns=["cell_id", "lat_min", "lat_max", "lon_min", "lon_max", "lat_c", "lon_c", "area_km2", "country_iso3",
                                  "continent", "fire_region", "stratum_id"])
    pq.write_table(pa.Table.from_pandas(cells, preserve_index=False), tmp / "cells.parquet")
    recs = []
    for (cid, y, m, w), (n, lvl) in ROWS.items():
        for dn, v in (("D", n), ("N", 0), ("ALL", n)):
            recs.append((cid, y, m, w, dn, v, v, 0.0, 28, 28, lvl))
    pq.write_table(pa.Table.from_pandas(pd.DataFrame(recs, columns=[
        "cell_id", "year", "month", "witness", "daynight", "detections", "cell_days", "frp_sum_mw", "days_available", "days_in_month",
        "data_level"]), preserve_index=False), tmp / "cell_month_witness.parquet")
    (tmp / "country_map.csv").write_text("firms_name,iso3,continent,method,note\nAustralia,AUS,OC,NE,x\nBrazil,BRA,SA,NE,x\n"
                                         "Indonesia,IDN,AS,NE,x\nUnused Land,UNU,EU,NE,x\n", encoding="utf-8")
    (tmp / "raw" / "zips").mkdir(parents=True)
    (tmp / "raw" / "api_2026").mkdir()
    (tmp / "raw" / "zips" / "a.zip").write_bytes(b"x")
    (tmp / "raw" / "api_2026" / "b.csv").write_bytes(b"x")
    return ro.Paths(products=tmp, country_map=tmp / "country_map.csv", raw=tmp / "raw", tmp=tmp / "dbtmp")


def test_cell_level_sums_and_all_harmonized_fields_are_null(tmp_path):
    paths = make_products(tmp_path)
    ro.build(paths)
    h = pq.read_table(paths.products / "cell_month_harmonized.parquet").to_pandas()
    assert len(h) == 7                                                        # 5 cells in 2020-01, 2 in 2026-11 (one cell) and 2026-10
    one = h[(h.cell_id == "g050_r0100_c0100") & (h.year == 2020)].iloc[0]
    assert one.raw_combined_cell_days == 5 + 7                                # Aqua + Terra, the contract's naive raw sum
    for col in ro.NULL_FLOATS:
        assert h[col].isna().all(), col
    assert (h.witnesses_used.map(len) == 0).all() and (h.n_witnesses == 0).all()
    assert (h.verdict == "CANNOT_DETERMINE").all() and (h.reason_codes.map(list) == [["NOT_HARMONIZED"]] * len(h)).all()
    assert h.method_version.str.endswith("-raw-only").all()


def test_entity_sums_global_and_continents_add_up(tmp_path):
    paths = make_products(tmp_path)
    ro.build(paths)
    e = pq.read_table(paths.products / "entity_month.parquet").to_pandas()
    jan = e[(e.year == 2020) & (e.month == 1)].set_index(["entity_type", "entity_id"])
    assert jan.loc[("COUNTRY", "AUS"), "raw_combined_cell_days"] == 5 + 7 + 0 + 3
    assert jan.loc[("COUNTRY", "AUS"), "n_cells"] == 2 and jan.loc[("COUNTRY", "AUS"), "entity_name"] == "Australia"
    assert json.loads(jan.loc[("COUNTRY", "AUS"), "raw_by_witness"]) == {"AQUA_MODIS": 5, "TERRA_MODIS": 10}
    assert jan.loc[("CONTINENT", "OC"), "entity_name"] == "Oceania"
    total = 5 + 7 + 0 + 3 + 11 + 13 + 2 + 4 + 17 + 19
    assert jan.loc[("GLOBAL", "GLOBAL"), "raw_combined_cell_days"] == total and jan.loc[("GLOBAL", "GLOBAL"), "n_cells"] == len(CELLS)
    countries = jan.loc["COUNTRY"].raw_combined_cell_days.sum()
    assert total - countries == 17 + 19                                       # the ocean cell is in GLOBAL only
    assert jan.loc["CONTINENT"].raw_combined_cell_days.sum() == countries
    assert set(e.entity_type) == {"COUNTRY", "CONTINENT", "GLOBAL"} and "UNU" not in set(e.entity_id)   # no empty country


def test_a_mixed_month_is_mixed_and_a_month_with_s_npp_lists_it(tmp_path):
    paths = make_products(tmp_path)
    ro.build(paths)
    e = pq.read_table(paths.products / "entity_month.parquet").to_pandas().set_index(["entity_type", "entity_id", "year", "month"])
    assert e.loc[("COUNTRY", "BRA", 2026, 10), "data_level"] == "MIXED"
    assert e.loc[("COUNTRY", "AUS", 2026, 11), "data_level"] == "NRT"
    assert json.loads(e.loc[("COUNTRY", "AUS", 2026, 11), "raw_by_witness"]) == {"AQUA_MODIS": 1, "SNPP_VIIRS": 6}
    assert e.loc[("COUNTRY", "AUS", 2020, 1), "data_level"] == "SP"


def test_metadata_is_real_and_names_what_it_found(tmp_path):
    paths = make_products(tmp_path)
    ro.build(paths)
    m = json.loads((paths.products / "metadata.json").read_text(encoding="utf-8"))
    assert m["synthetic"] is False and m["method_version"].endswith("-raw-only") and m["contract_version"] == "0.1.1"
    assert (m["first_month"], m["latest_month"]) == ("2020-01", "2026-11") and m["provisional_months"] == ["2026-10", "2026-11"]
    assert m["witnesses"] == ["AQUA_MODIS", "SNPP_VIIRS"] and m["grid"] == {"analysis_deg": 0.5, "fine_deg": 0.05}
    assert m["baseline_years"] == [] and "FIRMS" in m["citation"] and all(m["data_snapshot"].values())
    v = json.loads((paths.products / "validation_results.json").read_text(encoding="utf-8"))
    assert v["synthetic"] is False and v["tests"] == [] and v["contract_version"] == "0.1.1"


def test_the_output_passes_the_contract_in_real_mode_and_a_corrupted_copy_does_not(tmp_path):
    paths = make_products(tmp_path)
    ro.build(paths)
    only = ("cells", "cell_month_harmonized", "entity_month")
    assert cc.check_dir(paths.products, real=True, only=only) == []
    assert any("synthetic must be true" in e for e in cc.check_dir(paths.products, only=only))     # the fixture mode refuses real files
    h = pq.read_table(paths.products / "cell_month_harmonized.parquet").to_pandas()
    h.loc[0, "verdict"] = "ABOVE_NORMAL"                                       # a verdict with no estimate: not allowed
    h.loc[1, "estimate"] = 3.0                                                  # an estimate with no witness: not allowed
    pq.write_table(pa.Table.from_pandas(h, preserve_index=False), paths.products / "cell_month_harmonized.parquet")
    errors = cc.check_dir(paths.products, real=True, only=only)
    assert any("verdict" in e or "estimate" in e for e in errors)


def test_a_raw_only_row_without_not_harmonized_fails_in_real_mode(tmp_path):
    paths = make_products(tmp_path)
    ro.build(paths)
    only = ("cells", "cell_month_harmonized", "entity_month")
    for name in ("cell_month_harmonized", "entity_month"):
        path = paths.products / f"{name}.parquet"
        schema = pq.read_table(path).schema
        good = pq.read_table(path).to_pandas()
        assert cc.check_dir(paths.products, real=True, only=only) == []
        for bad_codes in ([], ["SINGLE_WITNESS"], ["NOT_HARMONIZED", "SINGLE_WITNESS"]):
            bad = good.copy()
            bad.at[0, "reason_codes"] = bad_codes
            pq.write_table(pa.Table.from_pandas(bad, schema=schema, preserve_index=False), path)
            errors = cc.check_dir(paths.products, real=True, only=only)
            assert any(name in e and "NOT_HARMONIZED" in e for e in errors), (name, bad_codes)
        pq.write_table(pa.Table.from_pandas(good, schema=schema, preserve_index=False), path)
    # a harmonized row must not carry the code
    schema = pq.read_table(paths.products / "cell_month_harmonized.parquet").schema
    h = pq.read_table(paths.products / "cell_month_harmonized.parquet").to_pandas()
    h["method_version"] = "0.1.0-combined"
    pq.write_table(pa.Table.from_pandas(h, schema=schema, preserve_index=False), paths.products / "cell_month_harmonized.parquet")
    assert any("not raw-only" in e for e in cc.check_dir(paths.products, real=True, only=only))


def test_the_checker_takes_contract_0_1_1_and_the_real_mode_requires_it(tmp_path):
    paths = make_products(tmp_path)
    ro.build(paths)
    only = ("cells", "cell_month_harmonized", "entity_month")
    meta_path = paths.products / "metadata.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta["contract_version"] = "0.1.0"
    meta_path.write_text(json.dumps(meta), encoding="utf-8")
    assert any("contract_version" in e for e in cc.check_dir(paths.products, real=True, only=only))
    assert "NOT_HARMONIZED" in cc.ENUMS["reason_code"]


def test_the_build_is_deterministic(tmp_path):
    paths = make_products(tmp_path)
    ro.build(paths)
    first = [(paths.products / f"{n}.parquet").read_bytes() for n in ("cell_month_harmonized", "entity_month")]
    ro.build(paths)
    assert first == [(paths.products / f"{n}.parquet").read_bytes() for n in ("cell_month_harmonized", "entity_month")]
