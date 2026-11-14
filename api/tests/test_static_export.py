"""The static export (T-043): every file is the API's own answer, and the compact map layout
decodes back to exactly the API's records. All data are SYNTHETIC test products built here."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fire_api.static_export import (
    CELL_FIELDS,
    CellList,
    ExportError,
    decode_columns,
    encode_cells,
    encode_columns,
    export_static,
)

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "v0.1.0"


@pytest.fixture
def export_dir(products_dir: Path, tmp_path: Path) -> Path:
    out = tmp_path / "data"
    export_static(out, latest_months=3)
    return out


def test_every_file_is_the_apis_own_answer(client: TestClient, export_dir: Path) -> None:
    manifest = json.loads((export_dir / "manifest.json").read_text())
    assert manifest["synthetic"] is True
    assert json.loads((export_dir / "meta.json").read_text()) == client.get("/api/meta").json()
    assert (
        json.loads((export_dir / "validation.json").read_text())
        == client.get("/api/validation").json()
    )
    for kind in ("COUNTRY", "CONTINENT"):
        items = client.get(f"/api/entities?type={kind}").json()
        assert json.loads((export_dir / f"entities-{kind}.json").read_text()) == items
        for item in items:
            key = f"{kind}-{item['entity_id']}"
            expected = client.get(
                f"/api/series?entity_type={kind}&entity_id={item['entity_id']}"
            ).json()
            assert json.loads((export_dir / "series" / f"{key}.json").read_text()) == expected
            csv = client.get(f"/api/export.csv?entity_type={kind}&entity_id={item['entity_id']}")
            assert (export_dir / "export" / f"{key}.csv").read_bytes() == csv.content
    for label in manifest["months"]:
        year, month = label.split("-")
        expected = client.get(f"/api/anomalies?year={year}&month={month}&limit=500").json()
        assert json.loads((export_dir / "anomalies" / f"{label}.json").read_text()) == expected


def test_the_compact_map_decodes_to_exactly_the_apis_response(
    client: TestClient, export_dir: Path
) -> None:
    cells = json.loads((export_dir / "cells.json").read_text())
    manifest = json.loads((export_dir / "manifest.json").read_text())
    assert manifest["months"]
    for label in manifest["months"]:
        year, month = label.split("-")
        api = client.get(f"/api/map?year={year}&month={month}&layer=raw").json()
        encoded = json.loads((export_dir / "map" / f"{label}.json").read_text())
        assert decode_columns(encoded, cells) == api


def test_the_layout_round_trips_every_kind_of_column() -> None:
    records = [
        {"cell_id": f"c{i}", "lat_min": 0.0, "lat_max": 0.5, "lon_min": float(i),
         "lon_max": i + 0.5,
         "year": 2020, "month": 3, "estimate": None if i % 3 else float(i),
         "verdict": "CANNOT_DETERMINE" if i % 2 else "WITHIN_NORMAL",
         "reason_codes": [] if i % 2 else ["OUTAGE", "PROVISIONAL_NRT"],
         "witnesses_used": ["AQUA_MODIS"], "raw_combined_cell_days": i * 7}
        for i in range(40)
    ]  # fmt: skip
    encoded = encode_columns(records)
    columns = encoded["columns"]
    assert columns["year"] == {"const": 2020}
    assert "dict" in columns["verdict"] and "dict" in columns["reason_codes"]
    assert "values" in columns["raw_combined_cell_days"]
    assert decode_columns(encoded, encode_cells(records)) == records
    assert not set(CELL_FIELDS) & set(columns)


def test_months_with_different_cells_decode_through_the_cell_index() -> None:
    def rec(cell: str, lon: float) -> dict[str, object]:
        return {"cell_id": cell, "lat_min": 0.0, "lat_max": 0.5, "lon_min": lon,
                "lon_max": lon + 0.5,
                "year": 2020, "month": 3, "raw_combined_cell_days": 1}  # fmt: skip

    first = [rec("a", 0.0), rec("b", 1.0)]
    second = [rec("b", 1.0), rec("c", 2.0)]
    shared = CellList()
    for month in (first, second):
        index = shared.index_of(month)
        encoded = encode_columns(month)
        if index != list(range(len(index))):
            encoded["cell_index"] = index
        assert decode_columns(encoded, shared.columns()) == month
    moved = [{**rec("b", 1.0), "lon_min": 9.0}]
    with pytest.raises(ExportError, match="changes its bounds"):
        shared.index_of(moved)


def test_a_non_empty_directory_is_refused_unless_overwrite_and_only_our_own(
    products_dir: Path, tmp_path: Path
) -> None:
    out = tmp_path / "data"
    export_static(out, latest_months=1)
    with pytest.raises(ExportError, match="not empty"):
        export_static(out, latest_months=1)
    export_static(out, overwrite=True, latest_months=1)  # an earlier export: replaced
    other = tmp_path / "other"
    other.mkdir()
    (other / "mine.txt").write_text("keep")
    with pytest.raises(ExportError, match="not empty"):
        export_static(other, latest_months=1)
    with pytest.raises(ExportError, match="not an earlier export"):
        export_static(other, overwrite=True, latest_months=1)
    assert (other / "mine.txt").read_text() == "keep"


def test_the_synthetic_flag_and_versions_are_passed_through(export_dir: Path) -> None:
    meta = json.loads((export_dir / "meta.json").read_text())
    manifest = json.loads((export_dir / "manifest.json").read_text())
    assert manifest["synthetic"] == meta["synthetic"]
    assert manifest["contract_version"] == meta["contract_version"]
    assert manifest["method_version"] == meta["method_version"]
    assert "/" not in json.dumps(manifest)  # no path of this machine is written
