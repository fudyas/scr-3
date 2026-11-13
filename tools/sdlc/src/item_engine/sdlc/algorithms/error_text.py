from abc import ABC


class ErrorTextHelper(ABC):
    """Folds multi-line failure text into one line for the command-line report."""

    @staticmethod
    def one_line(text: str) -> str:
        """Returns the text as one line with its non-empty lines joined by semicolons.

        Args:
            text: the failure text, possibly with several lines.

        Returns:
            The stripped non-empty lines joined by `; `, or `no detail` when none remain.
        """

        # Drops blank lines and surrounding whitespace before joining
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return "; ".join(lines) if lines else "no detail"
