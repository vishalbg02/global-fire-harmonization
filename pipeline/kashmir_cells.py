"""T-086 (D-033): the cells of Jammu and Kashmir by India's official boundary.

FIRMS gives the country of a detection from its file name, and a cell takes the country with most detections, so in the box
72.5 to 80.5 degrees E, 32.5 to 37.2 degrees N some cells are Pakistan or China (risk S23). This script reassigns the cells of that box whose
**centre lies inside India under Natural Earth's India point-of-view boundary** (`ne_10m_admin_0_countries_ind.geojson`, version 5.1.1, 1:10m;
the existing country mapping uses the 1:50m default: a labelled limitation) and regenerates the products that depend on the country:

  * `cells.parquet`: only `country_iso3` of the reassigned cells changes (continent stays Asia; stratum and fire region do not depend on the country);
  * `entity_month.parquet`: the rows of the COUNTRY entities IND, PAK and CHN, computed by the same code (`verdicts.entity_month`) on the new cells;
    every other row is kept as it is, and the recomputed values of those rows are compared with it and reported.

`cell_month_harmonized.parquet` is **not** regenerated (the Lead's scope); its cell-level DIURNAL_CAVEAT for the reassigned cells is a stated limitation.
Cells that differ outside the box, or Indian cells whose centre is outside the India polygon, are reported and not changed.

    python pipeline/kashmir_cells.py --ne C:/IgnisLine-data/ne_ind/ne_10m_admin_0_countries_ind.geojson            # dry run: the plan
    python pipeline/kashmir_cells.py --ne <file> --apply                                                         # write the two products
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parents[1]
BOX = (72.5, 80.5, 32.5, 37.2)               # lon_min, lon_max, lat_min, lat_max (the Lead's box on PR #74)
NE_SIZE = 13_242_091                         # bytes of ne_10m_admin_0_countries_ind.geojson, version 5.1.1
COUNTRIES = ("IND", "PAK", "CHN")            # the entities whose rows are regenerated
KEY = ["entity_type", "entity_id", "year", "month"]

Polygon = list[np.ndarray]                   # the rings of one polygon: the outer ring and its holes, each an (n, 2) array of lon, lat


# ----------------------------------------------------------------------------------------------------- geometry (NumPy only)
def load_polygons(geojson: Path, adm0_a3: str = "IND") -> list[Polygon]:
    """The polygons of one country in a Natural Earth GeoJSON, selected by `ADM0_A3`."""
    data = json.loads(Path(geojson).read_text(encoding="utf-8"))
    out: list[Polygon] = []
    for f in data["features"]:
        if f["properties"].get("ADM0_A3") != adm0_a3:
            continue
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        out += [[np.asarray(ring, dtype=float)[:, :2] for ring in poly] for poly in polys]
    if not out:
        raise ValueError(f"no feature with ADM0_A3 = {adm0_a3}")
    return out


def inside_polygon(lon: np.ndarray, lat: np.ndarray, rings: Polygon) -> np.ndarray:
    """Even-odd ray casting over every ring of one polygon (a point inside a hole is outside)."""
    inside = np.zeros(lon.shape, dtype=bool)
    for ring in rings:
        x1, y1 = ring[:-1, 0], ring[:-1, 1]
        x2, y2 = ring[1:, 0], ring[1:, 1]
        for a, b, c, d in zip(x1, y1, x2, y2, strict=True):
            if b == d:
                continue
            crosses = ((b > lat) != (d > lat)) & (lon < (c - a) * (lat - b) / (d - b) + a)
            inside ^= crosses
    return inside


def inside_polygons(lon: np.ndarray, lat: np.ndarray, polygons: list[Polygon]) -> np.ndarray:
    """A point is inside a multipolygon when it is inside any of its polygons (bounding boxes skip the far ones)."""
    lon, lat = np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)
    out = np.zeros(lon.shape, dtype=bool)
    for rings in polygons:
        outer = rings[0]
        near = (lon >= outer[:, 0].min()) & (lon <= outer[:, 0].max()) & (lat >= outer[:, 1].min()) & (lat <= outer[:, 1].max()) & ~out
        if near.any():
            out[near] = inside_polygon(lon[near], lat[near], rings)
    return out


# ------------------------------------------------------------------------------------------------------------ the plan
def plan(cells: dict[str, np.ndarray], polygons: list[Polygon], box: tuple[float, float, float, float] = BOX) -> dict:
    """What the India point-of-view boundary changes. `cells` holds cell_id, lon_c, lat_c, country_iso3 as arrays.

    changed: cells in the box whose centre is inside India and whose country is another country (reassigned to IND); a cell with no country is reported, not given one;
    india_outside: cells in the box that are India now but whose centre is outside the India polygon (reported, not changed);
    outside_box: cells outside the box whose centre is inside India and whose country is not India (reported, not changed).
    """
    lon, lat = cells["lon_c"].astype(float), cells["lat_c"].astype(float)
    country = np.array([c if c is not None else "" for c in cells["country_iso3"]], dtype=object)
    in_box = (lon >= box[0]) & (lon <= box[1]) & (lat >= box[2]) & (lat <= box[3])
    inside = inside_polygons(lon, lat, polygons)
    changed = in_box & inside & (country != "IND") & (country != "")
    rows = lambda m: [{"cell_id": str(cells["cell_id"][i]), "lon_c": float(lon[i]), "lat_c": float(lat[i]), "old": str(country[i]) or None}
                      for i in np.flatnonzero(m)]
    return {"changed": changed, "changed_rows": rows(changed), "india_outside_rows": rows(in_box & ~inside & (country == "IND")),
            "outside_box_rows": rows(~in_box & inside & (country != "IND") & (country != "")),
            "no_country_inside_rows": rows(inside & (country == "")), "in_box": int(in_box.sum()),
            "box_by_country_before": {str(k) or "none": int(((country == k) & in_box).sum()) for k in np.unique(country[in_box])}}


def reassign(cells: pa.Table, changed: np.ndarray) -> pa.Table:
    """The cells table with `country_iso3` set to IND where `changed`; every other value, column and row is as it was."""
    i = cells.schema.get_field_index("country_iso3")
    new = pc.if_else(pa.array(changed), pa.scalar("IND", pa.string()), cells["country_iso3"])
    return cells.set_column(i, cells.schema.field(i), new)


# -------------------------------------------------------------------------------------------------------- entity rows
def merge_entities(old: pa.Table, new: pa.Table, countries: tuple[str, ...] = COUNTRIES) -> pa.Table:
    """The rows of the COUNTRY entities `countries` from `new`, every other row from `old`, in the order of `old`.
    Both tables must have the same schema and the same keys in the same order."""
    if old.schema != new.schema:
        raise ValueError("schemas differ")
    for k in KEY:
        if not old[k].equals(new[k]):
            raise ValueError(f"the keys differ in {k}")
    take_new = pc.and_(pc.equal(old["entity_type"], "COUNTRY"), pc.is_in(old["entity_id"], pa.array(list(countries))))
    both = pa.concat_tables([old, new])
    n = old.num_rows
    idx = pc.if_else(take_new, pc.add(pa.array(np.arange(n, dtype=np.int64)), n), pa.array(np.arange(n, dtype=np.int64)))
    return both.take(idx)


def rows_differences(old: pa.Table, new: pa.Table, mask: np.ndarray) -> dict:
    """For the rows in `mask`: how many rows differ in any column between `old` and `new`, and the largest relative difference of a float column."""
    differing = np.zeros(int(mask.sum()), dtype=bool)
    worst = 0.0
    for name in old.column_names:
        a, b = old[name].to_numpy(zero_copy_only=False)[mask], new[name].to_numpy(zero_copy_only=False)[mask]
        if old.schema.field(name).type == pa.float64():
            a, b = a.astype(float), b.astype(float)
            same = (a == b) | (np.isnan(a) & np.isnan(b))
            both = ~np.isnan(a) & ~np.isnan(b) & ~same
            if both.any():
                worst = max(worst, float(np.max(np.abs(a[both] - b[both]) / np.maximum(np.abs(a[both]), 1e-300))))
        else:
            same = np.array([str(x) == str(y) for x, y in zip(a, b, strict=True)])
        differing |= ~same
    return {"rows": int(mask.sum()), "rows_differing": int(differing.sum()), "max_relative_difference": worst}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# -------------------------------------------------------------------------------------------------------------- main
def main() -> int:
    import duckdb
    import verdicts as vd

    ap = argparse.ArgumentParser()
    ap.add_argument("--ne", type=Path, required=True, help="ne_10m_admin_0_countries_ind.geojson (version 5.1.1)")
    ap.add_argument("--apply", action="store_true", help="write cells.parquet and entity_month.parquet (default: only print the plan)")
    args = ap.parse_args()
    if args.ne.stat().st_size != NE_SIZE:
        raise SystemExit(f"{args.ne}: expected {NE_SIZE:,} bytes, found {args.ne.stat().st_size:,}")
    paths = vd.Paths()
    cells = pq.read_table(paths.products / "cells.parquet")
    arr = {k: cells[k].to_numpy(zero_copy_only=False) for k in ("cell_id", "lon_c", "lat_c", "country_iso3")}
    p = plan(arr, load_polygons(args.ne))
    report = {"ne_file": args.ne.name, "ne_sha256": sha256(args.ne), "ne_bytes": args.ne.stat().st_size, "box": BOX, "cells_in_box": p["in_box"],
              "box_by_country_before": p["box_by_country_before"], "changed": len(p["changed_rows"]), "changed_rows": p["changed_rows"],
              "india_outside_rows": p["india_outside_rows"], "outside_box_rows": p["outside_box_rows"],
              "no_country_inside_rows": p["no_country_inside_rows"]}
    by_old: dict = {}
    for r in p["changed_rows"]:
        by_old[r["old"]] = by_old.get(r["old"], 0) + 1
    report["changed_by_old_country"] = by_old
    print(json.dumps({k: v for k, v in report.items() if not k.endswith("_rows")}, indent=1))
    print("reported, not changed: Indian cells with the centre outside the India polygon:", len(p["india_outside_rows"]),
          "| differing cells outside the box:", len(p["outside_box_rows"]),
          "| cells with no country inside India:", len(p["no_country_inside_rows"]))
    qa = ROOT / "data" / "interim" / "qa"
    qa.mkdir(parents=True, exist_ok=True)
    (qa / "kashmir_cells.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    if not args.apply:
        return 0

    new_cells = reassign(cells, p["changed"])
    assert new_cells.schema == cells.schema and new_cells.num_rows == cells.num_rows
    for name in cells.column_names:       # only country_iso3 may differ, and only where planned
        if name != "country_iso3":
            assert new_cells[name].equals(cells[name]), name
    old_entities = pq.read_table(paths.products / "entity_month.parquet")
    work = paths.tmp
    work.mkdir(parents=True, exist_ok=True)
    pq.write_table(new_cells, paths.products / "cells.parquet", compression="zstd")
    con = duckdb.connect()
    con.execute(f"SET temp_directory='{work.as_posix()}'")
    con.execute("SET memory_limit='6GB'")
    cmw = f"read_parquet('{(paths.products / 'cell_month_witness.parquet').as_posix()}')"
    years, months = vd._months_axis(con, cmw)
    tmp_out = work / "entity_month_t086.parquet"
    vd.entity_month(con, paths, years, months, tmp_out)
    recomputed = pq.read_table(tmp_out)
    merged = merge_entities(old_entities, recomputed)
    is_three = ((old_entities["entity_type"].to_numpy(zero_copy_only=False) == "COUNTRY")
                & np.isin(old_entities["entity_id"].to_numpy(zero_copy_only=False), list(COUNTRIES)))
    report["others_recomputed_vs_main"] = rows_differences(old_entities, recomputed, ~is_three)
    report["three_old_vs_new"] = rows_differences(old_entities, recomputed, is_three)
    pq.write_table(merged, paths.products / "entity_month.parquet", compression="zstd")
    report["sha256"] = {"cells.parquet": sha256(paths.products / "cells.parquet"),
                        "entity_month.parquet": sha256(paths.products / "entity_month.parquet")}
    (qa / "kashmir_cells.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("others_recomputed_vs_main", "three_old_vs_new", "sha256")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
