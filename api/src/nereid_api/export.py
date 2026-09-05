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


def _numeric(value: object) -> tuple[int, float]:
    """Sort finite coordinates before null/non-numeric values without coercion."""
    if not isinstance(value, (int, float, str)):
        return (1, 0.0)
    try:
        return (0, float(value))
    except ValueError:
        return (1, 0.0)


def _vertical_sort_value(row: dict[str, object]) -> tuple[int, float]:
    """Use masked pressure when present, otherwise the retained depth coordinate."""
    pressure = row.get("pressure_dbar")
    return _numeric(pressure) if pressure is not None else _numeric(row.get("depth_m"))


def _sort_key(row: dict[str, object]) -> tuple[object, ...]:
    return (
        str(row.get("wmo") or ""),
        _numeric(row.get("cycle")),
        str(row.get("direction") or ""),
        _numeric(row.get("source_profile_index")),
        _numeric(row.get("level_index")),
        _vertical_sort_value(row),
        _numeric(row.get("depth_m")),
        str(row.get("timestamp") or ""),
    )


def build_evidence_zip(envelope: ResultEnvelope, rows: list[dict[str, object]], generated_at: datetime) -> bytes:
    """Build a stable ZIP for selected rows; generation time is supplied by the caller."""
    ordered = sorted(rows, key=_sort_key)
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
