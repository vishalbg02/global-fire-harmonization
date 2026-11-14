"""Custom-area series through Member 2's single implementation of the science.

The API never reimplements `harmonize_area(cell_ids, months=None)` (docs/DATA_CONTRACT.md §8).
It is imported from `pipeline/harmonize.py` and called with the module defaults: the
overdispersion, relative-error and Aqua-cutoff settings are the method's, so the API cannot
drift from the science.
"""

import hashlib
import sys
import tempfile
import threading
from collections import OrderedDict
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import duckdb

from . import products
from .models import EntityMonth

PIPELINE_DIR = Path(__file__).resolve().parents[2] / "pipeline"


class HarmonizeUnavailable(Exception):
    """`harmonize_area()` cannot be imported or its products cannot be read."""


HarmonizeArea = Callable[..., list[Mapping[str, Any]]]


def _import_harmonize() -> Any:
    """The `harmonize` module of `pipeline/` (put on `sys.path` on first use)."""
    if not PIPELINE_DIR.is_dir():
        raise HarmonizeUnavailable(
            "Custom areas are not available right now: the harmonization code was not found."
        )
    if str(PIPELINE_DIR) not in sys.path:
        sys.path.append(str(PIPELINE_DIR))
    try:
        import harmonize
    except ImportError as exc:
        raise HarmonizeUnavailable(
            "Custom areas are not available right now: the harmonization code could not be loaded."
        ) from exc
    return harmonize


def load_harmonize_area() -> HarmonizeArea:
    """Return `harmonize_area(cell_ids, months=None)` from `pipeline/harmonize.py`, bound to
    this API's `PRODUCTS_DIR`.

    `pipeline/` is not a package and its modules import each other by name, so the directory is
    put on `sys.path` (nothing in `pipeline/` changes). DuckDB's spill files go to the system
    temporary directory, so nothing is written into the repository.
    """
    harmonize = _import_harmonize()

    def run(
        cell_ids: list[str], months: list[tuple[int, int]] | None = None
    ) -> list[Mapping[str, Any]]:
        paths = harmonize.Paths(
            products=products.products_dir().resolve(),
            tmp=Path(tempfile.gettempdir()) / "fire_api_duckdb",
        )
        try:
            return harmonize.harmonize_area(cell_ids, months, paths=paths)
        except (OSError, duckdb.Error) as exc:  # missing or unreadable products
            raise HarmonizeUnavailable(
                "Custom areas are not available right now: the products could not be read."
            ) from exc

    return run


# ------------------------------------------------------------------------------ result cache
# `harmonize_area()` scans the 146.6 million-row witness product on every call (about 3 s for a
# country-sized box), and the answer is a pure function of the cell set, the products and the
# method. So the validated answer is kept in memory, per process, in a bounded LRU.

CACHE_MAX_ENTRIES = 32  # one entry is a validated series of about 300 records (a few hundred kB)

# Every product file `harmonize_area()` reads (cells -> cell list, witness -> counts, calibration).
PRODUCT_FILES = ("cells.parquet", "cell_month_witness.parquet", "calibration.parquet")

CacheKey = tuple[str, str, tuple[tuple[str, int, int], ...], int, str]


class ResultCache:
    """A bounded, thread-safe LRU of validated series, with single-flight computation.

    Only successful results are stored: if the compute function raises, nothing is cached and
    the next call tries again. Concurrent calls for the same key compute once; the others wait
    for that result (or run the computation themselves if it failed).
    """

    def __init__(self, max_entries: int = CACHE_MAX_ENTRIES) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1.")
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._entries: OrderedDict[Any, list[EntityMonth]] = OrderedDict()
        self._inflight: dict[Any, threading.Lock] = {}

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def _get(self, key: Any) -> list[EntityMonth] | None:
        with self._lock:
            value = self._entries.get(key)
            if value is not None:
                self._entries.move_to_end(key)
            return value

    def get_or_compute(
        self, key: Any, compute: Callable[[], list[EntityMonth]]
    ) -> list[EntityMonth]:
        value = self._get(key)
        if value is not None:
            return list(value)
        with self._lock:
            flight = self._inflight.setdefault(key, threading.Lock())
        with flight:
            value = self._get(key)  # another thread may have finished while this one waited
            if value is None:
                try:
                    value = compute()
                    with self._lock:
                        self._entries[key] = value
                        self._entries.move_to_end(key)
                        while len(self._entries) > self.max_entries:
                            self._entries.popitem(last=False)
                finally:
                    with self._lock:
                        self._inflight.pop(key, None)
        return list(value)


_cache = ResultCache()


def clear_cache() -> None:
    """Forget every cached series (tests, or after replacing products in a running process)."""
    _cache.clear()


def method_version() -> str:
    """`harmonize.METHOD_VERSION`, read on every call so a changed method never hits the cache."""
    return str(_import_harmonize().METHOD_VERSION)


def _product_signature(directory: Path) -> tuple[tuple[str, int, int], ...]:
    """(name, modified time in ns, size) of each product file `harmonize_area()` reads."""
    out = []
    for name in PRODUCT_FILES:
        stat = (directory / name).stat()
        out.append((name, stat.st_mtime_ns, stat.st_size))
    return tuple(out)


def cache_key(cell_ids: list[str]) -> CacheKey | None:
    """The key of a request: products directory, a digest of the sorted distinct cell set (and
    its size), the products' modified times and sizes, and the method version. `None` when a
    product file cannot be inspected: the call then goes uncached and fails as it always did."""
    directory = products.products_dir().resolve()
    try:
        signature = _product_signature(directory)
    except OSError:
        return None
    ids = sorted(set(cell_ids))
    digest = hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()
    return (str(directory), digest, signature, len(ids), method_version())


def custom_series(cell_ids: list[str]) -> list[EntityMonth]:
    """The validated `entity_month` series of `cell_ids`, from the cache when the same cells,
    products and method were computed before. Records come from the single implementation of
    the science and are validated, not altered. Errors are raised and never cached."""
    harmonize_area = load_harmonize_area()

    def compute() -> list[EntityMonth]:
        records = harmonize_area(cell_ids, months=None)
        return [EntityMonth.model_validate(dict(r)) for r in records]

    key = cache_key(cell_ids)
    if key is None:
        return compute()
    return _cache.get_or_compute(key, compute)
