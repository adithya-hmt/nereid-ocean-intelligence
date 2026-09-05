# ruff: noqa: I001
# pyright: reportMissingImports=false
import pytest
from fastapi.testclient import TestClient

from nereid_api.main import create_app
from nereid_api.planner import AzurePlanner


class FakeCompletions:
    async def parse(self, **kwargs: object) -> object:
        message = type(
            "Message", (), {"parsed": {"operation": "find_profiles"}, "refusal": None}
        )()
        return type(
            "Response", (), {"choices": [type("Choice", (), {"message": message})()]}
        )()


class FakeClient:
    def __init__(self) -> None:
        self.chat = type("Chat", (), {"completions": FakeCompletions()})()


def test_execute_returns_scientific_receipt(snapshot_dir):
    client = TestClient(create_app(snapshot_dir))
    response = client.post(
        "/v1/query/execute",
        json={
            "operation": "find_profiles",
            "bbox": [60, 0, 80, 20],
            "start_date": "2023-03-01",
            "end_date": "2023-03-31",
            "parameters": ["TEMP", "PSAL"],
            "qc_mode": "research",
            "row_limit": 10000,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provenance"][0]["sha256"]
    assert body["qc_summary"]["rejected"] >= 1
    assert body["methods"]
    assert body["warnings"] == []


def test_api_preserves_one_to_one_provenance_for_multi_file_snapshot(snapshot_dir):
    client = TestClient(create_app(snapshot_dir))
    response = client.post(
        "/v1/query/execute",
        json={
            "operation": "find_profiles",
            "bbox": [60, 0, 80, 20],
            "start_date": "2023-03-01",
            "end_date": "2023-03-31",
            "parameters": ["TEMP", "PSAL"],
            "qc_mode": "exploratory",
        },
    )

    assert response.status_code == 200
    expected_urls = {
        "1900001": "https://example.test/a.nc",
        "1900002": "https://example.test/b.nc",
    }
    rows = response.json()["data"]
    assert {row["wmo"] for row in rows} == set(expected_urls)
    assert all(row["source_url"] == expected_urls[row["wmo"]] for row in rows)


def test_empty_result_is_a_successful_widening_suggestion(snapshot_dir):
    client = TestClient(create_app(snapshot_dir))
    response = client.post(
        "/v1/query/execute",
        json={
            "operation": "find_profiles",
            "bbox": [0, 0, 1, 1],
            "start_date": "2023-03-01",
            "end_date": "2023-03-31",
            "parameters": ["TEMP"],
        },
    )

    assert response.status_code == 200
    assert response.json()["warnings"] == [
        "No matching profiles; widen one bounded filter."
    ]


def test_paginated_result_reports_only_qc_rejections(snapshot_dir):
    client = TestClient(create_app(snapshot_dir))
    response = client.post(
        "/v1/query/execute",
        json={
            "operation": "find_profiles",
            "bbox": [60, 0, 80, 20],
            "start_date": "2023-03-01",
            "end_date": "2023-03-31",
            "parameters": ["TEMP", "PSAL"],
            "qc_mode": "research",
            "row_limit": 2,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["qc_summary"] == {"retained": 2, "rejected": 8}
    assert body["warnings"] == ["Results truncated to the requested row limit."]


def test_same_bbox_with_excluding_dates_returns_no_match(snapshot_dir):
    client = TestClient(create_app(snapshot_dir))
    response = client.post(
        "/v1/query/execute",
        json={
            "operation": "find_profiles",
            "bbox": [60, 0, 80, 20],
            "start_date": "2023-04-01",
            "end_date": "2023-04-30",
            "parameters": ["TEMP", "PSAL"],
        },
    )

    assert response.status_code == 200
    assert response.json()["warnings"] == [
        "No matching profiles; widen one bounded filter."
    ]


def test_section_masks_unsupported_gap(snapshot_dir):
    client = TestClient(create_app(snapshot_dir))
    response = client.post(
        "/v1/sections/derive",
        json={
            "profile_ids": [{"wmo": "1900001", "cycle": 7, "source_profile_index": 0, "direction": "A"}, {"wmo": "1900002", "cycle": 8, "source_profile_index": 0, "direction": "A"}],
            "qc_mode": "exploratory",
            "max_time_gap_hours": 24,
            "max_distance_km": 100,
            "depth_step_m": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query_plan"]["operation"] == "derive_section"
    assert body["provenance"]
    assert body["qc_summary"] == {"retained": 6, "rejected": 6}
    assert body["methods"]
    assert body["assumptions"]
    assert body["warnings"] == []
    assert body["section_request"] == {
        "profile_ids": [{"wmo": "1900001", "cycle": 7, "source_profile_index": 0, "direction": "A"}, {"wmo": "1900002", "cycle": 8, "source_profile_index": 0, "direction": "A"}],
        "qc_mode": "exploratory",
        "depth_step_m": 5,
        "max_time_gap_hours": 24,
        "max_distance_km": 100,
        "max_vertical_gap_m": 100.0,
    }
    section = body["data"][0]
    assert len(section["observation_coordinates"]) == 2
    assert section["masked_gaps"] == [
        {"left_profile_index": 0, "right_profile_index": 1, "reason": "time_gap"}
    ]
    assert all(cell["temperature"] is None for cell in section["section_cells"])


def test_text_planning_falls_back_to_explicit_filters_without_azure(
    monkeypatch, snapshot_dir
):
    for setting in (
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT",
        "OPENAI_API_VERSION",
    ):
        monkeypatch.delenv(setting, raising=False)
    client = TestClient(create_app(snapshot_dir))

    response = client.post(
        "/v1/query/plan", json={"question": "Find profiles near 10N in March"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "plan": None,
        "planner": "explicit",
        "warnings": [
            "AI interpretation unavailable—filters still work. Use explicit filters."
        ],
    }


def test_text_planning_invalid_model_plan_falls_back_to_explicit_filters(snapshot_dir):
    client = TestClient(
        create_app(snapshot_dir, text_planner=AzurePlanner(FakeClient(), "deployment"))
    )

    response = client.post("/v1/query/plan", json={"question": "Find profiles"})

    assert response.status_code == 200
    assert response.json() == {
        "plan": None,
        "planner": "explicit",
        "warnings": [
            "AI interpretation unavailable—filters still work. Use explicit filters."
        ],
    }


def test_missing_snapshot_returns_service_unavailable(tmp_path):
    client = TestClient(create_app(tmp_path))

    response = client.get("/health")

    assert response.status_code == 503

@pytest.mark.parametrize("operation", ["nearest_floats", "compare_profiles", "derive_section"])
def test_execute_dispatches_every_advertised_operation(snapshot_dir, operation):
    client = TestClient(create_app(snapshot_dir))
    if operation == "nearest_floats":
        payload = {"operation": operation, "bbox": [60, 0, 80, 20], "start_date": "2023-03-01", "end_date": "2023-03-31", "parameters": ["TEMP"], "row_limit": 10, "float_count": 1}
    else:
        payload = {"operation": operation, "profile_ids": [{"wmo": "1900001", "cycle": 7, "source_profile_index": 0, "direction": "A"}, {"wmo": "1900002", "cycle": 8, "source_profile_index": 0, "direction": "A"}], "parameters": ["TEMP", "PSAL"]}
    response = client.post("/v1/query/execute", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["query_plan"]["operation"] == operation
    if operation == "derive_section":
        assert body["section_request"]["profile_ids"] == payload["profile_ids"]
        assert "section_cells" in body["data"][0]


def test_exact_comparison_refuses_missing_or_qc_empty_representation(snapshot_dir):
    client = TestClient(create_app(snapshot_dir))
    payload = {"operation": "compare_profiles", "profile_ids": [{"wmo": "1900001", "cycle": 7, "source_profile_index": 0, "direction": "A"}, {"wmo": "missing", "cycle": 8, "source_profile_index": 0, "direction": "A"}], "parameters": ["TEMP"]}
    response = client.post("/v1/query/execute", json=payload)
    assert response.status_code == 422
    assert "missing requested representation" in response.json()["detail"]


@pytest.mark.parametrize("parameters", [["TEMP"], ["PSAL"], ["PRES"], []])
def test_parameter_specific_qc_and_masking(snapshot_dir, parameters):
    client = TestClient(create_app(snapshot_dir))
    response = client.post("/v1/query/execute", json={"operation": "find_profiles", "bbox": [60, 0, 80, 20], "start_date": "2023-03-01", "end_date": "2023-03-31", "parameters": parameters, "qc_mode": "exploratory"})
    assert response.status_code == 200
    rows = response.json()["data"]
    if parameters in (["PRES"], []):
        assert all(row["pressure_adjusted_qc"] in {1, 2} for row in rows)
    else:
        assert all(row["pressure_adjusted_qc"] is None for row in rows)
        assert all(row["pressure_dbar"] is None for row in rows)
        assert all(row["adjusted_pressure_error"] is None for row in rows)
    if parameters == ["TEMP"]:
        assert all(row["temperature_adjusted_qc"] in {1, 2} for row in rows)
        assert all(row["salinity_adjusted"] is None for row in rows if row["salinity_adjusted_qc"] is None)
    if parameters == ["PSAL"]:
        assert all(row["salinity_adjusted_qc"] in {1, 2} for row in rows)
        assert all(row["temperature_adjusted"] is None for row in rows if row["temperature_adjusted_qc"] is None)

@pytest.mark.parametrize(
    "payload",
    [
        {"operation": "find_profiles", "bbox": [60, 0, 80, 20], "start_date": "2023-03-01", "end_date": "2023-03-31"},
        {"operation": "nearest_floats", "bbox": [60, 0, 80, 20], "start_date": "2023-03-01", "end_date": "2023-03-31", "float_count": 1},
        {"operation": "get_profile", "wmo": "1900001", "cycle": 7, "direction": "A"},
        {"operation": "compare_profiles", "profile_ids": [{"wmo": "1900001", "cycle": 7, "source_profile_index": 0, "direction": "A"}, {"wmo": "1900002", "cycle": 8, "source_profile_index": 0, "direction": "A"}]},
        {"operation": "derive_section", "profile_ids": [{"wmo": "1900001", "cycle": 7, "source_profile_index": 0, "direction": "A"}, {"wmo": "1900002", "cycle": 8, "source_profile_index": 0, "direction": "A"}]},
    ],
)
def test_operation_selector_matrix_accepts_each_valid_endpoint_form(snapshot_dir, payload):
    assert TestClient(create_app(snapshot_dir)).post("/v1/query/execute", json=payload).status_code == 200

@pytest.mark.parametrize("parameters", [["PRES"], ["TEMP"]])
def test_derive_uses_temp_and_salinity_research_policy_even_when_unrequested(snapshot_dir, parameters):
    import pyarrow as pa
    import pyarrow.parquet as pq

    levels_path = snapshot_dir / "levels.parquet"
    rows = pq.read_table(levels_path).to_pylist()
    for row in rows:
        row["pressure_adjusted_qc"] = 1
        row["temperature_adjusted_qc"] = 2
        row["salinity_adjusted_qc"] = 2
    pq.write_table(pa.Table.from_pylist(rows), levels_path)
    payload = {"operation": "derive_section", "profile_ids": [{"wmo": "1900001", "cycle": 7, "source_profile_index": 0, "direction": "A"}, {"wmo": "1900002", "cycle": 8, "source_profile_index": 0, "direction": "A"}], "parameters": parameters, "qc_mode": "research"}
    response = TestClient(create_app(snapshot_dir)).post("/v1/query/execute", json=payload)
    assert response.status_code == 422
    assert "insufficient or missing requested representation" in response.json()["detail"]


def test_temp_only_never_returns_ct_from_bad_salinity_qc(snapshot_dir):
    import pyarrow as pa
    import pyarrow.parquet as pq

    levels_path = snapshot_dir / "levels.parquet"
    rows = pq.read_table(levels_path).to_pylist()
    for row in rows:
        if row["wmo"] == "1900001" and row["pressure_dbar"] in {0, 10, 60}:
            row["salinity_adjusted_qc"] = 3
    pq.write_table(pa.Table.from_pylist(rows), levels_path)
    payload = {"operation": "find_profiles", "bbox": [60, 0, 80, 20], "start_date": "2023-03-01", "end_date": "2023-03-31", "parameters": ["TEMP"], "qc_mode": "research"}
    response = TestClient(create_app(snapshot_dir)).post("/v1/query/execute", json=payload)
    assert response.status_code == 200
    assert all(row["conservative_temperature"] is None for row in response.json()["data"] if row["wmo"] == "1900001")


@pytest.mark.parametrize("parameters", [["TEMP"], ["PSAL"], ["PRES"]])
def test_unrequested_variables_are_completely_masked(snapshot_dir, parameters):
    payload = {"operation": "find_profiles", "bbox": [60, 0, 80, 20], "start_date": "2023-03-01", "end_date": "2023-03-31", "parameters": parameters, "qc_mode": "exploratory"}
    rows = TestClient(create_app(snapshot_dir)).post("/v1/query/execute", json=payload).json()["data"]
    fields = {"TEMP": ["temperature_raw", "temperature_adjusted", "temperature_best", "temperature_qc", "temperature_adjusted_qc", "temperature_adjusted_error", "conservative_temperature"], "PSAL": ["salinity_raw", "salinity_adjusted", "salinity_best", "salinity_qc", "salinity_adjusted_qc", "salinity_adjusted_error", "absolute_salinity"], "PRES": ["pressure_raw", "pressure_adjusted", "pressure_best", "pressure_dbar", "pressure_qc", "pressure_adjusted_qc", "pressure_adjusted_error", "adjusted_pressure_error"]}
    for variable, variable_fields in fields.items():
        if variable != parameters[0]:
            assert all(row[field] is None for row in rows for field in variable_fields)


def test_requested_metric_gating_and_adjusted_error_warnings(snapshot_dir):
    import pyarrow as pa
    import pyarrow.parquet as pq

    levels_path = snapshot_dir / "levels.parquet"
    rows = pq.read_table(levels_path).to_pylist()
    rows[0]["temperature_adjusted_error"] = None
    pq.write_table(pa.Table.from_pylist(rows), levels_path)
    payload = {"operation": "find_profiles", "bbox": [60, 0, 80, 20], "start_date": "2023-03-01", "end_date": "2023-03-31", "parameters": ["PRES"], "qc_mode": "research"}
    body = TestClient(create_app(snapshot_dir)).post("/v1/query/execute", json=payload).json()
    assert body["chart_spec"] == [{"profile_metrics": []}]
    assert body["methods"][0]["parameters"]["adjusted_errors"]
    assert not any("TEMP" in warning for warning in body["warnings"])


@pytest.mark.parametrize("operation", ["get_profile", "nearest_floats"])
def test_output_operations_apply_row_limit(snapshot_dir, operation):
    payload = ({"operation": operation, "wmo": "1900001", "cycle": 7, "direction": "A", "parameters": ["TEMP"], "row_limit": 1} if operation == "get_profile" else {"operation": operation, "bbox": [60, 0, 80, 20], "start_date": "2023-03-01", "end_date": "2023-03-31", "parameters": ["TEMP"], "row_limit": 10, "float_count": 1})
    response = TestClient(create_app(snapshot_dir)).post("/v1/query/execute", json=payload)
    assert response.status_code == 200
    assert len(response.json()["data"]) == (1 if operation == "get_profile" else 2)


@pytest.mark.parametrize("operation", ["compare_profiles", "derive_section"])
def test_exact_operations_refuse_selection_above_row_limit(snapshot_dir, operation):
    payload = {"operation": operation, "profile_ids": [{"wmo": "1900001", "cycle": 7, "source_profile_index": 0, "direction": "A"}, {"wmo": "1900002", "cycle": 8, "source_profile_index": 0, "direction": "A"}], "parameters": ["TEMP", "PSAL"], "row_limit": 1}
    response = TestClient(create_app(snapshot_dir)).post("/v1/query/execute", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"] == "exact selection exceeds row_limit"


def test_export_rejects_derive_section_plan_before_indexing_section_data(snapshot_dir):
    plan = {"operation": "derive_section", "profile_ids": [{"wmo": "1900001", "cycle": 7, "source_profile_index": 0, "direction": "A"}, {"wmo": "1900002", "cycle": 8, "source_profile_index": 0, "direction": "A"}], "parameters": ["TEMP", "PSAL"]}
    response = TestClient(create_app(snapshot_dir)).post("/v1/export", json={"plan": plan, "selections": [{"wmo": "1900001", "cycle": 7, "source_profile_index": 0, "direction": "A"}]})
    assert response.status_code == 422
    assert response.json()["detail"] == "export_selection supports level-row query plans only"


def test_section_marks_rejected_native_middle_level_as_vertical_gap(snapshot_dir):
    """QC filtering must not make nonadjacent native levels interpolable."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    levels = pq.read_table(snapshot_dir / "levels.parquet").to_pylist()
    for row in levels:
        if row["level_index"] == 1:
            row["pressure_adjusted_qc"] = 4
    pq.write_table(pa.Table.from_pylist(levels), snapshot_dir / "levels.parquet")
    client = TestClient(create_app(snapshot_dir))
    response = client.post("/v1/sections/derive", json={
        "profile_ids": [{"wmo": "1900001", "cycle": 7, "direction": "A", "source_profile_index": 0}, {"wmo": "1900002", "cycle": 8, "direction": "A", "source_profile_index": 0}],
        "qc_mode": "research", "depth_step_m": 5, "max_vertical_gap_m": 100, "max_time_gap_hours": 500,
    })
    assert response.status_code == 200
    cell = next(cell for cell in response.json()["data"][0]["section_cells"] if cell["depth_m"] == 5)
    assert cell["temperature"] is None
    assert cell["salinity"] is None
    assert cell["mask_reason"] == "vertical_gap"


def test_section_prioritizes_vertical_gap_over_pair_time_gap(snapshot_dir):
    import pyarrow as pa
    import pyarrow.parquet as pq

    levels = pq.read_table(snapshot_dir / "levels.parquet").to_pylist()
    for row in levels:
        if row["level_index"] == 1:
            row["pressure_adjusted_qc"] = 4
    pq.write_table(pa.Table.from_pylist(levels), snapshot_dir / "levels.parquet")
    response = TestClient(create_app(snapshot_dir)).post("/v1/sections/derive", json={
        "profile_ids": [{"wmo": "1900001", "cycle": 7, "direction": "A", "source_profile_index": 0}, {"wmo": "1900002", "cycle": 8, "direction": "A", "source_profile_index": 0}],
        "qc_mode": "research", "depth_step_m": 5, "max_vertical_gap_m": 100, "max_time_gap_hours": 24,
    })

    assert response.status_code == 200
    section = response.json()["data"][0]
    assert section["masked_gaps"] == [
        {"left_profile_index": 0, "right_profile_index": 1, "reason": "time_gap"}
    ]
    cell = next(cell for cell in section["section_cells"] if cell["depth_m"] == 5)
    assert cell["mask_reason"] == "vertical_gap"


def test_exact_selection_keeps_ascending_and_descending_collision_distinct(snapshot_dir):
    """Direction is part of the source-local representation identity."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    profiles = pq.read_table(snapshot_dir / "profiles.parquet").to_pylist()
    descending_profile = {**profiles[0], "direction": "D"}
    pq.write_table(pa.Table.from_pylist([*profiles, descending_profile]), snapshot_dir / "profiles.parquet")
    levels = pq.read_table(snapshot_dir / "levels.parquet").to_pylist()
    pq.write_table(pa.Table.from_pylist([*levels, *[{**row, "direction": "D"} for row in levels if row["wmo"] == "1900001"]]), snapshot_dir / "levels.parquet")
    response = TestClient(create_app(snapshot_dir)).post("/v1/query/execute", json={
        "operation": "compare_profiles", "parameters": ["TEMP"], "row_limit": 100,
        "profile_ids": [{"wmo": "1900001", "cycle": 7, "direction": "A", "source_profile_index": 0}, {"wmo": "1900001", "cycle": 7, "direction": "D", "source_profile_index": 0}],
    })
    assert response.status_code == 200
    assert {row["direction"] for row in response.json()["data"]} == {"A", "D"}


def test_nearest_receipt_is_scoped_to_complete_selected_representations(snapshot_dir):
    response = TestClient(create_app(snapshot_dir)).post("/v1/query/execute", json={
        "operation": "nearest_floats", "bbox": [60, 0, 80, 20], "start_date": "2023-03-01", "end_date": "2023-03-31",
        "parameters": ["TEMP"], "qc_mode": "research", "float_count": 2, "row_limit": 10,
    })
    assert response.status_code == 200
    body = response.json()
    identities = {(row["wmo"], row["cycle"], row["direction"], row["source_profile_index"]) for row in body["data"]}
    assert len(identities) == 2
    assert body["qc_summary"] == {"retained": 4, "rejected": 8}
    assert "Results truncated to the requested row limit." not in body["warnings"]
    assert body["methods"][0]["parameters"]["float_count"] == 2


def test_nearest_fewer_available_is_truthful_and_overflow_refuses_without_partial_rows(snapshot_dir):
    client = TestClient(create_app(snapshot_dir))
    payload = {"operation": "nearest_floats", "bbox": [60, 0, 80, 20], "start_date": "2023-03-01", "end_date": "2023-03-31", "parameters": ["TEMP"], "qc_mode": "research", "float_count": 3, "row_limit": 10}
    response = client.post("/v1/query/execute", json=payload)
    assert response.status_code == 200
    assert len({row["wmo"] for row in response.json()["data"]}) == 2
    assert any("Only 2 QC-eligible representations" in warning for warning in response.json()["warnings"])
    payload["row_limit"] = 1
    overflow = client.post("/v1/query/execute", json=payload)
    assert overflow.status_code == 422
    assert overflow.json()["detail"] == "nearest representations exceed row_limit"


def test_adjusted_error_keys_distinguish_source_representations(snapshot_dir):
    import pyarrow as pa
    import pyarrow.parquet as pq

    profiles_path, levels_path = snapshot_dir / "profiles.parquet", snapshot_dir / "levels.parquet"
    profiles = pq.read_table(profiles_path).to_pylist()
    levels = pq.read_table(levels_path).to_pylist()
    duplicate_profile = {**profiles[0], "source_profile_index": 1}
    duplicate_levels = [{**row, "source_profile_index": 1} for row in levels if row["wmo"] == profiles[0]["wmo"]]
    pq.write_table(pa.Table.from_pylist([*profiles, duplicate_profile]), profiles_path)
    pq.write_table(pa.Table.from_pylist([*levels, *duplicate_levels]), levels_path)
    response = TestClient(create_app(snapshot_dir)).post("/v1/query/execute", json={"operation": "find_profiles", "bbox": [60, 0, 80, 20], "start_date": "2023-03-01", "end_date": "2023-03-31", "parameters": ["TEMP"]})
    errors = response.json()["methods"][0]["parameters"]["adjusted_errors"]
    assert "1900001/7/A/0:TEMP" in errors
    assert "1900001/7/A/1:TEMP" in errors


def test_requested_raw_pressure_qc_is_quarantined_in_api_and_export(snapshot_dir):
    import io
    import zipfile
    import pyarrow as pa
    import pyarrow.parquet as pq

    levels = pq.read_table(snapshot_dir / "levels.parquet").to_pylist()
    levels[0]["pressure_qc"] = 4
    levels[0]["pressure_adjusted_qc"] = 1
    pq.write_table(pa.Table.from_pylist(levels), snapshot_dir / "levels.parquet")
    client = TestClient(create_app(snapshot_dir))
    plan = {"operation": "get_profile", "wmo": "1900001", "cycle": 7, "direction": "A", "parameters": ["PRES"], "qc_mode": "research"}
    result = client.post("/v1/query/execute", json=plan)
    assert result.status_code == 200
    row = next(row for row in result.json()["data"] if row["level_index"] == 0)
    assert row["pressure_raw"] is None
    assert row["pressure_adjusted"] is not None and row["depth_m"] is not None
    exported = client.post("/v1/export", json={"plan": plan, "selections": [{"wmo": "1900001", "cycle": 7, "direction": "A", "source_profile_index": 0}]})
    assert exported.status_code == 200
    exported_rows = list(__import__("csv").DictReader(__import__("io").StringIO(zipfile.ZipFile(io.BytesIO(exported.content)).read("selection.csv").decode())))
    assert next(row for row in exported_rows if row["level_index"] == "0")["pressure_raw"] == ""


def test_interpolation_marks_outside_vertical_support_as_gap():
    from nereid_api.service import _interpolate

    assert _interpolate([], 0, "conservative_temperature", 20) == (None, "vertical_gap")
    assert _interpolate([{"depth_m": 10, "level_index": 0, "conservative_temperature": 1.0}], 0, "conservative_temperature", 20) == (None, "vertical_gap")


def test_raw_qc_mismatch_is_quarantined_in_api_and_export(snapshot_dir):
    import io
    import zipfile
    import pyarrow as pa
    import pyarrow.parquet as pq

    levels = pq.read_table(snapshot_dir / "levels.parquet").to_pylist()
    levels[0]["temperature_qc"] = 4
    levels[0]["temperature_adjusted_qc"] = 1
    pq.write_table(pa.Table.from_pylist(levels), snapshot_dir / "levels.parquet")
    client = TestClient(create_app(snapshot_dir))
    plan = {"operation": "get_profile", "wmo": "1900001", "cycle": 7, "direction": "A", "parameters": ["TEMP"], "qc_mode": "research"}
    result = client.post("/v1/query/execute", json=plan)
    assert result.status_code == 200
    row = next(row for row in result.json()["data"] if row["level_index"] == 0)
    assert row["temperature_raw"] is None
    assert row["conservative_temperature"] is not None
    exported = client.post("/v1/export", json={"plan": plan, "selections": [{"wmo": "1900001", "cycle": 7, "direction": "A", "source_profile_index": 0}]})
    assert exported.status_code == 200
    csv = zipfile.ZipFile(io.BytesIO(exported.content)).read("selection.csv").decode()
    assert ",," in csv or ",\n" in csv
    assert "28.0" not in csv
