import os
import re
import sys
import zlib
from abc import ABC
from typing import Any, Dict, List, Match, Tuple

from scr_tools.algorithms.text_table import TextTableHelper

# Maps lifecycle statuses to consistent terminal colors
STATUS_CODES: Dict[str, str] = {
    "PLANNED": "94",
    "SCHEDULED": "94",
    "IN PROGRESS": "93",
    "TESTING": "35",
    "REVIEW": "95",
    "DONE": "92",
    "OBSOLETE": "2;90",
}

# Assigns stable foreground colors to tags
TAG_CODES: Tuple[str, ...] = ("34", "35", "31", "32", "36", "33", "90",
                              "94", "95", "96", "92", "93", "91")

# Matches status labels inside the member counts, including compound statuses
COUNT_PATTERN = re.compile(r"\b(" + "|".join(re.escape(status) for status in STATUS_CODES) + r") \d+")


class ListingRenderHelper(ABC):
    """Renders aligned SDLC listings with lifecycle colors and indented descriptions."""

    @staticmethod
    def prototype(tags: List[str]) -> str:
        """Returns prototype labels from the record's tags.

        Args:
            tags: the labels of the item or chain.

        Returns:
            Uppercase prototype labels, or empty text when no prototype tag exists.
        """
        # Selects complete prototype tags and removes duplicates after case normalization
        labels = [tag.upper() for tag in tags if re.fullmatch(r"p[1-9][0-9]*", tag, re.IGNORECASE)]
        return ", ".join(dict.fromkeys(labels))

    @staticmethod
    def colors_enabled(choice: str) -> bool:
        """Resolves forced colors or terminal detection, with NO_COLOR respected in auto mode."""
        if choice != "auto":
            return choice == "yes"
        return sys.stdout.isatty() and os.environ.get("NO_COLOR") is None

    @staticmethod
    def render(columns: List[str], rows: List[List[Any]], descriptions: List[str], use_color: bool) -> str:
        """Returns an aligned listing with each description directly below its record.

        Args:
            columns: the table columns in display order.
            rows: the table cells, with the record name first.
            descriptions: one description per row, or an empty list to omit descriptions.
            use_color: whether to emit terminal styling.

        Returns:
            The listing without a trailing newline.
        """
        # Sizes columns from plain cells and applies color after padding
        formatter = ListingRenderHelper._style_cell if use_color else None
        table = TextTableHelper.render(columns, rows, formatter).splitlines()
        lines = [ListingRenderHelper._paint("2;90", table[0]) if use_color else table[0]]
        for index, line in enumerate(table[1:]):
            lines.append(line)
            if descriptions and descriptions[index].strip():
                # Adds one indent level below the record, including nested chain members
                name = str(rows[index][0])
                indent = " " * (len(name) - len(name.lstrip()) + 4)
                for detail in descriptions[index].strip().splitlines():
                    text = ListingRenderHelper._paint("2;90", detail) if use_color else detail
                    lines.append(f"{indent}{text}")
        return "\n".join(lines)

    @staticmethod
    def details(name: str, fields: List[List[str]], use_color: bool) -> str:
        """Returns a record name with colored fields on separate, indented lines.

        Args:
            name: the full record identifier.
            fields: field names and their plain text values.
            use_color: whether to emit terminal styling.

        Returns:
            The detail text with nested indentation for multiline values.
        """
        lines = [ListingRenderHelper._paint("1", name) if use_color else name]
        for label, value in fields:
            heading = ListingRenderHelper._paint("2;90", f"{label}:") if use_color else f"{label}:"
            parts = value.splitlines() or ["-"]
            for index, part in enumerate(parts):
                text = ListingRenderHelper._style_cell(label, part) if use_color else part
                lines.append(f"    {heading} {text}" if index == 0 else f"        {text}")
        return "\n".join(lines)

    @staticmethod
    def _style_cell(column: str, text: str) -> str:
        """Colors lifecycle statuses, member counts, and tag text.

        Args:
            column: the name of the column that determines its palette.
            text: the padded cell text.

        Returns:
            The styled cell with its visible width preserved.
        """
        if column == "status":
            return ListingRenderHelper._paint(STATUS_CODES.get(text.strip(), ""), text)
        if column == "counts":
            return COUNT_PATTERN.sub(ListingRenderHelper._style_count, text)
        if column == "tags" and text.strip() != "-":
            tags = text.rstrip().split(", ")
            painted = [ListingRenderHelper._paint(TAG_CODES[zlib.crc32(tag.encode("utf-8")) % len(TAG_CODES)], tag)
                       for tag in tags]
            return ", ".join(painted) + text[len(text.rstrip()):]
        return text

    @staticmethod
    def _style_count(match: Match[str]) -> str:
        """Colors a member count with the palette of its lifecycle status."""
        return ListingRenderHelper._paint(STATUS_CODES[match.group(1)], match.group())

    @staticmethod
    def _paint(code: str, text: str) -> str:
        """Wraps text in an ANSI style, or keeps it plain when the code is empty."""
        return f"\033[{code}m{text}\033[0m" if code else text
