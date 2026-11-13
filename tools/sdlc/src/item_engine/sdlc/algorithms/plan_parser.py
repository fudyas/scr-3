import re
from abc import ABC
from typing import Dict, List, Optional

from sdlc.models.errors import PlanValidationError
from sdlc.models.plan import PlanBlock, PlanDocument, PlanTask

# Matches a block heading, such as `## BLK-0001 — Ledger data source`
BLOCK_HEADING = re.compile(r"^##\s+(BLK-\d{4,})\s+[—-]+\s+(.+?)\s*$")

# Matches a task heading, such as `### TSK-0001 — ADD LEDGER SOURCE`
TASK_HEADING = re.compile(r"^###\s+(TSK-\d{4,})\s+[—-]+\s+(.+?)\s*$")

# Matches a level-two section heading
SECTION_HEADING = re.compile(r"^##\s+(.+?)\s*$")

# Matches a metadata table row, such as `| depends_on | TSK-0001 |`
METADATA_ROW = re.compile(r"^\|\s*(?:\d+\s*\|\s*)?([a-z_]+)\s*\|\s*(.*?)\s*\|\s*$")

# Header sections every plan carries
REQUIRED_SECTIONS = ("Goal", "Context", "Design")

# Marker every task section carries to state its acceptance criteria
DONE_WHEN_MARKER = "**Done when**"

# Model hints a task may name
TASK_MODELS = ("low", "default", "high")

# Values that mean an empty metadata cell
EMPTY_CELLS = ("", "—", "-", "none")


class PlanParser(ABC):
    """Parses, validates, and slices plan documents."""

    @staticmethod
    def parse(text: str) -> PlanDocument:
        """Returns the plan document parsed from Markdown text.

        Steps:
            1. Read the title and every line before the first block heading as the header.
            2. Start a block at each block heading and a task at each task heading.
            3. Read each task's metadata table and keep its full section text.

        Args:
            text: the plan Markdown.

        Returns:
            The parsed plan; validation is a separate step.
        """
        lines = text.splitlines()
        title = ""
        header_lines: List[str] = []
        section_names: List[str] = []
        blocks: List[Dict[str, object]] = []
        current_task_lines: Optional[List[str]] = None

        # Scans the lines once, routing each line to the header, a block, or a task
        for line in lines:
            block_match = BLOCK_HEADING.match(line)
            task_match = TASK_HEADING.match(line)
            if block_match:
                blocks.append({"id": block_match.group(1), "title": block_match.group(2), "heading": line, "tasks": []})
                current_task_lines = None
            elif task_match:
                current_task_lines = [line]
                task = {"id": task_match.group(1), "title": task_match.group(2), "lines": current_task_lines}
                if blocks:
                    blocks[-1]["tasks"].append(task)
                else:
                    blocks.append({"id": "", "title": "", "heading": "", "tasks": [task]})
            elif blocks:
                if current_task_lines is not None:
                    current_task_lines.append(line)
            else:
                header_lines.append(line)
                if not title and line.startswith("# "):
                    title = line[2:].strip()
                section_match = SECTION_HEADING.match(line)
                if section_match:
                    section_names.append(section_match.group(1))

        return PlanDocument(
            title=title,
            header="\n".join(header_lines).strip(),
            section_names=section_names,
            blocks=[PlanParser._build_block(block) for block in blocks],
        )

    @staticmethod
    def validate(document: PlanDocument, raw_text: str) -> PlanDocument:
        """Returns the document when it follows every plan format rule.

        Args:
            document: the parsed plan.
            raw_text: the plan Markdown, checked for unfilled template placeholders.

        Returns:
            The same document.

        Raises:
            PlanValidationError: the plan breaks one or more rules; every problem is listed.
        """
        problems: List[str] = []

        # Checks the shell: title, required sections, placeholders, blocks
        if not document.title:
            problems.append("plan has no `# ` title line")
        for section in REQUIRED_SECTIONS:
            if section not in document.section_names:
                problems.append(f"plan has no `## {section}` section")
        if "{{" in raw_text:
            problems.append("plan still has `{{...}}` template placeholders")
        if not document.blocks:
            problems.append("plan has no `## BLK-NNNN — title` block")

        # Checks every block and task against the id, order, and content rules
        seen_blocks: List[str] = []
        seen_tasks: List[str] = []
        for block in document.blocks:
            if not block.block_id:
                problems.append("a task appears before the first block heading")
                continue
            if block.block_id in seen_blocks:
                problems.append(f"{block.block_id} appears more than once")
            seen_blocks.append(block.block_id)
            if not block.tasks:
                problems.append(f"{block.block_id} has no tasks")
            block_task_ids: List[str] = []
            for task in block.tasks:
                problems.extend(PlanParser._task_problems(task, block, block_task_ids, seen_tasks))
                block_task_ids.append(task.task_id)
                seen_tasks.append(task.task_id)

        if problems:
            raise PlanValidationError(problems)
        return document

    @staticmethod
    def task_handoff(document: PlanDocument, task_id: str) -> Optional[str]:
        """Returns the plan header, the task's block heading, and the task section, or None.

        Args:
            document: the parsed plan.
            task_id: the task to slice out.

        Returns:
            The self-contained text a task engineer needs, or None when the task does not exist.
        """
        for block in document.blocks:
            for task in block.tasks:
                if task.task_id == task_id:
                    return f"{document.header}\n\n{block.heading}\n\n{task.section}\n"
        return None

    @staticmethod
    def _build_block(block: Dict[str, object]) -> PlanBlock:
        """Returns a plan block built from the scanner's raw block record."""
        tasks = [PlanParser._build_task(task) for task in block["tasks"]]
        return PlanBlock(block_id=block["id"], title=block["title"], heading=block["heading"], tasks=tasks)

    @staticmethod
    def _build_task(task: Dict[str, object]) -> PlanTask:
        """Returns a plan task built from the scanner's raw task record and its metadata table."""
        metadata: Dict[str, str] = {}
        for line in task["lines"]:
            row = METADATA_ROW.match(line)
            if row and row.group(1) not in ("field",):
                metadata[row.group(1)] = row.group(2)
        depends_cell = metadata.get("depends_on", "")
        depends_on = [] if depends_cell.lower() in EMPTY_CELLS else [
            part.strip() for part in depends_cell.split(",") if part.strip()
        ]
        model_cell = metadata.get("model", "").lower()
        return PlanTask(
            task_id=task["id"],
            title=task["title"],
            depends_on=depends_on,
            model=None if model_cell in EMPTY_CELLS else model_cell,
            section="\n".join(task["lines"]).strip(),
        )

    @staticmethod
    def _task_problems(task: PlanTask, block: PlanBlock, earlier_in_block: List[str], seen_tasks: List[str]) -> List[str]:
        """Returns every rule a single task breaks.

        Args:
            task: the task to check.
            block: the block that holds the task.
            earlier_in_block: ids of the tasks above this one in the same block.
            seen_tasks: ids of every task above this one in the plan.

        Returns:
            One line per broken rule.
        """
        problems: List[str] = []
        if task.task_id in seen_tasks:
            problems.append(f"{task.task_id} appears more than once")
        if task.title != task.title.upper():
            problems.append(f"{task.task_id} title must be an UPPERCASE imperative phrase")
        if task.model is not None and task.model not in TASK_MODELS:
            problems.append(f"{task.task_id} model must be one of {', '.join(TASK_MODELS)}")
        if DONE_WHEN_MARKER not in task.section:
            problems.append(f"{task.task_id} has no {DONE_WHEN_MARKER} criteria")
        for dependency in task.depends_on:
            if dependency not in earlier_in_block:
                problems.append(
                    f"{task.task_id} depends on {dependency}, which is not an earlier task in {block.block_id}"
                )
        return problems
