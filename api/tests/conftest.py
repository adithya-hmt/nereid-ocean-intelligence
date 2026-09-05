# pyright: reportMissingImports=false
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest


@pytest.fixture
def snapshot_dir(tmp_path: Path) -> Path:
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    profiles = pa.table(
        {
            "wmo": ["1900001", "1900002"],
            "cycle": [7, 8],
            "direction": ["A", "A"],
            "latitude": [10.0, 10.1],
            "longitude": [70.0, 70.1],
            "timestamp": ["2023-03-15T00:00:00Z", "2023-03-25T00:00:00Z"],
            "data_mode": ["D", "D"],
            "source_url": ["https://example.test/a.nc", "https://example.test/b.nc"],
            "snapshot_doi": ["10.1234/nereid", "10.1234/nereid"],
            "fetched_at": ["2023-03-26T00:00:00Z", "2023-03-26T00:00:00Z"],
            "source_sha256": ["a" * 64, "b" * 64],
        }
    )
    rows = []
    for wmo, cycle in (("1900001", 7), ("1900002", 8)):
        for pressure, qc in zip((0, 10, 20, 30, 40, 60), (1, 2, 1, 3, 4, 1), strict=True):
            rows.append(
                {
                    "wmo": wmo,
                    "cycle": cycle,
                    "direction": "A",
                    "pressure_dbar": float(pressure),
                    "depth_m": float(pressure),
                    "temperature_raw": 28.0 - pressure / 10,
                    "temperature_adjusted": 27.9 - pressure / 10,
                    "temperature_best": 27.9 - pressure / 10,
                    "temperature_qc": qc,
                    "temperature_adjusted_qc": qc,
                    "temperature_adjusted_error": 0.01,
                    "salinity_raw": 34.0 + pressure / 100,
                    "salinity_adjusted": 34.01 + pressure / 100,
                    "salinity_best": 34.01 + pressure / 100,
                    "salinity_qc": qc,
                    "salinity_adjusted_qc": qc,
                    "salinity_adjusted_error": 0.001,
                    "adjusted_pressure_error": 0.1,
                    "data_mode": "D",
                    "source_sha256": "a" * 64 if wmo == "1900001" else "b" * 64,
                }
            )
    pq.write_table(profiles, snapshot / "profiles.parquet")
    pq.write_table(pa.Table.from_pylist(rows), snapshot / "levels.parquet")
    return snapshot
