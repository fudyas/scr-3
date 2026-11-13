import sys
from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, List, Optional, TypeVar

import click

from primitives.lib.utils.errorno import ErrorNo
from scr_tools.algorithms.json_output import JsonOutputHelper
from scr_tools.models.errors import ToolError

# Exit code of an expected failure the tool reports without a traceback
EXIT_ERROR = 2

# Exit code of a validation whose report holds an error
EXIT_PROBLEM = 3

# The wiring type that a tool controller builds lazily
TWiring = TypeVar("TWiring")


class ToolCommandController(ABC, Generic[TWiring]):
    """Base of the tool controllers: builds the wiring lazily and turns failures into exit codes."""

    def __init__(self, wiring_factory: Callable[[], TWiring], program_name: str) -> None:
        """Initializes the controller.

        Args:
            wiring_factory: builds the wiring on first use, so `--help` and argument errors need no settings.
            program_name: the command name that the usage text prints.
        """
        self._wiring_factory = wiring_factory
        self._program_name = program_name
        self._wiring: Optional[TWiring] = None

    @property
    def wiring(self) -> TWiring:
        """Returns the wiring, building it on first use."""
        if self._wiring is None:
            self._wiring = self._wiring_factory()
        return self._wiring

    @abstractmethod
    def build_command(self) -> click.Command:
        """Returns the Click command, or the command tree, without initializing the wiring."""

    def run(self, argv: List[str]) -> int:
        """Runs the selected command and returns its process exit code.

        Args:
            argv: command arguments without the executable name.

        Returns:
            The exit code that the command callback returns, zero when it returns nothing, two on invalid input
            or a tool error, or one when the user interrupts the command.
        """

        # Converts CLI and domain failures into stable process exit codes
        try:
            return self.build_command().main(args=argv, prog_name=self._program_name, standalone_mode=False) or 0
        except click.ClickException as error:
            error.show()
            return error.exit_code
        except click.exceptions.Exit as error:
            return error.exit_code
        except click.Abort:
            print("Aborted!", file=sys.stderr)
            return 1
        except ToolError as error:
            print(f"error: {error}", file=sys.stderr)
            return EXIT_ERROR

    @staticmethod
    def print_json(value: Any) -> None:
        """Prints models, lists, dictionaries, and plain JSON data in the shared JSON layout."""
        print(JsonOutputHelper.render(value))

    @staticmethod
    def require_confirmation(question: str, action: str, is_terminal: bool, error_type: Callable[[ErrorNo, str], ToolError]) -> None:
        """Asks on the terminal whether to run a guarded action and continues only on yes.

        Args:
            question: the question that the terminal shows.
            action: the phrase that names the guarded action in the refusal text.
            is_terminal: whether the standard input is a terminal that can confirm the action.
            error_type: builds the tool error of the refusal from its error code and reason.

        Raises:
            ToolError: `EABORTED` when the standard input is no terminal or the answer is not yes.
        """
        if not is_terminal:
            raise error_type(ErrorNo.EABORTED, f"a {action} needs a confirmation on a terminal")

        # Takes only y or yes as consent; an end of input counts as no
        try:
            confirmed = click.confirm(question, default=False, err=True)
        except click.Abort:
            confirmed = False
        if not confirmed:
            raise error_type(ErrorNo.EABORTED, f"the {action} is not confirmed")

    @staticmethod
    def build_group(name: str, help_text: str, commands: List[click.Command]) -> click.Group:
        """Returns a group of the commands that accepts `-h` next to `--help` on the group and every command."""
        for command in commands:
            command.context_settings["help_option_names"] = ["-h", "--help"]
        return click.Group(name, commands=commands, help=help_text,
                           context_settings={"help_option_names": ["-h", "--help"]})
