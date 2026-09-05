import hashlib
from datetime import datetime, timezone

from nereid_pipeline.manifest import SourceManifest, sha256_file
from nereid_pipeline.normalize import normalize_profile_file


def test_normalization_preserves_provenance_and_best_values(argo_nc, tmp_path, source_manifest):
    result = normalize_profile_file(argo_nc, tmp_path, source_manifest)
    levels = result.levels.to_pandas()
    assert result.profile_count == 1
    assert levels["wmo"].unique().tolist() == ["1900001"]
    assert levels["source_sha256"].nunique() == 1
    assert levels.loc[0, "temperature_best"] == levels.loc[0, "temperature_adjusted"]
    assert levels["temperature_qc"].tolist() == [1, 1, 2, 3, 4, 1]
    assert levels["temperature_adjusted_qc"].tolist() == [1, 2, 1, 3, 4, 1]
    assert levels["salinity_qc"].tolist() == [1, 1, 2, 3, 4, 1]
    assert levels["salinity_adjusted_qc"].tolist() == [2, 1, 2, 3, 4, 1]
    assert levels["temperature_adjusted_error"].tolist() == [0.01, 0.02, 0.03, 0.04, 0.05, 0.06]
    assert levels["salinity_adjusted_error"].tolist() == [0.001, 0.002, 0.003, 0.004, 0.005, 0.006]


def test_normalization_preserves_duplicate_cycle_representations(argo_nc_with_duplicate_profile_key, tmp_path):
    source = argo_nc_with_duplicate_profile_key
    provenance = SourceManifest(
        source_url="https://example.test/argo/R1900001_007_duplicate.nc",
        snapshot_doi="10.1234/nereid.snapshot",
        fetched_at=datetime(2023, 3, 16, tzinfo=timezone.utc),
        sha256=sha256_file(source),
    )

    result = normalize_profile_file(source, tmp_path, provenance)

    assert result.profile_count == 2
    assert result.profiles["source_profile_index"].to_pylist() == [0, 1]
    assert result.profiles["vertical_sampling_scheme"].to_pylist() == ["unspecified", "unspecified"]


def test_normalization_is_idempotent(argo_nc, tmp_path, source_manifest):
    first = normalize_profile_file(argo_nc, tmp_path, source_manifest)
    first_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (tmp_path / "profiles.parquet", tmp_path / "levels.parquet", tmp_path / "manifest.jsonl")
    }
    second = normalize_profile_file(argo_nc, tmp_path, source_manifest)
    second_hashes = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (tmp_path / "profiles.parquet", tmp_path / "levels.parquet", tmp_path / "manifest.jsonl")
    }
    assert (first.profile_count, first.level_count) == (second.profile_count, second.level_count)
    assert first_hashes == second_hashes
