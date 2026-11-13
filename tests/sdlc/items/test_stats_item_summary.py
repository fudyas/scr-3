import json
from pathlib import Path
from typing import Any, Callable, Dict, List

import pytest

from sdlc.controllers.cli import EXIT_ERROR, SdlcCliController
from sdlc.controllers.hook_cli import TelemetryHookController
from sdlc.models.item import ItemStatus, TaskStatus
from sdlc.wiring import AppWiring
from tests.sdlc.items.test_plan_and_schedule_usecases import PlanFlowHelper
from tests.sdlc.items.test_telemetry import LogicalClockHelper, TranscriptWriterHelper


class ItemTelemetryHelper:
    """Builds the telemetry of one running item for the summary tests."""

    @staticmethod
    def build(make_host: Callable[..., AppWiring], plan_text: str, tmp_path: Path) -> AppWiring:
        """Returns a host whose ITM-0001 has orchestrator turns, swe and validator runs, and one rework."""
        clock = LogicalClockHelper()
        host = make_host("alpha", now=clock.now)
        hooks = TelemetryHookController(host)
        session = tmp_path / "projects" / "proj" / "s1.jsonl"

        # Mints a running item and sends one task back to its engineer
        item_id = PlanFlowHelper.mint(host, "LEDGER-CORE-TOOLS")
        PlanFlowHelper.approve(host, item_id, plan_text)
        host.schedule_usecases.schedule(item_id, None)
        host.item_usecases.set_status(item_id, ItemStatus.IN_PROGRESS, False)
        host.plan_usecases.set_task_status(item_id, TaskStatus.IN_PROGRESS, ["TSK-0001"])
        host.plan_usecases.set_task_status(item_id, TaskStatus.VALIDATED, ["TSK-0001"])
        host.plan_usecases.rework_task(item_id, "TSK-0001", "qa", "system test failed")

        # Writes two orchestrator turns after the mark of the item
        hooks.handle({"hook_event_name": "PostToolUse", "tool_name": "Bash", "session_id": "s1",
                      "tool_input": {"command": f"./bin/lets sdlc mark {item_id} run"}})
        TranscriptWriterHelper.write(session, [
            TranscriptWriterHelper.assistant("m1", clock.now(), 40),
            TranscriptWriterHelper.assistant("m2", clock.now(), 60),
        ])
        hooks.handle({"hook_event_name": "Stop", "session_id": "s1", "transcript_path": str(session)})

        # Records one tagged swe run and one tagged validator run
        subagents = tmp_path / "projects" / "proj" / "s1" / "subagents"
        swe = TranscriptWriterHelper.write(subagents / "agent-a1.jsonl", [
            TranscriptWriterHelper.assistant("s1", "2099-01-01T00:01:00.000Z", 100, tool="Edit"),
        ])
        swe.with_suffix(".meta.json").write_text(json.dumps(
            {"agentType": "swe", "description": f"{item_id} TSK-0001 swe: add ledger"}))
        hooks.handle({"hook_event_name": "SubagentStop", "session_id": "s1", "agent_id": "a1",
                      "agent_type": "swe", "agent_transcript_path": str(swe)})
        validator = TranscriptWriterHelper.write(subagents / "agent-a2.jsonl", [
            TranscriptWriterHelper.assistant("v1", "2099-01-01T00:03:00.000Z", 7),
        ])
        validator.with_suffix(".meta.json").write_text(json.dumps(
            {"agentType": "validator", "description": f"{item_id} BLK-0001 validator: gates"}))
        hooks.handle({"hook_event_name": "SubagentStop", "session_id": "s1", "agent_id": "a2",
                      "agent_type": "validator", "agent_transcript_path": str(validator)})
        return host


class TestItemSummary:
    """Covers the per-item summary report and its command line form."""

    def test_summary_lists_each_role_and_a_total(self, make_host: Callable[..., AppWiring], plan_text: str,
                                                  tmp_path: Path) -> None:
        """Reports the orchestrator, each agent role by tokens, and a total with tasks and reworks."""
        host = ItemTelemetryHelper.build(make_host, plan_text, tmp_path)
        rows = {row["role"]: row for row in self._records(host.stats_usecases.item_summary("ITM-0001"))}
        orchestrator_tokens = 2 * (1 + 10 + 100) + 40 + 60
        swe_tokens = (1 + 10 + 100) + 100
        validator_tokens = (1 + 10 + 100) + 7
        assert list(rows) == ["orchestrator", "swe", "validator", "total"]
        assert rows["orchestrator"] == {"role": "orchestrator", "runs": 2, "tokens": orchestrator_tokens,
                                        "output_tokens": rows["orchestrator"]["output_tokens"],
                                        "seconds": None, "tasks": None, "reworks": None}
        assert rows["swe"]["runs"] == 1 and rows["swe"]["tokens"] == swe_tokens
        assert rows["swe"]["tasks"] == 1 and rows["swe"]["reworks"] is None
        assert rows["validator"]["tokens"] == validator_tokens and rows["validator"]["tasks"] == 0
        assert rows["total"]["runs"] == 4
        assert rows["total"]["tokens"] == orchestrator_tokens + swe_tokens + validator_tokens
        assert rows["total"]["output_tokens"] == (rows["orchestrator"]["output_tokens"]
                                                  + rows["swe"]["output_tokens"] + rows["validator"]["output_tokens"])
        assert rows["total"]["tasks"] == 1 and rows["total"]["reworks"] == 1

    def test_summary_of_an_item_without_telemetry_is_one_zero_total_row(self,
                                                                         make_host: Callable[..., AppWiring]) -> None:
        """Returns only the total row, with zero counts, for an item that has no telemetry."""
        host = make_host("alpha")
        assert self._records(host.stats_usecases.item_summary("ITM-0009")) == [
            {"role": "total", "runs": 0, "tokens": 0, "output_tokens": 0, "seconds": 0, "tasks": 0, "reworks": 0}]

    def test_cli_accepts_an_item_id(self, make_host: Callable[..., AppWiring], plan_text: str, tmp_path: Path,
                                    capsys: pytest.CaptureFixture) -> None:
        """Prints the summary for a short and a full item id, as a table and as JSON."""
        host = ItemTelemetryHelper.build(make_host, plan_text, tmp_path)
        cli = SdlcCliController(lambda: host)
        capsys.readouterr()
        assert cli.run(["stats", "ITM-0001"]) == 0
        table = capsys.readouterr().out
        assert "orchestrator" in table and "total" in table
        assert cli.run(["stats", "ITM-0001-LEDGER", "--json"]) == 0
        records = json.loads(capsys.readouterr().out)
        assert records[-1]["role"] == "total" and records[-1]["reworks"] == 1

    def test_cli_refuses_an_unknown_report_and_a_second_item(self, make_host: Callable[..., AppWiring],
                                                              capsys: pytest.CaptureFixture) -> None:
        """Fails with one error line for a name that is no report or item, and for two different items."""
        cli = SdlcCliController(lambda: make_host("alpha"))
        assert cli.run(["stats", "bogus"]) == EXIT_ERROR
        assert "unknown report 'bogus'" in capsys.readouterr().err
        assert cli.run(["stats", "ITM-0001", "--item", "ITM-0002"]) == EXIT_ERROR
        assert "give the item once" in capsys.readouterr().err

    @staticmethod
    def _records(table: Any) -> List[Dict[str, Any]]:
        """Returns the table rows as dicts keyed by column."""
        return [dict(zip(table.columns, row)) for row in table.rows]
