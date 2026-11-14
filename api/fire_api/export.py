"""CSV export of a monthly series (T-038).

The rows are the stored `entity_month` values, written as received: nothing is rounded,
converted or filled in. A missing value is an empty cell (never 0); a real 0 is written `0`.
"""

import csv
import io
import json
import re
from collections.abc import Sequence

from .models import EntityMonth, Metadata, Witness

BOM = "﻿"

# Column order follows the contract (`entity_month`, then one column per satellite).
COLUMNS = [
    "entity_type", "entity_id", "entity_name", "year", "month",
    "estimate", "ci90_low", "ci90_high", "sd", "raw_combined_cell_days",
    "witnesses_used", "n_witnesses", "disagreement_scale",
    "baseline_median", "baseline_p25", "baseline_p75",
    "pct_of_normal", "p_above", "p_below", "p_within",
    "verdict", "reason_codes", "data_level", "method_version", "n_cells",
]  # fmt: skip
RAW_COLUMNS = [f"raw_{w.value}" for w in Witness]

MEANING = (
    "Values are satellite-detected fire activity in fire-active cell-days "
    "(Aqua-equivalent scale); not fire counts or burned area."
)
ACKNOWLEDGEMENT = (
    "We acknowledge the use of data and imagery from NASA's Fire Information for Resource "
    "Management System (FIRMS) (https://earthdata.nasa.gov/firms), part of NASA's Earth Science "
    'Data and Information System (ESDIS), and from LANCE. FIRMS data are provided "as is".'
)
HOTSPOTS_NOTE = "Raw hotspot points are not included; they are available from NASA FIRMS."
UNCERTAINTY_NOTE = (
    "ci90_low and ci90_high are the 90% interval of the estimate; verdict and p_above, p_below, "
    "p_within describe the estimate against the baseline (see method_version)."
)
# Dataset DOIs from the collection metadata of NASA's CMR catalogue
# (https://cmr.earthdata.nasa.gov/search/collections.umm_json?short_name=<short name>).
SP_DOIS = [
    ("MODIS/Aqua MYD14 V061", "10.5067/MODIS/MYD14.061"),
    ("MODIS/Terra MOD14 V061", "10.5067/MODIS/MOD14.061"),
    ("VIIRS/NPP VNP14IMG V002", "10.5067/VIIRS/VNP14IMG.002"),
    ("VIIRS/JPSS1 VJ114IMG V002", "10.5067/VIIRS/VJ114IMG.002"),
]
# Near-real-time product DOIs, copied from the NASA Earthdata catalogue pages of each product.
NRT_DOIS = [
    ("MODIS MCD14DL NRT", "10.5067/FIRMS/MODIS/MCD14DL.NRT.0061"),
    ("VIIRS S-NPP VNP14IMGT NRT", "10.5067/FIRMS/VIIRS/VNP14IMGT_NRT.002"),
    ("VIIRS NOAA-20 VJ114IMGT NRT", "10.5067/FIRMS/VIIRS/VJ114IMGT_NRT.002"),
]


def _dois(items: list[tuple[str, str]]) -> str:
    return "; ".join(f"{name} doi:{doi}" for name, doi in items)


_FORMULA_START = ("=", "+", "-", "@")


def _text(value: str) -> str:
    """Text cells that a spreadsheet could read as a formula are prefixed with an apostrophe."""
    return "'" + value if value.startswith(_FORMULA_START) else value


def _number(value: float | int | None) -> str:
    return "" if value is None else repr(value) if isinstance(value, float) else str(value)


def _raw_by_witness(record: EntityMonth) -> dict[str, int | None]:
    try:
        parsed = json.loads(record.raw_by_witness) if record.raw_by_witness else {}
    except json.JSONDecodeError:
        parsed = {}
    return {name: parsed.get(name) for name in (w.value for w in Witness)}


def _row(record: EntityMonth) -> list[str]:
    raw = _raw_by_witness(record)
    return [
        _text(record.entity_type.value), _text(record.entity_id), _text(record.entity_name),
        _number(record.year), _number(record.month),
        _number(record.estimate), _number(record.ci90_low), _number(record.ci90_high),
        _number(record.sd), _number(record.raw_combined_cell_days),
        ";".join(w.value for w in record.witnesses_used), _number(record.n_witnesses),
        _number(record.disagreement_scale),
        _number(record.baseline_median), _number(record.baseline_p25),
        _number(record.baseline_p75),
        _number(record.pct_of_normal), _number(record.p_above), _number(record.p_below),
        _number(record.p_within),
        record.verdict.value, ";".join(c.value for c in record.reason_codes),
        record.data_level.value, _text(record.method_version), _number(record.n_cells),
        *(_number(raw[name]) for name in (w.value for w in Witness)),
    ]  # fmt: skip


def header_lines(meta: Metadata, subject: str) -> list[str]:
    status = "SYNTHETIC (not NASA observations)" if meta.synthetic else "REAL"
    snapshot = meta.data_snapshot
    lines = [
        f"data_status: {status}",
        f"area: {subject}",
        f"method_version: {meta.method_version}",
        f"contract_version: {meta.contract_version}",
        f"generated_at: {meta.generated_at}",
        f"data_snapshot_zips_downloaded: {snapshot.zips_downloaded or 'none'}",
        f"data_snapshot_api_pulled: {snapshot.api_pulled or 'none'}",
        f"meaning: {MEANING}",
        f"citation: {meta.citation}",
        f"acknowledgement: {ACKNOWLEDGEMENT}",
        f"notes: {HOTSPOTS_NOTE} {UNCERTAINTY_NOTE}",
        f"dataset_dois_standard_products_(SP): {_dois(SP_DOIS)}",
        f"dataset_dois_near-real-time_(NRT): {_dois(NRT_DOIS)}",
    ]
    return [f"# {line}" for line in lines]


def build_csv(records: Sequence[EntityMonth], meta: Metadata, subject: str) -> bytes:
    """UTF-8 with a byte-order mark, `#` metadata lines, then the table with CRLF line ends."""
    out = io.StringIO(newline="")
    out.write(BOM)
    for line in header_lines(meta, subject):
        out.write(line.replace("\r", " ").replace("\n", " ") + "\r\n")
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow([*COLUMNS, *RAW_COLUMNS])
    for record in records:
        writer.writerow(_row(record))
    return out.getvalue().encode("utf-8")


def _safe(part: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", part).strip("-") or "area"


def filename(entity_type: str, entity_id: str, meta: Metadata) -> str:
    prefix = "SYNTHETIC_" if meta.synthetic else ""
    return (
        f"{prefix}fire-harmonization_{_safe(entity_type)}_{_safe(entity_id)}"
        f"_{_safe(meta.method_version)}.csv"
    )
