from enum import Enum
from typing import Optional

from primitives.models.strict_model import StrictModel


class LogLevel(str, Enum):
    """The severity of a run-log line."""

    # Marks a progress line
    INFO = "info"

    # Marks a recoverable problem
    WARN = "warn"

    # Marks a failure
    ERROR = "error"


class LogEntry(StrictModel):
    """One line of an item's run log, written by the orchestrator or a pipeline agent."""

    # Gives the time of the line
    at: str

    # Names the host that wrote the line
    host: str

    # Identifies the item of the run
    item: str

    # Names the pipeline role that wrote the line
    role: str

    # Gives the severity of the line
    level: LogLevel = LogLevel.INFO

    # Identifies the task that the line concerns
    task: Optional[str] = None

    # Identifies the block that the line concerns
    block: Optional[str] = None

    # Holds the text of the line
    message: str
