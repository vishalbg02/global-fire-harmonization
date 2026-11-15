"""The columnar layout of a map month, shared by the offline export and GET /api/map/columns.

A month is stored column by column: a column that is the same for every cell is kept once
(``const``), a column with few distinct values keeps them once and an index per cell (``dict`` +
``idx``), and the rest is a plain list (``values``). The ids and bounds of the cells are kept once
in a shared cell list; a month names its cells by position in that list (``cell_index``). Nothing
is computed or rounded here: ``decode_columns`` gives back exactly the records that were encoded.
"""

from typing import Any

# Fields that belong to the shared cell list, not to a month.
CELL_FIELDS = ("cell_id", "lat_min", "lat_max", "lon_min", "lon_max")


class ExportError(Exception):
    """The export cannot be made as asked."""


def _token(value: Any) -> Any:
    """A hashable key that tells apart values that print differently (1 and 1.0, a list and its
    items): the same grouping as comparing their JSON text, without printing every value."""
    if isinstance(value, list):
        return ("list", tuple(_token(v) for v in value))
    if isinstance(value, dict):
        return ("dict", tuple(sorted((k, _token(v)) for k, v in value.items())))
    return (type(value).__name__, value)


def encode_columns(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Records with the same keys to one column per key.

    A column is ``{"const": v}`` when every value is equal, ``{"dict": [...], "idx": [...]}`` when
    a value (a text, or a list such as ``reason_codes``) repeats a lot, else ``{"values": [...]}``.
    """
    keys = [k for k in records[0] if k not in CELL_FIELDS] if records else []
    columns: dict[str, Any] = {}
    for key in keys:
        values = [r[key] for r in records]
        first = values[0]
        if all(v == first for v in values):
            columns[key] = {"const": first}
            continue
        unique: dict[Any, int] = {}
        table: list[Any] = []
        index: list[int] = []
        for v in values:
            token = _token(v)
            if token not in unique:
                unique[token] = len(table)
                table.append(v)
            index.append(unique[token])
        if len(table) <= len(values) // 4:
            columns[key] = {"dict": table, "idx": index}
        else:
            columns[key] = {"values": values}
    return {"n": len(records), "columns": columns}


def decode_columns(encoded: dict[str, Any], cells: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """The inverse of ``encode_columns``, joined with the shared cell list.

    ``cell_index`` (when present) says which cells of the shared list the month has, in order;
    without it the month has the first ``n`` cells.
    """
    n = int(encoded["n"])
    index = encoded.get("cell_index") or list(range(n))
    out: list[dict[str, Any]] = [{k: cells[k][j] for k in CELL_FIELDS} for j in index]
    for key, column in encoded["columns"].items():
        if "const" in column:
            for record in out:
                record[key] = column["const"]
        elif "dict" in column:
            table, idx = column["dict"], column["idx"]
            for i, record in enumerate(out):
                record[key] = table[idx[i]]
        else:
            for i, record in enumerate(out):
                record[key] = column["values"][i]
    return out


class CellList:
    """The shared cell list: every cell of every month once, in the order first seen."""

    def __init__(self) -> None:
        self.position: dict[str, int] = {}
        self.rows: list[dict[str, Any]] = []

    def index_of(self, records: list[dict[str, Any]]) -> list[int]:
        """The positions of a month's cells in the list, adding the cells not seen before."""
        out = []
        for r in records:
            at = self.position.get(r["cell_id"])
            if at is None:
                at = len(self.rows)
                self.position[r["cell_id"]] = at
                self.rows.append({k: r[k] for k in CELL_FIELDS})
            elif any(self.rows[at][k] != r[k] for k in CELL_FIELDS):
                raise ExportError(f"cell {r['cell_id']} changes its bounds between months")
            out.append(at)
        return out

    def columns(self) -> dict[str, list[Any]]:
        return {k: [r[k] for r in self.rows] for k in CELL_FIELDS}


def encode_cells(records: list[dict[str, Any]]) -> dict[str, list[Any]]:
    cells = CellList()
    cells.index_of(records)
    return cells.columns()
