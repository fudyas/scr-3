from typing import Callable, Dict, List, Optional

from sdlc.algorithms.dependency_graph import DependencyGraphHelper
from sdlc.algorithms.desc_slug import DescSlugHelper
from sdlc.algorithms.item_ids import ItemIdHelper
from sdlc.algorithms.record_amendment import RecordAmendmentHelper
from sdlc.algorithms.record_history import RecordHistoryHelper
from sdlc.algorithms.status_rules import StatusRulesHelper
from sdlc.algorithms.timestamps import TimestampHelper
from sdlc.algorithms.unique_values import UniqueValuesHelper
from sdlc.models.errors import DependencyError, InvalidTransitionError, ItemClaimError
from sdlc.models.item import Item, ItemKind, ItemStatus
from sdlc.models.record import HistoryEntry, RecordAmendment
from sdlc.models.views import DependencyReport
from sdlc.repositories.item_repository import ItemRepository
from sdlc.repositories.telemetry_repository import TelemetryRepository

# Statuses in which an item no longer blocks or waits on anything
TERMINAL_STATUSES = (ItemStatus.DONE, ItemStatus.OBSOLETE)


class ItemUsecases:
    """Mints items and changes their metadata, dependencies, and lifecycle status."""

    def __init__(self, items: ItemRepository, telemetry: TelemetryRepository, prefix: str, host: str,
                 completion_check: Optional[Callable[[Item], None]] = None) -> None:
        """Initializes the usecases.

        Args:
            items: the item repository.
            telemetry: the telemetry repository that records status events.
            prefix: the item id prefix, such as `ITM`.
            host: this host's name, used to claim items.
            completion_check: optional check that rejects stale acceptance before DONE.
        """
        self._items = items
        self._telemetry = telemetry
        self._prefix = prefix
        self._host = host
        self._completion_check = completion_check

    def normalize_id(self, text: str) -> str:
        """Returns the short item id for a short or full item id."""
        return ItemIdHelper.normalize_item(text, self._prefix)

    def sync(self) -> Optional[str]:
        """Refreshes the local ledger mirror and returns the remote commit."""
        return self._items.sync()

    def as_of(self) -> Optional[str]:
        """Returns the date of the local ledger mirror."""
        return self._items.as_of()

    def mint(self, kind: ItemKind, desc: str, idea: str, description: str, tags: List[str],
             depends_on: List[str]) -> Item:
        """Mints a new BACKLOG item with a cross-host unique number.

        Args:
            kind: the kind of work.
            desc: the DESC slug of the item id.
            idea: the user's idea in the user's own words.
            description: the normalized, longer statement of the idea.
            tags: free-text labels.
            depends_on: ids of items this item depends on.

        Returns:
            The minted item.

        Raises:
            InvalidDescError: the slug breaks the notation rules.
            DependencyError: a dependency names an unknown item.
        """
        DescSlugHelper.validate(desc)
        dependencies = [self.normalize_id(dependency) for dependency in depends_on]
        now = TimestampHelper.now()

        def build(number: int) -> Item:
            """Returns the new item for the allocated number."""
            return Item(
                prefix=self._prefix, number=number, desc=desc, kind=kind, idea=idea.strip(),
                description=description.strip(), tags=UniqueValuesHelper.ordered(tags),
                depends_on=dependencies,
                created_at=now, updated_at=now,
                history=[HistoryEntry(at=now, host=self._host, event="minted", detail=ItemStatus.BACKLOG.value)],
            )

        self.sync()
        known = {item.short_id for item in self._items.list_items()}
        unknown = [dependency for dependency in dependencies if dependency not in known]
        if unknown:
            raise DependencyError(f"unknown dependencies: {', '.join(unknown)}")
        item = self._items.mint(build)
        self._telemetry.record_event("item_minted", item.short_id, status_to=item.status.value,
                                     detail={"kind": item.kind.value})
        return item

    def get(self, item_id: str) -> Item:
        """Returns one item from the local ledger mirror."""
        return self._items.get(self.normalize_id(item_id))

    def list_items(self, statuses: List[ItemStatus], tags: List[str]) -> List[Item]:
        """Returns the items that match every filter; empty filters match all."""
        items = self._items.list_items()
        if statuses:
            items = [item for item in items if item.status in statuses]
        if tags:
            items = [item for item in items if all(tag in item.tags for tag in tags)]
        return items

    def change_tags(self, item_id: str, added: List[str], removed: List[str]) -> Item:
        """Adds and removes free-text tags on an item."""
        def change(item: Item, all_items: Dict[str, Item]) -> Item:
            """Returns the item with its tags updated."""
            tags = UniqueValuesHelper.ordered([tag for tag in item.tags if tag not in removed] + added)
            return self._touch(item, {"tags": tags}, "tags", ", ".join(tags))

        return self._items.modify(self.normalize_id(item_id), change, "tags")

    def amend(self, item_id: str, amendment: RecordAmendment) -> Item:
        """Replaces the idea, description, or DESC slug of an item that has not started.

        The plan, its approval, and the item status stay unchanged.

        Args:
            item_id: the item to amend.
            amendment: the replacement text per field.

        Returns:
            The stored item with one `amended` history entry that keeps the old values.

        Raises:
            AmendmentRefusedError: the item is past PLANNED, or the amendment is empty or changes no field.
            InvalidDescError: the DESC slug breaks the notation rules.
            ItemNotFoundError: the item does not exist.
        """
        def change(item: Item, all_items: Dict[str, Item]) -> Item:
            """Returns the amended item after the status guard passes."""
            RecordAmendmentHelper.check_item_status(item.short_id, item.status)
            return RecordAmendmentHelper.apply(item, amendment, self._host)

        return self._items.modify(self.normalize_id(item_id), change, "amend")

    def set_dependencies(self, item_id: str, depends_on: List[str]) -> Item:
        """Replaces an item's dependencies, refusing unknown ids and cycles.

        Raises:
            DependencyError: a dependency is unknown, the item itself, or closes a cycle.
        """
        short_id = self.normalize_id(item_id)
        dependencies = UniqueValuesHelper.ordered([self.normalize_id(dependency) for dependency in depends_on])

        def change(item: Item, all_items: Dict[str, Item]) -> Item:
            """Returns the item with its dependencies replaced after the graph checks pass."""
            if short_id in dependencies:
                raise DependencyError(f"{short_id} cannot depend on itself")
            unknown = [dependency for dependency in dependencies if dependency not in all_items]
            if unknown:
                raise DependencyError(f"unknown dependencies: {', '.join(unknown)}")
            graph = {key: value.depends_on for key, value in all_items.items()}
            graph[short_id] = dependencies
            cycle = DependencyGraphHelper.find_cycle(graph)
            if cycle is not None:
                raise DependencyError(f"dependency cycle: {' -> '.join(cycle)}")
            return self._touch(item, {"depends_on": dependencies}, "depends", ", ".join(dependencies) or "none")

        return self._items.modify(short_id, change, "depends")

    def check_dependencies(self, item_id: str) -> DependencyReport:
        """Returns whether every dependency of the item is DONE."""
        short_id = self.normalize_id(item_id)
        items = {item.short_id: item for item in self._items.list_items()}
        statuses = {key: item.status for key, item in items.items()}
        unmet = DependencyGraphHelper.unmet_dependencies(self._items.get(short_id).depends_on, statuses)
        described = [f"{dependency} ({statuses[dependency].value if dependency in statuses else 'unknown'})"
                     for dependency in unmet]
        return DependencyReport(item_id=short_id, ready=not unmet, unmet=described)

    def set_status(self, item_id: str, target: ItemStatus, force: bool) -> Item:
        """Moves an item through its lifecycle, enforcing claims, dependencies, and completion.

        Args:
            item_id: the item to move.
            target: the new status.
            force: whether to take over an item another host claims.

        Returns:
            The stored item.

        Raises:
            InvalidTransitionError: the lifecycle or a status guard refuses the change, REVIEW finds a task that
                is not VALIDATED, or DONE finds a task that is not DONE.
            DependencyError: a dependency is not DONE, or an active item depends on the item being obsoleted.
            ItemClaimError: another host runs the item.
        """
        short_id = self.normalize_id(item_id)
        previous: Dict[str, ItemStatus] = {}

        def change(item: Item, all_items: Dict[str, Item]) -> Item:
            """Returns the item in its new status after every guard passes."""
            previous["status"] = item.status
            StatusRulesHelper.check_item(item.status, target)
            updates = self._status_updates(item, target, all_items, force)
            return self._touch(item, updates, "status", f"{item.status.value} -> {target.value}")

        updated = self._items.modify(short_id, change, f"status {target.value}")
        self._telemetry.record_event("item_status", short_id, status_from=previous["status"].value,
                                     status_to=target.value)
        return updated

    def _status_updates(self, item: Item, target: ItemStatus, all_items: Dict[str, Item],
                        force: bool) -> Dict[str, object]:
        """Returns the field updates a status change implies, after its guards pass.

        Args:
            item: the item before the change.
            target: the new status.
            all_items: every item by short id.
            force: whether to take over an item another host claims.

        Returns:
            The fields to set on the item.

        Raises:
            InvalidTransitionError: a status guard refuses the change.
            DependencyError: a dependency guard refuses the change.
            ItemClaimError: another host runs the item.
        """
        updates: Dict[str, object] = {"status": target}
        if target == ItemStatus.IN_PROGRESS and item.hardware.required:
            updates["hardware"] = item.hardware.model_copy(update={"result": None, "confirmed_at": None})
        claimed_elsewhere = item.host is not None and item.host != self._host
        if target == ItemStatus.PLANNED and item.status == ItemStatus.BACKLOG:
            raise InvalidTransitionError("an item becomes PLANNED only through `items plan approve`")
        if target == ItemStatus.SCHEDULED and item.status == ItemStatus.PLANNED:
            raise InvalidTransitionError("an item becomes SCHEDULED only through `items schedule`")
        if target == ItemStatus.PLANNED:
            updates["queue_rank"] = None

        # Claims the item for this host when a run starts, after its dependencies are DONE
        if target == ItemStatus.IN_PROGRESS and item.status == ItemStatus.SCHEDULED:
            statuses = {key: value.status for key, value in all_items.items()}
            unmet = DependencyGraphHelper.unmet_dependencies(item.depends_on, statuses)
            if unmet:
                raise DependencyError(f"{item.short_id} is blocked by: {', '.join(unmet)}")
            if claimed_elsewhere and not force:
                raise ItemClaimError(f"{item.short_id} is claimed by host {item.host}")
            updates["host"] = self._host
        elif target in (ItemStatus.IN_PROGRESS, ItemStatus.TESTING, ItemStatus.REVIEW, ItemStatus.DONE) \
                and claimed_elsewhere:
            if not force:
                raise ItemClaimError(f"{item.short_id} runs on host {item.host}; use --force to take it over")
            updates["host"] = self._host

        # Releases the claim when a run aborts back to the queue
        if target == ItemStatus.SCHEDULED:
            updates["host"] = None

        # Requires the tasks to have reached the status the target item status needs
        StatusRulesHelper.check_item_tasks(
            target, {task_id: task.status for task_id, task in item.tasks.items()}
        )
        if target == ItemStatus.DONE and item.hardware.required and item.hardware.result != "pass":
            raise InvalidTransitionError("developer-confirmed real-hardware success required before DONE")
        if target == ItemStatus.DONE and self._completion_check is not None:
            self._completion_check(item)
        if target == ItemStatus.DONE:
            updates["queue_rank"] = None
        if target == ItemStatus.OBSOLETE:
            dependents = [key for key, value in all_items.items()
                          if item.short_id in value.depends_on and value.status not in TERMINAL_STATUSES]
            if dependents:
                raise DependencyError(
                    f"active items depend on {item.short_id}: {', '.join(dependents)}; change their dependencies first"
                )
            updates["queue_rank"] = None
        return updates

    def _touch(self, item: Item, updates: Dict[str, object], event: str, detail: str) -> Item:
        """Returns a copy of the item with the updates recorded in its history by this host."""
        return RecordHistoryHelper.touch(item, updates, self._host, event, detail)
