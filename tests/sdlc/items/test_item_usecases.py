from typing import Callable, Tuple

import pytest

from sdlc.models.errors import (
    AmendmentRefusedError, DependencyError, InvalidDescError, InvalidTransitionError, ItemClaimError,
)
from sdlc.models.item import ItemKind, ItemStatus, TaskStatus
from sdlc.models.record import RecordAmendment
from sdlc.wiring import AppWiring


class ItemFlowHelper:
    """Drives items through the pipeline for tests."""

    @staticmethod
    def mint(wiring: AppWiring, desc: str = "LEDGER-CORE-TOOLS", depends_on: Tuple[str, ...] = ()) -> str:
        """Mints an item and returns its short id."""
        item = wiring.item_usecases.mint(ItemKind.TASK, desc, "raw idea", "Normalized idea.", ["sdlc"],
                                         list(depends_on))
        return item.short_id

    @staticmethod
    def plan_and_schedule(wiring: AppWiring, item_id: str, plan_text: str) -> None:
        """Writes the plan draft, approves it, and schedules the item."""
        draft = wiring.plan_usecases.edit(item_id)
        draft.write_text(plan_text)
        wiring.plan_usecases.approve(item_id)
        wiring.schedule_usecases.schedule(item_id, None)


class TestItemUsecases:
    """Covers minting, metadata, dependencies, and lifecycle guards on a real ledger."""

    def test_mints_unique_numbers_across_hosts(self, make_host: Callable[[str], AppWiring]) -> None:
        """Gives two hosts consecutive numbers and never reuses them."""
        alpha, beta = make_host("alpha"), make_host("beta")
        first = ItemFlowHelper.mint(alpha)
        second = ItemFlowHelper.mint(beta, "GRAPH-CLAIM-AMEND")
        third = ItemFlowHelper.mint(alpha, "RETRIEVAL-FALLBACK-FIX")
        assert (first, second, third) == ("ITM-0001", "ITM-0002", "ITM-0003")
        item = alpha.item_usecases.get(second)
        assert item.full_id == "ITM-0002-GRAPH-CLAIM-AMEND" and item.status == ItemStatus.BACKLOG
        assert item.history[0].host == "beta"

    def test_rejects_bad_desc_and_unknown_dependency(self, make_host: Callable[[str], AppWiring]) -> None:
        """Refuses a malformed slug and a dependency on a missing item."""
        host = make_host("alpha")
        with pytest.raises(InvalidDescError):
            ItemFlowHelper.mint(host, "lowercase-slug")
        with pytest.raises(DependencyError):
            ItemFlowHelper.mint(host, depends_on=("ITM-0042",))

    def test_dependency_cycle_and_obsolete_guard(self, make_host: Callable[[str], AppWiring]) -> None:
        """Refuses a cycle and obsoleting an item an active item depends on."""
        host = make_host("alpha")
        first = ItemFlowHelper.mint(host)
        second = ItemFlowHelper.mint(host, "GRAPH-CLAIM-AMEND", depends_on=(first,))
        with pytest.raises(DependencyError, match="cycle"):
            host.item_usecases.set_dependencies(first, [second])
        with pytest.raises(DependencyError, match="depend on"):
            host.item_usecases.set_status(first, ItemStatus.OBSOLETE, False)
        assert not host.item_usecases.check_dependencies(second).ready
        host.item_usecases.set_dependencies(second, [])
        assert host.item_usecases.set_status(first, ItemStatus.OBSOLETE, False).status == ItemStatus.OBSOLETE

    def test_tags_are_unique_and_removable(self, make_host: Callable[[str], AppWiring]) -> None:
        """Adds tags once and removes them."""
        host = make_host("alpha")
        item_id = ItemFlowHelper.mint(host)
        host.item_usecases.change_tags(item_id, ["graph", "sdlc"], [])
        assert host.item_usecases.change_tags(item_id, [], ["sdlc"]).tags == ["graph"]

    def test_run_claims_item_and_guards_done(self, make_host: Callable[[str], AppWiring], plan_text: str) -> None:
        """Claims the item for one host, blocks the other, and requires DONE tasks before DONE."""
        alpha, beta = make_host("alpha"), make_host("beta")
        item_id = ItemFlowHelper.mint(alpha)
        ItemFlowHelper.plan_and_schedule(alpha, item_id, plan_text)
        assert alpha.item_usecases.set_status(item_id, ItemStatus.IN_PROGRESS, False).host == "alpha"
        for status in (TaskStatus.IN_PROGRESS, TaskStatus.VALIDATED):
            alpha.plan_usecases.set_task_status(item_id, status, ["all"])
        with pytest.raises(ItemClaimError):
            beta.item_usecases.set_status(item_id, ItemStatus.TESTING, False)
        alpha.item_usecases.set_status(item_id, ItemStatus.TESTING, False)
        with pytest.raises(InvalidTransitionError, match="cannot move TESTING -> DONE"):
            alpha.item_usecases.set_status(item_id, ItemStatus.DONE, False)
        with pytest.raises(ItemClaimError):
            beta.item_usecases.set_status(item_id, ItemStatus.REVIEW, False)
        alpha.item_usecases.set_status(item_id, ItemStatus.REVIEW, False)
        with pytest.raises(InvalidTransitionError, match="not DONE"):
            alpha.item_usecases.set_status(item_id, ItemStatus.DONE, False)
        alpha.plan_usecases.set_task_status(item_id, TaskStatus.DONE, ["all"])
        done = alpha.item_usecases.set_status(item_id, ItemStatus.DONE, False)
        assert done.status == ItemStatus.DONE and done.queue_rank is None

    def test_run_refuses_unmet_dependencies(self, make_host: Callable[[str], AppWiring], plan_text: str) -> None:
        """Refuses to start an item whose dependency is not DONE."""
        host = make_host("alpha")
        first = ItemFlowHelper.mint(host)
        second = ItemFlowHelper.mint(host, "GRAPH-CLAIM-AMEND", depends_on=(first,))
        ItemFlowHelper.plan_and_schedule(host, second, plan_text)
        with pytest.raises(DependencyError, match="blocked"):
            host.item_usecases.set_status(second, ItemStatus.IN_PROGRESS, False)

    def test_planned_and_scheduled_need_their_commands(self, make_host: Callable[[str], AppWiring]) -> None:
        """Refuses direct moves that bypass plan approval and scheduling."""
        host = make_host("alpha")
        item_id = ItemFlowHelper.mint(host)
        with pytest.raises(InvalidTransitionError, match="plan approve"):
            host.item_usecases.set_status(item_id, ItemStatus.PLANNED, False)

    def test_amend_replaces_text_and_keeps_old_values(self, make_host: Callable[[str], AppWiring]) -> None:
        """Replaces idea, description, and DESC on a BACKLOG item and records the old values."""
        host = make_host("alpha")
        item_id = ItemFlowHelper.mint(host)
        amendment = RecordAmendment(desc="LEDGER-CORE-REWORK", idea="new idea", description="New description.")
        amended = host.item_usecases.amend(item_id, amendment)
        stored = host.item_usecases.get(item_id)
        assert stored == amended
        assert stored.full_id == "ITM-0001-LEDGER-CORE-REWORK"
        assert stored.idea == "new idea" and stored.description == "New description."
        assert stored.status == ItemStatus.BACKLOG
        last = stored.history[-1]
        assert last.event == "amended" and last.host == "alpha"
        assert last.previous == {
            "desc": "LEDGER-CORE-TOOLS", "idea": "raw idea", "description": "Normalized idea.",
        }

    def test_amend_keeps_the_short_id_identity(self, make_host: Callable[[str], AppWiring]) -> None:
        """Resolves the old full id and keeps dependents on the amended item intact."""
        host = make_host("alpha")
        first = ItemFlowHelper.mint(host)
        second = ItemFlowHelper.mint(host, "GRAPH-CLAIM-AMEND", depends_on=(first,))
        host.item_usecases.amend(first, RecordAmendment(desc="LEDGER-CORE-REWORK"))
        assert host.item_usecases.get("ITM-0001-LEDGER-CORE-TOOLS").full_id == "ITM-0001-LEDGER-CORE-REWORK"
        report = host.item_usecases.check_dependencies(second)
        assert not report.ready and report.unmet == ["ITM-0001 (BACKLOG)"]

    def test_amend_leaves_plan_and_approval_of_a_planned_item(self, make_host: Callable[[str], AppWiring],
                                                              plan_text: str) -> None:
        """Keeps PLANNED status, plan revision, approval, and plan text through an amendment."""
        host = make_host("alpha")
        item_id = ItemFlowHelper.mint(host)
        host.plan_usecases.edit(item_id).write_text(plan_text)
        planned = host.plan_usecases.approve(item_id)
        assert planned.status == ItemStatus.PLANNED
        amended = host.item_usecases.amend(item_id, RecordAmendment(idea="sharper idea"))
        assert amended.status == ItemStatus.PLANNED
        assert amended.plan == planned.plan and amended.plan.is_approved
        assert amended.tasks == planned.tasks
        assert host.plan_usecases.show(item_id, False) == plan_text

    def test_amend_refuses_a_scheduled_item(self, make_host: Callable[[str], AppWiring], plan_text: str) -> None:
        """Refuses a SCHEDULED item and leaves the stored item unchanged."""
        host = make_host("alpha")
        item_id = ItemFlowHelper.mint(host)
        ItemFlowHelper.plan_and_schedule(host, item_id, plan_text)
        before = host.item_usecases.get(item_id)
        with pytest.raises(AmendmentRefusedError, match="SCHEDULED"):
            host.item_usecases.amend(item_id, RecordAmendment(idea="too late"))
        assert host.item_usecases.get(item_id) == before
