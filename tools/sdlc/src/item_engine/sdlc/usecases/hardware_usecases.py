import hashlib
from pathlib import Path
from typing import Dict, Optional, TYPE_CHECKING

from sdlc.algorithms.timestamps import TimestampHelper
from sdlc.datasources.git_command import GitCommandRunner
from sdlc.models.errors import SdlcError
from sdlc.models.item import HardwareAcceptance, Item, ItemStatus
from sdlc.models.record import HistoryEntry

if TYPE_CHECKING:
    from sdlc.wiring import AppWiring


class HardwareUsecases:
    """Records developer hardware results without granting device access."""

    def __init__(self, wiring: AppWiring) -> None:
        """Initializes the item ledger and review context dependencies."""
        self._wiring = wiring

    def record(self, action: str, item_id: str, deb: Optional[str], image_identity: Optional[str],
               notes_file: Optional[str], confirmed_by_developer: bool) -> Item:
        """Records hardware authority or a result for the installed promotion.

        Args:
            action: require, pass, or fail.
            item_id: the item whose hardware evidence changes.
            deb: the delivered package file for a result.
            image_identity: the tested hardware and image identity.
            notes_file: the developer's complete report.
            confirmed_by_developer: explicit developer confirmation of success.

        Returns:
            The updated item with append-only history.

        Raises:
            SdlcError: identity, approval, or developer evidence is missing.
        """
        items = self._wiring.items
        short_id = self._wiring.item_usecases.normalize_id(item_id)
        values = HardwareAcceptance(required=True)

        # Binds real-hardware results to the promoted, approved revision
        if action != "require":
            if not deb or not image_identity or not image_identity.strip() or not notes_file:
                raise SdlcError("hardware results require --deb, --image-identity, and --notes-file")
            if action == "pass" and not confirmed_by_developer:
                raise SdlcError("hardware success requires --confirmed-by-developer")
            context = self._wiring.worktree_usecases.context(short_id)
            if context.phase != "DONE" or not context.promotion_commit or not context.approved_tree:
                raise SdlcError("hardware results require an installed approved promotion")
            current_item = items.get(short_id)
            if current_item.status != ItemStatus.REVIEW:
                raise SdlcError("hardware results require the REVIEW hardware gate")
            if self._wiring.worktree_usecases.fingerprint(short_id) != context.approved_tree:
                raise SdlcError("integration changed after approval; verify and approve again")
            report = Path(notes_file).read_text(encoding="utf-8")
            if not report.strip():
                raise SdlcError("hardware report must not be empty")
            package = Path(deb).resolve()
            if not package.is_relative_to(context.worktree.resolve()):
                raise SdlcError("--deb must belong to the retained integration worktree")
            relative = package.relative_to(context.worktree.resolve()).as_posix()
            delivered = GitCommandRunner(self._wiring.settings.main_root).run_binary(
                ["show", f"{context.promotion_commit}:{relative}"], b""
            )
            with package.open("rb") as package_file:
                package_hash = hashlib.file_digest(package_file, "sha256").hexdigest()
            if hashlib.sha256(delivered).hexdigest() != package_hash:
                raise SdlcError("hardware package differs from the approved promoted artifact")
            values = HardwareAcceptance(
                required=True, result=action, package_sha256=package_hash,
                package_path=relative, promotion_commit=context.promotion_commit,
                image_identity=image_identity, notes=report, confirmed_at=TimestampHelper.now(),
            )

        def change(item: Item, all_items: Dict[str, Item]) -> Item:
            """Returns the item with hardware evidence and the original report in history."""
            if item.status in (ItemStatus.DONE, ItemStatus.OBSOLETE):
                raise SdlcError("terminal hardware evidence is immutable")
            if item.host and item.host != self._wiring.settings.host:
                raise SdlcError(f"item is claimed by host {item.host}")
            if action == "require" and item.hardware.required:
                return item
            entry = HistoryEntry(at=TimestampHelper.now(), host=self._wiring.settings.host,
                                 event="hardware", detail=values.model_dump_json())
            return item.model_copy(update={"hardware": values, "history": [*item.history, entry]})

        return items.modify(short_id, change, f"hardware {action}")

    def check_completion(self, item: Item) -> None:
        """Rejects stale hardware acceptance before item completion.

        Args:
            item: the item that requests DONE.

        Raises:
            SdlcError: approval, package, or promotion changed after hardware acceptance.
        """
        if not item.hardware.required:
            return
        context = self._wiring.worktree_usecases.context(item.short_id)
        if context.phase != "DONE" or context.promotion_commit != item.hardware.promotion_commit:
            raise SdlcError("hardware acceptance does not cover the current installed promotion")
        if self._wiring.worktree_usecases.fingerprint(item.short_id) != context.approved_tree:
            raise SdlcError("integration changed after hardware acceptance")
