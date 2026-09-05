# ruff: noqa: I001
# pyright: reportMissingImports=false
import asyncio

import pytest

from nereid_api.models import QueryPlan
from nereid_api.planner import (
    AzurePlanner,
    ExplicitPlanner,
    PlannerRejected,
    PlannerUnavailable,
    azure_planner_from_environment,
)

VALID_PLAN = {
    "operation": "find_profiles",
    "bbox": [60, 0, 80, 20],
    "start_date": "2023-03-01",
    "end_date": "2023-03-31",
    "parameters": ["TEMP", "PSAL"],
}


class FakeCompletions:
    def __init__(self, result: object = None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[dict[str, object]] = []

    async def parse(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.result


class FakeClient:
    def __init__(self, completions: FakeCompletions) -> None:
        self.chat = type("Chat", (), {"completions": completions})()


class FakeMessage:
    def __init__(self, parsed: object = None, refusal: str | None = None) -> None:
        self.parsed = parsed
        self.refusal = refusal


class FakeResponse:
    def __init__(self, message: FakeMessage) -> None:
        self.choices = [type("Choice", (), {"message": message})()]


def test_explicit_planner_passes_through_validated_filters():
    plan = QueryPlan.model_validate(VALID_PLAN)

    assert ExplicitPlanner().plan(plan) is plan


def test_azure_planner_rejects_unbounded_model_response():
    client = FakeClient(FakeCompletions(FakeResponse(FakeMessage(parsed={"operation": "find_profiles"}))))

    with pytest.raises(PlannerRejected, match="filters still work"):
        asyncio.run(AzurePlanner(client, "deployment").plan("find profiles"))


def test_azure_planner_rejects_refusal_or_missing_parsed_output():
    for message in (FakeMessage(refusal="I cannot help"), FakeMessage()):
        client = FakeClient(FakeCompletions(FakeResponse(message)))
        with pytest.raises(PlannerRejected):
            asyncio.run(AzurePlanner(client, "deployment").plan("find profiles"))


def test_azure_planner_maps_timeout_to_unavailable():
    client = FakeClient(FakeCompletions(error=TimeoutError()))

    with pytest.raises(PlannerUnavailable, match="timed out"):
        asyncio.run(AzurePlanner(client, "deployment").plan("find profiles"))


def test_azure_planner_uses_typed_parsing_with_only_query_plan_output():
    completions = FakeCompletions(FakeResponse(FakeMessage(parsed=QueryPlan.model_validate(VALID_PLAN))))
    planner = AzurePlanner(FakeClient(completions), "deployment")

    assert asyncio.run(planner.plan("profiles near 10N")) == QueryPlan.model_validate(VALID_PLAN)
    call = completions.calls[0]
    assert call["model"] == "deployment"
    assert call["response_format"] is QueryPlan
    assert isinstance(call["messages"], list)
    assert len(call["messages"]) == 2
    assert "find_profiles, nearest_floats, get_profile, compare_profiles, derive_section" in call["messages"][0]["content"]
    assert "TEMP, PSAL, PRES" in call["messages"][0]["content"]
    assert "research, exploratory" in call["messages"][0]["content"]
    assert "get_profile queries must include WMO, cycle, and direction" in call["messages"][0]["content"]
    assert "each with WMO, cycle, direction, and source_profile_index" in call["messages"][0]["content"]


def test_azure_planner_is_absent_without_all_required_configuration(monkeypatch):
    for setting in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT", "OPENAI_API_VERSION"):
        monkeypatch.delenv(setting, raising=False)

    assert azure_planner_from_environment() is None
