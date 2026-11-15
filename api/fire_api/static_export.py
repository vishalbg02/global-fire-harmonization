"""Export the preset views as static JSON files, for the offline copy of the app (T-043).

Every file is the API's own answer: the endpoints are called in-process through the FastAPI test
client, so there is one implementation and the files cannot disagree with it. Nothing is computed.
The one change of form is the map: the API's full response for a month is about 28 MB, so a month is
written column by column (a shared ``cells.json`` holds the ids and bounds once), which decodes back
to exactly the API's records.

    PRODUCTS_DIR=../data/products python -m fire_api.static_export --out ../app/public/data

One products directory per export. A non-empty output directory is refused unless ``--overwrite``
is given, and then only a directory that holds this script's ``manifest.json`` is cleared.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from .columnar import (
    CELL_FIELDS,
    CellList,
    ExportError,
    decode_columns,
    encode_cells,
    encode_columns,
)
from .main import app

FORMAT_VERSION = 1
MANIFEST = "manifest.json"
SUBDIRS = ("series", "anomalies", "map", "export")
TOP_FILES = (
    "meta.json",
    "validation.json",
    "entities-COUNTRY.json",
    "entities-CONTINENT.json",
    "cells.json",
    MANIFEST,
)
SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
ANOMALIES_LIMIT = 500

# The columnar helpers live in fire_api.columnar; the names stay importable from here.
__all__ = [
    "CELL_FIELDS",
    "CellList",
    "ExportError",
    "decode_columns",
    "encode_cells",
    "encode_columns",
    "export_static",
    "main",
]


# ------------------------------------------------------------------ the export
def _months(first: str, last: str) -> list[tuple[int, int]]:
    y, m = int(first[:4]), int(first[5:7])
    ly, lm = int(last[:4]), int(last[5:7])
    out = []
    while (y, m) <= (ly, lm):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _write_json(path: Path, value: Any) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    path.write_bytes(data)
    return len(data)


def _prepare(out: Path, overwrite: bool) -> None:
    if out.exists() and any(out.iterdir()):
        if not overwrite:
            raise ExportError(
                f"{out} is not empty. Use --overwrite to replace an earlier export "
                "(only a directory that holds this script's manifest.json is cleared)."
            )
        if not (out / MANIFEST).is_file():
            raise ExportError(
                f"{out} has no {MANIFEST}, so it is not an earlier export: not cleared."
            )
        for sub in SUBDIRS:
            shutil.rmtree(out / sub, ignore_errors=True)
        for name in TOP_FILES:
            (out / name).unlink(missing_ok=True)
    out.mkdir(parents=True, exist_ok=True)


def _get(client: TestClient, url: str) -> Any:
    response = client.get(url)
    if response.status_code != 200:
        raise ExportError(f"GET {url} answered {response.status_code}: {response.text[:200]}")
    return response


def export_static(
    out: Path,
    *,
    overwrite: bool = False,
    latest_months: int | None = None,
    only_months: list[str] | None = None,
    client: TestClient | None = None,
    log: Any = None,
) -> dict[str, Any]:
    """Write the offline copy into ``out`` and return the manifest."""
    say = log or (lambda _m: None)
    client = client or TestClient(app)
    started = time.monotonic()
    _prepare(out, overwrite)

    meta = _get(client, "/api/meta").json()
    sizes = {"meta.json": _write_json(out / "meta.json", meta)}
    sizes["validation.json"] = _write_json(
        out / "validation.json", _get(client, "/api/validation").json()
    )

    entities: list[dict[str, Any]] = []
    for kind in ("COUNTRY", "CONTINENT"):
        items = _get(client, f"/api/entities?type={kind}").json()
        sizes[f"entities-{kind}.json"] = _write_json(out / f"entities-{kind}.json", items)
        entities += [{"entity_type": kind, "entity_id": i["entity_id"]} for i in items]
    entities.append({"entity_type": "GLOBAL", "entity_id": "GLOBAL"})
    for e in entities:
        if not SAFE_ID.match(e["entity_id"]):
            raise ExportError(f"entity id {e['entity_id']!r} is not safe to use in a file name")

    exports: dict[str, str] = {}
    series_bytes = export_bytes = 0
    for e in entities:
        key = f"{e['entity_type']}-{e['entity_id']}"
        query = f"entity_type={e['entity_type']}&entity_id={e['entity_id']}"
        series_bytes += _write_json(
            out / "series" / f"{key}.json", _get(client, f"/api/series?{query}").json()
        )
        csv = _get(client, f"/api/export.csv?{query}")
        (out / "export").mkdir(parents=True, exist_ok=True)
        (out / "export" / f"{key}.csv").write_bytes(csv.content)
        disposition = csv.headers.get("content-disposition", "")
        match = re.search(r'filename="([^"]+)"', disposition)
        exports[key] = match.group(1) if match else f"{key}.csv"
        export_bytes += len(csv.content)
    say(f"{len(entities)} series and CSV files written")

    months = _months(meta["first_month"], meta["latest_month"])
    if latest_months is not None:
        months = months[-latest_months:]
    if only_months is not None:
        months = [(int(m[:4]), int(m[5:7])) for m in only_months]
    cells = CellList()
    map_bytes = anomalies_bytes = 0
    written: list[str] = []
    for year, month in months:
        label = f"{year}-{month:02d}"
        records = _get(client, f"/api/map?year={year}&month={month}&layer=raw").json()
        index = cells.index_of(records)
        encoded = encode_columns(records)
        if index != list(range(len(index))):
            encoded["cell_index"] = index  # not simply the first n cells of the shared list
        map_bytes += _write_json(out / "map" / f"{label}.json", encoded)
        written.append(label)
        if len(written) % 25 == 0:
            say(f"{len(written)} of {len(months)} months written")

    # The anomaly lists are small, and the calendar can select any month, so every month of the data
    # has one even when the map covers fewer months.
    for year, month in _months(meta["first_month"], meta["latest_month"]):
        url = f"/api/anomalies?year={year}&month={month}&limit={ANOMALIES_LIMIT}"
        anomalies_bytes += _write_json(
            out / "anomalies" / f"{year}-{month:02d}.json", _get(client, url).json()
        )
    sizes["cells.json"] = _write_json(out / "cells.json", cells.columns())
    sizes.update(
        {
            "series (all)": series_bytes,
            "export (all)": export_bytes,
            "map (all months)": map_bytes,
            "anomalies (all months)": anomalies_bytes,
        }
    )
    manifest = {
        "format_version": FORMAT_VERSION,
        "exported_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "synthetic": meta["synthetic"],
        "contract_version": meta["contract_version"],
        "method_version": meta["method_version"],
        "data_snapshot": meta.get("data_snapshot"),
        "months": written,
        "entities": len(entities),
        "exports": exports,
        "bytes": sizes,
        "seconds": round(time.monotonic() - started, 1),
    }
    _write_json(out / MANIFEST, manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export the preset views as static JSON (T-043).")
    parser.add_argument(
        "--out", type=Path, required=True, help="output directory (for example ../app/public/data)"
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="replace an earlier export in --out"
    )
    parser.add_argument(
        "--latest-months", type=int, default=None, help="only the last N months (for a quick test)"
    )
    args = parser.parse_args(argv)
    try:
        manifest = export_static(
            args.out,
            overwrite=args.overwrite,
            latest_months=args.latest_months,
            log=lambda m: print(m, file=sys.stderr),
        )
    except ExportError as exc:
        print(f"static_export: {exc}", file=sys.stderr)
        return 1
    total = sum(v for k, v in manifest["bytes"].items() if "(all" in k or k.endswith(".json"))
    months, areas, seconds = len(manifest["months"]), manifest["entities"], manifest["seconds"]
    print(f"exported {months} months, {areas} areas, {total / 1e6:.1f} MB in {seconds} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
