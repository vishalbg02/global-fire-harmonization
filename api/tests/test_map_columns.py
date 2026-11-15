"""GET /api/map/cells and GET /api/map/columns against GET /api/map (T-073).

SYNTHETIC products (tests/conftest.py plus a few awkward values): not NASA observations.
The columnar endpoints must give back, field by field, exactly the values of GET /api/map.
One test runs on the real products and is skipped, with its reason, when they are Git LFS pointers.
"""

import gzip
import json
import os
from pathlib import Path
from typing import Any, ClassVar

import pytest
from fastapi.testclient import TestClient

from fire_api import map_cache, map_columns, products
from fire_api.columnar import CELL_FIELDS, decode_columns
from fire_api.main import app
from fire_api.models import MapLayer
from tests.conftest import CELLS, HARMONIZED_ROWS, _harmonized, build_products

LAYERS = [layer.value for layer in MapLayer]
PLAIN = {"Accept-Encoding": "identity"}

# Floats whose shortest form is awkward: a sum that is not exact, a tiny and a huge exponent.
AWKWARD = {
    "estimate": 0.1 + 0.2,
    "ci90_low": 1e-7,
    "ci90_high": 1.2345678901234567e22,
    "pct_of_normal": 100.00000000000001,
    "p_above": 0.30000000000000004,
}

# 2020-01: c1, c2, c3 (a null estimate, an empty reason list, a reason). 2020-02: c1 only (the first
# cell of the list). 2020-03: c2 and c4 (not the first cells of the list). 2020-04: one cell twice
# over the same values, so most columns are constant. 2020-05: no cells.
ROWS = [
    *HARMONIZED_ROWS,
    _harmonized(
        "c2",
        2020,
        3,
        verdict="BELOW_NORMAL",
        p_below=0.97,
        reason_codes=["WIDE_INTERVAL", "SINGLE_WITNESS"],
    ),
    _harmonized(
        "c4", 2020, 3, witnesses_used=["AQUA_MODIS", "SNPP_VIIRS"], n_witnesses=2, **AWKWARD
    ),
    _harmonized("c3", 2020, 4),
]


@pytest.fixture
def awkward_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    build_products(tmp_path, ROWS)
    monkeypatch.setenv("PRODUCTS_DIR", str(tmp_path))
    return TestClient(app)


def _json(client: TestClient, url: str) -> Any:
    response = client.get(url, headers=PLAIN)
    assert response.status_code == 200, response.text
    return response.json()


def _decoded(client: TestClient, year: int, month: int, layer: str) -> list[dict[str, Any]]:
    cells = _json(client, "/api/map/cells")["columns"]
    columns = _json(client, f"/api/map/columns?year={year}&month={month}&layer={layer}")
    return decode_columns(columns, cells)


def _text(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


class TestIdenticalToMap:
    @pytest.mark.parametrize("layer", LAYERS)
    @pytest.mark.parametrize("year_month", [(2020, 1), (2020, 2), (2020, 3), (2020, 4), (2020, 5)])
    def test_every_field_of_every_record(
        self, awkward_client: TestClient, layer: str, year_month: tuple[int, int]
    ) -> None:
        year, month = year_month
        expected = _json(awkward_client, f"/api/map?year={year}&month={month}&layer={layer}")
        got = _decoded(awkward_client, year, month, layer)
        assert len(got) == len(expected)
        fields = {*CELL_FIELDS, *map_columns.MONTH_FIELDS, *map_columns.field_set(MapLayer(layer))}
        for record, decoded in zip(expected, got, strict=True):
            assert set(decoded) == fields
            for name in fields:
                assert decoded[name] == record[name], name
                assert _text(decoded[name]) == _text(record[name]), name  # same digits, same type

    def test_floats_are_the_shortest_form_as_in_map(self, awkward_client: TestClient) -> None:
        columns = awkward_client.get(
            "/api/map/columns?year=2020&month=3&layer=verdict", headers=PLAIN
        ).text
        whole = awkward_client.get("/api/map?year=2020&month=3&layer=verdict", headers=PLAIN).text
        for token in (
            "0.30000000000000004",
            "1e-7",
            "1.2345678901234568e+22",
            "100.00000000000001",
        ):
            assert token in whole, token
            assert token in columns, token

    def test_null_empty_and_listed_values_survive(self, awkward_client: TestClient) -> None:
        by_id = {r["cell_id"]: r for r in _decoded(awkward_client, 2020, 1, "verdict")}
        assert by_id["c2"]["estimate"] is None
        assert by_id["c2"]["pct_of_normal"] is None
        assert by_id["c2"]["reason_codes"] == ["OUTAGE"]
        assert by_id["c1"]["reason_codes"] == []
        month3 = {r["cell_id"]: r for r in _decoded(awkward_client, 2020, 3, "verdict")}
        assert month3["c2"]["reason_codes"] == ["WIDE_INTERVAL", "SINGLE_WITNESS"]

    def test_fields_outside_the_layers_set_are_absent(self, awkward_client: TestClient) -> None:
        # A field outside the layer's set is absent: it is never invented.
        got = _decoded(awkward_client, 2020, 3, "verdict")
        assert all("baseline_p25" not in r and "sd" not in r for r in got)

    def test_months_with_other_cells_decode_to_the_right_cells(
        self, awkward_client: TestClient
    ) -> None:
        cells = _json(awkward_client, "/api/map/cells")
        assert cells["columns"]["cell_id"] == ["c1", "c2", "c3", "c4"]
        first = _json(awkward_client, "/api/map/columns?year=2020&month=2&layer=raw")
        assert "cell_index" not in first  # c1 is the first cell of the list
        other = _json(awkward_client, "/api/map/columns?year=2020&month=3&layer=raw")
        assert other["cell_index"] == [1, 3]
        ids = [r["cell_id"] for r in _decoded(awkward_client, 2020, 3, "raw")]
        assert ids == ["c2", "c4"]

    def test_empty_month(self, awkward_client: TestClient) -> None:
        body = _json(awkward_client, "/api/map/columns?year=2020&month=5&layer=raw")
        assert body["n"] == 0 and body["columns"] == {}
        assert _json(awkward_client, "/api/map?year=2020&month=5&layer=raw") == []

    def test_constant_columns_are_stored_once(self, awkward_client: TestClient) -> None:
        body = _json(awkward_client, "/api/map/columns?year=2020&month=1&layer=verdict")
        assert body["columns"]["year"] == {"const": 2020}
        assert body["columns"]["month"] == {"const": 1}
        single = _json(awkward_client, "/api/map/columns?year=2020&month=4&layer=verdict")
        assert all("const" in c for c in single["columns"].values())

    def test_the_cell_list_is_every_cell_once_in_map_order(
        self, awkward_client: TestClient
    ) -> None:
        cells = _json(awkward_client, "/api/map/cells")
        assert cells["n"] == 4
        expected = {
            c["cell_id"]: c for c in _json(awkward_client, "/api/map?year=2020&month=1&layer=raw")
        }
        for i, cell_id in enumerate(cells["columns"]["cell_id"]):
            if cell_id in expected:
                for name in CELL_FIELDS:
                    assert cells["columns"][name][i] == expected[cell_id][name]

    def test_every_layer_has_the_fields_the_app_reads(self, awkward_client: TestClient) -> None:
        sent = [
            _json(awkward_client, f"/api/map/columns?year=2020&month=1&layer={layer}")
            for layer in LAYERS
        ]
        assert sent[0] == sent[1] == sent[2]
        assert set(sent[0]["columns"]) == {*map_columns.APP_FIELDS, "year", "month"}
        unread = {"sd", "n_witnesses", "baseline_median", "baseline_p25", "baseline_p75"}
        assert unread.isdisjoint(sent[0]["columns"])

    def test_map_is_unchanged(self, awkward_client: TestClient) -> None:
        # GET /api/map still returns every contract field, and its ETag keeps its form.
        response = awkward_client.get("/api/map?year=2020&month=1&layer=raw", headers=PLAIN)
        assert response.headers["etag"].startswith('W/"map-')
        assert set(response.json()[0]) >= {"sd", "witnesses_used", "method_version", "baseline_p25"}


class TestHeadersAndCache:
    URLS: ClassVar[list[str]] = [
        "/api/map/cells",
        "/api/map/columns?year=2020&month=1&layer=verdict",
    ]

    @pytest.mark.parametrize("url", URLS)
    def test_headers_and_gzip(self, client: TestClient, url: str) -> None:
        zipped = client.get(url, headers={"Accept-Encoding": "gzip"})
        assert zipped.status_code == 200
        assert zipped.headers["content-encoding"] == "gzip"
        assert zipped.headers["cache-control"] == "public, max-age=300"
        assert zipped.headers["vary"] == "Accept-Encoding"
        assert zipped.headers["etag"].startswith('W/"')
        plain = client.get(url, headers=PLAIN)
        assert "content-encoding" not in plain.headers
        assert plain.headers["etag"] == zipped.headers["etag"]
        assert zipped.json() == plain.json()

    @pytest.mark.parametrize("url", URLS)
    def test_not_modified(self, client: TestClient, url: str) -> None:
        etag = client.get(url).headers["etag"]
        again = client.get(url, headers={"If-None-Match": etag})
        assert again.status_code == 304
        assert again.content == b""
        assert again.headers["etag"] == etag
        assert client.get(url, headers={"If-None-Match": '"other"'}).status_code == 200

    def test_validators_differ_between_endpoints_and_months(self, client: TestClient) -> None:
        tags = {
            client.get(u).headers["etag"]
            for u in (
                "/api/map?year=2020&month=1&layer=raw",
                "/api/map/cells",
                "/api/map/columns?year=2020&month=1&layer=verdict",
                "/api/map/columns?year=2020&month=2&layer=verdict",
            )
        }
        assert len(tags) == 4
        # Every layer is one answer, so one validator.
        same = {
            client.get(f"/api/map/columns?year=2020&month=1&layer={layer}").headers["etag"]
            for layer in LAYERS
        }
        assert len(same) == 1

    def test_repeat_is_served_from_memory(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[int] = []
        real = products.map_cells

        def spy(year: int, month: int) -> Any:
            calls.append(month)
            return real(year, month)

        monkeypatch.setattr(products, "map_cells", spy)
        for layer in ("verdict", "harmonized", "raw", "verdict"):
            client.get(f"/api/map/columns?year=2020&month=1&layer={layer}")
        assert calls == [1]  # the layers share one entry

    def test_a_touched_product_file_invalidates(
        self, client: TestClient, products_dir: Path
    ) -> None:
        url = "/api/map/columns?year=2020&month=1&layer=verdict"
        before = client.get(url).headers["etag"]
        cells_before = client.get("/api/map/cells").headers["etag"]
        path = products_dir / "cell_month_harmonized.parquet"
        stat = path.stat()
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
        assert client.get(url).headers["etag"] != before
        assert client.get("/api/map/cells").headers["etag"] == cells_before  # cells file untouched
        assert client.get(url, headers={"If-None-Match": before}).status_code == 200
        path = products_dir / "cells.parquet"
        stat = path.stat()
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
        assert client.get("/api/map/cells").headers["etag"] != cells_before

    def test_cached_bytes_are_deterministic(self, client: TestClient) -> None:
        url = "/api/map/columns?year=2020&month=1&layer=verdict"
        first = map_columns.columns_payload(2020, 1, MapLayer.VERDICT)
        map_cache.clear_cache()
        second = map_columns.columns_payload(2020, 1, MapLayer.VERDICT)
        assert gzip.decompress(first.gzipped) == gzip.decompress(second.gzipped)
        assert client.get(url).status_code == 200


class TestErrors:
    @pytest.mark.parametrize(
        "url",
        [
            "/api/map/columns?year=2020&month=13&layer=raw",
            "/api/map/columns?year=2020&month=0&layer=raw",
            "/api/map/columns?year=0&month=1&layer=raw",
            "/api/map/columns?year=2020&month=1&layer=other",
            "/api/map/columns?year=2020&month=1",
            "/api/map/columns?month=1&layer=raw",
            "/api/map/columns?year=abc&month=1&layer=raw",
        ],
    )
    def test_invalid_parameters_are_400_like_map(self, client: TestClient, url: str) -> None:
        assert client.get(url).status_code == 400
        assert client.get(url.replace("/columns", "")).status_code == 400

    def test_unavailable_products_are_503_and_never_cached(self, empty_client: TestClient) -> None:
        for url in ("/api/map/cells", "/api/map/columns?year=2020&month=1&layer=raw"):
            response = empty_client.get(url)
            assert response.status_code == 503
            assert "detail" in response.json()
        assert len(map_cache._columns_cache) == 0

    def test_a_value_outside_the_contract_is_503(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        build_products(tmp_path, [_harmonized("c1", 2020, 1, p_above=1.5)])
        monkeypatch.setenv("PRODUCTS_DIR", str(tmp_path))
        client = TestClient(app)
        assert client.get("/api/map/columns?year=2020&month=1&layer=raw").status_code == 503
        assert client.get("/api/map?year=2020&month=1&layer=raw").status_code == 503
        assert len(map_cache._columns_cache) == 0


# ------------------------------------------------------------------ the real products
def _real_dir() -> Path:
    return Path(os.environ.get("PRODUCTS_DIR") or "../data/products")


def _real_ready() -> bool:
    d = _real_dir()
    needed = [d / n for n in map_cache.PRODUCT_FILES]
    return all(p.is_file() and p.stat().st_size > 1024 for p in needed)  # an LFS pointer is ~130 B


@pytest.mark.skipif(
    not _real_ready(),
    reason="the real products are LFS pointers or missing: fetch them or set PRODUCTS_DIR",
)
@pytest.mark.parametrize("layer", LAYERS)
def test_real_products_identical_to_map(monkeypatch: pytest.MonkeyPatch, layer: str) -> None:
    monkeypatch.setenv("PRODUCTS_DIR", str(_real_dir()))
    client = TestClient(app)
    expected = _json(client, f"/api/map?year=2023&month=7&layer={layer}")
    got = _decoded(client, 2023, 7, layer)
    assert len(got) == len(expected) > 1000
    fields = [*CELL_FIELDS, *map_columns.MONTH_FIELDS, *map_columns.field_set(MapLayer(layer))]
    for record, decoded in zip(expected, got, strict=True):
        for name in fields:
            assert _text(decoded[name]) == _text(record[name])


# ------------------------------------------------------ the area columns of the cell list (T-090)
class TestCellAreaColumns:
    """`GET /api/map/cells` also carries each cell's country and continent, as stored (additive).

    SYNTHETIC cells."""

    def test_the_two_area_columns_are_the_stored_values_cell_by_cell(
        self, client: TestClient
    ) -> None:
        columns = _json(client, "/api/map/cells")["columns"]
        stored = {c[0]: (c[5], c[6]) for c in CELLS}
        assert columns["cell_id"] == sorted(stored)
        assert columns["country_iso3"] == [stored[i][0] for i in columns["cell_id"]]
        assert columns["continent"] == [stored[i][1] for i in columns["cell_id"]]
        assert (
            None in columns["country_iso3"] and None in columns["continent"]
        )  # a cell with no country stays null

    def test_the_five_old_columns_are_unchanged_and_come_first(self, client: TestClient) -> None:
        body = _json(client, "/api/map/cells")
        assert list(body["columns"])[:5] == list(CELL_FIELDS)
        rows = products.cell_bounds()
        for name in CELL_FIELDS:
            assert _text(body["columns"][name]) == _text([r[name] for r in rows])
        assert body["n"] == len(rows)

    def test_the_month_columns_and_the_map_are_unchanged(self, client: TestClient) -> None:
        month = _json(client, "/api/map/columns?year=2020&month=1&layer=verdict")
        assert "country_iso3" not in month["columns"] and "continent" not in month["columns"]
        record = _json(client, "/api/map?year=2020&month=1&layer=verdict")[0]
        assert "country_iso3" not in record and "continent" not in record

    def test_the_area_columns_have_one_value_per_cell(self, client: TestClient) -> None:
        body = _json(client, "/api/map/cells")
        assert (
            len(body["columns"]["country_iso3"]) == len(body["columns"]["continent"]) == body["n"]
        )


@pytest.mark.skipif(
    not _real_ready(),
    reason="the real products are LFS pointers or missing: fetch them or set PRODUCTS_DIR",
)
def test_real_cell_list_area_columns_equal_cells_parquet(monkeypatch: pytest.MonkeyPatch) -> None:
    import duckdb

    monkeypatch.setenv("PRODUCTS_DIR", str(_real_dir()))
    body = _json(TestClient(app), "/api/map/cells")
    stored = (
        duckdb.connect()
        .execute(
            "SELECT cell_id, country_iso3, continent FROM read_parquet(?) ORDER BY cell_id",
            [str(_real_dir() / "cells.parquet")],
        )
        .fetchall()
    )
    assert body["n"] == len(stored) > 50000
    assert body["columns"]["cell_id"] == [r[0] for r in stored]
    assert body["columns"]["country_iso3"] == [r[1] for r in stored]
    assert body["columns"]["continent"] == [r[2] for r in stored]


class TestCellsFieldSetToken:
    def test_the_cells_etag_carries_the_field_set_token(self, client: TestClient) -> None:
        # A browser holding the answer from before country_iso3 and continent existed
        # must not be told "not modified" (T-090).
        etag = client.get("/api/map/cells", headers=PLAIN).headers["etag"]
        assert etag.startswith(f'W/"cells-{map_columns.CELLS_SCHEMA}-')
        assert map_columns.CELLS_SCHEMA != "v1"
        old = 'W/"cells-0123456789abcdef01234567"'
        stale = client.get("/api/map/cells", headers={**PLAIN, "If-None-Match": old})
        assert stale.status_code == 200
