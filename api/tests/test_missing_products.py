"""Missing products give the documented 503, never a crash or a fixture fallback (T-039).

All data are SYNTHETIC test products built here."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fire_api.main import app
from tests.conftest import METADATA, build_products


@pytest.fixture
def raw_only_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    build_products(tmp_path)
    for name in (
        "cell_month_harmonized.parquet",
        "entity_month.parquet",
        "validation_results.json",
    ):
        (tmp_path / name).unlink()
    meta = {**METADATA, "method_version": "0.1.0-raw-only", "synthetic": True}
    (tmp_path / "metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    monkeypatch.setenv("PRODUCTS_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def raw_client(raw_only_dir: Path) -> TestClient:
    return TestClient(app)


class TestMissingProducts:
    @pytest.mark.parametrize(
        "url",
        [
            "/api/entities?type=COUNTRY",
            "/api/series?entity_type=GLOBAL&entity_id=GLOBAL",
            "/api/evidence?entity_type=GLOBAL&entity_id=GLOBAL&year=2020&month=1",
            "/api/anomalies?year=2020&month=1",
            "/api/validation",
            "/api/export.csv?entity_type=GLOBAL&entity_id=GLOBAL",
        ],
    )
    def test_endpoints_that_need_a_missing_product_give_503(
        self, raw_client: TestClient, url: str
    ) -> None:
        r = raw_client.get(url)
        assert r.status_code == 503
        assert "Data are not available right now" in r.json()["detail"]

    def test_map_without_the_harmonized_product_gives_503(self, raw_client: TestClient) -> None:
        r = raw_client.get("/api/map?year=2020&month=1&layer=raw")
        assert r.status_code == 503
        assert "cell_month_harmonized.parquet" in r.json()["detail"]

    def test_meta_is_still_served_and_says_raw_only(self, raw_client: TestClient) -> None:
        assert raw_client.get("/api/meta").json()["method_version"] == "0.1.0-raw-only"

    def test_map_with_no_products_gives_503(self, empty_client: TestClient) -> None:
        assert empty_client.get("/api/map?year=2020&month=1&layer=raw").status_code == 503
