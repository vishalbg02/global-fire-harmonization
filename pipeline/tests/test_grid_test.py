"""Tests for pipeline/grid_test.py on a tiny dataset with known answers (D-009 grid-size comparison).

    python -m pytest pipeline/tests/test_grid_test.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import grid_test as gt

COLS = ["satellite", "lat", "lon", "acq_date", "daynight", "confidence_class", "type", "data_level"]


def det(sat, lat, lon, date, dn="D", conf="HIGH", typ=0, level="SP"):
    return {"satellite": sat, "lat": lat, "lon": lon, "acq_date": date, "daynight": dn, "confidence_class": conf, "type": typ,
            "data_level": level}


def write(folder: Path, sensor: str, rows: list[dict]) -> None:
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
            confidence_class, CAST(type AS SMALLINT) type, data_level FROM (VALUES {vals}) t({', '.join(COLS)}))
            TO '{(d / 'detections.parquet').as_posix()}' (FORMAT parquet)""")


@pytest.fixture
def data(tmp_path):
    aqua = [det("Aqua", 10.01, 20.01, "2012-03-01"), det("Aqua", 10.01, 20.01, "2012-03-01"),   # same fine cell, same day: 1 cell-day
            det("Aqua", 10.01, 20.01, "2012-03-02", dn="N"),                                       # a second day (night)
            det("Aqua", 12.01, 22.01, "2012-03-05"),                                               # cell C: Aqua only
            det("Aqua", 10.01, 20.01, "2012-03-09", conf="LOW"),                                   # removed: low confidence
            det("Aqua", 10.01, 20.01, "2012-03-10", typ=2),                                        # removed: not type 0
            det("Aqua", 10.01, 20.01, "2012-03-11", level="NRT", typ=None),                        # removed: not SP
            det("Aqua", 10.01, 20.01, "2017-01-01"),                                               # removed: outside the period
            det("Terra", 10.01, 20.01, "2012-03-12")]                                              # removed: not Aqua
    snpp = [det("N", 10.01, 20.01, "2012-03-01"), det("N", 10.01, 20.01, "2012-03-02", dn="N"), det("N", 10.01, 20.01, "2012-03-03"),
            det("N", 11.01, 21.01, "2012-03-04"),                                                  # cell B: S-NPP only
            det("N", 13.01, 23.01, "2012-03-06")]                                                  # cell D (masked in one test)
    write(tmp_path, "MODIS", aqua)
    write(tmp_path, "VIIRS_SNPP", snpp)
    return tmp_path


def mask_file(tmp_path: Path) -> Path:
    r, c = int((13.01 + 90) / 0.05), int((23.01 + 180) / 0.05)
    path = tmp_path / "mask.parquet"
    duckdb.sql(f"COPY (SELECT {r} AS r, {c} AS c) TO '{path.as_posix()}' (FORMAT parquet)")
    return path


def cell_months(con, data, fine, analysis, mask=None, dn=None):
    det_sql = gt.detections_sql(data)
    fcd = gt.build_fine_cell_days(con, det_sql, fine, mask is not None, mask or gt.MASK)
    cm = gt.cell_months(con, fcd, fine, analysis, dn)
    return {(s, ar, ac): n for s, ar, ac, n in con.execute(f"SELECT sat, ar, ac, sum(cell_days) FROM {cm} GROUP BY ALL").fetchall()}


def test_fine_cell_days_count_each_cell_and_day_once_and_apply_the_filters(data):
    con = gt.connect()
    cm = cell_months(con, data, 0.05, 0.5)
    ar, ac = int((10.01 + 90) // 0.5), int((20.01 + 180) // 0.5)
    assert cm[("AQUA", ar, ac)] == 2                      # two days; the duplicate point and every filtered row do not count
    assert cm[("SNPP", ar, ac)] == 3
    assert sum(v for (s, *_), v in cm.items() if s == "AQUA") == 3   # cell A (2) + cell C (1)
    assert sum(v for (s, *_), v in cm.items() if s == "SNPP") == 5   # A (3), B (1), D (1)


def test_day_and_night_are_separate_and_add_up(data):
    con = gt.connect()
    both = cell_months(con, data, 0.05, 0.5)
    day = cell_months(con, data, 0.05, 0.5, dn="D")
    night = cell_months(con, data, 0.05, 0.5, dn="N")
    ar, ac = int((10.01 + 90) // 0.5), int((20.01 + 180) // 0.5)
    assert day[("AQUA", ar, ac)] == 1 and night[("AQUA", ar, ac)] == 1 and both[("AQUA", ar, ac)] == 2


def test_the_approved_mask_removes_masked_cells(data):
    con = gt.connect()
    ar, ac = int((13.01 + 90) // 0.5), int((23.01 + 180) // 0.5)
    assert cell_months(con, data, 0.05, 0.5)[("SNPP", ar, ac)] == 1
    assert ("SNPP", ar, ac) not in cell_months(con, data, 0.05, 0.5, mask=mask_file(data))


def test_a_fine_cell_belongs_to_the_analysis_cell_holding_its_centre(data):
    con = gt.connect()
    cm = cell_months(con, data, 0.1, 0.25)
    # the 0.1 degree fine cell of (10.01, 20.01) has its centre at (10.05, 20.05): analysis 0.25 degree cell (row 400, column 800)
    assert cm[("AQUA", int((10.05 + 90) // 0.25), int((20.05 + 180) // 0.25))] == 2
    assert int((10.05 + 90) // 0.25) == 400


def test_metrics_on_a_known_example(data):
    con = gt.connect()
    cm = gt.cell_months(con, gt.build_fine_cell_days(con, gt.detections_sql(data), 0.05, False), 0.05, 0.5, None)
    m = gt.metrics(con, cm, months=60, min_activity=2)
    # cell-months (a, s): A (2, 3), B (0, 1), C (1, 0), D (0, 1)
    assert m["active_cells"] == 4 and m["cell_months_either"] == 4
    assert m["ratio_median"] == pytest.approx(2 / 3) and m["ratio_q25"] == pytest.approx(2 / 3)
    assert m["share_both_positive"] == pytest.approx(1 / 240) and m["share_one_zero"] == pytest.approx(3 / 240)
    assert m["share_both_zero"] == pytest.approx(236 / 240)
    assert m["aqua_ge_min_cell_months"] == 1 and m["share_aqua_ge_min"] == pytest.approx(1 / 240)
    # Spearman of a = (2, 0, 1, 0) and s = (3, 1, 0, 1), average ranks for ties: ra = (4, 1.5, 3, 1.5), rs = (4, 2.5, 1, 2.5), correlation 1/3
    assert m["spearman"] == pytest.approx(1 / 3, abs=1e-6)


def test_run_reports_every_combination_without_writing_into_the_data(data, tmp_path):
    mask = mask_file(data)
    before = sorted(p.name for p in data.rglob("*.parquet"))
    res = gt.run(data, tmp_path / "out", mask)
    assert len(res) == 2 * 2 * 2 * 3                       # mask on or off x fine grids x analysis grids x (all, D, N)
    assert {(r["fine"], r["analysis"]) for r in res} == {(f, a) for f in gt.FINE for a in gt.ANALYSIS}
    assert all(r["output_bytes"] > 0 for r in res if r["cell_months_either"])
    assert sorted(p.name for p in data.rglob("*.parquet")) == before
