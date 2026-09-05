"""Command-line entry point for bounded snapshot preparation."""

from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path

from nereid_pipeline.manifest import SourceManifest, sha256_file
from nereid_pipeline.normalize import normalize_profile_file


def main() -> None:
    parser = ArgumentParser(description="Normalize one explicitly selected ARGO NetCDF file.")
    parser.add_argument("--netcdf", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--snapshot-doi", required=True)
    args = parser.parse_args()
    source = args.netcdf
    result = normalize_profile_file(source, args.output, SourceManifest(
        source_url=args.source_url,
        snapshot_doi=args.snapshot_doi,
        fetched_at=datetime.now(timezone.utc),
        sha256=sha256_file(source),
    ))
    print(f"normalized {result.profile_count} profiles and {result.level_count} levels")
