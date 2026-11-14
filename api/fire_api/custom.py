"""Custom-area series through Member 2's single implementation of the science.

The API never reimplements `harmonize_area(cell_ids, months=None)` (docs/DATA_CONTRACT.md §8).
It is imported from `pipeline/harmonize.py` and called with the module defaults: the
overdispersion, relative-error and Aqua-cutoff settings are the method's, so the API cannot
drift from the science.
"""

import sys
import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import duckdb

from . import products

PIPELINE_DIR = Path(__file__).resolve().parents[2] / "pipeline"


class HarmonizeUnavailable(Exception):
    """`harmonize_area()` cannot be imported or its products cannot be read."""


HarmonizeArea = Callable[..., list[Mapping[str, Any]]]


def load_harmonize_area() -> HarmonizeArea:
    """Return `harmonize_area(cell_ids, months=None)` from `pipeline/harmonize.py`, bound to
    this API's `PRODUCTS_DIR`.

    `pipeline/` is not a package and its modules import each other by name, so the directory is
    put on `sys.path` (nothing in `pipeline/` changes). DuckDB's spill files go to the system
    temporary directory, so nothing is written into the repository.
    """
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
