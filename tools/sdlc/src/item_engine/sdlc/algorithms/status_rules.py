from abc import ABC
from typing import Dict, List, Set

from sdlc.models.errors import InvalidTransitionError
from sdlc.models.item import ItemStatus, TaskStatus

# Item status changes the lifecycle allows, keyed by the current status
ITEM_TRANSITIONS: Dict[ItemStatus, Set[ItemStatus]] = {
    ItemStatus.BACKLOG: {ItemStatus.PLANNED, ItemStatus.OBSOLETE},
    ItemStatus.PLANNED: {ItemStatus.BACKLOG, ItemStatus.SCHEDULED, ItemStatus.OBSOLETE},
    ItemStatus.SCHEDULED: {ItemStatus.PLANNED, ItemStatus.IN_PROGRESS, ItemStatus.OBSOLETE},
    ItemStatus.IN_PROGRESS: {ItemStatus.SCHEDULED, ItemStatus.TESTING},
    ItemStatus.TESTING: {ItemStatus.IN_PROGRESS, ItemStatus.REVIEW},
    ItemStatus.REVIEW: {ItemStatus.IN_PROGRESS, ItemStatus.TESTING, ItemStatus.DONE},
    ItemStatus.DONE: set(),
    ItemStatus.OBSOLETE: set(),
}

# Task status changes the lifecycle allows, keyed by the current status
TASK_TRANSITIONS: Dict[TaskStatus, Set[TaskStatus]] = {
    TaskStatus.TODO: {TaskStatus.IN_PROGRESS},
    TaskStatus.IN_PROGRESS: {TaskStatus.TODO, TaskStatus.VALIDATED},
    TaskStatus.VALIDATED: {TaskStatus.IN_PROGRESS, TaskStatus.DONE},
    TaskStatus.DONE: set(),
}

# Item statuses in which a task may become VALIDATED
VALIDATION_ITEM_STATUSES = (ItemStatus.IN_PROGRESS, ItemStatus.TESTING)


class StatusRulesHelper(ABC):
    """Checks item and task status changes against their lifecycles."""

    @staticmethod
    def check_item(current: ItemStatus, target: ItemStatus) -> None:
        """Checks that an item may move from the current status to the target status.

        Args:
            current: the item's status now.
            target: the requested status.

        Raises:
            InvalidTransitionError: the lifecycle does not allow the change.
        """
        if target not in ITEM_TRANSITIONS[current]:
            allowed = ", ".join(sorted(status.value for status in ITEM_TRANSITIONS[current])) or "none"
            raise InvalidTransitionError(
                f"item cannot move {current.value} -> {target.value} (allowed: {allowed})"
            )

    @staticmethod
    def check_task(current: TaskStatus, target: TaskStatus) -> None:
        """Checks that a task may move from the current status to the target status.

        Args:
            current: the task's status now.
            target: the requested status.

        Raises:
            InvalidTransitionError: the lifecycle does not allow the change.
        """
        if current == target:
            return
        if target not in TASK_TRANSITIONS[current]:
            allowed = ", ".join(sorted(status.value for status in TASK_TRANSITIONS[current])) or "none"
            raise InvalidTransitionError(
                f"task cannot move {current.value} -> {target.value} (allowed: {allowed})"
            )

    @staticmethod
    def check_task_in_item(item_status: ItemStatus, target: TaskStatus) -> None:
        """Checks that a task may take the target status while the item has the given status.

        Args:
            item_status: the status of the item that owns the task.
            target: the requested task status.

        Raises:
            InvalidTransitionError: the task would become VALIDATED outside item validation.
        """
        if target == TaskStatus.VALIDATED and item_status not in VALIDATION_ITEM_STATUSES:
            raise InvalidTransitionError(
                f"a task becomes VALIDATED only while the item is IN PROGRESS or TESTING, "
                f"not {item_status.value}; move the item back to validation first"
            )

    @staticmethod
    def check_item_tasks(target: ItemStatus, task_statuses: Dict[str, TaskStatus]) -> None:
        """Checks that the tasks of an item allow the item to take the target status.

        Args:
            target: the requested item status.
            task_statuses: the status of each task, keyed by task id.

        Raises:
            InvalidTransitionError: a task has not reached the status the target needs.
        """

        # REVIEW needs every task validated at least
        if target == ItemStatus.REVIEW:
            pending: List[str] = sorted(
                task_id for task_id, status in task_statuses.items()
                if status not in (TaskStatus.VALIDATED, TaskStatus.DONE)
            )
            if pending:
                raise InvalidTransitionError(
                    f"tasks are not VALIDATED: {', '.join(pending)}; validate them before REVIEW"
                )
            return

        # DONE needs every task done
        if target == ItemStatus.DONE:
            unfinished: List[str] = sorted(
                task_id for task_id, status in task_statuses.items() if status != TaskStatus.DONE
            )
            if unfinished:
                raise InvalidTransitionError(f"tasks are not DONE: {', '.join(unfinished)}")
