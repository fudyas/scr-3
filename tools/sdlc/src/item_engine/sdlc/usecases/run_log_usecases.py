import time
from typing import Callable, Iterator, List, Optional

from sdlc.algorithms.item_ids import ItemIdHelper
from sdlc.models.run_log import LogEntry, LogLevel
from sdlc.repositories.run_log_repository import RunLogRepository


class RunLogUsecases:
    """Writes and tails the per-item run log that gives the autonomous run its visibility."""

    def __init__(self, repository: RunLogRepository, item_prefix: str,
                 poll_seconds: float = 1.0, sleep: Callable[[float], None] = time.sleep) -> None:
        """Initializes the usecases.

        Args:
            repository: the run-log store.
            item_prefix: the item id prefix, such as `ITM`.
            poll_seconds: the wait between reads while following a log.
            sleep: the wait function, replaceable in tests.
        """
        self._repository = repository
        self._item_prefix = item_prefix
        self._poll_seconds = poll_seconds
        self._sleep = sleep

    def write(self, item: str, role: str, message: str, level: LogLevel,
              task: Optional[str], block: Optional[str]) -> LogEntry:
        """Appends one line to an item's run log."""
        item_id = ItemIdHelper.normalize_item(item, self._item_prefix)
        return self._repository.append(item_id, role, message, level, task, block)

    def tail(self, item: str, follow: bool, role: Optional[str], lines: Optional[int]) -> Iterator[LogEntry]:
        """Yields an item's run-log lines, optionally following new ones until interrupted.

        Args:
            item: a short or full item id.
            follow: whether to keep yielding lines as agents append them.
            role: show only lines from this role, when given.
            lines: show only the last N existing lines before following, when given.

        Yields:
            Each matching entry, oldest first.
        """
        item_id = ItemIdHelper.normalize_item(item, self._item_prefix)
        matched = self._matching(item_id, role)
        seen = max(0, len(matched) - lines) if lines is not None else 0
        for entry in matched[seen:]:
            seen += 1
            yield entry
        while follow:
            self._sleep(self._poll_seconds)
            matched = self._matching(item_id, role)
            for entry in matched[seen:]:
                seen += 1
                yield entry

    def _matching(self, item_id: str, role: Optional[str]) -> List[LogEntry]:
        """Returns the item's entries, filtered by role when one is given."""
        entries = self._repository.entries(item_id)
        return [entry for entry in entries if role is None or entry.role == role]
