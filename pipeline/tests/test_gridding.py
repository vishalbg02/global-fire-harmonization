"""Tests for pipeline/gridding.py on a small synthetic dataset with known answers (T-006).

    python -m pytest pipeline/tests/test_gridding.py -q
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gridding as gr

COLS = ["satellite", "lat", "lon", "acq_date", "daynight", "confidence_class", "type", "data_level", "frp_mw", "country_name"]


def det(sat, lat, lon, date, dn="D", conf="HIGH", typ=0, level="SP", frp=5.0, country="Brazil"):
    return {"satellite": sat, "lat": lat, "lon": lon, "acq_date": date, "daynight": dn, "confidence_class": conf, "type": typ,
            "data_level": level, "frp_mw": frp, "country_name": country}


def write_det(folder: Path, sensor: str, rows: list[dict]) -> None:
    by_year: dict[int, list] = {}
    for r in rows:
        by_year.setdefault(int(r["acq_date"][:4]), []).append(r)
    con = duckdb.connect()
    for year, rs in by_year.items():
        d = folder / f"sensor={sensor}" / f"year={year}"
        d.mkdir(parents=True, exist_ok=True)
        vals = ", ".join("(" + ", ".join("NULL" if r[c] is None else (f"'{r[c]}'" if isinstance(r[c], str) else str(r[c])) for c in COLS) + ")"
                         for r in rs)
        con.execute(f"""COPY (SELECT satellite, CAST(lat AS DOUBLE) lat, CAST(lon AS DOUBLE) lon, CAST(acq_date AS DATE) acq_date, daynight,
            confidence_class, CAST(type AS SMALLINT) type, data_level, CAST(frp_mw AS DOUBLE) frp_mw, country_name
            FROM (VALUES {vals}) t({', '.join(COLS)})) TO '{(d / 'detections.parquet').as_posix()}' (FORMAT parquet)""")


A = (10.01, 20.01)    # analysis cell row 200, column 400 (fine cell row 2000, column 4000)
B = (11.01, 21.01)    # row 202, column 402
C = (12.01, 22.01)    # row 204, column 404, masked
D_ = (13.01, 23.01)   # row 206, column 406, only API rows (no country)
CID = {"A": gr.cell_id(200, 400), "B": gr.cell_id(202, 402), "D": gr.cell_id(206, 406)}


def missing_html(pairs):
    cells = "".join(f"<td>{d}</td><td>{n}</td>" for d, n in pairs)
    return json.dumps({"success": True, "html": f"<tr>{cells}</tr>"})


@pytest.fixture
def paths(tmp_path):
    aqua = [det("Aqua", *A, "2012-02-10", conf="LOW"),                      # filtered, but it starts the window (Feb 10)
            det("Aqua", *A, "2012-03-05"), det("Aqua", *A, "2012-03-05", frp=-2.0),   # same fine cell and day: 1 cell-day, 2 detections
            det("Aqua", *A, "2012-03-06", dn="N", frp=3.0),
            det("Aqua", *A, "2012-03-09", typ=2),                            # removed: not type 0
            det("Aqua", *A, "2012-03-10", conf="LOW"),                       # removed: low confidence
            det("Aqua", *C, "2012-03-11"),                                   # removed: in the static mask
            det("Aqua", *A, "2012-04-20", level="NRT", typ=None),            # NRT row: kept, no type; also ends the window (Apr 20)
            det("Terra", *A, "2002-01-05"),                                  # before the record start: no rows
            det("Terra", *A, "2012-03-01"), det("Terra", *B, "2012-03-02")]
    snpp = [det("N", *B, "2012-03-02"), det("N", *B, "2012-03-02", dn="N"), det("N", *A, "2012-03-30"),
            det("N", *D_, "2012-03-15", country=None, level="NRT", typ=None)]
    write_det(tmp_path / "det", "MODIS", aqua)
    write_det(tmp_path / "det", "VIIRS_SNPP", snpp)
    r, c = int((12.01 + 90) / 0.05), int((22.01 + 180) / 0.05)
    duckdb.sql(f"COPY (SELECT {r} AS r, {c} AS c) TO '{(tmp_path / 'mask.parquet').as_posix()}' (FORMAT parquet)")
    regions = pa.table({"cell_id": list(CID.values()) + [gr.cell_id(204, 404)], "fire_region": ["SHSA", "SHSA", "NHAF", "SHSA"]})
    pq.write_table(regions, tmp_path / "regions.parquet")
    (tmp_path / "country_map.csv").write_text("firms_name,iso3,continent,method,note\nBrazil,BRA,SA,NATURAL_EARTH,x\n", encoding="utf-8")
    (tmp_path / "missing.json").write_text(missing_html([("2012-03-07", "Aqua (MODIS)"), ("2012-03-08", "Aqua (MODIS)"),
                                                          ("2012-03-20", "NOAA-21 (VIIRS)"), ("2012-03-03", "Suomi NPP (VIIRS)"),
                                                          ("2012-03-02", "Suomi NPP (VIIRS)")]), encoding="utf-8")
    return gr.Paths(detections=tmp_path / "det", mask=tmp_path / "mask.parquet", fire_regions=tmp_path / "regions.parquet",
                    country_map=tmp_path / "country_map.csv", missing_json=tmp_path / "missing.json", out=tmp_path / "out",
                    work=tmp_path / "work", tmp=tmp_path / "dbtmp", raw_availability=tmp_path / "avail")


@pytest.fixture
def built(paths):
    gr.build(paths)
    con = duckdb.connect()
    cmw = con.execute(f"SELECT * FROM read_parquet('{(paths.out / 'cell_month_witness.parquet').as_posix()}')").df()
    cells = con.execute(f"SELECT * FROM read_parquet('{(paths.out / 'cells.parquet').as_posix()}')").df()
    return paths, cmw, cells


def row(cmw, cell, witness, month, dn, year=2012):
    sel = cmw[(cmw.cell_id == cell) & (cmw.witness == witness) & (cmw.month == month) & (cmw.daynight == dn) & (cmw.year == year)]
    assert len(sel) == 1, (cell, witness, month, dn, len(sel))
    return sel.iloc[0]


# ------------------------------------------------------------------------------------ counting
def test_cell_days_count_each_fine_cell_and_day_once_per_daynight(built):
    _, cmw, _ = built
    d, n, a = (row(cmw, CID["A"], "AQUA_MODIS", 3, dn) for dn in ("D", "N", "ALL"))
    assert (d.cell_days, d.detections) == (1, 2)                       # two detections, one cell-day
    assert (n.cell_days, n.detections) == (1, 1)
    assert (a.cell_days, a.detections) == (2, 3)                        # ALL is D + N
    assert d.frp_sum_mw == pytest.approx(5.0)                           # the negative FRP is left out of the sum
    assert n.frp_sum_mw == pytest.approx(3.0) and a.frp_sum_mw == pytest.approx(8.0)


def test_filters_and_the_static_mask_remove_rows(built):
    _, cmw, cells = built
    # type 2, low confidence and the masked cell add nothing: only the March day and night cell-days of cell A remain for Aqua
    assert row(cmw, CID["A"], "AQUA_MODIS", 3, "ALL").cell_days == 2
    assert gr.cell_id(204, 404) not in set(cells.cell_id)               # the masked cell has no kept detection, so it is not a cell


def test_zero_rows_exist_for_operating_months(built):
    _, cmw, _ = built
    z = row(cmw, CID["B"], "AQUA_MODIS", 3, "ALL")                       # Aqua operated in March, nothing in cell B
    assert (z.cell_days, z.detections, z.frp_sum_mw) == (0, 0, 0.0)
    assert row(cmw, CID["A"], "AQUA_MODIS", 2, "ALL").cell_days == 0     # February: the window starts on 2012-02-10


def test_no_rows_before_a_witness_operated_or_before_the_record_start(built):
    _, cmw, _ = built
    snpp = cmw[cmw.witness == "SNPP_VIIRS"]
    assert set(snpp.month) == {3} and set(snpp.year) == {2012}          # S-NPP detections start in March 2012
    terra = cmw[cmw.witness == "TERRA_MODIS"]
    assert set(zip(terra.year, terra.month, strict=True)) == {(2012, 3)}   # the 2002-01 Terra row is before the record start
    assert not ((cmw.year * 100 + cmw.month) < 200207).any()


def test_every_active_cell_has_a_row_for_every_operated_witness_month_and_daynight(built):
    _, cmw, cells = built
    n_cells = len(cells)
    witness_months = cmw.groupby("witness")[["year", "month"]].apply(lambda d: len(d.drop_duplicates()))
    assert len(cmw) == n_cells * 3 * witness_months.sum()


# -------------------------------------------------------------------------------- availability
def test_days_available_removes_the_missing_days_and_respects_the_window(built):
    _, cmw, _ = built
    assert row(cmw, CID["A"], "AQUA_MODIS", 3, "ALL").days_available == 29      # 31 days minus the 7th and the 8th
    assert row(cmw, CID["A"], "AQUA_MODIS", 2, "ALL").days_available == 20      # 2012-02-10 to 02-29
    assert row(cmw, CID["A"], "AQUA_MODIS", 4, "ALL").days_available == 20      # up to 2012-04-20
    assert row(cmw, CID["A"], "AQUA_MODIS", 3, "ALL").days_in_month == 31
    # S-NPP: first detection 2012-03-02, last 2012-03-30. The listed day 2012-03-03 has no detections and is removed; the listed day
    # 2012-03-02 has detections, so it counts as available; NOAA-21 is ignored
    assert row(cmw, CID["A"], "SNPP_VIIRS", 3, "ALL").days_available == 28


def test_data_level_is_per_witness_month(built):
    _, cmw, _ = built
    assert row(cmw, CID["A"], "AQUA_MODIS", 3, "ALL").data_level == "SP"
    assert row(cmw, CID["A"], "AQUA_MODIS", 4, "ALL").data_level == "NRT"
    assert row(cmw, CID["A"], "SNPP_VIIRS", 3, "ALL").data_level == "MIXED"      # an SP row and an NRT row in the same month


def test_parse_missing_maps_the_four_witnesses_only(paths):
    m = gr.parse_missing(paths.missing_json)
    assert m["AQUA_MODIS"] == {dt.date(2012, 3, 7), dt.date(2012, 3, 8)}
    assert m["SNPP_VIIRS"] == {dt.date(2012, 3, 3), dt.date(2012, 3, 2)} and m["NOAA20_VIIRS"] == set() and m["TERRA_MODIS"] == set()


def test_availability_check_reports_gaps(paths):
    con = gr.connect(paths)
    res = gr.availability_check(con, paths, gr.parse_missing(paths.missing_json))
    assert res["AQUA_MODIS"]["listed_missing"] == 2 and res["AQUA_MODIS"]["listed_missing_but_has_detections"] == 0
    assert res["SNPP_VIIRS"]["window"] == ("2012-03-02", "2012-03-30")


# -------------------------------------------------------------------------------------- cells
def test_cells_attributes(built):
    _, _, cells = built
    c = cells.set_index("cell_id")
    a = c.loc[CID["A"]]
    assert (a.lat_min, a.lat_max, a.lon_min, a.lon_max) == (10.0, 10.5, 20.0, 20.5)
    assert (a.lat_c, a.lon_c) == (10.25, 20.25)
    assert (a.country_iso3, a.continent, a.fire_region, a.stratum_id) == ("BRA", "SA", "SHSA", "SHSA_BRA")
    assert 3_000 < a.area_km2 < 3_300                                    # about 55.6 km by 55 km at 10 degrees north
    d = c.loc[CID["D"]]                                                  # only API rows: no country
    assert pd.isna(d.country_iso3) and pd.isna(d.continent) and d.stratum_id == "NHAF_NOCOUNTRY"
    assert set(cells.cell_id) == set(CID.values())


# -------------------------------------------------------------------- contract and integrity
def test_the_product_validates_and_matches_an_independent_count(built):
    paths, _, _ = built
    assert gr.validate(paths) == []
    res = gr.integrity(paths)
    assert res["match"] and res["kept_detections_independent"] == res["kept_detections_product"]


def test_the_validator_catches_a_broken_product(built, tmp_path):
    paths, cmw, _ = built
    bad = cmw.copy()
    bad.loc[(bad.daynight == "ALL").idxmax(), "cell_days"] += 5          # ALL no longer equals D + N
    bad.loc[0, "days_available"] = bad.loc[0, "days_in_month"] + 1       # more days available than days in the month
    pq.write_table(pa.Table.from_pandas(bad, preserve_index=False), paths.out / "cell_month_witness.parquet")
    text = " | ".join(gr.validate(paths))
    assert "ALL must be D + N" in text and "days_available" in text


def test_monthly_totals_for_the_sensor_jump_evidence(built):
    paths, _, _ = built
    totals = {(w, m): n for y, m, w, n in gr.monthly_totals(paths) if y == 2012}
    assert totals[("AQUA_MODIS", 3)] == 2 and totals[("SNPP_VIIRS", 3)] == 4 and totals[("TERRA_MODIS", 3)] == 2


def test_build_never_changes_the_detections(paths):
    before = sorted((p.relative_to(paths.detections).as_posix(), p.stat().st_size) for p in paths.detections.rglob("*.parquet"))
    gr.build(paths)
    after = sorted((p.relative_to(paths.detections).as_posix(), p.stat().st_size) for p in paths.detections.rglob("*.parquet"))
    assert before == after
