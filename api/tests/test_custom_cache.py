"""The in-process cache of custom-area results (fire_api.custom.ResultCache).

Synthetic tests use a fake `harmonize_area` and dummy product files; one test runs the real
`harmonize_area()` on the real products and is skipped when they are Git LFS pointer files.
"""

import os
import threading
import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from fire_api import custom
from fire_api.main import app
from fire_api.models import EntityMonth
from tests.test_custom_real import NEEDED, URUGUAY, needs_real

REAL = Path(__file__).resolve().parents[2] / "data" / "products"
URL = "/api/series/custom"
BOX_A = {"bbox": [99, 0, 101, 1]}  # c1 and c2
BOX_B = {"bbox": [99, 0, 101, 0.6]}  # c1 only


def _record(month: int, n_cells: int) -> dict[str, Any]:
    return {
        "entity_type": "CUSTOM", "entity_id": "CUSTOM", "entity_name": "Custom area",
        "year": 2020, "month": month, "estimate": 10.0, "ci90_low": 8.0, "ci90_high": 12.0,
        "sd": 1.0, "raw_combined_cell_days": 12, "witnesses_used": ["SNPP_VIIRS"],
        "n_witnesses": 1, "disagreement_scale": None, "baseline_median": None,
        "baseline_p25": None, "baseline_p75": None, "pct_of_normal": None, "p_above": None,
        "p_below": None, "p_within": None, "verdict": "CANNOT_DETERMINE", "reason_codes": [],
        "data_level": "SP", "method_version": "fake", "n_cells": n_cells,
        "raw_by_witness": '{"SNPP_VIIRS": 12}',
    }  # fmt: skip


class Fake:
    """A `harmonize_area` stand-in that counts its calls."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.fail = False

    def __call__(self, cell_ids: list[str], months: Any = None) -> list[dict[str, Any]]:
        self.calls.append(list(cell_ids))
        if self.fail:
            raise custom.HarmonizeUnavailable("down")
        return [_record(1, len(cell_ids))]


@pytest.fixture
def fake(client: TestClient, products_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Fake:
    """The synthetic API plus the three product files `harmonize_area()` reads (dummy bytes)."""
    for name in custom.PRODUCT_FILES:
        if not (products_dir / name).exists():  # cells.parquet is the synthetic one
            (products_dir / name).write_bytes(b"x" * 10)
    fake = Fake()
    monkeypatch.setattr(custom, "load_harmonize_area", lambda: fake)
    return fake


def test_the_files_the_key_covers_are_the_files_the_real_test_needs() -> None:
    assert tuple(custom.PRODUCT_FILES) == NEEDED


def test_a_repeat_call_does_not_recompute(client: TestClient, fake: Fake) -> None:
    first = client.post(URL, json=BOX_A)
    second = client.post(URL, json=BOX_A)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(fake.calls) == 1
    assert fake.calls == [["c1", "c2"]]


def test_csv_export_shares_the_cache(client: TestClient, fake: Fake) -> None:
    assert client.post(URL, json=BOX_A).status_code == 200
    response = client.get("/api/export.csv", params={"bbox": "99,0,101,1"})
    assert response.status_code == 200
    assert response.content.startswith(b"\xef\xbb\xbf")
    assert "attachment; filename=" in response.headers["content-disposition"]
    assert len(fake.calls) == 1


def test_a_different_cell_set_recomputes(client: TestClient, fake: Fake) -> None:
    client.post(URL, json=BOX_A)
    client.post(URL, json=BOX_B)
    assert fake.calls == [["c1", "c2"], ["c1"]]
    client.post(URL, json=BOX_A)
    client.post(URL, json=BOX_B)
    assert len(fake.calls) == 2


def test_the_same_cells_in_another_order_hit(fake: Fake) -> None:
    key_a = custom.cache_key(["c2", "c1"])
    assert key_a is not None
    assert key_a == custom.cache_key(["c1", "c2", "c1"])
    assert key_a != custom.cache_key(["c1"])


@pytest.mark.parametrize("name", custom.PRODUCT_FILES)
def test_a_touched_product_file_recomputes(
    client: TestClient, fake: Fake, products_dir: Path, name: str
) -> None:
    client.post(URL, json=BOX_A)
    path = products_dir / name
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 5_000_000_000))
    client.post(URL, json=BOX_A)
    assert len(fake.calls) == 2
    client.post(URL, json=BOX_A)  # and the new state is cached again
    assert len(fake.calls) == 2


def test_a_resized_product_file_recomputes(
    client: TestClient, fake: Fake, products_dir: Path
) -> None:
    client.post(URL, json=BOX_A)
    path = products_dir / "calibration.parquet"
    stat = path.stat()
    path.write_bytes(b"y" * 11)
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))  # same time, different size
    client.post(URL, json=BOX_A)
    assert len(fake.calls) == 2


def test_a_changed_method_version_recomputes(
    client: TestClient, fake: Fake, monkeypatch: pytest.MonkeyPatch
) -> None:
    import harmonize

    client.post(URL, json=BOX_A)
    monkeypatch.setattr(harmonize, "METHOD_VERSION", harmonize.METHOD_VERSION + "-next")
    client.post(URL, json=BOX_A)
    assert len(fake.calls) == 2
    monkeypatch.undo()  # the old version is a hit again: nothing stale was overwritten
    client.post(URL, json=BOX_A)
    assert len(fake.calls) == 2


def test_another_products_directory_recomputes(
    client: TestClient, fake: Fake, tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # fmt: skip
    client.post(URL, json=BOX_A)
    other = tmp_path_factory.mktemp("other")
    from tests.conftest import build_products

    build_products(other)
    for name in custom.PRODUCT_FILES:
        if not (other / name).exists():
            (other / name).write_bytes(b"x" * 10)
    monkeypatch.setenv("PRODUCTS_DIR", str(other))
    client.post(URL, json=BOX_A)
    assert len(fake.calls) == 2


def test_errors_are_not_cached(client: TestClient, fake: Fake) -> None:
    fake.fail = True
    assert client.post(URL, json=BOX_A).status_code == 503
    assert client.post(URL, json=BOX_A).status_code == 503
    assert len(fake.calls) == 2  # the failure was tried again, not replayed
    fake.fail = False
    assert client.post(URL, json=BOX_A).status_code == 200
    assert client.post(URL, json=BOX_A).status_code == 200
    assert len(fake.calls) == 3


def test_a_validation_failure_is_not_cached(
    client: TestClient, fake: Fake, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad_record = _record(1, 2) | {"verdict": "NOT_A_VERDICT"}
    calls: list[int] = []

    def broken(cell_ids: list[str], months: Any = None) -> list[dict[str, Any]]:
        calls.append(1)
        return [bad_record]

    monkeypatch.setattr(custom, "load_harmonize_area", lambda: broken)
    for _ in range(2):
        assert client.post(URL, json=BOX_A).status_code == 503
    assert len(calls) == 2


def test_an_unreadable_product_is_never_cached(
    client: TestClient, products_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing product files: no key, the call goes straight to harmonize_area."""
    fake = Fake()
    monkeypatch.setattr(custom, "load_harmonize_area", lambda: fake)
    assert not (products_dir / "calibration.parquet").exists()
    assert custom.cache_key(["c1"]) is None
    client.post(URL, json=BOX_A)
    client.post(URL, json=BOX_A)
    assert len(fake.calls) == 2


def _series(n: int) -> list[EntityMonth]:
    return [EntityMonth.model_validate(_record(1, n))]


def test_the_lru_evicts_the_least_recently_used() -> None:
    cache = custom.ResultCache(max_entries=2)
    computed: list[str] = []

    def get(key: str) -> list[EntityMonth]:
        def compute() -> list[EntityMonth]:
            computed.append(key)
            return _series(1)

        return cache.get_or_compute(key, compute)

    get("a")
    get("b")
    get("a")  # a is now the most recent
    get("c")  # evicts b
    assert len(cache) == 2
    get("a")
    assert computed == ["a", "b", "c"]
    get("b")  # was evicted: recomputed, evicting c
    assert computed == ["a", "b", "c", "b"]
    get("c")
    assert computed == ["a", "b", "c", "b", "c"]


def test_the_default_bound_is_documented_and_positive() -> None:
    assert custom.CACHE_MAX_ENTRIES == 32
    with pytest.raises(ValueError):
        custom.ResultCache(max_entries=0)


def test_a_failed_compute_leaves_no_entry_and_no_stuck_lock() -> None:
    cache = custom.ResultCache(max_entries=2)

    def boom() -> list[EntityMonth]:
        raise RuntimeError("no")

    with pytest.raises(RuntimeError):
        cache.get_or_compute("k", boom)
    assert len(cache) == 0
    assert cache.get_or_compute("k", lambda: _series(1))[0].n_cells == 1


def test_concurrent_identical_requests_compute_once() -> None:
    cache = custom.ResultCache()
    count = 0
    count_lock = threading.Lock()

    def slow() -> list[EntityMonth]:
        nonlocal count
        with count_lock:
            count += 1
        time.sleep(0.2)
        return _series(1)

    results: list[list[EntityMonth]] = []
    threads = [
        threading.Thread(target=lambda: results.append(cache.get_or_compute("k", slow)))
        for _ in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert count == 1
    assert len(results) == 8


def test_callers_cannot_change_the_cached_list() -> None:
    cache = custom.ResultCache()
    first = cache.get_or_compute("k", lambda: _series(1))
    first.clear()
    assert len(cache.get_or_compute("k", lambda: _series(2))) == 1


@needs_real
def test_real_products_repeat_is_served_from_the_cache(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PRODUCTS_DIR", str(REAL))
    client = TestClient(app)
    t0 = time.perf_counter()
    first = client.post(URL, json={"bbox": URUGUAY})
    cold = time.perf_counter() - t0
    t0 = time.perf_counter()
    second = client.post(URL, json={"bbox": URUGUAY})
    warm = time.perf_counter() - t0
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert len(first.json()) > 200
    assert warm < cold / 5
    assert warm < 0.5
