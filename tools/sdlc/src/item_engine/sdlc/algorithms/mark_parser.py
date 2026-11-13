import re
from abc import ABC
from typing import Optional

from sdlc.models.mark import ParsedMark

# Stage name a `mark` command uses to end a session's attribution
END_STAGE = "end"


class MarkParser(ABC):
    """Finds the last SDLC `mark` that a Bash call ran."""

    @staticmethod
    def find(command: str, output: Optional[str], prefix: str) -> Optional[ParsedMark]:
        """Returns the last mark of the call, or None when the call ran no mark.

        The output is the evidence: `mark` prints `mark <ITEM> <stage>`, so the line shows through shell variables
        and wrappers, and a command that only mentions a mark in its text, such as a heredoc, records nothing. The
        command text is read only when the payload carries no output at all.

        Steps:
            1. When there is output, search it for `mark` result lines and keep the last one.
            2. When there is no output value, search the command text for `scr sdlc mark <ITEM> <stage>`.

        Args:
            command: the Bash command line.
            output: the standard output of the command, or None when the hook payload has no tool response.
            prefix: the item id prefix, such as `ITM`.

        Returns:
            The last mark found, with the item reduced to its `ITM-NNNN` id.
        """
        item_pattern = rf"({re.escape(prefix)}-\d{{4,}}[A-Z0-9-]*|-)"
        stage_pattern = r"([a-z][a-z0-9-]*)"

        # Reads the lines the mark command printed, or the command text when no output exists
        if output is not None:
            marks = list(re.finditer(rf"(?m)^mark\s+{item_pattern}\s+{stage_pattern}\s*$", output))
        else:
            marks = list(re.finditer(rf"sdlc\s+mark\s+{item_pattern}\s+{stage_pattern}", command or ""))
        if not marks:
            return None
        item_text, stage = marks[-1].group(1), marks[-1].group(2)
        item = re.match(rf"{re.escape(prefix)}-\d{{4,}}", item_text)
        return ParsedMark(item=item.group(0) if item else "", stage=stage)
