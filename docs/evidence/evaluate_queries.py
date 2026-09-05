# pyright: reportMissingImports=false
"""Validate corpus shape only; Azure planner score is unmeasured without credentials."""
import json
from pathlib import Path

from nereid_api.models import QueryPlan

cases = json.loads((Path(__file__).with_name('query-cases.json')).read_text())
if len(cases) != 30 or sum(case["expected"] == "rejection" for case in cases) != 5:
    raise ValueError("query corpus must contain 30 cases and five rejections")
for case in cases:
    if case["expected"] != "rejection":
        QueryPlan.model_validate(case["expected"])
print('corpus: 30 cases; validator-valid: 25; rejection cases: 5; planner score: unmeasured (Azure configuration unavailable)')
