"""Fire-region mask: the 14 GFED basis regions for every analysis cell (T-004).

The regions come from the GFED4s basis-regions grid (0.25 degrees; van der Werf et al., 2017,
ESSD 9, 697-720). Every analysis cell gets a region:

  GFED          most common GFED region among the cell's land 0.25 degree sub-cells
                (a tie takes the lowest region number)
  NEAREST_LAND  no land sub-cell: the region of the nearest land cell within 1.0 degree
  UNASSIGNED    no land within 1.0 degree: pooled directly to the global ratio

The fallback rules are proposals for the Lead. The lookup works for any analysis grid size.

    python pipeline/fire_regions.py build --hdf5 path/to/GFED4.1s_2001.hdf5   # one-time, needs h5py
    python pipeline/fire_regions.py report                                    # coverage on the detections
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "interim" / "fire_regions"
DETECTIONS = ROOT / "data" / "interim" / "detections"
GRID_NPY = "basis_regions_0.25.npy"

SUB = 0.25  # GFED grid size in degrees
NROW, NCOL = 720, 1440
FALLBACK_RADIUS_DEG = 1.0
UNASSIGNED = "UNASSIGNED"
REGION_NAMES = {
    1: ("BONA", "Boreal North America"), 2: ("TENA", "Temperate North America"), 3: ("CEAM", "Central America"),
    4: ("NHSA", "Northern Hemisphere South America"), 5: ("SHSA", "Southern Hemisphere South America"),
    6: ("EURO", "Europe"), 7: ("MIDE", "Middle East"), 8: ("NHAF", "Northern Hemisphere Africa"),
    9: ("SHAF", "Southern Hemisphere Africa"), 10: ("BOAS", "Boreal Asia"), 11: ("CEAS", "Central Asia"),
    12: ("SEAS", "Southeast Asia"), 13: ("EQAS", "Equatorial Asia"), 14: ("AUST", "Australia and New Zealand"),
}
CODES = {k: v[0] for k, v in REGION_NAMES.items()}


# ---------------------------------------------------------------------------------- reading
def read_basis_regions_hdf5(path: Path) -> np.ndarray:
    """Read ancill/basis_regions (720 x 1440, north first) from a GFED4s HDF5 file. Needs h5py."""
    import h5py
    with h5py.File(path, "r") as f:
        d = f["ancill/basis_regions"]
        grid = d[:].astype(np.uint8)
        for k, (code, _) in REGION_NAMES.items():  # the class names in the file must match this table
            label = d.attrs[f"class_{k}"]
            label = label.decode() if isinstance(label, bytes) else label
            if not label.startswith(code):
                raise ValueError(f"class_{k} is {label!r}, expected {code}")
    if grid.shape != (NROW, NCOL):
        raise ValueError(f"unexpected grid shape {grid.shape}")
    return grid


def load_grid(folder: Path = OUT) -> np.ndarray:
    return np.load(folder / GRID_NPY)


# ---------------------------------------------------------------------------------- lookup
def subcell_index(lat, lon):
    """Row (from the north) and column (from -180) in the 0.25 degree grid; longitude 180 counts as -180.

    Cell bounds are lower-inclusive, upper-exclusive (the proposed convention in the Member 2 prompt, S.3)."""
    lat, lon = np.asarray(lat, dtype=float), np.asarray(lon, dtype=float)
    lon = np.where(lon >= 180.0, lon - 360.0, lon)
    # lower bound inclusive, upper bound exclusive (the top row also takes lat 90): a point exactly on a
    # sub-cell's southern edge belongs to that sub-cell, which is the row north of the edge in a north-first grid
    r = np.clip(np.ceil((90.0 - lat) / SUB).astype(int) - 1, 0, NROW - 1)
    c = np.clip(np.floor((lon + 180.0) / SUB).astype(int), 0, NCOL - 1)
    return r, c


def region_at(grid: np.ndarray, lat, lon):
    """GFED class (0 = ocean, 1 to 14) at a point, with no fallback."""
    r, c = subcell_index(lat, lon)
    return grid[r, c]


# ---------------------------------------------------------------------------- analysis cells
def nearest_land_fill(grid: np.ndarray, radius_cells: int) -> np.ndarray:
    """For every 0.25 degree cell, the class of the nearest land cell within radius_cells (0 if none).

    Distance is measured in degrees on the sphere's local scale (longitude steps shrink with cos(lat)).
    Land cells keep their own class. Ties take the lowest class number.
    """
    h, w = grid.shape
    lat = 90.0 - SUB * (np.arange(h) + 0.5)
    cos = np.cos(np.radians(lat))[:, None]
    best = np.full((h, w), np.inf)
    out = np.where(grid > 0, grid, 0).astype(np.uint8)
    best[grid > 0] = 0.0
    padded = np.zeros((h + 2 * radius_cells, w), dtype=np.uint8)
    padded[radius_cells:radius_cells + h] = grid
    for dr in range(-radius_cells, radius_cells + 1):
        rows = padded[radius_cells + dr: radius_cells + dr + h]
        for dc in range(-radius_cells, radius_cells + 1):
            if dr == 0 and dc == 0:
                continue
            cand = np.roll(rows, -dc, axis=1)  # longitude wraps around the date line
            dist = np.sqrt(dr ** 2 + (dc * cos) ** 2) * SUB
            ok = (cand > 0) & (dist <= FALLBACK_RADIUS_DEG + 1e-9)
            better = ok & ((dist < best) | ((dist == best) & (cand < out)))
            best = np.where(better, dist, best)
            out = np.where(better, cand, out)
    return out


def assign_grid(grid: np.ndarray, res: float = 0.5) -> dict:
    """A region for every analysis cell of size `res` degrees (res must be a multiple of 0.25).

    Returns row and column indices (row from the south, column from -180), the region code per cell,
    the method per cell, and how many cells were decided by a tie.
    """
    k = round(res / SUB)
    if abs(k * SUB - res) > 1e-9 or NROW % k or NCOL % k:
        raise ValueError(f"resolution {res} is not a multiple of {SUB} that divides the grid")
    south = grid[::-1]  # row 0 = southernmost
    nr, nc = NROW // k, NCOL // k
    blocks = south.reshape(nr, k, nc, k).transpose(0, 2, 1, 3).reshape(nr, nc, k * k)
    counts = np.stack([(blocks == v).sum(axis=2) for v in range(1, 15)])  # (14, nr, nc)
    has_land = counts.sum(axis=0) > 0
    top = counts.argmax(axis=0) + 1  # argmax takes the first maximum: the lowest class on ties
    sorted_counts = np.sort(counts, axis=0)
    tie = has_land & (sorted_counts[-1] == sorted_counts[-2])
    region = np.where(has_land, top, 0)
    method = np.where(has_land, "GFED", UNASSIGNED).astype(object)
    # no land sub-cell: nearest land within the radius, taken from the filled 0.25 degree grid
    radius = round(FALLBACK_RADIUS_DEG / SUB)
    filled = nearest_land_fill(grid, radius)[::-1]
    fblocks = filled.reshape(nr, k, nc, k).transpose(0, 2, 1, 3).reshape(nr, nc, k * k)
    fcounts = np.stack([(fblocks == v).sum(axis=2) for v in range(1, 15)])
    f_has = fcounts.sum(axis=0) > 0
    f_top = fcounts.argmax(axis=0) + 1
    use_fill = ~has_land & f_has
    region = np.where(use_fill, f_top, region)
    method = np.where(use_fill, "NEAREST_LAND", method)
    rows, cols = np.indices((nr, nc))
    return {"res": res, "row": rows, "col": cols, "region": region, "method": method, "tie": tie}


def cell_id(res: float, row: int, col: int) -> str:
    return f"g{round(res * 100):03d}_r{row:04d}_c{col:04d}"


def region_name(code: int) -> str:
    return CODES.get(code, UNASSIGNED)


def cell_table(assigned: dict) -> dict[str, list]:
    """Flat columns (cell_id, fire_region, method) for every analysis cell."""
    res = assigned["res"]
    ids, regs, meth, rows, cols = [], [], [], [], []
    nr, nc = assigned["region"].shape
    for r in range(nr):
        for c in range(nc):
            ids.append(cell_id(res, r, c))
            regs.append(region_name(int(assigned["region"][r, c])) if assigned["method"][r, c] != UNASSIGNED else UNASSIGNED)
            meth.append(str(assigned["method"][r, c]))
            rows.append(r)
            cols.append(c)
    return {"cell_id": ids, "fire_region": regs, "method": meth, "row": rows, "col": cols}


def fire_region_for_cell(grid: np.ndarray, lat_min: float, lat_max: float, lon_min: float, lon_max: float) -> tuple[str, str]:
    """Region and method for one cell given by its bounds (any size, multiple of 0.25 degrees)."""
    res_lat, res_lon = lat_max - lat_min, lon_max - lon_min
    if abs(res_lat - res_lon) > 1e-9:
        raise ValueError("cells must be square in degrees")
    a = assign_grid(grid, res_lat)
    row = math.floor((lat_min + 90.0) / res_lat + 1e-9)
    col = math.floor((lon_min + 180.0) / res_lon + 1e-9)
    method = str(a["method"][row, col])
    return (UNASSIGNED if method == UNASSIGNED else CODES[int(a["region"][row, col])]), method


# ---------------------------------------------------------------------------------- commands
def build(hdf5: Path, out: Path = OUT, res: float = 0.5) -> dict:
    import pyarrow as pa
    import pyarrow.parquet as pq
    out.mkdir(parents=True, exist_ok=True)
    grid = read_basis_regions_hdf5(hdf5)
    np.save(out / GRID_NPY, grid)
    assigned = assign_grid(grid, res)
    table = cell_table(assigned)
    pq.write_table(pa.table(table), out / f"fire_region_g{round(res * 100):03d}.parquet", compression="zstd")
    method = assigned["method"]
    return {"cells": method.size, "gfed": int((method == "GFED").sum()), "nearest_land": int((method == "NEAREST_LAND").sum()),
            "unassigned": int((method == UNASSIGNED).sum()), "ties": int(assigned["tie"].sum())}


def report(out: Path = OUT, det: Path = DETECTIONS, res: float = 0.5) -> list[tuple]:
    """Detections per region and method, from the normalized detections (counted, nothing is changed)."""
    import duckdb
    pattern = (det / "sensor=*" / "year=*" / "detections.parquet").as_posix()
    table = (out / f"fire_region_g{round(res * 100):03d}.parquet").as_posix()
    con = duckdb.connect()
    con.execute("SET memory_limit='4GB'")
    sql = f"""SELECT t.fire_region, t.method, count(*) AS detections
        FROM (SELECT CAST(floor((lat + 90) / {res}) AS INTEGER) AS row,
                     CAST(floor((CASE WHEN lon >= 180 THEN lon - 360 ELSE lon END + 180) / {res}) AS INTEGER) AS col
              FROM read_parquet('{pattern}', hive_partitioning=true)) d
        JOIN read_parquet('{table}') t ON t.row = d.row AND t.col = d.col
        GROUP BY ALL ORDER BY detections DESC"""
    return con.execute(sql).fetchall()


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--hdf5", type=Path, required=True)
    sub.add_parser("report")
    args = ap.parse_args()
    if args.cmd == "build":
        print(build(args.hdf5))
    else:
        for r in report():
            print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
