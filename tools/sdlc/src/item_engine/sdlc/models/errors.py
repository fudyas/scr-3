from typing import List


class SdlcError(Exception):
    """Base class for every expected SDLC failure the CLI reports without a traceback."""


class ItemNotFoundError(SdlcError):
    """An item id that the ledger does not hold."""


class ChainNotFoundError(SdlcError):
    """A chain id that the ledger does not hold."""


class ChainMembershipError(SdlcError):
    """A chain member list that names unknown items or items of another chain."""


class InvalidItemIdError(SdlcError):
    """A string that does not parse as an item, block, or task id."""


class InvalidDescError(SdlcError):
    """A DESC slug that breaks the notation rules."""


class InvalidTransitionError(SdlcError):
    """A status change that the item or task lifecycle does not allow."""


class DependencyError(SdlcError):
    """A dependency change or check that the dependency rules refuse."""


class AmendmentRefusedError(SdlcError):
    """An amendment that the amend rules refuse."""


class ItemClaimError(SdlcError):
    """An item that another host already runs."""


class LedgerUnreachableError(SdlcError):
    """A ledger remote that cannot be reached; ledger writes fail closed."""


class LedgerContentionError(SdlcError):
    """A ledger write that lost every compare-and-swap retry."""


class GitCommandError(SdlcError):
    """A git command that exited with a failure."""


class GitTimeoutError(GitCommandError):
    """A git command that did not finish within its time limit."""


class LockError(SdlcError):
    """A lease operation that cannot complete."""


class WorktreeError(SdlcError):
    """A worktree operation that cannot complete."""


class IdeError(SdlcError):
    """An IDE that is not configured, not installed, or cannot open the worktree folder."""


class PlanValidationError(SdlcError):
    """A plan document that breaks the plan format rules."""

    def __init__(self, problems: List[str]) -> None:
        """Initializes the error with every problem found in the plan.

        Args:
            problems: one line per rule the plan breaks.
        """
        super().__init__("plan is invalid:\n" + "\n".join(f"  - {problem}" for problem in problems))
        self.problems = problems


class ReviewValidationError(SdlcError):
    """A review document that breaks the review format rules."""

    def __init__(self, problems: List[str]) -> None:
        """Initializes the error with every problem found in the review.

        Args:
            problems: one line per rule the review breaks.
        """
        super().__init__("review is invalid:\n" + "\n".join(f"  - {problem}" for problem in problems))
        self.problems = problems
