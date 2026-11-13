from abc import ABC
from typing import Dict, List

from sdlc.algorithms.desc_slug import DescSlugHelper
from sdlc.algorithms.record_history import RecordHistoryHelper, TrackedRecord
from sdlc.models.chain import ChainStatus
from sdlc.models.errors import AmendmentRefusedError
from sdlc.models.item import ItemStatus
from sdlc.models.record import RecordAmendment

# Item statuses in which the text of an item can still change
AMENDABLE_ITEM_STATUSES = (ItemStatus.BACKLOG, ItemStatus.PLANNED)

# Amendable fields in the order the rules check and report them
AMENDABLE_FIELDS = ("desc", "idea", "description")

# Hints that tell the user what to do for each refused item status
ITEM_STATUS_HINTS: Dict[ItemStatus, str] = {
    ItemStatus.SCHEDULED: "; run `items unschedule {short_id}` first",
    ItemStatus.IN_PROGRESS: "; the run has started, so record changes in the review",
    ItemStatus.TESTING: "; the run has started, so record changes in the review",
    ItemStatus.REVIEW: "; the run has started, so record changes in the review",
    ItemStatus.DONE: "; the item is closed",
    ItemStatus.OBSOLETE: "; the item is closed",
}


class RecordAmendmentHelper(ABC):
    """Checks the amend rules and builds the amended copy of an item or chain."""

    @staticmethod
    def check_item_status(short_id: str, status: ItemStatus) -> None:
        """Checks that an item in the given status can be amended.

        Args:
            short_id: the item's short id, for the message.
            status: the item's status now.

        Raises:
            AmendmentRefusedError: the item has left BACKLOG and PLANNED.
        """
        if status in AMENDABLE_ITEM_STATUSES:
            return
        hint = ITEM_STATUS_HINTS[status].format(short_id=short_id)
        raise AmendmentRefusedError(
            f"{short_id} is {status.value}; only BACKLOG and PLANNED items can be amended{hint}"
        )

    @staticmethod
    def check_chain_status(short_id: str, status: ChainStatus) -> None:
        """Checks that a chain in the given rolled-up status can be amended.

        Args:
            short_id: the chain's short id, for the message.
            status: the chain's rolled-up status now.

        Raises:
            AmendmentRefusedError: the chain is DONE.
        """
        if status == ChainStatus.DONE:
            raise AmendmentRefusedError(f"{short_id} is DONE; a DONE chain cannot be amended")

    @staticmethod
    def apply(record: TrackedRecord, amendment: RecordAmendment, host: str) -> TrackedRecord:
        """Returns the record with the amended fields and one `amended` history entry.

        Steps:
            1. Walk the fields in the order desc, idea, description and skip those the amendment leaves `None`.
            2. Refuse a field the record lacks and a value that is empty after stripping.
            3. Validate a DESC slug and skip a value equal to the current one.
            4. Refuse the amendment when no field changes, else record the new and the old values.

        Args:
            record: the item or chain before the amendment.
            amendment: the replacement text per field.
            host: the host that makes the change.

        Returns:
            The amended copy, with the old values in the new history entry.

        Raises:
            AmendmentRefusedError: a field is missing, empty, or unchanged, or no field changes.
            InvalidDescError: the DESC slug breaks the notation rules.
        """
        updates: Dict[str, object] = {}
        previous: Dict[str, str] = {}
        changes: List[str] = []
        for field in AMENDABLE_FIELDS:
            requested = getattr(amendment, field)
            if requested is None:
                continue

            # Refuses a field that this record type does not carry
            if not hasattr(record, field):
                raise AmendmentRefusedError(f"{record.short_id} has no {field} field")
            value = requested.strip()
            if not value:
                raise AmendmentRefusedError(f"{field} must not be empty")
            if field == "desc":
                DescSlugHelper.validate(value)
            current = getattr(record, field)
            if value == current:
                continue

            # Keeps the new value, the old value, and the one-line change summary
            updates[field] = value
            previous[field] = current
            changes.append(f"desc {current} -> {value}" if field == "desc" else field)
        if not updates:
            raise AmendmentRefusedError("the amendment changes no field")
        return RecordHistoryHelper.touch(record, updates, host, "amended", ", ".join(changes), previous=previous)
