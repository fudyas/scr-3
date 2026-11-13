from abc import ABC
from typing import List


class UniqueValuesHelper(ABC):
    """Removes empty and repeated values from label lists."""

    @staticmethod
    def ordered(values: List[str]) -> List[str]:
        """Returns the non-empty values without duplicates, in first-seen order."""
        unique: List[str] = []
        for value in values:
            if value and value not in unique:
                unique.append(value)
        return unique
