from typing import Callable, List

import pytest

from sdlc.models.errors import InvalidTransitionError
from sdlc.models.item import ItemStatus, TaskStatus
from sdlc.wiring import AppWiring
from tests.sdlc.items.test_item_usecases import ItemFlowHelper


class TestTaskRevalidation:
    """Covers the status order that forces a reworked task through validation again."""

    @staticmethod
    def _start(host: AppWiring, plan_text: str) -> str:
        """Plans the item and moves it IN PROGRESS with every task IN PROGRESS."""
        item_id = ItemFlowHelper.mint(host)
        ItemFlowHelper.plan_and_schedule(host, item_id, plan_text)
        host.item_usecases.set_status(item_id, ItemStatus.IN_PROGRESS, False)
        host.plan_usecases.set_task_status(item_id, TaskStatus.IN_PROGRESS, ["all"])
        return item_id

    @staticmethod
    def _validate(host: AppWiring, item_id: str, task_ids: List[str]) -> None:
        """Sets the given tasks VALIDATED."""
        host.plan_usecases.set_task_status(item_id, TaskStatus.VALIDATED, task_ids)

    def test_review_needs_every_task_validated(self, make_host: Callable[[str], AppWiring],
                                               plan_text: str) -> None:
        """Allows TESTING with some tasks validated and refuses REVIEW until all are."""
        host = make_host("alpha")
        item_id = self._start(host, plan_text)
        self._validate(host, item_id, ["TSK-0001", "TSK-0002"])
        host.item_usecases.set_status(item_id, ItemStatus.TESTING, False)
        with pytest.raises(InvalidTransitionError, match="TSK-0003"):
            host.item_usecases.set_status(item_id, ItemStatus.REVIEW, False)

    def test_qa_rework_blocks_review_until_validated_again(self, make_host: Callable[[str], AppWiring],
                                                           plan_text: str) -> None:
        """Refuses REVIEW while a task reworked after QA is IN PROGRESS."""
        host = make_host("alpha")
        item_id = self._start(host, plan_text)
        self._validate(host, item_id, ["all"])
        host.item_usecases.set_status(item_id, ItemStatus.TESTING, False)
        host.plan_usecases.rework_task(item_id, "TSK-0002", "qa", "system test failed")
        with pytest.raises(InvalidTransitionError, match="TSK-0002"):
            host.item_usecases.set_status(item_id, ItemStatus.REVIEW, False)
        self._validate(host, item_id, ["TSK-0002"])
        assert host.item_usecases.set_status(item_id, ItemStatus.REVIEW, False).status == ItemStatus.REVIEW

    def test_review_rework_needs_a_new_validation_pass(self, make_host: Callable[[str], AppWiring],
                                                       plan_text: str) -> None:
        """Forces a task reworked in REVIEW through IN PROGRESS, TESTING, and REVIEW again."""
        host = make_host("alpha")
        item_id = self._start(host, plan_text)
        self._validate(host, item_id, ["all"])
        host.item_usecases.set_status(item_id, ItemStatus.TESTING, False)
        host.item_usecases.set_status(item_id, ItemStatus.REVIEW, False)
        host.plan_usecases.rework_task(item_id, "TSK-0001", "review", "user asked for a change")

        # Refuses every shortcut from the reworked task to DONE
        with pytest.raises(InvalidTransitionError, match="VALIDATED only while"):
            self._validate(host, item_id, ["TSK-0001"])
        with pytest.raises(InvalidTransitionError):
            host.plan_usecases.set_task_status(item_id, TaskStatus.DONE, ["TSK-0001"])
        with pytest.raises(InvalidTransitionError, match="TSK-0001"):
            host.item_usecases.set_status(item_id, ItemStatus.DONE, False)

        # Walks the full validation pass again
        host.item_usecases.set_status(item_id, ItemStatus.IN_PROGRESS, False)
        self._validate(host, item_id, ["TSK-0001"])
        host.item_usecases.set_status(item_id, ItemStatus.TESTING, False)
        host.item_usecases.set_status(item_id, ItemStatus.REVIEW, False)
        host.plan_usecases.set_task_status(item_id, TaskStatus.DONE, ["all"])
        assert host.item_usecases.set_status(item_id, ItemStatus.DONE, False).status == ItemStatus.DONE

    def test_validate_rework_inside_the_build_still_works(self, make_host: Callable[[str], AppWiring],
                                                          plan_text: str) -> None:
        """Lets a validator rework a task and validate it again while the item is IN PROGRESS."""
        host = make_host("alpha")
        item_id = self._start(host, plan_text)
        self._validate(host, item_id, ["all"])
        host.plan_usecases.rework_task(item_id, "TSK-0001", "validate", "style gate failed")
        item = host.plan_usecases.set_task_status(item_id, TaskStatus.VALIDATED, ["TSK-0001"])
        assert item.tasks["TSK-0001"].status == TaskStatus.VALIDATED
