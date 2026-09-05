import pytest
from pydantic import ValidationError

from nereid_api.models import QueryPlan


def test_query_plan_rejects_unbounded_request():
    with pytest.raises(ValidationError):
        QueryPlan(operation="find_profiles", row_limit=1000)


def test_query_plan_caps_rows():
    with pytest.raises(ValidationError):
        QueryPlan(
            operation="find_profiles",
            bbox=(60, 0, 80, 20),
            start_date="2023-03-01",
            end_date="2023-03-31",
            parameters=["TEMP", "PSAL"],
            qc_mode="research",
            row_limit=100001,
        )
