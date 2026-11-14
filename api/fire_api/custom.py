"""Custom-area series through Member 2's single implementation of the science.

The API never reimplements `harmonize_area(cell_ids, months=None)` (docs/DATA_CONTRACT.md §8).
"""

from collections.abc import Callable, Mapping
from typing import Any


class HarmonizeUnavailable(Exception):
    """`harmonize_area()` cannot be imported yet."""


HarmonizeArea = Callable[..., list[Mapping[str, Any]]]


def load_harmonize_area() -> HarmonizeArea:
    """Return `harmonize_area` from `pipeline/`.

    The function has not been delivered (the Member 2 stub is due at about H10) and its module
    path is not yet documented in docs/ARCHITECTURE.md, so nothing is imported here. Once the
    path is documented, import it here; callers need no change.
    """
    raise HarmonizeUnavailable(
        "Custom areas are not available yet: the harmonization function has not been delivered."
    )
