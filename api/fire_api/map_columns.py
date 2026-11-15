"""GET /api/map/cells and GET /api/map/columns: the map month in the columnar layout (T-073).

An additive pair of endpoints beside GET /api/map, which stays as it is. The month is the same
records, validated against the same contract, but sent column by column with only the fields the
app reads:

- ``/api/map/cells``: the ids and bounds of every analysis cell, once (the cell list).
- ``/api/map/columns``: one month, ``{"n", "columns", "cell_index"?}``. A column is
  ``{"const": v}`` (the same for every cell), ``{"dict": [...], "idx": [...]}`` (few distinct
  values, kept once) or ``{"values": [...]}``; ``cell_index`` names the month's cells by position
  in the cell list (left out when they are its first ``n`` cells).

Every value is the stored value: nothing is rounded or computed, and numbers are printed in the
shortest form that reads back as the same number, as in GET /api/map. The answers are cached
serialized and compressed (fire_api.map_cache) like the map month.
Every layer has the same set of fields (the app reads the same ones whatever it shows).
"""

from typing import Any

from pydantic_core import to_json

from . import map_cache, products
from .columnar import CELL_FIELDS, encode_columns
from .models import MapLayer

# The fields the app reads from a map cell (api/README.md). `year` and `month` ride along as
# constant columns, so a decoded record is a complete map cell for what the app shows.
#
# The colour, the hover tooltip and the selected-cell card read: verdict, pct_of_normal, estimate,
# ci90_low, ci90_high, p_above, p_below, p_within, raw_combined_cell_days, reason_codes and
# data_level. The evidence panel of a selected cell (on every layer) adds witnesses_used,
# disagreement_scale and method_version. So the three layers need the same fields and share one
# set; `layer` is validated, as in GET /api/map. Not sent, because the map never reads them: sd,
# n_witnesses, baseline_median, baseline_p25, baseline_p75.
APP_FIELDS: tuple[str, ...] = (
    "estimate",
    "ci90_low",
    "ci90_high",
    "raw_combined_cell_days",
    "witnesses_used",
    "disagreement_scale",
    "pct_of_normal",
    "p_above",
    "p_below",
    "p_within",
    "verdict",
    "reason_codes",
    "data_level",
    "method_version",
)
MONTH_FIELDS: tuple[str, ...] = ("year", "month")

COLUMNS_KIND = "columns"
CELLS_KIND = "cells"


def field_set(layer: MapLayer) -> tuple[str, ...]:
    """The fields sent for a layer. Every layer has the same set (see above), so all layers share
    one cached answer per month."""
    return APP_FIELDS


def cell_list() -> list[dict[str, Any]]:
    """Every analysis cell, ordered by cell_id (the order of a map month)."""
    return products.cell_bounds()


# Added after the five cell fields (T-090, approved by the Lead on PR #74): the country and the
# continent of each cell as stored in cells.parquet, so a client can count an area's own cells.
# Additive: the five fields and every other endpoint are unchanged.
AREA_FIELDS: tuple[str, ...] = ("country_iso3", "continent")


def build_cells() -> bytes:
    rows = products.cell_list_with_areas()
    columns = {k: [r[k] for r in rows] for k in (*CELL_FIELDS, *AREA_FIELDS)}
    return to_json({"n": len(rows), "columns": columns})


def build_columns(year: int, month: int, layer: MapLayer) -> bytes:
    """The month in columns. The records are the validated MapCell records of GET /api/map."""
    wanted = set(CELL_FIELDS) | set(MONTH_FIELDS) | set(field_set(layer))
    records = [c.model_dump(mode="json", include=wanted) for c in products.map_cells(year, month)]
    position = {r["cell_id"]: i for i, r in enumerate(cell_list())}
    index = [position[r["cell_id"]] for r in records]
    encoded = encode_columns(records)
    if index != list(range(len(index))):
        encoded["cell_index"] = index
    return to_json(encoded)


def cells_payload() -> map_cache.MapPayload:
    return map_cache.variant_payload(CELLS_KIND, 0, 0, map_cache.CELLS_FILES, build_cells)


def cells_validator() -> str | None:
    return map_cache.variant_validator(CELLS_KIND, 0, 0, map_cache.CELLS_FILES)


def columns_payload(year: int, month: int, layer: MapLayer) -> map_cache.MapPayload:
    return map_cache.variant_payload(
        COLUMNS_KIND,
        year,
        month,
        map_cache.PRODUCT_FILES,
        lambda: build_columns(year, month, layer),
    )


def columns_validator(year: int, month: int, layer: MapLayer) -> str | None:
    return map_cache.variant_validator(COLUMNS_KIND, year, month, map_cache.PRODUCT_FILES)
