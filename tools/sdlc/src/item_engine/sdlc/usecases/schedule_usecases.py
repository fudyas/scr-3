from typing import Dict, List, Optional

from sdlc.algorithms.dependency_graph import DependencyGraphHelper
from sdlc.algorithms.item_ids import ItemIdHelper
from sdlc.algorithms.queue_rank import QueueRankHelper
from sdlc.algorithms.record_history import RecordHistoryHelper
from sdlc.models.errors import InvalidTransitionError
from sdlc.models.item import Item, ItemStatus
from sdlc.models.views import QueueEntry
from sdlc.repositories.item_repository import ItemRepository
from sdlc.repositories.telemetry_repository import TelemetryRepository

# Item statuses that hold a place in the run queue
QUEUED_STATUSES = (ItemStatus.SCHEDULED, ItemStatus.IN_PROGRESS, ItemStatus.TESTING, ItemStatus.REVIEW)


class ScheduleUsecases:
    """Orders approved items into the run queue and picks the next one to run."""

    def __init__(self, items: ItemRepository, telemetry: TelemetryRepository, prefix: str, host: str) -> None:
        """Initializes the usecases.

        Args:
            items: the item repository.
            telemetry: the telemetry repository that records schedule events.
            prefix: the item id prefix, such as `ITM`.
            host: this host's name, recorded in history.
        """
        self._items = items
        self._telemetry = telemetry
        self._prefix = prefix
        self._host = host

    def schedule(self, item_id: str, before: Optional[str]) -> Item:
        """Puts a PLANNED item into the run queue, or moves a SCHEDULED item within it.

        Args:
            item_id: the item to schedule.
            before: an item to place it directly before; None places it last.

        Returns:
            The stored SCHEDULED item.

        Raises:
            InvalidTransitionError: the item is not PLANNED or SCHEDULED, its plan lacks approval,
                or the `before` item is not queued.
        """
        short_id = ItemIdHelper.normalize_item(item_id, self._prefix)
        before_id = ItemIdHelper.normalize_item(before, self._prefix) if before else None

        def change(item: Item, all_items: Dict[str, Item]) -> Item:
            """Returns the item with its queue rank and SCHEDULED status."""
            if item.status not in (ItemStatus.PLANNED, ItemStatus.SCHEDULED):
                raise InvalidTransitionError(f"{short_id} is {item.status.value}; only a PLANNED item is scheduled")
            if not item.plan.is_approved:
                raise InvalidTransitionError(f"{short_id} has no approved plan")
            ranks = [other.queue_rank for key, other in all_items.items()
                     if key != short_id and other.queue_rank is not None and other.status in QUEUED_STATUSES]
            rank = QueueRankHelper.rank_last(ranks)
            if before_id is not None:
                target = all_items.get(before_id)
                if target is None or target.queue_rank is None or target.status != ItemStatus.SCHEDULED:
                    raise InvalidTransitionError(f"{before_id} is not SCHEDULED")
                rank = QueueRankHelper.rank_before(ranks, target.queue_rank)
            detail = f"before {before_id}" if before_id else "last"
            return RecordHistoryHelper.touch(item, {"status": ItemStatus.SCHEDULED, "queue_rank": rank},
                                           self._host, "scheduled", detail)

        scheduled = self._items.modify(short_id, change, "scheduled")
        self._telemetry.record_event("item_scheduled", short_id, status_to=ItemStatus.SCHEDULED.value)
        return scheduled

    def unschedule(self, item_id: str) -> Item:
        """Takes a SCHEDULED item out of the run queue, back to PLANNED.

        Raises:
            InvalidTransitionError: the item is not SCHEDULED.
        """
        short_id = ItemIdHelper.normalize_item(item_id, self._prefix)

        def change(item: Item, all_items: Dict[str, Item]) -> Item:
            """Returns the item back in PLANNED without a queue rank."""
            if item.status != ItemStatus.SCHEDULED:
                raise InvalidTransitionError(f"{short_id} is {item.status.value}; only a SCHEDULED item is unscheduled")
            return RecordHistoryHelper.touch(item, {"status": ItemStatus.PLANNED, "queue_rank": None},
                                           self._host, "unscheduled", "")

        unscheduled = self._items.modify(short_id, change, "unscheduled")
        self._telemetry.record_event("item_unscheduled", short_id, status_to=ItemStatus.PLANNED.value)
        return unscheduled

    def queue(self) -> List[QueueEntry]:
        """Returns running items first, then scheduled items in rank order, each with its readiness."""
        items = self._items.list_items()
        statuses = {item.short_id: item.status for item in items}
        queued = [item for item in items if item.status in QUEUED_STATUSES]
        queued.sort(key=lambda item: (item.status == ItemStatus.SCHEDULED, item.queue_rank or 0.0, item.number))
        entries = []
        for item in queued:
            unmet = DependencyGraphHelper.unmet_dependencies(item.depends_on, statuses)
            entries.append(QueueEntry(item=item, ready=not unmet, unmet=unmet))
        return entries

    def next_ready(self) -> Optional[Item]:
        """Returns the first SCHEDULED item whose dependencies are DONE and that no host claims."""
        for entry in self.queue():
            if entry.item.status == ItemStatus.SCHEDULED and entry.ready and entry.item.host is None:
                return entry.item
        return None
