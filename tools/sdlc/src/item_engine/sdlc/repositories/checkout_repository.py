from typing import List, Optional

from sdlc.datasources.git_command import GitCommandRunner


class CheckoutRepository:
    """Reads the change under test from the checkout that holds the running tool."""

    def __init__(self, runner: GitCommandRunner) -> None:
        """Initializes the repository.

        Args:
            runner: the git runner rooted at the checkout under test.
        """
        self._runner = runner

    def changed_paths(self, base: str) -> Optional[List[str]]:
        """Returns the paths that differ between the base and HEAD, or None when git fails.

        Args:
            base: the git revision that the change under test starts from.

        Returns:
            The changed paths, with a rename listed as both of its paths.
        """
        result = self._runner.run(["diff", "--name-only", "--no-renames", base, "HEAD"], check=False)
        if result.returncode != 0:
            return None
        return [line for line in result.stdout.splitlines() if line]
