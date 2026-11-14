"""Anomaly order (T-039 phase 2): larger probability, then the larger distance from normal
abs(ln(pct_of_normal / 100)) (missing or non-positive last), then entity_id ascending.

SYNTHETIC data built inside the tests, plus a check on the real products when they are present."""

import math
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from fire_api.main import app
from tests.conftest import ENTITY_COLUMNS, _entity, _write_parquet, build_products

ABOVE = {"verdict": "ABOVE_NORMAL"}
BELOW = {"verdict": "BELOW_NORMAL"}


def _client(directory: Path, monkeypatch: pytest.MonkeyPatch, rows: list[Any]) -> TestClient:
    build_products(directory)
    _write_parquet(directory, "entity_month.parquet", ENTITY_COLUMNS, rows)
    monkeypatch.setenv("PRODUCTS_DIR", str(directory))
    return TestClient(app)


def _ids(client: TestClient) -> list[str]:
    body = client.get("/api/anomalies?year=2020&month=1&limit=50").json()
    return [r["entity_id"] for r in body]


def test_probability_comes_first(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [
        _entity("COUNTRY", "AAA", "A", 2020, 1, p_above=0.90, pct_of_normal=900.0, **ABOVE),
        _entity("COUNTRY", "BBB", "B", 2020, 1, p_above=0.99, pct_of_normal=101.0, **ABOVE),
        _entity("COUNTRY", "CCC", "C", 2020, 1, p_below=0.95, pct_of_normal=10.0, **BELOW),
    ]
    assert _ids(_client(tmp_path, monkeypatch, rows)) == ["BBB", "CCC", "AAA"]


def test_ties_go_by_distance_from_normal_above_and_below(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Same probability. Distances: 400% and 25% are both 1.386 (4x and 1/4x, so entity_id
    # decides), 200% is 0.693, 80% is 0.223.
    rows = [
        _entity("COUNTRY", "DDD", "D", 2020, 1, p_above=1.0, pct_of_normal=80.0, **ABOVE),
        _entity("COUNTRY", "ZZZ", "Z", 2020, 1, p_above=1.0, pct_of_normal=400.0, **ABOVE),
        _entity("COUNTRY", "CCC", "C", 2020, 1, p_below=1.0, pct_of_normal=200.0, **BELOW),
        _entity("COUNTRY", "BBB", "B", 2020, 1, p_below=1.0, pct_of_normal=25.0, **BELOW),
    ]
    assert _ids(_client(tmp_path, monkeypatch, rows)) == ["BBB", "ZZZ", "CCC", "DDD"]


def test_missing_and_non_positive_pct_go_last_among_ties(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = [
        _entity("COUNTRY", "AAA", "A", 2020, 1, p_above=1.0, pct_of_normal=None, **ABOVE),
        _entity("COUNTRY", "BBB", "B", 2020, 1, p_below=1.0, pct_of_normal=0.0, **BELOW),
        _entity("COUNTRY", "CCC", "C", 2020, 1, p_below=1.0, pct_of_normal=-5.0, **BELOW),
        _entity("COUNTRY", "DDD", "D", 2020, 1, p_above=1.0, pct_of_normal=110.0, **ABOVE),
    ]
    # DDD has a distance; the other three have none (null, zero, negative) and go by id.
    assert _ids(_client(tmp_path, monkeypatch, rows)) == ["DDD", "AAA", "BBB", "CCC"]


def test_full_tie_goes_by_entity_id_and_is_stable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = [
        _entity("COUNTRY", name, name, 2020, 1, p_above=0.97, pct_of_normal=150.0, **ABOVE)
        for name in ("MMM", "CCC", "ZZZ", "AAA")
    ]
    client = _client(tmp_path, monkeypatch, rows)
    first = _ids(client)
    assert first == ["AAA", "CCC", "MMM", "ZZZ"]
    assert _ids(client) == first


REAL = Path(
    os.environ.get("PRODUCTS_DIR") or Path(__file__).resolve().parents[2] / "data" / "products"
)


def _is_real(name: str) -> bool:
    path = REAL / name
    return path.is_file() and path.stat().st_size > 1024  # an LFS pointer is about 130 bytes


@pytest.mark.skipif(
    not (_is_real("entity_month.parquet") and _is_real("cells.parquet")),
    reason="the products in data/products are Git LFS pointers: run `git lfs pull` "
    "(or set PRODUCTS_DIR to a folder with the real files)",
)
def test_real_products_2015_09_order_is_non_increasing_and_stable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PRODUCTS_DIR", str(REAL))
    client = TestClient(app)
    first = client.get("/api/anomalies?year=2015&month=9&limit=500").json()
    assert len(first) > 10

    def key(r: dict[str, Any]) -> tuple[float, float, str]:
        p = max(v for v in (r["p_above"], r["p_below"]) if v is not None)
        pct = r["pct_of_normal"]
        dist = abs(math.log(pct / 100.0)) if pct is not None and pct > 0 else -1.0
        return (-p, -dist, r["entity_id"])

    keys = [key(r) for r in first]
    assert keys == sorted(keys)
    assert client.get("/api/anomalies?year=2015&month=9&limit=500").json() == first
