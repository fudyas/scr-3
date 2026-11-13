import pytest

from sdlc.algorithms.plan_parser import PlanParser
from sdlc.models.errors import PlanValidationError


class TestPlanParser:
    """Covers plan parsing, validation, and task handoff slicing."""

    def test_parses_blocks_tasks_and_metadata(self, plan_text: str) -> None:
        """Parses blocks, tasks, dependencies, and model hints."""
        document = PlanParser.validate(PlanParser.parse(plan_text), plan_text)
        assert document.title == "ITM-0001-LEDGER-CORE-TOOLS — Plan"
        assert [block.block_id for block in document.blocks] == ["BLK-0001", "BLK-0002"]
        first, second = document.blocks[0].tasks
        assert (first.task_id, first.depends_on, first.model) == ("TSK-0001", [], "default")
        assert (second.depends_on, second.model) == (["TSK-0001"], "high")
        assert document.blocks[1].tasks[0].model is None

    def test_task_handoff_holds_header_and_one_task(self, plan_text: str) -> None:
        """Slices the header, the block heading, and only the requested task."""
        handoff = PlanParser.task_handoff(PlanParser.parse(plan_text), "TSK-0002")
        assert handoff is not None
        assert "## Goal" in handoff and "## BLK-0001 — Ledger source" in handoff
        assert "ADD LEDGER REPOSITORY" in handoff
        assert "ADD LEDGER SOURCE" not in handoff and "TELEMETRY" not in handoff
        assert PlanParser.task_handoff(PlanParser.parse(plan_text), "TSK-0099") is None

    def test_reports_every_problem(self, plan_text: str) -> None:
        """Lists a cross-block dependency, a lowercase title, a bad model, and a placeholder."""
        broken = (plan_text
                  .replace("| depends_on | — |\n\n**To do**\n\n1. Add the store.",
                           "| depends_on | TSK-0001 |\n\n**To do**\n\n1. {{fill me}}")
                  .replace("ADD LEDGER REPOSITORY", "Add ledger repository")
                  .replace("| model | high |", "| model | gpt |"))
        with pytest.raises(PlanValidationError) as raised:
            PlanParser.validate(PlanParser.parse(broken), broken)
        problems = "\n".join(raised.value.problems)
        assert "TSK-0003 depends on TSK-0001" in problems
        assert "TSK-0002 title must be" in problems
        assert "TSK-0002 model must be" in problems
        assert "placeholders" in problems

    def test_requires_sections_blocks_and_done_when(self) -> None:
        """Rejects a plan without required sections, blocks, or acceptance criteria."""
        text = "# X — Plan\n\n## Goal\n\nG\n\n## BLK-0001 — B\n\n### TSK-0001 — DO IT\n\n**To do**\n\n1. x\n"
        with pytest.raises(PlanValidationError) as raised:
            PlanParser.validate(PlanParser.parse(text), text)
        problems = "\n".join(raised.value.problems)
        assert "## Context" in problems and "## Design" in problems and "Done when" in problems

    def test_rejects_duplicate_ids_and_orphan_task(self) -> None:
        """Rejects duplicated task ids and a task before the first block."""
        text = ("# X — Plan\n\n## Goal\n\n## Context\n\n## Design\n\n### TSK-0001 — ORPHAN\n\n**Done when**\n\n"
                "## BLK-0001 — B\n\n### TSK-0002 — A\n\n**Done when**\n\n### TSK-0002 — B\n\n**Done when**\n")
        with pytest.raises(PlanValidationError) as raised:
            PlanParser.validate(PlanParser.parse(text), text)
        problems = "\n".join(raised.value.problems)
        assert "before the first block" in problems and "TSK-0002 appears more than once" in problems
