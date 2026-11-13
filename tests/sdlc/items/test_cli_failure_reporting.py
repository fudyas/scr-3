from pathlib import Path
from typing import Callable

import pytest

from sdlc.algorithms.error_text import ErrorTextHelper
from sdlc.controllers.cli import EXIT_ERROR, SdlcCliController
from sdlc.wiring import AppWiring
from tests.sdlc.items.test_review import ReviewFlowHelper, ReviewTextHelper


class TestErrorTextHelper:
    """Covers folding failure text into one line."""

    def test_multi_line_text_with_blank_lines_becomes_one_line(self) -> None:
        """Strips each line, drops blank lines, and joins the rest with semicolons."""
        text = "fatal: first reason\n\n   hint: second reason  \n\t\nlast line\n"
        assert ErrorTextHelper.one_line(text) == "fatal: first reason; hint: second reason; last line"

    @pytest.mark.parametrize("text", ["", "   ", "\n\n \t\n"])
    def test_blank_text_gives_no_detail(self, text: str) -> None:
        """Returns the placeholder when no line has content."""
        assert ErrorTextHelper.one_line(text) == "no detail"


class TestCliFailureReporting:
    """Covers that every CLI failure ends with one `error:` line over a real ledger."""

    def test_log_write_prints_one_confirmation_line(self, make_host: Callable[[str], AppWiring],
                                                    capsys: pytest.CaptureFixture) -> None:
        """Confirms a successful log write on stdout."""
        cli = SdlcCliController(lambda: make_host("alpha"))
        assert cli.run(["log", "write", "ITM-0001", "--role", "run", "start"]) == 0
        assert capsys.readouterr().out.splitlines() == ["logged ITM-0001 run info"]

    def test_log_write_failure_ends_with_one_error_line(self, make_host: Callable[[str], AppWiring],
                                                        capsys: pytest.CaptureFixture) -> None:
        """Reports an unexpected storage failure as a last `error: unexpected` line."""
        host = make_host("alpha")
        host.settings.logs_dir.mkdir(parents=True, exist_ok=True)
        (host.settings.logs_dir / "ITM-0001").write_text("not a directory")
        cli = SdlcCliController(lambda: host)
        assert cli.run(["log", "write", "ITM-0001", "--role", "run", "start"]) == EXIT_ERROR
        last_line = capsys.readouterr().err.splitlines()[-1]
        assert last_line.startswith("error: unexpected")

    def test_ledger_write_failure_prints_one_error_line(self, make_host: Callable[[str], AppWiring], plan_text: str,
                                                        tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Prints exactly one `error: ledger remote` line per failed ledger write and keeps the draft."""
        host = make_host("alpha")
        item_id = ReviewFlowHelper.planned_item(host, plan_text)
        draft = host.review_usecases.edit(item_id)
        draft.write_text(ReviewTextHelper.valid())
        capsys.readouterr()

        # Points a second wiring at a remote that does not exist
        broken_settings = host.settings.model_copy(update={"ledger_remote": str(tmp_path / "missing.git")})
        cli = SdlcCliController(lambda: AppWiring(broken_settings))
        commands = [
            ["items", "amend", item_id, "--idea", "x"],
            ["items", "tag", "add", item_id, "x"],
            ["items", "status", "set", item_id, "OBSOLETE"],
            ["items", "review", "commit", item_id],
        ]
        for command in commands:
            assert cli.run(command) == EXIT_ERROR
            error_lines = capsys.readouterr().err.splitlines()
            assert len(error_lines) == 1 and error_lines[0].startswith("error: ledger remote"), command
        assert draft.exists()
