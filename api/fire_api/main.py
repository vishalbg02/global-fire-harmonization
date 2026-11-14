"""FastAPI application: read-only endpoints over the contract products (T-034).

Responses are bare payloads and errors use FastAPI's default body (`{"detail": ...}`);
the D-022 envelope and error format are not approved. Status codes: 400 invalid parameters,
404 unknown entity, 422 invalid custom area, 503 products or the harmonization function
unavailable.
"""

from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from . import custom, products
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


@app.post(CUSTOM_AREA_PATH, response_model=list[EntityMonth])
def post_custom_series(body: CustomAreaRequest) -> list[EntityMonth]:
    west, south, east, north = body.bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise HTTPException(
            422, "bbox must be [W, S, E, N] with -180 <= W < E <= 180 and -90 <= S < N <= 90."
        )
    cell_ids = products.cells_with_centre_in(west, south, east, north)
    if not cell_ids:
        raise HTTPException(422, "No analysis cells have their centre inside this area.")
    try:
        harmonize_area = custom.load_harmonize_area()
    except HarmonizeUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    records = harmonize_area(cell_ids, months=None)
    # Records come from the single implementation of the science and are validated, not altered.
    return [EntityMonth.model_validate(dict(r)) for r in records]


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
