from typing import Any, List

from pydantic import Field

from primitives.models.strict_model import StrictModel


class StatsTable(StrictModel):
    """A query result as column names and rows."""

    columns: List[str] = Field(default_factory=list, description="Lists the column names.")
    rows: List[List[Any]] = Field(default_factory=list, description="Lists the rows of cell values.")
