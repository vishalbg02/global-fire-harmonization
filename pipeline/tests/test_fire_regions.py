"""Tests for the fire-region mask (T-004).

    python -m pytest pipeline/tests/test_fire_regions.py -q
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import fire_regions as fr

REAL = (fr.OUT / fr.GRID_NPY).exists()


def blank() -> np.ndarray:
    return np.zeros((fr.NROW, fr.NCOL), dtype=np.uint8)


def sub_row(lat: float) -> int:
    return int((90.0 - lat) // 0.25)


def sub_col(lon: float) -> int:
    return int((lon + 180.0) // 0.25)


def paint(g, lat0, lat1, lon0, lon1, cls):
    """Set the 0.25 degree cells between the bounds (south, north, west, east) to a class."""
    g[sub_row(lat1 - 0.01): sub_row(lat0 + 0.01) + 1, sub_col(lon0 + 0.01): sub_col(lon1 - 0.01) + 1] = cls


# ------------------------------------------------------------------------------- lookup
def test_region_at_edges_and_date_line():
    g = blank()
    g[0, 0] = 3          # lat 89.875, lon -179.875
    g[-1, -1] = 9        # lat -89.875, lon 179.875
    assert fr.region_at(g, 89.9, -179.9) == 3
    assert fr.region_at(g, 90.0, -180.0) == 3         # the top row includes lat 90; the -180 column is the first
    assert fr.region_at(g, -90.0, 179.9) == 9         # the south pole row is the last row
    assert fr.region_at(g, -89.9, 180.0) == 0         # longitude 180 counts as -180 (column 0), which is ocean here
    assert fr.region_at(g, 89.9, 180.0) == 3          # ... and lands on the -180 column
    r, c = fr.subcell_index([0.0, 10.0, 10.1, 0.25], [0.0, -180.0, -179.9, 0.25])
    assert (r.tolist(), c.tolist()) == ([359, 319, 319, 358], [720, 0, 0, 721])   # a point on a cell's southern edge is inside it


def test_region_at_is_vectorized():
    g = blank()
    g[sub_row(10.1), sub_col(20.1)] = 8
    out = fr.region_at(g, np.array([10.1, 10.1, -10.0]), np.array([20.1, 21.0, 20.1]))
    assert out.tolist() == [8, 0, 0]


# ------------------------------------------------------------------------ cell assignment
def test_cell_takes_the_most_common_land_region():
    g = blank()
    paint(g, 10.0, 10.5, 20.0, 20.5, 8)                 # one 0.5 degree cell, all four sub-cells class 8
    g[sub_row(10.4), sub_col(20.1)] = 9                 # one sub-cell is class 9
    a = fr.assign_grid(g, 0.5)
    row, col = int((10.0 + 90) / 0.5), int((20.0 + 180) / 0.5)
    assert a["region"][row, col] == 8 and a["method"][row, col] == "GFED" and not a["tie"][row, col]


def test_tie_takes_the_lowest_region_and_is_counted():
    g = blank()
    paint(g, 10.0, 10.5, 20.0, 20.5, 9)
    g[sub_row(10.4), sub_col(20.1)] = 5
    g[sub_row(10.4), sub_col(20.4)] = 5
    a = fr.assign_grid(g, 0.5)
    row, col = int((10.0 + 90) / 0.5), int((20.0 + 180) / 0.5)
    assert a["region"][row, col] == 5 and a["tie"][row, col]
    assert a["tie"].sum() == 1


def test_ocean_sub_cells_do_not_outvote_land():
    g = blank()
    g[sub_row(10.1), sub_col(20.1)] = 13                # a single land sub-cell among three ocean ones
    a = fr.assign_grid(g, 0.5)
    row, col = int((10.0 + 90) / 0.5), int((20.0 + 180) / 0.5)
    assert a["region"][row, col] == 13 and a["method"][row, col] == "GFED"


def test_nearest_land_within_the_radius_and_unassigned_beyond():
    g = blank()
    paint(g, 10.0, 10.5, 20.0, 20.5, 8)
    a = fr.assign_grid(g, 0.5)
    near = (int((10.0 + 90) / 0.5), int((20.5 + 180) / 0.5))           # the cell east of the land: ocean, 0 degrees away
    far = (int((10.0 + 90) / 0.5), int((22.0 + 180) / 0.5))            # about 1.5 degrees away
    assert a["method"][near] == "NEAREST_LAND" and a["region"][near] == 8
    assert a["method"][far] == "UNASSIGNED"
    border = (int((10.0 + 90) / 0.5), int((21.0 + 180) / 0.5))         # 0.5 degrees from the land edge, still inside the radius
    assert a["method"][border] == "NEAREST_LAND"


def test_nearest_land_prefers_the_closer_region():
    g = blank()
    g[sub_row(10.1), sub_col(20.1)] = 7                 # land to the west
    g[sub_row(10.1), sub_col(21.6)] = 12                # land to the east, farther away
    filled = fr.nearest_land_fill(g, 4)
    assert filled[sub_row(10.1), sub_col(20.6)] == 7 and filled[sub_row(10.1), sub_col(21.1)] == 12
    assert filled[sub_row(10.1), sub_col(20.1)] == 7    # land keeps its own class


def test_fill_wraps_around_the_date_line():
    g = blank()
    g[sub_row(10.1), 0] = 11                            # land at lon -179.875
    filled = fr.nearest_land_fill(g, 4)
    assert filled[sub_row(10.1), fr.NCOL - 1] == 11     # the cell at lon +179.875 is its neighbour across the date line


def test_every_cell_gets_a_value_and_method():
    g = blank()
    paint(g, -10.0, 10.0, 0.0, 30.0, 8)
    a = fr.assign_grid(g, 0.5)
    t = fr.cell_table(a)
    assert len(t["cell_id"]) == 360 * 720 and len(set(t["cell_id"])) == 360 * 720
    assert all(t["fire_region"]) and set(t["method"]) <= {"GFED", "NEAREST_LAND", "UNASSIGNED"}
    assert set(t["fire_region"]) == {"NHAF", "UNASSIGNED"}
    assert all((m == "UNASSIGNED") == (r == "UNASSIGNED") for r, m in zip(t["fire_region"], t["method"], strict=True))


def test_cell_id_format():
    assert fr.cell_id(0.5, 123, 456) == "g050_r0123_c0456"
    assert fr.cell_id(0.25, 5, 7) == "g025_r0005_c0007"


def test_other_grid_sizes_and_bad_ones():
    g = blank()
    paint(g, 0.0, 1.0, 0.0, 1.0, 13)
    a = fr.assign_grid(g, 1.0)
    assert a["region"].shape == (180, 360) and a["region"][90, 180] == 13
    a25 = fr.assign_grid(g, 0.25)
    assert a25["region"].shape == (720, 1440)
    with pytest.raises(ValueError):
        fr.assign_grid(g, 0.3)


def test_fire_region_for_cell_from_bounds():
    g = blank()
    paint(g, 10.0, 10.5, 20.0, 20.5, 8)
    assert fr.fire_region_for_cell(g, 10.0, 10.5, 20.0, 20.5) == ("NHAF", "GFED")
    assert fr.fire_region_for_cell(g, 50.0, 50.5, 20.0, 20.5) == ("UNASSIGNED", "UNASSIGNED")
    with pytest.raises(ValueError):
        fr.fire_region_for_cell(g, 10.0, 10.5, 20.0, 21.0)


def test_region_codes_are_the_fourteen_gfed_regions():
    assert [fr.CODES[k] for k in range(1, 15)] == ["BONA", "TENA", "CEAM", "NHSA", "SHSA", "EURO", "MIDE", "NHAF",
                                                    "SHAF", "BOAS", "CEAS", "SEAS", "EQAS", "AUST"]
    assert len(fr.REGION_NAMES) == 14


# ----------------------------------- the vectorized result equals a plain per-cell reference
def naive_cell(g, R, C):
    """Per-cell reference: land sub-cells vote; with none, ocean sub-cells vote with their nearest land within 1 degree."""
    south = g[::-1]
    sub = [(2 * R + i, 2 * C + j) for i in range(2) for j in range(2)]
    land = [int(south[r, c]) for r, c in sub if south[r, c] > 0]
    if land:
        counts = {k: land.count(k) for k in set(land)}
        best = max(counts.values())
        return min(k for k, v in counts.items() if v == best), "GFED"
    votes = []
    for r, c in sub:
        lat = -90.0 + 0.25 * (r + 0.5)
        best = (math.inf, 99)
        for dr in range(-4, 5):
            for dc in range(-4, 5):
                rr, cc = r + dr, (c + dc) % fr.NCOL
                if not (0 <= rr < fr.NROW) or south[rr, cc] == 0:
                    continue
                d = math.hypot(dr, dc * math.cos(math.radians(lat))) * 0.25
                if d <= 1.0 + 1e-9 and (d, int(south[rr, cc])) < best:
                    best = (d, int(south[rr, cc]))
        if best[1] != 99:
            votes.append(best[1])
    if not votes:
        return 0, "UNASSIGNED"
    counts = {k: votes.count(k) for k in set(votes)}
    top = max(counts.values())
    return min(k for k, v in counts.items() if v == top), "NEAREST_LAND"


def test_vectorized_assignment_matches_the_reference():
    rng = np.random.default_rng(7)
    g = blank()
    for _ in range(300):                                 # random patches of land, with gaps and date line crossings
        r, c = int(rng.integers(0, fr.NROW)), int(rng.integers(0, fr.NCOL))
        h, w = int(rng.integers(1, 6)), int(rng.integers(1, 6))
        cls = int(rng.integers(1, 15))
        rows = np.arange(r, min(r + h, fr.NROW))
        cols = (np.arange(c, c + w)) % fr.NCOL
        g[np.ix_(rows, cols)] = cls
    a = fr.assign_grid(g, 0.5)
    land_cells = np.argwhere(a["method"] != "UNASSIGNED")
    sample = [tuple(x) for x in land_cells[rng.choice(len(land_cells), 150, replace=False)]]
    sample += [(int(rng.integers(0, 360)), int(rng.integers(0, 720))) for _ in range(150)]
    for R, C in sample:
        want_region, want_method = naive_cell(g, R, C)
        assert (int(a["region"][R, C]), str(a["method"][R, C])) == (want_region, want_method), (R, C)


# --------------------------------------------------------------------------- real GFED grid
@pytest.mark.skipif(not REAL, reason="GFED grid not on this machine")
def test_real_grid_has_the_fourteen_regions():
    g = fr.load_grid()
    assert g.shape == (720, 1440) and g.dtype == np.uint8
    assert set(np.unique(g)) == set(range(15))


@pytest.mark.skipif(not REAL, reason="GFED grid not on this machine")
@pytest.mark.parametrize("lat, lon, code", [
    (0.5, 114.0, "EQAS"), (22.0, 10.0, "NHAF"), (-5.0, -60.0, "SHSA"), (48.0, 2.0, "EURO"), (-25.0, 135.0, "AUST"),
    (60.0, 100.0, "BOAS"), (60.0, -110.0, "BONA"), (40.0, -100.0, "TENA"), (19.4, -99.1, "CEAM"), (22.0, 80.0, "SEAS"),
    (48.0, 68.0, "CEAS"), (25.0, 45.0, "MIDE"), (-5.0, 25.0, "SHAF"), (5.0, -72.0, "NHSA"),
])
def test_real_grid_known_places(lat, lon, code):
    assert fr.CODES[int(fr.region_at(fr.load_grid(), lat, lon))] == code


@pytest.mark.skipif(not REAL, reason="GFED grid not on this machine")
def test_real_grid_every_cell_assigned_and_unassigned_is_ocean_like():
    a = fr.assign_grid(fr.load_grid(), 0.5)
    assert a["region"].shape == (360, 720)
    assert set(a["method"].ravel()) == {"GFED", "NEAREST_LAND", "UNASSIGNED"}
    assert (a["method"] == "GFED").sum() > 60_000
    assert a["tie"].sum() < 50                         # ties are rare; they are counted, not hidden
    assert fr.fire_region_for_cell(fr.load_grid(), 20.0, 20.5, -156.5, -156.0)[1] == "UNASSIGNED"   # open ocean near Hawaii
