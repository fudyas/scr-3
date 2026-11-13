from abc import ABC
from typing import Optional

from sdlc.models.errors import SdlcError

# Trailer key for the Claude session URL recorded in the promotion merge commit
SESSION_TRAILER_KEY = "Codex-Session"


class PromotionMessageHelper(ABC):
    """Builds the commit message for a promotion merge."""

    @staticmethod
    def build(branch: str, item_id: str, codex_session: Optional[str]) -> str:
        """Returns the promotion merge commit message.

        If a session URL is given, the message includes one empty line and a
        trailer carrying the session link. Otherwise, the message is subject only.

        Args:
            branch: the branch being merged, e.g., work/ITM-0007/integration.
            item_id: the item id, e.g., ITM-0007.
            codex_session: the Claude session URL, or None to omit the trailer.

        Returns:
            The commit message as a string, possibly with a trailer.

        Raises:
            SdlcError: the session URL is blank after stripping or holds a newline.
        """
        subject = f"Merge {branch} ({item_id})"

        if codex_session is None:
            return subject

        cleaned = codex_session.strip()
        if not cleaned or "\n" in codex_session or "\r" in codex_session:
            raise SdlcError("--codex-session needs one non-empty line")

        return subject + "\n\n" + f"{SESSION_TRAILER_KEY}: {cleaned}"
