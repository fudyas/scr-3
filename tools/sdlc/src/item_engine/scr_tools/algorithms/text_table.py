from abc import ABC
from typing import Any, Callable, List, Optional


class TextTableHelper(ABC):
    """Renders rows as an aligned plain-text table."""

    @staticmethod
    def render(columns: List[str], rows: List[List[Any]],
               cell_formatter: Optional[Callable[[str, str], str]] = None) -> str:
        """Returns the table with a header row and columns padded to their widest cell.

        Args:
            columns: the column names.
            rows: the cell values; None renders as `-`.
            cell_formatter: optional styling applied to each padded cell after column sizing.

        Returns:
            The table text without a trailing newline.
        """
        rows = [[index, *row] for index, row in enumerate(rows, 1)]
        columns = ["#", *columns]
        cells = [[TextTableHelper._cell(value) for value in row] for row in rows]
        widths = [len(column) for column in columns]
        for row in cells:
            for index, value in enumerate(row):
                widths[index] = max(widths[index], len(value))
        lines = ["  ".join(column.upper().ljust(widths[index]) for index, column in enumerate(columns)).rstrip()]
        for row in cells:
            # Pads plain text before styling so ANSI codes do not change column widths
            padded = [value.ljust(widths[index]) for index, value in enumerate(row)]
            if padded:
                padded[-1] = padded[-1].rstrip()
            if cell_formatter is not None:
                padded = [cell_formatter(columns[index], value) for index, value in enumerate(padded)]
            lines.append("  ".join(padded).rstrip())
        return "\n".join(lines)

    @staticmethod
    def _cell(value: Any) -> str:
        """Returns the display text of one cell."""
        if value is None or value == "":
            return "-"
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value).replace("\n", " ")
