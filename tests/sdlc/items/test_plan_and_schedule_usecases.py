from typing import Callable

import pytest

from sdlc.models.errors import InvalidTransitionError, PlanValidationError, SdlcError
from sdlc.models.item import ItemKind, ItemStatus, TaskStatus
from sdlc.wiring import AppWiring


class PlanFlowHelper:
    """Mints items for plan and schedule tests."""

    @staticmethod
    def mint(wiring: AppWiring, desc: str) -> str:
        """Mints an item and returns its short id."""
        return wiring.item_usecases.mint(ItemKind.FIX, desc, "idea", "Description.", [], []).short_id

    @staticmethod
    def approve(wiring: AppWiring, item_id: str, plan_text: str) -> None:
        """Writes the draft and approves it."""
        wiring.plan_usecases.edit(item_id).write_text(plan_text)
        wiring.plan_usecases.approve(item_id)


class TestPlanUsecases:
    """Covers drafts, commits, approval, handoffs, and task moves."""

    def test_draft_starts_from_template(self, make_host: Callable[[str], AppWiring]) -> None:
        """Seeds a draft from the template with the item id and refuses it until filled."""
        host = make_host("alpha")
        item_id = PlanFlowHelper.mint(host, "LEDGER-CORE-TOOLS")
        draft = host.plan_usecases.edit(item_id)
        assert draft.read_text().startswith("# ITM-0001-LEDGER-CORE-TOOLS — Plan")
        with pytest.raises(PlanValidationError, match="placeholders"):
            host.plan_usecases.check(item_id)

    def test_approve_commits_draft_and_builds_tasks(self, make_host: Callable[[str], AppWiring],
                                                    plan_text: str) -> None:
        """Commits the draft, records approval, and creates TODO task records."""
        host = make_host("alpha")
        item_id = PlanFlowHelper.mint(host, "LEDGER-CORE-TOOLS")
        PlanFlowHelper.approve(host, item_id, plan_text)
        item = host.item_usecases.get(item_id)
        assert item.status == ItemStatus.PLANNED and item.plan.is_approved and item.plan.revision == 1
        assert {task_id: task.block for task_id, task in item.tasks.items()} == {
            "TSK-0001": "BLK-0001", "TSK-0002": "BLK-0001", "TSK-0003": "BLK-0002"}
        assert host.plan_usecases.show(item_id, draft=False) == plan_text
        assert host.plan_usecases.edit(item_id).read_text() == plan_text

    def test_replan_drops_approval(self, make_host: Callable[[str], AppWiring], plan_text: str) -> None:
        """Sends a PLANNED item back to BACKLOG when a new revision lands."""
        host = make_host("alpha")
        item_id = PlanFlowHelper.mint(host, "LEDGER-CORE-TOOLS")
        PlanFlowHelper.approve(host, item_id, plan_text)
        host.plan_usecases.edit(item_id).write_text(plan_text.replace("Build the ledger core.", "Build it."))
        item = host.plan_usecases.commit(item_id)
        assert item.status == ItemStatus.BACKLOG and item.plan.revision == 2 and not item.plan.is_approved

    def test_task_handoff_and_rework(self, make_host: Callable[[str], AppWiring], plan_text: str) -> None:
        """Hands off one task and records a QA rework on a running item."""
        host = make_host("alpha")
        item_id = PlanFlowHelper.mint(host, "LEDGER-CORE-TOOLS")
        PlanFlowHelper.approve(host, item_id, plan_text)
        assert "ADD LEDGER SOURCE" in host.plan_usecases.task_handoff(item_id, "TSK-0001")
        with pytest.raises(InvalidTransitionError, match="only while it runs"):
            host.plan_usecases.set_task_status(item_id, TaskStatus.IN_PROGRESS, ["TSK-0001"])
        host.schedule_usecases.schedule(item_id, None)
        host.item_usecases.set_status(item_id, ItemStatus.IN_PROGRESS, False)
        host.plan_usecases.set_task_status(item_id, TaskStatus.IN_PROGRESS, ["TSK-0001"])
        host.plan_usecases.set_task_status(item_id, TaskStatus.VALIDATED, ["TSK-0001"])
        item = host.plan_usecases.rework_task(item_id, "TSK-0001", "qa", "system test failed")
        assert item.tasks["TSK-0001"].status == TaskStatus.IN_PROGRESS
        with pytest.raises(SdlcError, match="no tasks"):
            host.plan_usecases.set_task_status(item_id, TaskStatus.IN_PROGRESS, ["TSK-0042"])
        with pytest.raises(SdlcError, match="rework stage"):
            host.plan_usecases.rework_task(item_id, "TSK-0001", "lunch", "")


class TestScheduleUsecases:
    """Covers queue order, readiness, and the next pick."""

    def test_orders_queue_and_picks_next_ready(self, make_host: Callable[[str], AppWiring], plan_text: str) -> None:
        """Places items by rank, honors `before`, and skips blocked items for `next`."""
        host = make_host("alpha")
        first = PlanFlowHelper.mint(host, "LEDGER-CORE-TOOLS")
        second = PlanFlowHelper.mint(host, "GRAPH-CLAIM-AMEND")
        third = PlanFlowHelper.mint(host, "RETRIEVAL-FALLBACK-FIX")
        for item_id in (first, second, third):
            PlanFlowHelper.approve(host, item_id, plan_text)
        host.schedule_usecases.schedule(first, None)
        host.schedule_usecases.schedule(second, None)
        host.schedule_usecases.schedule(third, second)
        assert [entry.item.short_id for entry in host.schedule_usecases.queue()] == [first, third, second]

        # Blocks the head of the queue on the second item so `next` skips it
        host.schedule_usecases.unschedule(first)
        host.item_usecases.set_dependencies(first, [second])
        host.schedule_usecases.schedule(first, third)
        assert host.schedule_usecases.next_ready().short_id == third

    def test_refuses_unapproved_plan(self, make_host: Callable[[str], AppWiring]) -> None:
        """Refuses to schedule an item without an approved plan."""
        host = make_host("alpha")
        item_id = PlanFlowHelper.mint(host, "LEDGER-CORE-TOOLS")
        with pytest.raises(InvalidTransitionError):
            host.schedule_usecases.schedule(item_id, None)
