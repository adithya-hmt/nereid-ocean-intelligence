# pyright: reportMissingImports=false
"""FastAPI entry points for bounded local ARGO investigations."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from nereid_api.models import QcPolicy, QueryPlan, ResultEnvelope
from nereid_api.service import InvestigationService, SectionRequest
from nereid_api.store import ArgoStore, SnapshotUnavailable


def create_app(snapshot_dir: Path, web_origin: str | None = None) -> FastAPI:
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

    @app.get("/health")
    def health() -> dict[str, str]:
        if service is None:
            raise HTTPException(status_code=503, detail="ARGO snapshot is unavailable")
        return {"status": "ok"}

    @app.post("/v1/query/execute", response_model=ResultEnvelope)
    def execute(plan: QueryPlan) -> ResultEnvelope:
        if service is None:
            raise HTTPException(status_code=503, detail="ARGO snapshot is unavailable")
        try:
            return service.execute(plan)  # nosec B608: QueryPlan is validated; store binds every value.
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/v1/sections/derive")
    def derive_section(request: SectionRequest) -> dict:
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
