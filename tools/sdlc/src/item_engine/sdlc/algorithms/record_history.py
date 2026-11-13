from abc import ABC
from typing import Dict, Optional, TypeVar

from sdlc.algorithms.timestamps import TimestampHelper
from sdlc.models.record import HistoryEntry, LedgerRecord

# Any ledger record type that keeps a history trail
TrackedRecord = TypeVar("TrackedRecord", bound=LedgerRecord)


class RecordHistoryHelper(ABC):
    """Applies field updates to a ledger record and records them in its history trail."""

    @staticmethod
    def touch(record: TrackedRecord, updates: Dict[str, object], host: str, event: str,
              detail: str, previous: Optional[Dict[str, str]] = None) -> TrackedRecord:
        """Returns a copy of the record with the updates, a fresh timestamp, and one history entry.

        Args:
            record: the item or chain before the change.
            updates: the fields to set.
            host: the host that makes the change.
            event: the history event name, such as `status`.
            detail: a one-line description of the change.
            previous: the old values of the fields that the event replaced, if any.

        Returns:
            The updated copy.
        """
        now = TimestampHelper.now()
        entry = HistoryEntry(at=now, host=host, event=event, detail=detail, previous=previous or {})
        history = record.history + [entry]
        return record.model_copy(update={**updates, "updated_at": now, "history": history})
