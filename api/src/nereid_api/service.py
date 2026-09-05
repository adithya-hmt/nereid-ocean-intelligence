# pyright: reportMissingImports=false
"""Deterministic assembly of scientific investigation responses."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from itertools import pairwise
from math import asin, cos, radians, sin, sqrt
from typing import Any, cast

import numpy as np
from pydantic import BaseModel, Field, JsonValue

from nereid_api.analytics import principal_thermocline, strongest_salinity_gradient
from nereid_api.models import (
    DataMode,
    MethodRecord,
    ObservationSeries,
    ProfileSeries,
    Provenance,
    QcPolicy,
    QcSummary,
    QueryPlan,
    ResultEnvelope,
)
from nereid_api.store import ArgoStore


class SectionRequest(BaseModel):
    """Bounded controls for deriving a section from selected local profiles."""

    profile_ids: list[tuple[str, int]] = Field(min_length=2, max_length=100)
    qc_mode: QcPolicy = QcPolicy.RESEARCH
    depth_step_m: float = Field(default=10, gt=0, le=100)
    max_time_gap_hours: float = Field(default=168, gt=0, le=24 * 31)
    max_distance_km: float = Field(default=500, gt=0, le=2_000)


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _profile_metrics(rows: list[dict[str, Any]], policy: QcPolicy) -> list[dict[str, JsonValue]]:
    grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["wmo"], row["cycle"])].append(row)
    metrics: list[dict[str, Any]] = []
    for (wmo, cycle), levels in grouped.items():
        first = levels[0]
        temperature = ObservationSeries(
            raw_values=[row["temperature_raw"] for row in levels],
            raw_qc=[row["temperature_qc"] for row in levels],
            adjusted_values=[row["temperature_adjusted"] for row in levels],
            adjusted_qc=[row["temperature_adjusted_qc"] for row in levels],
            adjusted_errors=[row["temperature_adjusted_error"] for row in levels],
        )
        salinity = ObservationSeries(
            raw_values=[row["salinity_raw"] for row in levels],
            raw_qc=[row["salinity_qc"] for row in levels],
            adjusted_values=[row["salinity_adjusted"] for row in levels],
            adjusted_qc=[row["salinity_adjusted_qc"] for row in levels],
            adjusted_errors=[row["salinity_adjusted_error"] for row in levels],
        )
        profile = ProfileSeries(
            wmo=wmo,
            cycle=cycle,
            depth_m=[row["depth_m"] for row in levels],
            latitude=first["latitude"],
            longitude=first["longitude"],
            timestamp=first["timestamp"],
            data_mode=DataMode(first["data_mode"]),
            conservative_temperature=temperature,
            absolute_salinity=salinity,
        )
        for metric in (principal_thermocline(profile, policy), strongest_salinity_gradient(profile, policy)):
            if metric is not None:
                metrics.append(
                    cast(
                        dict[str, JsonValue],
                        {"wmo": wmo, "cycle": cycle, **metric.model_dump(mode="json")},
                    )
                )
    return metrics


def _distance_km(left: dict[str, Any], right: dict[str, Any]) -> float:
    latitude_delta = radians(right["latitude"] - left["latitude"])
    longitude_delta = radians(right["longitude"] - left["longitude"])
    latitude_left, latitude_right = radians(left["latitude"]), radians(right["latitude"])
    haversine = sin(latitude_delta / 2) ** 2 + cos(latitude_left) * cos(latitude_right) * sin(longitude_delta / 2) ** 2
    return 2 * 6371.0088 * asin(sqrt(haversine))


def _interpolate(levels: list[dict[str, Any]], depth_m: float, field: str) -> float | None:
    depths = np.asarray([row["depth_m"] for row in levels], dtype=float)
    values = np.asarray([row[field] for row in levels], dtype=float)
    if depth_m < depths.min() or depth_m > depths.max():
        return None
    return float(np.interp(depth_m, depths, values))


class InvestigationService:
    """Runs only typed, bounded operations against one local snapshot."""

    def __init__(self, store: ArgoStore):
        self.store = store

    def execute(self, plan: QueryPlan) -> ResultEnvelope:
        if plan.operation == "find_profiles":
            rows = self.store.find_profiles(plan)
            candidate_count = self.store.count_candidates(plan)
        elif plan.operation == "get_profile" and plan.wmo is not None and plan.cycle is not None:
            rows = self.store.get_profile(plan.wmo, plan.cycle, plan.qc_mode)
            candidate_count = len(rows)
        else:
            raise ValueError(f"unsupported executable operation: {plan.operation}")

        data = [{key: _json_value(value) for key, value in row.items()} for row in rows]
        provenance = [
            Provenance(
                source_url=row["source_url"],
                snapshot_doi=row["snapshot_doi"],
                fetched_at=row["fetched_at"],
                sha256=row["source_sha256"],
            )
            for row in {row["source_sha256"]: row for row in rows}.values()
        ]
        metrics = _profile_metrics(rows, plan.qc_mode) if rows else []
        warnings = [] if rows else ["No matching profiles; widen one bounded filter."]
        return ResultEnvelope(
            query_plan=plan,
            data=data,
            chart_spec=[{"profile_metrics": metrics}],
            provenance=provenance,
            qc_summary=QcSummary(retained=len(rows), rejected=max(candidate_count - len(rows), 0)),
            methods=[
                MethodRecord(
                    name="duckdb_parameterized_profile_query",
                    version="1",
                    parameters={"qc_policy": plan.qc_mode, "row_limit": plan.row_limit},
                )
            ],
            assumptions=[],
            warnings=warnings,
        )

    def derive_section(self, request: SectionRequest) -> dict[str, Any]:
        rows = self.store.compare_profiles(request.profile_ids, request.qc_mode)
        grouped: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[(row["wmo"], row["cycle"])].append(row)
        profiles = sorted(grouped.values(), key=lambda levels: levels[0]["timestamp"])
        coordinates = [
            {
                "wmo": levels[0]["wmo"],
                "cycle": levels[0]["cycle"],
                "latitude": levels[0]["latitude"],
                "longitude": levels[0]["longitude"],
                "timestamp": _json_value(levels[0]["timestamp"]),
            }
            for levels in profiles
        ]
        cells: list[dict[str, Any]] = []
        masked_gaps: list[dict[str, Any]] = []
        for index, (left, right) in enumerate(pairwise(profiles)):
            left_point, right_point = coordinates[index], coordinates[index + 1]
            elapsed_hours = abs(
                (datetime.fromisoformat(right_point["timestamp"]) - datetime.fromisoformat(left_point["timestamp"])).total_seconds()
            ) / 3600
            reason = None
            if elapsed_hours > request.max_time_gap_hours:
                reason = "time_gap"
            elif _distance_km(left_point, right_point) > request.max_distance_km:
                reason = "distance_gap"
            if reason:
                masked_gaps.append({"left_profile_index": index, "right_profile_index": index + 1, "reason": reason})
            deepest = min(max(row["depth_m"] for row in left), max(row["depth_m"] for row in right))
            for depth_m in np.arange(0, deepest + request.depth_step_m, request.depth_step_m):
                left_temperature = _interpolate(left, depth_m, "temperature_adjusted")
                right_temperature = _interpolate(right, depth_m, "temperature_adjusted")
                left_salinity = _interpolate(left, depth_m, "salinity_adjusted")
                right_salinity = _interpolate(right, depth_m, "salinity_adjusted")
                cells.append(
                    {
                        "left_profile_index": index,
                        "right_profile_index": index + 1,
                        "depth_m": float(depth_m),
                        "temperature": None
                        if reason or left_temperature is None or right_temperature is None
                        else (left_temperature + right_temperature) / 2,
                        "salinity": None
                        if reason or left_salinity is None or right_salinity is None
                        else (left_salinity + right_salinity) / 2,
                    }
                )
        return {"observation_coordinates": coordinates, "section_cells": cells, "masked_gaps": masked_gaps}
