import subprocess

import pytest

from sdlc.algorithms.promotion_message import PromotionMessageHelper, SESSION_TRAILER_KEY
from sdlc.models.errors import SdlcError


class TestPromotionMessageHelper:
    """Covers promotion merge commit message generation."""

    def test_subject_without_session(self) -> None:
        """Returns the subject when no session URL is given."""
        message = PromotionMessageHelper.build("work/ITM-0007/integration", "ITM-0007", None)
        assert message == "Merge work/ITM-0007/integration (ITM-0007)"

    def test_subject_and_trailer_with_session(self) -> None:
        """Returns the subject, empty line, and trailer when a session URL is given."""
        url = "https://claude.ai/code/session_01RB2EQVyWyJgePm512Hn3uf"
        message = PromotionMessageHelper.build("work/ITM-0023/integration", "ITM-0023", url)
        expected = f"Merge work/ITM-0023/integration (ITM-0023)\n\n{SESSION_TRAILER_KEY}: {url}"
        assert message == expected

    def test_strips_session_whitespace(self) -> None:
        """Strips whitespace from the session URL."""
        url = "https://claude.ai/code/session_01RB2EQVyWyJgePm512Hn3uf"
        message = PromotionMessageHelper.build("work/ITM-0001/integration", "ITM-0001", f"  {url}  ")
        assert f"{SESSION_TRAILER_KEY}: {url}" in message

    def test_rejects_blank_session(self) -> None:
        """Raises SdlcError when session is blank after stripping."""
        with pytest.raises(SdlcError, match="--codex-session needs one non-empty line"):
            PromotionMessageHelper.build("work/ITM-0001/integration", "ITM-0001", "   ")

    def test_rejects_session_with_newline(self) -> None:
        """Raises SdlcError when session contains a newline."""
        with pytest.raises(SdlcError, match="--codex-session needs one non-empty line"):
            PromotionMessageHelper.build("work/ITM-0001/integration", "ITM-0001", "url\nmore")

    def test_rejects_session_with_carriage_return(self) -> None:
        """Raises SdlcError when session contains a carriage return."""
        with pytest.raises(SdlcError, match="--codex-session needs one non-empty line"):
            PromotionMessageHelper.build("work/ITM-0001/integration", "ITM-0001", "url\rmore")

    def test_trailer_parsed_by_git_interpret_trailers(self) -> None:
        """The trailer is correctly formatted for git interpret-trailers."""
        url = "https://claude.ai/code/session_01RB2EQVyWyJgePm512Hn3uf"
        message = PromotionMessageHelper.build("work/ITM-0007/integration", "ITM-0007", url)

        # Parses the message with git interpret-trailers to verify format
        result = subprocess.run(
            ["git", "interpret-trailers", "--parse"],
            input=message,
            text=True,
            capture_output=True,
            check=True,
        )
        assert f"{SESSION_TRAILER_KEY}: {url}" in result.stdout
