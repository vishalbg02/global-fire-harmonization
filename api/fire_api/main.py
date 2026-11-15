"""FastAPI application: read-only endpoints over the contract products (T-034).

Responses are bare payloads and errors use FastAPI's default body (`{"detail": ...}`);
the D-022 envelope and error format are not approved. Status codes: 400 invalid parameters,
404 unknown entity, 422 invalid custom area, 503 products or the harmonization function
unavailable.
"""

import math
from collections.abc import Callable
from typing import Annotated, Any, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from starlette.middleware.gzip import GZipMiddleware

from . import custom, export, map_cache, map_columns, polygon, products
from .custom import HarmonizeUnavailable
from .models import (
    Anomaly,
    CustomAreaRequest,
    EntityEvidence,
    EntityItem,
    EntityMonth,
    EntityType,
    MapCell,
    MapLayer,
    Metadata,
    ValidationResults,
)

CUSTOM_AREA_PATH = "/api/series/custom"
EXPORT_PATH = "/api/export.csv"

app = FastAPI(title="Global Fire Harmonization API", version="0.1.0")
# Compresses responses of 1000 bytes or more when the client sends Accept-Encoding: gzip.
# Level 6: about 0.13 s for the 29 MB map month against 0.32 s at starlette's default 9, for
# 9% more bytes.
app.add_middleware(GZipMiddleware, minimum_size=1000, compresslevel=6)

Year = Annotated[int, Query(ge=1, le=9999)]
MonthParam = Annotated[int, Query(ge=1, le=12)]


def _detail(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": message})


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
    # Invalid parameters are 400; an invalid custom-area body (POST) is 422.
    is_body = request.url.path == CUSTOM_AREA_PATH or (
        request.url.path == EXPORT_PATH and request.method == "POST"
    )
    if is_body:
        # A rule of the request shape (e.g. both bbox and polygon) comes with its own sentence.
        errors = exc.errors()
        for error in errors:
            if error.get("type") == "value_error" and error.get("msg", "").startswith(
                "Value error, "
            ):
                return _detail(422, error["msg"].removeprefix("Value error, "))
        return JSONResponse(status_code=422, content={"detail": jsonable_encoder(errors)})
    return JSONResponse(status_code=400, content={"detail": jsonable_encoder(exc.errors())})


@app.exception_handler(products.ProductsUnavailable)
async def products_unavailable(request: Request, exc: products.ProductsUnavailable) -> JSONResponse:
    return _detail(503, f"Data are not available right now. {exc}")


@app.exception_handler(ValidationError)
async def contract_violation(request: Request, exc: ValidationError) -> JSONResponse:
    # A stored product that does not match the contract is reported, never coerced.
    count = exc.error_count()
    return _detail(503, f"A product does not match the data contract: {count} error(s).")


@app.exception_handler(products.NotFound)
async def not_found(request: Request, exc: products.NotFound) -> JSONResponse:
    return _detail(404, str(exc))


@app.get("/api/meta", response_model=Metadata)
def get_meta() -> Metadata:
    return products.metadata()


@app.get("/api/entities", response_model=list[EntityItem])
def get_entities(type: Annotated[Literal["COUNTRY", "CONTINENT"], Query()]) -> list[EntityItem]:
    return products.entities(EntityType(type))


MAP_CACHE_CONTROL = "public, max-age=300"


def _accepts_gzip(header: str) -> bool:
    for part in header.split(","):
        coding, _, params = part.partition(";")
        if coding.strip().lower() in ("gzip", "x-gzip", "*"):
            return params.replace(" ", "").lower() not in ("q=0", "q=0.0", "q=0.00", "q=0.000")
    return False


def _cached_response(request: Request, etag: str | None, payload: Callable[[], Any]) -> Response:
    """A cached, pre-compressed JSON answer with its validator: 304 when the client has it, gzip
    when the client accepts it. `payload` is only called when the bytes are needed."""
    headers = {"Cache-Control": MAP_CACHE_CONTROL, "Vary": "Accept-Encoding"}
    if etag is not None:
        headers["ETag"] = etag
        tags = [t.strip() for t in request.headers.get("if-none-match", "").split(",")]
        if etag in tags or "*" in tags:
            return Response(status_code=304, headers=headers)
    cached = payload()
    if cached.etag:
        headers["ETag"] = cached.etag
    if _accepts_gzip(request.headers.get("accept-encoding", "")):
        headers["Content-Encoding"] = "gzip"
        body = cached.gzipped
    else:
        body = cached.identity()
    return Response(content=body, media_type="application/json", headers=headers)


@app.get("/api/map", response_model=list[MapCell])
def get_map(request: Request, year: Year, month: MonthParam, layer: MapLayer) -> Response:
    # `layer` is validated, but every layer returns the same fields (the app colours them), so
    # all layers share one cached, pre-compressed answer per month (api/fire_api/map_cache.py).
    return _cached_response(
        request, map_cache.validator(year, month), lambda: map_cache.payload(year, month)
    )


@app.get("/api/map/cells")
def get_map_cells(request: Request) -> Response:
    """The ids and bounds of every analysis cell, once, in columns (api/README.md)."""
    return _cached_response(request, map_columns.cells_validator(), map_columns.cells_payload)


@app.get("/api/map/columns")
def get_map_columns(request: Request, year: Year, month: MonthParam, layer: MapLayer) -> Response:
    """One map month in columns, with only the fields the app reads for the layer (api/README.md);
    the values are those of GET /api/map."""
    return _cached_response(
        request,
        map_columns.columns_validator(year, month, layer),
        lambda: map_columns.columns_payload(year, month, layer),
    )


@app.get("/api/series", response_model=list[EntityMonth])
def get_series(
    entity_type: Literal["COUNTRY", "CONTINENT", "GLOBAL"], entity_id: str
) -> list[EntityMonth]:
    return products.series(EntityType(entity_type), entity_id)


NO_CENTRES = "No analysis cells have their centre inside this area."


def _cells_of(body: CustomAreaRequest) -> tuple[list[str], str, str]:
    """The cell IDs of the area, its CSV subject line and the identifier of its file name."""
    if body.polygon is not None:
        try:
            ring = polygon.validate_ring(body.polygon)
        except polygon.PolygonError as exc:
            raise HTTPException(422, str(exc)) from exc
        west, south, east, north = polygon.bounds(ring)
        candidates = products.cell_centres_in(west, south, east, north)
        cell_ids = polygon.centres_inside(candidates, ring)
        subject = f"CUSTOM polygon ({len(ring)} points)"
        ident = f"polygon-{len(ring)}pts-{polygon.digest(ring)}"
    else:
        assert body.bbox is not None
        west, south, east, north = body.bbox
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
            raise HTTPException(
                422, "bbox must be [W, S, E, N] with -180 <= W < E <= 180 and -90 <= S < N <= 90."
            )
        cell_ids = products.cells_with_centre_in(west, south, east, north)
        text = ",".join(f"{p:g}" for p in body.bbox)
        subject, ident = f"CUSTOM bbox {text}", text
    if not cell_ids:
        raise HTTPException(422, NO_CENTRES)
    return cell_ids, subject, ident


def _custom_series_of(cell_ids: list[str]) -> list[EntityMonth]:
    try:
        # Validated, unaltered records of the single implementation of the science (cached).
        return custom.custom_series(cell_ids)
    except HarmonizeUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


def _custom_series(bbox: tuple[float, float, float, float]) -> list[EntityMonth]:
    return _custom_series_of(_cells_of(CustomAreaRequest(bbox=bbox))[0])


@app.post(CUSTOM_AREA_PATH, response_model=list[EntityMonth])
def post_custom_series(body: CustomAreaRequest) -> list[EntityMonth]:
    return _custom_series_of(_cells_of(body)[0])


def _csv_response(records: list[EntityMonth], subject: str, name: str, meta: Metadata) -> Response:
    return Response(
        content=export.build_csv(records, meta, subject),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@app.post(EXPORT_PATH)
def post_export_csv(body: CustomAreaRequest) -> Response:
    """The monthly series of a custom area (same body as POST /api/series/custom) as CSV."""
    cell_ids, subject, ident = _cells_of(body)
    meta = products.metadata()
    records = _custom_series_of(cell_ids)
    return _csv_response(records, subject, export.filename("CUSTOM", ident, meta), meta)


@app.get(EXPORT_PATH)
def get_export_csv(
    entity_type: Annotated[Literal["COUNTRY", "CONTINENT", "GLOBAL"] | None, Query()] = None,
    entity_id: str | None = None,
    bbox: str | None = None,
) -> Response:
    """The monthly series of one preset area (`entity_type` + `entity_id`) or of a custom
    rectangle (`bbox=W,S,E,N`) as CSV. Exactly one of the two must be given."""
    preset = entity_type is not None or entity_id is not None
    if preset == (bbox is not None):
        raise HTTPException(400, "Give either entity_type and entity_id, or bbox, not both.")
    if preset:
        if entity_type is None or entity_id is None:
            raise HTTPException(400, "entity_type and entity_id are both required.")
        meta = products.metadata()
        records = products.series(EntityType(entity_type), entity_id)
        subject = f"{entity_type} {entity_id}"
        name = export.filename(entity_type, entity_id, meta)
    else:
        assert bbox is not None
        try:
            parts = tuple(float(p) for p in bbox.split(","))
        except ValueError:
            parts = ()
        if len(parts) != 4 or not all(map(math.isfinite, parts)):
            raise HTTPException(400, "bbox must be four numbers: W,S,E,N.")
        meta = products.metadata()
        records = _custom_series((parts[0], parts[1], parts[2], parts[3]))
        subject = f"CUSTOM bbox {bbox}"
        name = export.filename("CUSTOM", ",".join(f"{p:g}" for p in parts), meta)
    return _csv_response(records, subject, name, meta)


@app.get("/api/evidence", response_model=EntityEvidence)
def get_evidence(
    entity_type: EntityType, entity_id: str, year: Year, month: MonthParam
) -> EntityEvidence:
    return products.evidence(entity_type, entity_id, year, month)


@app.get("/api/anomalies", response_model=list[Anomaly])
def get_anomalies(
    year: Year, month: MonthParam, limit: Annotated[int, Query(ge=1, le=500)] = 20
) -> list[Anomaly]:
    return products.anomalies(year, month, limit)


@app.get("/api/validation", response_model=ValidationResults)
def get_validation() -> ValidationResults:
    return products.validation_results()
