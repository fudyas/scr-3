from primitives.models.strict_model import StrictModel


class ParsedMark(StrictModel):
    """The item and stage a `mark` command set; the item is empty when the mark names none."""

    # Identifies the item that the mark names
    item: str

    # Names the stage that the mark sets
    stage: str
