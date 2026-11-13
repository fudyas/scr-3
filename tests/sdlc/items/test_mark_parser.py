import pytest

from sdlc.algorithms.mark_parser import END_STAGE, MarkParser
from sdlc.models.mark import ParsedMark


class TestMarkParser:
    """Covers finding the last SDLC mark in a Bash call, from its output or its command text."""

    def test_reads_the_mark_from_the_output_when_the_command_hides_it_behind_a_variable(self) -> None:
        """Finds the mark that a shell variable or wrapper keeps out of the command text."""
        command = 'L="./bin/lets sdlc" && $L mark ITM-0001 review && echo done'
        output = "mark ITM-0001 review\ndone\n"
        assert MarkParser.find(command, output, "ITM") == ParsedMark(item="ITM-0001", stage="review")

    def test_reduces_a_full_item_id_to_the_short_id(self) -> None:
        """Keeps only `ITM-NNNN` of an item id that carries its DESC slug."""
        mark = MarkParser.find("", "mark ITM-0001-LEDGER-CORE run\n", "ITM")
        assert mark == ParsedMark(item="ITM-0001", stage="run")

    def test_last_mark_of_the_output_wins(self) -> None:
        """Returns the final state when one call runs several marks."""
        output = "mark ITM-0001 run\nlines between\nmark ITM-0001 end\n"
        assert MarkParser.find("", output, "ITM") == ParsedMark(item="ITM-0001", stage=END_STAGE)

    def test_falls_back_to_the_command_text_without_an_output_value(self) -> None:
        """Reads the literal command when the payload carries no output at all."""
        command = "./bin/lets sdlc mark ITM-0002 plan 2>&1 | tail -1"
        assert MarkParser.find(command, None, "ITM") == ParsedMark(item="ITM-0002", stage="plan")

    def test_last_mark_of_the_command_wins(self) -> None:
        """Returns the final mark when the command text names several."""
        command = "./bin/lets sdlc mark ITM-0001 run && ./bin/lets sdlc mark ITM-0001 end"
        assert MarkParser.find(command, None, "ITM") == ParsedMark(item="ITM-0001", stage="end")

    def test_output_outranks_the_command_text(self) -> None:
        """Trusts the result line over the command, because only a mark that ran prints it."""
        command = "./bin/lets sdlc mark ITM-0001 run && false"
        assert MarkParser.find(command, "mark ITM-0001 plan\n", "ITM") == ParsedMark(item="ITM-0001", stage="plan")

    def test_a_command_that_only_mentions_a_mark_records_nothing(self) -> None:
        """Ignores example text in a heredoc or an echo when the call printed no mark line."""
        command = "cat <<'EOF'\n./bin/lets sdlc mark ITM-0001 run\nEOF"
        assert MarkParser.find(command, "", "ITM") is None
        assert MarkParser.find(command, "some other output\n", "ITM") is None

    def test_a_dash_item_gives_an_empty_item(self) -> None:
        """Maps the `-` item of a mark without an item to an empty item."""
        assert MarkParser.find("", "mark - end\n", "ITM") == ParsedMark(item="", stage="end")

    @pytest.mark.parametrize("command,output", [
        ("git status", ""),
        ("echo benchmark ITM-0001 run", "benchmark ITM-0001 run\n"),
        ("echo done", "log: mark ITM-0001 inside a sentence\n"),
        ("", ""),
    ])
    def test_ignores_calls_that_ran_no_mark(self, command: str, output: str) -> None:
        """Finds nothing in ordinary calls and in text that only looks like a mark."""
        assert MarkParser.find(command, output, "ITM") is None

    def test_ignores_another_item_prefix(self) -> None:
        """Finds only marks of the configured item prefix."""
        assert MarkParser.find("", "mark CHN-0001 run\n", "ITM") is None
