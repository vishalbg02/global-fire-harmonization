"""Tests for pipeline/qa_filters.py on small synthetic datasets with known answers (T-005).

    python -m pytest pipeline/tests/test_qa_filters.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import qa_filters as qa

COLS = ["sensor", "satellite", "lat", "lon", "acq_date", "acq_time_utc", "daynight", "confidence_class", "confidence_raw",
        "frp_mw", "scan_km", "track_km", "type", "version", "country_name", "data_level"]


def row(**kw):
    base = {"sensor": "MODIS", "satellite": "Aqua", "lat": 10.0, "lon": 20.0, "acq_date": "2020-05-01", "acq_time_utc": 1000,
            "daynight": "D", "confidence_class": "HIGH", "confidence_raw": "80", "frp_mw": 5.0, "scan_km": 1.0, "track_km": 1.0,
            "type": 0, "version": "6.03", "country_name": "A", "data_level": "SP"}
    base.update(kw)
    return base


def write(det_dir: Path, rows: list[dict]) -> str:
    """Write rows as sensor=/year= partitions like T-003 and return the read_parquet source."""
    con = duckdb.connect()
    groups: dict[tuple, list] = {}
    for r in rows:
        groups.setdefault((r["sensor"], r["_year"] if "_year" in r else int(r["acq_date"][:4])), []).append(r)
    for (sensor, year), rs in groups.items():
        d = det_dir / f"sensor={sensor}" / f"year={year}"
        d.mkdir(parents=True, exist_ok=True)
        vals = ", ".join("(" + ", ".join("NULL" if r[c] is None else (f"'{r[c]}'" if isinstance(r[c], str) else str(r[c]))
                                          for c in COLS) + ")" for r in rs)
        con.execute(f"""COPY (SELECT sensor, satellite, CAST(lat AS DOUBLE) lat, CAST(lon AS DOUBLE) lon, CAST(acq_date AS DATE) acq_date,
            CAST(acq_time_utc AS INTEGER) acq_time_utc, daynight, confidence_class, confidence_raw, CAST(frp_mw AS DOUBLE) frp_mw,
            CAST(scan_km AS DOUBLE) scan_km, CAST(track_km AS DOUBLE) track_km, CAST(type AS SMALLINT) type, version, country_name, data_level
            FROM (VALUES {vals}) t({', '.join(COLS)})) TO '{(d / 'detections.parquet').as_posix()}' (FORMAT parquet)""")
    return qa.source(det_dir)


@pytest.fixture
def con(tmp_path):
    return qa.connect(tmp_path / "dbtmp")


# ------------------------------------------------------------------------------ value domains
def test_each_domain_violation_is_counted(tmp_path, con):
    rows = [
        row(),                                                  # clean
        row(lat=95.0, acq_time_utc=1001),                       # lat out
        row(lon=-181.0, acq_time_utc=1002),                     # lon out
        row(acq_time_utc=2460),                                 # time out (hour)
        row(acq_time_utc=1275),                                 # time out (minutes 75)
        row(confidence_raw="150", acq_time_utc=1003),           # MODIS confidence out
        row(confidence_raw="x", acq_time_utc=1004),             # MODIS confidence not a number
        row(daynight="X", acq_time_utc=1005),                   # daynight out
        row(type=5, acq_time_utc=1006),                         # type out
        row(frp_mw=-1.0, acq_time_utc=1007),                    # frp negative
        row(scan_km=0.0, track_km=-1.0, acq_time_utc=1008),     # scan and track not positive
        row(acq_date="2021-01-01", _year=2020, acq_time_utc=1009),  # date outside its year
        row(lat=None, acq_time_utc=1010),                       # null key field
        row(frp_mw=None, acq_time_utc=1011),                    # frp null (informational)
    ]
    src = write(tmp_path / "det", rows)
    (r,) = qa.domain_violations(con, src)
    got = dict(zip(qa.DOMAIN_COLUMNS, r, strict=True))
    assert got["rows"] == 14
    assert got["lat_out"] == 1 and got["lon_out"] == 1 and got["time_out"] == 2
    assert got["confidence_out"] == 2 and got["daynight_out"] == 1 and got["type_out"] == 1
    assert got["frp_negative"] == 1 and got["scan_not_positive"] == 1 and got["track_not_positive"] == 1
    assert got["date_outside_year"] == 1 and got["null_key"] == 1 and got["frp_null"] == 1


def test_viirs_confidence_domain(tmp_path, con):
    rows = [row(sensor="VIIRS_SNPP", satellite="N", confidence_raw=c, acq_time_utc=1000 + i) for i, c in enumerate(["l", "N", "h", "z", "50"])]
    (r,) = qa.domain_violations(con, write(tmp_path / "det", rows))
    assert dict(zip(qa.DOMAIN_COLUMNS, r, strict=True))["confidence_out"] == 2  # 'z' and '50' are not l, n, h


# ---------------------------------------------------------------------------------- duplicates
def test_duplicates_within_and_across_country_files(tmp_path, con):
    rows = [row(country_name="A"), row(country_name="A"),             # repeat inside country A
            row(country_name="B"),                                     # same detection listed again under country B
            row(lat=11.0, country_name="A"), row(lat=12.0, country_name="A")]  # distinct
    (r,) = qa.duplicates(con, write(tmp_path / "det", rows))
    got = dict(zip(qa.DUP_COLUMNS, r, strict=True))
    assert got["rows"] == 5 and got["dup_rows"] == 2
    assert got["dup_same_country_file"] == 1 and got["dup_cross_country_files"] == 1


def test_year_boundaries_do_not_overlap(tmp_path, con):
    rows = [row(acq_date="2025-12-31", sensor="MODIS"), row(acq_date="2026-01-01", data_level="NRT", type=None)]
    b = qa.year_boundary(con, write(tmp_path / "det", rows))
    assert [(s, y, str(lo), str(hi)) for s, y, lo, hi in b] == [("MODIS", 2025, "2025-12-31", "2025-12-31"),
                                                                 ("MODIS", 2026, "2026-01-01", "2026-01-01")]


# -------------------------------------------------------------------------------------- filters
def test_filter_funnel_counts_every_step(tmp_path, con):
    sp = [row(type=0, confidence_class="HIGH", acq_time_utc=1), row(type=0, confidence_class="LOW", confidence_raw="10", acq_time_utc=2),
          row(type=1, acq_time_utc=3), row(type=2, acq_time_utc=4), row(type=3, acq_time_utc=5),
          row(type=None, acq_time_utc=6),                                   # SP without a type
          row(type=0, confidence_class=None, confidence_raw="x", acq_time_utc=7)]  # unclassified confidence
    nrt = [row(data_level="NRT", type=None, confidence_class="NOMINAL", acq_time_utc=8),
           row(data_level="NRT", type=None, confidence_class="LOW", confidence_raw="5", acq_time_utc=9)]
    rows = qa.filter_funnel(con, write(tmp_path / "det", sp + nrt))
    by = {r[1]: dict(zip(qa.FUNNEL_COLUMNS, r, strict=True)) for r in rows}
    s, n = by["SP"], by["NRT"]
    assert s["rows"] == 7 and s["sp_type_missing"] == 1 and s["sp_type1_volcano"] == 1
    assert s["sp_type2_static"] == 1 and s["sp_type3_offshore"] == 1
    assert s["after_type_filter"] == 3                      # the three type 0 rows
    assert s["after_confidence_only"] == 5                  # HIGH x5 (LOW and unclassified are out)
    assert s["after_type_and_confidence"] == 1              # type 0 and HIGH
    assert s["confidence_unclassified"] == 1
    assert n["rows"] == 2 and n["after_type_filter"] == 2   # NRT has no type; kept here, the mask handles it
    assert n["after_type_and_confidence"] == 1


# ---------------------------------------------------------------------------------- static mask
def mask_rows():
    def cell(lat, lon, n, typ, year, level="SP", **kw):
        return [row(sensor="VIIRS_SNPP", satellite="N", lat=lat + 0.01, lon=lon + 0.01, acq_date=f"{year}-06-01", type=typ,
                    data_level=level, acq_time_utc=1000 + i, **kw) for i in range(n)]
    r = []
    r += cell(10, 20, 10, 2, 2015)                       # A: static in training
    r += cell(11, 21, 10, 0, 2015)                       # B: fire in training
    r += cell(12, 22, 5, 2, 2015) + cell(12, 22, 5, 0, 2016)   # C: half static
    r += cell(13, 23, 2, 2, 2015)                        # D: only 2 detections (below the minimum count)
    r += cell(10, 20, 4, 2, 2024) + cell(10, 20, 1, 0, 2024)   # evaluation years
    r += cell(11, 21, 5, 0, 2024)
    r += cell(12, 22, 2, 2, 2024) + cell(12, 22, 2, 0, 2024)
    r += cell(10, 20, 3, None, 2026, "NRT") + cell(11, 21, 2, None, 2026, "NRT") + cell(12, 22, 1, None, 2026, "NRT")
    return r


def sweep(tmp_path, con):
    out = qa.mask_sweep(con, write(tmp_path / "det", mask_rows()), 0.1)
    return {(m["min_share"], m["min_detections"]): m for m in out}


def test_mask_sweep_shares_and_holdout(tmp_path, con):
    m = sweep(tmp_path, con)
    half = m[(0.5, 3)]
    assert half["eval_static_total"] == 6 and half["eval_fire_total"] == 8
    assert half["static_removed"] == 6 and half["fire_lost"] == 3            # cells A and C are masked
    assert half["static_removed_share"] == pytest.approx(1.0) and half["fire_lost_share"] == pytest.approx(3 / 8)
    assert half["precision"] == pytest.approx(6 / 9)
    strict = m[(0.7, 3)]
    assert strict["static_removed"] == 4 and strict["fire_lost"] == 1        # only cell A is masked
    assert m[(0.9, 3)]["static_removed"] == 4


def test_mask_minimum_count_rule_and_cells_and_nrt_rows(tmp_path, con):
    m = sweep(tmp_path, con)
    assert m[(0.5, 3)]["cells_masked"] == 2        # A and C; D has only 2 detections so it is never masked
    assert m[(0.7, 3)]["cells_masked"] == 1        # A only (C is 50% static)
    assert m[(0.3, 3)]["cells_masked"] == 2 and m[(0.3, 10)]["cells_masked"] == 2
    assert m[(0.5, 3)]["nrt_rows_total"] == 6
    assert m[(0.5, 3)]["nrt_rows_masked"] == 4     # 3 in A + 1 in C
    assert m[(0.7, 3)]["nrt_rows_masked"] == 3     # 3 in A


def test_save_mask_writes_only_cells_that_pass(tmp_path, con):
    src = write(tmp_path / "det", mask_rows())
    qa.mask_sweep(con, src, 0.1)
    n = qa.save_mask(con, 0.1, 0.7, 3, tmp_path / "mask.parquet")
    assert n == 1
    cells = duckdb.sql(f"SELECT r, c, n_total, n_static FROM read_parquet('{(tmp_path / 'mask.parquet').as_posix()}')").fetchall()
    assert cells == [(1000, 2000, 15, 14)]  # cell A: 14 of its 15 SP detections are static


def test_fine_cell_index_edges(con):
    r = con.execute(f"SELECT {qa.fine_cell_sql(0.5)} FROM (VALUES (-90.0, -180.0), (89.99, 179.99), (10.0, 180.0)) t(lat, lon)").fetchall()
    assert r == [(0, 0), (359, 719), (200, 0)]  # longitude 180 counts as -180


# ----------------------------------------------------------------------------- day / night
@pytest.mark.parametrize("lat, lon, date, hhmm, lo, hi", [
    (0.0, 0.0, "2026-03-20", 1200, 0, 5),       # equinox, noon on the prime meridian
    (0.0, 0.0, "2026-03-20", 0, 170, 180),      # midnight
    (0.0, 90.0, "2026-03-20", 600, 0, 5),       # 90 E at 06:00 UTC is local noon
    (60.0, 0.0, "2026-12-21", 1200, 82, 85),    # winter noon at 60 N: 60 + 23.4 degrees
    (70.0, 0.0, "2026-12-21", 1200, 91, 96),    # polar night: the sun stays below the horizon
])
def test_solar_zenith(con, lat, lon, date, hhmm, lo, hi):
    z = con.execute(f"SELECT {qa.zenith_sql()} FROM (SELECT {lat} AS lat, {lon} AS lon, DATE '{date}' AS acq_date, {hhmm} AS acq_time_utc)").fetchone()[0]
    assert lo <= z <= hi


def test_daynight_check_counts_agreement(tmp_path, con):
    rows = [row(lat=0.0, lon=0.0, acq_date="2026-03-20", acq_time_utc=1200, daynight="D"),            # agrees
            row(lat=0.0, lon=0.0, acq_date="2026-03-20", acq_time_utc=0, daynight="N", sensor="VIIRS_SNPP", satellite="N"),  # agrees
            row(lat=0.0, lon=0.0, acq_date="2026-03-20", acq_time_utc=1201, daynight="N", data_level="NRT", type=None),     # disagrees
            row(lat=0.0, lon=0.0, acq_date="2026-03-20", acq_time_utc=1202, daynight="D", data_level="NRT", type=None)]    # agrees
    out = {(s, lvl): (n, dec, ag) for s, lvl, n, dec, ag in qa.daynight_check(con, write(tmp_path / "det", rows), pct=100)}
    assert out[("MODIS", "SP")] == (1, 1, 1)
    assert out[("VIIRS_SNPP", "SP")] == (1, 1, 1)
    assert out[("MODIS", "NRT")] == (2, 2, 1)


# ------------------------------------------------------------------------------ end to end
def test_run_writes_the_summary_and_never_changes_the_data(tmp_path):
    det = tmp_path / "det"
    write(det, mask_rows() + [row(acq_time_utc=1), row(acq_time_utc=1)])
    before = sorted((p.relative_to(det).as_posix(), p.stat().st_size) for p in det.rglob("*.parquet"))
    out = tmp_path / "qa"
    res = qa.run(det, out, tmp=tmp_path / "dbtmp", zips=tmp_path / "nozips")
    assert (out / "qa_summary.md").exists() and (out / "qa_results.json").exists()
    text = (out / "qa_summary.md").read_text(encoding="utf-8")
    for heading in ("Value domains", "Exact duplicates", "Filter funnel", "Static-source mask", "Day/night"):
        assert heading in text
    assert res["unzipped"] == (0, 0)
    after = sorted((p.relative_to(det).as_posix(), p.stat().st_size) for p in det.rglob("*.parquet"))
    assert before == after
