"""Deterministic selected-derivative evidence exports."""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from nereid_api.models import ResultEnvelope

_FILES = ("README.txt", "selection.csv", "provenance.json", "query-plan.json", "methods.json")


def _json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _numeric(value: object) -> float:
    if not isinstance(value, (int, float, str)):
        raise TypeError("export level coordinate must be numeric")
    return float(value)


def _vertical_sort_value(row: dict[str, object]) -> float:
    """Use masked pressure when present, otherwise the retained depth coordinate."""
    pressure = row.get("pressure_dbar")
    return _numeric(pressure) if pressure is not None else _numeric(row["depth_m"])


def build_evidence_zip(envelope: ResultEnvelope, rows: list[dict[str, object]], generated_at: datetime) -> bytes:
    """Build a stable ZIP for selected rows; generation time is supplied by the caller."""
    ordered = sorted(rows, key=lambda row: (str(row.get("wmo", "")), int(str(row.get("cycle", 0))), str(row.get("timestamp", "")), _vertical_sort_value(row)))
    fields = sorted({key for row in ordered for key in row})
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(ordered)
    citation = "Argo (2026). Argo float data and metadata from Global Data Assembly Centre (Argo GDAC). https://doi.org/10.17882/42182"
    readme = f"Nereid selected ARGO derivative\n{citation}\nSnapshot DOI: {', '.join(sorted({item.snapshot_doi for item in envelope.provenance}))}\nGeneration timestamp: {generated_at.isoformat()}\nThis export is a selected derivative, not a lossless replacement for original NetCDF files.\n"
    content = {
        "README.txt": readme.encode("utf-8"),
        "selection.csv": csv_buffer.getvalue().encode("utf-8"),
        "provenance.json": _json([item.model_dump(mode="json") for item in envelope.provenance]),
        "query-plan.json": _json(envelope.query_plan.model_dump(mode="json")),
        "methods.json": _json({"methods": [item.model_dump(mode="json") for item in envelope.methods], "qc_summary": envelope.qc_summary.model_dump(mode="json")}),
    }
    output = io.BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name in _FILES:
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, content[name])
    return output.getvalue()
