import inspect
from pathlib import Path
from typing import Any, Callable, Dict, List
from unittest.mock import Mock

import click
import pytest

from sdlc.controllers.cli import EXIT_BLOCKED, EXIT_ERROR, SdlcCliController
from sdlc.models.system_test_selection import SystemTestSelection
from sdlc.wiring import AppWiring


class TestSdlcCliController:
    """Covers the command line end to end over a real ledger."""

    def test_lock_check_requires_the_actual_holder(self, make_host: Callable[[str], AppWiring],
                                                  capsys: pytest.CaptureFixture) -> None:
        """Rejects a free lease and a foreign holder without altering the lease."""
        host = make_host("alpha")
        cli = SdlcCliController(lambda: host)
        assert cli.run(["lock", "check", "stack", "--holder", "ITM-0001"]) == EXIT_ERROR
        assert "is free" in capsys.readouterr().err
        assert cli.run(["lock", "acquire", "stack", "--holder", "ITM-0001"]) == 0
        assert cli.run(["lock", "check", "stack", "--holder", "ITM-0002"]) == EXIT_ERROR
        assert "held by ITM-0001, not ITM-0002" in capsys.readouterr().err
        assert cli.run(["lock", "check", "stack"]) == EXIT_ERROR
        assert "needs a lease name and --holder" in capsys.readouterr().err
        assert cli.run(["lock", "check", "stack", "--holder", "ITM-0001"]) == 0
        assert host.lock_usecases.status("stack")["stack"].holder_id == "ITM-0001"

    def test_full_item_flow(self, make_host: Callable[[str], AppWiring], plan_text: str,
                            capsys: pytest.CaptureFixture) -> None:
        """Mints, plans, approves, schedules, picks, and lists an item through the CLI."""
        wiring = make_host("alpha")
        cli = SdlcCliController(lambda: wiring)
        assert cli.run(["items", "new", "--kind", "task", "--desc", "LEDGER-CORE-TOOLS", "--idea", "make ledger",
                        "--description", "Build the ledger core."]) == 0
        assert capsys.readouterr().out.strip() == "ITM-0001-LEDGER-CORE-TOOLS"

        assert cli.run(["items", "plan", "edit", "ITM-0001"]) == 0
        draft_path = capsys.readouterr().out.strip()
        with open(draft_path, "w", encoding="utf-8") as handle:
            handle.write(plan_text)
        assert cli.run(["items", "plan", "check", "ITM-0001"]) == 0
        assert "2 blocks, 3 tasks" in capsys.readouterr().out
        assert cli.run(["items", "plan", "approve", "ITM-0001"]) == 0
        assert cli.run(["items", "schedule", "ITM-0001"]) == 0
        assert cli.run(["items", "next"]) == 0
        assert cli.run(["items", "depends", "check", "ITM-0001"]) == 0
        assert cli.run(["items", "task", "show", "ITM-0001", "TSK-0003"]) == 0
        assert cli.run(["items", "list", "--status", "SCHEDULED"]) == 0
        output = capsys.readouterr().out
        assert "approved (PLANNED)" in output and "READY ITM-0001" in output
        assert "ADD TELEMETRY STORE" in output and "SCHEDULED" in output

    def test_items_list_table_layout(self, make_host: Callable[[str], AppWiring],
                                     capsys: pytest.CaptureFixture) -> None:
        """Prints the item table with the header, padded columns, and the ledger footer unchanged."""
        cli = SdlcCliController(lambda: make_host("alpha"))
        assert cli.run(["items", "new", "--kind", "task", "--desc", "LEDGER-CORE-TOOLS", "--idea", "make ledger",
                        "--description", "Build the ledger core.", "--tag", "p1", "--tag", "core"]) == 0
        assert cli.run(["items", "new", "--kind", "fix", "--desc", "FIX-X", "--idea", "fix x",
                        "--description", "Fix x."]) == 0
        capsys.readouterr()
        assert cli.run(["items", "list"]) == 0
        lines = capsys.readouterr().out.splitlines()
        assert lines[:3] == [
            "#  ITEM                        STATUS   CHAIN  TAGS",
            "1  ITM-0001-LEDGER-CORE-TOOLS  BACKLOG  -      p1, core",
            "2  ITM-0002-FIX-X              BACKLOG  -      -",
        ]
        assert lines[3] == "" and lines[4].startswith("ledger as of ")

    def test_reports_errors_and_blocked_dependencies(self, make_host: Callable[[str], AppWiring],
                                                     capsys: pytest.CaptureFixture) -> None:
        """Returns the error code for refused commands and the blocked code for unmet dependencies."""
        wiring = make_host("alpha")
        cli = SdlcCliController(lambda: wiring)
        assert cli.run(["items", "show", "ITM-0009"]) == EXIT_ERROR
        assert "no item ITM-0009" in capsys.readouterr().err
        cli.run(["items", "new", "--kind", "fix", "--desc", "LEDGER-CORE-TOOLS", "--idea", "a", "--description", "b"])
        cli.run(["items", "new", "--kind", "fix", "--desc", "GRAPH-CLAIM-AMEND", "--idea", "a", "--description", "b",
                 "--depends", "ITM-0001"])
        capsys.readouterr()
        assert cli.run(["items", "depends", "check", "ITM-0002"]) == EXIT_BLOCKED
        assert "BLOCKED ITM-0002 by ITM-0001 (BACKLOG)" in capsys.readouterr().out
        assert cli.run(["items", "new", "--kind", "fix", "--desc", "X-Y", "--description", "b"]) == EXIT_ERROR

    @pytest.mark.parametrize("arguments", [
        [], ["unknown"], ["items", "show"], ["items", "new", "--kind", "invalid", "--desc", "A-B"],
        ["items", "list", "--status", "invalid"], ["log", "tail", "ITM-0001", "--lines", "invalid"],
        ["items", "list", "--include", "invalid"], ["items", "list", "--exclude", "invalid"],
        ["chains", "list", "--include", "invalid"], ["chains", "list", "--exclude", "invalid"],
        ["chains", "list", "--include", "TESTING"], ["chains", "list", "--exclude", "OBSOLETE"],
    ])
    def test_invalid_arguments_need_no_repository(self, arguments: List[str],
                                                  capsys: pytest.CaptureFixture) -> None:
        """Rejects invalid CLI input before repository initialization."""
        factory = Mock(side_effect=AssertionError("repository must remain unopened"))
        cli = SdlcCliController(factory)
        assert cli.run(arguments) == EXIT_ERROR
        assert "Usage:" in capsys.readouterr().err
        factory.assert_not_called()

    def test_help_needs_no_repository(self, capsys: pytest.CaptureFixture) -> None:
        """Shows long and short help for every command without repository access."""
        factory = Mock(side_effect=AssertionError("repository must remain unopened"))
        cli = SdlcCliController(factory)

        # Covers root help and all command help flags
        for command in [None, *cli.build_command().commands]:
            for flag in ["--help", "-h"]:
                arguments = [flag] if command is None else [command, flag]
                assert cli.run(arguments) == 0
                assert "Usage:" in capsys.readouterr().out
        factory.assert_not_called()

    @pytest.mark.parametrize("arguments, expected", [
        (["items", "tag", "add", "ITM-0001", "first", "second"],
         {"action": "add", "item_id": "ITM-0001", "tags": ["first", "second"]}),
        (["items", "depends", "set", "ITM-0001", "none"],
         {"action": "set", "item_id": "ITM-0001", "dependencies": ["none"]}),
        (["items", "list", "--tag", "first", "--tag", "second", "--status", "BACKLOG", "--json"],
         {"tag": ["first", "second"], "status": ["BACKLOG"], "exclude": [], "desc": False,
          "colors": "auto", "as_json": True, "depends": False}),
        (["stats"], {"report": "items", "item_id": None, "sql": None, "as_json": False}),
        (["log", "tail", "ITM-0001", "-f", "--lines", "5"],
         {"action": "tail", "item_id": "ITM-0001", "message": [], "role": None,
          "task": None, "block": None, "level": "info", "follow": True, "lines": 5}),
        (["lock", "status"], {"action": "status", "name": None, "holder": None,
                              "no_wait": False, "steal": False, "force": False}),
        (["chains", "new", "--desc", "A-B", "--description", "d", "--item", "ITM-0002", "--item", "ITM-0001"],
         {"desc": "A-B", "description": "d", "description_file": None, "tag": [], "item": ["ITM-0002", "ITM-0001"]}),
        (["items", "amend", "ITM-0001", "--desc", "A-B", "--idea", "x"],
         {"item_id": "ITM-0001", "desc": "A-B", "idea": "x", "idea_file": None, "description": None,
          "description_file": None}),
        (["chains", "amend", "CHN-0001", "--description", "d"],
         {"chain_id": "CHN-0001", "desc": None, "description": "d", "description_file": None}),
        (["chains", "items", "CHN-0001", "none"], {"chain_id": "CHN-0001", "items": ["none"]}),
        (["chains", "list", "--status", "IN_PROGRESS"],
         {"status": ["IN_PROGRESS"], "exclude": [], "with_tasks": False, "desc": False,
          "colors": "auto", "as_json": False}),
        (["chains", "list", "--with-tasks"],
         {"status": [], "exclude": [], "with_tasks": True, "desc": False, "colors": "auto", "as_json": False}),
        (["worktree", "snapshot", "ITM-0001", "--json"],
         {"action": "snapshot", "item_id": "ITM-0001", "name": None, "base": None, "delete_branch": False,
          "message": None, "expected_tree": None, "expected_artifacts": None, "expected_commit": None,
          "codex_session": None, "as_json": True}),
        (["worktree", "settle", "ITM-0001", "--expected-tree", "abc", "--message", "review"],
         {"action": "settle", "item_id": "ITM-0001", "name": None, "base": None, "delete_branch": False,
          "message": "review", "expected_tree": "abc", "expected_artifacts": None, "expected_commit": None,
          "codex_session": None, "as_json": False}),
        (["worktree", "verified", "ITM-0001", "--expected-tree", "abc", "--expected-artifacts", "a" * 64],
         {"action": "verified", "item_id": "ITM-0001", "name": None, "base": None, "delete_branch": False,
          "message": None, "expected_tree": "abc", "expected_artifacts": "a" * 64, "expected_commit": None,
          "codex_session": None, "as_json": False}),
    ])
    def test_click_argument_contract(self, arguments: List[str], expected: Dict[str, Any]) -> None:
        """Preserves repeatable values, optional arguments, defaults, and callback signatures."""
        cli = SdlcCliController(Mock())
        command = cli.build_command()
        selected = command.commands[arguments[0]]
        if isinstance(selected, click.Group):
            selected = selected.commands[arguments[1]]
        callback = selected.callback
        recorder = Mock(return_value=0)
        selected.callback = recorder
        assert command.main(args=arguments, standalone_mode=False) == 0
        assert recorder.call_args.kwargs == expected
        inspect.signature(callback).bind(**recorder.call_args.kwargs)

    def test_promotion_forwards_explicit_artifact_digest(self) -> None:
        """Forwards the explicit INPUT digest and tested commit to the promotion usecase."""
        wiring = Mock()
        wiring.worktree_usecases.promote.return_value = "installed-commit"
        cli = SdlcCliController(lambda: wiring)
        assert cli.run(["worktree", "promote", "ITM-0001", "--expected-commit", "tested-commit",
                        "--expected-artifacts", "a" * 64]) == 0
        wiring.worktree_usecases.promote.assert_called_once_with("ITM-0001", "tested-commit", "a" * 64)

    def test_test_domains_prints_targets_on_stdout_and_explanations_on_stderr(
            self, capsys: pytest.CaptureFixture) -> None:
        """Splits the selection into target lines on stdout and explanation lines on stderr."""
        wiring = Mock()
        wiring.system_test_usecases.select.return_value = SystemTestSelection(
            targets=["tests/system/graph", "tests/system/stack"],
            explanations=["src/app/services/graph/app.py -> graph", "tools/scr/stack/run.sh -> stack"],
        )
        assert SdlcCliController(lambda: wiring).run(["test-domains", "--base", "abc123"]) == 0
        wiring.system_test_usecases.select.assert_called_once_with("abc123")
        captured = capsys.readouterr()
        assert captured.out.splitlines() == ["tests/system/graph", "tests/system/stack"]
        assert captured.err.splitlines() == ["src/app/services/graph/app.py -> graph",
                                             "tools/scr/stack/run.sh -> stack"]

    def test_file_input_tags_and_task_status(self, make_host: Callable[[str], AppWiring], plan_text: str,
                                            tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Preserves file input, repeated tags, dependency clearing, and task updates."""
        cli = SdlcCliController(lambda: make_host("alpha"))
        idea = tmp_path / "idea.txt"
        description = tmp_path / "description.txt"
        idea.write_text("Build CLI.")
        description.write_text("Keep command contracts.")
        assert cli.run(["items", "new", "--kind", "task", "--desc", "LEDGER-CORE-TOOLS", "--idea-file", str(idea),
                        "--description-file", str(description), "--tag", "first", "--tag", "second"]) == 0
        assert cli.run(["items", "show", "ITM-0001", "--json"]) == 0
        output = capsys.readouterr().out
        assert '"first"' in output and '"second"' in output and "Keep command contracts." in output
        assert cli.run(["items", "depends", "set", "ITM-0001", "none"]) == 0
        assert cli.run(["items", "plan", "edit", "ITM-0001"]) == 0
        draft = capsys.readouterr().out.splitlines()[-1]
        Path(draft).write_text(plan_text)
        assert cli.run(["items", "plan", "approve", "ITM-0001"]) == 0
        assert cli.run(["items", "schedule", "ITM-0001"]) == 0
        assert cli.run(["items", "status", "set", "ITM-0001", "IN_PROGRESS"]) == 0
        assert cli.run(["items", "task", "set", "ITM-0001", "IN_PROGRESS", "TSK-0001"]) == 0
        assert cli.run(["items", "task", "set", "ITM-0001", "VALIDATED", "TSK-0001"]) == 0
        assert cli.run(["items", "task", "set", "ITM-0001", "DONE", "TSK-0001"]) == 0
        assert "1/3" in capsys.readouterr().out
        assert cli.run(["stats", "--item", "ITM-0001", "--json"]) == 0

    def test_item_amend_flow(self, make_host: Callable[[str], AppWiring], tmp_path: Path,
                             capsys: pytest.CaptureFixture) -> None:
        """Amends the idea from a file and the description inline, then shows the new text and the history line."""
        cli = SdlcCliController(lambda: make_host("alpha"))
        assert cli.run(["items", "new", "--kind", "task", "--desc", "LEDGER-CORE-TOOLS", "--idea", "old idea",
                        "--description", "Old description."]) == 0
        idea = tmp_path / "idea.txt"
        idea.write_text("New idea from a file.")
        capsys.readouterr()
        assert cli.run(["items", "amend", "ITM-0001", "--idea-file", str(idea),
                        "--description", "New description."]) == 0
        output = capsys.readouterr().out
        assert "ITM-0001-LEDGER-CORE-TOOLS amended: idea, description" in output
        assert "note:" not in output
        assert cli.run(["items", "show", "ITM-0001"]) == 0
        output = capsys.readouterr().out
        assert "idea: New idea from a file." in output and "New description." in output
        assert "old idea" not in output and "Old description." not in output
        assert "amended  idea, description" in output

    def test_item_amend_renames_slug(self, make_host: Callable[[str], AppWiring],
                                     capsys: pytest.CaptureFixture) -> None:
        """Replaces the DESC slug and keeps the short id."""
        cli = SdlcCliController(lambda: make_host("alpha"))
        assert cli.run(["items", "new", "--kind", "task", "--desc", "LEDGER-CORE-TOOLS", "--idea", "a",
                        "--description", "b"]) == 0
        capsys.readouterr()
        assert cli.run(["items", "amend", "ITM-0001", "--desc", "GRAPH-CLAIM-AMEND"]) == 0
        assert ("ITM-0001-GRAPH-CLAIM-AMEND amended: desc LEDGER-CORE-TOOLS -> GRAPH-CLAIM-AMEND"
                in capsys.readouterr().out)

    def test_item_amend_of_planned_item_notes_unchanged_plan(self, make_host: Callable[[str], AppWiring],
                                                             plan_text: str, capsys: pytest.CaptureFixture) -> None:
        """Tells the user that the approved plan stays as it is and how to replan."""
        cli = SdlcCliController(lambda: make_host("alpha"))
        assert cli.run(["items", "new", "--kind", "task", "--desc", "LEDGER-CORE-TOOLS", "--idea", "a",
                        "--description", "b"]) == 0
        assert cli.run(["items", "plan", "edit", "ITM-0001"]) == 0
        Path(capsys.readouterr().out.splitlines()[-1]).write_text(plan_text)
        assert cli.run(["items", "plan", "approve", "ITM-0001"]) == 0
        capsys.readouterr()
        assert cli.run(["items", "amend", "ITM-0001", "--idea", "new idea"]) == 0
        output = capsys.readouterr().out
        assert "ITM-0001-LEDGER-CORE-TOOLS amended: idea" in output
        assert ("note: plan r1 is unchanged (approved r1); run /sdlc-plan ITM-0001 to replan against the new text"
                in output)

    @pytest.mark.parametrize("arguments, message", [
        (["--idea", "x", "--idea-file", "idea.txt"], "give at most one of --idea or --idea-file"),
        ([], "the amendment changes no field"),
        (["--idea", ""], "idea must not be empty"),
    ])
    def test_item_amend_refusals(self, make_host: Callable[[str], AppWiring], arguments: List[str], message: str,
                                 capsys: pytest.CaptureFixture) -> None:
        """Returns the error code for both idea forms, no field option, and an empty idea."""
        cli = SdlcCliController(lambda: make_host("alpha"))
        assert cli.run(["items", "new", "--kind", "task", "--desc", "LEDGER-CORE-TOOLS", "--idea", "a",
                        "--description", "b"]) == 0
        capsys.readouterr()
        assert cli.run(["items", "amend", "ITM-0001", *arguments]) == EXIT_ERROR
        assert message in capsys.readouterr().err

    def test_chain_flow(self, make_host: Callable[[str], AppWiring], capsys: pytest.CaptureFixture) -> None:
        """Mints a chain, replaces its items, lists it, and shows its members in order."""
        cli = SdlcCliController(lambda: make_host("alpha"))
        for desc in ["LEDGER-CORE-TOOLS", "GRAPH-CLAIM-AMEND"]:
            assert cli.run(["items", "new", "--kind", "task", "--desc", desc, "--idea", "a", "--description", "b"]) == 0
        capsys.readouterr()
        assert cli.run(["chains", "new", "--desc", "EMBEDDING-PIPELINE", "--description", "Embed the corpus.",
                        "--tag", "p1", "--item", "ITM-0001"]) == 0
        assert capsys.readouterr().out.strip() == "CHN-0001-EMBEDDING-PIPELINE"
        assert cli.run(["chains", "items", "CHN-0001", "ITM-0002", "ITM-0001"]) == 0
        assert "items: ITM-0002 -> ITM-0001" in capsys.readouterr().out
        assert cli.run(["chains", "list"]) == 0
        output = capsys.readouterr().out

        # Matches the chain row by its columns: chain, status, prototype, items, tags
        assert ["1", "CHN-0001-EMBEDDING-PIPELINE", "BACKLOG", "P1", "2", "p1"] in [line.split() for line in output.splitlines()]
        assert cli.run(["chains", "list", "--with-tasks"]) == 0
        rows = capsys.readouterr().out.splitlines()
        assert rows[1].split()[1] == "CHN-0001-EMBEDDING-PIPELINE"
        assert rows[2].split()[1] == "ITM-0002-GRAPH-CLAIM-AMEND"
        assert rows[3].split()[1] == "ITM-0001-LEDGER-CORE-TOOLS"
        assert cli.run(["chains", "list", "--status", "DONE"]) == 0
        assert "EMBEDDING-PIPELINE" not in capsys.readouterr().out
        assert cli.run(["chains", "show", "chn-0001"]) == 0
        lines = capsys.readouterr().out.splitlines()
        members = [line for line in lines if line.startswith(("1 ", "2 "))]
        assert "ITM-0002-GRAPH-CLAIM-AMEND" in members[0] and "ITM-0001-LEDGER-CORE-TOOLS" in members[1]
        assert cli.run(["chains", "show", "CHN-0001", "--json"]) == 0
        assert '"status": "BACKLOG"' in capsys.readouterr().out
        assert cli.run(["chains", "items", "CHN-0002", "ITM-0001"]) == EXIT_ERROR
        assert "no chain CHN-0002" in capsys.readouterr().err

    def test_group_help_needs_no_repository(self, capsys: pytest.CaptureFixture) -> None:
        """Shows long and short help for every items and chains subcommand without repository access."""
        factory = Mock(side_effect=AssertionError("repository must remain unopened"))
        cli = SdlcCliController(factory)
        root = cli.build_command()

        # Covers every subcommand of both groups with both help flags
        for group in ["items", "chains"]:
            for subcommand in root.commands[group].commands:
                for flag in ["--help", "-h"]:
                    assert cli.run([group, subcommand, flag]) == 0
                    assert "Usage:" in capsys.readouterr().out
        factory.assert_not_called()

    def test_chain_amend_flow(self, make_host: Callable[[str], AppWiring], capsys: pytest.CaptureFixture) -> None:
        """Amends the description and the DESC slug of a chain, then shows the new text and full id."""
        cli = SdlcCliController(lambda: make_host("alpha"))
        assert cli.run(["chains", "new", "--desc", "EMBEDDING-PIPELINE", "--description", "Old chain text."]) == 0
        capsys.readouterr()
        assert cli.run(["chains", "amend", "CHN-0001", "--desc", "EMBEDDING-SAL-PIPELINE",
                        "--description", "New chain text."]) == 0
        assert "CHN-0001-EMBEDDING-SAL-PIPELINE amended: desc EMBEDDING-PIPELINE -> EMBEDDING-SAL-PIPELINE" in (
            capsys.readouterr().out)
        assert cli.run(["chains", "show", "CHN-0001"]) == 0
        output = capsys.readouterr().out
        assert "CHN-0001-EMBEDDING-SAL-PIPELINE" in output and "New chain text." in output
        assert "Old chain text." not in output
