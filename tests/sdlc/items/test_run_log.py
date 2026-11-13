from pathlib import Path
from typing import Callable, Optional

from sdlc.algorithms.log_render import RESET, LogRenderHelper
from sdlc.models.run_log import LogEntry, LogLevel
from sdlc.repositories.run_log_repository import RunLogRepository
from sdlc.usecases.run_log_usecases import RunLogUsecases


class TestLogRender:
    """Covers the pure rendering of a run-log entry."""

    @staticmethod
    def _entry(role: str, level: LogLevel = LogLevel.INFO, task: str = None, block: str = None) -> LogEntry:
        """Returns an entry with a fixed timestamp."""
        return LogEntry(at="2026-10-04T13:45:07.123Z", host="alpha", item="ITM-0012", role=role,
                        level=level, task=task, block=block, message="built the slice")

    def test_renders_clock_role_tag_and_message_without_color(self) -> None:
        """Plain mode shows the time, role, task tag, and message with no escapes."""
        line = LogRenderHelper.render(self._entry("swe", task="TSK-0003"), use_color=False)
        assert line == "13:45:07  swe         TSK-0003  built the slice"
        assert "\033[" not in line

    def test_colors_a_known_role(self) -> None:
        """A known role wraps the line in its SGR color and the reset."""
        line = LogRenderHelper.render(self._entry("swe"), use_color=True)
        assert line.startswith("\033[32m") and line.endswith(RESET)

    def test_error_level_overrides_role_color_with_bold_red(self) -> None:
        """An error line is bold red whatever the role, so failures stand out."""
        line = LogRenderHelper.render(self._entry("qa", level=LogLevel.ERROR), use_color=True)
        assert line.startswith("\033[1;31m")

    def test_unknown_role_stays_plain_even_in_color_mode(self) -> None:
        """An unknown role has no color code, so the line is left plain."""
        line = LogRenderHelper.render(self._entry("mystery"), use_color=True)
        assert "\033[" not in line

    def test_block_tag_used_when_no_task(self) -> None:
        """The block id fills the tag column when the line names no task."""
        line = LogRenderHelper.render(self._entry("validator", block="BLK-0001"), use_color=False)
        assert "BLK-0001" in line


class TestRunLogUsecases:
    """Covers writing, reading, filtering, and following an item's run log over a real store."""

    @staticmethod
    def _usecases(tmp_path: Path, sleep: Optional[Callable[[float], None]] = None) -> RunLogUsecases:
        """Returns usecases over a run log rooted at the temp path."""
        repository = RunLogRepository(tmp_path / "logs", "alpha")
        if sleep is None:
            return RunLogUsecases(repository, "ITM")
        return RunLogUsecases(repository, "ITM", poll_seconds=0, sleep=sleep)

    def test_write_normalizes_the_id_and_reads_back_in_order(self, tmp_path: Path) -> None:
        """A full id and a short id write to the same per-item log, read oldest first."""
        usecases = self._usecases(tmp_path)
        usecases.write("ITM-0012-GRAPH-CLAIM-AMEND", "run", "claimed", LogLevel.INFO, None, None)
        usecases.write("ITM-0012", "swe", "built", LogLevel.INFO, "TSK-0001", None)
        messages = [entry.message for entry in usecases.tail("ITM-0012", follow=False, role=None, lines=None)]
        assert messages == ["claimed", "built"]
        assert (tmp_path / "logs" / "ITM-0012" / "events.jsonl").exists()

    def test_role_filter_and_last_lines(self, tmp_path: Path) -> None:
        """The role filter and the line limit narrow what the tail yields."""
        usecases = self._usecases(tmp_path)
        usecases.write("ITM-0012", "run", "a", LogLevel.INFO, None, None)
        usecases.write("ITM-0012", "swe", "b", LogLevel.INFO, None, None)
        usecases.write("ITM-0012", "run", "c", LogLevel.INFO, None, None)
        runs = [entry.message for entry in usecases.tail("ITM-0012", follow=False, role="run", lines=None)]
        assert runs == ["a", "c"]
        last = [entry.message for entry in usecases.tail("ITM-0012", follow=False, role=None, lines=1)]
        assert last == ["c"]

    def test_follow_yields_lines_appended_after_the_initial_batch(self, tmp_path: Path) -> None:
        """Following emits the existing lines, then new ones written while polling."""
        repository = RunLogRepository(tmp_path / "logs", "alpha")
        polls = []

        def fake_sleep(_seconds: float) -> None:
            """Appends one line on the first poll, then stops the follow loop."""
            polls.append(1)
            if len(polls) == 1:
                repository.append("ITM-0012", "qa", "qa pass", LogLevel.INFO, None, None)
            else:
                raise KeyboardInterrupt

        usecases = RunLogUsecases(repository, "ITM", poll_seconds=0, sleep=fake_sleep)
        repository.append("ITM-0012", "run", "start", LogLevel.INFO, None, None)
        collected = []
        try:
            for entry in usecases.tail("ITM-0012", follow=True, role=None, lines=None):
                collected.append(entry.message)
        except KeyboardInterrupt:
            pass
        assert collected == ["start", "qa pass"]
