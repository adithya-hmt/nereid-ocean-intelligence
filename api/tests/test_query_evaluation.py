import asyncio
import importlib.util
import json
import re
from pathlib import Path

from nereid_api.models import QueryPlan
from nereid_api.planner import PlannerRejected

spec = importlib.util.spec_from_file_location("evaluate_queries", Path(__file__).parents[2] / "docs/evidence/evaluate_queries.py")
if spec is None or spec.loader is None:
    raise RuntimeError("unable to load query evaluator")
evaluate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluate)


class FakePlanner:
    async def plan(self, question):
        if question == "reject":
            raise PlannerRejected("rejected")
        return QueryPlan(operation="get_profile", wmo="1902202", cycle=161, direction="A")


def test_score_compares_every_expected_filter_and_rejections():
    cases = [{"question": "good", "expected": {"operation": "get_profile", "wmo": "1902202", "cycle": 161, "direction": "A"}}, {"question": "reject", "expected": "rejection"}, {"question": "good", "expected": {"operation": "get_profile", "wmo": "other", "cycle": 161, "direction": "A"}}]
    assert asyncio.run(evaluate.score(FakePlanner(), cases)) == (2, 3)


def _contains_selector(question: str, selector: str) -> bool:
    return bool(re.search(rf"(?<![A-Z0-9]){re.escape(selector)}(?![A-Z0-9])", question, re.IGNORECASE))


def test_checked_in_allowed_cases_are_self_describing_and_construct_typed_plans():
    cases = json.loads((Path(__file__).parents[2] / "docs/evidence/query-cases.json").read_text())
    allowed = [case for case in cases if case["expected"] != "rejection"]
    assert len(cases) == 30
    assert len(allowed) == 25
    assert sum(case["expected"] == "rejection" for case in cases) == 5

    plans = [QueryPlan.model_validate(case["expected"]) for case in allowed]
    parameter_markers = {
        "TEMP": ("TEMP", "temperature"),
        "PSAL": ("PSAL", "salinity"),
        "PRES": ("PRES", "pressure"),
    }
    operation_markers = {
        "find_profiles": ("find", "search", "list", "show"),
        "nearest_floats": ("nearest",),
        "get_profile": ("get", "retrieve", "open", "inspect"),
        "compare_profiles": ("compare",),
        "derive_section": ("derive",),
    }

    for case, plan in zip(allowed, plans, strict=True):
        question = case["question"]
        assert any(_contains_selector(question, marker) for marker in operation_markers[plan.operation])
        for parameter in plan.parameters:
            assert all(_contains_selector(question, marker) for marker in parameter_markers[parameter])
        qc_marker = "research QC1" if plan.qc_mode == "research" else "exploratory QC1-2"
        assert _contains_selector(question, qc_marker)

        if plan.operation in {"find_profiles", "nearest_floats"}:
            assert plan.bbox is not None and plan.start_date is not None and plan.end_date is not None
            assert _contains_selector(question, "bbox")
            assert all(_contains_selector(question, f"{value:g}") for value in plan.bbox)
            assert _contains_selector(question, plan.start_date.isoformat())
            assert _contains_selector(question, plan.end_date.isoformat())
        if plan.operation == "nearest_floats":
            assert plan.float_count is not None
            assert re.search(rf"nearest\s+{plan.float_count}\s+floats", question, re.IGNORECASE)
        if plan.operation == "get_profile":
            assert plan.wmo is not None and plan.cycle is not None and plan.direction is not None
            assert _contains_selector(question, "WMO") and _contains_selector(question, plan.wmo)
            assert _contains_selector(question, "cycle") and _contains_selector(question, str(plan.cycle))
            assert _contains_selector(question, f"direction {plan.direction}")
        if plan.operation in {"compare_profiles", "derive_section"}:
            for profile_id in plan.profile_ids:
                assert _contains_selector(question, "WMO") and _contains_selector(question, profile_id.wmo)
                assert _contains_selector(question, "cycle") and _contains_selector(question, str(profile_id.cycle))
                assert _contains_selector(question, f"direction {profile_id.direction}")
                assert _contains_selector(question, f"source profile index {profile_id.source_profile_index}")

    assert all(evaluate.matches(plan, case["expected"]) for case, plan in zip(allowed, plans, strict=True))
    expected = next(case["expected"] for case in allowed if case["expected"]["operation"] == "compare_profiles")
    plan = QueryPlan.model_validate(expected)
    assert evaluate.matches(plan, expected)
    wrong_direction = {**expected, "profile_ids": [{**expected["profile_ids"][0], "direction": "D"}, expected["profile_ids"][1]]}
    assert not evaluate.matches(plan, wrong_direction)
