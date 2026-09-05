# pyright: reportMissingImports=false
"""FastAPI entry points for bounded local ARGO investigations."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from nereid_api.models import QcPolicy, QueryPlan, ResultEnvelope, SectionRequest
from nereid_api.planner import (
    AzurePlanner,
    PlannerUnavailable,
    azure_planner_from_environment,
)
from nereid_api.service import InvestigationService
from nereid_api.store import ArgoStore, SnapshotUnavailable


class PlanRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2_000)


class PlanResponse(BaseModel):
    plan: QueryPlan | None
    planner: Literal["azure", "explicit"]
    warnings: list[str]


def create_app(
    snapshot_dir: Path,
    web_origin: str | None = None,
    text_planner: AzurePlanner | None = None,
) -> FastAPI:
    """Create an app backed by one local snapshot without opening network access."""
    app = FastAPI(title="Nereid API")
    if web_origin:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[web_origin],
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["content-type"],
        )
    try:
        service: InvestigationService | None = InvestigationService(ArgoStore(snapshot_dir))
    except SnapshotUnavailable:
        service = None
    planner = text_planner or azure_planner_from_environment()

    @app.get("/health")
    def health() -> dict[str, str]:
        if service is None:
            raise HTTPException(status_code=503, detail="ARGO snapshot is unavailable")
        return {"status": "ok"}

    @app.post("/v1/query/plan", response_model=PlanResponse)
    async def plan_query(request: PlanRequest) -> PlanResponse:
        if planner is None:
            return PlanResponse(
                plan=None,
                planner="explicit",
                warnings=["AI interpretation unavailable—filters still work. Use explicit filters."],
            )
        try:
            return PlanResponse(plan=await planner.plan(request.question), planner="azure", warnings=[])
        except PlannerUnavailable as error:
            return PlanResponse(plan=None, planner="explicit", warnings=[str(error)])

    @app.post("/v1/query/execute", response_model=ResultEnvelope)
    def execute(plan: QueryPlan) -> ResultEnvelope:
        if service is None:
            raise HTTPException(status_code=503, detail="ARGO snapshot is unavailable")
        try:
            return service.execute(plan)  # nosec B608: QueryPlan is validated; store binds every value.
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/v1/sections/derive", response_model=ResultEnvelope)
    def derive_section(request: SectionRequest) -> ResultEnvelope:
        if service is None:
            raise HTTPException(status_code=503, detail="ARGO snapshot is unavailable")
        return service.derive_section(request)

    @app.get("/v1/profiles/{wmo}/{cycle}", response_model=ResultEnvelope)
    def get_profile(
        wmo: str,
        cycle: int,
        qc_mode: Annotated[QcPolicy, Query()] = QcPolicy.RESEARCH,
    ) -> ResultEnvelope:
        if service is None:
            raise HTTPException(status_code=503, detail="ARGO snapshot is unavailable")
        plan = QueryPlan(operation="get_profile", wmo=wmo, cycle=cycle, qc_mode=qc_mode)
        return service.execute(plan)  # nosec B608: QueryPlan is validated; store binds every value.

    return app
