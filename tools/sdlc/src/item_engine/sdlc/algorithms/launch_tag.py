import re
from abc import ABC

from sdlc.models.telemetry import LaunchTag


class LaunchTagParser(ABC):
    """Parses the SDLC attribution from a subagent launch description."""

    @staticmethod
    def parse(description: str, prefix: str) -> LaunchTag:
        """Returns the attribution in a description such as `ITM-0003 TSK-0002 swe: add ledger`.

        Args:
            description: the description given to the Agent tool at launch.
            prefix: the item id prefix, such as `ITM`.

        Returns:
            The parsed tag; fields stay empty when the description carries no attribution.
        """
        pattern = re.compile(
            rf"^\s*({re.escape(prefix)}-\d{{4,}})(?:-[A-Z0-9-]+)?"
            r"(?:\s+(BLK-\d{4,}|TSK-\d{4,}))?"
            r"\s+([a-z][a-z0-9-]*)\s*:\s*(.*)$"
        )
        match = pattern.match(description or "")
        if match is None:
            return LaunchTag(summary=description or "")
        scope = match.group(2) or ""
        return LaunchTag(
            item=match.group(1),
            block=scope if scope.startswith("BLK-") else None,
            task=scope if scope.startswith("TSK-") else None,
            role=match.group(3),
            summary=match.group(4).strip(),
        )
