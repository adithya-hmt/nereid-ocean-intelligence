# pyright: reportMissingImports=false
"""Deterministic assembly of scientific investigation responses."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime
from itertools import pairwise
from math import asin, cos, radians, sin, sqrt
from typing import Any, cast

import numpy as np
from pydantic import JsonValue

from nereid_api.analytics import principal_thermocline, strongest_salinity_gradient
from nereid_api.models import (
    DataMode,
    DerivedObservationSeries,
    MethodRecord,
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
    return value.isoformat() if isinstance(value, datetime) else value


def _provenance(rows: list[dict[str, Any]]) -> list[Provenance]:
    return [Provenance(source_url=row["source_url"], snapshot_doi=row["snapshot_doi"], fetched_at=row["fetched_at"], sha256=row["source_sha256"]) for row in {row["source_sha256"]: row for row in rows}.values()]


def _mask_unrequested(rows: list[dict[str, Any]], parameters: Sequence[str]) -> list[dict[str, Any]]:
    """Never expose an unrequested variable's QC 3/4 value or flag."""
    requested = set(parameters) or {"TEMP", "PSAL", "PRES"}
    fields = {
        "TEMP": ("temperature_raw", "temperature_adjusted", "temperature_best", "temperature_qc", "temperature_adjusted_qc", "temperature_adjusted_error", "conservative_temperature"),
        "PSAL": ("salinity_raw", "salinity_adjusted", "salinity_best", "salinity_qc", "salinity_adjusted_qc", "salinity_adjusted_error", "absolute_salinity"),
    }
    for row in rows:
        for parameter, names in fields.items():
            qc = row[f"{'temperature' if parameter == 'TEMP' else 'salinity'}_adjusted_qc"]
            if parameter not in requested and qc in {3, 4}:
                for name in names:
                    row[name] = None
    return rows


def _profile_metrics(rows: list[dict[str, Any]], policy: QcPolicy) -> list[dict[str, JsonValue]]:
    grouped: dict[tuple[str, int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["wmo"], row["cycle"], row["source_profile_index"])].append(row)
    metrics: list[dict[str, JsonValue]] = []
    for (wmo, cycle, index), levels in grouped.items():
        first = levels[0]
        profile = ProfileSeries(wmo=wmo, cycle=cycle, depth_m=[row["depth_m"] for row in levels], latitude=first["latitude"], longitude=first["longitude"], timestamp=first["timestamp"], data_mode=DataMode(first["data_mode"]), conservative_temperature=DerivedObservationSeries(values=[row["conservative_temperature"] for row in levels], adjusted_qc=[row["temperature_adjusted_qc"] for row in levels], adjusted_errors=[row["temperature_adjusted_error"] for row in levels]), absolute_salinity=DerivedObservationSeries(values=[row["absolute_salinity"] for row in levels], adjusted_qc=[row["salinity_adjusted_qc"] for row in levels], adjusted_errors=[row["salinity_adjusted_error"] for row in levels]), pressure_adjusted_qc=[row["pressure_adjusted_qc"] for row in levels], pressure_adjusted_errors=[row["pressure_adjusted_error"] for row in levels])
        for metric in (principal_thermocline(profile, policy), strongest_salinity_gradient(profile, policy)):
            if metric:
                metrics.append(cast(dict[str, JsonValue], {"wmo": wmo, "cycle": cycle, "source_profile_index": index, **metric.model_dump(mode="json")}))
    return metrics


def _distance_km(left: dict[str, Any], right: dict[str, Any]) -> float:
    lat_delta, lon_delta = radians(right["latitude"] - left["latitude"]), radians(right["longitude"] - left["longitude"])
    haversine = sin(lat_delta / 2) ** 2 + cos(radians(left["latitude"])) * cos(radians(right["latitude"])) * sin(lon_delta / 2) ** 2
    return 2 * 6371.0088 * asin(sqrt(haversine))


def _interpolate(levels: list[dict[str, Any]], depth_m: float, field: str) -> float | None:
    valid = [(row["depth_m"], row[field]) for row in levels if row[field] is not None]
    if not valid or depth_m < valid[0][0] or depth_m > valid[-1][0]:
        return None
    return float(np.interp(depth_m, *zip(*valid, strict=True)))


class InvestigationService:
    def __init__(self, store: ArgoStore):
        self.store = store

    @staticmethod
    def _require_exact_representations(plan: QueryPlan, rows: list[dict[str, Any]]) -> None:
        requested = {(item.wmo, item.cycle, item.source_profile_index) for item in plan.profile_ids}
        returned = {(row["wmo"], row["cycle"], row["source_profile_index"]) for row in rows}
        missing = requested - returned
        if missing:
            names = ", ".join(f"{wmo}/{cycle}/{index}" for wmo, cycle, index in sorted(missing))
            raise ValueError(f"insufficient or missing requested representation: {names}")

    def _envelope(self, plan: QueryPlan, rows: list[dict[str, Any]], candidate_count: int, eligible_count: int) -> ResultEnvelope:
        rows = _mask_unrequested(rows, plan.parameters)
        data = [{key: _json_value(value) for key, value in row.items()} for row in rows]
        warnings = ["No matching profiles; widen one bounded filter."] if not rows else (["Results truncated to the requested row limit."] if plan.operation == "find_profiles" and eligible_count > len(rows) else [])
        if plan.operation == "nearest_floats":
            warnings = warnings + ["Nearest representations are ordered by squared geographic distance from the bounding-box center."]
        return ResultEnvelope(query_plan=plan, data=data, chart_spec=[{"profile_metrics": _profile_metrics(rows, plan.qc_mode) if rows else []}], provenance=_provenance(rows), qc_summary=QcSummary(retained=len(rows), rejected=max(candidate_count - eligible_count, 0)), methods=[MethodRecord(name="duckdb_parameterized_profile_query", version="1", parameters={"qc_policy": plan.qc_mode, "parameters": plan.parameters or ["TEMP", "PSAL", "PRES"], "row_limit": plan.row_limit, "nearest_order": "bbox_center_distance" if plan.operation == "nearest_floats" else "not_applicable"})], assumptions=[], warnings=warnings)

    def run_plan(self, plan: QueryPlan) -> ResultEnvelope:
        if plan.operation == "derive_section":
            return self.derive_section(SectionRequest(profile_ids=plan.profile_ids, qc_mode=plan.qc_mode), plan)
        if plan.operation == "find_profiles":
            rows, candidate_count, eligible_count = self.store.find_profiles(plan), self.store.count_candidates(plan), self.store.count_qc_eligible(plan)
        elif plan.operation == "nearest_floats":
            rows, candidate_count, eligible_count = self.store.nearest_floats(plan), self.store.count_candidates(plan), self.store.count_qc_eligible(plan)
        elif plan.operation == "get_profile":
            rows = self.store.get_profile(plan.wmo or "", plan.cycle or 0, plan)
            candidate_count, eligible_count = self.store.count_profile_candidates(plan.wmo or "", plan.cycle or 0), len(rows)
        else:  # compare_profiles has exact profile IDs.
            rows = self.store.compare_profiles(plan.profile_ids, plan)
            self._require_exact_representations(plan, rows)
            identities = {(item.wmo, item.cycle, item.source_profile_index) for item in plan.profile_ids if item.source_profile_index is not None}
            candidate_count, eligible_count = self.store.count_selected_candidates(plan, identities), self.store.count_selected_qc_eligible(plan, identities)
        return self._envelope(plan, rows, candidate_count, eligible_count)

    def export_selection(self, plan: QueryPlan, selections: list[dict[str, Any]]) -> ResultEnvelope:
        if plan.operation == "derive_section":
            raise ValueError("export_selection supports level-row query plans only")
        envelope = self.run_plan(plan)
        requested = {(item["wmo"], item["cycle"], item["source_profile_index"]) for item in selections}
        if len(requested) != len(selections):
            raise ValueError("export selections must be unique")
        available = {(row["wmo"], row["cycle"], row["source_profile_index"]) for row in envelope.data}
        if not requested <= available:
            raise ValueError("export selection is not present in the bounded QC-eligible result")
        rows = [row for row in envelope.data if (row["wmo"], row["cycle"], row["source_profile_index"]) in requested]
        candidate_count = self.store.count_selected_candidates(plan, requested)
        eligible_count = self.store.count_selected_qc_eligible(plan, requested)
        return envelope.model_copy(update={"data": rows, "provenance": _provenance(rows), "qc_summary": QcSummary(retained=len(rows), rejected=max(candidate_count - eligible_count, 0))})

    def derive_section(self, request: SectionRequest, query_plan: QueryPlan | None = None) -> ResultEnvelope:
        plan = query_plan or QueryPlan(operation="derive_section", profile_ids=request.profile_ids, parameters=["TEMP", "PSAL"], qc_mode=request.qc_mode)
        scientific_plan = QueryPlan(
            operation="compare_profiles",
            profile_ids=request.profile_ids,
            parameters=["TEMP", "PSAL"],
            qc_mode=request.qc_mode,
        )
        rows = self.store.compare_profiles(request.profile_ids, scientific_plan)
        self._require_exact_representations(scientific_plan, rows)
        identities = {(item.wmo, item.cycle, item.source_profile_index) for item in request.profile_ids if item.source_profile_index is not None}
        envelope = self._envelope(plan, rows, self.store.count_selected_candidates(scientific_plan, identities), self.store.count_selected_qc_eligible(scientific_plan, identities))
        grouped: dict[tuple[str, int, int], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[(row["wmo"], row["cycle"], row["source_profile_index"])].append(row)
        profiles = [grouped[(item.wmo, item.cycle, item.source_profile_index)] for item in request.profile_ids if item.source_profile_index is not None and (item.wmo, item.cycle, item.source_profile_index) in grouped]
        coordinates = [{key: _json_value(levels[0][key]) for key in ("wmo", "cycle", "source_profile_index", "vertical_sampling_scheme", "latitude", "longitude", "timestamp")} for levels in profiles]
        cells: list[dict[str, Any]] = []
        gaps: list[dict[str, Any]] = []
        for index, (left, right) in enumerate(pairwise(profiles)):
            reason = "time_gap" if abs((datetime.fromisoformat(right[0]["timestamp"]) - datetime.fromisoformat(left[0]["timestamp"])).total_seconds()) / 3600 > request.max_time_gap_hours else ("distance_gap" if _distance_km(left[0], right[0]) > request.max_distance_km else None)
            if reason:
                gaps.append({"left_profile_index": index, "right_profile_index": index + 1, "reason": reason})
            for depth in np.arange(0, min(max(row["depth_m"] for row in left), max(row["depth_m"] for row in right)) + request.depth_step_m, request.depth_step_m):
                temperature, salinity = _interpolate(left, depth, "conservative_temperature"), _interpolate(right, depth, "conservative_temperature")
                left_salinity, right_salinity = _interpolate(left, depth, "absolute_salinity"), _interpolate(right, depth, "absolute_salinity")
                cells.append({"left_profile_index": index, "right_profile_index": index + 1, "depth_m": float(depth), "temperature": None if reason or temperature is None or salinity is None else (temperature + salinity) / 2, "salinity": None if reason or left_salinity is None or right_salinity is None else (left_salinity + right_salinity) / 2})
        section = cast(dict[str, JsonValue], {"observation_coordinates": coordinates, "section_cells": cells, "masked_gaps": gaps})
        return envelope.model_copy(update={"data": [section], "chart_spec": [{"section": section}], "section_request": request, "methods": [MethodRecord(name="gap_masked_linear_section", version="1", parameters={"depth_step_m": request.depth_step_m, "max_time_gap_hours": request.max_time_gap_hours, "max_distance_km": request.max_distance_km})], "assumptions": ["Sections only connect the explicitly requested source representations."]})
