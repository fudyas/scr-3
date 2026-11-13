import re
from abc import ABC
from typing import List

from sdlc.models.errors import ReviewValidationError

# Matches a decision heading, such as `## D-01 — Keep one status per error`
DECISION_HEADING = re.compile(r"^##\s+(D-\d{2,})\s+[—-]+\s+(.+?)\s*$")

# Matches the first-level title line of a review
TITLE_LINE = re.compile(r"^#\s+\S")

# Matches a decision field line, such as `- **Overrides:** TSK-0010 To do 2`
FIELD_LINE = re.compile(r"^(?:-|\d+(?:\.\d+)*\.)\s+\*\*(Overrides|Decision):\*\*\s*(.*?)\s*$")

# Fields every decision carries
REQUIRED_FIELDS = ("Overrides", "Decision")

# Heading of the review section inside a task handoff
HANDOFF_HEADING = "## Review (user decisions)"

# Sentence that tells the engineer how the review ranks against the plan
PRECEDENCE_NOTE = "Where a decision below disagrees with the plan above, the decision wins."


class ReviewParser(ABC):
    """Validates review documents and slices them into task handoffs."""

    @staticmethod
    def validate(text: str) -> int:
        """Returns the number of decisions when the review passes every rule.

        Steps:
            1. Check the title line and that no template placeholder is left.
            2. Collect the decision sections in order.
            3. Check that the decision ids count up from `D-01` and that each decision has both fields.

        Args:
            text: the review Markdown.

        Returns:
            The number of decisions.

        Raises:
            ReviewValidationError: the review breaks one or more rules.
        """
        problems: List[str] = []
        lines = text.splitlines()

        # Checks the title and the template placeholders
        first_line = next((line for line in lines if line.strip()), "")
        if not TITLE_LINE.match(first_line):
            problems.append("the first line must be a `# <ITEM> — Review` title")
        if "{{" in text or "}}" in text:
            problems.append("a template placeholder `{{...}}` is still in the text")

        # Splits the text into decision sections
        sections: List[List[str]] = []
        for line in lines:
            if DECISION_HEADING.match(line):
                sections.append([line])
            elif sections:
                sections[-1].append(line)
        if not sections:
            problems.append("the review needs at least one `## D-01 — <title>` decision")

        # Checks the ids and the fields of every decision
        for position, section in enumerate(sections, start=1):
            match = DECISION_HEADING.match(section[0])
            decision_id = match.group(1) if match else ""
            if decision_id != f"D-{position:02d}":
                problems.append(f"decision {position} must be `D-{position:02d}`, not `{decision_id}`")
            fields = {field.group(1): field.group(2) for line in section[1:] if (field := FIELD_LINE.match(line))}
            for name in REQUIRED_FIELDS:
                if not fields.get(name):
                    problems.append(f"{decision_id} needs a non-empty `- **{name}:**` line")
        if problems:
            raise ReviewValidationError(problems)
        return len(sections)

    @staticmethod
    def handoff_section(text: str) -> str:
        """Returns the review as a section for a task handoff, with the precedence note.

        Args:
            text: the committed review Markdown.

        Returns:
            The section text, without the review's own title line.
        """

        # Drops the title line, because the handoff has its own heading
        lines = text.strip().splitlines()
        if lines and TITLE_LINE.match(lines[0]):
            lines = lines[1:]
        body = "\n".join(lines).strip()
        return f"{HANDOFF_HEADING}\n\n{PRECEDENCE_NOTE}\n\n{body}\n"
