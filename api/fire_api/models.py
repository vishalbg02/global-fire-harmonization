"""Pydantic models mirroring docs/DATA_CONTRACT.md (contract_version 0.1.1).

Unknown enum values, missing fields and wrong types fail validation. Nothing is coerced:
`None` stays `None` and a real zero stays 0.
"""

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Verdict(StrEnum):
    ABOVE_NORMAL = "ABOVE_NORMAL"
    BELOW_NORMAL = "BELOW_NORMAL"
    WITHIN_NORMAL = "WITHIN_NORMAL"
    CANNOT_DETERMINE = "CANNOT_DETERMINE"
    NO_DETECTED_ACTIVITY = "NO_DETECTED_ACTIVITY"


class ReasonCode(StrEnum):
    OUTAGE = "OUTAGE"
    INSUFFICIENT_BASELINE = "INSUFFICIENT_BASELINE"
    INSUFFICIENT_OVERLAP = "INSUFFICIENT_OVERLAP"
    WITNESS_DISAGREEMENT = "WITNESS_DISAGREEMENT"
    WIDE_INTERVAL = "WIDE_INTERVAL"
    PROVISIONAL_NRT = "PROVISIONAL_NRT"
    AQUA_DRIFT_ERA = "AQUA_DRIFT_ERA"
    SINGLE_WITNESS = "SINGLE_WITNESS"
    POOLED_CALIBRATION = "POOLED_CALIBRATION"
    DIURNAL_CAVEAT = "DIURNAL_CAVEAT"
    NOT_HARMONIZED = "NOT_HARMONIZED"


class Witness(StrEnum):
    AQUA_MODIS = "AQUA_MODIS"
    TERRA_MODIS = "TERRA_MODIS"
    SNPP_VIIRS = "SNPP_VIIRS"
    NOAA20_VIIRS = "NOAA20_VIIRS"
    NOAA21_VIIRS = "NOAA21_VIIRS"


class DataLevel(StrEnum):
    SP = "SP"
    NRT = "NRT"
    MIXED = "MIXED"


class EntityType(StrEnum):
    CELL = "CELL"
    COUNTRY = "COUNTRY"
    CONTINENT = "CONTINENT"
    GLOBAL = "GLOBAL"
    CUSTOM = "CUSTOM"


class TestStatus(StrEnum):
    __test__ = False  # not a pytest class

    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"
    NOT_RUN = "NOT_RUN"


class MapLayer(StrEnum):
    """Layer modes of GET /api/map. They change how the app colours cells, not the payload."""

    VERDICT = "verdict"
    RAW = "raw"
    HARMONIZED = "harmonized"


Probability = Annotated[float, Field(ge=0, le=1)]
Month = Annotated[int, Field(ge=1, le=12)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HarmonizedFields(_Strict):
    """Fields shared by cell_month_harmonized (§3) and entity_month (§4)."""

    estimate: float | None
    ci90_low: float | None
    ci90_high: float | None
    sd: float | None
    raw_combined_cell_days: int
    witnesses_used: list[Witness]
    n_witnesses: int
    disagreement_scale: Annotated[float, Field(ge=1)] | None
    baseline_median: float | None
    baseline_p25: float | None
    baseline_p75: float | None
    pct_of_normal: float | None
    p_above: Probability | None
    p_below: Probability | None
    p_within: Probability | None
    verdict: Verdict
    reason_codes: list[ReasonCode]
    data_level: DataLevel
    method_version: str


class MapCell(HarmonizedFields):
    """One analysis cell for one month: cell bounds plus its cell_month_harmonized fields."""

    cell_id: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    year: int
    month: Month


class EntityMonth(HarmonizedFields):
    """entity_month (§4); `raw_by_witness` is the JSON-encoded string map of the contract."""

    entity_type: EntityType
    entity_id: str
    entity_name: str
    year: int
    month: Month
    n_cells: int
    raw_by_witness: str | None


class EntityEvidence(HarmonizedFields):
    """An entity_month record with `raw_by_witness` decoded into an object (GET /api/evidence)."""

    entity_type: EntityType
    entity_id: str
    entity_name: str
    year: int
    month: Month
    n_cells: int
    raw_by_witness: dict[Witness, int] | None


class EntityItem(_Strict):
    entity_type: EntityType
    entity_id: str
    entity_name: str
    bbox: tuple[float, float, float, float]  # [W, S, E, N]


class Anomaly(_Strict):
    entity_type: EntityType
    entity_id: str
    entity_name: str
    verdict: Verdict
    p_above: Probability | None
    p_below: Probability | None
    pct_of_normal: float | None


class Grid(_Strict):
    analysis_deg: float | None
    fine_deg: float | None


class DataSnapshot(_Strict):
    zips_downloaded: str | None
    api_pulled: str | None


class Metadata(_Strict):
    """metadata.json (§7)."""

    contract_version: str
    method_version: str
    synthetic: bool
    generated_at: str
    grid: Grid
    baseline_years: list[int]
    first_month: str
    latest_month: str
    provisional_months: list[str]
    witnesses: list[Witness]
    data_snapshot: DataSnapshot
    citation: str


class ValidationTest(_Strict):
    test_id: str
    family: str
    title: str
    case: str
    criterion: str
    threshold: str
    measured: dict[str, float | int | str | bool | None]
    status: TestStatus
    notes: str


class ValidationResults(_Strict):
    """validation_results.json (§6)."""

    contract_version: str
    method_version: str
    generated_at: str
    synthetic: bool
    tests: list[ValidationTest]


class CustomAreaRequest(_Strict):
    """Body of POST /api/series/custom and POST /api/export.csv: exactly one of

    - `bbox`: a bounding box [W, S, E, N] in degrees (WGS84), or
    - `polygon`: one outer ring of [lon, lat] points (3 to 100 different points, the first
      point not repeated: the API closes it).

    The shape of the ring is checked by `fire_api.polygon.validate_ring` (messages in `detail`).
    """

    bbox: tuple[float, float, float, float] | None = None
    polygon: list[tuple[float, float]] | None = Field(default=None, max_length=10_000)

    @model_validator(mode="after")
    def _exactly_one(self) -> "CustomAreaRequest":
        if (self.bbox is None) == (self.polygon is None):
            raise ValueError("Give either bbox or polygon, not both and not neither.")
        return self
