"""Free-polygon custom areas (T-044): the centre rule, validation, the endpoints and the cache.

SYNTHETIC data only (the fixtures of data/fixtures/v0.1.0 and the tiny products of conftest);
the real-product comparisons are skipped with a reason when the products are Git LFS pointers.
"""

import math
import random
from fractions import Fraction
from pathlib import Path
from typing import Any, ClassVar

import duckdb
import pytest
from fastapi.testclient import TestClient

from fire_api import custom, polygon, products
from fire_api.main import app
from tests.test_custom_real import REAL, URUGUAY, needs_real

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "v0.1.0"
URL = "/api/series/custom"
EXPORT = "/api/export.csv"
# conftest cells: c1 centre (100.25, 0.25), c2 (100.25, 0.75), c3 (-49.75, -9.75), c4 (10.25, 20.25)
SQUARE_C1_C2 = [[100.0, 0.0], [100.5, 0.0], [100.5, 1.0], [100.0, 1.0]]


# ----------------------------------------------------------------- independent brute force
def _f(p: tuple[float, float]) -> tuple[Fraction, Fraction]:
    return Fraction(p[0]), Fraction(p[1])


def brute_inside(point: tuple[float, float], ring: list[tuple[float, float]]) -> bool:
    """Winding number (not the code's even-odd formulation), all in exact fractions; a point
    on any side counts as inside."""
    px, py = _f(point)
    winding = 0
    n = len(ring)
    for i in range(n):
        ax, ay = _f(ring[i])
        bx, by = _f(ring[(i + 1) % n])
        cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
        if cross == 0 and min(ax, bx) <= px <= max(ax, bx) and min(ay, by) <= py <= max(ay, by):
            return True
        if ay <= py:
            if by > py and cross > 0:
                winding += 1
        elif by <= py and cross < 0:
            winding -= 1
    return winding != 0


def all_centres(cells_file: Path) -> list[tuple[str, float, float]]:
    con = duckdb.connect()
    try:
        rows = con.execute(
            "SELECT cell_id, lon_c, lat_c FROM read_parquet(?) ORDER BY cell_id",
            [str(cells_file)],
        ).fetchall()
    finally:
        con.close()
    return [(r[0], r[1], r[2]) for r in rows]


def brute_cells(centres: list[tuple[str, float, float]], ring: list[tuple[float, float]]) -> list:
    west, south, east, north = polygon.bounds(ring)  # only to skip the far cells quickly
    return [
        cid
        for cid, lon, lat in centres
        if west <= lon <= east and south <= lat <= north and brute_inside((lon, lat), ring)
    ]


def selected_by_the_code(cells_file: Path, ring: list[tuple[float, float]]) -> list[str]:
    west, south, east, north = polygon.bounds(ring)
    candidates = [
        c for c in all_centres(cells_file) if west <= c[1] <= east and south <= c[2] <= north
    ]
    return polygon.centres_inside(candidates, ring)


# ---------------------------------------------------------------------------- the rule
class TestPointInPolygon:
    SQUARE: ClassVar[list[tuple[float, float]]] = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]

    @pytest.mark.parametrize(
        "point, expected",
        [
            ((1, 1), True),
            ((3, 1), False),
            ((-0.001, 1), False),
            ((0, 0), True),  # corner
            ((2, 2), True),  # corner
            ((1, 0), True),  # bottom edge
            ((2, 1), True),  # right edge
            ((0, 1.5), True),  # left edge
            ((1, 2), True),  # top edge
            ((1, 2.0000001), False),
            ((1, -1), False),
        ],
    )
    def test_square_boundary_is_inside(self, point: tuple[float, float], expected: bool) -> None:
        assert polygon.point_in_polygon(point, self.SQUARE) is expected

    def test_a_concave_notch(self) -> None:
        # A "C" shape open to the right: the notch is outside.
        ring = [(0, 0), (4, 0), (4, 1), (1, 1), (1, 3), (4, 3), (4, 4), (0, 4)]
        ring = [(float(x), float(y)) for x, y in ring]
        assert polygon.point_in_polygon((0.5, 2), ring)
        assert not polygon.point_in_polygon((2.5, 2), ring)  # in the notch
        assert polygon.point_in_polygon((2.5, 0.5), ring)
        assert polygon.point_in_polygon((1, 2), ring)  # on the notch's edge
        assert polygon.point_in_polygon((2.5, 1), ring)  # on the notch's lower edge

    def test_a_ray_through_a_vertex_counts_once(self) -> None:
        diamond = [(0.0, 1.0), (1.0, 0.0), (2.0, 1.0), (1.0, 2.0)]
        assert polygon.point_in_polygon((1, 1), diamond)  # ray along y=1 hits two vertices
        assert not polygon.point_in_polygon((2.5, 1), diamond)
        assert not polygon.point_in_polygon((-0.5, 1), diamond)

    def test_a_point_on_a_slanted_edge_is_inside_even_with_rounding(self) -> None:
        ring = [(0.0, 0.0), (0.3, 0.1), (0.0, 0.5)]
        a, b = ring[0], ring[1]
        t = 0.5
        assert polygon.point_in_polygon((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), ring)

    def test_orientation_does_not_matter(self) -> None:
        ring = [(0.0, 0.0), (3.0, 0.0), (0.0, 3.0)]
        for p in [(1, 1), (2, 2), (1.5, 1.5), (0, 3), (-1, 1)]:
            assert polygon.point_in_polygon(p, ring) == polygon.point_in_polygon(p, ring[::-1])


def test_random_points_agree_with_the_winding_number() -> None:
    rng = random.Random(44)
    for _ in range(40):
        n = rng.randint(3, 9)
        # A star-shaped (so simple) ring around a random centre.
        cx, cy = rng.uniform(-20, 20), rng.uniform(-20, 20)
        angles = sorted(rng.uniform(0, 2 * math.pi) for _ in range(n))
        ring = [
            (round(cx + r * math.cos(a), 2), round(cy + r * math.sin(a), 2))
            for a in angles
            for r in [rng.uniform(1, 8)]
        ]
        try:
            polygon.validate_ring(ring)
        except polygon.PolygonError:
            continue
        for _ in range(60):
            p = (round(rng.uniform(-30, 30), 1), round(rng.uniform(-30, 30), 1))
            assert polygon.point_in_polygon(p, ring) == brute_inside(p, ring), (ring, p)


# ------------------------------------------------------------- cells on the SYNTHETIC fixtures
@pytest.mark.skipif(not FIXTURES.is_dir(), reason="data/fixtures/v0.1.0 not present")
class TestFixtureCells:
    CELLS = FIXTURES / "cells.parquet"

    def test_random_simple_polygons_match_the_brute_force(self) -> None:
        centres = all_centres(self.CELLS)
        rng = random.Random(7)
        compared = 0
        for _ in range(60):
            n = rng.randint(3, 8)
            cx, cy = rng.uniform(-100, 120), rng.uniform(-20, 40)
            angles = sorted(rng.uniform(0, 2 * math.pi) for _ in range(n))
            ring = [
                (
                    round(max(-180, min(180, cx + r * math.cos(a))), 2),
                    round(max(-90, min(90, cy + r * math.sin(a))), 2),
                )
                for a in angles
                for r in [rng.uniform(2, 40)]
            ]
            try:
                polygon.validate_ring(ring)
            except polygon.PolygonError:
                continue
            assert selected_by_the_code(self.CELLS, ring) == brute_cells(centres, ring)
            compared += 1
        assert compared >= 30

    def test_polygons_with_corners_on_cell_centres_match(self) -> None:
        """Vertices and edges that pass exactly through centres: the boundary rule."""
        centres = all_centres(self.CELLS)
        rng = random.Random(3)
        sample = rng.sample(centres, 12)
        for k in range(len(sample) - 2):
            ring = [(c[1], c[2]) for c in sample[k : k + 3]]
            try:
                polygon.validate_ring(ring)
            except polygon.PolygonError:
                continue
            got = selected_by_the_code(self.CELLS, ring)
            assert got == brute_cells(centres, ring)
            assert {c[0] for c in sample[k : k + 3]} <= set(got)  # its own corners are inside

    def test_a_rectangle_as_a_polygon_equals_the_bbox_result(self, monkeypatch) -> None:
        monkeypatch.setenv("PRODUCTS_DIR", str(FIXTURES))
        for west, south, east, north in [
            (-130.0, -30.0, 0.25, 45.0),
            (0.25, -30.0, 140.75, 45.0),
        ]:
            ring = [(west, south), (east, south), (east, north), (west, north)]
            expected = products.cells_with_centre_in(west, south, east, north)
            assert expected
            assert selected_by_the_code(self.CELLS, ring) == expected


# ------------------------------------------------------------------ the real products
@pytest.fixture(scope="module")
def centres() -> list[tuple[str, float, float]]:
    return all_centres(REAL / "cells.parquet") if (REAL / "cells.parquet").is_file() else []


@needs_real
class TestRealProducts:
    CELLS = REAL / "cells.parquet"

    def test_a_concave_polygon(self, centres: list) -> None:
        # A "U" over southern South America.
        ring = [(-70.0, -40.0), (-55.0, -40.0), (-55.0, -25.0), (-60.0, -25.0), (-60.0, -35.0),
                (-65.0, -35.0), (-65.0, -25.0), (-70.0, -25.0)]  # fmt: skip
        polygon.validate_ring(ring)
        got = selected_by_the_code(self.CELLS, ring)
        assert got == brute_cells(centres, ring)
        assert len(got) > 100
        notch = (-62.25, -30.25)  # in the U's gap
        assert not brute_inside(notch, ring)

    def test_a_triangle_over_uruguay(self, centres: list) -> None:
        ring = [(-58.4, -34.9), (-53.1, -33.0), (-57.0, -30.1)]
        polygon.validate_ring(ring)
        got = selected_by_the_code(self.CELLS, ring)
        assert got == brute_cells(centres, ring)
        assert 0 < len(got) < 107

    def test_a_rectangle_polygon_equals_the_bbox_result(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PRODUCTS_DIR", str(REAL))
        west, south, east, north = URUGUAY
        ring = [(west, south), (east, south), (east, north), (west, north)]
        assert selected_by_the_code(self.CELLS, ring) == products.cells_with_centre_in(
            west, south, east, north
        )
        assert len(products.cells_with_centre_in(west, south, east, north)) == 107

    def test_the_endpoint_returns_the_real_series_of_a_polygon(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PRODUCTS_DIR", str(REAL))
        ring = [[-58.4, -34.9], [-53.1, -33.0], [-57.0, -30.1]]
        expected = selected_by_the_code(self.CELLS, [(a, b) for a, b in ring])
        response = TestClient(app).post(URL, json={"polygon": ring})
        assert response.status_code == 200
        assert {r["n_cells"] for r in response.json()} == {len(expected)}


# ------------------------------------------------------------------------- validation
SQUARE = [[0, 0], [2, 0], [2, 2], [0, 2]]


class TestValidateRing:
    def test_a_valid_ring_is_returned_as_tuples(self) -> None:
        assert polygon.validate_ring(SQUARE) == [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]

    def test_exactly_100_points_are_allowed(self) -> None:
        ring = [
            [
                round(10 * math.cos(2 * math.pi * i / 100), 6),
                round(10 * math.sin(2 * math.pi * i / 100), 6),
            ]
            for i in range(100)
        ]
        assert len(polygon.validate_ring(ring)) == 100

    @pytest.mark.parametrize(
        "ring, message",
        [
            ([[0, 0], [1, 1]], polygon.NOT_ENOUGH),
            ([[0, 0], [0, 0], [1, 1]], polygon.NOT_ENOUGH),  # 2 distinct
            ([[0, 0], [1, 0], [0, 0]], polygon.NOT_ENOUGH),
            ([[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]], polygon.REPEATED),
            ([[0, 0], [2, 0], [2, 0], [2, 2]], polygon.REPEATED),
            ([[0, 0], [2, 0], [2, 181]], polygon.OUT_OF_RANGE),
            ([[0, 0], [2, 0], [2, 91]], polygon.OUT_OF_RANGE),
            ([[-180.5, 0], [2, 0], [2, 1]], polygon.OUT_OF_RANGE),
            ([[0, 0], [2, 0], [float("nan"), 1]], polygon.NOT_FINITE),
            ([[0, 0], [2, 0], [float("inf"), 1]], polygon.NOT_FINITE),
            ([[0, 0], [2, 0], [1, float("-inf")]], polygon.NOT_FINITE),
            ([[0, 0], [2, 0], [1]], polygon.NOT_FINITE),
            ([[0, 0], [1, 1], [2, 2]], polygon.NO_AREA),
            ([[0, 0], [1, 0], [2, 0]], polygon.NO_AREA),
            ([[170, 0], [-170, 0], [-170, 10], [170, 10]], polygon.ANTIMERIDIAN),
            ([[179, 0], [-179, 5], [179, 10]], polygon.ANTIMERIDIAN),
            ([[0, 0], [2, 2], [2, 0], [0, 2]], polygon.SELF_INTERSECTING),  # bow tie
            ([[0, 0], [4, 0], [4, 4], [2, -1], [0, 4]], polygon.SELF_INTERSECTING),
            ([[0, 0], [4, 0], [4, 2], [2, 0], [2, 2], [0, 2]], polygon.SELF_INTERSECTING),  # touch
            ([[0, 0], [4, 0], [2, 0], [2, 3]], polygon.SELF_INTERSECTING),  # folds back on itself
            ([[0, 0], [2, 0], [4, 0], [4, 3], [0, 3], [1, 0]], polygon.SELF_INTERSECTING),
        ],
    )
    def test_rejections(self, ring: list[list[float]], message: str) -> None:
        with pytest.raises(polygon.PolygonError) as info:
            polygon.validate_ring(ring)
        assert str(info.value) == message

    def test_more_than_100_points(self) -> None:
        ring = [[i / 100, (i % 2) / 100] for i in range(101)]
        with pytest.raises(polygon.PolygonError, match="at most 100"):
            polygon.validate_ring(ring)

    def test_a_concave_ring_is_valid(self) -> None:
        polygon.validate_ring([[0, 0], [4, 0], [4, 4], [2, 1], [0, 4]])

    def test_a_ring_touching_the_world_box_is_valid(self) -> None:
        polygon.validate_ring([[-90, -90], [90, -90], [0, 90]])


# --------------------------------------------------------------------------- endpoints
class Fake:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, cell_ids: list[str], months: Any = None) -> list[dict[str, Any]]:
        from tests.test_custom_cache import _record

        self.calls.append(list(cell_ids))
        return [_record(1, len(cell_ids))]


@pytest.fixture
def fake(client: TestClient, products_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Fake:
    for name in custom.PRODUCT_FILES:
        if not (products_dir / name).exists():
            (products_dir / name).write_bytes(b"x" * 10)
    f = Fake()
    monkeypatch.setattr(custom, "load_harmonize_area", lambda: f)
    return f


class TestEndpoints:
    def test_a_polygon_selects_the_cells_with_their_centre_inside(
        self, client: TestClient, fake: Fake
    ) -> None:
        r = client.post(URL, json={"polygon": SQUARE_C1_C2})
        assert r.status_code == 200
        assert fake.calls == [["c1", "c2"]]
        assert r.json()[0]["n_cells"] == 2

    def test_a_triangle_leaves_out_a_cell_whose_centre_is_outside(
        self, client: TestClient, fake: Fake
    ) -> None:
        # The triangle covers most of c2 (0.5 to 1 N) but not its centre (100.25, 0.75).
        tri = [[100.0, 0.0], [100.5, 0.0], [100.5, 0.6]]
        # centre of c1 (100.25, 0.25) is inside this triangle? y <= 0.6 * (x-100)/0.5 -> 0.3: yes
        r = client.post(URL, json={"polygon": tri})
        assert r.status_code == 200
        assert fake.calls == [["c1"]]

    def test_a_centre_on_the_boundary_is_inside(self, client: TestClient, fake: Fake) -> None:
        # The left side of this rectangle passes through c1's centre longitude (100.25).
        ring = [[100.25, 0.0], [101.0, 0.0], [101.0, 0.25], [100.25, 0.25]]
        assert client.post(URL, json={"polygon": ring}).status_code == 200
        assert fake.calls == [["c1"]]  # c1's centre is exactly the corner (100.25, 0.25)

    def test_a_tiny_polygon_with_no_centre_gives_422(self, client: TestClient, fake: Fake) -> None:
        ring = [[100.3, 0.3], [100.4, 0.3], [100.4, 0.4]]
        r = client.post(URL, json={"polygon": ring})
        assert r.status_code == 422
        assert r.json()["detail"] == "No analysis cells have their centre inside this area."
        assert fake.calls == []

    def test_a_bbox_still_works(self, client: TestClient, fake: Fake) -> None:
        assert client.post(URL, json={"bbox": [99, 0, 101, 1]}).status_code == 200
        assert fake.calls == [["c1", "c2"]]

    @pytest.mark.parametrize(
        "body, text",
        [
            ({"bbox": [99, 0, 101, 1], "polygon": SQUARE}, "not both"),
            ({}, "not both"),
            ({"polygon": SQUARE[:2]}, polygon.NOT_ENOUGH),
            ({"polygon": [[0, 0], [1, 1], [2, 2]]}, polygon.NO_AREA),
            ({"polygon": [[0, i / 1000] for i in range(101)]}, "at most 100"),
            ({"polygon": [[0, 0], [1, 0], [1, 95]]}, polygon.OUT_OF_RANGE),
            ({"polygon": [[0, 0], [1, 0], [200, 1]]}, polygon.OUT_OF_RANGE),
            ({"polygon": [[0, 0], [1, 0], [0, 1], [0, 0]]}, polygon.REPEATED),
            ({"polygon": [[0, 0], [2, 2], [2, 0], [0, 2]]}, polygon.SELF_INTERSECTING),
            ({"polygon": [[170, 0], [-170, 0], [-170, 10], [170, 10]]}, polygon.ANTIMERIDIAN),
        ],
    )
    def test_422_with_a_clear_message(
        self, client: TestClient, fake: Fake, body: dict[str, Any], text: str
    ) -> None:
        for path in (URL, EXPORT):
            r = client.post(path, json=body)
            assert r.status_code == 422, path
            assert text in r.json()["detail"], path
        assert fake.calls == []

    def test_nan_and_infinity_in_the_json_give_422(self, client: TestClient, fake: Fake) -> None:
        for token in ("NaN", "Infinity", "-Infinity"):
            raw = f'{{"polygon": [[0, 0], [2, 0], [{token}, 1]]}}'
            r = client.post(URL, content=raw, headers={"content-type": "application/json"})
            assert r.status_code == 422
            assert r.json()["detail"] == polygon.NOT_FINITE

    @pytest.mark.parametrize(
        "polygon_value", ["nope", [[0, 0, 0], [1, 1, 1], [2, 2, 2]], [["a", 1]]]
    )
    def test_a_malformed_polygon_gives_422(self, client: TestClient, polygon_value: Any) -> None:
        assert client.post(URL, json={"polygon": polygon_value}).status_code == 422

    def test_the_openapi_describes_both_shapes(self, client: TestClient) -> None:
        schema = client.get("/openapi.json").json()["components"]["schemas"]["CustomAreaRequest"]
        assert set(schema["properties"]) == {"bbox", "polygon"}
        assert "required" not in schema


class TestExportPost:
    def test_polygon_csv_header_and_file_name(self, client: TestClient, fake: Fake) -> None:
        r = client.post(EXPORT, json={"polygon": SQUARE_C1_C2})
        assert r.status_code == 200
        text = r.content.decode("utf-8-sig")
        assert "# area: CUSTOM polygon (4 points)" in text
        assert "# data_status: SYNTHETIC" in text
        disposition = r.headers["content-disposition"]
        name = disposition.split('filename="')[1].rstrip('"')
        assert name.startswith("SYNTHETIC_fire-harmonization_CUSTOM_polygon-4pts-")
        assert name.endswith(".csv")
        assert all(c.isalnum() or c in "._-" for c in name)

    def test_the_same_polygon_gives_the_same_file_name(
        self, client: TestClient, fake: Fake
    ) -> None:
        names = {
            client.post(EXPORT, json={"polygon": SQUARE_C1_C2}).headers["content-disposition"]
            for _ in range(2)
        }
        assert len(names) == 1

    def test_post_accepts_a_bbox_too(self, client: TestClient, fake: Fake) -> None:
        r = client.post(EXPORT, json={"bbox": [99, 0, 101, 1]})
        assert r.status_code == 200
        assert "# area: CUSTOM bbox 99,0,101,1" in r.content.decode("utf-8-sig")

    def test_the_get_export_is_unchanged(self, client: TestClient, fake: Fake) -> None:
        r = client.get(EXPORT, params={"bbox": "99,0,101,1"})
        assert r.status_code == 200
        assert "CUSTOM_99-0-101-1" in r.headers["content-disposition"]

    def test_503_when_the_science_is_unavailable(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def unavailable() -> Any:
            raise custom.HarmonizeUnavailable("Custom areas are not available right now: test.")

        monkeypatch.setattr(custom, "load_harmonize_area", unavailable)
        assert client.post(EXPORT, json={"polygon": SQUARE_C1_C2}).status_code == 503


class TestCacheSharing:
    def test_two_polygons_with_the_same_cells_share_one_computation(
        self, client: TestClient, fake: Fake
    ) -> None:
        a = client.post(URL, json={"polygon": SQUARE_C1_C2})
        b = client.post(
            URL, json={"polygon": [[99.9, -0.1], [101.0, -0.1], [101.0, 1.1], [99.9, 1.1]]}
        )
        c = client.post(URL, json={"bbox": [99, 0, 101, 1]})
        d = client.post(EXPORT, json={"polygon": [[100.1, 0.1], [100.4, 0.1], [100.25, 0.9]]})
        assert a.status_code == b.status_code == c.status_code == d.status_code == 200
        assert a.json() == b.json() == c.json()
        assert len(fake.calls) == 1

    def test_a_polygon_with_other_cells_recomputes(self, client: TestClient, fake: Fake) -> None:
        client.post(URL, json={"polygon": SQUARE_C1_C2})
        client.post(URL, json={"polygon": [[100.0, 0.0], [100.5, 0.0], [100.5, 0.5], [100.0, 0.5]]})
        assert fake.calls == [["c1", "c2"], ["c1"]]
