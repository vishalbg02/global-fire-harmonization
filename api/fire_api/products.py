"""Read-only access to the contract products: Parquet through DuckDB, JSON as files.

This module selects, filters, joins and orders stored values. It never computes science:
no conversions, baselines, percentiles, probabilities or verdicts.
"""

import json
import os
from pathlib import Path
from typing import Any

import duckdb

from .models import (
    Anomaly,
    EntityEvidence,
    EntityItem,
    EntityMonth,
    EntityType,
    MapCell,
    Metadata,
    ValidationResults,
)

DEFAULT_PRODUCTS_DIR = "data/products"
HARMONIZED_VERDICTS = ("ABOVE_NORMAL", "BELOW_NORMAL")


class ProductsUnavailable(Exception):
    """A product file is missing or unreadable."""


class NotFound(Exception):
    """The requested entity, or its month, does not exist in the products."""


def products_dir() -> Path:
    """The products directory from PRODUCTS_DIR (default `data/products`), read on every call.

    An empty value (as in a copied `.env.example`) counts as unset.
    """
    return Path(os.environ.get("PRODUCTS_DIR") or DEFAULT_PRODUCTS_DIR)


def _file(name: str) -> Path:
    path = products_dir() / name
    if not path.is_file():
        raise ProductsUnavailable(f"Product file not found: {name}")
    return path


def _query(sql: str, params: list[Any]) -> list[dict[str, Any]]:
    """Run SQL on a fresh in-memory DuckDB connection; return rows as dicts (None stays None)."""
    try:
        con = duckdb.connect()
        try:
            cursor = con.execute(sql, params)
            columns = [d[0] for d in cursor.description]
            return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
        finally:
            con.close()
    except duckdb.Error as exc:
        raise ProductsUnavailable(f"A product could not be read: {exc}") from exc


def _json(name: str) -> Any:
    try:
        return json.loads(_file(name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductsUnavailable(f"A product could not be read: {name}") from exc


def metadata() -> Metadata:
    return Metadata.model_validate(_json("metadata.json"))


def validation_results() -> ValidationResults:
    return ValidationResults.model_validate(_json("validation_results.json"))


def entities(entity_type: EntityType) -> list[EntityItem]:
    """Entities of one type with a bbox [W, S, E, N].

    The contract has no product with entity bounding boxes, so the bbox is the envelope
    (min and max) of the bounds of the cells assigned to the entity. Entities with no cells
    have no derivable bbox and are not listed.
    """
    column = {EntityType.COUNTRY: "country_iso3", EntityType.CONTINENT: "continent"}[entity_type]
    rows = _query(
        f"""
        SELECT e.entity_type, e.entity_id, e.entity_name,
               b.w, b.s, b.e, b.n
        FROM (SELECT DISTINCT entity_type, entity_id, entity_name
              FROM read_parquet(?) WHERE entity_type = ?) AS e
        JOIN (SELECT {column} AS entity_id,
                     min(lon_min) AS w, min(lat_min) AS s, max(lon_max) AS e, max(lat_max) AS n
              FROM read_parquet(?) WHERE {column} IS NOT NULL GROUP BY {column}) AS b
          ON b.entity_id = e.entity_id
        ORDER BY e.entity_id
        """,
        [str(_file("entity_month.parquet")), entity_type.value, str(_file("cells.parquet"))],
    )
    return [
        EntityItem(
            entity_type=r["entity_type"],
            entity_id=r["entity_id"],
            entity_name=r["entity_name"],
            bbox=(r["w"], r["s"], r["e"], r["n"]),
        )
        for r in rows
    ]


def map_cells(year: int, month: int) -> list[MapCell]:
    """Every analysis cell for one month: cell bounds joined to cell_month_harmonized."""
    rows = _query(
        """
        SELECT c.cell_id, c.lat_min, c.lat_max, c.lon_min, c.lon_max,
               h.* EXCLUDE (cell_id)
        FROM read_parquet(?) AS h
        JOIN read_parquet(?) AS c USING (cell_id)
        WHERE h.year = ? AND h.month = ?
        ORDER BY c.cell_id
        """,
        [str(_file("cell_month_harmonized.parquet")), str(_file("cells.parquet")), year, month],
    )
    return [MapCell.model_validate(r) for r in rows]


def _entity_exists(entity_type: EntityType, entity_id: str) -> bool:
    rows = _query(
        "SELECT 1 AS found FROM read_parquet(?) WHERE entity_type = ? AND entity_id = ? LIMIT 1",
        [str(_file("entity_month.parquet")), entity_type.value, entity_id],
    )
    return bool(rows)


def series(entity_type: EntityType, entity_id: str) -> list[EntityMonth]:
    """The monthly series of a preset entity, ordered by year then month."""
    if not _entity_exists(entity_type, entity_id):
        raise NotFound(f"Unknown entity: {entity_type.value} {entity_id}")
    rows = _query(
        """
        SELECT * FROM read_parquet(?)
        WHERE entity_type = ? AND entity_id = ?
        ORDER BY year, month
        """,
        [str(_file("entity_month.parquet")), entity_type.value, entity_id],
    )
    return [EntityMonth.model_validate(r) for r in rows]


def evidence(entity_type: EntityType, entity_id: str, year: int, month: int) -> EntityEvidence:
    """One entity_month record with `raw_by_witness` decoded from its JSON string."""
    if not _entity_exists(entity_type, entity_id):
        raise NotFound(f"Unknown entity: {entity_type.value} {entity_id}")
    rows = _query(
        """
        SELECT * FROM read_parquet(?)
        WHERE entity_type = ? AND entity_id = ? AND year = ? AND month = ?
        """,
        [str(_file("entity_month.parquet")), entity_type.value, entity_id, year, month],
    )
    if not rows:
        raise NotFound(f"No record for {entity_type.value} {entity_id} in {year}-{month:02d}")
    row = rows[0]
    encoded = row["raw_by_witness"]
    row["raw_by_witness"] = None if encoded is None else json.loads(encoded)
    return EntityEvidence.model_validate(row)


def anomalies(year: int, month: int, limit: int) -> list[Anomaly]:
    """Entities with a confident verdict in a month, ordered by max(p_above, p_below) descending.

    Selection and ordering only: the probabilities and verdicts are read as stored.
    """
    rows = _query(
        """
        SELECT entity_type, entity_id, entity_name, verdict, p_above, p_below, pct_of_normal
        FROM read_parquet(?)
        WHERE year = ? AND month = ? AND verdict IN ('ABOVE_NORMAL', 'BELOW_NORMAL')
        ORDER BY greatest(p_above, p_below) DESC NULLS LAST, entity_type, entity_id
        LIMIT ?
        """,
        [str(_file("entity_month.parquet")), year, month, limit],
    )
    return [Anomaly.model_validate(r) for r in rows]


def cells_with_centre_in(west: float, south: float, east: float, north: float) -> list[str]:
    """IDs of the analysis cells whose centre lies inside the box (bounds inclusive)."""
    rows = _query(
        """
        SELECT cell_id FROM read_parquet(?)
        WHERE lon_c BETWEEN ? AND ? AND lat_c BETWEEN ? AND ?
        ORDER BY cell_id
        """,
        [str(_file("cells.parquet")), west, east, south, north],
    )
    return [r["cell_id"] for r in rows]
