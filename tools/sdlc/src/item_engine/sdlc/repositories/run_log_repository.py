from pathlib import Path
from typing import List, Optional

from sdlc.algorithms.timestamps import TimestampHelper
from sdlc.datasources.jsonl_store import JsonlStore
from sdlc.models.run_log import LogEntry, LogLevel

# Stream that holds one item's run-log lines
EVENTS_STREAM = "events"


class RunLogRepository:
    """Stores and reads each item's run log as a local JSON-lines stream in its own directory."""

    def __init__(self, logs_dir: Path, host: str) -> None:
        """Initializes the repository.

        Args:
            logs_dir: the directory that holds one `<ITM-NNNN>/` folder per item.
            host: the host name stamped on every line.
        """
        self._logs_dir = logs_dir
        self._host = host

    def append(self, item_id: str, role: str, message: str, level: LogLevel,
               task: Optional[str], block: Optional[str]) -> LogEntry:
        """Appends one line to the item's run log and returns it.

        Args:
            item_id: the short item id, such as `ITM-0012`.
            role: the author role, such as `run` or `swe`.
            message: the log text.
            level: the severity.
            task: the task id the line is about, if any.
            block: the block id the line is about, if any.

        Returns:
            The stored entry.
        """
        entry = LogEntry(at=TimestampHelper.now(), host=self._host, item=item_id, role=role,
                         level=level, task=task, block=block, message=message)
        self._store(item_id).append(EVENTS_STREAM, entry.model_dump(mode="json"))
        return entry

    def entries(self, item_id: str) -> List[LogEntry]:
        """Returns every run-log line of the item in write order."""
        return [LogEntry.from_document(record) for record in self._store(item_id).read(EVENTS_STREAM)]

    def _store(self, item_id: str) -> JsonlStore:
        """Returns the JSON-lines store of one item's run log."""
        return JsonlStore(self._logs_dir / item_id)
