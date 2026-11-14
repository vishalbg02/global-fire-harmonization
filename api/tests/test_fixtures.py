"""The API against Member 2's SYNTHETIC fixtures (data/fixtures/v0.1.0, T-010).

Structural checks only: every record must validate against the contract models, and the
counts are compared with the fixture files themselves, not with numbers copied from a README.
"""

from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from fire_api.main import app
from fire_api.models import (
    Anomaly,
    EntityEvidence,
    EntityItem,
    EntityMonth,
    MapCell,
    Metadata,
    ValidationResults,
)

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "v0.1.0"

pytestmark = pytest.mark.skipif(not FIXTURES.is_dir(), reason="data/fixtures/v0.1.0 not present")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("PRODUCTS_DIR", str(FIXTURES))
    return TestClient(app)


def _count(sql: str, *params: object) -> int:
    con = duckdb.connect()
    try:
        return con.execute(sql, list(params)).fetchone()[0]  # type: ignore[index]
    finally:
        con.close()


def test_meta_and_validation_are_synthetic(client: TestClient) -> None:
    meta = Metadata.model_validate(client.get("/api/meta").json())
    assert meta.synthetic is True
    results = ValidationResults.model_validate(client.get("/api/validation").json())
    assert results.synthetic is True
    assert all(t.test_id.startswith("SYNTHETIC-") for t in results.tests)


@pytest.mark.parametrize("entity_type", ["COUNTRY", "CONTINENT"])
def test_entities_have_a_valid_bbox(client: TestClient, entity_type: str) -> None:
    items = client.get("/api/entities", params={"type": entity_type}).json()
    assert items
    for raw in items:
        item = EntityItem.model_validate(raw)
        west, south, east, north = item.bbox
        assert west < east
        assert south < north


def test_map_returns_every_cell_of_a_month_and_all_records_validate(client: TestClient) -> None:
    meta = client.get("/api/meta").json()
    year, month = (int(x) for x in meta["latest_month"].split("-"))
    body = client.get(f"/api/map?year={year}&month={month}&layer=verdict").json()
    expected = _count(
        "SELECT count(*) FROM read_parquet(?) WHERE year = ? AND month = ?",
        str(FIXTURES / "cell_month_harmonized.parquet"),
        year,
        month,
    )
    assert expected > 0
    assert len(body) == expected
    for record in body:
        MapCell.model_validate(record)


def test_every_verdict_in_the_fixtures_passes_through_the_map(client: TestClient) -> None:
    seen: set[str] = set()
    for year, month in [(2015, 9), (2019, 8), (2020, 8), (2004, 7), (2016, 2), (2024, 6)]:
        for record in client.get(f"/api/map?year={year}&month={month}&layer=raw").json():
            MapCell.model_validate(record)
            seen.add(record["verdict"])
    assert {"ABOVE_NORMAL", "BELOW_NORMAL", "WITHIN_NORMAL"} <= seen


def test_series_is_complete_and_ordered_for_every_listed_entity(client: TestClient) -> None:
    items = client.get("/api/entities", params={"type": "COUNTRY"}).json()
    for item in items:
        rows = client.get(
            "/api/series", params={"entity_type": "COUNTRY", "entity_id": item["entity_id"]}
        ).json()
        assert rows
        keys = [(r["year"], r["month"]) for r in rows]
        assert keys == sorted(keys)
        for r in rows:
            EntityMonth.model_validate(r)


def test_evidence_decodes_raw_by_witness_and_anomalies_are_ordered(client: TestClient) -> None:
    evidence = client.get(
        "/api/evidence",
        params={"entity_type": "COUNTRY", "entity_id": "IDN", "year": 2015, "month": 9},
    ).json()
    parsed = EntityEvidence.model_validate(evidence)
    assert parsed.raw_by_witness is None or isinstance(parsed.raw_by_witness, dict)

    body = client.get("/api/anomalies?year=2015&month=9&limit=20").json()
    scores = []
    for raw in body:
        a = Anomaly.model_validate(raw)
        scores.append(max(p for p in (a.p_above, a.p_below) if p is not None))
        assert a.verdict in {"ABOVE_NORMAL", "BELOW_NORMAL"}
    assert scores == sorted(scores, reverse=True)


def test_custom_area_series_comes_from_harmonize_area(client: TestClient) -> None:
    con = duckdb.connect()
    try:
        lat_c, lon_c = con.execute(
            "SELECT lat_c, lon_c FROM read_parquet(?) ORDER BY cell_id LIMIT 1",
            [str(FIXTURES / "cells.parquet")],
        ).fetchone()  # type: ignore[misc]
    finally:
        con.close()
    box = [lon_c - 0.1, lat_c - 0.1, lon_c + 0.1, lat_c + 0.1]
    response = client.post("/api/series/custom", json={"bbox": box})
    assert response.status_code == 200
    records = [EntityMonth.model_validate(r) for r in response.json()]
    assert records
    assert {r.entity_type for r in records} == {"CUSTOM"}
