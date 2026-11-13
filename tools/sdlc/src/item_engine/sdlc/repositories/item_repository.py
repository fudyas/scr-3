from typing import Callable, Dict, List, Optional

from sdlc.models.errors import ItemNotFoundError
from sdlc.models.item import Item
from sdlc.models.ledger import LedgerChange
from sdlc.repositories.ledger_ids import IDS_FILE, LedgerIdHelper
from sdlc.repositories.ledger_repository import LedgerRepository, LedgerSnapshot

# Ledger directory that holds one folder per item
ITEMS_DIR = "items"


class ItemRepository:
    """Stores items, their plans, and their reviews on the shared ledger."""

    def __init__(self, ledger: LedgerRepository, prefix: str) -> None:
        """Initializes the repository.

        Args:
            ledger: the ledger repository that serializes writes.
            prefix: the item id prefix, such as `ITM`.
        """
        self._ledger = ledger
        self._prefix = prefix

    def as_of(self) -> Optional[str]:
        """Returns the date of the local ledger mirror, or None before the first sync."""
        return self._ledger.as_of()

    def sync(self) -> Optional[str]:
        """Refreshes the local ledger mirror and returns the remote commit."""
        return self._ledger.sync()

    def list_items(self, snapshot: Optional[LedgerSnapshot] = None) -> List[Item]:
        """Returns every item, ordered by number."""
        view = snapshot or self._ledger.snapshot()
        paths = [path for path in view.list_paths(ITEMS_DIR) if path.endswith("/item.json")]
        texts = view.read_texts(paths)
        items = [Item.model_validate_json(text) for text in texts.values() if text]
        return sorted(items, key=lambda item: item.number)

    def get(self, short_id: str, snapshot: Optional[LedgerSnapshot] = None) -> Item:
        """Returns one item.

        Raises:
            ItemNotFoundError: the ledger holds no item with the id.
        """
        view = snapshot or self._ledger.snapshot()
        text = view.read_text(self._item_path(short_id))
        if text is None:
            raise ItemNotFoundError(f"no item {short_id} on the ledger (run `lets sdlc sync`?)")
        return Item.model_validate_json(text)

    def read_plan(self, short_id: str) -> Optional[str]:
        """Returns the item's committed plan, or None when it has none."""
        return self._ledger.snapshot().read_text(self._plan_path(short_id))

    def read_review(self, short_id: str) -> Optional[str]:
        """Returns the item's committed review, or None when it has none."""
        return self._ledger.snapshot().read_text(self._review_path(short_id))

    def mint(self, build: Callable[[int], Item]) -> Item:
        """Allocates the next item number across all hosts and stores the built item.

        Args:
            build: creates the item for the allocated number.

        Returns:
            The stored item.
        """
        def mutator(snapshot: LedgerSnapshot) -> LedgerChange:
            """Returns the change that allocates the next number and writes the item."""
            highest_existing = max((item.number for item in self.list_items(snapshot)), default=0)
            allocation = LedgerIdHelper.allocate(snapshot, self._prefix, highest_existing)
            item = build(allocation.number)
            return LedgerChange(
                changes={
                    IDS_FILE: allocation.ids_text,
                    self._item_path(item.short_id): self._serialize(item),
                },
                message=f"{item.full_id}: mint",
                result=item,
            )

        return self._ledger.transact(mutator)

    def modify(self, short_id: str, change: Callable[[Item, Dict[str, Item]], Item], message: str,
               plan_text: Optional[str] = None, review_text: Optional[str] = None) -> Item:
        """Applies a change to one item on fresh ledger data and stores the result.

        Args:
            short_id: the item to change.
            change: returns the changed item from the current item and every item by short id;
                it raises to refuse the change.
            message: the ledger commit message.
            plan_text: a new plan document to store with the item, if any.
            review_text: a new review document to store with the item, if any.

        Returns:
            The stored item.

        Raises:
            ItemNotFoundError: the ledger holds no item with the id.
        """
        def mutator(snapshot: LedgerSnapshot) -> LedgerChange:
            """Returns the change that writes the updated item, plan, and review."""
            all_items = {item.short_id: item for item in self.list_items(snapshot)}
            if short_id not in all_items:
                raise ItemNotFoundError(f"no item {short_id} on the ledger")
            updated = change(all_items[short_id], all_items)
            changes: Dict[str, Optional[str]] = {self._item_path(short_id): self._serialize(updated)}
            if plan_text is not None:
                changes[self._plan_path(short_id)] = plan_text
            if review_text is not None:
                changes[self._review_path(short_id)] = review_text
            return LedgerChange(changes=changes, message=f"{updated.full_id}: {message}", result=updated)

        return self._ledger.transact(mutator)

    @staticmethod
    def _item_path(short_id: str) -> str:
        """Returns the ledger path of an item record."""
        return f"{ITEMS_DIR}/{short_id}/item.json"

    @staticmethod
    def _plan_path(short_id: str) -> str:
        """Returns the ledger path of an item plan."""
        return f"{ITEMS_DIR}/{short_id}/PLAN.md"

    @staticmethod
    def _review_path(short_id: str) -> str:
        """Returns the ledger path of an item review."""
        return f"{ITEMS_DIR}/{short_id}/REVIEW.md"

    @staticmethod
    def _serialize(item: Item) -> str:
        """Returns the stable JSON text of an item record."""
        return item.model_dump_json(indent=2) + "\n"
