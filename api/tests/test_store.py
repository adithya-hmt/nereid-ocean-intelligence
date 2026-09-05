# ruff: noqa: I001
# pyright: reportMissingImports=false
import pytest

from nereid_api.models import QcPolicy, QueryPlan
from nereid_api.store import ArgoStore, SnapshotUnavailable


def _plan(**changes):
    values = {
        "operation": "find_profiles",
        "bbox": (60, 0, 80, 20),
        "start_date": "2023-03-01",
        "end_date": "2023-03-31",
        "parameters": ["TEMP", "PSAL"],
        "qc_mode": "research",
        "row_limit": 100,
    }
    values.update(changes)
    return QueryPlan(**values)


def test_store_requires_complete_snapshot(tmp_path):
    with pytest.raises(SnapshotUnavailable, match="profiles.parquet"):
        ArgoStore(tmp_path)


def test_find_profiles_applies_qc_bounds_and_limit(snapshot_dir):
    store = ArgoStore(snapshot_dir)

    research_rows = store.find_profiles(_plan(row_limit=2))
    exploratory_rows = store.find_profiles(_plan(qc_mode="exploratory"))

    assert len(research_rows) == 2
    assert {row["temperature_adjusted_qc"] for row in research_rows} == {1}
    assert {row["salinity_adjusted_qc"] for row in research_rows} == {1}
    assert {row["temperature_adjusted_qc"] for row in exploratory_rows} == {1, 2}
    assert all(row["temperature_adjusted_qc"] not in {3, 4} for row in exploratory_rows)
    assert all(row["salinity_adjusted_qc"] not in {3, 4} for row in exploratory_rows)


def test_get_profile_and_compare_profiles_apply_qc_policy(snapshot_dir):
    store = ArgoStore(snapshot_dir)

    research_rows = store.get_profile("1900001", 7, QcPolicy.RESEARCH)
    comparison_rows = store.compare_profiles(
        [("1900001", 7), ("1900002", 8)], QcPolicy.EXPLORATORY
    )

    assert {row["wmo"] for row in research_rows} == {"1900001"}
    assert {row["temperature_adjusted_qc"] for row in research_rows} == {1}
    assert {row["wmo"] for row in comparison_rows} == {"1900001", "1900002"}
    assert {row["temperature_adjusted_qc"] for row in comparison_rows} == {1, 2}
