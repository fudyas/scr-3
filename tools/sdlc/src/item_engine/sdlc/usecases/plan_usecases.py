from pathlib import Path
from typing import Dict, List

from sdlc.algorithms.item_ids import ItemIdHelper
from sdlc.algorithms.plan_parser import PlanParser
from sdlc.algorithms.record_history import RecordHistoryHelper
from sdlc.algorithms.review_parser import ReviewParser
from sdlc.algorithms.status_rules import StatusRulesHelper
from sdlc.algorithms.timestamps import TimestampHelper
from sdlc.datasources.draft_source import DraftSource
from sdlc.models.errors import InvalidTransitionError, SdlcError
from sdlc.models.item import Item, ItemStatus, TaskRecord, TaskStatus
from sdlc.models.plan import PlanDocument
from sdlc.repositories.item_repository import ItemRepository
from sdlc.repositories.telemetry_repository import TelemetryRepository

# Item statuses in which the plan may still change
PLANNABLE_STATUSES = (ItemStatus.BACKLOG, ItemStatus.PLANNED)

# Item statuses in which task statuses move
RUNNING_STATUSES = (ItemStatus.IN_PROGRESS, ItemStatus.TESTING, ItemStatus.REVIEW)

# Pipeline stages that send a task back to its engineer
REWORK_STAGES = ("validate", "integrate", "qa", "review", "promote")


class PlanUsecases:
    """Drafts, validates, commits, and approves item plans, and moves their tasks."""

    def __init__(self, items: ItemRepository, drafts: DraftSource, telemetry: TelemetryRepository,
                 template_path: Path, prefix: str, host: str) -> None:
        """Initializes the usecases.

        Args:
            items: the item repository.
            drafts: the local plan drafts.
            telemetry: the telemetry repository that records plan and task events.
            template_path: the plan template a new draft starts from.
            prefix: the item id prefix, such as `ITM`.
            host: this host's name, recorded in history.
        """
        self._items = items
        self._drafts = drafts
        self._telemetry = telemetry
        self._template_path = template_path
        self._prefix = prefix
        self._host = host

    def edit(self, item_id: str) -> Path:
        """Returns the draft path, creating the draft from the committed plan or the template.

        Raises:
            ItemNotFoundError: the item does not exist.
        """
        item = self._items.get(self._short_id(item_id))
        if self._drafts.read(item.short_id) is None:
            committed = self._items.read_plan(item.short_id)
            template = self._template_path.read_text(encoding="utf-8").replace("{{ITEM_ID}}", item.full_id)
            self._drafts.write(item.short_id, committed or template)
        return self._drafts.path(item.short_id)

    def check(self, item_id: str) -> PlanDocument:
        """Returns the parsed draft when it passes every plan rule.

        Raises:
            SdlcError: the item has no draft.
            PlanValidationError: the draft breaks one or more rules.
        """
        short_id = self._short_id(item_id)
        text = self._drafts.read(short_id)
        if text is None:
            raise SdlcError(f"{short_id} has no draft; run `lets sdlc items plan edit {short_id}` first")
        return PlanParser.validate(PlanParser.parse(text), text)

    def approve(self, item_id: str) -> Item:
        """Commits a pending draft, then records the user's approval and moves the item to PLANNED.

        Returns:
            The stored PLANNED item.

        Raises:
            InvalidTransitionError: the item has no committed plan or is past planning.
            PlanValidationError: the pending draft breaks the plan rules.
        """
        short_id = self._short_id(item_id)
        if self._drafts.read(short_id) is not None:
            self.commit(short_id)

        def change(item: Item, all_items: Dict[str, Item]) -> Item:
            """Returns the item with its current plan revision approved."""
            if item.status != ItemStatus.BACKLOG:
                raise InvalidTransitionError(f"{short_id} is {item.status.value}; only a BACKLOG plan is approved")
            if item.plan.revision == 0:
                raise InvalidTransitionError(f"{short_id} has no committed plan")
            plan = item.plan.model_copy(update={"approved_revision": item.plan.revision,
                                                "approved_at": TimestampHelper.now()})
            return RecordHistoryHelper.touch(item, {"plan": plan, "status": ItemStatus.PLANNED}, self._host,
                                           "plan_approved", f"revision {item.plan.revision}")

        approved = self._items.modify(short_id, change, "plan approved")
        self._telemetry.record_event("plan_approved", short_id, status_from=ItemStatus.BACKLOG.value,
                                     status_to=ItemStatus.PLANNED.value, value=approved.plan.revision)
        return approved

    def commit(self, item_id: str) -> Item:
        """Lands the validated draft on the ledger as a new plan revision and rebuilds the task records.

        A PLANNED item drops back to BACKLOG because the new revision lacks approval.

        Returns:
            The stored item.

        Raises:
            InvalidTransitionError: the item is past planning.
            PlanValidationError: the draft breaks the plan rules.
        """
        short_id = self._short_id(item_id)
        document = self.check(short_id)
        text = self._drafts.read(short_id) or ""
        tasks = {
            task.task_id: TaskRecord(block=block.block_id, title=task.title, depends_on=task.depends_on,
                                     model=task.model)
            for block in document.blocks for task in block.tasks
        }

        def change(item: Item, all_items: Dict[str, Item]) -> Item:
            """Returns the item with the new plan revision and fresh task records."""
            if item.status not in PLANNABLE_STATUSES:
                raise InvalidTransitionError(f"{short_id} is {item.status.value}; its plan is frozen")
            plan = item.plan.model_copy(update={"revision": item.plan.revision + 1})
            return RecordHistoryHelper.touch(
                item, {"plan": plan, "tasks": tasks, "status": ItemStatus.BACKLOG, "queue_rank": None},
                self._host, "plan_committed", f"revision {plan.revision}, {len(tasks)} tasks",
            )

        committed = self._items.modify(short_id, change, "plan committed", plan_text=text)
        self._drafts.discard(short_id)
        self._telemetry.record_event("plan_committed", short_id, value=committed.plan.revision,
                                     detail={"blocks": len(document.blocks), "tasks": len(tasks)})
        return committed

    def show(self, item_id: str, draft: bool) -> str:
        """Returns the committed plan or the local draft.

        Raises:
            SdlcError: the requested plan does not exist.
        """
        short_id = self._short_id(item_id)
        text = self._drafts.read(short_id) if draft else self._items.read_plan(short_id)
        if text is None:
            raise SdlcError(f"{short_id} has no {'draft' if draft else 'committed plan'}")
        return text

    def task_handoff(self, item_id: str, task_id: str) -> str:
        """Returns the plan header plus one task section, and the review when the item has one.

        Raises:
            SdlcError: the item has no committed plan or the task does not exist.
        """
        short_id = self._short_id(item_id)
        text = self._items.read_plan(short_id)
        if text is None:
            raise SdlcError(f"{short_id} has no committed plan")
        handoff = PlanParser.task_handoff(PlanParser.parse(text), task_id)
        if handoff is None:
            raise SdlcError(f"{short_id} has no task {task_id}")

        # Appends the user's review, which ranks above the plan text
        review = self._items.read_review(short_id)
        if review:
            handoff = f"{handoff.rstrip()}\n\n{ReviewParser.handoff_section(review)}"
        return handoff

    def set_task_status(self, item_id: str, target: TaskStatus, task_ids: List[str]) -> Item:
        """Moves tasks of a running item; `all` selects every task.

        Raises:
            InvalidTransitionError: the item is not running, a task lifecycle refuses the change, or a task
                becomes VALIDATED while the item is not IN PROGRESS or TESTING.
            SdlcError: a task id is unknown.
        """
        short_id = self._short_id(item_id)
        changed: Dict[str, TaskStatus] = {}

        def change(item: Item, all_items: Dict[str, Item]) -> Item:
            """Returns the item with the selected tasks moved."""
            selected = self._select_tasks(item, task_ids)

            # Refuses VALIDATED outside the item validation phase
            StatusRulesHelper.check_task_in_item(item.status, target)
            tasks = dict(item.tasks)
            for task_id in selected:
                StatusRulesHelper.check_task(tasks[task_id].status, target)
                changed[task_id] = tasks[task_id].status
                tasks[task_id] = tasks[task_id].model_copy(update={"status": target})
            return RecordHistoryHelper.touch(item, {"tasks": tasks}, self._host, "task_status",
                                           f"{', '.join(selected)} -> {target.value}")

        updated = self._items.modify(short_id, change, f"tasks {target.value}")
        for task_id, previous in changed.items():
            self._telemetry.record_event("task_status", short_id, task=task_id, status_from=previous.value,
                                         status_to=target.value)
        return updated

    def rework_task(self, item_id: str, task_id: str, stage: str, reason: str) -> Item:
        """Sends a task back to its engineer after a failed pipeline stage and records the rework.

        Raises:
            SdlcError: the stage or task is unknown.
            InvalidTransitionError: the item is not running or the task is DONE.
        """
        if stage not in REWORK_STAGES:
            raise SdlcError(f"rework stage must be one of {', '.join(REWORK_STAGES)}")
        short_id = self._short_id(item_id)
        previous: Dict[str, TaskStatus] = {}

        def change(item: Item, all_items: Dict[str, Item]) -> Item:
            """Returns the item with the task back IN PROGRESS."""
            self._select_tasks(item, [task_id])
            task = item.tasks[task_id]
            previous["status"] = task.status
            StatusRulesHelper.check_task(task.status, TaskStatus.IN_PROGRESS)
            tasks = {**item.tasks, task_id: task.model_copy(update={"status": TaskStatus.IN_PROGRESS})}
            return RecordHistoryHelper.touch(item, {"tasks": tasks}, self._host, "task_rework",
                                           f"{task_id} after {stage}: {reason}")

        updated = self._items.modify(short_id, change, f"rework {task_id}")
        self._telemetry.record_event("task_rework", short_id, task=task_id, status_from=previous["status"].value,
                                     status_to=TaskStatus.IN_PROGRESS.value, detail={"stage": stage, "reason": reason})
        return updated

    def _select_tasks(self, item: Item, task_ids: List[str]) -> List[str]:
        """Returns the task ids to change after checking the item runs and the ids exist.

        Raises:
            InvalidTransitionError: the item is not running.
            SdlcError: a task id is unknown.
        """
        if item.status not in RUNNING_STATUSES:
            raise InvalidTransitionError(f"{item.short_id} is {item.status.value}; tasks move only while it runs")
        if task_ids == ["all"]:
            return sorted(item.tasks)
        unknown = [task_id for task_id in task_ids if task_id not in item.tasks]
        if unknown:
            raise SdlcError(f"{item.short_id} has no tasks {', '.join(unknown)}")
        return task_ids

    def _short_id(self, item_id: str) -> str:
        """Returns the short item id for a short or full item id."""
        return ItemIdHelper.normalize_item(item_id, self._prefix)

