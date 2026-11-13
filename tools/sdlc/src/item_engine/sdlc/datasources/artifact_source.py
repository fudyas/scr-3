import base64
import hashlib
import os
import stat
import uuid
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Iterator, List, Set

from sdlc.models.artifact import ArtifactBinding, ArtifactBundle, ArtifactCodec, ArtifactEntry, ArtifactManifest
from sdlc.models.errors import SdlcError


class ArtifactSource:
    """Captures explicit regular files and materializes isolated artifact copies."""

    def __init__(self, artifacts_dir: Path, worktrees_dir: Path) -> None:
        """Stores the dedicated artifact and assigned-worktree roots.

        Args:
            artifacts_dir: the managed artifact namespace in the main checkout.
            worktrees_dir: the parent of item integration worktrees.
        """
        self._artifacts = artifacts_dir.absolute()
        self._worktrees = worktrees_dir.absolute()

    @staticmethod
    def relative(path: str) -> PurePosixPath:
        """Returns a safe canonical relative path or rejects traversal."""
        if not path or "\\" in path or "\x00" in path or any(part in ("", ".", "..") for part in path.split("/")):
            raise SdlcError(f"invalid artifact relative path: {path!r}")
        result = PurePosixPath(path)
        if result.is_absolute():
            raise SdlcError(f"absolute artifact path is forbidden: {path!r}")
        return result

    def managed(self, item_id: str, path: str) -> Path:
        """Returns a destination inside the item's stage or a legacy collection."""
        parts = self.relative(path).parts
        allowed_item = len(parts) >= 4 and parts[:2] == ("items", item_id) and parts[2] in (
            "planning", "implementation", "qa")
        allowed_legacy = len(parts) >= 3 and parts[0] == "legacy"
        if not allowed_item and not allowed_legacy:
            raise SdlcError(f"artifact destination outside managed scope: {path}")
        return self._artifacts.joinpath(*parts)

    @staticmethod
    @contextmanager
    def _parent(path: Path, create: bool = False) -> Iterator[int]:
        """Opens each ancestor without following symlinks and yields its parent descriptor.

        Args:
            path: the absolute file path whose parent is required.
            create: whether missing ancestor directories can enter the managed namespace.

        Yields:
            The descriptor of the file's parent directory.

        Raises:
            SdlcError: an ancestor is missing, a symlink, or not a directory.
        """
        if not path.is_absolute() or ".." in path.parts or "\x00" in str(path):
            raise SdlcError(f"invalid absolute artifact path: {path}")
        descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
        try:
            # Anchors every step to the already-open parent against symlink replacement
            for part in path.parts[1:-1]:
                if create:
                    try:
                        os.mkdir(part, mode=0o755, dir_fd=descriptor)
                    except FileExistsError:
                        pass
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            yield descriptor
        except OSError as error:
            raise SdlcError(f"unsafe or unavailable artifact path {path}: {error.strerror}") from error
        finally:
            os.close(descriptor)

    @staticmethod
    def read_entry(path: Path, original_path: str, managed_path: str) -> ArtifactEntry:
        """Captures bytes and permissions through descriptors without following links.

        Args:
            path: the explicit source file.
            original_path: its preserved provenance path.
            managed_path: its relative artifact destination.

        Returns:
            The complete regular-file record.

        Raises:
            SdlcError: the source is missing, unstable, or not regular.
        """
        with ArtifactSource._parent(path) as parent:
            descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            with os.fdopen(descriptor, "rb") as handle:
                before = os.fstat(handle.fileno())
                if not stat.S_ISREG(before.st_mode):
                    raise SdlcError(f"artifact source is not a regular file: {path}")
                payload = handle.read()
                after = os.fstat(handle.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns, before.st_mode) != (
                after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_mode):
            raise SdlcError(f"artifact source changed during capture: {path}")
        return ArtifactEntry(original_path=original_path, managed_path=managed_path,
                             sha256=hashlib.sha256(payload).hexdigest(), size=len(payload),
                             mode=stat.S_IMODE(before.st_mode), payload_base64=base64.b64encode(payload).decode("ascii"))

    def read_manifest(self, path: Path) -> ArtifactManifest:
        """Returns a strict manifest read without following source symlinks."""
        entry = self.read_entry(path.absolute(), "manifest.json", "manifest.json")
        return ArtifactManifest.model_validate_json(ArtifactCodec.payload(entry))

    def capture(self, item_id: str, manifest: ArtifactManifest, stage: str) -> ArtifactBundle:
        """Captures only explicit allowlisted source files from the manifest.

        Args:
            item_id: the publishing item's normalized identity.
            manifest: the complete selected input or result manifest.
            stage: the required lifecycle stage.

        Returns:
            The byte-preserving bundle ready for durable publication.

        Raises:
            SdlcError: source, destination, stage, or entry validation fails.
        """
        if manifest.schema_version != 1 or manifest.purpose not in ("INPUT", "RESULT"):
            raise SdlcError("artifact manifest requires schema_version 1 and purpose INPUT or RESULT")
        if stage not in ("planning", "implementation", "qa") or manifest.stage not in (None, stage):
            raise SdlcError("artifact manifest stage does not match publication stage")
        entries: List[ArtifactEntry] = []
        sources: Set[str] = set()
        for entry in manifest.entries:
            # Rejects aliases before any source open, including hidden-file aliases
            self.relative(entry.original_path)
            self.managed(item_id, entry.managed_path)
            path = entry.source_path
            if not path.is_absolute() or ".." in path.parts or "\x00" in str(path) or str(path) in sources:
                raise SdlcError(f"invalid or duplicate artifact source: {path}")
            sources.add(str(path))
            allowed = [self._worktrees / item_id / "integration" / root for root in ("contracts", "evidence")]
            allowed.extend([self._artifacts / "items" / item_id, self._artifacts / "legacy"])
            if not any(path.is_relative_to(root) and path != root for root in allowed):
                raise SdlcError(f"artifact source outside import scope: {path}")
            entries.append(self.read_entry(path, entry.original_path, entry.managed_path))
        bundle = ArtifactBundle(item_id=item_id, purpose=manifest.purpose, stage=stage,
                                source_tree=manifest.source_tree, source_commit=manifest.source_commit,
                                input_digest=manifest.input_digest, entries=entries)
        self.validate(bundle)
        return bundle

    def validate(self, bundle: ArtifactBundle) -> None:
        """Rejects unsafe, duplicate, or internally inconsistent bundle entries."""
        if bundle.schema_version != 1 or bundle.purpose not in ("INPUT", "RESULT"):
            raise SdlcError("unsupported artifact bundle schema or purpose")
        if bundle.stage not in ("planning", "implementation", "qa") or not bundle.entries:
            raise SdlcError("artifact bundle requires a valid stage and nonempty entries")
        destinations: Set[str] = set()
        originals: Set[str] = set()
        for entry in bundle.entries:
            self.relative(entry.original_path)
            self.managed(bundle.item_id, entry.managed_path)
            ArtifactCodec.payload(entry)
            if entry.managed_path in destinations or entry.original_path in originals:
                raise SdlcError(f"duplicate artifact path: {entry.managed_path}")
            destinations.add(entry.managed_path)
            originals.add(entry.original_path)
        for path in destinations:
            if any(str(parent) in destinations for parent in PurePosixPath(path).parents):
                raise SdlcError(f"artifact file conflicts with an ancestor destination: {path}")

    def binding(self, bundle: ArtifactBundle) -> ArtifactBinding:
        """Returns the portable durable locator and this host's snapshot path."""
        digest = ArtifactCodec.digest(bundle)
        return ArtifactBinding(item_id=bundle.item_id, purpose=bundle.purpose, stage=bundle.stage,
                               digest=digest, ledger_path=f"artifacts/bundles/{digest}.json",
                               snapshot_path=self._artifacts / "snapshots" / digest,
                               source_tree=bundle.source_tree, input_digest=bundle.input_digest)

    def recapture(self, bundle: ArtifactBundle, source_tree: str) -> ArtifactBundle:
        """Returns a new input bundle from the exact selected managed files."""
        entries = [self.read_entry(self.managed(bundle.item_id, entry.managed_path),
                                   entry.original_path, entry.managed_path) for entry in bundle.entries]
        return bundle.model_copy(update={"source_tree": source_tree, "entries": entries})

    @staticmethod
    def _matches(path: Path, entry: ArtifactEntry) -> bool:
        """Returns whether an existing regular file exactly matches its record."""
        actual = ArtifactSource.read_entry(path, entry.original_path, entry.managed_path)
        return actual == entry

    @staticmethod
    def _existing(path: Path) -> bool:
        """Returns file existence without following any symlink ancestor."""
        try:
            with ArtifactSource._parent(path) as parent:
                os.stat(path.name, dir_fd=parent, follow_symlinks=False)
            return True
        except SdlcError as error:
            # Allows absent directories while retaining every other path failure
            if isinstance(error.__cause__, FileNotFoundError):
                return False
            raise

    @staticmethod
    def _write_missing(path: Path, entry: ArtifactEntry) -> None:
        """Creates a complete file atomically without replacing an existing destination.

        Args:
            path: a prevalidated destination inside the artifact namespace.
            entry: the expected payload and recorded permission bits.

        Raises:
            SdlcError: a destination conflict or filesystem error occurs.
        """
        with ArtifactSource._parent(path, create=True) as parent:
            temporary = f".artifact-{uuid.uuid4().hex}.tmp"
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o600, dir_fd=parent)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(ArtifactCodec.payload(entry))
                    os.fchmod(handle.fileno(), entry.mode)
                    handle.flush()
                    os.fsync(handle.fileno())
                try:
                    os.link(temporary, path.name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
                except FileExistsError:
                    if not ArtifactSource._matches(path, entry):
                        raise SdlcError(f"artifact restore conflict: {path}")
            finally:
                os.unlink(temporary, dir_fd=parent)

    def materialize(self, bundle: ArtifactBundle) -> ArtifactBinding:
        """Restores missing managed and snapshot files after a full conflict preflight.

        Args:
            bundle: the already durable and validated bundle.

        Returns:
            The binding to the independent local snapshot.

        Raises:
            SdlcError: any destination conflicts or violates the path boundary.
        """
        self.validate(bundle)
        binding = self.binding(bundle)
        # Preflights every destination before the first managed write
        for entry in bundle.entries:
            for path in (self.managed(bundle.item_id, entry.managed_path), binding.snapshot_path / entry.managed_path):
                if self._existing(path) and not self._matches(path, entry):
                    raise SdlcError(f"artifact restore conflict: {path}")
        for entry in bundle.entries:
            for path in (self.managed(bundle.item_id, entry.managed_path), binding.snapshot_path / entry.managed_path):
                if not self._existing(path):
                    self._write_missing(path, entry)
        self.verify_snapshot(bundle)
        return binding

    @staticmethod
    def _files(descriptor: int, prefix: str = "") -> Set[str]:
        """Returns snapshot file paths while rejecting links and special files."""
        result: Set[str] = set()
        for name in os.listdir(descriptor):
            metadata = os.stat(name, dir_fd=descriptor, follow_symlinks=False)
            relative = f"{prefix}{name}"
            if stat.S_ISDIR(metadata.st_mode):
                child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
                try:
                    result.update(ArtifactSource._files(child, f"{relative}/"))
                finally:
                    os.close(child)
            elif stat.S_ISREG(metadata.st_mode):
                result.add(relative)
            else:
                raise SdlcError(f"snapshot contains a link or special file: {relative}")
        return result

    def verify_snapshot(self, bundle: ArtifactBundle) -> None:
        """Verifies the complete immutable copy without touching mutable artifacts."""
        self.validate(bundle)
        binding = self.binding(bundle)
        try:
            with self._parent(binding.snapshot_path / "placeholder") as descriptor:
                if self._files(descriptor) != {entry.managed_path for entry in bundle.entries}:
                    raise SdlcError(f"artifact snapshot file set changed: {binding.digest}; restore required")
        except SdlcError as error:
            if isinstance(error.__cause__, FileNotFoundError):
                raise SdlcError(f"artifact snapshot missing: {binding.digest}; run "
                                f"lets sdlc artifacts restore --bundle {binding.digest}") from error
            raise
        for entry in bundle.entries:
            if not self._matches(binding.snapshot_path / entry.managed_path, entry):
                raise SdlcError(f"artifact snapshot changed: {entry.managed_path}")

    def verify_live(self, bundle: ArtifactBundle) -> None:
        """Verifies every explicitly selected mutable input file."""
        for entry in bundle.entries:
            if not self._matches(self.managed(bundle.item_id, entry.managed_path), entry):
                raise SdlcError(f"selected artifact input changed: {entry.managed_path}")
