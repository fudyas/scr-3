from pathlib import Path
from typing import List, Optional

from sdlc.algorithms.item_ids import ItemIdHelper
from sdlc.algorithms.promotion_message import PromotionMessageHelper
from sdlc.datasources.worktree_source import INTEGRATION_NAME, WorktreeSource
from sdlc.models.errors import WorktreeError
from sdlc.models.review_session import ReviewSession
from sdlc.models.worktree import PresentedChange, WorktreeInfo


class WorktreeUsecases:
    """Creates and removes the block and integration worktrees of a running item."""

    def __init__(self, worktrees: WorktreeSource, prefix: str) -> None:
        """Initializes the usecases.

        Args:
            worktrees: the worktree data source.
            prefix: the item id prefix, such as `ITM`.
        """
        self._worktrees = worktrees
        self._prefix = prefix

    def add(self, item_id: str, name: str, base: Optional[str]) -> WorktreeInfo:
        """Creates the item worktree for a block or the integration branch, or returns the existing one.

        Raises:
            WorktreeError: the name is neither a block id nor `integration`.
        """
        self._check_name(name)
        if name in ("verification", "promotion"):
            raise WorktreeError("verification and promotion worktrees are created only from review context")
        return self._worktrees.add(ItemIdHelper.normalize_item(item_id, self._prefix), name, base)

    def remove(self, item_id: str, name: str, delete_branch: bool) -> None:
        """Removes an item worktree and, when asked, its merged work branch."""
        self._check_name(name)
        if delete_branch and name in ("verification", "promotion"):
            raise WorktreeError("detached gate worktrees have no work branch to delete")
        self._worktrees.remove(ItemIdHelper.normalize_item(item_id, self._prefix), name, delete_branch)

    def present(self, item_id: str, base: Optional[str]) -> PresentedChange:
        """Shows the item change as staged, uncommitted changes in the integration worktree for review.

        Args:
            item_id: the item id, with or without its DESC slug.
            base: the working branch the item merges into; None means the main checkout's branch.

        Raises:
            WorktreeError: the integration worktree is missing or holds uncommitted changes.
        """
        return self._worktrees.present(ItemIdHelper.normalize_item(item_id, self._prefix),
                                       base or self._worktrees.current_branch())

    def settle(self, item_id: str, message: str, expected_tree: str,
               expected_artifacts: Optional[str] = None) -> Optional[str]:
        """Commits the exact verified and approved tree on top of the built history."""
        return self._worktrees.settle(ItemIdHelper.normalize_item(item_id, self._prefix), message, expected_tree,
                                     expected_artifacts)

    def context(self, item_id: str) -> ReviewSession:
        """Returns the persistent integration workspace and review revision state."""
        return self._worktrees.context(ItemIdHelper.normalize_item(item_id, self._prefix))

    def snapshot(self, item_id: str) -> ReviewSession:
        """Creates the immutable verification worktree for the current review revision."""
        return self._worktrees.snapshot(ItemIdHelper.normalize_item(item_id, self._prefix))

    def verified(self, item_id: str, expected_tree: str,
                 expected_artifacts: Optional[str] = None) -> ReviewSession:
        """Records the exact snapshot that passed validation and QA."""
        return self._worktrees.verified(ItemIdHelper.normalize_item(item_id, self._prefix), expected_tree,
                                       expected_artifacts)

    def approve(self, item_id: str, expected_tree: str,
                expected_artifacts: Optional[str] = None) -> ReviewSession:
        """Records user approval of the exact verified snapshot."""
        return self._worktrees.approve(ItemIdHelper.normalize_item(item_id, self._prefix), expected_tree,
                                      expected_artifacts)

    def prepare_promotion(self, item_id: str, codex_session: Optional[str] = None,
                          expected_artifacts: Optional[str] = None) -> ReviewSession:
        """Prepares the promotion merge in isolation from the user's main-checkout edits.

        Args:
            item_id: the item id, with or without its DESC slug.
            codex_session: the Claude session URL for the merge commit trailer, or None for no trailer.
            expected_artifacts: the exact input digest, required when artifacts are bound.

        Returns:
            The review context with the prepared promotion commit.

        Raises:
            SdlcError: the session URL is blank or spans several lines.
        """
        short_id = ItemIdHelper.normalize_item(item_id, self._prefix)

        # Builds the merge message here so the data source only runs git
        message = PromotionMessageHelper.build(self._worktrees.branch(short_id, INTEGRATION_NAME), short_id,
                                               codex_session)
        return self._worktrees.prepare_promotion(short_id, message, expected_artifacts)

    def promote(self, item_id: str, expected_commit: str,
                expected_artifacts: Optional[str] = None) -> str:
        """Installs the exact tested merge while preserving unrelated main-checkout edits."""
        return self._worktrees.promote(ItemIdHelper.normalize_item(item_id, self._prefix), expected_commit,
                                      expected_artifacts)

    def fingerprint(self, item_id: str) -> str:
        """Returns the tree hash of the whole integration working tree."""
        return self._worktrees.fingerprint(ItemIdHelper.normalize_item(item_id, self._prefix))

    def list_paths(self, item_id: str) -> List[Path]:
        """Returns the worktree paths that exist for the item."""
        return self._worktrees.list_for_item(ItemIdHelper.normalize_item(item_id, self._prefix))

    @staticmethod
    def _check_name(name: str) -> None:
        """Checks that a worktree name is a block id or `integration`.

        Raises:
            WorktreeError: the name is not allowed.
        """
        if name not in (INTEGRATION_NAME, "verification", "promotion") and not ItemIdHelper.is_block_id(name):
            raise WorktreeError(f"worktree name must be a block id or {INTEGRATION_NAME!r}: {name!r}")
