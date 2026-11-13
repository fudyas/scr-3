from enum import Enum
from typing import List, Optional

from pydantic import Field

from sdlc.models.record import LedgerRecord


class ChainStatus(str, Enum):
    """The rolled-up status of a chain, derived from its member items at read time."""

    # Marks a chain whose members have not started
    BACKLOG = "BACKLOG"

    # Marks a chain with a started member that is not yet done
    IN_PROGRESS = "IN PROGRESS"

    # Marks a chain whose members are all done
    DONE = "DONE"


class Chain(LedgerRecord):
    """An SDLC chain: a named, ordered group of items that frames one body of work."""

    items: List[str] = Field(default_factory=list, description="Lists the ids of the member items in chain order.")

    # Names the host that runs the chain
    host: Optional[str] = None
