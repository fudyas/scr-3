from pathlib import Path
from typing import Dict, List, Optional

from pydantic import Field

from primitives.models.strict_model import StrictModel
from sdlc.models.chain import Chain, ChainStatus
from sdlc.models.item import Item, ItemStatus


class ChainView(StrictModel):
    """A chain with its rolled-up status and its member items in chain order."""

    # Holds the chain record
    chain: Chain

    # Gives the rolled-up status of the chain
    status: ChainStatus
    members: List[Item] = Field(default_factory=list, description="Lists the member items in chain order.")
    counts: Dict[ItemStatus, int] = Field(default_factory=dict, description="Counts the member items of each status.")


class IdeOpening(StrictModel):
    """The outcome of opening an item's integration worktree in an IDE."""

    # Locates the folder that the IDE opened
    folder: Path

    # Names the IDE that opened the folder
    ide: str

    # Gives the exit code of the IDE launch
    exit_code: int

    # Names the SSH host that the IDE connected to, or None for a local folder
    host: Optional[str] = None


class DependencyReport(StrictModel):
    """Whether an item's dependencies are all DONE, with the ones that are not."""

    # Identifies the item that was checked
    item_id: str

    # Tells whether every dependency is done
    ready: bool
    unmet: List[str] = Field(default_factory=list, description="Lists the ids of the dependencies that are not done.")


class QueueEntry(StrictModel):
    """One active or scheduled item in run order, with its dependency readiness."""

    # Holds the queued item
    item: Item

    # Tells whether every dependency of the item is done
    ready: bool
    unmet: List[str] = Field(default_factory=list, description="Lists the ids of the dependencies that are not done.")
