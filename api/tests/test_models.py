# pyright: reportMissingImports=false
# ruff: noqa: I001
import pytest

from nereid_api.models import DerivedObservationSeries, ProfileSeries, QueryPlan, SectionRequest


def test_query_plan_rejects_unbounded_request():
    with pytest.raises(ValueError):
        QueryPlan(operation="find_profiles", row_limit=1000)


def test_profile_requires_source_record_arrays_to_align_with_depths():
    observations = DerivedObservationSeries(
        values=[10.0, 9.0], adjusted_qc=[1, 1], adjusted_errors=[0.1, 0.1]
    )
    with pytest.raises(ValueError, match="align with depth_m"):
        ProfileSeries(
            wmo="1234567",
            cycle=1,
            depth_m=[0.0, 10.0, 20.0],
            latitude=10.0,
            longitude=20.0,
            timestamp="2023-03-01T00:00:00Z",
            data_mode="D",
            conservative_temperature=observations,
            absolute_salinity=observations,
            pressure_adjusted_qc=[1, 1, 1],
            pressure_adjusted_errors=[0.1, 0.1, 0.1],
        )


def test_section_parameters_are_canonical_and_exclude_pressure():
    identifiers = [
        {"wmo": "a", "cycle": 1, "direction": "A", "source_profile_index": 0},
        {"wmo": "b", "cycle": 1, "direction": "A", "source_profile_index": 0},
    ]
    assert SectionRequest(profile_ids=identifiers, parameters=[]).parameters == ["TEMP", "PSAL"]
    assert SectionRequest(profile_ids=identifiers, parameters=["TEMP"]).parameters == ["TEMP"]
    assert SectionRequest(profile_ids=identifiers, parameters=["PSAL"]).parameters == ["PSAL"]
    with pytest.raises(ValueError):
        QueryPlan(operation="derive_section", profile_ids=identifiers, parameters=["PRES"])


def test_query_plan_caps_rows():
    with pytest.raises(ValueError):
        QueryPlan(
            operation="find_profiles",
            bbox=(60, 0, 80, 20),
            start_date="2023-03-01",
            end_date="2023-03-31",
            parameters=["TEMP", "PSAL"],
            qc_mode="research",
            row_limit=100001,
        )

@pytest.mark.parametrize(
    "values",
    [
        {"operation": "find_profiles", "wmo": "1900001", "cycle": 7},
        {"operation": "get_profile", "bbox": [60, 0, 80, 20], "start_date": "2023-03-01", "end_date": "2023-03-31"},
        {"operation": "compare_profiles", "profile_ids": [{"wmo": "a", "cycle": 1, "source_profile_index": 0, "direction": "A"}]},
        {"operation": "derive_section", "profile_ids": [{"wmo": "a", "cycle": 1, "source_profile_index": 0, "direction": "A"}, {"wmo": "a", "cycle": 1, "source_profile_index": 0, "direction": "A"}]},
    ],
)
def test_operation_selector_matrix_rejects_incompatible_or_incomplete_selectors(values):
    with pytest.raises(ValueError):
        QueryPlan(**values)
