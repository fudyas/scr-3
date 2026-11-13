from pathlib import Path
from typing import Dict

from sdlc.algorithms.item_ids import ItemIdHelper
from sdlc.algorithms.record_history import RecordHistoryHelper
from sdlc.algorithms.review_parser import ReviewParser
from sdlc.datasources.draft_source import DraftSource
from sdlc.models.errors import SdlcError
from sdlc.models.item import Item
from sdlc.repositories.item_repository import ItemRepository
from sdlc.repositories.telemetry_repository import TelemetryRepository


class ReviewUsecases:
    """Drafts, validates, and commits the user's review of an item, which ranks above its plan."""

    def __init__(self, items: ItemRepository, drafts: DraftSource, telemetry: TelemetryRepository,
                 template_path: Path, prefix: str, host: str) -> None:
        """Initializes the usecases.

        Args:
            items: the item repository.
            drafts: the local review drafts.
            telemetry: the telemetry repository that records review events.
            template_path: the review template a new draft starts from.
            prefix: the item id prefix, such as `ITM`.
            host: this host's name, recorded in history.
        """
        self._items = items
        self._drafts = drafts
        self._telemetry = telemetry
        self._template_path = template_path
        self._prefix = prefix
        self._host = host

    def edit(self, item_id: str) -> Path:
        """Returns the draft path, creating the draft from the committed review or the template.

        Raises:
            ItemNotFoundError: the item does not exist.
        """
        item = self._items.get(self._short_id(item_id))
        if self._drafts.read(item.short_id) is None:
            committed = self._items.read_review(item.short_id)
            template = self._template_path.read_text(encoding="utf-8").replace("{{ITEM_ID}}", item.full_id)
            self._drafts.write(item.short_id, committed or template)
        return self._drafts.path(item.short_id)

    def check(self, item_id: str) -> int:
        """Returns the number of decisions in the draft when it passes every review rule.

        Raises:
            SdlcError: the item has no draft.
            ReviewValidationError: the draft breaks one or more rules.
        """
        short_id = self._short_id(item_id)
        text = self._drafts.read(short_id)
        if text is None:
            raise SdlcError(f"{short_id} has no review draft; run `lets sdlc items review edit {short_id}` first")
        return ReviewParser.validate(text)

    def commit(self, item_id: str) -> Item:
        """Lands the validated draft on the ledger as the item's review. The plan and the item status stay as they are.

        Returns:
            The stored item.

        Raises:
            ReviewValidationError: the draft breaks the review rules.
        """
        short_id = self._short_id(item_id)
        decision_count = self.check(short_id)
        text = self._drafts.read(short_id) or ""

        def change(item: Item, all_items: Dict[str, Item]) -> Item:
            """Returns the item with one history entry for the new review."""
            return RecordHistoryHelper.touch(item, {}, self._host, "review_committed", f"{decision_count} decisions")

        committed = self._items.modify(short_id, change, "review committed", review_text=text)
        self._drafts.discard(short_id)
        self._telemetry.record_event("review_committed", short_id, value=decision_count)
        return committed

    def show(self, item_id: str, draft: bool) -> str:
        """Returns the committed review or the local draft.

        Raises:
            SdlcError: the requested review does not exist.
        """
        short_id = self._short_id(item_id)
        text = self._drafts.read(short_id) if draft else self._items.read_review(short_id)
        if text is None:
            raise SdlcError(f"{short_id} has no {'review draft' if draft else 'committed review'}")
        return text

    def _short_id(self, item_id: str) -> str:
        """Returns the short item id, such as `ITM-0001`, for any accepted spelling."""
        return ItemIdHelper.normalize_item(item_id, self._prefix)
