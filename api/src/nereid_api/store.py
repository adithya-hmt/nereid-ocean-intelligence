# pyright: reportMissingImports=false
"""Read-only, parameterized DuckDB access to a normalized ARGO snapshot."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from nereid_api.models import ProfileIdentifier, QcPolicy, QueryPlan


class SnapshotUnavailable(FileNotFoundError):
    """Raised when a required local snapshot table is unavailable."""


_JOIN = """FROM levels AS l INNER JOIN profiles AS p
USING (wmo, cycle, direction, source_profile_index)"""
_GEO = """p.longitude BETWEEN ? AND ? AND p.latitude BETWEEN ? AND ?
AND CAST(p.timestamp AS DATE) BETWEEN ? AND ?"""
_QC = """(l.pressure_adjusted_qc = 1 OR (? AND l.pressure_adjusted_qc = 2))
AND (NOT ? OR l.temperature_adjusted_qc = 1 OR (? AND l.temperature_adjusted_qc = 2))
AND (NOT ? OR l.salinity_adjusted_qc = 1 OR (? AND l.salinity_adjusted_qc = 2))"""
_FIND_SQL = f"SELECT l.*, p.latitude, p.longitude, p.timestamp, p.source_url, p.snapshot_doi, p.fetched_at {_JOIN} WHERE {_GEO} AND {_QC} ORDER BY p.timestamp, l.wmo, l.cycle, l.source_profile_index, l.pressure_dbar LIMIT ?"
_GEO_COUNT_SQL = f"SELECT count(*) AS row_count {_JOIN} WHERE {_GEO}"
_GEO_ELIGIBLE_SQL = f"SELECT count(*) AS row_count {_JOIN} WHERE {_GEO} AND {_QC}"
_PROFILE_SQL = f"SELECT l.*, p.latitude, p.longitude, p.timestamp, p.source_url, p.snapshot_doi, p.fetched_at {_JOIN} WHERE l.wmo = ? AND l.cycle = ? AND {_QC} ORDER BY p.timestamp, l.source_profile_index, l.pressure_dbar"
_PROFILE_COUNT_SQL = "SELECT count(*) AS row_count FROM levels WHERE wmo = ? AND cycle = ?"
_SELECTED_SQL = f"SELECT l.*, p.latitude, p.longitude, p.timestamp, p.source_url, p.snapshot_doi, p.fetched_at {_JOIN} WHERE list_contains(?, struct_pack(wmo := l.wmo, cycle := l.cycle, source_profile_index := l.source_profile_index)) AND {_QC} ORDER BY p.timestamp, l.wmo, l.cycle, l.source_profile_index, l.pressure_dbar"
_SELECTED_COUNT_SQL = "SELECT count(*) AS row_count FROM levels AS l WHERE list_contains(?, struct_pack(wmo := l.wmo, cycle := l.cycle, source_profile_index := l.source_profile_index))"
_SELECTED_ELIGIBLE_SQL = """SELECT count(*) AS row_count FROM levels AS l
WHERE list_contains(?, struct_pack(wmo := l.wmo, cycle := l.cycle, source_profile_index := l.source_profile_index))
AND (l.pressure_adjusted_qc = 1 OR (? AND l.pressure_adjusted_qc = 2))
AND (NOT ? OR l.temperature_adjusted_qc = 1 OR (? AND l.temperature_adjusted_qc = 2))
AND (NOT ? OR l.salinity_adjusted_qc = 1 OR (? AND l.salinity_adjusted_qc = 2))"""
_NEAREST_SQL = """WITH eligible AS (
SELECT l.*, p.latitude, p.longitude, p.timestamp, p.source_url, p.snapshot_doi, p.fetched_at,
((p.latitude - ?) * (p.latitude - ?) + (p.longitude - ?) * (p.longitude - ?)) AS center_distance
FROM levels AS l INNER JOIN profiles AS p USING (wmo, cycle, direction, source_profile_index)
WHERE p.longitude BETWEEN ? AND ? AND p.latitude BETWEEN ? AND ?
AND CAST(p.timestamp AS DATE) BETWEEN ? AND ?
AND (l.pressure_adjusted_qc = 1 OR (? AND l.pressure_adjusted_qc = 2))
AND (NOT ? OR l.temperature_adjusted_qc = 1 OR (? AND l.temperature_adjusted_qc = 2))
AND (NOT ? OR l.salinity_adjusted_qc = 1 OR (? AND l.salinity_adjusted_qc = 2))
), selected AS (
SELECT DISTINCT wmo, cycle, direction, source_profile_index FROM eligible
ORDER BY min(center_distance) OVER (PARTITION BY wmo, cycle, direction, source_profile_index), wmo, cycle, source_profile_index LIMIT ?
)
SELECT eligible.* FROM eligible INNER JOIN selected USING (wmo, cycle, direction, source_profile_index)
ORDER BY center_distance, timestamp, wmo, cycle, source_profile_index, pressure_dbar"""
_TEMPLATES = {_FIND_SQL, _GEO_COUNT_SQL, _GEO_ELIGIBLE_SQL, _PROFILE_SQL, _PROFILE_COUNT_SQL, _SELECTED_SQL, _SELECTED_COUNT_SQL, _SELECTED_ELIGIBLE_SQL, _NEAREST_SQL}


def _qc_values(plan: QueryPlan | QcPolicy, parameters: list[str] | None = None) -> list[bool]:
    policy = plan.qc_mode if isinstance(plan, QueryPlan) else plan
    requested = set(plan.parameters if isinstance(plan, QueryPlan) else parameters or []) or {"TEMP", "PSAL", "PRES"}
    exploratory = policy is QcPolicy.EXPLORATORY
    return [exploratory, "TEMP" in requested, exploratory, "PSAL" in requested, exploratory]


class ArgoStore:
    def __init__(self, snapshot_dir: Path):
        profiles_path, levels_path = Path(snapshot_dir) / "profiles.parquet", Path(snapshot_dir) / "levels.parquet"
        missing = [str(path) for path in (profiles_path, levels_path) if not path.is_file()]
        if missing:
            raise SnapshotUnavailable("snapshot requires " + ", ".join(missing))
        self.connection = duckdb.connect(":memory:")
        self.connection.read_parquet(str(profiles_path)).create_view("profiles")
        self.connection.read_parquet(str(levels_path)).create_view("levels")

    def _rows(self, sql: str, values: list[Any]) -> list[dict[str, Any]]:
        if sql not in _TEMPLATES:
            raise ValueError("query must be a fixed store template")
        execute_fixed_template = self.connection.execute
        cursor = execute_fixed_template(sql, parameters=values)  # nosec B608
        return [dict(zip([item[0] for item in cursor.description], row, strict=True)) for row in cursor.fetchall()]

    @staticmethod
    def _geo_values(plan: QueryPlan) -> list[Any]:
        if plan.bbox is None or plan.start_date is None or plan.end_date is None:
            raise ValueError("geographic operation requires bounded geography and dates")
        west, south, east, north = plan.bbox
        return [west, east, south, north, plan.start_date, plan.end_date]

    def find_profiles(self, plan: QueryPlan) -> list[dict[str, Any]]:
        return self._rows(_FIND_SQL, [*self._geo_values(plan), *_qc_values(plan), plan.row_limit])

    def nearest_floats(self, plan: QueryPlan) -> list[dict[str, Any]]:
        west, south, east, north = plan.bbox or (0, 0, 0, 0)
        center_lon, center_lat = (west + east) / 2, (south + north) / 2
        return self._rows(_NEAREST_SQL, [center_lat, center_lat, center_lon, center_lon, *self._geo_values(plan), *_qc_values(plan), plan.row_limit])

    def count_candidates(self, plan: QueryPlan) -> int:
        rows = self._rows(_GEO_COUNT_SQL, self._geo_values(plan))
        return int(rows[0]["row_count"])

    def count_qc_eligible(self, plan: QueryPlan) -> int:
        rows = self._rows(_GEO_ELIGIBLE_SQL, [*self._geo_values(plan), *_qc_values(plan)])
        return int(rows[0]["row_count"])

    def get_profile(self, wmo: str, cycle: int, plan: QueryPlan | QcPolicy) -> list[dict[str, Any]]:
        return self._rows(_PROFILE_SQL, [wmo, cycle, *_qc_values(plan)])

    def count_profile_candidates(self, wmo: str, cycle: int) -> int:
        return int(self._rows(_PROFILE_COUNT_SQL, [wmo, cycle])[0]["row_count"])

    @staticmethod
    def _selected(ids: list[ProfileIdentifier] | set[tuple[str, int, int]]) -> list[dict[str, Any]]:
        if isinstance(ids, set):
            return [{"wmo": w, "cycle": c, "source_profile_index": i} for w, c, i in ids]
        return [{"wmo": item.wmo, "cycle": item.cycle, "source_profile_index": item.source_profile_index} for item in ids if item.source_profile_index is not None]

    def compare_profiles(self, ids: list[ProfileIdentifier], plan: QueryPlan) -> list[dict[str, Any]]:
        return self._rows(_SELECTED_SQL, [self._selected(ids), *_qc_values(plan)])

    def count_selected_candidates(self, plan: QueryPlan, identities: set[tuple[str, int, int]]) -> int:
        return int(self._rows(_SELECTED_COUNT_SQL, [self._selected(identities)])[0]["row_count"]) if identities else 0

    def count_selected_qc_eligible(self, plan: QueryPlan, identities: set[tuple[str, int, int]]) -> int:
        return int(self._rows(_SELECTED_ELIGIBLE_SQL, [self._selected(identities), *_qc_values(plan)])[0]["row_count"]) if identities else 0
