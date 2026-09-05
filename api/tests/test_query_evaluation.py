import asyncio
import importlib.util
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
        return QueryPlan(operation="get_profile", wmo="1902202", cycle=161, direction='A')

def test_score_compares_every_expected_filter_and_rejections():
    cases = [{"question": "good", "expected": {"operation": "get_profile", "wmo": "1902202", "cycle": 161, "direction": "A"}}, {"question": "reject", "expected": "rejection"}, {"question": "good", "expected": {"operation": "get_profile", "wmo": "other", "cycle": 161, "direction": "A"}}]
    assert asyncio.run(evaluate.score(FakePlanner(), cases)) == (2, 3)


def test_checked_in_allowed_cases_construct_typed_plans_and_score_nested_direction_and_count():
    import json

    cases = json.loads((Path(__file__).parents[2] / "docs/evidence/query-cases.json").read_text())
    allowed = [case for case in cases if case["expected"] != "rejection"]
    assert len(allowed) == 25
    plans = [QueryPlan.model_validate(case["expected"]) for case in allowed]
    assert all(plan.operation != "nearest_floats" or plan.float_count is not None for plan in plans)
    assert all(item.direction == "A" for plan in plans for item in plan.profile_ids)
    expected = next(case["expected"] for case in allowed if case["expected"]["operation"] == "compare_profiles")
    plan = QueryPlan.model_validate(expected)
    assert evaluate.matches(plan, expected)
    wrong_direction = {**expected, "profile_ids": [{**expected["profile_ids"][0], "direction": "D"}, expected["profile_ids"][1]]}
    assert not evaluate.matches(plan, wrong_direction)
