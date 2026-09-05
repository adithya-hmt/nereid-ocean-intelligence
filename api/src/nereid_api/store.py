# pyright: reportMissingImports=false
"""Read-only, parameterized DuckDB access to a normalized ARGO snapshot."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from nereid_api.models import QcPolicy, QueryPlan


class SnapshotUnavailable(FileNotFoundError):
    """Raised when a required local snapshot table is unavailable."""


_FIND_SQL = """
    SELECT l.*, p.latitude, p.longitude, p.timestamp, p.source_url,
           p.snapshot_doi, p.fetched_at
    FROM levels AS l
    INNER JOIN profiles AS p USING (wmo, cycle, direction, source_profile_index)
    WHERE p.longitude BETWEEN ? AND ?
      AND p.latitude BETWEEN ? AND ?
      AND CAST(p.timestamp AS DATE) BETWEEN ? AND ?
      AND (l.pressure_adjusted_qc = 1 OR (? AND l.pressure_adjusted_qc = 2))
      AND (l.temperature_adjusted_qc = 1 OR (? AND l.temperature_adjusted_qc = 2))
      AND (l.salinity_adjusted_qc = 1 OR (? AND l.salinity_adjusted_qc = 2))
    ORDER BY p.timestamp, l.wmo, l.cycle, l.pressure_dbar
    LIMIT ?
"""

_PROFILE_SQL = """
    SELECT l.*, p.latitude, p.longitude, p.timestamp, p.source_url,
           p.snapshot_doi, p.fetched_at
    FROM levels AS l
    INNER JOIN profiles AS p USING (wmo, cycle, direction, source_profile_index)
    WHERE l.wmo = ? AND l.cycle = ?
      AND (l.pressure_adjusted_qc = 1 OR (? AND l.pressure_adjusted_qc = 2))
      AND (l.temperature_adjusted_qc = 1 OR (? AND l.temperature_adjusted_qc = 2))
      AND (l.salinity_adjusted_qc = 1 OR (? AND l.salinity_adjusted_qc = 2))
    ORDER BY p.timestamp, l.pressure_dbar
"""

_CANDIDATE_COUNT_SQL = """
    SELECT count(*) AS row_count FROM levels AS l
    INNER JOIN profiles AS p USING (wmo, cycle, direction, source_profile_index)
    WHERE p.longitude BETWEEN ? AND ?
      AND p.latitude BETWEEN ? AND ?
      AND CAST(p.timestamp AS DATE) BETWEEN ? AND ?
"""

_ELIGIBLE_COUNT_SQL = """
    SELECT count(*) AS row_count FROM levels AS l
    INNER JOIN profiles AS p USING (wmo, cycle, direction, source_profile_index)
    WHERE p.longitude BETWEEN ? AND ?
      AND p.latitude BETWEEN ? AND ?
      AND CAST(p.timestamp AS DATE) BETWEEN ? AND ?
      AND (l.pressure_adjusted_qc = 1 OR (? AND l.pressure_adjusted_qc = 2))
      AND (l.temperature_adjusted_qc = 1 OR (? AND l.temperature_adjusted_qc = 2))
      AND (l.salinity_adjusted_qc = 1 OR (? AND l.salinity_adjusted_qc = 2))
"""

_PROFILE_CANDIDATE_COUNT_SQL = """
    SELECT count(*) AS row_count FROM levels
    WHERE wmo = ? AND cycle = ?
"""

_SELECTED_CANDIDATE_COUNT_SQL = """
    SELECT count(*) AS row_count FROM levels AS l
    WHERE list_contains(?, struct_pack(
          wmo := l.wmo,
          cycle := l.cycle,
          source_profile_index := l.source_profile_index
      ))
"""

_SELECTED_ELIGIBLE_COUNT_SQL = _SELECTED_CANDIDATE_COUNT_SQL + """
      AND (l.pressure_adjusted_qc = 1 OR (? AND l.pressure_adjusted_qc = 2))
      AND (l.temperature_adjusted_qc = 1 OR (? AND l.temperature_adjusted_qc = 2))
      AND (l.salinity_adjusted_qc = 1 OR (? AND l.salinity_adjusted_qc = 2))
"""


def _qc_values(policy: QcPolicy) -> list[bool]:
    exploratory = policy is QcPolicy.EXPLORATORY
    return [exploratory, exploratory, exploratory]


class ArgoStore:
    """A bounded read-only view over one local normalized snapshot."""

    def __init__(self, snapshot_dir: Path):
        self.snapshot_dir = Path(snapshot_dir)
        profiles_path = self.snapshot_dir / "profiles.parquet"
        levels_path = self.snapshot_dir / "levels.parquet"
        missing = [str(path) for path in (profiles_path, levels_path) if not path.is_file()]
        if missing:
            raise SnapshotUnavailable("snapshot requires " + ", ".join(missing))

        self.connection = duckdb.connect(":memory:")
        self.connection.read_parquet(str(profiles_path)).create_view("profiles")
        self.connection.read_parquet(str(levels_path)).create_view("levels")

    def _rows(self, sql: str, values: list[Any]) -> list[dict[str, Any]]:
        if sql not in {_FIND_SQL, _PROFILE_SQL, _CANDIDATE_COUNT_SQL, _ELIGIBLE_COUNT_SQL, _PROFILE_CANDIDATE_COUNT_SQL, _SELECTED_CANDIDATE_COUNT_SQL, _SELECTED_ELIGIBLE_COUNT_SQL}:
            raise ValueError("query must be a fixed store template")
        # `sql` is checked against the module's closed set of literal templates above;
        # all runtime values are passed separately to DuckDB's bound-parameter API.
        execute_fixed_template = self.connection.execute
        cursor = execute_fixed_template(sql, parameters=values)  # nosec B608
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

    def find_profiles(self, plan: QueryPlan) -> list[dict[str, Any]]:
        """Return policy-allowed levels within a bounded geographic and date window."""
        assert plan.bbox and plan.start_date and plan.end_date
        west, south, east, north = plan.bbox
        return self._rows(
            _FIND_SQL,
            [
                west,
                east,
                south,
                north,
                plan.start_date,
                plan.end_date,
                *_qc_values(plan.qc_mode),
                plan.row_limit,
            ],
        )

    def count_candidates(self, plan: QueryPlan) -> int:
        """Count unfiltered levels selected by a bounded plan for QC reporting."""
        assert plan.bbox and plan.start_date and plan.end_date
        west, south, east, north = plan.bbox
        result = self._rows(
            _CANDIDATE_COUNT_SQL,
            [west, east, south, north, plan.start_date, plan.end_date],
        )
        return int(result[0]["row_count"]) if result else 0

    def count_qc_eligible(self, plan: QueryPlan) -> int:
        """Count policy-allowed rows before pagination for an accurate QC summary."""
        assert plan.bbox and plan.start_date and plan.end_date
        west, south, east, north = plan.bbox
        result = self._rows(
            _ELIGIBLE_COUNT_SQL,
            [
                west,
                east,
                south,
                north,
                plan.start_date,
                plan.end_date,
                *_qc_values(plan.qc_mode),
            ],
        )
        return int(result[0]["row_count"]) if result else 0

    def count_selected_candidates(
        self, plan: QueryPlan, identities: set[tuple[str, int, int]]
    ) -> int:
        """Count unfiltered levels for server-validated selected representations."""
        if not identities:
            return 0
        selected = [
            {"wmo": wmo, "cycle": cycle, "source_profile_index": source_profile_index}
            for wmo, cycle, source_profile_index in identities
        ]
        result = self._rows(
            _SELECTED_CANDIDATE_COUNT_SQL,
            [selected],
        )
        return int(result[0]["row_count"]) if result else 0

    def count_selected_qc_eligible(
        self, plan: QueryPlan, identities: set[tuple[str, int, int]]
    ) -> int:
        """Count policy-allowed server-validated selected levels before pagination."""
        if not identities:
            return 0
        selected = [
            {"wmo": wmo, "cycle": cycle, "source_profile_index": source_profile_index}
            for wmo, cycle, source_profile_index in identities
        ]
        result = self._rows(
            _SELECTED_ELIGIBLE_COUNT_SQL,
            [
                selected, *_qc_values(plan.qc_mode),
            ],
        )
        return int(result[0]["row_count"]) if result else 0

    def count_profile_candidates(self, profile_ids: list[tuple[str, int]]) -> int:
        """Count unfiltered selected levels for section QC accounting."""
        return sum(
            int(result[0]["row_count"])
            for wmo, cycle in profile_ids
            if (result := self._rows(_PROFILE_CANDIDATE_COUNT_SQL, [wmo, cycle]))
        )

    def get_profile(self, wmo: str, cycle: int, qc_mode: QcPolicy) -> list[dict[str, Any]]:
        return self._rows(
            _PROFILE_SQL,
            [wmo, cycle, *_qc_values(qc_mode)],
        )

    def compare_profiles(
        self, profile_ids: list[tuple[str, int]], qc_mode: QcPolicy
    ) -> list[dict[str, Any]]:
        if not profile_ids:
            return []
        rows = [
            row
            for wmo, cycle in profile_ids
            for row in self.get_profile(wmo, cycle, qc_mode)
        ]
        return sorted(rows, key=lambda row: (row["timestamp"], row["wmo"], row["cycle"], row["pressure_dbar"]))
