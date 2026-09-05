"""Normalize ARGO profile NetCDF files into reproducible Parquet tables."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import gsw
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import xarray as xr

from nereid_pipeline.manifest import SourceManifest, sha256_file


@dataclass(frozen=True)
class NormalizationResult:
    profiles: pa.Table
    levels: pa.Table
    profile_count: int
    level_count: int


def _text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8").strip()
    return str(value).strip()


def _qc(value: Any) -> int | None:
    text = _text(value)
    return int(text) if text.isdigit() else None


def _number(value: Any) -> float:
    return float(value) if value is not None else float("nan")


def _best(raw: float, adjusted: float) -> float:
    return adjusted if np.isfinite(adjusted) else raw


def _timestamp(value: Any) -> str:
    return np.datetime_as_string(np.datetime64(value), unit="s") + "Z"


def _atomic_parquet(table: pa.Table, destination: Path) -> None:
    with NamedTemporaryFile(dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        pq.write_table(table, temporary_path)
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def _atomic_text(content: str, destination: Path) -> None:
    with NamedTemporaryFile(dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp", mode="w", encoding="utf-8", delete=False) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    try:
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def normalize_profile_file(source: Path, output_dir: Path, provenance: SourceManifest) -> NormalizationResult:
    """Convert one local ARGO NetCDF file, replacing its deterministic snapshot output.

    This preserves all measurements and their flags; QC filtering is intentionally left
    to scientific query code so rejected values cannot be silently discarded here.
    """
    source = Path(source)
    if sha256_file(source) != provenance.sha256:
        raise ValueError("source checksum does not match provenance")

    profile_rows: list[dict[str, Any]] = []
    level_rows: list[dict[str, Any]] = []
    with xr.open_dataset(source) as dataset:
        profile_total = dataset.sizes["N_PROF"]
        for profile_index in range(profile_total):
            wmo = _text(dataset["PLATFORM_NUMBER"].values[profile_index])
            cycle = int(dataset["CYCLE_NUMBER"].values[profile_index])
            direction = _text(dataset["DIRECTION"].values[profile_index])
            latitude = _number(dataset["LATITUDE"].values[profile_index])
            longitude = _number(dataset["LONGITUDE"].values[profile_index])
            timestamp = _timestamp(dataset["JULD"].values[profile_index])
            data_mode = _text(dataset["DATA_MODE"].values[profile_index])
            profile_rows.append({
                "wmo": wmo, "cycle": cycle, "direction": direction,
                "latitude": latitude, "longitude": longitude, "timestamp": timestamp,
                "data_mode": data_mode, "source_url": provenance.source_url,
                "snapshot_doi": provenance.snapshot_doi,
                "fetched_at": provenance.fetched_at.isoformat(), "source_sha256": provenance.sha256,
            })
            pressures = dataset["PRES"].values[profile_index]
            for level_index, pressure_value in enumerate(pressures):
                pressure = _number(pressure_value)
                temp_raw = _number(dataset["TEMP"].values[profile_index, level_index])
                temp_adjusted = _number(dataset["TEMP_ADJUSTED"].values[profile_index, level_index])
                salinity_raw = _number(dataset["PSAL"].values[profile_index, level_index])
                salinity_adjusted = _number(dataset["PSAL_ADJUSTED"].values[profile_index, level_index])
                level_rows.append({
                    "wmo": wmo, "cycle": cycle, "direction": direction,
                    "pressure_dbar": pressure,
                    "depth_m": float(-gsw.z_from_p(pressure, latitude)),
                    "temperature_raw": temp_raw, "temperature_adjusted": temp_adjusted,
                    "temperature_best": _best(temp_raw, temp_adjusted),
                    "temperature_qc": _qc(dataset["TEMP_QC"].values[profile_index, level_index]),
                    "temperature_adjusted_qc": _qc(dataset["TEMP_ADJUSTED_QC"].values[profile_index, level_index]),
                    "temperature_adjusted_error": _number(dataset["TEMP_ADJUSTED_ERROR"].values[profile_index, level_index]),
                    "salinity_raw": salinity_raw, "salinity_adjusted": salinity_adjusted,
                    "salinity_best": _best(salinity_raw, salinity_adjusted),
                    "salinity_qc": _qc(dataset["PSAL_QC"].values[profile_index, level_index]),
                    "salinity_adjusted_qc": _qc(dataset["PSAL_ADJUSTED_QC"].values[profile_index, level_index]),
                    "salinity_adjusted_error": _number(dataset["PSAL_ADJUSTED_ERROR"].values[profile_index, level_index]),
                    "adjusted_pressure_error": _number(dataset["PRES_ADJUSTED_ERROR"].values[profile_index, level_index]),
                    "data_mode": data_mode, "source_sha256": provenance.sha256,
                })

    profile_keys = [(row["wmo"], row["cycle"], row["direction"]) for row in profile_rows]
    if len(profile_keys) != len(set(profile_keys)):
        raise ValueError("duplicate (wmo, cycle, direction) profile key")

    level_keys = [(row["wmo"], row["cycle"], row["direction"], row["pressure_dbar"]) for row in level_rows]
    if len(level_keys) != len(set(level_keys)):
        raise ValueError("duplicate (wmo, cycle, direction, pressure_dbar) level key")

    profiles = pa.Table.from_pylist(profile_rows)
    levels = pa.Table.from_pylist(level_rows)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _atomic_parquet(profiles, output_dir / "profiles.parquet")
    _atomic_parquet(levels, output_dir / "levels.parquet")
    manifest_lines = []
    for row in profile_rows:
        manifest_lines.append(json.dumps({**asdict(provenance), "fetched_at": provenance.fetched_at.isoformat(), **{key: row[key] for key in ("wmo", "cycle", "direction")}}, sort_keys=True, separators=(",", ":")))
    _atomic_text("\n".join(manifest_lines) + "\n", output_dir / "manifest.jsonl")
    return NormalizationResult(profiles, levels, len(profile_rows), len(level_rows))
