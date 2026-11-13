from typing import Any, Dict, Optional

from pydantic import ConfigDict, Field

from primitives.models.strict_model import StrictModel


class IdAllocation(StrictModel):
    """A newly allocated record number with the ids file text that records it."""

    # Gives the newly allocated record number
    number: int

    # Holds the ids file text that records the allocation
    ids_text: str


class LedgerChange(StrictModel):
    """The file changes one ledger transaction writes, with the value it hands back."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    changes: Dict[str, Optional[str]] = Field(
        default_factory=dict, description="Maps each ledger file path to its new text, or to None to delete the file."
    )

    # Holds the commit message of the transaction
    message: str

    # Holds the value that the transaction hands back to its caller
    result: Any = None
