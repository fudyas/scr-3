from typing import List, Optional

from pydantic import Field

from primitives.models.strict_model import StrictModel


class PlanTask(StrictModel):
    """One task section of a plan document."""

    # Identifies the task, such as TSK-0001
    task_id: str

    # Gives the title of the task
    title: str
    depends_on: List[str] = Field(
        default_factory=list, description="Lists the ids of the tasks that must finish first."
    )

    # Names the model tier that builds the task
    model: Optional[str] = None

    # Holds the full text of the task section
    section: str


class PlanBlock(StrictModel):
    """One block section of a plan document with its ordered tasks."""

    # Identifies the block, such as BLK-0001
    block_id: str

    # Gives the title of the block
    title: str

    # Holds the heading line of the block section
    heading: str
    tasks: List[PlanTask] = Field(default_factory=list, description="Lists the tasks of the block in order.")


class PlanDocument(StrictModel):
    """A parsed plan: the shared header sections and the blocks of tasks."""

    # Gives the title of the plan
    title: str

    # Holds the shared header text before the first block
    header: str
    section_names: List[str] = Field(default_factory=list, description="Lists the names of the header sections.")
    blocks: List[PlanBlock] = Field(default_factory=list, description="Lists the blocks of the plan in order.")
