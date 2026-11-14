"""CSV export (T-038). All data are SYNTHETIC test products built in conftest."""

import csv
import io
from typing import Any

import pytest
from fastapi.testclient import TestClient

from fire_api import custom
from fire_api.export import COLUMNS, RAW_COLUMNS, build_csv
from fire_api.models import EntityMonth, Metadata
from tests.conftest import METADATA
from tests.test_endpoints import _entity_record

URL = "/api/export.csv"


def parse(content: bytes) -> tuple[list[str], list[list[str]], list[dict[str, str]]]:
    text = content.decode("utf-8")
    assert text.startswith("﻿")
    lines = text[1:].split("\r\n")
    header = [ln for ln in lines if ln.startswith("#")]
    body = "\r\n".join(ln for ln in lines if not ln.startswith("#"))
    rows = list(csv.reader(io.StringIO(body, newline="")))
    rows = [r for r in rows if r]
    return header, rows, [dict(zip(rows[0], r, strict=True)) for r in rows[1:]]


class TestPreset:
    def test_columns_rows_and_order(self, client: TestClient) -> None:
        r = client.get(URL, params={"entity_type": "COUNTRY", "entity_id": "IDN"})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/csv")
        _, rows, records = parse(r.content)
        assert rows[0] == [*COLUMNS, *RAW_COLUMNS]
        assert [(x["year"], x["month"]) for x in records] == [
            ("2020", "1"),
            ("2020", "2"),
            ("2020", "3"),
        ]
        jan = records[0]
        assert jan["verdict"] == "ABOVE_NORMAL"
        assert jan["pct_of_normal"] == "140.0"
        assert jan["raw_AQUA_MODIS"] == "5" and jan["raw_SNPP_VIIRS"] == "7"
        assert jan["raw_TERRA_MODIS"] == ""  # absent, not 0
        assert jan["witnesses_used"] == "SNPP_VIIRS"

    def test_filename_and_synthetic_prefix(self, client: TestClient) -> None:
        r = client.get(URL, params={"entity_type": "COUNTRY", "entity_id": "IDN"})
        assert (
            r.headers["content-disposition"]
            == 'attachment; filename="SYNTHETIC_fire-harmonization_COUNTRY_IDN_SYNTHETIC-test.csv"'
        )

    def test_header_lines(self, client: TestClient) -> None:
        r = client.get(URL, params={"entity_type": "COUNTRY", "entity_id": "IDN"})
        header, _, _ = parse(r.content)
        joined = "\n".join(header)
        assert "# data_status: SYNTHETIC" in joined
        assert "# method_version: SYNTHETIC-test" in joined
        assert "# contract_version: 0.1.0" in joined
        assert "# generated_at: 2026-11-14T00:00:00Z" in joined
        assert "not fire counts or burned area" in joined
        assert "NASA's Fire Information for Resource Management System" in joined
        assert "doi:" in joined

    def test_null_is_empty_and_zero_is_zero(self, client: TestClient) -> None:
        # BRA has p_above 0.0 (a real zero) and the SA continent has nulls.
        _, _, brazil = parse(
            client.get(URL, params={"entity_type": "COUNTRY", "entity_id": "BRA"}).content
        )
        assert brazil[0]["p_above"] == "0.0"
        _, _, sa = parse(
            client.get(URL, params={"entity_type": "CONTINENT", "entity_id": "SA"}).content
        )
        assert sa[0]["p_above"] == "" and sa[0]["verdict"] == "CANNOT_DETERMINE"
        assert sa[0]["raw_SNPP_VIIRS"] == ""

    def test_unknown_entity_404(self, client: TestClient) -> None:
        r = client.get(URL, params={"entity_type": "COUNTRY", "entity_id": "ZZZ"})
        assert r.status_code == 404

    def test_missing_products_503(self, empty_client: TestClient) -> None:
        r = empty_client.get(URL, params={"entity_type": "COUNTRY", "entity_id": "IDN"})
        assert r.status_code == 503


class TestParameters:
    @pytest.mark.parametrize(
        "params",
        [
            {},
            {"entity_type": "COUNTRY"},
            {"entity_id": "IDN"},
            {"entity_type": "PLANET", "entity_id": "X"},
            {"entity_type": "COUNTRY", "entity_id": "IDN", "bbox": "99,0,101,1"},
            {"bbox": "a,b,c,d"},
            {"bbox": "1,2,3"},
            {"bbox": "nan,0,1,1"},
        ],
    )
    def test_invalid_combinations_give_400(
        self, client: TestClient, params: dict[str, str]
    ) -> None:
        assert client.get(URL, params=params).status_code == 400

    @pytest.mark.parametrize("bbox", ["101,0,99,1", "99,1,101,0", "-181,0,10,1", "0,-91,10,1"])
    def test_out_of_range_bbox_gives_422(self, client: TestClient, bbox: str) -> None:
        assert client.get(URL, params={"bbox": bbox}).status_code == 422

    def test_bbox_without_cells_gives_422(self, client: TestClient) -> None:
        assert client.get(URL, params={"bbox": "99,0.3,101,0.4"}).status_code == 422


class TestCustom:
    def test_503_until_harmonize_area_exists(self, client: TestClient) -> None:
        r = client.get(URL, params={"bbox": "99,0,101,1"})
        assert r.status_code == 503
        assert "not available yet" in r.json()["detail"]

    def test_custom_rows_and_filename(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake(cell_ids: list[str], months: Any = None) -> list[dict[str, Any]]:
            return [
                {**_entity_record("CUSTOM", "custom_x", "Custom area", m), "n_cells": len(cell_ids)}
                for m in (1, 2)
            ]

        monkeypatch.setattr(custom, "load_harmonize_area", lambda: fake)
        r = client.get(URL, params={"bbox": "99,0,101,1"})
        assert r.status_code == 200
        _, _, records = parse(r.content)
        assert [x["entity_type"] for x in records] == ["CUSTOM", "CUSTOM"]
        assert records[0]["n_cells"] == "2"
        assert "CUSTOM_99-0-101-1" in r.headers["content-disposition"]


class TestSpreadsheetSafety:
    def _record(self, **kw: Any) -> EntityMonth:
        return EntityMonth.model_validate({**_entity_record("COUNTRY", "X", "n", 1), **kw})

    def test_text_cells_starting_with_a_formula_character_are_prefixed(self) -> None:
        meta = Metadata.model_validate(METADATA)
        rec = self._record(entity_name="=HYPERLINK(1)")
        _, _, rows = parse(build_csv([rec], meta, "x"))
        assert rows[0]["entity_name"] == "'=HYPERLINK(1)"

    def test_negative_numbers_are_not_prefixed(self) -> None:
        meta = Metadata.model_validate(METADATA)
        rec = self._record(estimate=-1.5)
        _, _, rows = parse(build_csv([rec], meta, "x"))
        assert rows[0]["estimate"] == "-1.5"

    def test_commas_and_quotes_are_escaped(self) -> None:
        meta = Metadata.model_validate(METADATA)
        rec = self._record(entity_name='Korea, "Rep."')
        _, _, rows = parse(build_csv([rec], meta, "x"))
        assert rows[0]["entity_name"] == 'Korea, "Rep."'

    def test_real_data_status(self) -> None:
        meta = Metadata.model_validate({**METADATA, "synthetic": False})
        header, _, _ = parse(build_csv([], meta, "x"))
        assert "# data_status: REAL" in header
