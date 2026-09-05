"""Validated contracts for bounded scientific investigations."""

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


Operation = Literal[
    "find_profiles",
    "nearest_floats",
    "get_profile",
    "compare_profiles",
    "derive_section",
    "export_selection",
]
Parameter = Literal["TEMP", "PSAL", "PRES"]


class QcPolicy(StrEnum):
    """Observation quality policy applied before scientific calculations."""

    RESEARCH = "research"
    EXPLORATORY = "exploratory"


class QueryPlan(BaseModel):
    """A bounded, allow-listed request that can be executed deterministically."""

    model_config = ConfigDict(extra="forbid")

    operation: Operation
    bbox: tuple[float, float, float, float] | None = None
    start_date: date | None = None
    end_date: date | None = None
    parameters: list[Parameter] = Field(default_factory=list)
    qc_mode: QcPolicy = QcPolicy.RESEARCH
    wmo: str | None = None
    cycle: int | None = Field(default=None, ge=0)
    row_limit: Annotated[int, Field(ge=1, le=100_000)] = 10_000

    @model_validator(mode="after")
    def require_bounded_selector(self) -> "QueryPlan":
        geographic_window = all(
            value is not None for value in (self.bbox, self.start_date, self.end_date)
        )
        profile_selector = self.wmo is not None and self.cycle is not None
        if not (geographic_window or profile_selector):
            raise ValueError(
                "query plan requires bbox, start_date, and end_date, or wmo and cycle"
            )
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date")
        if self.bbox:
            west, south, east, north = self.bbox
            if not (-180 <= west <= 180 and -180 <= east <= 180):
                raise ValueError("bbox longitude values must be between -180 and 180")
            if not (-90 <= south <= 90 and -90 <= north <= 90):
                raise ValueError("bbox latitude values must be between -90 and 90")
            if west >= east or south >= north:
                raise ValueError("bbox must have west < east and south < north")
        return self


class Provenance(BaseModel):
    source_url: str
    snapshot_doi: str
    fetched_at: datetime
    sha256: str


class QcSummary(BaseModel):
    retained: int = Field(ge=0)
    rejected: int = Field(ge=0)


class MethodRecord(BaseModel):
    name: str
    version: str
    parameters: dict[str, JsonValue]


class DataMode(StrEnum):
    """ARGO profile processing state retained with every scientific input."""

    REAL_TIME = "R"
    DELAYED = "D"
    ADJUSTED_REAL_TIME = "A"


class ObservationSeries(BaseModel):
    """Raw and adjusted values plus their per-level ARGO quality metadata."""

    raw_values: list[float | None]
    raw_qc: list[int | None]
    adjusted_values: list[float | None]
    adjusted_qc: list[int | None]
    adjusted_errors: list[float | None]


class ProfileSeries(BaseModel):
    """A source-faithful profile whose observation arrays share native depth levels."""

    wmo: str
    cycle: int = Field(ge=0)
    depth_m: list[float]
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timestamp: datetime
    data_mode: DataMode
    conservative_temperature: ObservationSeries
    absolute_salinity: ObservationSeries

    @model_validator(mode="after")
    def require_observation_alignment(self) -> "ProfileSeries":
        level_count = len(self.depth_m)
        for name in ("conservative_temperature", "absolute_salinity"):
            observations = getattr(self, name)
            for field_name in (
                "raw_values",
                "raw_qc",
                "adjusted_values",
                "adjusted_qc",
                "adjusted_errors",
            ):
                if len(getattr(observations, field_name)) != level_count:
                    raise ValueError(f"{name}.{field_name} must align with depth_m")
        return self


class DerivedMetric(BaseModel):
    name: str
    depth_m: float
    value: float
    units: str
    uncertainty_m: float = Field(gt=0)
    algorithm: str
    parameters: dict[str, JsonValue]
    quality_label: str


class ResultEnvelope(BaseModel):
    query_plan: QueryPlan
    data: list[dict[str, JsonValue]]
    chart_spec: list[dict[str, JsonValue]]
    provenance: list[Provenance]
    qc_summary: QcSummary
    methods: list[MethodRecord]
    assumptions: list[str]
    warnings: list[str]
    answer: str | None = None
