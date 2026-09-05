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
