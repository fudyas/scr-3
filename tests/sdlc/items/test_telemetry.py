import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List

from sdlc.algorithms.timestamps import TimestampHelper
from sdlc.controllers.hook_cli import TelemetryHookController
from sdlc.models.item import ItemKind
from sdlc.wiring import AppWiring


class TranscriptWriterHelper:
    """Writes transcript files shaped like Claude Code's."""

    @staticmethod
    def assistant(message_id: str, at: str, output_tokens: int, tool: str = "Bash") -> Dict[str, Any]:
        """Returns one assistant line."""
        return {
            "type": "assistant", "timestamp": at, "isSidechain": False, "perTurnEffort": "medium",
            "message": {"id": message_id, "model": "claude-sonnet-5-5",
                        "content": [{"type": "tool_use", "id": f"tool-{message_id}", "name": tool, "input": {}}],
                        "usage": {"input_tokens": 1, "output_tokens": output_tokens,
                                  "cache_creation_input_tokens": 10, "cache_read_input_tokens": 100}},
        }

    @staticmethod
    def write(path: Path, lines: List[Dict[str, Any]]) -> Path:
        """Appends the lines to the transcript file and returns its path."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as handle:
            for line in lines:
                handle.write(json.dumps(line) + "\n")
        return path


class LogicalClockHelper:
    """A strictly increasing UTC clock on one logical sequence, so marks and turns order deterministically."""

    def __init__(self) -> None:
        """Starts the clock at a fixed base moment."""
        self._moment = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def now(self) -> str:
        """Advances the clock one millisecond and returns the new moment as an ISO timestamp."""
        self._moment += timedelta(milliseconds=1)
        return TimestampHelper.format(self._moment)


class TestTelemetryHarvest:
    """Covers hook routing, attribution, incremental harvest, and the reports."""

    def test_reports_tokens_per_item_role_and_task(self, make_host: Callable[..., AppWiring],
                                                    tmp_path: Path) -> None:
        """Attributes orchestrator turns by mark and subagent runs by launch tag, then reports them."""
        clock = LogicalClockHelper()
        host = make_host("alpha", now=clock.now)
        hooks = TelemetryHookController(host)
        session = tmp_path / "projects" / "proj" / "s1.jsonl"

        # Marks the session as running ITM-0001, then writes two orchestrator turns after the mark
        hooks.handle({"hook_event_name": "PostToolUse", "tool_name": "Bash", "session_id": "s1",
                      "tool_input": {"command": "./bin/lets sdlc mark ITM-0001-LEDGER run"}})
        TranscriptWriterHelper.write(session, [
            TranscriptWriterHelper.assistant("m1", clock.now(), 40),
            TranscriptWriterHelper.assistant("m2", clock.now(), 60),
        ])
        hooks.handle({"hook_event_name": "Stop", "session_id": "s1", "transcript_path": str(session)})

        # Writes one more turn; the next Stop harvests only the new line
        TranscriptWriterHelper.write(session, [TranscriptWriterHelper.assistant("m3", clock.now(), 5)])
        hooks.handle({"hook_event_name": "Stop", "session_id": "s1", "transcript_path": str(session)})

        # Records a tagged swe run, its resumed second harvest, and a validator run
        swe = TranscriptWriterHelper.write(tmp_path / "projects" / "proj" / "s1" / "subagents" / "agent-a1.jsonl", [
            TranscriptWriterHelper.assistant("s1", "2099-01-01T00:01:00.000Z", 100, tool="Edit"),
        ])
        (swe.with_suffix(".meta.json")).write_text(json.dumps(
            {"agentType": "swe", "description": "ITM-0001 TSK-0001 swe: add ledger"}))
        hooks.handle({"hook_event_name": "SubagentStop", "session_id": "s1", "agent_id": "a1",
                      "agent_type": "swe", "agent_transcript_path": str(swe)})
        TranscriptWriterHelper.write(swe, [TranscriptWriterHelper.assistant("s2", "2099-01-01T00:02:00.000Z", 50)])
        hooks.handle({"hook_event_name": "SubagentStop", "session_id": "s1", "agent_id": "a1",
                      "agent_type": "swe", "agent_transcript_path": str(swe)})
        validator = TranscriptWriterHelper.write(tmp_path / "projects" / "proj" / "s1" / "subagents" / "agent-a2.jsonl",
                                                 [TranscriptWriterHelper.assistant("v1", "2099-01-01T00:03:00.000Z", 7)])
        (validator.with_suffix(".meta.json")).write_text(json.dumps(
            {"agentType": "validator", "description": "ITM-0001 BLK-0001 validator: gates"}))
        hooks.handle({"hook_event_name": "SubagentStop", "session_id": "s1", "agent_id": "a2",
                      "agent_transcript_path": str(validator)})

        # Ends attribution; a later turn stays unattributed because its timestamp follows the end mark
        hooks.handle({"hook_event_name": "PostToolUse", "tool_name": "Bash", "session_id": "s1",
                      "tool_input": {"command": "./bin/lets sdlc mark ITM-0001 end"}})
        TranscriptWriterHelper.write(session, [TranscriptWriterHelper.assistant("m4", clock.now(), 9)])
        hooks.handle({"hook_event_name": "Stop", "session_id": "s1", "transcript_path": str(session)})

        stats = host.stats_usecases
        items = self._records(stats.report("items", None))
        turn_tokens = 3 * (1 + 10 + 100) + 40 + 60 + 5
        swe_tokens = 2 * (1 + 10 + 100) + 150
        validator_tokens = (1 + 10 + 100) + 7
        assert items == [{"item": "ITM-0001", "orchestrator_tokens": turn_tokens,
                          "agent_tokens": swe_tokens + validator_tokens,
                          "total_tokens": turn_tokens + swe_tokens + validator_tokens,
                          "agent_output_tokens": 157, "agent_runs": 2, "tasks": 1, "reworks": 0,
                          "agent_seconds": 60.0}]
        roles = {row["role"]: row for row in self._records(stats.report("roles", None))}
        assert roles["swe"]["runs"] == 1 and roles["swe"]["avg_tokens_per_task"] == swe_tokens
        assert roles["validator"]["avg_tokens_per_task"] is None
        tasks = self._records(stats.report("tasks", "ITM-0001"))
        assert tasks[0]["swe_tokens"] == swe_tokens and tasks[0]["swe_runs"] == 1
        stages = self._records(stats.report("stages", None))
        assert {(row["item"], row["stage"], row["calls"]) for row in stages} == {("ITM-0001", "run", 3),
                                                                                  ("-", "-", 1)}

    def test_keeps_last_appended_agent_harvest_on_equal_timestamps(self, make_host: Callable[..., AppWiring],
                                                                    tmp_path: Path) -> None:
        """Counts one run with the latest cumulative usage when two harvests share one timestamp."""
        host = make_host("alpha", now=lambda: "2026-01-01T00:00:00.000Z")
        hooks = TelemetryHookController(host)
        swe = TranscriptWriterHelper.write(tmp_path / "projects" / "proj" / "s1" / "subagents" / "agent-a1.jsonl", [
            TranscriptWriterHelper.assistant("s1", "2099-01-01T00:01:00.000Z", 100, tool="Edit"),
        ])
        (swe.with_suffix(".meta.json")).write_text(json.dumps(
            {"agentType": "swe", "description": "ITM-0001 TSK-0001 swe: add ledger"}))
        hooks.handle({"hook_event_name": "SubagentStop", "session_id": "s1", "agent_id": "a1",
                      "agent_type": "swe", "agent_transcript_path": str(swe)})
        TranscriptWriterHelper.write(swe, [TranscriptWriterHelper.assistant("s2", "2099-01-01T00:02:00.000Z", 50)])
        hooks.handle({"hook_event_name": "SubagentStop", "session_id": "s1", "agent_id": "a1",
                      "agent_type": "swe", "agent_transcript_path": str(swe)})

        query = host.stats_usecases.query("SELECT COUNT(*), SUM(total_tokens) FROM agent_runs")
        assert query.rows == [[1, 2 * (1 + 10 + 100) + 150]]

    def test_ignores_non_mark_commands_and_records_events(self, make_host: Callable[..., AppWiring]) -> None:
        """Ignores ordinary Bash calls and records pipeline events from usecases."""
        host = make_host("alpha")
        assert not host.telemetry_usecases.on_bash_command("s1", "git status")
        host.item_usecases.mint(ItemKind.TASK, "LEDGER-CORE-TOOLS", "idea", "Description.", [], [])
        doctor = dict(host.stats_usecases.doctor().rows)
        assert doctor["pipeline events"] == 1 and doctor["attributions"] == 0
        query = host.stats_usecases.query("SELECT event, item FROM events")
        assert query.rows == [["item_minted", "ITM-0001"]]

    def test_attributes_a_mark_that_a_shell_variable_hides(self, make_host: Callable[..., AppWiring]) -> None:
        """Reads the mark from the command output when the command text holds only `$L mark`."""
        host = make_host("alpha")
        hooks = TelemetryHookController(host)
        hooks.handle({
            "hook_event_name": "PostToolUse", "tool_name": "Bash", "session_id": "s1",
            "tool_input": {"command": 'L="./bin/lets sdlc" && $L mark ITM-0001 review && echo done'},
            "tool_response": {"stdout": "mark ITM-0001 review\ndone", "stderr": "", "interrupted": False},
        })
        query = host.stats_usecases.query("SELECT item, stage, source FROM attributions")
        assert query.rows == [["ITM-0001", "review", "mark"]]

    def test_records_the_last_mark_of_one_call(self, make_host: Callable[..., AppWiring]) -> None:
        """Records the end of attribution when one call marks a stage and then ends it."""
        host = make_host("alpha")
        TelemetryHookController(host).handle({
            "hook_event_name": "PostToolUse", "tool_name": "Bash", "session_id": "s1",
            "tool_input": {"command": "$L mark ITM-0001 run && $L mark ITM-0001 end"},
            "tool_response": {"stdout": "mark ITM-0001 run\nmark ITM-0001 end\n"},
        })
        query = host.stats_usecases.query("SELECT item, stage FROM attributions")
        assert query.rows == [["", ""]]

    def test_ignores_a_payload_without_a_usable_tool_response(self, make_host: Callable[..., AppWiring]) -> None:
        """Handles a missing or non-text tool response without recording anything."""
        host = make_host("alpha")
        hooks = TelemetryHookController(host)
        for response in (None, 5, {"stderr": "x"}):
            hooks.handle({"hook_event_name": "PostToolUse", "tool_name": "Bash", "session_id": "s1",
                          "tool_input": {"command": "echo mark of the beast"}, "tool_response": response})
        assert host.stats_usecases.query("SELECT COUNT(*) FROM attributions").rows == [[0]]

    def test_skips_a_subagent_stop_without_a_transcript(self, make_host: Callable[..., AppWiring],
                                                        tmp_path: Path) -> None:
        """Records no agent run for a hook-only stop whose transcript file does not exist."""
        host = make_host("alpha")
        TelemetryHookController(host).handle({
            "hook_event_name": "SubagentStop", "session_id": "s1", "agent_id": "ghost",
            "agent_transcript_path": str(tmp_path / "projects" / "proj" / "s1" / "subagents" / "agent-ghost.jsonl"),
        })
        assert host.stats_usecases.query("SELECT COUNT(*) FROM agent_runs").rows == [[0]]
        doctor = dict(host.stats_usecases.doctor().rows)
        assert doctor["agent runs"] == 0 and doctor["agent runs without a transcript"] == 0

    def test_blacklisted_item_is_left_out_of_every_measurement(self, make_host: Callable[..., AppWiring],
                                                                tmp_path: Path) -> None:
        """Hides a blacklisted item from reports, queries, and the doctor while its raw records stay on disk."""
        clock = LogicalClockHelper()
        base = make_host("alpha", now=clock.now)
        host = AppWiring(base.settings.model_copy(update={"telemetry_blacklist": ["ITM-0001"]}), now=clock.now)
        hooks = TelemetryHookController(host)
        session = tmp_path / "projects" / "proj" / "s1.jsonl"
        for desc in ("LEDGER-CORE-TOOLS", "GRAPH-CLAIM-AMEND"):
            host.item_usecases.mint(ItemKind.TASK, desc, "idea", "Description.", [], [])

        # Records two orchestrator turns for ITM-0001, then one for ITM-0002
        hooks.handle({"hook_event_name": "PostToolUse", "tool_name": "Bash", "session_id": "s1",
                      "tool_input": {"command": "./bin/lets sdlc mark ITM-0001 run"}})
        TranscriptWriterHelper.write(session, [TranscriptWriterHelper.assistant("m1", clock.now(), 40),
                                               TranscriptWriterHelper.assistant("m2", clock.now(), 60)])
        hooks.handle({"hook_event_name": "Stop", "session_id": "s1", "transcript_path": str(session)})
        hooks.handle({"hook_event_name": "PostToolUse", "tool_name": "Bash", "session_id": "s1",
                      "tool_input": {"command": "./bin/lets sdlc mark ITM-0002 run"}})
        TranscriptWriterHelper.write(session, [TranscriptWriterHelper.assistant("m3", clock.now(), 5)])
        hooks.handle({"hook_event_name": "Stop", "session_id": "s1", "transcript_path": str(session)})

        # Records one agent run for each item
        for agent_id, item in (("a1", "ITM-0001"), ("a2", "ITM-0002")):
            run = TranscriptWriterHelper.write(
                tmp_path / "projects" / "proj" / "s1" / "subagents" / f"agent-{agent_id}.jsonl",
                [TranscriptWriterHelper.assistant(agent_id, "2099-01-01T00:01:00.000Z", 10)])
            run.with_suffix(".meta.json").write_text(json.dumps(
                {"agentType": "swe", "description": f"{item} TSK-0001 swe: work"}))
            hooks.handle({"hook_event_name": "SubagentStop", "session_id": "s1", "agent_id": agent_id,
                          "agent_type": "swe", "agent_transcript_path": str(run)})

        stats = host.stats_usecases
        items = self._records(stats.report("items", None))
        assert [row["item"] for row in items] == ["ITM-0002"]
        assert items[0]["orchestrator_tokens"] == 1 + 10 + 100 + 5
        assert stats.query("SELECT agent_id FROM agent_runs").rows == [["a2"]]
        assert stats.query("SELECT item FROM events").rows == [["ITM-0002"]]
        assert stats.query("SELECT item FROM attributions").rows == [["ITM-0002"]]
        assert stats.query("SELECT message_id FROM turns").rows == [["m3"]]
        doctor = dict(stats.doctor().rows)
        assert doctor["items left out by the blacklist"] == "ITM-0001" and doctor["agent runs"] == 1

        # Keeps the raw records, so removing the item from the blacklist brings the data back
        telemetry_dir = host.settings.telemetry_dir
        assert "ITM-0001" in (telemetry_dir / "agent_runs.jsonl").read_text()
        assert "ITM-0001" in (telemetry_dir / "attributions.jsonl").read_text()
        open_host = AppWiring(base.settings, now=clock.now)
        assert {row["item"] for row in self._records(open_host.stats_usecases.report("items", None))} == {
            "ITM-0001", "ITM-0002"}

    @staticmethod
    def _records(table: Any) -> List[Dict[str, Any]]:
        """Returns the table rows as dictionaries."""
        return [dict(zip(table.columns, row)) for row in table.rows]
