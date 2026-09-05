from datetime import datetime, timezone

import numpy as np
import pytest
import xarray as xr

from nereid_pipeline.manifest import SourceManifest, sha256_file


@pytest.fixture
def argo_nc(tmp_path):
    path = tmp_path / "R1900001_007.nc"
    dataset = xr.Dataset(
        data_vars={
            "PLATFORM_NUMBER": (("N_PROF",), np.array([b"1900001"])),
            "CYCLE_NUMBER": (("N_PROF",), np.array([7], dtype=np.int32)),
            "DIRECTION": (("N_PROF",), np.array([b"A"])),
            "LATITUDE": (("N_PROF",), np.array([10.0])),
            "LONGITUDE": (("N_PROF",), np.array([70.0])),
            "JULD": (("N_PROF",), np.array(["2023-03-15T00:00:00"], dtype="datetime64[s]")),
            "PRES": (("N_PROF", "N_LEVELS"), [[0, 10, 20, 30, 40, 50]]),
            "TEMP": (("N_PROF", "N_LEVELS"), [[28.0, 27.5, 27.0, 26.0, 25.0, 24.0]]),
            "TEMP_ADJUSTED": (("N_PROF", "N_LEVELS"), [[27.9, 27.4, 26.9, 25.9, 24.9, 23.9]]),
            "TEMP_QC": (("N_PROF", "N_LEVELS"), np.array([[b"1", b"1", b"2", b"3", b"4", b"1"]])),
            "PSAL": (("N_PROF", "N_LEVELS"), [[34.0, 34.1, 34.2, 34.3, 34.4, 34.5]]),
            "PSAL_ADJUSTED": (("N_PROF", "N_LEVELS"), [[34.01, 34.11, 34.21, 34.31, 34.41, 34.51]]),
            "PSAL_QC": (("N_PROF", "N_LEVELS"), np.array([[b"1", b"1", b"2", b"3", b"4", b"1"]])),
            "PRES_ADJUSTED_ERROR": (("N_PROF", "N_LEVELS"), [[0.1, 0.1, 0.1, 0.1, 0.1, 0.1]]),
            "DATA_MODE": (("N_PROF",), np.array([b"D"])),
        }
    )
    dataset.to_netcdf(path)
    return path


@pytest.fixture
def source_manifest(argo_nc):
    return SourceManifest(
        source_url="https://example.test/argo/R1900001_007.nc",
        snapshot_doi="10.1234/nereid.snapshot",
        fetched_at=datetime(2023, 3, 16, tzinfo=timezone.utc),
        sha256=sha256_file(argo_nc),
    )
