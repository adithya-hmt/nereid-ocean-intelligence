# pyright: reportMissingImports=false
"""Score configured Azure typed planning against the checked-in corpus."""
import asyncio
import json
import sys
from pathlib import Path
from typing import Protocol, cast

from nereid_api.models import QueryPlan
from nereid_api.planner import (
    PlannerRejected,
    PlannerUnavailable,
    azure_planner_from_environment,
)


class Planner(Protocol):
    async def plan(self, question: str) -> QueryPlan: ...

def matches(plan: QueryPlan, expected: dict[str, object]) -> bool:
    actual = plan.model_dump(mode="json")
    return all(actual.get(key) == value for key, value in expected.items())

async def score(planner: Planner, cases: list[dict[str, object]]) -> tuple[int, int]:
    correct = 0
    for case in cases:
        expected = case["expected"]
        try:
            plan = await planner.plan(str(case["question"]))
            correct += expected != "rejection" and matches(plan, cast(dict[str, object], expected))
        except PlannerRejected:
            correct += expected == "rejection"
        except PlannerUnavailable:
            raise
    return correct, len(cases)

async def main() -> int:
    cases = json.loads(Path(__file__).with_name("query-cases.json").read_text())
    if len(cases) != 30 or sum(case["expected"] == "rejection" for case in cases) != 5:
        raise ValueError("query corpus must contain 30 cases and five rejections")
    planner = azure_planner_from_environment()
    if planner is None:
        print("planner evaluation BLOCKED: Azure configuration unavailable; no score measured")
        return 2
    correct, total = await score(planner, cases)
    print(f"planner score: {correct}/{total}")
    return 0 if correct >= 27 else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
