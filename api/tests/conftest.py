"""SYNTHETIC contract products built inside the tests. Not NASA observations."""

import json
from pathlib import Path
from typing import Any

import duckdb
import pytest
from fastapi.testclient import TestClient

from fire_api import custom
from fire_api.main import app

HARMONIZED_COLUMNS = """
    cell_id VARCHAR, year INTEGER, month INTEGER,
    estimate DOUBLE, ci90_low DOUBLE, ci90_high DOUBLE, sd DOUBLE,
    raw_combined_cell_days INTEGER, witnesses_used VARCHAR[], n_witnesses INTEGER,
    disagreement_scale DOUBLE, baseline_median DOUBLE, baseline_p25 DOUBLE, baseline_p75 DOUBLE,
    pct_of_normal DOUBLE, p_above DOUBLE, p_below DOUBLE, p_within DOUBLE,
    verdict VARCHAR, reason_codes VARCHAR[], data_level VARCHAR, method_version VARCHAR
"""
ENTITY_COLUMNS = """
    entity_type VARCHAR, entity_id VARCHAR, entity_name VARCHAR, year INTEGER, month INTEGER,
    estimate DOUBLE, ci90_low DOUBLE, ci90_high DOUBLE, sd DOUBLE,
    raw_combined_cell_days INTEGER, witnesses_used VARCHAR[], n_witnesses INTEGER,
    disagreement_scale DOUBLE, baseline_median DOUBLE, baseline_p25 DOUBLE, baseline_p75 DOUBLE,
    pct_of_normal DOUBLE, p_above DOUBLE, p_below DOUBLE, p_within DOUBLE,
    verdict VARCHAR, reason_codes VARCHAR[], data_level VARCHAR, method_version VARCHAR,
    n_cells INTEGER, raw_by_witness VARCHAR
"""

# cell_id, lat_min, lat_max, lon_min, lon_max, country_iso3, continent
CELLS = [
    ("c1", 0.0, 0.5, 100.0, 100.5, "IDN", "AS"),
    ("c2", 0.5, 1.0, 100.0, 100.5, "IDN", "AS"),
    ("c3", -10.0, -9.5, -50.0, -49.5, "BRA", "SA"),
    ("c4", 20.0, 20.5, 10.0, 10.5, None, None),
]


def _harmonized(cell_id: str, year: int, month: int, **kw: Any) -> tuple[Any, ...]:
    row = {
        "estimate": 10.0, "ci90_low": 8.0, "ci90_high": 12.0, "sd": 1.0,
        "raw_combined_cell_days": 12, "witnesses_used": ["SNPP_VIIRS"], "n_witnesses": 1,
        "disagreement_scale": None, "baseline_median": 9.0, "baseline_p25": 6.0,
        "baseline_p75": 12.0, "pct_of_normal": 111.0, "p_above": 0.1, "p_below": 0.1,
        "p_within": 0.8, "verdict": "WITHIN_NORMAL", "reason_codes": [], "data_level": "SP",
        "method_version": "SYNTHETIC-test",
    }  # fmt: skip
    row.update(kw)
    return (cell_id, year, month, *row.values())


def _entity(etype: str, eid: str, name: str, year: int, month: int, **kw: Any) -> tuple[Any, ...]:
    raw = kw.pop("raw_by_witness", '{"SNPP_VIIRS": 12}')
    h = _harmonized(eid, year, month, **kw)
    return (etype, eid, name, year, month, *h[3:], 2, raw)


HARMONIZED_ROWS = [
    _harmonized("c1", 2020, 1, verdict="ABOVE_NORMAL", p_above=0.9),
    _harmonized("c2", 2020, 1, estimate=None, ci90_low=None, ci90_high=None, sd=None,
                raw_combined_cell_days=0, pct_of_normal=None, p_above=None, p_below=None,
                p_within=None, verdict="CANNOT_DETERMINE", reason_codes=["OUTAGE"]),
    _harmonized("c3", 2020, 1, estimate=0.0, raw_combined_cell_days=0, baseline_median=0.0,
                pct_of_normal=None, verdict="NO_DETECTED_ACTIVITY", p_above=None,
                p_below=None, p_within=None),
    _harmonized("c1", 2020, 2),
]  # fmt: skip

# Inserted out of order on purpose, to test that series are ordered by year then month.
ENTITY_ROWS = [
    _entity("COUNTRY", "IDN", "Indonesia", 2020, 3),
    _entity("COUNTRY", "IDN", "Indonesia", 2020, 1, verdict="ABOVE_NORMAL", p_above=0.9,
            p_below=0.0, pct_of_normal=140.0, raw_by_witness='{"AQUA_MODIS": 5, "SNPP_VIIRS": 7}'),
    _entity("COUNTRY", "IDN", "Indonesia", 2020, 2),
    _entity("COUNTRY", "BRA", "Brazil", 2020, 1, verdict="BELOW_NORMAL", p_above=0.0,
            p_below=0.95, pct_of_normal=40.0),
    _entity("COUNTRY", "XXX", "No cells here", 2020, 1),
    _entity("CONTINENT", "AS", "Asia", 2020, 1, verdict="ABOVE_NORMAL", p_above=0.7, p_below=0.1,
            pct_of_normal=130.0),
    _entity("CONTINENT", "SA", "South America", 2020, 1, verdict="CANNOT_DETERMINE",
            p_above=None, p_below=None, p_within=None, raw_by_witness=None),
    _entity("GLOBAL", "GLOBAL", "Global (synthetic cells)", 2020, 1, verdict="BELOW_NORMAL",
            p_above=0.05, p_below=0.95, pct_of_normal=70.0),
]  # fmt: skip

METADATA = {
    "contract_version": "0.1.0",
    "method_version": "SYNTHETIC-test",
    "synthetic": True,
    "generated_at": "2026-11-14T00:00:00Z",
    "grid": {"analysis_deg": 0.5, "fine_deg": None},
    "baseline_years": [2003, 2022],
    "first_month": "2002-07",
    "latest_month": "2020-03",
    "provisional_months": ["2020-03"],
    "witnesses": ["AQUA_MODIS", "SNPP_VIIRS"],
    "data_snapshot": {"zips_downloaded": "2026-11-14", "api_pulled": None},
    "citation": "SYNTHETIC test data, not NASA observations.",
}

VALIDATION = {
    "contract_version": "0.1.0",
    "method_version": "SYNTHETIC-test",
    "generated_at": "2026-11-14T00:00:00Z",
    "synthetic": True,
    "tests": [
        {
            "test_id": "SYNTHETIC-A1",
            "family": "A",
            "title": "Example",
            "case": "Example case",
            "criterion": "Example criterion",
            "threshold": "SYNTHETIC placeholder",
            "measured": {"value": 1.5, "other": None},
            "status": "FAIL",
            "notes": "SYNTHETIC EXAMPLE — not a result",
        }
    ],
}


def _write_parquet(directory: Path, name: str, columns: str, rows: list[tuple[Any, ...]]) -> None:
    con = duckdb.connect()
    con.execute(f"CREATE TABLE t ({columns})")
    marks = ", ".join("?" for _ in rows[0])
    con.executemany(f"INSERT INTO t VALUES ({marks})", rows)
    con.execute(f"COPY t TO '{directory / name}' (FORMAT PARQUET)")
    con.close()


def build_products(directory: Path, harmonized_rows: list[tuple[Any, ...]] | None = None) -> None:
    cols = """cell_id VARCHAR, lat_min DOUBLE, lat_max DOUBLE, lon_min DOUBLE, lon_max DOUBLE,
              lat_c DOUBLE, lon_c DOUBLE, area_km2 DOUBLE, country_iso3 VARCHAR,
              continent VARCHAR, fire_region VARCHAR, stratum_id VARCHAR"""
    cell_rows = [
        (cid, a, b, c, d, (a + b) / 2, (c + d) / 2, 3000.0, iso, cont, "REG", "STR")
        for cid, a, b, c, d, iso, cont in CELLS
    ]
    _write_parquet(directory, "cells.parquet", cols, cell_rows)
    _write_parquet(
        directory, "cell_month_harmonized.parquet", HARMONIZED_COLUMNS,
        harmonized_rows or HARMONIZED_ROWS,
    )  # fmt: skip
    _write_parquet(directory, "entity_month.parquet", ENTITY_COLUMNS, ENTITY_ROWS)
    (directory / "metadata.json").write_text(json.dumps(METADATA), encoding="utf-8")
    (directory / "validation_results.json").write_text(json.dumps(VALIDATION), encoding="utf-8")


@pytest.fixture(autouse=True)
def _fresh_custom_cache() -> None:
    """No custom-area result survives from one test to the next."""
    custom.clear_cache()


@pytest.fixture
def products_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    build_products(tmp_path)
    monkeypatch.setenv("PRODUCTS_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def client(products_dir: Path) -> TestClient:
    return TestClient(app)


@pytest.fixture
def empty_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """A client whose products directory has no products."""
    monkeypatch.setenv("PRODUCTS_DIR", str(tmp_path))
    return TestClient(app)
