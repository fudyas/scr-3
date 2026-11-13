import json
from pathlib import Path
from typing import Any, Callable, List
from unittest.mock import Mock

import pytest

from sdlc.controllers.cli import SdlcCliController
from sdlc.models.review_session import ReviewSession
from sdlc.wiring import AppWiring
from scr_tools.algorithms.json_output import JsonOutputHelper

# The em dash that the JSON output must keep as a UTF-8 character
EM_DASH = "—"

# The escaped form of the em dash that the shared layout never prints
ESCAPED_EM_DASH = "\\u2014"


class TestSdlcCliJsonOutput:
    """Proves that every `--json` output of the SDLC CLI uses the shared JSON layout."""

    @staticmethod
    def _assert_shared_layout(output: str) -> Any:
        """Asserts that the output equals the shared rendering of its own parsed value and returns that value."""
        parsed = json.loads(output)
        assert output == JsonOutputHelper.render(parsed) + "\n"
        return parsed

    @staticmethod
    def _run_json(cli: SdlcCliController, capsys: pytest.CaptureFixture, arguments: List[str]) -> Any:
        """Runs the command, checks its output layout, and returns the parsed JSON value."""
        capsys.readouterr()
        assert cli.run(arguments) == 0
        return TestSdlcCliJsonOutput._assert_shared_layout(capsys.readouterr().out)

    def test_items_list_and_show_keep_utf8(self, make_host: Callable[..., AppWiring],
                                           capsys: pytest.CaptureFixture) -> None:
        """Prints the item list and one item in the shared layout with the em dash unescaped."""
        cli = SdlcCliController(lambda: make_host("alpha"))
        assert cli.run(["items", "new", "--kind", "task", "--desc", "LEDGER-CORE-TOOLS", "--idea", "make ledger",
                        "--description", f"Build {EM_DASH} the ledger core."]) == 0

        listed = self._run_json(cli, capsys, ["items", "list", "--json"])
        assert [entry["number"] for entry in listed] == [1]

        capsys.readouterr()
        assert cli.run(["items", "show", "ITM-0001", "--json"]) == 0
        output = capsys.readouterr().out
        assert self._assert_shared_layout(output)["description"] == f"Build {EM_DASH} the ledger core."
        assert EM_DASH in output and ESCAPED_EM_DASH not in output

    def test_items_queue_prints_the_queue_entries(self, make_host: Callable[..., AppWiring], plan_text: str,
                                                  capsys: pytest.CaptureFixture) -> None:
        """Prints the scheduled item with the keys item, status, ready, unmet, and host."""
        cli = SdlcCliController(lambda: make_host("alpha"))
        assert cli.run(["items", "new", "--kind", "task", "--desc", "LEDGER-CORE-TOOLS", "--idea", "make ledger",
                        "--description", "Build the ledger core."]) == 0
        assert cli.run(["items", "plan", "edit", "ITM-0001"]) == 0
        draft_path = capsys.readouterr().out.splitlines()[-1]
        Path(draft_path).write_text(plan_text, encoding="utf-8")
        assert cli.run(["items", "plan", "approve", "ITM-0001"]) == 0
        assert cli.run(["items", "schedule", "ITM-0001"]) == 0

        queued = self._run_json(cli, capsys, ["items", "queue", "--json"])
        assert len(queued) == 1
        assert set(queued[0]) == {"item", "status", "ready", "unmet", "host"}
        assert queued[0]["item"] == "ITM-0001-LEDGER-CORE-TOOLS" and queued[0]["ready"] is True

    def test_chains_list_and_show(self, make_host: Callable[..., AppWiring], capsys: pytest.CaptureFixture) -> None:
        """Prints the chain list and one chain with its members in the shared layout."""
        cli = SdlcCliController(lambda: make_host("alpha"))
        assert cli.run(["items", "new", "--kind", "task", "--desc", "LEDGER-CORE-TOOLS", "--idea", "a",
                        "--description", "b"]) == 0
        assert cli.run(["chains", "new", "--desc", "EMBEDDING-PIPELINE", "--description", "Embed the corpus.",
                        "--item", "ITM-0001"]) == 0

        listed = self._run_json(cli, capsys, ["chains", "list", "--json"])
        assert [entry["members"] for entry in listed] == [[{"item": "ITM-0001-LEDGER-CORE-TOOLS", "status": "BACKLOG"}]]

        shown = self._run_json(cli, capsys, ["chains", "show", "CHN-0001", "--json"])
        assert shown["status"] == "BACKLOG" and shown["counts"] == {"BACKLOG": 1}

    def test_stats_item_prints_records(self, make_host: Callable[..., AppWiring],
                                       capsys: pytest.CaptureFixture) -> None:
        """Prints the per-item stats rows in the shared layout."""
        cli = SdlcCliController(lambda: make_host("alpha"))
        assert cli.run(["items", "new", "--kind", "task", "--desc", "LEDGER-CORE-TOOLS", "--idea", "a",
                        "--description", "b"]) == 0

        records = self._run_json(cli, capsys, ["stats", "--item", "ITM-0001", "--json"])
        assert isinstance(records, list)

    def test_worktree_context_prints_the_session(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Prints the review session with its path as text, through a stub wiring."""
        session = ReviewSession(item_id="ITM-0001", worktree=tmp_path / "integration", branch="work/ITM-0001/integration",
                                target_branch="master", base_commit="abc", built_tip="def")
        wiring = Mock()
        wiring.worktree_usecases.context.return_value = session
        cli = SdlcCliController(lambda: wiring)

        parsed = self._run_json(cli, capsys, ["worktree", "context", "ITM-0001", "--json"])
        assert parsed["worktree"] == str(tmp_path / "integration")
        assert parsed["phase"] == "SHOW" and parsed["verified_tree"] is None
