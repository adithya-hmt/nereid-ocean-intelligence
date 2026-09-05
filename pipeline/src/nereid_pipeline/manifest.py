"""Immutable source provenance helpers."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path


@dataclass(frozen=True)
class SourceManifest:
    """Provenance attached to every normalized source observation."""

    source_url: str
    snapshot_doi: str
    fetched_at: datetime
    sha256: str


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of *path* without loading it all into memory."""
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
