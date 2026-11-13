from pathlib import Path
from typing import Optional

from sdlc.algorithms.ide_command import IdeCommandHelper
from sdlc.algorithms.item_ids import ItemIdHelper
from sdlc.datasources.ide_launcher_source import IdeLauncherSource
from sdlc.datasources.worktree_source import INTEGRATION_NAME, WorktreeSource
from sdlc.models.errors import IdeError
from sdlc.models.views import IdeOpening


class IdeUsecases:
    """Opens the integration worktree of an item in an IDE for review."""

    def __init__(self, worktrees: WorktreeSource, launcher: IdeLauncherSource, prefix: str,
                 default_ide: Optional[str]) -> None:
        """Initializes the usecases.

        Args:
            worktrees: the worktree data source.
            launcher: the data source that starts the IDE process.
            prefix: the item id prefix, such as `ITM`.
            default_ide: the IDE from the project configuration, or None when it sets none.
        """
        self._worktrees = worktrees
        self._launcher = launcher
        self._prefix = prefix
        self._default_ide = default_ide

    def open_integration(self, item_id: str, ide: Optional[str], host: Optional[str] = None,
                         remote_path: Optional[str] = None) -> IdeOpening:
        """Opens the item's integration worktree folder in the IDE.

        Steps:
            1. Validate the remote options and resolve the integration folder of the item.
            2. Pick the IDE: the explicit one, else the project default.
            3. Build the command and start the IDE.

        Args:
            item_id: the item id, with or without its DESC slug.
            ide: the IDE program to use instead of the default, or None.
            host: the SSH host or alias, supplied together with remote_path, or None for a local folder.
            remote_path: the absolute path of the remote checkout's `.codex` directory, or None.

        Returns:
            The folder, the IDE command text, and the IDE exit code.

        Raises:
            IdeError: the remote options are invalid, the local worktree does not exist, or the IDE cannot start.
        """

        # Requires an explicit remote root so a local checkout path never selects the remote folder
        if (host is None) != (remote_path is None):
            raise IdeError("--host and --path must be supplied together")

        # Resolves remote folders without checking the local filesystem for their worktrees
        short_id = ItemIdHelper.normalize_item(item_id, self._prefix)
        if remote_path is not None:
            root = Path(remote_path)
            if not root.is_absolute() or root.name != ".codex":
                raise IdeError("--path must be an absolute path to the remote checkout's .codex directory")
            folder = root / "worktrees" / short_id / INTEGRATION_NAME
        else:
            folder = self._worktrees.path(short_id, INTEGRATION_NAME)
            if not (folder / ".git").exists():
                raise IdeError(f"no {INTEGRATION_NAME} worktree for {short_id}; /sdlc-run creates it before QA")

        # Picks the explicit IDE over the project default and starts it
        chosen_ide = ide or self._default_ide or ""
        exit_code = self._launcher.launch(IdeCommandHelper.build(chosen_ide, folder, host))
        return IdeOpening(folder=folder, ide=chosen_ide, exit_code=exit_code, host=host)
