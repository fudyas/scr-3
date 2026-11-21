import importlib.util
import os
import sys
from abc import ABC
from pathlib import Path
from typing import List

from sdlc.datasources.git_command import MainRootHelper
from sdlc.models.item import ItemStatus
from sdlc.wiring import AppWiring


# Loads retained SCR restoration mechanisms without importing the retired ceremony CLI
LEGACY_SPEC = importlib.util.spec_from_file_location("scr_image_safety", Path(__file__).resolve().parents[3] / "sdlc.py")
LEGACY = importlib.util.module_from_spec(LEGACY_SPEC)
LEGACY_SPEC.loader.exec_module(LEGACY)


class SafetyCliHelper(ABC):
    """Adapts approved item plans to the retained SCR package safety mechanisms."""

    @staticmethod
    def main(arguments: List[str]) -> int:
        """Runs a package or image safety command from any project checkout.

        Args:
            arguments: the command and its arguments.

        Returns:
            Zero on success, one on a refused safety operation.
        """
        try:
            # Refuses retired commands before argument parsing or repository access
            if arguments and arguments[0] in LEGACY.RETIRED_COMMANDS:
                raise LEGACY.SDLCError("retired ceremony command")
            args = LEGACY.SdlcCliHelper.parser().parse_args(arguments)
            command = arguments[0]
            if command not in {"package-init", "test-package", "verify-package", "lock-run", "models"}:
                raise LEGACY.SDLCError("retired ceremony command")
            # Consumes only the CLI separator before forwarding the child command
            if command == "lock-run" and args.command[:1] == ["--"]:
                args.command = args.command[1:]
            main_root = MainRootHelper.resolve(Path.cwd())
            ctx = LEGACY.Context(main_root, Path(__file__).resolve().parents[6])
            if getattr(args, "recover", False):
                os.environ["SDLC_RECOVERY"] = "1"

            # Uses item approval instead of creating or changing legacy requirement records
            if command == "package-init":
                wiring = AppWiring.from_directory(Path.cwd())
                item = wiring.item_usecases.get(args.id)
                if not item.plan.is_approved or item.status not in (ItemStatus.IN_PROGRESS, ItemStatus.TESTING):
                    raise LEGACY.SDLCError("package scaffolding requires a running approved item")
                if not item.hardware.required:
                    raise LEGACY.SDLCError("image item requires ./bin/lets sdlc hardware require ID")
                output = Path(args.output or Path.cwd()).resolve()
                assigned_root = (wiring.settings.worktrees_dir / item.short_id).resolve()
                if not output.is_relative_to(assigned_root) or output == assigned_root:
                    raise LEGACY.SDLCError("--output must identify the assigned item block or integration worktree")
                args.output = str(output)
                LEGACY.SdlcPackageHelper.cmd_package_init(
                    ctx, args, {"id": item.short_id, "state": "implementing",
                                "current_round": item.plan.revision})
            else:
                args.func(ctx, args)
            return 0
        except (LEGACY.SDLCError, OSError, ValueError) as error:
            print(f"error: {error}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    sys.exit(SafetyCliHelper.main(sys.argv[1:]))
