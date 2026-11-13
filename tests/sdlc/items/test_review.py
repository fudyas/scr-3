from abc import ABC
from pathlib import Path
from typing import Callable

import pytest

from sdlc.algorithms.review_parser import HANDOFF_HEADING, PRECEDENCE_NOTE, ReviewParser
from sdlc.controllers.cli import EXIT_ERROR, SdlcCliController
from sdlc.models.errors import ReviewValidationError, SdlcError
from sdlc.models.item import ItemKind, ItemStatus
from sdlc.wiring import AppWiring


class ReviewTextHelper(ABC):
    """Builds review documents for the tests."""

    # One valid decision section
    DECISION = (
        "## D-01 — One status per error\n\n"
        "- **Overrides:** TSK-0001 To do 1\n"
        "- **Decision:** Each error maps to exactly one status.\n"
    )

    @staticmethod
    def valid() -> str:
        """Returns a valid review with one decision."""
        return f"# ITM-0001-LEDGER-CORE-TOOLS — Review\n\nIntro line.\n\n{ReviewTextHelper.DECISION}"

    @staticmethod
    def two_decisions() -> str:
        """Returns a valid review with two decisions."""
        second = ReviewTextHelper.DECISION.replace("D-01", "D-02").replace("One status", "Keep the decoder")
        return f"{ReviewTextHelper.valid()}\n{second}"


class ReviewFlowHelper(ABC):
    """Mints an item with a committed plan for the review tests."""

    @staticmethod
    def planned_item(wiring: AppWiring, plan_text: str) -> str:
        """Mints an item, approves its plan, and returns the short id."""
        item_id = wiring.item_usecases.mint(ItemKind.FIX, "LEDGER-CORE-TOOLS", "idea", "Description.", [], []).short_id
        wiring.plan_usecases.edit(item_id).write_text(plan_text)
        wiring.plan_usecases.approve(item_id)
        return item_id

    @staticmethod
    def commit_review(wiring: AppWiring, item_id: str, text: str) -> None:
        """Writes the review draft and commits it."""
        wiring.review_usecases.edit(item_id).write_text(text)
        wiring.review_usecases.commit(item_id)


class TestReviewParser:
    """Covers the review format rules and the handoff section."""

    def test_accepts_a_valid_review(self) -> None:
        """Counts the decisions of a valid review."""
        assert ReviewParser.validate(ReviewTextHelper.valid()) == 1
        assert ReviewParser.validate(ReviewTextHelper.two_decisions()) == 2

    @pytest.mark.parametrize("text,problem", [
        ("no title\n\n" + ReviewTextHelper.DECISION, "title"),
        ("# T — Review\n\nOnly intro.\n", "at least one"),
        ("# T — Review\n\n" + ReviewTextHelper.DECISION.replace("One status per error", "{{Title}}"), "placeholder"),
        ("# T — Review\n\n" + ReviewTextHelper.DECISION.replace("D-01", "D-02"), "must be `D-01`"),
        ("# T — Review\n\n" + ReviewTextHelper.DECISION.replace("- **Overrides:** TSK-0001 To do 1\n", ""),
         "Overrides"),
        ("# T — Review\n\n" + ReviewTextHelper.DECISION.replace("Each error maps to exactly one status.", ""),
         "Decision"),
    ])
    def test_rejects_a_review_that_breaks_a_rule(self, text: str, problem: str) -> None:
        """Names the broken rule in the error."""
        with pytest.raises(ReviewValidationError, match=problem):
            ReviewParser.validate(text)

    def test_handoff_section_drops_the_title_and_adds_the_precedence_note(self) -> None:
        """Puts the review under its own heading with the precedence note and keeps every decision."""
        section = ReviewParser.handoff_section(ReviewTextHelper.two_decisions())
        assert section.startswith(f"{HANDOFF_HEADING}\n\n{PRECEDENCE_NOTE}\n\n")
        assert "# ITM-0001-LEDGER-CORE-TOOLS — Review" not in section
        assert "## D-01 — One status per error" in section and "## D-02 — Keep the decoder" in section


class TestReviewUsecases:
    """Covers the review draft, commit, show, and handoff over a real ledger."""

    def test_draft_starts_from_the_template_and_is_refused_until_filled(self, make_host: Callable[[str], AppWiring],
                                                                        plan_text: str) -> None:
        """Seeds the draft with the item id and refuses it while placeholders remain."""
        host = make_host("alpha")
        item_id = ReviewFlowHelper.planned_item(host, plan_text)
        draft = host.review_usecases.edit(item_id)
        assert draft.read_text().startswith("# ITM-0001-LEDGER-CORE-TOOLS — Review")
        with pytest.raises(ReviewValidationError, match="placeholder"):
            host.review_usecases.check(item_id)

    def test_check_needs_a_draft(self, make_host: Callable[[str], AppWiring], plan_text: str) -> None:
        """Refuses a check when no draft exists."""
        host = make_host("alpha")
        item_id = ReviewFlowHelper.planned_item(host, plan_text)
        with pytest.raises(SdlcError, match="no review draft"):
            host.review_usecases.check(item_id)

    def test_commit_stores_the_review_and_leaves_plan_and_status_unchanged(self, make_host: Callable[[str], AppWiring],
                                                                           plan_text: str) -> None:
        """Lands REVIEW.md on the ledger while PLAN.md, its approval, and the item status stay as they were."""
        host = make_host("alpha")
        item_id = ReviewFlowHelper.planned_item(host, plan_text)
        before = host.item_usecases.get(item_id)
        ReviewFlowHelper.commit_review(host, item_id, ReviewTextHelper.valid())
        after = host.item_usecases.get(item_id)
        assert host.review_usecases.show(item_id, draft=False) == ReviewTextHelper.valid()
        assert host.plan_usecases.show(item_id, draft=False) == plan_text
        assert after.status == ItemStatus.PLANNED == before.status
        assert after.plan == before.plan
        assert after.history[-1].event == "review_committed" and after.history[-1].detail == "1 decisions"

    def test_commit_discards_the_draft_and_the_next_edit_starts_from_the_committed_review(
            self, make_host: Callable[[str], AppWiring], plan_text: str) -> None:
        """Removes the draft on commit and seeds the next draft from the committed review."""
        host = make_host("alpha")
        item_id = ReviewFlowHelper.planned_item(host, plan_text)
        ReviewFlowHelper.commit_review(host, item_id, ReviewTextHelper.valid())
        with pytest.raises(SdlcError, match="no review draft"):
            host.review_usecases.show(item_id, draft=True)
        assert host.review_usecases.edit(item_id).read_text() == ReviewTextHelper.valid()

    def test_invalid_draft_is_not_committed(self, make_host: Callable[[str], AppWiring], plan_text: str) -> None:
        """Keeps the ledger free of a review that breaks the format rules."""
        host = make_host("alpha")
        item_id = ReviewFlowHelper.planned_item(host, plan_text)
        host.review_usecases.edit(item_id).write_text("# T — Review\n")
        with pytest.raises(ReviewValidationError):
            host.review_usecases.commit(item_id)
        with pytest.raises(SdlcError, match="no committed review"):
            host.review_usecases.show(item_id, draft=False)

    def test_task_handoff_carries_the_review_only_when_one_exists(self, make_host: Callable[[str], AppWiring],
                                                                  plan_text: str) -> None:
        """Appends the review with the precedence note to every task handoff, and leaves handoffs without one alone."""
        host = make_host("alpha")
        item_id = ReviewFlowHelper.planned_item(host, plan_text)
        plain = host.plan_usecases.task_handoff(item_id, "TSK-0001")
        assert HANDOFF_HEADING not in plain
        ReviewFlowHelper.commit_review(host, item_id, ReviewTextHelper.valid())
        reviewed = host.plan_usecases.task_handoff(item_id, "TSK-0001")
        assert reviewed.startswith(plain.rstrip())
        assert HANDOFF_HEADING in reviewed and PRECEDENCE_NOTE in reviewed
        assert "## D-01 — One status per error" in reviewed
        assert HANDOFF_HEADING in host.plan_usecases.task_handoff(item_id, "TSK-0003")

    def test_review_commit_is_allowed_while_the_item_runs(self, make_host: Callable[[str], AppWiring],
                                                          plan_text: str) -> None:
        """Accepts a review after the plan is frozen, because reviews come after the build."""
        host = make_host("alpha")
        item_id = ReviewFlowHelper.planned_item(host, plan_text)
        host.schedule_usecases.schedule(item_id, None)
        host.item_usecases.set_status(item_id, ItemStatus.IN_PROGRESS, False)
        ReviewFlowHelper.commit_review(host, item_id, ReviewTextHelper.two_decisions())
        assert host.item_usecases.get(item_id).status == ItemStatus.IN_PROGRESS
        assert host.review_usecases.show(item_id, draft=False) == ReviewTextHelper.two_decisions()


class TestReviewCli:
    """Covers the `items review` command line."""

    def test_edit_check_commit_show_flow(self, make_host: Callable[[str], AppWiring], plan_text: str,
                                         capsys: pytest.CaptureFixture) -> None:
        """Runs the four actions through the CLI."""
        wiring = make_host("alpha")
        item_id = ReviewFlowHelper.planned_item(wiring, plan_text)
        cli = SdlcCliController(lambda: wiring)
        capsys.readouterr()
        assert cli.run(["items", "review", "edit", item_id]) == 0
        draft_path = Path(capsys.readouterr().out.strip())
        draft_path.write_text(ReviewTextHelper.two_decisions(), encoding="utf-8")
        assert cli.run(["items", "review", "show", item_id, "--draft"]) == 0
        assert capsys.readouterr().out == ReviewTextHelper.two_decisions()
        assert cli.run(["items", "review", "check", item_id]) == 0
        assert capsys.readouterr().out.strip() == "review OK: 2 decisions"
        assert cli.run(["items", "review", "commit", item_id]) == 0
        assert capsys.readouterr().out.strip() == "ITM-0001-LEDGER-CORE-TOOLS review committed (PLANNED)"
        assert cli.run(["items", "review", "show", item_id]) == 0
        assert capsys.readouterr().out == ReviewTextHelper.two_decisions()
        assert cli.run(["items", "task", "show", item_id, "TSK-0001"]) == 0
        assert PRECEDENCE_NOTE in capsys.readouterr().out

    def test_reports_failures_as_errors(self, make_host: Callable[[str], AppWiring], plan_text: str,
                                        capsys: pytest.CaptureFixture) -> None:
        """Returns the error code for a missing draft, an unknown item, and an invalid review."""
        wiring = make_host("alpha")
        item_id = ReviewFlowHelper.planned_item(wiring, plan_text)
        cli = SdlcCliController(lambda: wiring)
        capsys.readouterr()
        assert cli.run(["items", "review", "check", item_id]) == EXIT_ERROR
        assert "no review draft" in capsys.readouterr().err
        assert cli.run(["items", "review", "show", "ITM-0009"]) == EXIT_ERROR
        assert cli.run(["items", "review", "edit", item_id]) == 0
        capsys.readouterr()
        assert cli.run(["items", "review", "commit", item_id]) == EXIT_ERROR
        assert "review is invalid" in capsys.readouterr().err
