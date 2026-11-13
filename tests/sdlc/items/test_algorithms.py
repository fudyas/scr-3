import json
from typing import List

import pytest

from sdlc.algorithms.chain_membership import ChainMembershipHelper
from sdlc.algorithms.chain_status import ChainStatusHelper
from sdlc.algorithms.dependency_graph import DependencyGraphHelper
from sdlc.algorithms.desc_slug import DescSlugHelper
from sdlc.algorithms.item_ids import ItemIdHelper
from sdlc.algorithms.launch_tag import LaunchTagParser
from sdlc.algorithms.queue_rank import QueueRankHelper
from sdlc.algorithms.record_amendment import RecordAmendmentHelper
from sdlc.algorithms.record_history import RecordHistoryHelper
from sdlc.algorithms.status_rules import StatusRulesHelper
from sdlc.algorithms.timestamps import TimestampHelper
from sdlc.algorithms.unique_values import UniqueValuesHelper
from sdlc.models.chain import Chain, ChainStatus
from sdlc.models.errors import (AmendmentRefusedError, ChainMembershipError, InvalidDescError, InvalidItemIdError,
                                InvalidTransitionError)
from sdlc.models.item import Item, ItemKind, ItemStatus, TaskStatus
from sdlc.models.record import HistoryEntry, RecordAmendment
from scr_tools.algorithms.text_table import TextTableHelper

# An item.json text in the format that predates the `previous` history field
LEGACY_ITEM_JSON = """{
  "prefix": "ITM",
  "number": 7,
  "desc": "INDEXING-SERVICE",
  "description": "Old description.",
  "tags": [
    "search"
  ],
  "history": [
    {
      "at": "2026-10-01T09:00:00.000Z",
      "host": "host-a",
      "event": "mint",
      "detail": ""
    },
    {
      "at": "2026-10-02T09:00:00.000Z",
      "host": "host-a",
      "event": "tags",
      "detail": "search"
    }
  ],
  "created_at": "2026-10-01T09:00:00.000Z",
  "updated_at": "2026-10-02T09:00:00.000Z",
  "kind": "task",
  "idea": "Old idea.",
  "status": "BACKLOG",
  "depends_on": [],
  "host": null,
  "queue_rank": null,
  "plan": {
    "revision": 0,
    "approved_revision": null,
    "approved_at": null
  },
  "tasks": {}
}
"""


class ModelFactoryHelper:
    """Builds item and chain records for algorithm tests without a ledger."""

    @staticmethod
    def item() -> Item:
        """Returns a BACKLOG item with a short history."""
        return Item.model_validate_json(LEGACY_ITEM_JSON)

    @staticmethod
    def chain() -> Chain:
        """Returns a chain with one member and no history."""
        return Chain(prefix="CHN", number=3, desc="SEARCH-STACK", description="Old chain text.", items=["ITM-0007"],
                     created_at="2026-10-01T09:00:00.000Z", updated_at="2026-10-01T09:00:00.000Z")


class TestItemIdHelper:
    """Covers item, block, and task id parsing."""

    def test_parses_short_and_full_ids(self) -> None:
        """Parses the number from short and full ids in any case."""
        assert ItemIdHelper.parse_item_number("ITM-0012", "ITM") == 12
        assert ItemIdHelper.parse_item_number("itm-0012-graph-claim", "ITM") == 12
        assert ItemIdHelper.normalize_item("ITM-12345-X-Y", "ITM") == "ITM-12345"

    def test_rejects_foreign_ids(self) -> None:
        """Rejects ids with another prefix or too few digits."""
        with pytest.raises(InvalidItemIdError):
            ItemIdHelper.parse_item_number("BLG-0001", "ITM")
        with pytest.raises(InvalidItemIdError):
            ItemIdHelper.parse_item_number("ITM-12", "ITM")

    def test_recognizes_block_and_task_ids(self) -> None:
        """Recognizes block and task ids."""
        assert ItemIdHelper.is_block_id("BLK-0001")
        assert ItemIdHelper.is_task_id("TSK-0010")
        assert not ItemIdHelper.is_block_id("integration")


class TestDescSlugHelper:
    """Covers DESC slug normalization and validation."""

    def test_normalizes_free_text(self) -> None:
        """Turns free text into an uppercase hyphen slug."""
        assert DescSlugHelper.normalize(" graph claim_amend ") == "GRAPH-CLAIM-AMEND"

    def test_accepts_notation_slug(self) -> None:
        """Accepts a slug of two to eight words."""
        assert DescSlugHelper.validate("GRAPH-CLAIM-AMEND") == "GRAPH-CLAIM-AMEND"

    @pytest.mark.parametrize("desc", ["graph-claim", "GRAPH", "A-B-C-D-E-F-G-H-I", "GRAPH--CLAIM", "GRAPH_CLAIM"])
    def test_rejects_bad_slugs(self, desc: str) -> None:
        """Rejects lowercase, one-word, too-long, and malformed slugs."""
        with pytest.raises(InvalidDescError):
            DescSlugHelper.validate(desc)


class TestStatusRulesHelper:
    """Covers the item and task lifecycles."""

    def test_allows_lifecycle_path(self) -> None:
        """Allows the planned path from BACKLOG to DONE."""
        path = [ItemStatus.BACKLOG, ItemStatus.PLANNED, ItemStatus.SCHEDULED, ItemStatus.IN_PROGRESS,
                ItemStatus.TESTING, ItemStatus.REVIEW, ItemStatus.DONE]
        for current, target in zip(path, path[1:]):
            StatusRulesHelper.check_item(current, target)

    def test_review_loops_back_and_only_review_reaches_done(self) -> None:
        """Sends a reviewed item back to the build or to QA, and refuses DONE straight from TESTING."""
        StatusRulesHelper.check_item(ItemStatus.REVIEW, ItemStatus.IN_PROGRESS)
        StatusRulesHelper.check_item(ItemStatus.REVIEW, ItemStatus.TESTING)
        with pytest.raises(InvalidTransitionError):
            StatusRulesHelper.check_item(ItemStatus.TESTING, ItemStatus.DONE)

    def test_refuses_skipping_and_leaving_terminal(self) -> None:
        """Refuses skipped stages and moves out of terminal statuses."""
        with pytest.raises(InvalidTransitionError):
            StatusRulesHelper.check_item(ItemStatus.BACKLOG, ItemStatus.IN_PROGRESS)
        with pytest.raises(InvalidTransitionError):
            StatusRulesHelper.check_item(ItemStatus.DONE, ItemStatus.BACKLOG)
        with pytest.raises(InvalidTransitionError):
            StatusRulesHelper.check_item(ItemStatus.IN_PROGRESS, ItemStatus.OBSOLETE)

    def test_task_rework_and_idempotence(self) -> None:
        """Allows rework from VALIDATED and a no-op move; refuses leaving DONE."""
        StatusRulesHelper.check_task(TaskStatus.VALIDATED, TaskStatus.IN_PROGRESS)
        StatusRulesHelper.check_task(TaskStatus.IN_PROGRESS, TaskStatus.IN_PROGRESS)
        with pytest.raises(InvalidTransitionError):
            StatusRulesHelper.check_task(TaskStatus.DONE, TaskStatus.IN_PROGRESS)
        with pytest.raises(InvalidTransitionError):
            StatusRulesHelper.check_task(TaskStatus.TODO, TaskStatus.DONE)

    def test_task_becomes_validated_only_during_validation(self) -> None:
        """Allows VALIDATED in IN PROGRESS and TESTING, refuses it in REVIEW, and ignores other targets."""
        StatusRulesHelper.check_task_in_item(ItemStatus.IN_PROGRESS, TaskStatus.VALIDATED)
        StatusRulesHelper.check_task_in_item(ItemStatus.TESTING, TaskStatus.VALIDATED)
        with pytest.raises(InvalidTransitionError, match="IN PROGRESS or TESTING"):
            StatusRulesHelper.check_task_in_item(ItemStatus.REVIEW, TaskStatus.VALIDATED)
        for target in (TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.DONE):
            StatusRulesHelper.check_task_in_item(ItemStatus.REVIEW, target)

    def test_review_needs_every_task_validated_or_done(self) -> None:
        """Refuses REVIEW and lists the sorted tasks that are not VALIDATED or DONE."""
        StatusRulesHelper.check_item_tasks(
            ItemStatus.REVIEW, {"TSK-0001": TaskStatus.VALIDATED, "TSK-0002": TaskStatus.DONE})
        with pytest.raises(InvalidTransitionError, match="tasks are not VALIDATED: TSK-0002, TSK-0003"):
            StatusRulesHelper.check_item_tasks(ItemStatus.REVIEW, {
                "TSK-0003": TaskStatus.TODO, "TSK-0001": TaskStatus.VALIDATED, "TSK-0002": TaskStatus.IN_PROGRESS})

    def test_done_needs_every_task_done(self) -> None:
        """Refuses DONE and lists the sorted tasks that are not DONE."""
        StatusRulesHelper.check_item_tasks(ItemStatus.DONE, {"TSK-0001": TaskStatus.DONE})
        with pytest.raises(InvalidTransitionError, match="tasks are not DONE: TSK-0001, TSK-0002"):
            StatusRulesHelper.check_item_tasks(
                ItemStatus.DONE, {"TSK-0002": TaskStatus.IN_PROGRESS, "TSK-0001": TaskStatus.VALIDATED})

    def test_other_item_targets_ignore_task_statuses(self) -> None:
        """Passes every other item target whatever the task statuses are."""
        statuses = {"TSK-0001": TaskStatus.TODO, "TSK-0002": TaskStatus.IN_PROGRESS}
        for target in (ItemStatus.PLANNED, ItemStatus.SCHEDULED, ItemStatus.IN_PROGRESS, ItemStatus.TESTING,
                       ItemStatus.OBSOLETE):
            StatusRulesHelper.check_item_tasks(target, statuses)


class TestDependencyGraphHelper:
    """Covers cycle detection and readiness."""

    def test_finds_cycle(self) -> None:
        """Finds a three-node cycle."""
        cycle = DependencyGraphHelper.find_cycle({"A": ["B"], "B": ["C"], "C": ["A"]})
        assert cycle is not None and cycle[0] == cycle[-1] and set(cycle) == {"A", "B", "C"}

    def test_accepts_dag(self) -> None:
        """Accepts a diamond-shaped graph."""
        assert DependencyGraphHelper.find_cycle({"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}) is None

    def test_reports_unmet(self) -> None:
        """Reports dependencies that are unknown or not DONE."""
        statuses = {"A": ItemStatus.DONE, "B": ItemStatus.TESTING}
        assert DependencyGraphHelper.unmet_dependencies(["A", "B", "C"], statuses) == ["B", "C"]


class TestQueueRankHelper:
    """Covers queue ranks."""

    def test_rank_last_and_before(self) -> None:
        """Places items last and between neighbors."""
        assert QueueRankHelper.rank_last([]) == 1.0
        assert QueueRankHelper.rank_last([1.0, 3.0]) == 4.0
        assert QueueRankHelper.rank_before([1.0, 2.0, 3.0], 2.0) == 1.5
        assert QueueRankHelper.rank_before([2.0], 2.0) == 1.5


class TestLaunchTagParser:
    """Covers subagent launch description parsing."""

    def test_parses_task_scope(self) -> None:
        """Parses item, task, role, and summary."""
        tag = LaunchTagParser.parse("ITM-0003 TSK-0002 swe: add ledger", "ITM")
        assert (tag.item, tag.task, tag.block, tag.role, tag.summary) == ("ITM-0003", "TSK-0002", None, "swe",
                                                                          "add ledger")

    def test_parses_block_scope_and_full_id(self) -> None:
        """Parses a full item id with a block scope."""
        tag = LaunchTagParser.parse("ITM-0003-LEDGER-CORE BLK-0001 validator: gates", "ITM")
        assert (tag.item, tag.block, tag.role) == ("ITM-0003", "BLK-0001", "validator")

    def test_parses_item_scope(self) -> None:
        """Parses an item-scoped launch without block or task."""
        tag = LaunchTagParser.parse("ITM-0003 planner: draft plan", "ITM")
        assert (tag.item, tag.task, tag.role) == ("ITM-0003", None, "planner")

    def test_leaves_untagged_description(self) -> None:
        """Keeps an untagged description as the summary."""
        tag = LaunchTagParser.parse("Explore the repo", "ITM")
        assert tag.item is None and tag.summary == "Explore the repo"


class TestTextTableHelper:
    """Covers plain-text table rendering."""

    def test_aligns_columns(self) -> None:
        """Pads columns and renders empty cells as dashes."""
        text = TextTableHelper.render(["id", "value"], [["a", None], ["long-id", 2.0]])
        assert text.splitlines() == ["#  ID       VALUE", "1  a        -", "2  long-id  2"]


class TestTimestampHelper:
    """Covers timestamp normalization."""

    def test_normalizes_offsets(self) -> None:
        """Normalizes `Z` and offset forms to one sortable form."""
        assert TimestampHelper.normalize("2026-10-04T09:49:12.345Z") == "2026-10-04T09:49:12.345Z"
        assert TimestampHelper.normalize("2026-10-04T11:49:12+02:00") == "2026-10-04T09:49:12.000Z"
        assert TimestampHelper.seconds_between("2026-10-04T09:49:12.000Z", "2026-10-04T09:50:12.500Z") == 60.5


class TestChainStatusHelper:
    """Covers the chain status rollup and member counts."""

    @pytest.mark.parametrize("statuses, expected", [
        ([], ChainStatus.BACKLOG),
        ([ItemStatus.BACKLOG, ItemStatus.PLANNED, ItemStatus.SCHEDULED], ChainStatus.BACKLOG),
        ([ItemStatus.BACKLOG, ItemStatus.IN_PROGRESS], ChainStatus.IN_PROGRESS),
        ([ItemStatus.TESTING], ChainStatus.IN_PROGRESS),
        ([ItemStatus.REVIEW], ChainStatus.IN_PROGRESS),
        ([ItemStatus.DONE, ItemStatus.BACKLOG], ChainStatus.IN_PROGRESS),
        ([ItemStatus.DONE, ItemStatus.OBSOLETE], ChainStatus.DONE),
        ([ItemStatus.OBSOLETE], ChainStatus.DONE),
        ([ItemStatus.OBSOLETE, ItemStatus.PLANNED], ChainStatus.BACKLOG),
    ])
    def test_rolls_up_member_statuses(self, statuses: List[ItemStatus], expected: ChainStatus) -> None:
        """Drops obsolete members, then reports DONE, BACKLOG, or IN PROGRESS."""
        assert ChainStatusHelper.rollup(statuses) == expected

    def test_counts_in_lifecycle_order(self) -> None:
        """Counts members per status in lifecycle order and omits empty statuses."""
        counts = ChainStatusHelper.counts([ItemStatus.DONE, ItemStatus.BACKLOG, ItemStatus.DONE])
        assert list(counts.items()) == [(ItemStatus.BACKLOG, 1), (ItemStatus.DONE, 2)]


class TestChainMembershipHelper:
    """Covers the chain member list checks."""

    def test_accepts_known_unique_free_members(self) -> None:
        """Accepts known items that no other chain holds, including the chain's own current members."""
        ChainMembershipHelper.validate("CHN-0001", ["ITM-0002", "ITM-0001"], {"CHN-0001": ["ITM-0001"]},
                                       {"ITM-0001", "ITM-0002"})

    def test_reports_every_problem(self) -> None:
        """Reports repeated, unknown, and taken members in one error."""
        with pytest.raises(ChainMembershipError) as error:
            ChainMembershipHelper.validate("CHN-0002", ["ITM-0001", "ITM-0001", "ITM-0009"],
                                           {"CHN-0001": ["ITM-0001"]}, {"ITM-0001"})
        message = str(error.value)
        assert "more than once: ITM-0001" in message and "unknown items: ITM-0009" in message
        assert "already in CHN-0001: ITM-0001" in message


class TestUniqueValuesHelper:
    """Covers label list cleanup."""

    def test_keeps_first_seen_order(self) -> None:
        """Drops empty and repeated values and keeps first-seen order."""
        assert UniqueValuesHelper.ordered(["b", "", "a", "b"]) == ["b", "a"]


class TestRecordHistoryHelper:
    """Covers the history entry that a record change appends."""

    def test_touch_stores_no_previous_values_by_default(self) -> None:
        """Appends an entry with an empty previous map when the caller gives none."""
        touched = RecordHistoryHelper.touch(ModelFactoryHelper.item(), {"desc": "OTHER-SLUG"}, "host-b", "x", "d")
        assert touched.desc == "OTHER-SLUG"
        assert touched.history[-1] == HistoryEntry(at=touched.updated_at, host="host-b", event="x", detail="d")
        assert touched.history[-1].previous == {}

    def test_touch_stores_the_given_previous_values(self) -> None:
        """Appends an entry that carries the old values the caller gives."""
        touched = RecordHistoryHelper.touch(ModelFactoryHelper.item(), {}, "host-b", "x", "d",
                                            previous={"idea": "Old idea."})
        assert touched.history[-1].previous == {"idea": "Old idea."}
        assert len(touched.history) == 3


class TestRecordAmendmentHelper:
    """Covers the amend rules and the amended record."""

    @pytest.mark.parametrize("status", [ItemStatus.BACKLOG, ItemStatus.PLANNED])
    def test_item_status_passes_before_scheduling(self, status: ItemStatus) -> None:
        """Passes BACKLOG and PLANNED items."""
        RecordAmendmentHelper.check_item_status("ITM-0007", status)

    @pytest.mark.parametrize("status, hint", [
        (ItemStatus.SCHEDULED, "run `items unschedule ITM-0007` first"),
        (ItemStatus.IN_PROGRESS, "the run has started, so record changes in the review"),
        (ItemStatus.TESTING, "the run has started, so record changes in the review"),
        (ItemStatus.REVIEW, "the run has started, so record changes in the review"),
        (ItemStatus.DONE, "the item is closed"),
        (ItemStatus.OBSOLETE, "the item is closed"),
    ])
    def test_item_status_refuses_the_other_statuses(self, status: ItemStatus, hint: str) -> None:
        """Refuses every other status and names the status and its hint."""
        with pytest.raises(AmendmentRefusedError) as raised:
            RecordAmendmentHelper.check_item_status("ITM-0007", status)
        assert str(raised.value) == (
            f"ITM-0007 is {status.value}; only BACKLOG and PLANNED items can be amended; {hint}"
        )

    @pytest.mark.parametrize("status", [ChainStatus.BACKLOG, ChainStatus.IN_PROGRESS])
    def test_chain_status_passes_until_done(self, status: ChainStatus) -> None:
        """Passes a chain that is not DONE."""
        RecordAmendmentHelper.check_chain_status("CHN-0003", status)

    def test_chain_status_refuses_done(self) -> None:
        """Refuses a DONE chain."""
        with pytest.raises(AmendmentRefusedError, match="CHN-0003 is DONE; a DONE chain cannot be amended"):
            RecordAmendmentHelper.check_chain_status("CHN-0003", ChainStatus.DONE)

    def test_apply_replaces_and_strips_the_text(self) -> None:
        """Replaces idea, description, and desc, keeps the short id, and changes the full id."""
        item = ModelFactoryHelper.item()
        amendment = RecordAmendment(desc=" EMBEDDING-SERVICE ", idea=" New idea.\n", description="\nNew text. ")
        amended = RecordAmendmentHelper.apply(item, amendment, "host-b")
        assert (amended.idea, amended.description, amended.desc) == ("New idea.", "New text.", "EMBEDDING-SERVICE")
        assert amended.short_id == "ITM-0007"
        assert amended.full_id == "ITM-0007-EMBEDDING-SERVICE"
        assert amended.tags == item.tags
        assert item.idea == "Old idea."

    def test_apply_appends_one_entry_with_the_old_values(self) -> None:
        """Appends one amended entry whose previous map holds only the changed fields."""
        item = ModelFactoryHelper.item()
        amendment = RecordAmendment(desc="EMBEDDING-SERVICE", idea="Old idea.", description="New text.")
        amended = RecordAmendmentHelper.apply(item, amendment, "host-b")
        assert amended.history[:-1] == item.history
        entry = amended.history[-1]
        assert (entry.event, entry.host) == ("amended", "host-b")
        assert entry.detail == "desc INDEXING-SERVICE -> EMBEDDING-SERVICE, description"
        assert entry.previous == {"desc": "INDEXING-SERVICE", "description": "Old description."}

    def test_apply_lists_every_changed_field_in_order(self) -> None:
        """Reports the changed fields in the order desc, idea, description."""
        amendment = RecordAmendment(description="New text.", idea="New idea.", desc="EMBEDDING-SERVICE")
        amended = RecordAmendmentHelper.apply(ModelFactoryHelper.item(), amendment, "host-b")
        assert amended.history[-1].detail == "desc INDEXING-SERVICE -> EMBEDDING-SERVICE, idea, description"

    def test_apply_amends_a_chain(self) -> None:
        """Replaces the description and desc of a chain and keeps its members."""
        chain = ModelFactoryHelper.chain()
        amended = RecordAmendmentHelper.apply(chain, RecordAmendment(desc="VECTOR-STACK", description="New."), "host-b")
        assert (amended.full_id, amended.description, amended.items) == ("CHN-0003-VECTOR-STACK", "New.", ["ITM-0007"])
        assert amended.history[-1].previous == {"desc": "SEARCH-STACK", "description": "Old chain text."}

    @pytest.mark.parametrize("amendment, message", [
        (RecordAmendment(idea="   "), "idea must not be empty"),
        (RecordAmendment(description=""), "description must not be empty"),
        (RecordAmendment(desc=" "), "desc must not be empty"),
        (RecordAmendment(), "the amendment changes no field"),
        (RecordAmendment(desc="INDEXING-SERVICE", idea=" Old idea. "), "the amendment changes no field"),
    ])
    def test_apply_refuses_empty_and_unchanged_text(self, amendment: RecordAmendment, message: str) -> None:
        """Refuses empty text, an amendment with no fields, and an amendment equal to the current values."""
        with pytest.raises(AmendmentRefusedError, match=message):
            RecordAmendmentHelper.apply(ModelFactoryHelper.item(), amendment, "host-b")

    def test_apply_refuses_a_bad_slug(self) -> None:
        """Refuses a slug that breaks the notation rules."""
        with pytest.raises(InvalidDescError):
            RecordAmendmentHelper.apply(ModelFactoryHelper.item(), RecordAmendment(desc="lower-case"), "host-b")

    def test_apply_refuses_idea_on_a_chain(self) -> None:
        """Refuses a field that the record type lacks."""
        with pytest.raises(AmendmentRefusedError, match="CHN-0003 has no idea field"):
            RecordAmendmentHelper.apply(ModelFactoryHelper.chain(), RecordAmendment(idea="x"), "host-b")


class TestHistoryEntrySerialization:
    """Covers the stable JSON form of history entries."""

    def test_legacy_item_text_round_trips_byte_identically(self) -> None:
        """Writes an old-format item.json back unchanged."""
        item = Item.model_validate_json(LEGACY_ITEM_JSON)
        assert item.model_dump_json(indent=2) + "\n" == LEGACY_ITEM_JSON
        assert item.history[0].previous == {}

    def test_only_the_amended_entry_carries_previous(self) -> None:
        """Adds the previous key to the amended entry and leaves the earlier entries as they were."""
        amended = RecordAmendmentHelper.apply(ModelFactoryHelper.item(), RecordAmendment(idea="New idea."), "host-b")
        written = json.loads(amended.model_dump_json(indent=2))
        legacy = json.loads(LEGACY_ITEM_JSON)
        assert written["history"][:-1] == legacy["history"]
        assert all("previous" not in entry for entry in written["history"][:-1])
        assert written["history"][-1]["previous"] == {"idea": "Old idea."}
