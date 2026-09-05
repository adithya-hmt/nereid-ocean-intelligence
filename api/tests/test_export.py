# pyright: reportMissingImports=false
import csv
import io
import json
from datetime import datetime, timezone
from zipfile import ZipFile

from nereid_api.export import build_evidence_zip
from nereid_api.models import (
    MethodRecord,
    Provenance,
    QcSummary,
    QueryPlan,
    ResultEnvelope,
)


def test_export_is_deterministic_and_source_faithful():
    envelope = ResultEnvelope(query_plan=QueryPlan(operation="get_profile", wmo="1902202", cycle=161), data=[], chart_spec=[], provenance=[Provenance(source_url="https://data-argo.ifremer.fr/dac/aoml/1902202/profiles/D1902202_161.nc", snapshot_doi="https://doi.org/10.17882/42182", fetched_at=datetime(2026, 9, 5, tzinfo=timezone.utc), sha256="a" * 64)], qc_summary=QcSummary(retained=2, rejected=1), methods=[MethodRecord(name="method", version="1", parameters={"units": "dbar"})], assumptions=[], warnings=[])
    rows = [{"wmo": "1902202", "cycle": 161, "timestamp": "2023-03-30T20:40:02Z", "pressure_dbar": 10, "temperature_adjusted": 20.0, "temperature_adjusted_qc": 1}, {"wmo": "1902202", "cycle": 161, "timestamp": "2023-03-30T20:40:02Z", "pressure_dbar": 2, "temperature_adjusted": 21.0, "temperature_adjusted_qc": 1}]
    generated_at = datetime(2026, 9, 5, tzinfo=timezone.utc)
    payload = build_evidence_zip(envelope, rows, generated_at)
    assert payload == build_evidence_zip(envelope, list(reversed(rows)), generated_at)
    with ZipFile(io.BytesIO(payload)) as archive:
        assert archive.namelist() == ["README.txt", "selection.csv", "provenance.json", "query-plan.json", "methods.json"]
        selected = list(csv.DictReader(io.StringIO(archive.read("selection.csv").decode())))
        assert len(selected) == 2 and selected[0]["pressure_dbar"] == "2"
        assert json.loads(archive.read("provenance.json"))[0]["sha256"] == "a" * 64
        assert json.loads(archive.read("query-plan.json"))["wmo"] == "1902202"
        methods = json.loads(archive.read("methods.json"))
        assert methods["qc_summary"] == {"retained": 2, "rejected": 1}
        assert methods["methods"][0]["parameters"]["units"] == "dbar"
        assert "selected derivative" in archive.read("README.txt").decode()


def test_export_endpoint_downloads_the_exact_evidence_members(snapshot_dir):
    from fastapi.testclient import TestClient
    from nereid_api.main import create_app

    client = TestClient(create_app(snapshot_dir))
    result = client.post("/v1/query/execute", json={
        "operation": "find_profiles", "bbox": [60, 0, 80, 20],
        "start_date": "2023-03-01", "end_date": "2023-03-31",
        "parameters": ["TEMP", "PSAL"], "qc_mode": "research",
    }).json()
    selection = {"wmo": "1900001", "cycle": 7, "source_profile_index": 0}
    response = client.post("/v1/export", json={
        "plan": result["query_plan"], "selections": [selection],
    })

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename=nereid-evidence.zip'
    with ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.namelist() == ["README.txt", "selection.csv", "provenance.json", "query-plan.json", "methods.json"]
        selected = list(csv.DictReader(io.StringIO(archive.read("selection.csv").decode())))
        assert [(row["wmo"], float(row["pressure_dbar"])) for row in selected] == sorted((row["wmo"], float(row["pressure_dbar"])) for row in selected)
        assert {row["wmo"] for row in selected} == {"1900001"}
        assert {row["source_profile_index"] for row in selected} == {"0"}
        assert all(row["temperature_adjusted_qc"] not in {"3", "4"} for row in selected)

    altered = client.post("/v1/export", json={"plan": result["query_plan"], "selections": [{"wmo": "1900001", "cycle": 7, "source_profile_index": 99}]})
    assert altered.status_code == 422
