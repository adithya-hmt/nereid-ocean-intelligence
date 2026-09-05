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


def _mask_unrequested(rows: list[dict[str, Any]], parameters: Sequence[str], policy: QcPolicy) -> list[dict[str, Any]]:
    """Null every unrequested variable and derived values lacking their inputs' QC."""
    requested = set(parameters) or {"TEMP", "PSAL", "PRES"}
    fields = {
        "PRES": ("pressure_raw", "pressure_adjusted", "pressure_best", "pressure_dbar", "pressure_qc", "pressure_adjusted_qc", "pressure_adjusted_error", "adjusted_pressure_error"),
        "TEMP": ("temperature_raw", "temperature_adjusted", "temperature_best", "temperature_qc", "temperature_adjusted_qc", "temperature_adjusted_error", "conservative_temperature"),
        "PSAL": ("salinity_raw", "salinity_adjusted", "salinity_best", "salinity_qc", "salinity_adjusted_qc", "salinity_adjusted_error", "absolute_salinity"),
    }
    allowed = {1} if policy is QcPolicy.RESEARCH else {1, 2}
    for row in rows:
        # Raw observations are independently quarantined by their own Argo QC.
        if "TEMP" in requested and row["temperature_qc"] not in allowed:
            row["temperature_raw"] = None
        if "PSAL" in requested and row["salinity_qc"] not in allowed:
            row["salinity_raw"] = None
        if not {row["pressure_adjusted_qc"], row["salinity_adjusted_qc"]} <= allowed:
            row["absolute_salinity"] = None
        if not {row["pressure_adjusted_qc"], row["temperature_adjusted_qc"], row["salinity_adjusted_qc"]} <= allowed:
            row["conservative_temperature"] = None
        for parameter, names in fields.items():
            if parameter not in requested:
                for name in names:
                    row[name] = None
    return rows


def _profile_metrics(rows: list[dict[str, Any]], policy: QcPolicy, parameters: Sequence[str]) -> list[dict[str, JsonValue]]:
    grouped: dict[tuple[str, int, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["wmo"], row["cycle"], row["direction"], row["source_profile_index"])].append(row)
    metrics: list[dict[str, JsonValue]] = []
    for (wmo, cycle, direction, index), levels in grouped.items():
        first = levels[0]
        profile = ProfileSeries(wmo=wmo, cycle=cycle, depth_m=[row["depth_m"] for row in levels], latitude=first["latitude"], longitude=first["longitude"], timestamp=first["timestamp"], data_mode=DataMode(first["data_mode"]), conservative_temperature=DerivedObservationSeries(values=[row["conservative_temperature"] for row in levels], adjusted_qc=[row["temperature_adjusted_qc"] for row in levels], adjusted_errors=[row["temperature_adjusted_error"] for row in levels]), absolute_salinity=DerivedObservationSeries(values=[row["absolute_salinity"] for row in levels], adjusted_qc=[row["salinity_adjusted_qc"] for row in levels], adjusted_errors=[row["salinity_adjusted_error"] for row in levels]), pressure_adjusted_qc=[row["pressure_adjusted_qc"] for row in levels], pressure_adjusted_errors=[row["pressure_adjusted_error"] for row in levels])
        requested = set(parameters) or {"TEMP", "PSAL", "PRES"}
        metric_functions = []
        if "TEMP" in requested:
            metric_functions.append(principal_thermocline)
        if "PSAL" in requested:
            metric_functions.append(strongest_salinity_gradient)
        for metric_function in metric_functions:
            metric = metric_function(profile, policy)
            if metric:
                metrics.append(cast(dict[str, JsonValue], {"wmo": wmo, "cycle": cycle, "direction": direction, "source_profile_index": index, **metric.model_dump(mode="json")}))
    return metrics


def _distance_km(left: dict[str, Any], right: dict[str, Any]) -> float:
    lat_delta, lon_delta = radians(right["latitude"] - left["latitude"]), radians(right["longitude"] - left["longitude"])
    haversine = sin(lat_delta / 2) ** 2 + cos(radians(left["latitude"])) * cos(radians(right["latitude"])) * sin(lon_delta / 2) ** 2
    return 2 * 6371.0088 * asin(sqrt(haversine))


def _interpolate(levels: list[dict[str, Any]], depth_m: float, field: str, max_gap_m: float) -> tuple[float | None, str | None]:
    """Return only exact or adjacent bounded interpolation; never bridge a gap."""
    valid = sorted((float(row["depth_m"]), row[field], int(row["level_index"])) for row in levels if row[field] is not None)
    for native_depth, value, _level_index in valid:
        if native_depth == depth_m:
            return float(value), None
    for (lower_depth, lower, lower_index), (upper_depth, upper, upper_index) in pairwise(valid):
        if lower_depth < depth_m < upper_depth:
            # A rejected native level is a physical discontinuity, even if the
            # remaining depth bracket is shorter than the configurable bound.
            if upper_depth - lower_depth > max_gap_m or upper_index != lower_index + 1:
                return None, "vertical_gap"
            return float(lower + (upper - lower) * (depth_m - lower_depth) / (upper_depth - lower_depth)), None
    return None, None


class InvestigationService:
    def __init__(self, store: ArgoStore):
        self.store = store

    @staticmethod
    def _require_exact_representations(plan: QueryPlan, rows: list[dict[str, Any]]) -> None:
        requested = {(item.wmo, item.cycle, item.direction, item.source_profile_index) for item in plan.profile_ids}
        returned = {(row["wmo"], row["cycle"], row["direction"], row["source_profile_index"]) for row in rows}
        missing = requested - returned
        if missing:
            names = ", ".join(f"{wmo}/{cycle}/{direction}/{index}" for wmo, cycle, direction, index in sorted(missing))
            raise ValueError(f"insufficient or missing requested representation: {names}")

    def _envelope(self, plan: QueryPlan, rows: list[dict[str, Any]], candidate_count: int, eligible_count: int) -> ResultEnvelope:
        metrics = _profile_metrics(rows, plan.qc_mode, plan.parameters) if rows else []
        rows = _mask_unrequested(rows, plan.parameters, plan.qc_mode)
        data = [{key: _json_value(value) for key, value in row.items()} for row in rows]
        requested = set(plan.parameters) or {"TEMP", "PSAL", "PRES"}
        error_fields = {"PRES": "pressure_adjusted_error", "TEMP": "temperature_adjusted_error", "PSAL": "salinity_adjusted_error"}
        error_parameters: dict[str, dict[str, float | int | None]] = {}
        warnings: list[str] = []
        grouped_rows: dict[tuple[str, int, str, int], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped_rows[(row["wmo"], row["cycle"], row["direction"], row["source_profile_index"])].append(row)
        for identity, levels in grouped_rows.items():
            for parameter in requested:
                available = [float(row[error_fields[parameter]]) for row in levels if row[error_fields[parameter]] is not None and np.isfinite(float(row[error_fields[parameter]])) and float(row[error_fields[parameter]]) >= 0]
                key = f"{identity[0]}/{identity[1]}/{identity[2]}:{parameter}"
                error_parameters[key] = {"adjusted_error_available_count": len(available), "adjusted_error_max": max(available) if available else None}
                if len(available) != len(levels):
                    warnings.append(f"Adjusted-error metadata is missing or invalid for eligible {parameter} measurements in representation {identity[0]}/{identity[1]}/{identity[2]}.")
        if not rows:
            warnings.append("No matching profiles; widen one bounded filter.")
        elif plan.operation in {"find_profiles", "nearest_floats", "get_profile"} and eligible_count > len(rows):
            warnings.append("Results truncated to the requested row limit.")
        if len({row["vertical_sampling_scheme"] for row in rows}) > 1:
            warnings.append("Selected representations use multiple vertical sampling schemes.")
        if plan.operation == "nearest_floats":
            selected_count = len({(row["wmo"], row["cycle"], row["direction"], row["source_profile_index"]) for row in rows})
            warnings.append("Nearest representations are ordered by squared geographic distance from the bounding-box center.")
            if plan.float_count is not None and selected_count < plan.float_count:
                warnings.append(f"Only {selected_count} QC-eligible representations were available for requested float_count {plan.float_count}.")
        return ResultEnvelope(query_plan=plan, data=data, chart_spec=[{"profile_metrics": metrics}], provenance=_provenance(rows), qc_summary=QcSummary(retained=len(rows), rejected=max(candidate_count - eligible_count, 0)), methods=[MethodRecord(name="duckdb_parameterized_profile_query", version="1", parameters={"qc_policy": plan.qc_mode, "parameters": plan.parameters or ["TEMP", "PSAL", "PRES"], "row_limit": plan.row_limit, "nearest_order": "bbox_center_distance" if plan.operation == "nearest_floats" else "not_applicable", "float_count": plan.float_count if plan.operation == "nearest_floats" else None, "adjusted_errors": error_parameters})], assumptions=[], warnings=warnings)

    def run_plan(self, plan: QueryPlan) -> ResultEnvelope:
        if plan.operation == "derive_section":
            return self.derive_section(SectionRequest(profile_ids=plan.profile_ids, qc_mode=plan.qc_mode), plan)
        if plan.operation == "find_profiles":
            rows, candidate_count, eligible_count = self.store.find_profiles(plan), self.store.count_candidates(plan), self.store.count_qc_eligible(plan)
        elif plan.operation == "nearest_floats":
            rows = self.store.nearest_floats(plan)
            identities = {(row["wmo"], row["cycle"], row["direction"], row["source_profile_index"]) for row in rows}
            # Receipts describe the complete representations actually selected,
            # never the larger geographic candidate window.
            candidate_count = self.store.count_selected_candidates(plan, identities)
            eligible_count = self.store.count_selected_qc_eligible(plan, identities)
            if eligible_count > plan.row_limit:
                raise ValueError("nearest representations exceed row_limit")
        elif plan.operation == "get_profile":
            rows = self.store.get_profile(plan.wmo or "", plan.cycle or 0, plan.direction or "A", plan)
            candidate_count = self.store.count_profile_candidates(plan.wmo or "", plan.cycle or 0, plan.direction or "A")
            eligible_count = self.store.count_profile_qc_eligible(plan.wmo or "", plan.cycle or 0, plan.direction or "A", plan)
        else:  # compare_profiles has exact profile IDs.
            identities = {(item.wmo, item.cycle, item.direction, item.source_profile_index) for item in plan.profile_ids if item.source_profile_index is not None}
            candidate_count, eligible_count = self.store.count_selected_candidates(plan, identities), self.store.count_selected_qc_eligible(plan, identities)
            if eligible_count > plan.row_limit:
                raise ValueError("exact selection exceeds row_limit")
            rows = self.store.compare_profiles(plan.profile_ids, plan)
            self._require_exact_representations(plan, rows)
        return self._envelope(plan, rows, candidate_count, eligible_count)

    def export_selection(self, plan: QueryPlan, selections: list[dict[str, Any]]) -> ResultEnvelope:
        if plan.operation == "derive_section":
            raise ValueError("export_selection supports level-row query plans only")
        envelope = self.run_plan(plan)
        requested = {(item["wmo"], item["cycle"], item["direction"], item["source_profile_index"]) for item in selections}
        if len(requested) != len(selections):
            raise ValueError("export selections must be unique")
        available = {(row["wmo"], row["cycle"], row["direction"], row["source_profile_index"]) for row in envelope.data}
        if not requested <= available:
            raise ValueError("export selection is not present in the bounded QC-eligible result")
        rows = [row for row in envelope.data if (row["wmo"], row["cycle"], row["direction"], row["source_profile_index"]) in requested]
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
            row_limit=plan.row_limit,
        )
        identities = {(item.wmo, item.cycle, item.direction, item.source_profile_index) for item in request.profile_ids if item.source_profile_index is not None}
        candidate_count = self.store.count_selected_candidates(scientific_plan, identities)
        eligible_count = self.store.count_selected_qc_eligible(scientific_plan, identities)
        if eligible_count > plan.row_limit:
            raise ValueError("exact selection exceeds row_limit")
        rows = self.store.compare_profiles(request.profile_ids, scientific_plan)
        self._require_exact_representations(scientific_plan, rows)
        envelope = self._envelope(plan, rows, candidate_count, eligible_count)
        grouped: dict[tuple[str, int, str, int], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            grouped[(row["wmo"], row["cycle"], row["direction"], row["source_profile_index"])].append(row)
        profiles = [grouped[(item.wmo, item.cycle, item.direction, item.source_profile_index)] for item in request.profile_ids if item.source_profile_index is not None and (item.wmo, item.cycle, item.direction, item.source_profile_index) in grouped]
        coordinates = [{key: _json_value(levels[0][key]) for key in ("wmo", "cycle", "direction", "source_profile_index", "vertical_sampling_scheme", "latitude", "longitude", "timestamp")} for levels in profiles]
        cells: list[dict[str, Any]] = []
        gaps: list[dict[str, Any]] = []
        for index, (left, right) in enumerate(pairwise(profiles)):
            reason = "time_gap" if abs((datetime.fromisoformat(right[0]["timestamp"]) - datetime.fromisoformat(left[0]["timestamp"])).total_seconds()) / 3600 > request.max_time_gap_hours else ("distance_gap" if _distance_km(left[0], right[0]) > request.max_distance_km else None)
            if reason:
                gaps.append({"left_profile_index": index, "right_profile_index": index + 1, "reason": reason})
            for depth in np.arange(0, min(max(row["depth_m"] for row in left), max(row["depth_m"] for row in right)) + request.depth_step_m, request.depth_step_m):
                temperature, temperature_reason = _interpolate(left, depth, "conservative_temperature", request.max_vertical_gap_m)
                right_temperature, right_temperature_reason = _interpolate(right, depth, "conservative_temperature", request.max_vertical_gap_m)
                left_salinity, left_salinity_reason = _interpolate(left, depth, "absolute_salinity", request.max_vertical_gap_m)
                right_salinity, right_salinity_reason = _interpolate(right, depth, "absolute_salinity", request.max_vertical_gap_m)
                vertical_reason = temperature_reason or right_temperature_reason or left_salinity_reason or right_salinity_reason
                cell_reason = reason or vertical_reason
                cells.append({"left_profile_index": index, "right_profile_index": index + 1, "depth_m": float(depth), "temperature": None if cell_reason or temperature is None or right_temperature is None else (temperature + right_temperature) / 2, "salinity": None if cell_reason or left_salinity is None or right_salinity is None else (left_salinity + right_salinity) / 2, "mask_reason": cell_reason})
        section = cast(dict[str, JsonValue], {"observation_coordinates": coordinates, "section_cells": cells, "masked_gaps": gaps})
        return envelope.model_copy(update={"data": [section], "chart_spec": [{"section": section}], "section_request": request, "methods": [MethodRecord(name="gap_masked_linear_section", version="1", parameters={"depth_step_m": request.depth_step_m, "max_time_gap_hours": request.max_time_gap_hours, "max_distance_km": request.max_distance_km, "max_vertical_gap_m": request.max_vertical_gap_m})], "assumptions": ["Sections only connect the explicitly requested source representations."]})
