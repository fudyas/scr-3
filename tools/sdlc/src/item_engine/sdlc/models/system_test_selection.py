from typing import List

from pydantic import Field

from primitives.models.strict_model import StrictModel


class SystemTestSelection(StrictModel):
    """Holds the system test run targets chosen for a change and the reasons for the choice."""

    targets: List[str] = Field(
        default_factory=list, description="Lists the pytest paths to run, empty when no system test applies."
    )
    explanations: List[str] = Field(
        default_factory=list,
        description="Lists one line per changed path, or one line for the reason of a full run.",
    )
