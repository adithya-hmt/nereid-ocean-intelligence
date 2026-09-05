# pyright: reportMissingImports=false
"""FastAPI entry points for bounded local ARGO investigations."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from nereid_api.export import build_evidence_zip
from nereid_api.models import QcPolicy, QueryPlan, ResultEnvelope, SectionRequest
from nereid_api.planner import (
    AzurePlanner,
    PlannerRejected,
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


class SelectedRepresentation(BaseModel):
    wmo: str
    cycle: int = Field(ge=0)
    source_profile_index: int = Field(ge=0)


class ExportRequest(BaseModel):
    plan: QueryPlan
    selections: list[SelectedRepresentation] = Field(min_length=1, max_length=100)


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
        except (PlannerUnavailable, PlannerRejected) as error:
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

    @app.post("/v1/export")
    def export(request: ExportRequest) -> Response:
        if service is None:
            raise HTTPException(status_code=503, detail="ARGO snapshot is unavailable")
        try:
            envelope = service.export_selection(request.plan, [item.model_dump() for item in request.selections])
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return Response(
            build_evidence_zip(envelope, envelope.data, datetime.now(timezone.utc)),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=nereid-evidence.zip"},
        )

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


def create_offline_app() -> FastAPI:
    """Start the pinned local replay snapshot for browser acceptance tests."""
    return create_app(
        Path(os.environ["NEREID_SNAPSHOT_DIR"]),
        web_origin=os.environ.get("NEREID_WEB_ORIGIN"),
    )
