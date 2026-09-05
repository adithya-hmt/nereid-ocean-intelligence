from nereid_pipeline.manifest import sha256_file


def test_sha256_is_stable(tmp_path):
    path = tmp_path / "sample.nc"
    path.write_bytes(b"argo")
    assert sha256_file(path) == "774113f725e8622bcdb91dde0a36221bedf7cb2623a39f1218f17cf6ed246d19"
