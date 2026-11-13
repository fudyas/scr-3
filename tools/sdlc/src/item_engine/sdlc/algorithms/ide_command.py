import shlex
from abc import ABC
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote

from sdlc.models.errors import IdeError


class IdeCommandHelper(ABC):
    """Builds the command line that opens a folder in an IDE or editor."""

    @staticmethod
    def build(ide: str, folder: Path, host: Optional[str] = None) -> List[str]:
        """Returns the program, its own arguments, and the folder to open.

        Args:
            ide: the program name or path, optionally followed by arguments, such as `code --new-window`.
            folder: the folder the program opens.
            host: the SSH host or alias for a remote folder, or None for a local folder.

        Returns:
            The argument list to run, with the local folder or remote folder URI as the last argument.

        Raises:
            IdeError: the IDE text is blank or has an unclosed quote, or the SSH host is invalid.
        """

        # Splits the text the way a shell does, so quoted arguments stay whole
        try:
            words = shlex.split(ide or "")
        except ValueError as error:
            raise IdeError(f"cannot read the IDE command {ide!r}: {error}") from error
        if not words:
            raise IdeError("no IDE given; pass --ide or set SCR_SDLC_IDE in etc/proj.conf")

        # VS Code supports this switch to open workspaces without Workspace Trust restrictions
        if Path(words[0]).name in {"code", "code-insiders"} and "--disable-workspace-trust" not in words[1:]:
            words.append("--disable-workspace-trust")

        # Keeps the SSH authority in the folder URI so WSL launchers cannot reinterpret a plain folder path
        if host is not None:
            if not host or any(character.isspace() or character == "\x00" for character in host):
                raise IdeError("--host must name an SSH host or alias without whitespace")
            authority = quote(f"ssh-remote+{host}", safe="+@:-[]")
            uri = f"vscode-remote://{authority}{quote(folder.as_posix(), safe='/')}"
            return [*words, "--folder-uri", uri]
        return [*words, str(folder)]
