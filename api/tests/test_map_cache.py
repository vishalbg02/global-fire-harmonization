"""The cached, pre-compressed answer of GET /api/map (fire_api.map_cache). SYNTHETIC products."""

import gzip
import json
import os
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fire_api import map_cache, products
from fire_api.main import app
from fire_api.models import MapCell
from tests.conftest import HARMONIZED_ROWS, build_products

URL = "/api/map?year=2020&month=1&layer=verdict"


def _calls(monkeypatch: pytest.MonkeyPatch) -> list[tuple[int, int]]:
    calls: list[tuple[int, int]] = []
    real = products.map_cells

    def spy(year: int, month: int) -> list[MapCell]:
        calls.append((year, month))
        return real(year, month)

    monkeypatch.setattr(products, "map_cells", spy)
    return calls


def _touch(path: Path) -> None:
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))


class TestPayload:
    def test_bytes_are_what_the_endpoint_always_sent(self, client: TestClient) -> None:
        expected = json.dumps(
            [c.model_dump(mode="json") for c in products.map_cells(2020, 1)],
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
        identity = client.get(URL, headers={"Accept-Encoding": "identity"})
        assert identity.content == expected
        assert json.loads(identity.content)[0]["cell_id"] == "c1"

    def test_gzip_and_identity_carry_the_same_json(self, client: TestClient) -> None:
        zipped = client.get(URL, headers={"Accept-Encoding": "gzip"})
        assert zipped.headers["content-encoding"] == "gzip"
        plain = client.get(URL, headers={"Accept-Encoding": "identity"})
        assert "content-encoding" not in plain.headers
        assert zipped.json() == plain.json()
        assert gzip.decompress(map_cache.payload(2020, 1).gzipped) == plain.content

    def test_accept_encoding_is_read_with_its_quality(self) -> None:
        from fire_api.main import _accepts_gzip

        assert _accepts_gzip("gzip, deflate, br")
        assert _accepts_gzip("deflate, gzip;q=0.5")
        assert not _accepts_gzip("gzip;q=0")
        assert not _accepts_gzip("identity")
        assert not _accepts_gzip("")

    def test_every_layer_gets_the_same_bytes(self, client: TestClient) -> None:
        bodies = {
            layer: client.get(f"/api/map?year=2020&month=1&layer={layer}").content
            for layer in ("verdict", "raw", "harmonized")
        }
        assert len(set(bodies.values())) == 1
        assert len(map_cache._cache) == 1


class TestCache:
    def test_a_repeat_does_not_read_the_products(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls = _calls(monkeypatch)
        first = client.get(URL)
        second = client.get(URL)
        assert first.content == second.content
        assert calls == [(2020, 1)]

    def test_other_months_are_other_entries(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls = _calls(monkeypatch)
        client.get(URL)
        client.get("/api/map?year=2020&month=2&layer=verdict")
        assert calls == [(2020, 1), (2020, 2)]

    def test_touching_a_product_file_invalidates(
        self, client: TestClient, products_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls = _calls(monkeypatch)
        before = client.get(URL).headers["etag"]
        for name in map_cache.PRODUCT_FILES:
            _touch(products_dir / name)
            after = client.get(URL)
            assert after.headers["etag"] != before, name
            before = after.headers["etag"]
        assert len(calls) == 3

    def test_new_values_are_served_after_the_file_is_replaced(
        self, client: TestClient, products_dir: Path
    ) -> None:
        assert client.get(URL).json()[0]["verdict"] == "ABOVE_NORMAL"
        rows = list(HARMONIZED_ROWS)
        row = list(rows[0])
        row[row.index("ABOVE_NORMAL")] = "BELOW_NORMAL"
        rows[0] = tuple(row)
        build_products(products_dir, harmonized_rows=rows)
        _touch(products_dir / "cell_month_harmonized.parquet")
        assert client.get(URL).json()[0]["verdict"] == "BELOW_NORMAL"

    def test_errors_are_not_cached(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        bad = list(HARMONIZED_ROWS)
        row = list(bad[0])
        row[row.index("ABOVE_NORMAL")] = "MAYBE_ABOVE"
        bad[0] = tuple(row)
        build_products(tmp_path, harmonized_rows=bad)
        monkeypatch.setenv("PRODUCTS_DIR", str(tmp_path))
        test_client = TestClient(app)
        assert test_client.get(URL).status_code == 503
        assert len(map_cache._cache) == 0
        build_products(tmp_path)
        _touch(tmp_path / "cell_month_harmonized.parquet")
        assert test_client.get(URL).status_code == 200

    def test_the_cache_is_bounded(self) -> None:
        cache = map_cache.MapCache(max_entries=2)
        sig: map_cache.Signature = (("a", 1, 1),)
        for month in (1, 2, 3):
            cache.get_or_build(("d", 2020, month, sig), lambda: b"[]")
        assert len(cache) == 2

    def test_concurrent_requests_build_once(self) -> None:
        cache = map_cache.MapCache()
        key: map_cache.Key = ("d", 2020, 1, (("a", 1, 1),))
        built: list[int] = []

        def slow() -> bytes:
            built.append(1)
            time.sleep(0.1)
            return b"[]"

        threads = [threading.Thread(target=cache.get_or_build, args=(key, slow)) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(built) == 1


class TestHeaders:
    def test_validators_and_cache_control(self, client: TestClient) -> None:
        response = client.get(URL)
        assert response.headers["cache-control"] == "public, max-age=300"
        assert response.headers["etag"].startswith('W/"map-')
        assert "Accept-Encoding" in response.headers["vary"]
        assert response.headers["content-type"] == "application/json"

    def test_if_none_match_gives_304_without_reading_products(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        etag = client.get(URL).headers["etag"]
        calls = _calls(monkeypatch)
        response = client.get(URL, headers={"If-None-Match": etag})
        assert response.status_code == 304
        assert response.content == b""
        assert response.headers["etag"] == etag
        assert calls == []

    def test_a_stale_validator_gets_the_full_answer(
        self, client: TestClient, products_dir: Path
    ) -> None:
        etag = client.get(URL).headers["etag"]
        _touch(products_dir / "cells.parquet")
        response = client.get(URL, headers={"If-None-Match": etag})
        assert response.status_code == 200
        assert response.headers["etag"] != etag

    def test_missing_products_still_give_503(self, empty_client: TestClient) -> None:
        response = empty_client.get(URL)
        assert response.status_code == 503
        assert "not available" in response.json()["detail"]

    def test_invalid_parameters_still_give_400(self, client: TestClient) -> None:
        assert client.get("/api/map?year=2020&month=13&layer=raw").status_code == 400
