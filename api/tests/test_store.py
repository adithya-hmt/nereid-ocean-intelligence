# ruff: noqa: I001
# pyright: reportMissingImports=false
from pathlib import Path

import pytest

from nereid_api.models import ProfileIdentifier, QcPolicy, QueryPlan
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
    assert {row["pressure_adjusted_qc"] for row in research_rows} == {1}
    assert all(row["pressure_adjusted_qc"] not in {3, 4} for row in exploratory_rows)
    assert {row["temperature_adjusted_qc"] for row in exploratory_rows} == {1, 2}
    assert all(row["temperature_adjusted_qc"] not in {3, 4} for row in exploratory_rows)
    assert all(row["salinity_adjusted_qc"] not in {3, 4} for row in exploratory_rows)


def test_committed_snapshot_keeps_each_source_representation_separate():
    snapshot = Path(__file__).parents[2] / "data/snapshots/indian-ocean-2023-03"
    rows = ArgoStore(snapshot).get_profile("2902388", 274, QcPolicy.RESEARCH)

    assert {row["source_profile_index"] for row in rows} == {0, 1}
    assert len({row["vertical_sampling_scheme"] for row in rows}) == 2
    assert all(row["temperature_adjusted_qc"] not in {3, 4} for row in rows)


def test_store_joins_valid_multi_file_snapshot_provenance_one_to_one(snapshot_dir):
    store = ArgoStore(snapshot_dir)

    rows = store.find_profiles(_plan(qc_mode="exploratory"))

    expected = {
        ("1900001", 7, 0): ("a" * 64, "https://example.test/a.nc"),
        ("1900002", 8, 0): ("b" * 64, "https://example.test/b.nc"),
    }
    for row in rows:
        assert (row["source_sha256"], row["source_url"]) == expected[
            (row["wmo"], row["cycle"], row["source_profile_index"])
        ]


def test_find_profiles_filters_all_scientific_variables_even_when_unrequested(
    snapshot_dir,
):
    store = ArgoStore(snapshot_dir)

    rows = store.find_profiles(_plan(parameters=[]))

    assert {row["temperature_adjusted_qc"] for row in rows} == {1}
    assert {row["salinity_adjusted_qc"] for row in rows} == {1}


def test_find_profiles_applies_date_filter_with_matching_bbox(snapshot_dir):
    store = ArgoStore(snapshot_dir)

    rows = store.find_profiles(_plan(start_date="2023-04-01", end_date="2023-04-30"))

    assert rows == []


def test_selected_candidate_counts_are_bounded_and_ignore_pagination(snapshot_dir):
    store = ArgoStore(snapshot_dir)
    plan = _plan(row_limit=1)
    identities = {("1900001", 7, "A", 0)}

    assert store.count_selected_candidates(plan, identities) == 6
    assert store.count_selected_qc_eligible(plan, identities) == 2


def test_get_profile_and_compare_profiles_apply_qc_policy(snapshot_dir):
    store = ArgoStore(snapshot_dir)

    research_rows = store.get_profile("1900001", 7, QcPolicy.RESEARCH)
    comparison_rows = store.compare_profiles(
        [ProfileIdentifier(wmo="1900001", cycle=7, direction="A", source_profile_index=0), ProfileIdentifier(wmo="1900002", cycle=8, direction="A", source_profile_index=0)], _plan(qc_mode="exploratory")
    )

    assert {row["wmo"] for row in research_rows} == {"1900001"}
    assert {row["temperature_adjusted_qc"] for row in research_rows} == {1}
    assert {row["wmo"] for row in comparison_rows} == {"1900001", "1900002"}
    assert {row["temperature_adjusted_qc"] for row in comparison_rows} == {1, 2}
