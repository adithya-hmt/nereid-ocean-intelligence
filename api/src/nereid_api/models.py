# ruff: noqa: I001
# pyright: reportMissingImports=false
"""Validated contracts for bounded scientific investigations."""

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

Operation = Literal["find_profiles", "nearest_floats", "get_profile", "compare_profiles", "derive_section"]
Parameter = Literal["TEMP", "PSAL", "PRES"]


class QcPolicy(StrEnum):
    RESEARCH = "research"
    EXPLORATORY = "exploratory"


class ProfileIdentifier(BaseModel):
    """One preserved ARGO representation; index is required where lanes matter."""

    model_config = ConfigDict(extra="forbid")
    wmo: str = Field(min_length=1)
    cycle: int = Field(ge=0)
    direction: Literal["A", "D"]
    source_profile_index: int | None = Field(default=None, ge=0)


class SectionRequest(BaseModel):
    """Complete bounded controls needed to replay one derived section."""

    model_config = ConfigDict(extra="forbid")
    profile_ids: list[ProfileIdentifier] = Field(min_length=2, max_length=100)
    qc_mode: QcPolicy = QcPolicy.RESEARCH
    depth_step_m: float = Field(default=10, gt=0, le=100)
    max_time_gap_hours: float = Field(default=168, gt=0, le=24 * 31)
    max_distance_km: float = Field(default=500, gt=0, le=2_000)
    max_vertical_gap_m: float = Field(default=100, gt=0, le=500)

    @model_validator(mode="after")
    def require_unique_representations(self) -> "SectionRequest":
        identities = [(item.wmo, item.cycle, item.direction, item.source_profile_index) for item in self.profile_ids]
        if len(identities) != len(set(identities)):
            raise ValueError("profile_ids must be unique")
        if any(item.source_profile_index is None for item in self.profile_ids):
            raise ValueError("section profile_ids require source_profile_index")
        return self


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
    direction: Literal["A", "D"] | None = None
    profile_ids: list[ProfileIdentifier] = Field(default_factory=list, max_length=100)
    row_limit: Annotated[int, Field(ge=1, le=100_000)] = 10_000
    float_count: Annotated[int | None, Field(ge=1, le=100)] = None

    @model_validator(mode="after")
    def validate_operation_selector(self) -> "QueryPlan":
        geographic = self.bbox is not None or self.start_date is not None or self.end_date is not None
        complete_geographic = self.bbox is not None and self.start_date is not None and self.end_date is not None
        single_profile = self.wmo is not None or self.cycle is not None or self.direction is not None
        complete_single_profile = self.wmo is not None and self.cycle is not None and self.direction is not None
        if self.start_date is not None and self.end_date is not None and self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date")
        if self.bbox:
            west, south, east, north = self.bbox
            if not (-180 <= west <= 180 and -180 <= east <= 180) or not (-90 <= south <= 90 and -90 <= north <= 90):
                raise ValueError("bbox coordinates are out of range")
            if west >= east or south >= north:
                raise ValueError("bbox must have west < east and south < north")
        if self.operation in {"find_profiles", "nearest_floats"}:
            if not complete_geographic or single_profile or self.profile_ids or (self.operation == "nearest_floats" and self.float_count is None) or (self.operation == "find_profiles" and self.float_count is not None):
                raise ValueError(f"{self.operation} requires bbox, start_date, and end_date only")
        elif self.operation == "get_profile":
            if not complete_single_profile or geographic or self.profile_ids or self.float_count is not None:
                raise ValueError("get_profile requires exactly wmo, cycle, and direction")
        else:
            identities = [(item.wmo, item.cycle, item.direction, item.source_profile_index) for item in self.profile_ids]
            if geographic or single_profile or self.float_count is not None or not (2 <= len(self.profile_ids) <= 100):
                raise ValueError(f"{self.operation} requires 2–100 profile_ids only")
            if len(identities) != len(set(identities)):
                raise ValueError("profile_ids must be unique")
            if any(item.source_profile_index is None for item in self.profile_ids):
                raise ValueError(f"{self.operation} profile_ids require source_profile_index")
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
    REAL_TIME = "R"
    DELAYED = "D"
    ADJUSTED_REAL_TIME = "A"


class ObservationSeries(BaseModel):
    raw_values: list[float | None]
    raw_qc: list[int | None]
    adjusted_values: list[float | None]
    adjusted_qc: list[int | None]
    adjusted_errors: list[float | None]


class DerivedObservationSeries(BaseModel):
    values: list[float | None]
    adjusted_qc: list[int | None]
    adjusted_errors: list[float | None]


class ProfileSeries(BaseModel):
    wmo: str
    cycle: int = Field(ge=0)
    depth_m: list[float]
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timestamp: datetime
    data_mode: DataMode
    conservative_temperature: DerivedObservationSeries
    absolute_salinity: DerivedObservationSeries
    pressure_adjusted_qc: list[int | None]
    pressure_adjusted_errors: list[float | None]

    @model_validator(mode="after")
    def require_observation_alignment(self) -> "ProfileSeries":
        count = len(self.depth_m)
        for name in ("conservative_temperature", "absolute_salinity"):
            for field_name in ("values", "adjusted_qc", "adjusted_errors"):
                if len(getattr(getattr(self, name), field_name)) != count:
                    raise ValueError(f"{name}.{field_name} must align with depth_m")
        if len(self.pressure_adjusted_qc) != count or len(self.pressure_adjusted_errors) != count:
            raise ValueError("pressure_adjusted fields must align with depth_m")
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
    section_request: SectionRequest | None = None
    answer: str | None = None
