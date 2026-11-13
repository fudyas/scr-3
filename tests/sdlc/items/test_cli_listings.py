import re
import json
import sys
from typing import Callable, List

import click
import pytest

from sdlc.controllers.cli import SdlcCliController
from sdlc.models.item import ItemKind, ItemStatus, TaskStatus
from sdlc.wiring import AppWiring


class TestSdlcListings:
    """Covers status selection, nested descriptions, and terminal output through the real CLI."""

    @pytest.fixture
    def cli(self, make_host: Callable[[str], AppWiring], plan_text: str) -> SdlcCliController:
        """Creates active, backlog, and retired items with one chain for each."""
        host = make_host("alpha")
        slugs = ["ACTIVE-WORK", "BACKLOG-WORK", "RETIRED-WORK"]
        prototypes = ["p1", "P2", "p12"]
        for slug, prototype in zip(slugs, prototypes):
            host.item_usecases.mint(ItemKind.TASK, slug, "idea", f"{slug} description.\nSecond detail line.",
                                   ["sdlc", prototype], [])

        # Starts the first item through the supported lifecycle and retires the third
        host.plan_usecases.edit("ITM-0001").write_text(plan_text)
        host.plan_usecases.approve("ITM-0001")
        host.schedule_usecases.schedule("ITM-0001", None)
        host.item_usecases.set_status("ITM-0001", ItemStatus.IN_PROGRESS, False)
        host.item_usecases.set_status("ITM-0003", ItemStatus.OBSOLETE, False)
        for number, slug in enumerate(slugs, 1):
            host.chain_usecases.mint(slug, f"{slug} chain description.\nSecond chain detail.",
                                     ["sdlc", prototypes[number - 1]],
                                     [f"ITM-{number:04d}"])
        return SdlcCliController(lambda: host)

    @pytest.mark.parametrize("group, terminal", [("items", "OBSOLETE"), ("chains", "DONE")])
    def test_filters_include_first_and_exclude_last(self, cli: SdlcCliController, group: str, terminal: str,
                                                    capsys: pytest.CaptureFixture) -> None:
        """Preserves repeated filters, defaults, legacy status selection, and exclusion precedence in JSON."""
        cases = [
            ([], [1, 2, 3]),
            (["--exclude", terminal], [1, 2]),
            (["--include", "IN_PROGRESS", "--include", "BACKLOG"], [1, 2]),
            (["--exclude", "IN_PROGRESS", "--include", "IN_PROGRESS", "--include", "BACKLOG"], [2]),
            (["--include", "IN_PROGRESS", "--exclude", "IN_PROGRESS"], []),
            (["--exclude", "IN_PROGRESS", "--exclude", terminal], [2]),
            (["--status", "IN_PROGRESS"], [1]),
            (["--include", "IN_PROGRESS", "--status", "BACKLOG"], [1, 2]),
            (["--include", "in_progress"], [1]),
        ]
        for arguments, expected in cases:
            assert cli.run([group, "list", *arguments, "--desc", "--colors", "yes", "--json"]) == 0
            output = capsys.readouterr().out
            assert "\033[" not in output
            assert [record["number"] for record in json.loads(output)] == expected, arguments

        # Keeps item tag filters in effect alongside both status filters
        if group == "items":
            assert cli.run([group, "list", "--include", "BACKLOG", "--tag", "missing", "--json"]) == 0
            assert json.loads(capsys.readouterr().out) == []

    def test_chain_member_filters_preserve_parent_context(
            self, cli: SdlcCliController, capsys: pytest.CaptureFixture) -> None:
        """Selects matching items inside mixed chains and keeps complete summaries and member order."""
        host = cli.wiring
        host.chain_usecases.set_items("CHN-0002", [])
        host.chain_usecases.set_items("CHN-0001", ["ITM-0002", "ITM-0001"])
        for task_status in [TaskStatus.IN_PROGRESS, TaskStatus.VALIDATED, TaskStatus.DONE]:
            host.plan_usecases.set_task_status("ITM-0001", task_status, ["all"])
        for item_status in [ItemStatus.TESTING, ItemStatus.REVIEW, ItemStatus.DONE]:
            host.item_usecases.set_status("ITM-0001", item_status, False)

        # Covers both reported commands, item-only statuses, precedence, and empty chains
        cases = [
            ([], [(1, [2, 1]), (2, []), (3, [3])]),
            (["--include", "DONE"], [(1, [1])]),
            (["--exclude", "DONE"], [(1, [2]), (3, [3])]),
            (["--exclude", "DONE", "--include", "DONE", "--include", "BACKLOG"], [(1, [2])]),
            (["--include", "OBSOLETE"], [(3, [3])]),
            (["--include", "DONE", "--exclude", "DONE"], []),
            (["--include", "SCHEDULED"], []),
        ]
        for arguments, expected in cases:
            assert cli.run(["chains", "list", "--with-tasks", *arguments, "--json"]) == 0
            records = json.loads(capsys.readouterr().out)
            assert [(record["number"], [int(member["item"].split("-")[1]) for member in record["members"]])
                    for record in records] == expected, arguments
            if records and records[0]["number"] == 1:
                assert records[0]["status"] == "IN PROGRESS"
                assert records[0]["counts"] == {"BACKLOG": 1, "DONE": 1}
                assert records[0]["items"] == ["ITM-0002", "ITM-0001"]

            # Keeps text output and member descriptions consistent with the JSON selection
            assert cli.run(["chains", "list", "--with-tasks", *arguments, "--desc", "--colors", "no"]) == 0
            output = capsys.readouterr().out
            lines = output.splitlines()
            assert [int(line.strip().split("-")[1]) for line in lines if re.match(r"^\d+\s+ITM-", line)] == [
                member for _, members in expected for member in members]
            for number, slug in enumerate(["ACTIVE-WORK", "BACKLOG-WORK", "RETIRED-WORK"], 1):
                assert (f"        {slug} description." in output) == any(number in members for _, members in expected)

        # Retains chain-status selection when member output is absent
        assert cli.run(["chains", "list", "--include", "DONE", "--json"]) == 0
        assert [record["number"] for record in json.loads(capsys.readouterr().out)] == [3]

    def test_sync_refreshes_stale_host_listings(
            self, cli: SdlcCliController, make_host: Callable[[str], AppWiring],
            capsys: pytest.CaptureFixture) -> None:
        """Makes item and chain listings agree across hosts after the remote ledger changes."""
        other_host = make_host("beta")
        other_cli = SdlcCliController(lambda: other_host)
        assert other_cli.run(["sync"]) == 0
        capsys.readouterr()

        # Leaves beta's mirror stale while alpha retires a backlog item remotely
        cli.wiring.item_usecases.set_status("ITM-0002", ItemStatus.OBSOLETE, False)
        for group in ["items", "chains"]:
            arguments = [group, "list", "--json"]
            assert cli.run(arguments) == 0
            latest = json.loads(capsys.readouterr().out)
            assert other_cli.run(arguments) == 0
            stale = json.loads(capsys.readouterr().out)
            assert stale != latest
        assert other_cli.run(["sync"]) == 0
        capsys.readouterr()
        for group in ["items", "chains"]:
            arguments = [group, "list", "--json"]
            assert cli.run(arguments) == 0
            latest = json.loads(capsys.readouterr().out)
            assert other_cli.run(arguments) == 0
            assert json.loads(capsys.readouterr().out) == latest

    @pytest.mark.parametrize("group", ["items", "chains"])
    def test_colors_preserve_alignment_and_descriptions_follow_names(
            self, cli: SdlcCliController, group: str, capsys: pytest.CaptureFixture) -> None:
        """Keeps column widths independent of ANSI codes and indents every line of nested descriptions."""
        arguments: List[str] = [group, "list"] + (["--with-tasks"] if group == "chains" else [])
        assert cli.run([*arguments, "--colors", "no"]) == 0
        plain = capsys.readouterr().out
        assert "description." not in plain
        assert ("PROTOTYPE" in plain.splitlines()[0]) == (group == "chains")
        for number, slug, prototype in [(1, "ACTIVE-WORK", "P1"), (2, "BACKLOG-WORK", "P2"),
                                        (3, "RETIRED-WORK", "P12")]:
            record_lines = [line for line in plain.splitlines() if slug in line]
            assert record_lines
            if group == "chains":
                assert all(f"  {prototype} " in line for line in record_lines)
            if group == "items":
                assert f"CHN-{number:04d}-{slug}" in record_lines[0]
        if group == "items":
            assert plain.splitlines()[0].split() == ["#", "ITEM", "STATUS", "CHAIN", "TAGS"]
        assert cli.run([*arguments, "--colors", "yes"]) == 0
        colored = capsys.readouterr().out
        assert "\033[93m" in colored
        assert click.unstyle(colored) == plain

        assert cli.run([*arguments, "--desc", "--colors", "yes"]) == 0
        described = capsys.readouterr().out
        assert "    \033[2;90m" in described
        lines = click.unstyle(described).splitlines()
        for index, line in enumerate(lines):
            if line.startswith(("ITM-", "CHN-", "    ITM-")):
                nested = line.startswith("    ITM-")
                indent = "        " if nested else "    "
                assert lines[index + 1].startswith(indent) and "description." in lines[index + 1]
                assert lines[index + 2].startswith(indent + "Second")

        # Filters descriptions with their records and omits an excluded chain's members
        assert cli.run([*arguments, "--include", "IN_PROGRESS", "--desc", "--colors", "no"]) == 0
        filtered = capsys.readouterr().out
        assert "ACTIVE-WORK description." in filtered
        assert "BACKLOG-WORK" not in filtered and "RETIRED-WORK" not in filtered

    @pytest.mark.parametrize("tty, no_color, expected", [(True, False, True), (False, False, False), (True, True, False)])
    def test_auto_colors_respect_terminal_and_environment(
            self, cli: SdlcCliController, tty: bool, no_color: bool, expected: bool,
            monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
        """Colors terminal listings by default and leaves redirected or NO_COLOR output plain."""
        monkeypatch.setattr(sys.stdout, "isatty", lambda: tty)
        if no_color:
            monkeypatch.setenv("NO_COLOR", "")
        else:
            monkeypatch.delenv("NO_COLOR", raising=False)
        for group in ["items", "chains"]:
            assert cli.run([group, "list", "--desc"]) == 0
            assert ("\033[" in capsys.readouterr().out) is expected

    def test_dependencies_nest_below_filtered_items(
            self, cli: SdlcCliController, capsys: pytest.CaptureFixture) -> None:
        """Shows dependencies outside parent filters with their own status and description."""
        cli.wiring.item_usecases.set_dependencies("ITM-0002", ["ITM-0001"])
        arguments = ["items", "list", "--include", "BACKLOG", "--desc", "--colors", "no"]
        assert cli.run(arguments) == 0
        assert "ACTIVE-WORK" not in capsys.readouterr().out
        assert cli.run([*arguments, "--depends"]) == 0
        output = capsys.readouterr().out
        assert "    ITM-0001-ACTIVE-WORK" in output
        assert "        ACTIVE-WORK description." in output
        assert "IN PROGRESS" in output
        assert cli.run([*arguments, "--depends", "--json"]) == 0
        records = json.loads(capsys.readouterr().out)
        assert len(records) == 1 and records[0]["depends_on"] == ["ITM-0001"]

    @pytest.mark.parametrize("group, record", [("items", "ITM-0001"), ("chains", "CHN-0001")])
    def test_show_colors_and_indented_details(
            self, cli: SdlcCliController, group: str, record: str, capsys: pytest.CaptureFixture) -> None:
        """Preserves plain detail text across color modes and keeps JSON free of styles."""
        arguments = [group, "show", record]
        assert cli.run([*arguments, "--colors", "no"]) == 0
        plain = capsys.readouterr().out
        assert "    prototype: P1" in plain
        assert "    status: IN PROGRESS" in plain
        assert "        Second" in plain
        if group == "items":
            assert "    kind: task" in plain
        assert cli.run([*arguments, "--colors", "yes"]) == 0
        colored = capsys.readouterr().out
        assert "\033[93m" in colored
        assert click.unstyle(colored) == plain
        assert cli.run([*arguments, "--colors", "yes", "--json"]) == 0
        output = capsys.readouterr().out
        assert "\033[" not in output
        assert json.loads(output)["number"] == 1
