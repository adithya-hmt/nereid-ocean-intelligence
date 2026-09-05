import hashlib

from nereid_pipeline.normalize import normalize_profile_file


def test_normalization_preserves_provenance_and_best_values(argo_nc, tmp_path, source_manifest):
    result = normalize_profile_file(argo_nc, tmp_path, source_manifest)
    levels = result.levels.to_pandas()
    assert result.profile_count == 1
    assert levels["wmo"].unique().tolist() == ["1900001"]
    assert levels["source_sha256"].nunique() == 1
    assert levels.loc[0, "temperature_best"] == levels.loc[0, "temperature_adjusted"]
    assert levels["temperature_qc"].tolist() == [1, 1, 2, 3, 4, 1]


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
