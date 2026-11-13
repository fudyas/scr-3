import shutil
import subprocess
from typing import List

from sdlc.models.errors import IdeError


class IdeLauncherSource:
    """Starts an IDE or editor process and waits for it to exit."""

    def launch(self, command: List[str]) -> int:
        """Runs the command attached to the current terminal and returns its exit code.

        The process keeps the terminal, so a terminal editor such as vim works and a GUI launcher such as
        cursor returns as soon as it hands the folder to its window.

        Args:
            command: the program, its arguments, and the folder to open.

        Returns:
            The exit code of the IDE process.

        Raises:
            IdeError: the program is not on the search path, or it cannot start.
        """

        # Fails early with a clear message when the program does not exist
        if shutil.which(command[0]) is None:
            raise IdeError(f"IDE program not found: {command[0]!r}; install it or pass another one with --ide")
        try:
            return subprocess.run(command, check=False).returncode
        except OSError as error:
            raise IdeError(f"cannot start {command[0]!r}: {error}") from error
