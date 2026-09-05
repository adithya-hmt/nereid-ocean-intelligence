# pyright: reportMissingImports=false
import csv
import io
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

import pyarrow as pa
import pyarrow.parquet as pq
from fastapi.testclient import TestClient

from nereid_api.export import build_evidence_zip
from nereid_api.models import (
    MethodRecord,
    Provenance,
    QcSummary,
    QueryPlan,
    ResultEnvelope,
)


def test_export_is_deterministic_and_source_faithful():
    envelope = ResultEnvelope(
        query_plan=QueryPlan(operation="get_profile", wmo="1902202", cycle=161, direction="A"),
        data=[],
        chart_spec=[{"profile_metrics": [{"name": "metric", "value": 1.0}]}],
        provenance=[
            Provenance(
                source_url="https://data-argo.ifremer.fr/dac/aoml/1902202/profiles/D1902202_161.nc",
                snapshot_doi="https://doi.org/10.17882/42182",
                fetched_at=datetime(2026, 9, 5, tzinfo=UTC),
                sha256="a" * 64,
            )
        ],
        qc_summary=QcSummary(retained=2, rejected=1),
        methods=[
            MethodRecord(name="method", version="1", parameters={"units": "dbar"})
        ],
        assumptions=["Assumption."],
        warnings=["Warning."],
    )
    rows = [
        {
            "wmo": "1902202",
            "cycle": 161,
            "timestamp": "2023-03-30T20:40:02Z",
            "pressure_dbar": 10,
            "temperature_adjusted": 20.0,
            "temperature_adjusted_qc": 1,
        },
        {
            "wmo": "1902202",
            "cycle": 161,
            "timestamp": "2023-03-30T20:40:02Z",
            "pressure_dbar": 2,
            "temperature_adjusted": 21.0,
            "temperature_adjusted_qc": 1,
        },
    ]
    generated_at = datetime(2026, 9, 5, tzinfo=UTC)
    payload = build_evidence_zip(envelope, rows, generated_at)
    assert payload == build_evidence_zip(envelope, list(reversed(rows)), generated_at)
    with ZipFile(io.BytesIO(payload)) as archive:
        assert archive.namelist() == [
            "README.txt",
            "selection.csv",
            "provenance.json",
            "query-plan.json",
            "methods.json",
        ]
        selected = list(
            csv.DictReader(io.StringIO(archive.read("selection.csv").decode()))
        )
        assert len(selected) == 2 and selected[0]["pressure_dbar"] == "2"
        assert json.loads(archive.read("provenance.json"))[0]["sha256"] == "a" * 64
        assert json.loads(archive.read("query-plan.json"))["wmo"] == "1902202"
        methods = json.loads(archive.read("methods.json"))
        assert methods["chart_spec"] == [{"profile_metrics": [{"name": "metric", "value": 1.0}]}]
        assert methods["assumptions"] == ["Assumption."]
        assert methods["warnings"] == ["Warning."]
        assert methods["qc_summary"] == {"retained": 2, "rejected": 1}
        assert methods["methods"][0]["parameters"]["units"] == "dbar"
        assert "selected derivative" in archive.read("README.txt").decode()


def test_export_warning_order_is_hash_seed_independent():
    script = """
from datetime import UTC, datetime
from nereid_api.export import build_evidence_zip
from nereid_api.models import QueryPlan
from nereid_api.service import InvestigationService

row = {
    "wmo": "1900001", "cycle": 7, "direction": "A", "source_profile_index": 0,
    "vertical_sampling_scheme": "primary", "level_index": 0,
    "pressure_raw": 0.0, "pressure_adjusted": 0.0, "pressure_best": 0.0,
    "pressure_dbar": 0.0, "pressure_qc": 1, "pressure_adjusted_qc": 1,
    "pressure_adjusted_error": None, "adjusted_pressure_error": None, "depth_m": 0.0,
    "temperature_raw": 20.0, "temperature_adjusted": 20.0, "temperature_best": 20.0,
    "temperature_qc": 1, "temperature_adjusted_qc": 1,
    "temperature_adjusted_error": None, "conservative_temperature": 20.0,
    "salinity_raw": 35.0, "salinity_adjusted": 35.0, "salinity_best": 35.0,
    "salinity_qc": 1, "salinity_adjusted_qc": 1,
    "salinity_adjusted_error": None, "absolute_salinity": 35.0,
    "latitude": 10.0, "longitude": 70.0, "timestamp": datetime(2023, 3, 15, tzinfo=UTC),
    "data_mode": "D", "source_url": "https://example.test/a.nc",
    "snapshot_doi": "10.1234/nereid", "fetched_at": datetime(2023, 3, 26, tzinfo=UTC),
    "source_sha256": "a" * 64,
}
plan = QueryPlan(operation="get_profile", wmo="1900001", cycle=7, direction="A", parameters=["PSAL", "TEMP", "PRES"])
envelope = InvestigationService(None)._envelope(plan, [row], 1, 1)
assert [warning.split(" eligible ")[1].split()[0] for warning in envelope.warnings] == ["PRES", "TEMP", "PSAL"]
assert list(envelope.methods[0].parameters["adjusted_errors"]) == [
    "1900001/7/A/0:PRES", "1900001/7/A/0:TEMP", "1900001/7/A/0:PSAL",
]
import sys
sys.stdout.buffer.write(build_evidence_zip(envelope, envelope.data, datetime(2026, 9, 5, tzinfo=UTC)))
"""
    api_dir = Path(__file__).resolve().parents[1]

    def export_for_hash_seed(seed: str) -> bytes:
        environment = os.environ | {"PYTHONHASHSEED": seed, "PYTHONPATH": str(api_dir / "src")}
        return subprocess.run(
            [sys.executable, "-c", script], cwd=api_dir, env=environment,
            check=True, capture_output=True,
        ).stdout

    assert export_for_hash_seed("1") == export_for_hash_seed("2")


def test_export_sorts_masked_pressure_by_depth_without_coercing_none():
    envelope = ResultEnvelope(
        query_plan=QueryPlan(operation="get_profile", wmo="1902202", cycle=161, direction="A", parameters=["TEMP"]),
        data=[], chart_spec=[], provenance=[], qc_summary=QcSummary(retained=2, rejected=0), methods=[], assumptions=[], warnings=[],
    )
    rows = [
        {"wmo": "1902202", "cycle": 161, "timestamp": "2023-03-30T20:40:02Z", "pressure_dbar": None, "depth_m": 10.0},
        {"wmo": "1902202", "cycle": 161, "timestamp": "2023-03-30T20:40:02Z", "pressure_dbar": None, "depth_m": 2.0},
    ]
    payload = build_evidence_zip(envelope, rows, datetime(2026, 9, 5, tzinfo=UTC))
    assert payload == build_evidence_zip(envelope, list(reversed(rows)), datetime(2026, 9, 5, tzinfo=UTC))
    with ZipFile(io.BytesIO(payload)) as archive:
        selected = list(csv.DictReader(io.StringIO(archive.read("selection.csv").decode())))
        assert [row["depth_m"] for row in selected] == ["2.0", "10.0"]
        assert all(row["pressure_dbar"] == "" for row in selected)


def test_export_sort_includes_full_identity_and_native_level_index():
    envelope = ResultEnvelope(query_plan=QueryPlan(operation="get_profile", wmo="1902202", cycle=161, direction="A"), data=[], chart_spec=[], provenance=[], qc_summary=QcSummary(retained=4, rejected=0), methods=[], assumptions=[], warnings=[])
    rows = [
        {"wmo": "1902202", "cycle": 161, "direction": "D", "source_profile_index": 0, "level_index": 0, "depth_m": 0},
        {"wmo": "1902202", "cycle": 161, "direction": "A", "source_profile_index": 1, "level_index": 0, "depth_m": 0},
        {"wmo": "1902202", "cycle": 161, "direction": "A", "source_profile_index": 0, "level_index": 1, "depth_m": None},
        {"wmo": "1902202", "cycle": 161, "direction": "A", "source_profile_index": 0, "level_index": 0, "depth_m": 10},
    ]
    payload = build_evidence_zip(envelope, rows, datetime(2026, 9, 5, tzinfo=UTC))
    assert payload == build_evidence_zip(envelope, list(reversed(rows)), datetime(2026, 9, 5, tzinfo=UTC))
    with ZipFile(io.BytesIO(payload)) as archive:
        selected = list(csv.DictReader(io.StringIO(archive.read("selection.csv").decode())))
        assert [(row["direction"], row["source_profile_index"], row["level_index"]) for row in selected] == [("A", "0", "0"), ("A", "0", "1"), ("A", "1", "0"), ("D", "0", "0")]


def test_export_endpoint_downloads_the_exact_evidence_members(snapshot_dir):
    from nereid_api.main import create_app

    client = TestClient(create_app(snapshot_dir))
    result = client.post(
        "/v1/query/execute",
        json={
            "operation": "find_profiles",
            "bbox": [60, 0, 80, 20],
            "start_date": "2023-03-01",
            "end_date": "2023-03-31",
            "parameters": ["TEMP", "PSAL"],
            "qc_mode": "research",
        },
    ).json()
    selection = {"wmo": "1900001", "cycle": 7, "source_profile_index": 0, "direction": "A"}
    levels_path = snapshot_dir / "levels.parquet"
    levels = pq.read_table(levels_path).to_pylist()
    for row in levels:
        if row["wmo"] == "1900001":
            row["temperature_adjusted_error"] = None
            row["pressure_qc"] = row["pressure_adjusted_qc"] = 1
            row["temperature_qc"] = row["temperature_adjusted_qc"] = 1
            row["salinity_qc"] = row["salinity_adjusted_qc"] = 1
    pq.write_table(pa.Table.from_pylist(levels), levels_path)
    response = client.post(
        "/v1/export",
        json={
            "plan": result["query_plan"],
            "selections": [selection],
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["content-disposition"]
        == "attachment; filename=nereid-evidence.zip"
    )
    with ZipFile(io.BytesIO(response.content)) as archive:
        assert archive.namelist() == [
            "README.txt",
            "selection.csv",
            "provenance.json",
            "query-plan.json",
            "methods.json",
        ]
        selected = list(
            csv.DictReader(io.StringIO(archive.read("selection.csv").decode()))
        )
        assert [
            (row["wmo"], float(row["depth_m"])) for row in selected
        ] == sorted((row["wmo"], float(row["depth_m"])) for row in selected)
        assert all(row["pressure_dbar"] == "" for row in selected)
        assert {row["wmo"] for row in selected} == {"1900001"}
        assert {row["source_profile_index"] for row in selected} == {"0"}
        assert all(row["temperature_adjusted_qc"] not in {"3", "4"} for row in selected)
        methods = json.loads(archive.read("methods.json"))
        assert methods["qc_summary"] == {"retained": 6, "rejected": 0}
        metrics = methods["chart_spec"][0]["profile_metrics"]
        assert {
            (metric["wmo"], metric["cycle"], metric["direction"], metric["source_profile_index"])
            for metric in metrics
        } == {("1900001", 7, "A", 0)}
        assert all(metric["algorithm"] and isinstance(metric["value"], float) for metric in metrics)
        assert not any(metric["wmo"] == "1900002" for metric in metrics)
        assert methods["assumptions"] == []
        assert methods["warnings"] == [
            "Adjusted-error metadata is missing or invalid for eligible TEMP measurements in representation 1900001/7/A/0."
        ]
        errors = methods["methods"][0]["parameters"]["adjusted_errors"]
        assert set(errors) == {"1900001/7/A/0:TEMP", "1900001/7/A/0:PSAL"}
        assert errors["1900001/7/A/0:TEMP"]["adjusted_error_available_count"] == 0
        units = methods["methods"][0]["units"]
        assert {field: units[field] for field in ("pressure_dbar", "depth_m", "temperature_raw", "temperature_adjusted", "salinity_raw", "salinity_adjusted", "conservative_temperature", "absolute_salinity")} == {
            "pressure_dbar": "dbar", "depth_m": "m", "temperature_raw": "degC", "temperature_adjusted": "degC", "salinity_raw": "PSS-78 unitless", "salinity_adjusted": "PSS-78 unitless", "conservative_temperature": "degC", "absolute_salinity": "g kg-1",
        }

    altered = client.post(
        "/v1/export",
        json={
            "plan": result["query_plan"],
            "selections": [{"wmo": "1900001", "cycle": 7, "source_profile_index": 99, "direction": "A"}],
        },
    )
    assert altered.status_code == 422


def test_export_rejects_selected_complete_rows_above_plan_limit_for_find_profiles(snapshot_dir):
    from nereid_api.main import create_app

    response = TestClient(create_app(snapshot_dir)).post(
        "/v1/export",
        json={
            "plan": {
                "operation": "find_profiles",
                "bbox": [60, 0, 80, 20],
                "start_date": "2023-03-01",
                "end_date": "2023-03-31",
                "parameters": ["TEMP"],
                "row_limit": 1,
            },
            "selections": [{"wmo": "1900001", "cycle": 7, "direction": "A", "source_profile_index": 0}],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "exact selection exceeds row_limit"


def test_export_rejects_selected_complete_rows_above_plan_limit_for_get_profile(snapshot_dir):
    from nereid_api.main import create_app

    response = TestClient(create_app(snapshot_dir)).post(
        "/v1/export",
        json={
            "plan": {
                "operation": "get_profile",
                "wmo": "1900001",
                "cycle": 7,
                "direction": "A",
                "parameters": ["TEMP"],
                "row_limit": 1,
            },
            "selections": [{"wmo": "1900001", "cycle": 7, "direction": "A", "source_profile_index": 0}],
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "exact selection exceeds row_limit"


def test_export_selection_recomputes_receipt_for_exact_multiple_representations(snapshot_dir):
    from nereid_api.main import create_app

    client = TestClient(create_app(snapshot_dir))
    plan = {"operation": "find_profiles", "bbox": [60, 0, 80, 20], "start_date": "2023-03-01", "end_date": "2023-03-31", "parameters": ["TEMP"], "qc_mode": "research"}
    selections = [
        {"wmo": "1900001", "cycle": 7, "direction": "A", "source_profile_index": 0},
        {"wmo": "1900002", "cycle": 8, "direction": "A", "source_profile_index": 0},
    ]
    response = client.post("/v1/export", json={"plan": plan, "selections": selections})
    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        selected = list(csv.DictReader(io.StringIO(archive.read("selection.csv").decode())))
        methods = json.loads(archive.read("methods.json"))
        assert {(row["wmo"], row["source_profile_index"]) for row in selected} == {("1900001", "0"), ("1900002", "0")}
        errors = methods["methods"][0]["parameters"]["adjusted_errors"]
        assert set(errors) == {"1900001/7/A/0:TEMP", "1900002/8/A/0:TEMP"}
        assert methods["qc_summary"] == {"retained": 4, "rejected": 8}


def test_export_endpoint_accepts_a_valid_get_profile_plan(snapshot_dir):
    from nereid_api.main import create_app

    client = TestClient(create_app(snapshot_dir))
    response = client.post(
        "/v1/export",
        json={
            "plan": {
                "operation": "get_profile",
                "wmo": "1900001",
                "cycle": 7,
                "direction": "A",
                "parameters": ["TEMP", "PSAL"],
                "qc_mode": "research",
            },
            "selections": [{"wmo": "1900001", "cycle": 7, "source_profile_index": 0, "direction": "A"}],
        },
    )

    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        methods = json.loads(archive.read("methods.json"))
        assert methods["qc_summary"] == {"retained": 2, "rejected": 4}
