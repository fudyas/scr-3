from pathlib import Path
from typing import List, Optional

from pydantic import ValidationError

from sdlc.algorithms.item_ids import ItemIdHelper
from sdlc.datasources.artifact_source import ArtifactSource
from sdlc.models.artifact import ArtifactBinding, ArtifactBundle
from sdlc.models.errors import ItemClaimError, SdlcError
from sdlc.repositories.artifact_repository import ArtifactRepository
from sdlc.repositories.item_repository import ItemRepository


class ArtifactUsecases:
    """Coordinates explicit publication, recovery, and exact-pair review evidence."""

    def __init__(self, repository: ArtifactRepository, source: ArtifactSource,
                 items: ItemRepository, item_prefix: str, host: str) -> None:
        """Stores existing repositories, local artifact boundaries, and host identity.

        Args:
            repository: the immutable bundle and index repository.
            source: the bounded local filesystem source.
            items: the item repository that owns publication authority.
            item_prefix: the stable item prefix.
            host: the publishing host identity.
        """
        self._repository = repository
        self._source = source
        self._items = items
        self._prefix = item_prefix
        self._host = host

    def _item(self, item_id: str, writing: bool = False) -> str:
        """Returns a normalized existing item after fresh ownership checks."""
        short_id = ItemIdHelper.normalize_item(item_id, self._prefix)
        self._repository.sync()
        item = self._items.get(short_id)
        if writing and item.host is not None and item.host != self._host:
            raise ItemClaimError(f"{short_id} is claimed by host {item.host}")
        return short_id

    def publish(self, item_id: str, manifest_path: Path, stage: str) -> ArtifactBinding:
        """Publishes a complete manifest remotely before creating managed copies.

        Args:
            item_id: the publishing item's short or full identity.
            manifest_path: the explicit local manifest file.
            stage: the planning, implementation, or QA stage.

        Returns:
            The durable binding and independent local snapshot path.

        Raises:
            SdlcError: manifest, source, ownership, persistence, or destination validation fails.
        """
        short_id = self._item(item_id, writing=True)
        try:
            manifest = self._source.read_manifest(manifest_path)
        except ValidationError as error:
            raise SdlcError(f"invalid artifact manifest: {error}") from error
        bundle = self._source.capture(short_id, manifest, stage)
        self._repository.store(bundle, self._items, self._host)
        return self._source.materialize(bundle)

    def list(self, item_id: str) -> List[ArtifactBinding]:
        """Returns retained input and result locators in publication order."""
        short_id = self._item(item_id)
        bundles = self._repository.history(short_id)
        for bundle in bundles:
            self._source.validate(bundle)
        return [self._source.binding(bundle) for bundle in bundles]

    def _bundle(self, digest: str) -> ArtifactBundle:
        """Returns a synced durable bundle with namespace and owner validation."""
        self._repository.sync()
        bundle = self._repository.get(digest)
        short_id = ItemIdHelper.normalize_item(bundle.item_id, self._prefix)
        if short_id != bundle.item_id:
            raise SdlcError("artifact bundle owner is not a normalized item id")
        self._items.get(short_id)
        self._source.validate(bundle)
        return bundle

    def restore(self, bundle_digest: str) -> ArtifactBinding:
        """Restores missing managed files and the independent immutable snapshot."""
        return self._source.materialize(self._bundle(bundle_digest))

    def verify(self, bundle_digest: str) -> ArtifactBinding:
        """Verifies durable bytes and the complete local immutable copy."""
        bundle = self._bundle(bundle_digest)
        self._source.verify_snapshot(bundle)
        return self._source.binding(bundle)

    def capture_review(self, item_id: str, source_tree: str) -> Optional[ArtifactBinding]:
        """Recaptures the complete selected input set and binds its exact source tree.

        Args:
            item_id: the reviewed item identity.
            source_tree: the real source Git tree under review.

        Returns:
            A durable input binding, or none for a genuinely artifact-free item.

        Raises:
            SdlcError: selection, ownership, live bytes, or durable publication fails.
        """
        short_id = ItemIdHelper.normalize_item(item_id, self._prefix)
        self._repository.sync()
        index = self._repository.index(short_id)
        if index is None:
            return None
        self._item(short_id, writing=True)
        if index.input_digest is None:
            raise SdlcError(f"artifact-bearing item has no selected INPUT bundle: {short_id}")
        selected = self._repository.get(index.input_digest)
        self._source.validate(selected)
        if selected.item_id != short_id or selected.purpose != "INPUT":
            raise SdlcError(f"artifact input selection belongs to another item or purpose: {short_id}")
        bundle = self._source.recapture(selected, source_tree)
        self._repository.store(bundle, self._items, self._host, expected_input=index.input_digest)
        return self._source.materialize(bundle)

    def verify_review(self, item_id: str, source_tree: str, binding: Optional[ArtifactBinding]) -> None:
        """Rejects changed selection, source, live input, or immutable snapshot bytes.

        Args:
            item_id: the reviewed item identity.
            source_tree: the exact source Git tree under review.
            binding: the input locator recorded by the review context.

        Raises:
            SdlcError: any component of the source/input pair changed or disappeared.
        """
        short_id = ItemIdHelper.normalize_item(item_id, self._prefix)
        self._repository.sync()
        index = self._repository.index(short_id)
        if binding is None:
            if index is not None:
                raise SdlcError(f"artifact-bearing item cannot use source-only review: {short_id}")
            return
        self._items.get(short_id)
        if index is None or index.input_digest != binding.digest:
            raise SdlcError(f"review artifact input selection changed: {short_id}")
        bundle = self._repository.get(binding.digest)
        self._source.validate(bundle)
        expected = self._source.binding(bundle)
        if binding != expected or bundle.item_id != short_id or bundle.purpose != "INPUT" or bundle.source_tree != source_tree:
            raise SdlcError(f"review artifact source/input binding mismatch: {short_id}")
        self._source.verify_snapshot(bundle)
        self._source.verify_live(bundle)

    def result_for(self, item_id: str, source_tree: str, input_digest: str) -> ArtifactBinding:
        """Returns the newest verified QA result for the exact source/input pair.

        Args:
            item_id: the reviewed item's identity.
            source_tree: the exact source Git tree.
            input_digest: the current complete input selection.

        Returns:
            The latest matching durable result with a verified local snapshot.

        Raises:
            SdlcError: input selection changed, no result matches, or result bytes changed.
        """
        short_id = self._item(item_id)
        index = self._repository.index(short_id)
        if index is None or index.input_digest != input_digest:
            raise SdlcError(f"QA result input selection changed: {short_id}")
        inputs = self._repository.get(input_digest)
        if inputs.item_id != short_id or inputs.purpose != "INPUT" or inputs.source_tree != source_tree:
            raise SdlcError(f"QA result source/input binding mismatch: {short_id}")
        for digest in reversed(index.result_digests):
            bundle = self._repository.get(digest)
            self._source.validate(bundle)
            if bundle.item_id != short_id or bundle.purpose != "RESULT":
                raise SdlcError(f"QA result index ownership or purpose mismatch: {short_id}")
            if bundle.source_tree == source_tree and bundle.input_digest == input_digest:
                self._source.verify_snapshot(bundle)
                return self._source.binding(bundle)
        raise SdlcError(f"missing QA RESULT for {short_id} source {source_tree} input {input_digest}")
