from abc import ABC
from pathlib import Path
from typing import List, Optional
import base64
import hashlib
import json
import re

from pydantic import Field

from primitives.models.strict_model import StrictModel
from sdlc.models.errors import SdlcError


class ArtifactBinding(StrictModel):
    """The durable locator and local snapshot of one artifact bundle."""

    item_id: str
    purpose: str
    stage: str
    digest: str
    ledger_path: str
    snapshot_path: Path
    source_tree: Optional[str] = None
    input_digest: Optional[str] = None


class ArtifactEntry(StrictModel):
    """One regular file with its original path, permissions, and exact payload."""

    original_path: str
    managed_path: str
    sha256: str
    size: int
    mode: int
    payload_base64: str


class ArtifactBundle(StrictModel):
    """An immutable input or result collection with source provenance."""

    schema_version: int = 1
    item_id: str
    purpose: str
    stage: str
    source_tree: Optional[str] = None
    source_commit: Optional[str] = None
    input_digest: Optional[str] = None
    entries: List[ArtifactEntry]


class ArtifactIndex(StrictModel):
    """The current complete input selection and retained publication history."""

    schema_version: int = 1
    input_digest: Optional[str] = None
    result_digests: List[str] = Field(default_factory=list)
    history: List[str] = Field(default_factory=list)


class ArtifactManifestEntry(StrictModel):
    """One explicit local source and its durable destination mapping."""

    source_path: Path
    original_path: str
    managed_path: str


class ArtifactManifest(StrictModel):
    """An explicit publication request that separates purpose from stage."""

    schema_version: int = 1
    purpose: str
    stage: Optional[str] = None
    source_tree: Optional[str] = None
    source_commit: Optional[str] = None
    input_digest: Optional[str] = None
    entries: List[ArtifactManifestEntry]


class ArtifactCodec(ABC):
    """Validates content-addressed bundle records and canonical serialization."""

    @staticmethod
    def canonical(bundle: ArtifactBundle) -> str:
        """Returns canonical UTF-8 JSON text for a bundle."""
        document = bundle.model_dump(mode="json")
        document["entries"] = sorted(document["entries"], key=lambda entry: entry["managed_path"])
        return json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def digest(bundle: ArtifactBundle) -> str:
        """Returns the digest of the canonical bundle bytes."""
        return hashlib.sha256(ArtifactCodec.canonical(bundle).encode("utf-8")).hexdigest()

    @staticmethod
    def validate_digest(digest: str) -> None:
        """Rejects values that cannot name a SHA-256 bundle."""
        if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise SdlcError(f"invalid artifact digest: {digest!r}")

    @staticmethod
    def payload(entry: ArtifactEntry) -> bytes:
        """Returns exact payload bytes after size, hash, and permission checks.

        Args:
            entry: the file record to verify.

        Returns:
            The original file bytes.

        Raises:
            SdlcError: the record contains invalid payload or metadata.
        """
        # Rejects unsupported metadata before any filesystem write
        if entry.mode < 0 or entry.mode > 0o7777 or entry.size < 0:
            raise SdlcError(f"invalid artifact metadata: {entry.managed_path}")
        try:
            payload = base64.b64decode(entry.payload_base64, validate=True)
        except (ValueError, TypeError) as error:
            raise SdlcError(f"invalid artifact base64: {entry.managed_path}") from error
        if len(payload) != entry.size or hashlib.sha256(payload).hexdigest() != entry.sha256:
            raise SdlcError(f"artifact payload hash or size mismatch: {entry.managed_path}")
        return payload
