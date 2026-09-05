"""Command-line entry point for bounded snapshot preparation."""

from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path

from nereid_pipeline.manifest import SourceManifest, sha256_file
from nereid_pipeline.normalize import normalize_profile_files


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("--fetched-at timestamps must include a timezone")
    return parsed


def main() -> None:
    parser = ArgumentParser(description="Normalize explicitly selected ARGO NetCDF files.")
    parser.add_argument("--netcdf", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-url", action="append", required=True)
    parser.add_argument("--snapshot-doi", required=True)
    parser.add_argument("--fetched-at", action="append", required=True, type=_timestamp)
    args = parser.parse_args()
    if not (len(args.netcdf) == len(args.source_url) == len(args.fetched_at)):
        parser.error("--netcdf, --source-url, and --fetched-at require one value per source")
    inputs = [
        (source, SourceManifest(source_url=url, snapshot_doi=args.snapshot_doi, fetched_at=fetched_at, sha256=sha256_file(source)))
        for source, url, fetched_at in zip(args.netcdf, args.source_url, args.fetched_at, strict=True)
    ]
    result = normalize_profile_files(inputs, args.output)
    print(f"normalized {result.profile_count} profiles and {result.level_count} levels")
