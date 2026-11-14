"""Endpoint tests on SYNTHETIC products (see conftest.py). Not NASA observations."""

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from fire_api import custom, products
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
from tests.conftest import HARMONIZED_ROWS, build_products


def _by_id(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {i[key]: i for i in items}


class TestMetaAndValidation:
    def test_meta_returns_the_metadata_object(self, client: TestClient) -> None:
        body = client.get("/api/meta").json()
        Metadata.model_validate(body)
        assert body["synthetic"] is True
        assert body["data_snapshot"]["api_pulled"] is None

    def test_validation_is_served_as_is_failures_included(self, client: TestClient) -> None:
        body = client.get("/api/validation").json()
        ValidationResults.model_validate(body)
        assert body["tests"][0]["status"] == "FAIL"
        assert body["tests"][0]["measured"] == {"value": 1.5, "other": None}

    def test_missing_products_give_503(self, empty_client: TestClient) -> None:
        for path in ("/api/meta", "/api/validation", "/api/map?year=2020&month=1&layer=verdict"):
            response = empty_client.get(path)
            assert response.status_code == 503, path
            assert "not available" in response.json()["detail"]


class TestProductsDir:
    def test_default_is_data_products(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PRODUCTS_DIR", raising=False)
        assert products.products_dir() == Path("data/products")

    def test_an_empty_value_counts_as_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PRODUCTS_DIR", "")
        assert products.products_dir() == Path("data/products")

    def test_the_environment_value_is_used_and_read_on_every_call(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("PRODUCTS_DIR", str(tmp_path))
        assert products.products_dir() == tmp_path


class TestEntities:
    def test_countries_have_a_bbox_derived_from_their_cells(self, client: TestClient) -> None:
        items = client.get("/api/entities", params={"type": "COUNTRY"}).json()
        for item in items:
            EntityItem.model_validate(item)
        ids = _by_id(items, "entity_id")
        assert list(ids) == ["BRA", "IDN"]
        assert ids["IDN"]["bbox"] == [100.0, 0.0, 100.5, 1.0]  # [W, S, E, N]
        assert ids["BRA"]["bbox"] == [-50.0, -10.0, -49.5, -9.5]
        assert ids["IDN"]["entity_name"] == "Indonesia"

    def test_entity_without_cells_is_not_listed(self, client: TestClient) -> None:
        items = client.get("/api/entities", params={"type": "COUNTRY"}).json()
        assert "XXX" not in {i["entity_id"] for i in items}

    def test_continents(self, client: TestClient) -> None:
        items = client.get("/api/entities", params={"type": "CONTINENT"}).json()
        assert [i["entity_id"] for i in items] == ["AS", "SA"]

    @pytest.mark.parametrize("value", ["country", "GLOBAL", "CELL", "nonsense"])
    def test_type_must_be_uppercase_country_or_continent(
        self, client: TestClient, value: str
    ) -> None:
        assert client.get("/api/entities", params={"type": value}).status_code == 400

    def test_type_is_required(self, client: TestClient) -> None:
        assert client.get("/api/entities").status_code == 400


class TestMap:
    URL = "/api/map?year=2020&month=1&layer={layer}"

    def test_one_record_per_cell_with_bounds_and_harmonized_fields(
        self, client: TestClient
    ) -> None:
        body = client.get(self.URL.format(layer="verdict")).json()
        for record in body:
            MapCell.model_validate(record)
        assert [r["cell_id"] for r in body] == ["c1", "c2", "c3"]
        c1 = body[0]
        assert (c1["lat_min"], c1["lat_max"], c1["lon_min"], c1["lon_max"]) == (
            0.0,
            0.5,
            100.0,
            100.5,
        )
        assert c1["verdict"] == "ABOVE_NORMAL"
        assert c1["witnesses_used"] == ["SNPP_VIIRS"]

    def test_values_are_returned_as_stored_null_stays_null_and_zero_stays_zero(
        self, client: TestClient
    ) -> None:
        by_id = _by_id(client.get(self.URL.format(layer="harmonized")).json(), "cell_id")
        assert by_id["c2"]["estimate"] is None
        assert by_id["c2"]["pct_of_normal"] is None
        assert by_id["c2"]["raw_combined_cell_days"] == 0
        assert by_id["c3"]["estimate"] == 0.0
        assert by_id["c3"]["baseline_median"] == 0.0
        assert by_id["c3"]["verdict"] == "NO_DETECTED_ACTIVITY"
        assert by_id["c1"]["estimate"] == 10.0  # not altered

    def test_every_layer_returns_the_same_payload(self, client: TestClient) -> None:
        payloads = [client.get(self.URL.format(layer=layer)).json() for layer in
                    ("verdict", "raw", "harmonized")]  # fmt: skip
        assert payloads[0] == payloads[1] == payloads[2]

    def test_other_months_only_return_their_cells(self, client: TestClient) -> None:
        body = client.get("/api/map?year=2020&month=2&layer=raw").json()
        assert [r["cell_id"] for r in body] == ["c1"]

    def test_a_month_with_no_rows_is_an_empty_list(self, client: TestClient) -> None:
        response = client.get("/api/map?year=1999&month=5&layer=raw")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.parametrize(
        "query",
        [
            "year=2020&month=1&layer=other",
            "year=2020&month=13&layer=raw",
            "year=2020&month=0&layer=raw",
            "year=abc&month=1&layer=raw",
            "month=1&layer=raw",
            "year=2020&month=1",
        ],
    )
    def test_invalid_parameters_give_400(self, client: TestClient, query: str) -> None:
        response = client.get(f"/api/map?{query}")
        assert response.status_code == 400
        assert "detail" in response.json()

    def test_a_stored_value_outside_the_contract_is_reported_not_coerced(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bad = list(HARMONIZED_ROWS)
        row = list(bad[0])
        row[bad[0].index("ABOVE_NORMAL")] = "MAYBE_ABOVE"
        bad[0] = tuple(row)
        build_products(tmp_path, harmonized_rows=bad)
        monkeypatch.setenv("PRODUCTS_DIR", str(tmp_path))
        response = TestClient(app).get("/api/map?year=2020&month=1&layer=verdict")
        assert response.status_code == 503
        assert "data contract" in response.json()["detail"]


class TestSeries:
    def test_series_is_ordered_by_year_then_month(self, client: TestClient) -> None:
        body = client.get("/api/series?entity_type=COUNTRY&entity_id=IDN").json()
        for record in body:
            EntityMonth.model_validate(record)
        assert [(r["year"], r["month"]) for r in body] == [(2020, 1), (2020, 2), (2020, 3)]

    def test_raw_by_witness_stays_a_json_string_in_the_series(self, client: TestClient) -> None:
        first = client.get("/api/series?entity_type=COUNTRY&entity_id=IDN").json()[0]
        assert first["raw_by_witness"] == '{"AQUA_MODIS": 5, "SNPP_VIIRS": 7}'

    def test_global_and_continent_series(self, client: TestClient) -> None:
        assert len(client.get("/api/series?entity_type=GLOBAL&entity_id=GLOBAL").json()) == 1
        assert len(client.get("/api/series?entity_type=CONTINENT&entity_id=AS").json()) == 1

    def test_unknown_entity_gives_404(self, client: TestClient) -> None:
        response = client.get("/api/series?entity_type=COUNTRY&entity_id=ZZZ")
        assert response.status_code == 404
        assert "ZZZ" in response.json()["detail"]

    @pytest.mark.parametrize("entity_type", ["CELL", "CUSTOM", "planet"])
    def test_entity_types_not_stored_in_entity_month_give_400(
        self, client: TestClient, entity_type: str
    ) -> None:
        assert client.get(f"/api/series?entity_type={entity_type}&entity_id=x").status_code == 400


class TestEvidence:
    URL = "/api/evidence?entity_type={t}&entity_id={i}&year={y}&month={m}"

    def test_raw_by_witness_is_decoded_into_an_object(self, client: TestClient) -> None:
        body = client.get(self.URL.format(t="COUNTRY", i="IDN", y=2020, m=1)).json()
        EntityEvidence.model_validate(body)
        assert body["raw_by_witness"] == {"AQUA_MODIS": 5, "SNPP_VIIRS": 7}
        assert body["verdict"] == "ABOVE_NORMAL"

    def test_null_raw_by_witness_stays_null(self, client: TestClient) -> None:
        body = client.get(self.URL.format(t="CONTINENT", i="SA", y=2020, m=1)).json()
        assert body["raw_by_witness"] is None
        assert body["p_above"] is None

    def test_unknown_entity_and_missing_month_give_404(self, client: TestClient) -> None:
        assert client.get(self.URL.format(t="COUNTRY", i="ZZZ", y=2020, m=1)).status_code == 404
        assert client.get(self.URL.format(t="COUNTRY", i="IDN", y=2019, m=1)).status_code == 404

    def test_invalid_parameters_give_400(self, client: TestClient) -> None:
        assert client.get(self.URL.format(t="COUNTRY", i="IDN", y=2020, m=13)).status_code == 400
        assert client.get(self.URL.format(t="PLANET", i="IDN", y=2020, m=1)).status_code == 400


class TestAnomalies:
    def test_only_confident_verdicts_ordered_by_max_probability(self, client: TestClient) -> None:
        body = client.get("/api/anomalies?year=2020&month=1&limit=10").json()
        for record in body:
            Anomaly.model_validate(record)
        assert {r["verdict"] for r in body} <= {"ABOVE_NORMAL", "BELOW_NORMAL"}
        # BRA 0.95 and GLOBAL 0.95 tie (then entity_type, entity_id), IDN 0.9, AS 0.7.
        assert [(r["entity_type"], r["entity_id"]) for r in body] == [
            ("COUNTRY", "BRA"),
            ("GLOBAL", "GLOBAL"),
            ("COUNTRY", "IDN"),
            ("CONTINENT", "AS"),
        ]

    def test_cannot_determine_is_excluded(self, client: TestClient) -> None:
        body = client.get("/api/anomalies?year=2020&month=1&limit=10").json()
        assert "SA" not in {r["entity_id"] for r in body}

    def test_limit_applies(self, client: TestClient) -> None:
        body = client.get("/api/anomalies?year=2020&month=1&limit=2").json()
        assert len(body) == 2

    @pytest.mark.parametrize("limit", ["0", "-1", "501", "x"])
    def test_invalid_limit_gives_400(self, client: TestClient, limit: str) -> None:
        assert client.get(f"/api/anomalies?year=2020&month=1&limit={limit}").status_code == 400

    def test_a_month_with_none_is_an_empty_list(self, client: TestClient) -> None:
        assert client.get("/api/anomalies?year=2020&month=2&limit=5").json() == []


class TestCustomArea:
    URL = "/api/series/custom"

    def test_503_until_harmonize_area_exists(self, client: TestClient) -> None:
        response = client.post(self.URL, json={"bbox": [99, -1, 101, 2]})
        assert response.status_code == 503
        assert "not available yet" in response.json()["detail"]

    def test_calls_harmonize_area_with_the_cells_whose_centres_are_inside(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[tuple[list[str], Any]] = []

        def fake_harmonize_area(cell_ids: list[str], months: Any = None) -> list[dict[str, Any]]:
            calls.append((cell_ids, months))
            return [
                {
                    **_entity_record("CUSTOM", "custom_x", "Custom area", month),
                    "n_cells": len(cell_ids),
                }
                for month in (2, 1)
            ]

        monkeypatch.setattr(custom, "load_harmonize_area", lambda: fake_harmonize_area)
        # c1 (centre 0.25, 100.25) and c2 (0.75, 100.25) are inside; c3 and c4 are not.
        response = client.post(self.URL, json={"bbox": [99, 0, 101, 1]})
        assert response.status_code == 200
        assert calls == [(["c1", "c2"], None)]
        body = response.json()
        assert [r["entity_type"] for r in body] == ["CUSTOM", "CUSTOM"]
        assert body[0]["month"] == 2  # returned as given by harmonize_area, not re-ordered
        assert body[0]["n_cells"] == 2

    def test_cell_selection_uses_the_centre_not_the_edges(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: list[list[str]] = []

        def fake(cell_ids: list[str], months: Any = None) -> list[dict[str, Any]]:
            seen.append(cell_ids)
            return []

        monkeypatch.setattr(custom, "load_harmonize_area", lambda: fake)
        # The box covers only the edge of c1 (0 to 0.5): its centre 0.25 is outside 0.3 to 0.4.
        assert client.post(self.URL, json={"bbox": [99, 0.3, 101, 0.4]}).status_code == 422
        assert seen == []

    def test_a_record_that_breaks_the_contract_is_reported(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def bad(cell_ids: list[str], months: Any = None) -> list[dict[str, Any]]:
            return [{**_entity_record("CUSTOM", "c", "C", 1), "verdict": "MAYBE"}]

        monkeypatch.setattr(custom, "load_harmonize_area", lambda: bad)
        response = client.post(self.URL, json={"bbox": [99, 0, 101, 1]})
        assert response.status_code == 503
        assert "data contract" in response.json()["detail"]

    @pytest.mark.parametrize(
        "body",
        [
            {"bbox": [101, 0, 99, 1]},  # W >= E
            {"bbox": [99, 1, 101, 0]},  # S >= N
            {"bbox": [-181, 0, 10, 1]},
            {"bbox": [0, -91, 10, 1]},
            {"bbox": [99, 0, 101]},  # three numbers
            {"bbox": "nope"},
            {},
            {"polygon": [[0, 0], [1, 0], [1, 1]]},
        ],
    )
    def test_an_invalid_area_gives_422(self, client: TestClient, body: dict[str, Any]) -> None:
        assert client.post(self.URL, json=body).status_code == 422

    def test_an_area_with_no_cell_centres_gives_422(self, client: TestClient) -> None:
        response = client.post(self.URL, json={"bbox": [0, 0, 1, 1]})
        assert response.status_code == 422
        assert "No analysis cells" in response.json()["detail"]


def _entity_record(etype: str, eid: str, name: str, month: int) -> dict[str, Any]:
    return {
        "entity_type": etype, "entity_id": eid, "entity_name": name, "year": 2020, "month": month,
        "estimate": 1.0, "ci90_low": 0.5, "ci90_high": 1.5, "sd": 0.2,
        "raw_combined_cell_days": 3, "witnesses_used": ["SNPP_VIIRS"], "n_witnesses": 1,
        "disagreement_scale": None, "baseline_median": 1.0, "baseline_p25": 0.5,
        "baseline_p75": 1.5, "pct_of_normal": 100.0, "p_above": 0.1, "p_below": 0.1,
        "p_within": 0.8, "verdict": "WITHIN_NORMAL", "reason_codes": [],
        "data_level": "SP", "method_version": "SYNTHETIC-test", "n_cells": 1,
        "raw_by_witness": None,
    }  # fmt: skip
