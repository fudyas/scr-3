from typing import List, Optional

from pydantic import ValidationError

from sdlc.models.artifact import ArtifactBundle, ArtifactCodec, ArtifactIndex
from sdlc.models.errors import ItemClaimError, SdlcError
from sdlc.models.ledger import LedgerChange
from sdlc.repositories.item_repository import ItemRepository
from sdlc.repositories.ledger_repository import LedgerRepository, LedgerSnapshot


class ArtifactRepository:
    """Persists immutable bundles and atomic input/result indexes through ledger CAS."""

    def __init__(self, ledger: LedgerRepository) -> None:
        """Stores the existing ledger repository."""
        self._ledger = ledger

    def sync(self) -> None:
        """Refreshes the local mirror before artifact decisions."""
        self._ledger.sync()

    @staticmethod
    def _index_path(item_id: str) -> str:
        """Returns the durable index path for an item."""
        return f"artifacts/items/{item_id}/index.json"

    def get(self, digest: str, snapshot: Optional[LedgerSnapshot] = None) -> ArtifactBundle:
        """Returns a durable bundle after canonical digest verification.

        Args:
            digest: the SHA-256 locator of the expected bundle.
            snapshot: an optional transaction view for consistent reads.

        Returns:
            The exact stored bundle.

        Raises:
            SdlcError: the bundle is missing, malformed, or inconsistent with its digest.
        """
        ArtifactCodec.validate_digest(digest)
        text = (snapshot or self._ledger.snapshot()).read_text(f"artifacts/bundles/{digest}.json")
        if text is None:
            raise SdlcError(f"missing durable artifact bundle: {digest}")
        try:
            bundle = ArtifactBundle.model_validate_json(text)
        except ValidationError as error:
            raise SdlcError(f"invalid durable artifact bundle: {digest}") from error
        if ArtifactCodec.digest(bundle) != digest or ArtifactCodec.canonical(bundle) != text:
            raise SdlcError(f"durable artifact digest mismatch: {digest}")
        return bundle

    def index(self, item_id: str, snapshot: Optional[LedgerSnapshot] = None) -> Optional[ArtifactIndex]:
        """Returns an index and refuses missing-index source-only downgrade.

        Args:
            item_id: the normalized owner identity.
            snapshot: an optional transaction view.

        Returns:
            The validated index or no index for an artifact-free item.

        Raises:
            SdlcError: an index is corrupt or durable item bundles lost their index.
        """
        view = snapshot or self._ledger.snapshot()
        text = view.read_text(self._index_path(item_id))
        if text is None:
            # Reads only the dedicated durable bundle directory, never local runtime state
            for path in view.list_paths("artifacts/bundles"):
                candidate = view.read_text(path)
                try:
                    bundle = ArtifactBundle.model_validate_json(candidate or "")
                except ValidationError as error:
                    raise SdlcError(f"invalid durable artifact bundle: {path}") from error
                if bundle.item_id == item_id:
                    raise SdlcError(f"missing artifact index for {item_id}; recover durable selection before review")
            return None
        try:
            index = ArtifactIndex.model_validate_json(text)
        except ValidationError as error:
            raise SdlcError(f"invalid artifact index: {item_id}") from error
        if index.schema_version != 1 or len(index.history) != len(set(index.history)) or not index.history:
            raise SdlcError(f"invalid artifact index history: {item_id}")
        for digest in index.history:
            ArtifactCodec.validate_digest(digest)
        if index.input_digest not in index.history and index.input_digest is not None:
            raise SdlcError(f"artifact input is absent from history: {item_id}")
        if len(index.result_digests) != len(set(index.result_digests)) or any(
                digest not in index.history for digest in index.result_digests):
            raise SdlcError(f"artifact results are absent from history: {item_id}")
        return index

    def history(self, item_id: str) -> List[ArtifactBundle]:
        """Returns the item's retained bundles with index ownership checks."""
        index = self.index(item_id)
        if index is None:
            return []
        bundles = [self.get(digest) for digest in index.history]
        if any(bundle.item_id != item_id for bundle in bundles):
            raise SdlcError(f"artifact index references another item's bundle: {item_id}")
        for digest, bundle in zip(index.history, bundles):
            if (digest in index.result_digests) != (bundle.purpose == "RESULT"):
                raise SdlcError(f"artifact index purpose mismatch: {item_id}")
            if digest == index.input_digest and bundle.purpose != "INPUT":
                raise SdlcError(f"artifact index selected a non-input bundle: {item_id}")
        return bundles

    def store(self, bundle: ArtifactBundle, items: ItemRepository, host: str,
              expected_input: Optional[str] = None) -> None:
        """Publishes a bundle and index atomically after fresh item and binding checks.

        Args:
            bundle: the validated complete bundle to retain.
            items: the existing item repository for ownership checks.
            host: the publishing host identity.
            expected_input: the previous input digest required during review capture.

        Raises:
            SdlcError: ownership, binding, or current selection refuses publication.
        """
        digest = ArtifactCodec.digest(bundle)
        text = ArtifactCodec.canonical(bundle)

        def mutate(snapshot: LedgerSnapshot) -> LedgerChange:
            """Builds one publication on the current remote ledger view."""
            item = items.get(bundle.item_id, snapshot)
            if item.host is not None and item.host != host:
                raise ItemClaimError(f"{bundle.item_id} is claimed by host {item.host}")
            index = self.index(bundle.item_id, snapshot) or ArtifactIndex()
            if expected_input is not None and index.input_digest != expected_input:
                raise SdlcError(f"artifact input selection changed during capture: {bundle.item_id}")
            self._validate_purpose(bundle, index, snapshot)
            path = f"artifacts/bundles/{digest}.json"
            existing = snapshot.read_text(path)
            if existing is not None and existing != text:
                raise SdlcError(f"immutable artifact bundle conflict: {digest}")
            changes = {}
            if existing is None:
                changes[path] = text
            updated = index.model_copy(deep=True)
            if digest not in updated.history:
                updated.history.append(digest)
            if bundle.purpose == "INPUT":
                updated.input_digest = digest
            elif digest not in updated.result_digests:
                updated.result_digests.append(digest)
            if updated != index:
                changes[self._index_path(bundle.item_id)] = updated.model_dump_json()
            return LedgerChange(changes=changes, message=f"{bundle.item_id}: publish artifacts {digest}")

        self._ledger.transact(mutate)

    def _validate_purpose(self, bundle: ArtifactBundle, index: ArtifactIndex, snapshot: LedgerSnapshot) -> None:
        """Checks independent input/result lifecycle and exact source bindings."""
        if bundle.purpose == "INPUT":
            if bundle.input_digest is not None:
                raise SdlcError("INPUT artifact bundle cannot reference another input digest")
            return
        if bundle.purpose != "RESULT" or not bundle.source_tree or not bundle.input_digest:
            raise SdlcError("RESULT artifact bundle requires source_tree and input_digest")
        inputs = self.get(bundle.input_digest, snapshot)
        if inputs.item_id != bundle.item_id or inputs.purpose != "INPUT" or inputs.source_tree != bundle.source_tree:
            raise SdlcError("RESULT artifact bundle does not match its source/input pair")
        if index.input_digest != bundle.input_digest:
            raise SdlcError("RESULT artifact bundle references a superseded input selection")
        if {entry.managed_path for entry in inputs.entries}.intersection(entry.managed_path for entry in bundle.entries):
            raise SdlcError("RESULT artifact destinations overlap selected INPUT files")
