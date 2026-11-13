from typing import Any, Dict, List, Optional

from pydantic import Field, SerializerFunctionWrapHandler, model_serializer

from primitives.models.strict_model import StrictModel


class HistoryEntry(StrictModel):
    """One dated event in a ledger record's history trail."""

    # Gives the time of the event
    at: str

    # Names the host that recorded the event
    host: str

    # Names the event
    event: str

    # Describes the event
    detail: str = ""

    # Holds the old values of the fields that the event replaced
    previous: Dict[str, str] = Field(default_factory=dict)

    @model_serializer(mode="wrap")
    def _omit_empty_previous(self, handler: SerializerFunctionWrapHandler) -> Dict[str, Any]:
        """Serializes the entry without the `previous` key when no old values were kept."""
        data = handler(self)
        if not data.get("previous"):
            data.pop("previous", None)
        return data


class RecordAmendment(StrictModel):
    """The text fields that an amendment replaces; a `None` field stays unchanged."""

    # Holds the new DESC slug
    desc: Optional[str] = None

    # Holds the new idea text
    idea: Optional[str] = None

    # Holds the new description text
    description: Optional[str] = None


class LedgerRecord(StrictModel):
    """The identity, labels, and history that every item and chain record on the ledger shares."""

    # Gives the id prefix of the record kind, such as ITM
    prefix: str

    # Gives the record number within its prefix
    number: int

    # Gives the DESC slug of the record
    desc: str

    # Holds the description of the record
    description: str
    tags: List[str] = Field(default_factory=list, description="Lists the labels of the record.")
    history: List[HistoryEntry] = Field(
        default_factory=list, description="Lists the events of the record in time order."
    )

    # Gives the creation time
    created_at: str

    # Gives the time of the last update
    updated_at: str

    @property
    def short_id(self) -> str:
        """Returns the stable identity, such as `ITM-0012`."""
        return f"{self.prefix}-{self.number:04d}"

    @property
    def full_id(self) -> str:
        """Returns the identity with its DESC slug, such as `ITM-0012-GRAPH-CLAIM-AMEND`."""
        return f"{self.short_id}-{self.desc}"
