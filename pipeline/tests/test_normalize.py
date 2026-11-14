"""Tests for pipeline/normalize.py on small synthetic CSV zips (T-003).

    python -m pytest pipeline/tests/test_normalize.py -q
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import normalize as nm

MODIS_HEADER = "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight,type"
VIIRS_HEADER = "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_ti5,frp,daynight,type"
NRT_MODIS_HEADER = "latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,instrument,confidence,version,bright_t31,frp,daynight"

MODIS_BRAZIL = [
    "-4.05,-49.05,300.3,2.1,1.4,2002-07-05,0126,Aqua,MODIS,23,6.2,285,8.8,N,0",     # LOW
    "-4.06,-49.06,310.0,1.0,1.0,2002-07-05,1326,Aqua,MODIS,30,6.2,290,9.1,D,0",     # NOMINAL (boundary)
    "-4.07,-49.07,320.0,1.0,1.0,2002-07-06,1326,Terra,MODIS,79,6.2,291,9.2,D,0",    # NOMINAL (boundary)
    "-4.08,-49.08,330.0,1.0,1.0,2002-07-06,2359,Terra,MODIS,80,6.2,292,9.3,N,2",    # HIGH (boundary)
]
MODIS_IVORY = ["5.0,-4.0,300.0,1.0,1.0,2002-08-01,0005,Aqua,MODIS,55,6.03,280,5.0,N,3"]


def make_zip(path: Path, prefix: str, year: int, header: str, files: dict[str, list[str]], extra: dict[str, bytes] | None = None):
    with zipfile.ZipFile(path, "w") as z:
        for country, rows in files.items():
            z.writestr(f"{prefix}/{year}/{prefix}_{year}_{country}.csv", header + "\n" + "\n".join(rows) + ("\n" if rows else ""))
        for name, data in (extra or {}).items():
            z.writestr(name, data)


@pytest.fixture
def env(tmp_path):
    paths = nm.Paths(raw=tmp_path / "raw", out=tmp_path / "out", tmp=tmp_path / "extract", db_tmp=tmp_path / "dbtmp")
    (paths.raw / "zips").mkdir(parents=True)
    return paths


def read(paths, sensor, year):
    f = nm.part_dir(paths, sensor, year) / "detections.parquet"
    return duckdb.sql(f"SELECT * FROM read_parquet('{f.as_posix()}')").df()


def test_modis_zip_is_normalized(env):
    make_zip(env.raw / "zips" / "modis_2002_all_countries.zip", "modis", 2002, MODIS_HEADER,
             {"Brazil": MODIS_BRAZIL, "Cote_d_Ivoire": MODIS_IVORY, "Empty": []},
             extra={"modis/2002/AttributesReadme.txt": b"not a csv"})
    con = nm.connect(env)
    stats = nm.run_zip(env, "modis", 2002, con)
    df = read(env, "MODIS", 2002).drop(columns=["year"], errors="ignore")
    assert list(df.columns) == nm.SCHEMA
    assert len(df) == 5 and stats["rows_csv"] == stats["rows_parquet"] == 5
    assert stats["source_files"] == 2  # the empty file adds no rows; the readme is not read
    assert set(df.sensor) == {"MODIS"} and set(df.data_level) == {"SP"}
    # confidence classes at the FIRMS boundaries: <30 LOW, 30-79 NOMINAL, >=80 HIGH
    got = dict(zip(df.confidence_raw, df.confidence_class, strict=True))
    assert got == {"23": "LOW", "30": "NOMINAL", "79": "NOMINAL", "80": "HIGH", "55": "NOMINAL"}
    assert set(df.version) == {"6.2", "6.03"}  # kept as text, never re-formatted
    assert df.acq_time_utc.tolist().count(5) == 1  # HHMM "0005" kept as the integer 5, not dropped
    assert set(df.country_name) == {"Brazil", "Cote d Ivoire"}
    assert df.type.tolist().count(3) == 1
    assert not any(stats["cast_problems"].values())


def test_viirs_confidence_letters_and_unexpected_satellite(env):
    rows = [
        "1.0,2.0,330.0,0.4,0.4,2012-01-20,0346,N,VIIRS,l,1,300.0,5.0,D,0",
        "1.1,2.1,330.0,0.4,0.4,2012-01-20,0347,N,VIIRS,n,1,300.0,5.0,D,0",
        "1.2,2.2,330.0,0.4,0.4,2012-01-21,0348,N,VIIRS,h,1,300.0,5.0,N,0",
        "1.3,2.3,330.0,0.4,0.4,2012-01-21,0349,N20,VIIRS,h,1,300.0,5.0,N,0",  # wrong satellite for this file
    ]
    make_zip(env.raw / "zips" / "viirs-snpp_2012_all_countries.zip", "viirs-snpp", 2012, VIIRS_HEADER, {"Peru": rows})
    stats = nm.run_zip(env, "viirs-snpp", 2012, nm.connect(env))
    df = read(env, "VIIRS_SNPP", 2012)
    assert df.confidence_class.tolist() == ["LOW", "NOMINAL", "HIGH", "HIGH"]
    assert stats["satellites_unexpected"] == ["N20"]  # recorded, not removed
    assert len(df) == 4


def test_bad_values_become_null_and_are_counted_never_dropped(env):
    rows = [
        "abc,-49.05,300.3,2.1,1.4,2002-07-05,0126,Aqua,MODIS,23,6.2,285,8.8,N,0",   # bad latitude
        "-4.06,-49.06,310.0,1.0,1.0,2002-13-45,1326,Aqua,MODIS,xx,6.2,290,9.1,D,0",  # bad date, bad confidence
        "-4.07,-49.07,320.0,1.0,1.0,2003-01-01,1326,Terra,MODIS,79,6.2,291,oops,D,9",  # outside year, bad frp
        ",-49.08,320.0,1.0,1.0,2002-07-07,1326,Terra,MODIS,79,6.2,291,9.0,D,0",  # empty latitude (missing, not a bad cast)
    ]
    make_zip(env.raw / "zips" / "modis_2002_all_countries.zip", "modis", 2002, MODIS_HEADER, {"Brazil": rows})
    stats = nm.run_zip(env, "modis", 2002, nm.connect(env))
    df = read(env, "MODIS", 2002)
    assert len(df) == 4 == stats["rows_parquet"]
    p = stats["cast_problems"]
    assert p["latitude"] == 1 and p["acq_date"] == 1 and p["confidence"] == 1 and p["frp"] == 1
    assert p["acq_date_outside_partition_year"] == 1
    assert p["rows_with_a_missing_key_field"] == 1
    assert df.lat.isna().sum() == 2 and df.acq_date.isna().sum() == 1  # null, not 0 and not dropped


def test_header_check_fails_loudly(env):
    make_zip(env.raw / "zips" / "modis_2002_all_countries.zip", "modis", 2002, "lat,lon,acq_date", {"Brazil": ["1,2,2002-07-05"]})
    with pytest.raises(RuntimeError, match="missing expected columns"):
        nm.run_zip(env, "modis", 2002, nm.connect(env))
    assert not nm.done(env, "MODIS", 2002)


def test_unexpected_columns_are_recorded(env):
    header = MODIS_HEADER + ",surprise"
    rows = [r + ",1" for r in MODIS_BRAZIL[:1]]
    make_zip(env.raw / "zips" / "modis_2002_all_countries.zip", "modis", 2002, header, {"Brazil": rows})
    stats = nm.run_zip(env, "modis", 2002, nm.connect(env))
    assert stats["unexpected_columns"] == ["surprise"]


def test_rerun_is_idempotent_and_force_redoes(env):
    make_zip(env.raw / "zips" / "modis_2002_all_countries.zip", "modis", 2002, MODIS_HEADER, {"Brazil": MODIS_BRAZIL})
    con = nm.connect(env)
    assert nm.run_zip(env, "modis", 2002, con)["rows_parquet"] == 4
    assert nm.run_zip(env, "modis", 2002, con) is None  # skipped
    assert nm.run_zip(env, "modis", 2002, con, force=True)["rows_parquet"] == 4
    assert not (env.tmp / "modis_2002").exists()  # the extracted CSVs are deleted


def test_extraction_ignores_path_tricks(env, tmp_path):
    zp = tmp_path / "evil.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("../outside.csv", "a,b\n1,2\n")
        z.writestr("modis/2002/modis_2002_Brazil.csv", MODIS_HEADER + "\n" + MODIS_BRAZIL[0] + "\n")
    dest = tmp_path / "work"
    n = nm.extract_csvs(zp, dest)
    assert n == 2 and not (tmp_path / "outside.csv").exists()  # nothing is written outside the work folder
    assert sorted(p.name for p in dest.iterdir()) == ["modis_2002_Brazil.csv", "outside.csv"]  # flat, base names only


def test_api_rows_have_levels_from_the_source_and_no_country(env):
    sp = env.raw / "api_2026" / "MODIS_SP"
    nrt = env.raw / "api_2026" / "MODIS_NRT"
    sp.mkdir(parents=True)
    nrt.mkdir(parents=True)
    (sp / "2026-01-01_5.csv").write_text(MODIS_HEADER + "\n-4.05,-49.05,300.3,2.1,1.4,2026-01-02,0126,Aqua,MODIS,23,6.2,285,8.8,N,0\n", encoding="utf-8")
    (nrt / "2026-09-01_2.csv").write_text(NRT_MODIS_HEADER + "\n-4.05,-49.05,300.3,2.1,1.4,2026-09-02,0126,Terra,MODIS,95,6.2NRT,285,8.8,N\n", encoding="utf-8")
    stats = nm.run_api(env, "MODIS", nm.connect(env))
    df = read(env, "MODIS", 2026)
    assert stats["rows_parquet"] == 2
    assert dict(zip(df.satellite, df.data_level, strict=True)) == {"Aqua": "SP", "Terra": "NRT"}
    assert df.country_name.isna().all()
    assert df.type.isna().sum() == 1  # the NRT row has no type
    assert df.version.tolist().count("6.2NRT") == 1


def test_counts_file_matches_the_parquet_files(env):
    make_zip(env.raw / "zips" / "modis_2002_all_countries.zip", "modis", 2002, MODIS_HEADER, {"Brazil": MODIS_BRAZIL})
    nm.run_zip(env, "modis", 2002, nm.connect(env))
    path = nm.write_counts(env)
    rows = [line.split("\t") for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows[0] == ["sensor", "year", "satellite", "data_level", "rows"]
    assert sum(int(r[4]) for r in rows[1:]) == 4
    assert {r[2] for r in rows[1:]} == {"Aqua", "Terra"}
    stats = json.loads((nm.part_dir(env, "MODIS", 2002) / "stats.json").read_text(encoding="utf-8"))
    assert stats["rows_by_satellite"] == {"Aqua": 2, "Terra": 2}
