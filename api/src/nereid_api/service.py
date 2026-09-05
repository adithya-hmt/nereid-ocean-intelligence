# pyright: reportMissingImports=false
"""Deterministic assembly of scientific investigation responses."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from itertools import pairwise
from math import asin, cos, radians, sin, sqrt
from typing import Any, cast

import numpy as np
from pydantic import JsonValue

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
    SectionRequest,
)
from nereid_api.store import ArgoStore


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _provenance(rows: list[dict[str, Any]]) -> list[Provenance]:
    return [
        Provenance(
            source_url=row["source_url"],
            snapshot_doi=row["snapshot_doi"],
            fetched_at=row["fetched_at"],
            sha256=row["source_sha256"],
        )
        for row in {row["source_sha256"]: row for row in rows}.values()
    ]


def _profile_metrics(rows: list[dict[str, Any]], policy: QcPolicy) -> list[dict[str, JsonValue]]:
    grouped: dict[tuple[str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["wmo"], row["cycle"], row["source_profile_index"])].append(row)
    metrics: list[dict[str, Any]] = []
    for (wmo, cycle, source_profile_index), levels in grouped.items():
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
                        {"wmo": wmo, "cycle": cycle, "source_profile_index": source_profile_index, **metric.model_dump(mode="json")},
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
            eligible_count = self.store.count_qc_eligible(plan)
        elif plan.operation == "get_profile" and plan.wmo is not None and plan.cycle is not None:
            rows = self.store.get_profile(plan.wmo, plan.cycle, plan.qc_mode)
            candidate_count = len(rows)
            eligible_count = len(rows)
        else:
            raise ValueError(f"unsupported executable operation: {plan.operation}")

        data = [{key: _json_value(value) for key, value in row.items()} for row in rows]
        provenance = _provenance(rows)
        metrics = _profile_metrics(rows, plan.qc_mode) if rows else []
        warnings = (
            ["No matching profiles; widen one bounded filter."]
            if not rows
            else ["Results truncated to the requested row limit."]
            if eligible_count > len(rows)
            else []
        )
        schemes = {(row["wmo"], row["cycle"]): set() for row in rows}
        for row in rows:
            schemes[(row["wmo"], row["cycle"])].add(row["vertical_sampling_scheme"])
        if any(len(values) > 1 for values in schemes.values()):
            warnings.append("A selected cycle contains multiple ARGO vertical sampling schemes; representations remain separate.")
        return ResultEnvelope(
            query_plan=plan,
            data=data,
            chart_spec=[{"profile_metrics": metrics}],
            provenance=provenance,
            qc_summary=QcSummary(
                retained=len(rows),
                rejected=max(candidate_count - eligible_count, 0),
            ),
            methods=[
                MethodRecord(
                    name="duckdb_parameterized_profile_query",
                    version="1",
                    parameters={"qc_policy": plan.qc_mode, "row_limit": plan.row_limit, "source_representations": "preserved by source_profile_index"},
                )
            ],
            assumptions=["Pressure levels are retained per source representation; any analysis ordering is deterministic and does not alter QC flags."] if any(len(values) > 1 for values in schemes.values()) else [],
            warnings=warnings,
        )

    def export_selection(self, plan: QueryPlan, selections: list[dict[str, Any]]) -> ResultEnvelope:
        """Re-execute a bounded plan and export only known QC-eligible representations."""
        envelope = self.execute(plan)  # nosec B608: QueryPlan dispatch uses fixed, bound store queries.
        requested = {(item["wmo"], item["cycle"], item["source_profile_index"]) for item in selections}
        if len(requested) != len(selections):
            raise ValueError("export selections must be unique")
        available = {(row["wmo"], row["cycle"], row["source_profile_index"]) for row in envelope.data}
        if not requested <= available:
            raise ValueError("export selection is not present in the bounded QC-eligible result")
        rows = [row for row in envelope.data if (row["wmo"], row["cycle"], row["source_profile_index"]) in requested]
        candidate_count = self.store.count_selected_candidates(plan, requested)
        eligible_count = self.store.count_selected_qc_eligible(plan, requested)
        return envelope.model_copy(update={
            "data": rows,
            "provenance": _provenance(rows),
            "qc_summary": QcSummary(
                retained=len(rows),
                rejected=max(candidate_count - eligible_count, 0),
            ),
        })

    def derive_section(self, request: SectionRequest) -> ResultEnvelope:
        """Return a complete receipt for a QC-filtered, gap-masked section."""
        rows = self.store.compare_profiles(request.profile_ids, request.qc_mode)
        candidate_count = self.store.count_profile_candidates(request.profile_ids)
        # Each WMO/cycle selection expands to every preserved source representation.
        grouped: dict[tuple[str, int, int], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[(row["wmo"], row["cycle"], row["source_profile_index"])].append(row)
        profiles = sorted(grouped.values(), key=lambda levels: levels[0]["timestamp"])
        coordinates = [
            {
                "wmo": levels[0]["wmo"],
                "cycle": levels[0]["cycle"],
                "source_profile_index": levels[0]["source_profile_index"],
                "vertical_sampling_scheme": levels[0]["vertical_sampling_scheme"],
                "latitude": levels[0]["latitude"],
                "longitude": levels[0]["longitude"],
                "timestamp": _json_value(levels[0]["timestamp"]),
            }
            for levels in profiles
        ]
        cells: list[dict[str, Any]] = []
        masked_gaps: list[dict[str, Any]] = []
        lanes: dict[int, list[tuple[int, list[dict[str, Any]]]]] = defaultdict(list)
        for index, levels in enumerate(profiles):
            lanes[levels[0]["source_profile_index"]].append((index, levels))
        for lane in lanes.values():
            for (left_index, left), (right_index, right) in pairwise(lane):
                left_point, right_point = coordinates[left_index], coordinates[right_index]
                elapsed_hours = abs((datetime.fromisoformat(right_point["timestamp"]) - datetime.fromisoformat(left_point["timestamp"])).total_seconds()) / 3600
                reason = "time_gap" if elapsed_hours > request.max_time_gap_hours else "distance_gap" if _distance_km(left_point, right_point) > request.max_distance_km else None
                if reason:
                    masked_gaps.append({"left_profile_index": left_index, "right_profile_index": right_index, "reason": reason})
                deepest = min(max(row["depth_m"] for row in left), max(row["depth_m"] for row in right))
                for depth_m in np.arange(0, deepest + request.depth_step_m, request.depth_step_m):
                    left_temperature = _interpolate(left, depth_m, "temperature_adjusted")
                    right_temperature = _interpolate(right, depth_m, "temperature_adjusted")
                    left_salinity = _interpolate(left, depth_m, "salinity_adjusted")
                    right_salinity = _interpolate(right, depth_m, "salinity_adjusted")
                    cells.append({
                        "left_profile_index": left_index,
                        "right_profile_index": right_index,
                        "depth_m": float(depth_m),
                        "temperature": None
                        if reason or left_temperature is None or right_temperature is None
                        else (left_temperature + right_temperature) / 2,
                        "salinity": None
                        if reason or left_salinity is None or right_salinity is None
                        else (left_salinity + right_salinity) / 2,
                    }
                )
        section = cast(
            dict[str, JsonValue],
            {
                "observation_coordinates": coordinates,
                "section_cells": cells,
                "masked_gaps": masked_gaps,
            },
        )
        wmo, cycle = request.profile_ids[0]
        plan = QueryPlan(
            operation="derive_section",
            wmo=wmo,
            cycle=cycle,
            parameters=["TEMP", "PSAL"],
            qc_mode=request.qc_mode,
        )
        return ResultEnvelope(
            query_plan=plan,
            data=[section],
            chart_spec=[{"section": section}],
            provenance=_provenance(rows),
            qc_summary=QcSummary(
                retained=len(rows),
                rejected=max(candidate_count - len(rows), 0),
            ),
            methods=[
                MethodRecord(
                    name="gap_masked_linear_section",
                    version="1",
                    parameters={
                        "depth_step_m": request.depth_step_m,
                        "max_time_gap_hours": request.max_time_gap_hours,
                        "max_distance_km": request.max_distance_km,
                    },
                )
            ],
            assumptions=["Each WMO/cycle expands to all source representations; interpolation occurs only within a representation's native depth range and never across representations."],
            warnings=[] if rows else ["No matching profiles; widen one bounded filter."],
            section_request=request,
        )
