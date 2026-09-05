# pyright: reportMissingImports=false
"""Optional, typed natural-language planning for bounded ARGO queries."""

from __future__ import annotations

import os
from typing import Any

from openai import APITimeoutError, AsyncAzureOpenAI
from pydantic import ValidationError

from nereid_api.models import QueryPlan


class PlannerUnavailable(Exception):
    """Raised when the optional text planner cannot safely produce a plan."""


class ExplicitPlanner:
    """Preserve user-supplied, already validated filter controls."""

    def plan(self, filters: QueryPlan) -> QueryPlan:
        return filters


class AzurePlanner:
    """Use Azure structured output only to propose a locally validated QueryPlan."""

    def __init__(self, client: Any, deployment: str) -> None:
        self._client = client
        self._deployment = deployment

    async def plan(self, question: str) -> QueryPlan:
        try:
            completion = await self._client.chat.completions.parse(
                model=self._deployment,
                response_format=QueryPlan,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Translate the user's question into exactly one QueryPlan. "
                            "Allowed operations: find_profiles, nearest_floats, get_profile, "
                            "compare_profiles, derive_section, export_selection. Allowed parameters: "
                            "TEMP, PSAL, PRES. Allowed QC modes: research, exploratory. Use only these "
                            "values and the QueryPlan row limits. Every geographic query must include a "
                            "bounded bbox and start and end dates; profile queries must include WMO and "
                            "cycle. Do not produce SQL, analytics, measurements, conclusions, or scientific claims."
                        ),
                    },
                    {"role": "user", "content": question},
                ],
            )
        except (APITimeoutError, TimeoutError) as error:
            raise PlannerUnavailable("AI interpretation timed out; use explicit filters.") from error
        except Exception as error:
            raise PlannerUnavailable("AI interpretation is unavailable; use explicit filters.") from error

        message = completion.choices[0].message if completion.choices else None
        parsed = message.parsed if message else None
        if message is None or message.refusal or parsed is None:
            raise PlannerUnavailable("AI interpretation is unavailable; use explicit filters.")
        try:
            return QueryPlan.model_validate(parsed)
        except ValidationError as error:
            raise PlannerUnavailable(
                "AI interpretation unavailable—filters still work. Use explicit filters."
            ) from error


def azure_planner_from_environment() -> AzurePlanner | None:
    """Create an Azure client only when its complete configuration is present."""
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    api_version = os.getenv("OPENAI_API_VERSION")
    if not endpoint or not api_key or not deployment or not api_version:
        return None
    client = AsyncAzureOpenAI(
        azure_endpoint=endpoint,
        api_version=api_version,
        api_key=api_key,
        timeout=15.0,
        max_retries=1,
    )
    return AzurePlanner(client, deployment)
