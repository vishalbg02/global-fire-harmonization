"""The serialized, compressed answer of GET /api/map, kept in memory per month (T-073).

A map month is 56,000 cells and 32 MB of JSON. Building it (DuckDB, contract validation,
serialization, gzip) takes about 0.8 s, and the answer is a pure function of the two product
files it reads and of the month. So the bytes are built once per (products directory, month) and
served again until a product file changes. Nothing about the answer changes: same fields, same
values, same order, byte for byte what the endpoint returned before.

Only the compressed bytes are kept (about 3 MB per month); a client that does not accept gzip gets
them decompressed. The `layer` parameter is validated but never changes the payload (every layer
returns the same fields; the app colours them), so layers share one entry.
"""

import gzip
import hashlib
import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pydantic import TypeAdapter

from . import products
from .models import MapCell

# Both files the map joins. A change of either one (modified time or size) is a new key.
PRODUCT_FILES = ("cell_month_harmonized.parquet", "cells.parquet")

# Every month is about 3 MB compressed, so the bound is about 50 MB. The app keeps a few months
# and prefetches their neighbours, so 16 covers a browsing session and a few visitors.
CACHE_MAX_ENTRIES = 16

# Compressed once and served many times, so the best level is worth its extra 0.15 s here
# (3.07 MB at level 6 against 2.95 MB at level 9 for a typical month).
COMPRESS_LEVEL = 9

_ADAPTER: TypeAdapter[list[MapCell]] = TypeAdapter(list[MapCell])

Signature = tuple[tuple[str, int, int], ...]
# (directory, year, month, signature) for /api/map; (kind, directory, year, month, signature) for
# the columnar endpoints, so the two never share an entry or a validator.
Key = tuple[object, ...]

# The columnar answers are small (a fraction of the map month), so more of them are kept.
COLUMNS_CACHE_MAX_ENTRIES = 64
CELLS_FILES = ("cells.parquet",)


@dataclass(frozen=True)
class MapPayload:
    """One cached answer: gzip bytes of the JSON array and its validator."""

    gzipped: bytes
    etag: str

    def identity(self) -> bytes:
        return gzip.decompress(self.gzipped)


def product_signature(directory: Path, files: tuple[str, ...] = PRODUCT_FILES) -> Signature | None:
    """(name, modified time in ns, size) of each product file the map reads, or None when one
    cannot be inspected (the request then goes uncached and fails as it always did)."""
    out = []
    try:
        for name in files:
            stat = (directory / name).stat()
            out.append((name, stat.st_mtime_ns, stat.st_size))
    except OSError:
        return None
    return tuple(out)


def cache_key(year: int, month: int) -> Key | None:
    directory = products.products_dir().resolve()
    signature = product_signature(directory)
    if signature is None:
        return None
    return (str(directory), year, month, signature)


def etag_of(key: Key) -> str:
    """A weak validator for the month: it covers the gzip and the identity form of the same
    bytes, and changes when a product file does. Cheap: no data is read to compute it."""
    digest = hashlib.sha256(repr(key).encode("utf-8")).hexdigest()[:24]
    prefix = key[0] if len(key) == 5 else "map"
    return f'W/"{prefix}-{digest}"'


def build(year: int, month: int) -> bytes:
    """The JSON array exactly as the endpoint has always sent it: validated against the
    contract (a value outside it is reported, never coerced), compact separators."""
    return _ADAPTER.dump_json(products.map_cells(year, month))


class MapCache:
    """A bounded, thread-safe LRU with single-flight builds: concurrent requests for the same
    key build once; only successful builds are stored."""

    def __init__(self, max_entries: int = CACHE_MAX_ENTRIES) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be at least 1.")
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._entries: OrderedDict[Key, MapPayload] = OrderedDict()
        self._inflight: dict[Key, threading.Lock] = {}

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def _get(self, key: Key) -> MapPayload | None:
        with self._lock:
            value = self._entries.get(key)
            if value is not None:
                self._entries.move_to_end(key)
            return value

    def get_or_build(self, key: Key, make: Callable[[], bytes]) -> MapPayload:
        value = self._get(key)
        if value is not None:
            return value
        with self._lock:
            flight = self._inflight.setdefault(key, threading.Lock())
        with flight:
            value = self._get(key)  # another thread may have finished while this one waited
            if value is None:
                try:
                    value = MapPayload(
                        gzipped=gzip.compress(make(), compresslevel=COMPRESS_LEVEL, mtime=0),
                        etag=etag_of(key),
                    )
                    with self._lock:
                        self._entries[key] = value
                        self._entries.move_to_end(key)
                        while len(self._entries) > self.max_entries:
                            self._entries.popitem(last=False)
                finally:
                    with self._lock:
                        self._inflight.pop(key, None)
        return value


_cache = MapCache()


_columns_cache = MapCache(COLUMNS_CACHE_MAX_ENTRIES)


def clear_cache() -> None:
    """Forget every cached answer (tests, or after replacing products in a running process)."""
    _cache.clear()
    _columns_cache.clear()


def payload(year: int, month: int) -> MapPayload:
    """The cached answer for a month, built on first use. Errors (a missing product, a value
    outside the contract) are raised and never cached."""
    key = cache_key(year, month)
    if key is None:
        # A product file is missing or unreadable: let the query report it (503).
        raw = build(year, month)
        return MapPayload(gzip.compress(raw, compresslevel=COMPRESS_LEVEL, mtime=0), "")
    return _cache.get_or_build(key, lambda: build(year, month))


def validator(year: int, month: int) -> str | None:
    """The ETag the month would have now, without building it (for If-None-Match)."""
    key = cache_key(year, month)
    return None if key is None else etag_of(key)


def _variant_key(kind: str, year: int, month: int, files: tuple[str, ...]) -> Key | None:
    directory = products.products_dir().resolve()
    signature = product_signature(directory, files)
    if signature is None:
        return None
    return (kind, str(directory), year, month, signature)


def variant_payload(
    kind: str, year: int, month: int, files: tuple[str, ...], make: Callable[[], bytes]
) -> MapPayload:
    """The cached answer of a columnar endpoint (`kind` names it; `files` are the product files
    it reads). Same rules as `payload`: errors are raised and never cached."""
    key = _variant_key(kind, year, month, files)
    if key is None:
        return MapPayload(gzip.compress(make(), compresslevel=COMPRESS_LEVEL, mtime=0), "")
    return _columns_cache.get_or_build(key, make)


def variant_validator(kind: str, year: int, month: int, files: tuple[str, ...]) -> str | None:
    key = _variant_key(kind, year, month, files)
    return None if key is None else etag_of(key)
