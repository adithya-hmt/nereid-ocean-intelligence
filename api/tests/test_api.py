# pyright: reportMissingImports=false
from fastapi.testclient import TestClient
from nereid_api.main import create_app


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
    assert response.json()["warnings"] == ["No matching profiles; widen one bounded filter."]


def test_section_masks_unsupported_gap(snapshot_dir):
    client = TestClient(create_app(snapshot_dir))
    response = client.post(
        "/v1/sections/derive",
        json={
            "profile_ids": [["1900001", 7], ["1900002", 8]],
            "qc_mode": "exploratory",
            "max_time_gap_hours": 24,
            "max_distance_km": 100,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["observation_coordinates"]) == 2
    assert body["masked_gaps"] == [{"left_profile_index": 0, "right_profile_index": 1, "reason": "time_gap"}]
    assert all(cell["temperature"] is None for cell in body["section_cells"])


def test_missing_snapshot_returns_service_unavailable(tmp_path):
    client = TestClient(create_app(tmp_path))

    response = client.get("/health")

    assert response.status_code == 503
