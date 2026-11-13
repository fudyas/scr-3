from enum import Enum
from typing import Dict, List, Optional

from pydantic import Field

from primitives.models.strict_model import StrictModel
from sdlc.models.record import LedgerRecord


class ItemKind(str, Enum):
    """The kind of work an item delivers."""

    # Marks new functionality
    TASK = "task"

    # Marks an enhancement of existing functionality
    IMPROVE = "improve"

    # Marks a restructure that keeps behavior
    REFACTOR = "refactor"

    # Marks a defect correction
    FIX = "fix"


class ItemStatus(str, Enum):
    """The lifecycle status of an item."""

    # Marks an item without an approved plan
    BACKLOG = "BACKLOG"

    # Marks an item whose current plan revision the user approved
    PLANNED = "PLANNED"

    # Marks an item that waits in the run queue
    SCHEDULED = "SCHEDULED"

    # Marks an item that a host builds
    IN_PROGRESS = "IN PROGRESS"

    # Marks an item that is assembled and under QA
    TESTING = "TESTING"

    # Marks an item that passed QA and awaits the user review
    REVIEW = "REVIEW"

    # Marks an item merged into the working branch
    DONE = "DONE"

    # Marks an item retired before a run
    OBSOLETE = "OBSOLETE"


class TaskStatus(str, Enum):
    """The lifecycle status of a task."""

    # Marks a task that has not started
    TODO = "TODO"

    # Marks a task that an engineer works on
    IN_PROGRESS = "IN PROGRESS"

    # Marks a task whose gates passed
    VALIDATED = "VALIDATED"

    # Marks a finished task
    DONE = "DONE"


class TaskRecord(StrictModel):
    """The ledger record of one task: its place in the plan and its status."""

    # Identifies the plan block that holds the task
    block: str

    # Gives the title of the task
    title: str
    depends_on: List[str] = Field(
        default_factory=list, description="Lists the ids of the tasks that must finish first."
    )

    # Names the model tier that builds the task
    model: Optional[str] = None

    # Gives the lifecycle status of the task
    status: TaskStatus = TaskStatus.TODO


class PlanState(StrictModel):
    """The revision and approval state of an item's plan."""

    # Counts the committed plan revisions
    revision: int = 0

    # Gives the revision that the user approved
    approved_revision: Optional[int] = None

    # Gives the time of the approval
    approved_at: Optional[str] = None

    @property
    def is_approved(self) -> bool:
        """Returns whether the current plan revision carries the user's approval."""
        return self.revision > 0 and self.approved_revision == self.revision


class HardwareAcceptance(StrictModel):
    """Records hardware authority and the exact package accepted by the developer."""

    required: bool = False
    result: Optional[str] = None
    package_path: Optional[str] = None
    promotion_commit: Optional[str] = None
    package_sha256: Optional[str] = None
    image_identity: Optional[str] = None
    notes: Optional[str] = None
    confirmed_at: Optional[str] = None


class Item(LedgerRecord):
    """An SDLC item: one unit of work from idea to promotion into the working branch."""

    # Tells what kind of work the item delivers
    kind: ItemKind

    # Holds the normalized idea text
    idea: str

    # Gives the lifecycle status of the item
    status: ItemStatus = ItemStatus.BACKLOG
    depends_on: List[str] = Field(
        default_factory=list, description="Lists the ids of the items that must be done first."
    )

    # Names the host that holds the claim
    host: Optional[str] = None

    # Orders the item in the run queue
    queue_rank: Optional[float] = None
    plan: PlanState = Field(default_factory=PlanState, description="Tracks the revision and approval of the plan.")
    tasks: Dict[str, TaskRecord] = Field(default_factory=dict, description="Maps each task id to its ledger record.")

    hardware: HardwareAcceptance = Field(default_factory=HardwareAcceptance, exclude_if=lambda value: not value.required)
