import re
from abc import ABC

from sdlc.models.errors import InvalidItemIdError

# Matches a block id, such as `BLK-0001`
BLOCK_ID_PATTERN = re.compile(r"^BLK-\d{4,}$")

# Matches a task id, such as `TSK-0001`
TASK_ID_PATTERN = re.compile(r"^TSK-\d{4,}$")


class ItemIdHelper(ABC):
    """Parses and formats item, block, and task ids."""

    @staticmethod
    def format_item(prefix: str, number: int) -> str:
        """Returns the short item id for the given number, such as `ITM-0012`."""
        return f"{prefix}-{number:04d}"

    @staticmethod
    def parse_item_number(text: str, prefix: str) -> int:
        """Returns the item number from a short or full item id.

        Args:
            text: an id such as `ITM-0012` or `ITM-0012-GRAPH-CLAIM-AMEND`, in any letter case.
            prefix: the item id prefix, such as `ITM`.

        Returns:
            The item number.

        Raises:
            InvalidItemIdError: the text is not an item id with the given prefix.
        """
        match = re.match(rf"^{re.escape(prefix)}-(\d{{4,}})(?:-[A-Z0-9-]+)?$", text.strip().upper())
        if match is None:
            raise InvalidItemIdError(f"not an item id: {text!r} (expected {prefix}-NNNN)")
        return int(match.group(1))

    @staticmethod
    def normalize_item(text: str, prefix: str) -> str:
        """Returns the short item id for a short or full item id."""
        return ItemIdHelper.format_item(prefix, ItemIdHelper.parse_item_number(text, prefix))

    @staticmethod
    def is_block_id(text: str) -> bool:
        """Returns whether the text is a block id."""
        return BLOCK_ID_PATTERN.match(text) is not None

    @staticmethod
    def is_task_id(text: str) -> bool:
        """Returns whether the text is a task id."""
        return TASK_ID_PATTERN.match(text) is not None
