# pyright: reportMissingImports=false
"""Normalize ARGO profile NetCDF files into reproducible Parquet tables."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
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
    return value.decode("utf-8").strip() if isinstance(value, bytes) else str(value).strip()


def _qc(value: Any) -> int | None:
    text = _text(value)
    return int(text) if text.isdigit() else None


def _number(value: Any) -> float:
    return float(value) if value is not None else float("nan")


def _finite(value: float) -> float | None:
    return value if np.isfinite(value) else None


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


def _value(dataset: xr.Dataset, name: str, profile: int, level: int) -> float:
    return _number(dataset[name].values[profile, level]) if name in dataset else float("nan")


def _qc_value(dataset: xr.Dataset, name: str, profile: int, level: int) -> int | None:
    return _qc(dataset[name].values[profile, level]) if name in dataset else None


def _collect(source: Path, provenance: SourceManifest) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if sha256_file(source) != provenance.sha256:
        raise ValueError("source checksum does not match provenance")
    profile_rows: list[dict[str, Any]] = []
    level_rows: list[dict[str, Any]] = []
    with xr.open_dataset(source) as dataset:
        for profile_index in range(dataset.sizes["N_PROF"]):
            wmo = _text(dataset["PLATFORM_NUMBER"].values[profile_index])
            cycle = int(dataset["CYCLE_NUMBER"].values[profile_index])
            direction = _text(dataset["DIRECTION"].values[profile_index])
            latitude, longitude = _number(dataset["LATITUDE"].values[profile_index]), _number(dataset["LONGITUDE"].values[profile_index])
            data_mode = _text(dataset["DATA_MODE"].values[profile_index])
            scheme = _text(dataset["VERTICAL_SAMPLING_SCHEME"].values[profile_index]) if "VERTICAL_SAMPLING_SCHEME" in dataset else "unspecified"
            base = {"wmo": wmo, "cycle": cycle, "direction": direction, "source_profile_index": profile_index, "vertical_sampling_scheme": scheme}
            profile_rows.append({**base, "latitude": latitude, "longitude": longitude, "timestamp": _timestamp(dataset["JULD"].values[profile_index]), "data_mode": data_mode, "source_url": provenance.source_url, "snapshot_doi": provenance.snapshot_doi, "fetched_at": provenance.fetched_at.isoformat(), "source_sha256": provenance.sha256})
            for level_index in range(dataset.sizes["N_LEVELS"]):
                pressure_raw = _value(dataset, "PRES", profile_index, level_index)
                pressure_adjusted = _value(dataset, "PRES_ADJUSTED", profile_index, level_index)
                pressure_best = _best(pressure_raw, pressure_adjusted)
                temp_raw, temp_adjusted = _value(dataset, "TEMP", profile_index, level_index), _value(dataset, "TEMP_ADJUSTED", profile_index, level_index)
                salinity_raw, salinity_adjusted = _value(dataset, "PSAL", profile_index, level_index), _value(dataset, "PSAL_ADJUSTED", profile_index, level_index)
                if all(np.isfinite(value) for value in (salinity_adjusted, pressure_adjusted, longitude, latitude)):
                    absolute_salinity = float(gsw.SA_from_SP(salinity_adjusted, pressure_adjusted, longitude, latitude))
                else:
                    absolute_salinity = None
                conservative_temperature = float(gsw.CT_from_t(absolute_salinity, temp_adjusted, pressure_adjusted)) if absolute_salinity is not None and np.isfinite(temp_adjusted) else None
                level_rows.append({**base, "level_index": level_index, "pressure_raw": pressure_raw, "pressure_adjusted": pressure_adjusted, "pressure_best": pressure_best, "pressure_dbar": pressure_best, "pressure_qc": _qc_value(dataset, "PRES_QC", profile_index, level_index), "pressure_adjusted_qc": _qc_value(dataset, "PRES_ADJUSTED_QC", profile_index, level_index), "pressure_adjusted_error": _value(dataset, "PRES_ADJUSTED_ERROR", profile_index, level_index), "adjusted_pressure_error": _value(dataset, "PRES_ADJUSTED_ERROR", profile_index, level_index), "depth_m": _finite(float(-gsw.z_from_p(pressure_adjusted, latitude))) if np.isfinite(pressure_adjusted) and np.isfinite(latitude) else None, "temperature_raw": temp_raw, "temperature_adjusted": temp_adjusted, "temperature_best": _best(temp_raw, temp_adjusted), "temperature_qc": _qc(dataset["TEMP_QC"].values[profile_index, level_index]), "temperature_adjusted_qc": _qc(dataset["TEMP_ADJUSTED_QC"].values[profile_index, level_index]), "temperature_adjusted_error": _value(dataset, "TEMP_ADJUSTED_ERROR", profile_index, level_index), "salinity_raw": salinity_raw, "salinity_adjusted": salinity_adjusted, "salinity_best": _best(salinity_raw, salinity_adjusted), "salinity_qc": _qc(dataset["PSAL_QC"].values[profile_index, level_index]), "salinity_adjusted_qc": _qc(dataset["PSAL_ADJUSTED_QC"].values[profile_index, level_index]), "salinity_adjusted_error": _value(dataset, "PSAL_ADJUSTED_ERROR", profile_index, level_index), "absolute_salinity": absolute_salinity, "conservative_temperature": conservative_temperature, "data_mode": data_mode, "source_sha256": provenance.sha256})
    return profile_rows, level_rows


def normalize_profile_files(inputs: Sequence[tuple[Path, SourceManifest]], output_dir: Path) -> NormalizationResult:
    """Normalize all selected sources as one deterministic, atomic snapshot."""
    profile_rows, level_rows = [], []
    for source, provenance in inputs:
        profiles, levels = _collect(Path(source), provenance)
        profile_rows.extend(profiles)
        level_rows.extend(levels)
    profile_rows.sort(key=lambda row: (row["wmo"], row["cycle"], row["direction"], row["source_sha256"], row["source_profile_index"]))
    level_rows.sort(key=lambda row: (row["wmo"], row["cycle"], row["direction"], row["source_sha256"], row["source_profile_index"], row["pressure_adjusted"], row["pressure_best"]))
    profile_keys = [(row["wmo"], row["cycle"], row["direction"], row["source_profile_index"]) for row in profile_rows]
    # Fill-value rows have no level identity. Never use NaN as part of a set key.
    level_keys = [(row["wmo"], row["cycle"], row["direction"], row["source_profile_index"], row["pressure_best"]) for row in level_rows if np.isfinite(row["pressure_best"])]
    if len(profile_keys) != len(set(profile_keys)):
        raise ValueError("duplicate (wmo, cycle, direction, source_profile_index) profile key")
    if len(level_keys) != len(set(level_keys)):
        raise ValueError("duplicate normalized level pressure key")
    profiles, levels = pa.Table.from_pylist(profile_rows), pa.Table.from_pylist(level_rows)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _atomic_parquet(profiles, output_dir / "profiles.parquet")
    _atomic_parquet(levels, output_dir / "levels.parquet")
    lines = [json.dumps({**asdict(next(provenance for source, provenance in inputs if provenance.sha256 == row["source_sha256"])), "fetched_at": row["fetched_at"], **{key: row[key] for key in ("wmo", "cycle", "direction", "source_profile_index")}}, sort_keys=True, separators=(",", ":")) for row in profile_rows]
    _atomic_text("\n".join(lines) + "\n", output_dir / "manifest.jsonl")
    return NormalizationResult(profiles, levels, len(profile_rows), len(level_rows))


def normalize_profile_file(source: Path, output_dir: Path, provenance: SourceManifest) -> NormalizationResult:
    """Compatibility wrapper for normalizing one selected source."""
    return normalize_profile_files([(source, provenance)], output_dir)
