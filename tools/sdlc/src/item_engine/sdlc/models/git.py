from primitives.models.strict_model import StrictModel


class PushOutcome(StrictModel):
    """The result of one non-forced ledger push."""

    # Tells whether the remote accepted the push
    accepted: bool

    # Holds the git error output of a refused push
    detail: str = ""


class GitResult(StrictModel):
    """The outcome of one git command."""

    # Gives the exit code of the command
    returncode: int

    # Holds the standard output of the command
    stdout: str

    # Holds the standard error of the command
    stderr: str
