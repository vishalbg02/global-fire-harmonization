"""Tests for pipeline/kashmir_cells.py (T-086) on SYNTHETIC polygons, cells and entity rows with known answers.

    python -m pytest pipeline/tests/test_kashmir_cells.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pyarrow as pa
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import kashmir_cells as kc

SQUARE = np.array([[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]], dtype=float)
HOLE = np.array([[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]], dtype=float)
ISLAND = np.array([[20, 0], [22, 0], [22, 2], [20, 2], [20, 0]], dtype=float)
L_SHAPE = np.array([[30, 0], [34, 0], [34, 2], [32, 2], [32, 4], [30, 4], [30, 0]], dtype=float)   # concave


def test_point_in_polygon_with_a_hole_a_second_polygon_and_a_concave_shape():
    polys = [[SQUARE, HOLE], [ISLAND], [L_SHAPE]]
    lon = np.array([1.0, 5.0, 9.9, 10.5, 21.0, 23.0, 31.0, 33.0, 33.0, 31.0])
    lat = np.array([1.0, 5.0, 9.9, 5.0, 1.0, 1.0, 3.0, 3.0, 1.0, 1.0])
    expected = [True, False, True, False, True, False, True, False, True, True]     # (5, 5) is in the hole; (33, 3) is in the notch of the L
    assert kc.inside_polygons(lon, lat, polys).tolist() == expected


def test_a_point_far_from_every_polygon_is_outside():
    assert not kc.inside_polygons(np.array([100.0]), np.array([-50.0]), [[SQUARE]]).any()


def cells(rows):
    return {"cell_id": np.array([r[0] for r in rows], dtype=object), "lon_c": np.array([r[1] for r in rows]), "lat_c": np.array([r[2] for r in rows]),
            "country_iso3": np.array([r[3] for r in rows], dtype=object)}


def test_the_plan_changes_only_cells_in_the_box_inside_india_with_another_country():
    india = [[np.array([[73, 33], [79, 33], [79, 36], [73, 36], [73, 33]], dtype=float)]]
    box = (72.5, 80.5, 32.5, 37.2)
    rows = [("a", 74.0, 34.0, "PAK"),      # in the box, inside India, Pakistan: changed
            ("b", 78.0, 35.0, "CHN"),      # changed
            ("c", 76.0, 34.0, "IND"),      # already India: unchanged
            ("d", 80.0, 36.5, "CHN"),      # in the box but outside the India polygon: unchanged
            ("e", 75.0, 34.5, None),       # no country: reported, not given one
            ("f", 90.0, 25.0, "BGD")]      # outside the box
    p = kc.plan(cells(rows), india, box)
    assert [r["cell_id"] for r in p["changed_rows"]] == ["a", "b"]
    assert p["changed"].tolist() == [True, True, False, False, False, False]
    assert [r["cell_id"] for r in p["no_country_inside_rows"]] == ["e"]
    assert p["in_box"] == 5 and p["box_by_country_before"] == {"CHN": 2, "IND": 1, "PAK": 1, "none": 1}
    assert p["india_outside_rows"] == [] and p["outside_box_rows"] == []


def test_an_indian_cell_outside_the_india_polygon_and_a_differing_cell_outside_the_box_are_reported_not_changed():
    india = [[np.array([[73, 33], [79, 33], [79, 36], [73, 36], [73, 33]], dtype=float), ]]
    box = (72.5, 80.5, 32.5, 37.2)
    far_india = [[np.array([[60, 20], [62, 20], [62, 22], [60, 22], [60, 20]], dtype=float)]]
    rows = [("g", 77.0, 36.9, "IND"), ("h", 61.0, 21.0, "PAK"), ("i", 74.0, 34.0, "IND")]
    p = kc.plan(cells(rows), india + far_india, box)
    assert [r["cell_id"] for r in p["india_outside_rows"]] == ["g"]
    assert [r["cell_id"] for r in p["outside_box_rows"]] == ["h"]
    assert not p["changed"].any()


def cell_table():
    return pa.table({"cell_id": ["a", "b", "c"], "lat_c": [1.0, 2.0, 3.0], "continent": ["AS", "AS", "AS"], "country_iso3": ["PAK", "IND", None]})


def test_reassign_changes_only_the_planned_country_values():
    t = cell_table()
    out = kc.reassign(t, np.array([True, False, False]))
    assert out["country_iso3"].to_pylist() == ["IND", "IND", None]
    for name in ("cell_id", "lat_c", "continent"):
        assert out[name].equals(t[name])
    assert out.schema == t.schema


def entity_table(n_cells_ind: int, estimate_pak: float):
    keys = [("COUNTRY", e, 2020, m) for e in ("IDN", "IND", "PAK", "CHN") for m in (1, 2)]
    est = {"IDN": 5.0, "IND": 7.0, "PAK": estimate_pak, "CHN": 9.0}
    return pa.table({"entity_type": [k[0] for k in keys], "entity_id": [k[1] for k in keys], "year": [k[2] for k in keys], "month": [k[3] for k in keys],
                     "estimate": [est[k[1]] for k in keys], "n_cells": [n_cells_ind if k[1] == "IND" else 3 for k in keys],
                     "reason_codes": [["A"] if k[1] == "IND" else [] for k in keys]})


def test_merge_takes_only_the_three_entities_from_the_new_table_and_keeps_every_other_row():
    old, new = entity_table(10, 4.0), entity_table(12, 3.5)
    new = new.set_column(new.schema.get_field_index("estimate"), "estimate", pa.array([5.0001 if e == "IDN" else v for e, v in zip(new["entity_id"].to_pylist(), new["estimate"].to_pylist(), strict=True)]))
    merged = kc.merge_entities(old, new)
    ids = merged["entity_id"].to_pylist()
    assert ids == old["entity_id"].to_pylist()                              # the order of `old`
    est = dict(zip(ids, merged["estimate"].to_pylist(), strict=True))
    assert est["IDN"] == 5.0                                                # not a regenerated entity: the old value, not 5.0001
    assert est["PAK"] == 3.5 and est["IND"] == 7.0 and est["CHN"] == 9.0
    assert [n for e, n in zip(ids, merged["n_cells"].to_pylist(), strict=True) if e == "IND"] == [12, 12]
    assert merged.schema == old.schema


def test_merge_refuses_different_schemas_or_keys():
    old = entity_table(10, 4.0)
    with pytest.raises(ValueError):
        kc.merge_entities(old, old.drop(["n_cells"]))
    shifted = old.set_column(old.schema.get_field_index("month"), "month", pa.array([m + 1 for m in old["month"].to_pylist()]))
    with pytest.raises(ValueError):
        kc.merge_entities(old, shifted)


def test_the_difference_report_counts_rows_and_the_largest_relative_change():
    old, new = entity_table(10, 4.0), entity_table(12, 4.0)
    mask = np.array([e == "IND" for e in old["entity_id"].to_pylist()])
    d = kc.rows_differences(old, new, mask)
    assert d == {"rows": 2, "rows_differing": 2, "max_relative_difference": 0.0}          # n_cells differs, floats are equal
    new2 = new.set_column(new.schema.get_field_index("estimate"), "estimate", pa.array([v * 1.001 if e == "PAK" else v for e, v in zip(new["entity_id"].to_pylist(), new["estimate"].to_pylist(), strict=True)]))
    d2 = kc.rows_differences(old, new2, np.array([e == "PAK" for e in old["entity_id"].to_pylist()]))
    assert d2["rows_differing"] == 2 and d2["max_relative_difference"] == pytest.approx(0.001)


def test_load_polygons_selects_one_country_and_reads_holes(tmp_path):
    def poly(coords):
        return [coords]
    geo = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"ADM0_A3": "IND"}, "geometry": {"type": "MultiPolygon", "coordinates": [[SQUARE.tolist(), HOLE.tolist()], poly(ISLAND.tolist())]}},
        {"type": "Feature", "properties": {"ADM0_A3": "PAK"}, "geometry": {"type": "Polygon", "coordinates": [L_SHAPE.tolist()]}}]}
    f = tmp_path / "ind.geojson"
    f.write_text(json.dumps(geo), encoding="utf-8")
    polys = kc.load_polygons(f, "IND")
    assert len(polys) == 2 and len(polys[0]) == 2 and len(polys[1]) == 1
    assert kc.inside_polygons(np.array([1.0, 5.0, 21.0]), np.array([1.0, 5.0, 1.0]), polys).tolist() == [True, False, True]
    with pytest.raises(ValueError):
        kc.load_polygons(f, "XXX")
