"""Free-polygon custom areas (T-044): validation and the point-in-polygon rule.

A grid cell belongs to a polygon when its **centre** lies inside the polygon, boundary
included (the rectangle's rule). Inside is the even-odd (ray-casting) rule; the rings that
reach it are simple (no self-intersection), so it is the same as the winding-number rule.

Plain Python, no geometry library. Arithmetic is in floats with an exact (`Fraction`) fallback
whenever a result is too close to zero to trust, so a centre exactly on an edge or a corner is
reliably counted as inside.
"""

import hashlib
import math
from collections.abc import Sequence
from fractions import Fraction

MAX_POINTS = 100
Point = tuple[float, float]

NOT_ENOUGH = "A polygon needs at least 3 different corner points."
TOO_MANY = f"A polygon can have at most {MAX_POINTS} corner points."
NOT_FINITE = "Every corner point must be a pair of finite numbers: longitude, latitude."
OUT_OF_RANGE = "Every corner point must have -180 <= longitude <= 180 and -90 <= latitude <= 90."
REPEATED = (
    "Corner points must all be different: do not repeat the first point at the end "
    "(the polygon is closed automatically)."
)
ANTIMERIDIAN = (
    "Polygons that cross the antimeridian (longitude 180) are not supported: no side may span "
    "more than 180 degrees of longitude."
)
NO_AREA = (
    "The polygon has no area: its corner points lie on one line, or its bounding box needs "
    "west < east and south < north."
)
SELF_INTERSECTING = (
    "The polygon crosses or touches itself (or two of its sides overlap). "
    "Use a simple outline whose sides only meet at their corners."
)


class PolygonError(ValueError):
    """The ring is not a usable polygon; the message is meant for the person who drew it."""


def _frac(value: float) -> Fraction:
    return Fraction(value)


def _orient_exact(a: Point, b: Point, p: Point) -> int:
    """Sign of the cross product (b - a) x (p - a), computed exactly."""
    ax, ay, bx, by, px, py = (_frac(v) for v in (*a, *b, *p))
    cross = (bx - ax) * (py - ay) - (by - ay) * (px - ax)
    return (cross > 0) - (cross < 0)


def _orient(a: Point, b: Point, p: Point) -> int:
    """Sign of the cross product, in floats unless the value is within rounding error of 0."""
    cross = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    if abs(cross) > 1e-9:
        return (cross > 0) - (cross < 0)
    return _orient_exact(a, b, p)


def _on_segment(a: Point, b: Point, p: Point) -> bool:
    """p is inside the bounding box of segment a-b (p already known collinear)."""
    return min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])


def _segments_meet(a: Point, b: Point, c: Point, d: Point) -> bool:
    """The closed segments a-b and c-d share at least one point."""
    o1, o2 = _orient_exact(a, b, c), _orient_exact(a, b, d)
    o3, o4 = _orient_exact(c, d, a), _orient_exact(c, d, b)
    if o1 != o2 and o3 != o4:
        return True
    return (
        (o1 == 0 and _on_segment(a, b, c))
        or (o2 == 0 and _on_segment(a, b, d))
        or (o3 == 0 and _on_segment(c, d, a))
        or (o4 == 0 and _on_segment(c, d, b))
    )


def _folds_back(a: Point, b: Point, c: Point) -> bool:
    """Sides a-b and b-c (sharing b) lie on one line and run over each other."""
    if _orient_exact(a, b, c) != 0:
        return False
    ba = (_frac(a[0]) - _frac(b[0]), _frac(a[1]) - _frac(b[1]))
    bc = (_frac(c[0]) - _frac(b[0]), _frac(c[1]) - _frac(b[1]))
    return ba[0] * bc[0] + ba[1] * bc[1] > 0


def validate_ring(points: Sequence[Sequence[float]]) -> list[Point]:
    """The ring as a list of (lon, lat) tuples, or a `PolygonError` with the reason.

    One outer ring, 3 to 100 different points, finite, inside the world box, first point not
    repeated at the end, no side spanning more than 180 degrees of longitude (no antimeridian
    crossing; the bounding box needs west < east), non-zero area, and no two sides meeting
    except consecutive ones at their shared corner.
    """
    if len(points) > MAX_POINTS:
        raise PolygonError(f"{TOO_MANY} This one has {len(points)}.")
    ring: list[Point] = []
    for p in points:
        if len(p) != 2 or not all(isinstance(v, int | float) and math.isfinite(v) for v in p):
            raise PolygonError(NOT_FINITE)
        ring.append((float(p[0]), float(p[1])))
    if any(not (-180 <= lon <= 180 and -90 <= lat <= 90) for lon, lat in ring):
        raise PolygonError(OUT_OF_RANGE)
    if len(set(ring)) < 3:
        raise PolygonError(NOT_ENOUGH)
    if len(set(ring)) != len(ring):
        raise PolygonError(REPEATED)
    n = len(ring)
    sides = [(ring[i], ring[(i + 1) % n]) for i in range(n)]
    if any(abs(a[0] - b[0]) > 180 for a, b in sides):
        raise PolygonError(ANTIMERIDIAN)
    west, south, east, north = bounds(ring)
    if not (west < east and south < north) or all(
        _orient_exact(ring[0], ring[1], p) == 0 for p in ring[2:]
    ):
        raise PolygonError(NO_AREA)
    for i in range(n):
        if _folds_back(ring[i - 1], ring[i], ring[(i + 1) % n]):
            raise PolygonError(SELF_INTERSECTING)
        for j in range(i + 2, n):
            if i == 0 and j == n - 1:
                continue  # the closing side is adjacent to the first
            if _segments_meet(*sides[i], *sides[j]):
                raise PolygonError(SELF_INTERSECTING)
    return ring


def bounds(ring: Sequence[Point]) -> tuple[float, float, float, float]:
    """(west, south, east, north) of the ring."""
    lons = [p[0] for p in ring]
    lats = [p[1] for p in ring]
    return min(lons), min(lats), max(lons), max(lats)


def point_in_polygon(point: Point, ring: Sequence[Point]) -> bool:
    """Even-odd ray casting; a point on an edge or a corner is inside."""
    py = point[1]
    inside = False
    n = len(ring)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        side = _orient(a, b, point)
        if side == 0 and _on_segment(a, b, point):
            return True
        if (a[1] > py) != (b[1] > py) and side != 0 and (side > 0) == (b[1] > a[1]):
            # The side crosses the horizontal line through the point, to the point's right.
            inside = not inside
    return inside


def centres_inside(
    candidates: Sequence[tuple[str, float, float]], ring: Sequence[Point]
) -> list[str]:
    """IDs, in the order given, of the (id, lon, lat) centres inside the ring."""
    return [cid for cid, lon, lat in candidates if point_in_polygon((lon, lat), ring)]


def digest(ring: Sequence[Point]) -> str:
    """A short stable name of a ring, for file names."""
    text = ";".join(f"{lon!r},{lat!r}" for lon, lat in ring)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
