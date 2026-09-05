# pyright: reportMissingImports=false
from fastapi.testclient import TestClient
from nereid_api.main import create_app
from nereid_api.planner import AzurePlanner


class FakeCompletions:
    async def parse(self, **kwargs: object) -> object:
        message = type("Message", (), {"parsed": {"operation": "find_profiles"}, "refusal": None})()
        return type("Response", (), {"choices": [type("Choice", (), {"message": message})()]})()


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
    assert body["qc_summary"] == {"retained": 2, "rejected": 6}
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
            "depth_step_m": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["query_plan"]["operation"] == "derive_section"
    assert body["provenance"]
    assert body["qc_summary"] == {"retained": 8, "rejected": 4}
    assert body["methods"]
    assert body["assumptions"]
    assert body["warnings"] == []
    assert body["section_request"] == {
        "profile_ids": [["1900001", 7], ["1900002", 8]],
        "qc_mode": "exploratory",
        "depth_step_m": 5,
        "max_time_gap_hours": 24,
        "max_distance_km": 100,
    }
    section = body["data"][0]
    assert len(section["observation_coordinates"]) == 2
    assert section["masked_gaps"] == [{"left_profile_index": 0, "right_profile_index": 1, "reason": "time_gap"}]
    assert all(cell["temperature"] is None for cell in section["section_cells"])


def test_text_planning_falls_back_to_explicit_filters_without_azure(monkeypatch, snapshot_dir):
    for setting in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT", "OPENAI_API_VERSION"):
        monkeypatch.delenv(setting, raising=False)
    client = TestClient(create_app(snapshot_dir))

    response = client.post("/v1/query/plan", json={"question": "Find profiles near 10N in March"})

    assert response.status_code == 200
    assert response.json() == {
        "plan": None,
        "planner": "explicit",
        "warnings": ["AI interpretation unavailable—filters still work. Use explicit filters."],
    }


def test_text_planning_invalid_model_plan_falls_back_to_explicit_filters(snapshot_dir):
    client = TestClient(create_app(snapshot_dir, text_planner=AzurePlanner(FakeClient(), "deployment")))

    response = client.post("/v1/query/plan", json={"question": "Find profiles"})

    assert response.status_code == 200
    assert response.json() == {
        "plan": None,
        "planner": "explicit",
        "warnings": ["AI interpretation unavailable—filters still work. Use explicit filters."],
    }


def test_missing_snapshot_returns_service_unavailable(tmp_path):
    client = TestClient(create_app(tmp_path))

    response = client.get("/health")

    assert response.status_code == 503
