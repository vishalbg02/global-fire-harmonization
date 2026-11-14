"""FastAPI application: read-only endpoints over the contract products (T-034).

Responses are bare payloads and errors use FastAPI's default body (`{"detail": ...}`);
the D-022 envelope and error format are not approved. Status codes: 400 invalid parameters,
404 unknown entity, 422 invalid custom area, 503 products or the harmonization function
unavailable.
"""

import math
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from starlette.middleware.gzip import GZipMiddleware

from . import custom, export, products
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
    # Invalid parameters are 400; an invalid custom-area body is 422.
    status = 422 if request.url.path == CUSTOM_AREA_PATH else 400
    return JSONResponse(status_code=status, content={"detail": jsonable_encoder(exc.errors())})


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


@app.get("/api/map", response_model=list[MapCell])
def get_map(year: Year, month: MonthParam, layer: MapLayer) -> list[MapCell]:
    # `layer` is validated, but every layer returns the same fields (the app colours them).
    return products.map_cells(year, month)


@app.get("/api/series", response_model=list[EntityMonth])
def get_series(
    entity_type: Literal["COUNTRY", "CONTINENT", "GLOBAL"], entity_id: str
) -> list[EntityMonth]:
    return products.series(EntityType(entity_type), entity_id)


def _custom_series(bbox: tuple[float, float, float, float]) -> list[EntityMonth]:
    west, south, east, north = bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise HTTPException(
            422, "bbox must be [W, S, E, N] with -180 <= W < E <= 180 and -90 <= S < N <= 90."
        )
    cell_ids = products.cells_with_centre_in(west, south, east, north)
    if not cell_ids:
        raise HTTPException(422, "No analysis cells have their centre inside this area.")
    try:
        # Validated, unaltered records of the single implementation of the science (cached).
        return custom.custom_series(cell_ids)
    except HarmonizeUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post(CUSTOM_AREA_PATH, response_model=list[EntityMonth])
def post_custom_series(body: CustomAreaRequest) -> list[EntityMonth]:
    return _custom_series(body.bbox)


@app.get("/api/export.csv")
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
    return Response(
        content=export.build_csv(records, meta, subject),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


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
