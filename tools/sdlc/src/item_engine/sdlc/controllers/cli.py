import os
import shlex
import sys
import traceback
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import click

from sdlc.algorithms.error_text import ErrorTextHelper
from sdlc.algorithms.ide_command import IdeCommandHelper
from sdlc.algorithms.listing_render import ListingRenderHelper
from sdlc.algorithms.log_render import LogRenderHelper
from sdlc.models.chain import ChainStatus
from sdlc.models.artifact import ArtifactBinding
from sdlc.models.errors import InvalidItemIdError, SdlcError
from sdlc.models.item import Item, ItemKind, ItemStatus, TaskStatus
from sdlc.usecases.hardware_usecases import HardwareUsecases
from sdlc.models.record import RecordAmendment
from sdlc.models.run_log import LogLevel
from sdlc.models.stats import StatsTable
from sdlc.models.views import ChainView
from sdlc.usecases.stats_usecases import STATS_COMMAND_REPORTS
from sdlc.wiring import AppWiring
from scr_tools.algorithms.text_table import TextTableHelper
from scr_tools.controllers.tool_command_controller import ToolCommandController

# Exit code of an expected failure the tool reports without a traceback
EXIT_ERROR = 2

# Exit code of a dependency check that finds unmet dependencies
EXIT_BLOCKED = 3

# Item statuses accepted on the command line, keyed by their spelling with underscores
STATUS_CHOICES = {status.value.replace(" ", "_"): status for status in ItemStatus}

# Task statuses accepted on the command line, keyed by their spelling with underscores
TASK_STATUS_CHOICES = {status.value.replace(" ", "_"): status for status in TaskStatus}

# Chain statuses accepted on the command line, keyed by their spelling with underscores
CHAIN_STATUS_CHOICES = {status.value.replace(" ", "_"): status for status in ChainStatus}

# Member list argument that clears a chain
CLEAR_MEMBERS = "none"

# Indent of a member item row under its chain in `chains list --with-tasks`
MEMBER_INDENT = "    "


class SdlcCliController:
    """Adapts `lets sdlc` arguments into usecase calls and renders their results."""

    def __init__(self, wiring_factory: Callable[[], AppWiring]) -> None:
        """Initializes the controller.

        Args:
            wiring_factory: builds the wiring on first use, so `--help` needs no repository.
        """
        self._wiring_factory = wiring_factory
        self._wiring: Optional[AppWiring] = None

    @property
    def wiring(self) -> AppWiring:
        """Returns the wiring, building it on first use."""
        if self._wiring is None:
            self._wiring = self._wiring_factory()
        return self._wiring

    def run(self, argv: List[str]) -> int:
        """Runs the selected command and returns its process exit code.

        Args:
            argv: command arguments without the executable name.

        Returns:
            Zero on success, two on invalid input, domain errors, or unexpected failures, three when
            dependencies block execution, or one when the user interrupts the command. Every failure ends
            with one `error:` line on stderr and a nonzero exit code.
        """

        # Converts CLI, domain, and unexpected failures into stable process exit codes
        try:
            return self.build_command().main(args=argv, prog_name="lets sdlc", standalone_mode=False) or 0
        except click.ClickException as error:
            error.show()
            return error.exit_code
        except click.exceptions.Exit as error:
            return error.exit_code
        except click.Abort:
            print("Aborted!", file=sys.stderr)
            return 1
        except SdlcError as error:
            print(f"error: {ErrorTextHelper.one_line(str(error))}", file=sys.stderr)
            return EXIT_ERROR
        except Exception as error:
            # Prints the traceback first so the final stderr line stays the one-line error
            traceback.print_exc()
            print(f"error: unexpected {type(error).__name__}: {ErrorTextHelper.one_line(str(error))}",
                  file=sys.stderr)
            return EXIT_ERROR

    def hardware(self, action: str, item_id: str, deb: Optional[str], image_identity: Optional[str],
                 notes_file: Optional[str], confirmed_by_developer: bool) -> None:
        """Records hardware authority or the developer's result for one delivered package."""
        item = HardwareUsecases(self.wiring).record(action, item_id, deb, image_identity,
                                                   notes_file, confirmed_by_developer)
        ToolCommandController.print_json(item)

    def build_command(self) -> click.Group:
        """Returns the Click command tree without initializing repository wiring."""

        # Keeps help and argument validation independent of repository access
        commands = [
            click.Command('sync', help='refresh the local ledger mirror from the remote',
                          params=[], callback=self.sync),
            self._items_group(),
            self._artifacts_group(),
            click.Command('hardware', help='record required hardware acceptance and developer results',
                          params=[
                              click.Argument(['action'], type=click.Choice(['require', 'pass', 'fail'])),
                              click.Argument(['item_id']),
                              click.Option(['--deb'], type=click.Path(exists=True, dir_okay=False)),
                              click.Option(['--image-identity']),
                              click.Option(['--notes-file'], type=click.Path(exists=True, dir_okay=False)),
                              click.Option(['--confirmed-by-developer'], is_flag=True),
                          ], callback=self.hardware),
            self._chains_group(),
            click.Command('lock', help='acquire, release, check ownership, or inspect a host-local lease',
                          params=[
                              click.Argument(['action'], type=click.Choice(["acquire", "release", "check", "status"]), required=True),
                              click.Argument(['name'], required=False),
                              click.Option(['--holder'], help="holder id, usually the item id"),
                              click.Option(['--no-wait'], is_flag=True, help="fail at once when the lease is held"),
                              click.Option(['--steal'], is_flag=True, help="break the current holder's lease (acquire)"),
                              click.Option(['--force'], is_flag=True, help="release a lease another holder keeps"),
                          ], callback=self.lock),
            click.Command('worktree', help='add, remove, or list item worktrees, or present the item change for review',
                          params=[
                              click.Argument(['action'], required=True, type=click.Choice(
                                  ["add", "remove", "list", "present", "settle", "fingerprint", "context",
                                   "snapshot", "verified", "approve", "prepare-promotion", "promote"])),
                              click.Argument(['item_id'], required=True, metavar='ITEM'),
                              click.Argument(['name'], required=False),
                              click.Option(
                                  ['--base'],
                                  help='branch to cut from (add only); default is the main checkout branch',
                              ),
                              click.Option(['--delete-branch'], is_flag=True, help="delete the merged branch (remove)"),
                              click.Option(['--message'], help="commit message for the review changes (settle)"),
                              click.Option(['--expected-tree'], help="exact tree required by verified, approve, and settle"),
                              click.Option(['--expected-artifacts'], help="exact INPUT bundle digest for artifact review"),
                              click.Option(['--expected-commit'], help="tested merge commit required by promote"),
                              click.Option(['--codex-session'],
                                           help="Codex-Session trailer URL for the promotion merge commit "
                                                "(prepare-promotion)"),
                              click.Option(['--json', 'as_json'], is_flag=True, help="print review context as JSON"),
                          ], callback=self.worktree),
            click.Command('ide', help="open an item's integration worktree in an IDE for review",
                          params=[
                              click.Argument(['item_id'], required=True, metavar='ITEM'),
                              click.Option(
                                  ['--ide'],
                                  help='IDE or editor program to use instead of SCR_SDLC_IDE from etc/proj.conf',
                              ),
                              click.Option(['--host'], help='SSH host or alias for the remote IDE connection; requires --path'),
                              click.Option(
                                  ['--path', 'remote_path'],
                                  help='absolute path to the remote checkout .codex directory; requires --host',
                              ),
                          ], callback=self.ide),
            click.Command('mark', help="attribute this session's next turns to an item stage",
                          params=[
                              click.Argument(['item_id'], required=True, metavar='ITEM'),
                              click.Argument(['stage'], required=True),
                          ], callback=self.mark),
            click.Command('log', help='append a per-item run-log line, or tail the log',
                          params=[
                              click.Argument(['action'], type=click.Choice(["write", "tail"]), required=True),
                              click.Argument(['item_id'], required=True, metavar='ITEM'),
                              click.Argument(['message'], nargs=-1, callback=self._list_values, required=False),
                              click.Option(
                                  ['--role'],
                                  help='write: author role (run, planner, swe, validator, integrator, qa)',
                              ),
                              click.Option(['--task'], help="write: task id this line is about"),
                              click.Option(['--block'], help="write: block id this line is about"),
                              click.Option(
                                  ['--level'],
                                  type=click.Choice([level.value for level in LogLevel]),
                                  default=LogLevel.INFO.value,
                              ),
                              click.Option(
                                  ['--follow', '-f'],
                                  is_flag=True,
                                  help='tail: stream new lines until interrupted',
                              ),
                              click.Option(['--lines'], type=int, help="tail: show only the last N lines before following"),
                          ], callback=self.log),
            click.Command('stats', help='report pipeline telemetry; give an item id for a per-item summary',
                          params=[
                              click.Argument(
                                  ['report'],
                                  metavar='[REPORT|ITEM]',
                                  required=False,
                                  default='items',
                              ),
                              click.Option(['--item', 'item_id'], help="limit a report to one item"),
                              click.Option(['--sql'], help="query for the `sql` report"),
                              click.Option(['--json', 'as_json'], is_flag=True),
                          ], callback=self.stats),
            click.Command('test-domains', help='print the system test targets that the change since --base requires',
                          params=[
                              click.Option(['--base'], help="git revision the change starts from; without it all domains run"),
                          ], callback=self.test_domains),
        ]
        return self._command_group("sdlc", "SCR SDLC pipeline tooling.", commands)

    def _artifacts_group(self) -> click.Group:
        """Returns public commands for durable stage artifact bundles."""

        # Restricts every action to its own supported arguments before repository access
        commands = [
            click.Command('publish', params=[
                click.Argument(['item_id']),
                click.Option(['--stage'], required=True, type=click.Choice(['planning', 'implementation', 'qa'])),
                click.Option(['--manifest', 'manifest_path'], required=True,
                             type=click.Path(exists=True, dir_okay=False, path_type=Path)),
                click.Option(['--json', 'as_json'], is_flag=True),
            ], callback=self.artifact_publish),
            click.Command('list', params=[
                click.Argument(['item_id']), click.Option(['--json', 'as_json'], is_flag=True),
            ], callback=self.artifact_list),
        ]
        for action in ['restore', 'verify']:
            commands.append(click.Command(action, params=[
                click.Option(['--bundle', 'bundle_digest'], required=True),
                click.Option(['--json', 'as_json'], is_flag=True),
            ], callback=self.artifact_restore if action == 'restore' else self.artifact_verify))
        return self._command_group('artifacts', 'manage immutable planning, implementation, and QA bundles', commands)

    def artifact_publish(self, item_id: str, stage: str, manifest_path: Path, as_json: bool) -> int:
        """Publishes explicit stage files and prints their durable bundle binding."""
        binding = self.wiring.artifact_usecases.publish(item_id, manifest_path, stage)
        self._print_artifact(binding, as_json)
        return 0

    def artifact_list(self, item_id: str, as_json: bool) -> int:
        """Prints retained input and result bindings for one item."""
        bindings = self.wiring.artifact_usecases.list(item_id)
        if as_json:
            ToolCommandController.print_json(bindings)
            return 0
        for binding in bindings:
            self._print_artifact(binding, False)
        return 0

    def artifact_restore(self, bundle_digest: str, as_json: bool) -> int:
        """Restores missing managed files and immutable snapshot from durable ledger bytes."""
        self._print_artifact(self.wiring.artifact_usecases.restore(bundle_digest), as_json)
        return 0

    def artifact_verify(self, bundle_digest: str, as_json: bool) -> int:
        """Verifies durable bundle and local immutable snapshot bytes and modes."""
        self._print_artifact(self.wiring.artifact_usecases.verify(bundle_digest), as_json)
        return 0

    @staticmethod
    def _print_artifact(binding: ArtifactBinding, as_json: bool) -> None:
        """Prints a binding with distinct source, purpose, durable locator, and local snapshot."""
        if as_json:
            ToolCommandController.print_json(binding)
            return
        input_digest = binding.digest if binding.purpose == 'INPUT' else binding.input_digest
        result_digest = binding.digest if binding.purpose == 'RESULT' else None
        print(f"{binding.item_id} {binding.purpose} {binding.stage}: {binding.digest}\n"
              f"source tree {binding.source_tree}; INPUT {input_digest}; RESULT {result_digest}\n"
              f"ledger {binding.ledger_path}; snapshot {binding.snapshot_path}")

    def _items_group(self) -> click.Group:
        """Returns the `items` command group that mints items and drives them through plan, queue, and run."""
        commands = [
            click.Command('new', help='mint a new BACKLOG item',
                          params=[
                              click.Option(['--kind'], type=click.Choice([kind.value for kind in ItemKind]), required=True),
                              click.Option(['--desc'], required=True, help="DESC slug, e.g. GRAPH-CLAIM-AMEND"),
                              click.Option(['--idea'], help="the user's idea in the user's own words"),
                              click.Option(
                                  ['--idea-file'],
                                  type=click.Path(path_type=Path),
                                  help="file holding the user's idea",
                              ),
                              click.Option(['--description'], help="normalized longer statement of the idea"),
                              click.Option(
                                  ['--description-file'],
                                  type=click.Path(path_type=Path),
                                  help='file holding the description',
                              ),
                              click.Option(
                                  ['--tag'],
                                  multiple=True,
                                  callback=self._list_values,
                                  help='free-text tag (repeatable)',
                              ),
                              click.Option(
                                  ['--depends'],
                                  multiple=True,
                                  callback=self._list_values,
                                  help='item it depends on (repeatable)',
                              ),
                          ], callback=self.new),
            click.Command('list', help='list items',
                          params=[
                              *self._listing_options(sorted(STATUS_CHOICES)),
                              click.Option(['--tag'], multiple=True, callback=self._list_values),
                              click.Option(['--depends'], is_flag=True, help='list direct dependencies below each item'),
                          ], callback=self.list_items),
            click.Command('show', help='show one item with its tasks and history',
                          params=[
                              click.Argument(['item_id'], required=True, metavar='ITEM'),
                              click.Option(['--json', 'as_json'], is_flag=True),
                              self._color_option(),
                          ], callback=self.show),
            click.Command('amend', help='replace the idea, description, or DESC slug of a BACKLOG or PLANNED item',
                          params=[
                              click.Argument(['item_id'], required=True, metavar='ITEM'),
                              click.Option(['--desc'], help="new DESC slug, e.g. GRAPH-CLAIM-AMEND"),
                              click.Option(['--idea'], help="new idea in the user's own words"),
                              click.Option(
                                  ['--idea-file'],
                                  type=click.Path(path_type=Path),
                                  help="file holding the new idea",
                              ),
                              click.Option(['--description'], help="new normalized longer statement of the idea"),
                              click.Option(
                                  ['--description-file'],
                                  type=click.Path(path_type=Path),
                                  help='file holding the new description',
                              ),
                          ], callback=self.amend),
            click.Command('tag', help='add or remove item tags',
                          params=[
                              click.Argument(['action'], type=click.Choice(["add", "remove"]), required=True),
                              click.Argument(['item_id'], required=True, metavar='ITEM'),
                              click.Argument(['tags'], nargs=-1, callback=self._list_values, required=True),
                          ], callback=self.tag),
            click.Command('depends', help='set or check inter-item dependencies',
                          params=[
                              click.Argument(['action'], type=click.Choice(["set", "check"]), required=True),
                              click.Argument(['item_id'], required=True, metavar='ITEM'),
                              click.Argument(['dependencies'], nargs=-1, callback=self._list_values, required=False),
                          ], callback=self.depends),
            click.Command('status', help='move an item through its lifecycle',
                          params=[
                              click.Argument(['action'], type=click.Choice(["set"]), required=True),
                              click.Argument(['item_id'], required=True, metavar='ITEM'),
                              click.Argument(['status'], type=click.Choice(sorted(STATUS_CHOICES)), required=True),
                              click.Option(['--force'], is_flag=True, help="take over an item another host claims"),
                          ], callback=self.status),
            click.Command('obsolete', help='retire an item that will not be built',
                          params=[
                              click.Argument(['item_id'], required=True, metavar='ITEM'),
                          ], callback=self.obsolete),
            click.Command('plan', help='edit, check, commit, approve, or show an item plan',
                          params=[
                              click.Argument(
                                  ['action'],
                                  type=click.Choice(['edit', 'check', 'commit', 'approve', 'show']),
                                  required=True,
                              ),
                              click.Argument(['item_id'], required=True, metavar='ITEM'),
                              click.Option(['--draft'], is_flag=True, help="show the local draft (show only)"),
                          ], callback=self.plan),
            click.Command('review', help="edit, check, commit, or show the user's review of an item",
                          params=[
                              click.Argument(['action'], type=click.Choice(['edit', 'check', 'commit', 'show']),
                                             required=True),
                              click.Argument(['item_id'], required=True, metavar='ITEM'),
                              click.Option(['--draft'], is_flag=True, help="show the local draft (show only)"),
                          ], callback=self.review),
            click.Command('schedule', help='queue a PLANNED item for implementation',
                          params=[
                              click.Argument(['item_id'], required=True, metavar='ITEM'),
                              click.Option(['--before'], help="place it directly before this SCHEDULED item"),
                          ], callback=self.schedule),
            click.Command('unschedule', help='take a SCHEDULED item out of the queue',
                          params=[
                              click.Argument(['item_id'], required=True, metavar='ITEM'),
                          ], callback=self.unschedule),
            click.Command('queue', help='show running and scheduled items in run order',
                          params=[
                              click.Option(['--json', 'as_json'], is_flag=True),
                          ], callback=self.queue),
            click.Command('next', help='print the next ready SCHEDULED item, or NONE',
                          params=[], callback=self.next_item),
            click.Command('task', help='show a task handoff, move tasks, or record a rework',
                          params=[
                              click.Argument(['action'], type=click.Choice(["show", "set", "rework"]), required=True),
                              click.Argument(['item_id'], required=True, metavar='ITEM'),
                              click.Argument(['values'], nargs=-1, callback=self._list_values, required=True),
                              click.Option(['--stage'], help="rework only: validate, integrate, qa, or promote"),
                              click.Option(['--reason'], default="", help="rework only: one-line failure summary"),
                          ], callback=self.task),
        ]
        return self._command_group(
            "items", "mint and amend items, plan and queue them, and move them and their tasks", commands
        )

    def _chains_group(self) -> click.Group:
        """Returns the `chains` command group that frames items into named, ordered chains."""
        commands = [
            click.Command('new', help='mint a new chain, optionally with its ordered items',
                          params=[
                              click.Option(['--desc'], required=True, help="DESC slug, e.g. EMBEDDING-SAL-PIPELINE"),
                              click.Option(['--description'], help="what the chain frames"),
                              click.Option(
                                  ['--description-file'],
                                  type=click.Path(path_type=Path),
                                  help='file holding the description',
                              ),
                              click.Option(
                                  ['--tag'],
                                  multiple=True,
                                  callback=self._list_values,
                                  help='free-text tag (repeatable)',
                              ),
                              click.Option(
                                  ['--item'],
                                  multiple=True,
                                  callback=self._list_values,
                                  help='member item, in implementation order (repeatable)',
                              ),
                          ], callback=self.chain_new),
            click.Command('amend', help='replace the description or DESC slug of a chain that is not DONE',
                          params=[
                              click.Argument(['chain_id'], required=True, metavar='CHAIN'),
                              click.Option(['--desc'], help="new DESC slug, e.g. EMBEDDING-SAL-PIPELINE"),
                              click.Option(['--description'], help="new text for what the chain frames"),
                              click.Option(
                                  ['--description-file'],
                                  type=click.Path(path_type=Path),
                                  help='file holding the new description',
                              ),
                          ], callback=self.chain_amend),
            click.Command('items', help=f'replace the ordered items of a chain; `{CLEAR_MEMBERS}` clears them',
                          params=[
                              click.Argument(['chain_id'], required=True, metavar='CHAIN'),
                              click.Argument(['items'], nargs=-1, callback=self._list_values, required=True),
                          ], callback=self.chain_items),
            click.Command('list', help='list chains with their rolled-up status',
                          params=[
                              *self._listing_options(sorted(STATUS_CHOICES)),
                              click.Option(
                                  ['--with-tasks'],
                                  is_flag=True,
                                  help='list member items in chain order; status filters select members',
                              ),
                          ], callback=self.chain_list),
            click.Command('show', help='show one chain with its items in order',
                          params=[
                              click.Argument(['chain_id'], required=True, metavar='CHAIN'),
                              click.Option(['--json', 'as_json'], is_flag=True),
                              self._color_option(),
                          ], callback=self.chain_show),
        ]
        return self._command_group("chains", "mint and amend chains, set their items, and list their status", commands)

    def _listing_options(self, statuses: List[str]) -> List[click.Option]:
        """Returns the shared status filters and presentation options for listings.

        Args:
            statuses: the accepted lifecycle status names.

        Returns:
            Repeatable filters, description and color options, and JSON output selection.
        """
        return [
            click.Option(['--include', '--status', 'status'], type=click.Choice(statuses, case_sensitive=False),
                         multiple=True, callback=self._list_values,
                         help='include this status (repeatable; all statuses by default)'),
            click.Option(['--exclude'], type=click.Choice(statuses, case_sensitive=False), multiple=True,
                         callback=self._list_values, help='exclude this status after includes (repeatable)'),
            click.Option(['--desc'], is_flag=True, help='print descriptions below record names'),
            self._color_option(),
            click.Option(['--json', 'as_json'], is_flag=True),
        ]

    @staticmethod
    def _color_option() -> click.Option:
        """Returns the shared terminal color option."""
        return click.Option(['--colors'], type=click.Choice(['auto', 'yes', 'no']), default='auto',
                            show_default=True, help='use terminal colors; auto respects NO_COLOR')

    @staticmethod
    def _command_group(name: str, help_text: str, commands: List[click.Command]) -> click.Group:
        """Returns a command group whose commands, and the group itself, accept `-h` for help.

        Args:
            name: the group name on the command line.
            help_text: the one-line group help.
            commands: the commands and nested groups of the group.

        Returns:
            The command group.
        """
        for command in commands:
            command.context_settings["help_option_names"] = ["-h", "--help"]
        return click.Group(name, commands=commands, help=help_text,
                           context_settings={"help_option_names": ["-h", "--help"]})

    @staticmethod
    def _list_values(context: click.Context, parameter: click.Parameter, values: Tuple[str, ...]) -> List[str]:
        """Converts repeatable Click values into lists for application usecases.

        Args:
            context: invocation context supplied by Click.
            parameter: argument or option supplied by Click.
            values: parsed values in command-line order.

        Returns:
            A list that preserves the parsed order.
        """
        return list(values)

    def sync(self) -> int:
        """Refreshes the local ledger mirror."""
        tip = self.wiring.item_usecases.sync()
        print(f"ledger synced at {tip[:12]}" if tip else "remote has no ledger yet")
        return 0

    def new(
            self,
            kind: str,
            desc: str,
            idea: Optional[str],
            idea_file: Optional[Path],
            description: Optional[str],
            description_file: Optional[Path],
            tag: List[str],
            depends: List[str],
    ) -> int:
        """Mints a new item and prints its full id."""
        idea = self._text_argument(idea, idea_file, "--idea")
        description = self._text_argument(description, description_file, "--description")
        item = self.wiring.item_usecases.mint(
            ItemKind(kind), desc, idea, description, tag, depends
        )
        print(item.full_id)
        return 0

    def amend(
            self,
            item_id: str,
            desc: Optional[str],
            idea: Optional[str],
            idea_file: Optional[Path],
            description: Optional[str],
            description_file: Optional[Path],
    ) -> int:
        """Amends an item and prints what changed; tells the user when a plan exists that the amendment leaves as is."""
        amendment = RecordAmendment(
            desc=desc,
            idea=self._optional_text_argument(idea, idea_file, "--idea"),
            description=self._optional_text_argument(description, description_file, "--description"),
        )
        item = self.wiring.item_usecases.amend(item_id, amendment)
        print(f"{item.full_id} amended: {item.history[-1].detail}")

        # Warns that the plan and its approval still bind the old text
        if item.plan.revision > 0:
            print(f"note: plan r{item.plan.revision} is unchanged ({self._plan_approval(item)}); "
                  f"run /sdlc-plan {item.short_id} to replan against the new text")
        return 0

    def list_items(self, status: List[str], exclude: List[str], tag: List[str], desc: bool,
                   colors: str, as_json: bool, depends: bool = False) -> int:
        """Prints the items that match the filters."""
        statuses = [STATUS_CHOICES[value] for value in status]
        excluded = {STATUS_CHOICES[value] for value in exclude}
        items = [item for item in self.wiring.item_usecases.list_items(statuses, tag) if item.status not in excluded]
        if as_json:
            ToolCommandController.print_json(items)
            return 0

        # Resolves each item's containing chain from the local ledger mirror
        chains = {member: view.chain.full_id for view in self.wiring.chain_usecases.list_views()
                  for member in view.chain.items}
        rows: List[List[Any]] = []
        descriptions: List[str] = []
        for item in items:
            rows.append([item.full_id, item.status.value, chains.get(item.short_id), ", ".join(item.tags)])
            descriptions.append(item.description)

            # Includes direct dependencies independently of the parent selection filters
            if depends:
                for dependency_id in item.depends_on:
                    dependency = self.wiring.item_usecases.get(dependency_id)
                    rows.append([f"{MEMBER_INDENT}{dependency.full_id}", dependency.status.value,
                                 chains.get(dependency.short_id), ", ".join(dependency.tags)])
                    descriptions.append(dependency.description)
        print(ListingRenderHelper.render(["item", "status", "chain", "tags"], rows,
                                        descriptions if desc else [], ListingRenderHelper.colors_enabled(colors)))
        self._print_as_of()
        return 0

    def show(self, item_id: str, as_json: bool, colors: str = "auto") -> int:
        """Prints one item with its tasks and recent history."""
        item = self.wiring.item_usecases.get(item_id)
        if as_json:
            ToolCommandController.print_json(item)
            return 0
        approval = self._plan_approval(item)
        use_color = ListingRenderHelper.colors_enabled(colors)
        print(ListingRenderHelper.details(item.full_id, [
            ["status", item.status.value], ["kind", item.kind.value],
            ["prototype", ListingRenderHelper.prototype(item.tags) or "-"],
            ["host", item.host or "-"], ["plan", f"r{item.plan.revision} ({approval})"],
            ["tags", ', '.join(item.tags) or "-"], ["depends_on", ', '.join(item.depends_on) or "-"],
            ["idea", item.idea], ["description", item.description],
        ], use_color))
        print()
        if item.tasks:
            rows = [[task_id, task.block, task.status.value, ", ".join(task.depends_on), task.model, task.title]
                    for task_id, task in sorted(item.tasks.items())]
            print(ListingRenderHelper.render(["task", "block", "status", "depends_on", "model", "title"],
                                            rows, [], use_color))
            print()
        for entry in item.history[-8:]:
            print(f"{entry.at}  {entry.host}  {entry.event}  {entry.detail}")
        return 0

    def tag(self, action: str, item_id: str, tags: List[str]) -> int:
        """Adds or removes tags."""
        added = tags if action == "add" else []
        removed = tags if action == "remove" else []
        item = self.wiring.item_usecases.change_tags(item_id, added, removed)
        print(f"{item.full_id} tags: {', '.join(item.tags) or '-'}")
        return 0

    def depends(self, action: str, item_id: str, dependencies: List[str]) -> int:
        """Sets or checks dependencies; a blocked check exits with a distinct code."""
        if action == "set":
            dependencies = [] if dependencies == ["none"] else dependencies
            item = self.wiring.item_usecases.set_dependencies(item_id, dependencies)
            print(f"{item.full_id} depends_on: {', '.join(item.depends_on) or '-'}")
            return 0
        report = self.wiring.item_usecases.check_dependencies(item_id)
        if report.ready:
            print(f"READY {report.item_id}")
            return 0
        print(f"BLOCKED {report.item_id} by {', '.join(report.unmet)}")
        return EXIT_BLOCKED

    def status(self, action: str, item_id: str, status: str, force: bool) -> int:
        """Moves an item to a new status."""
        item = self.wiring.item_usecases.set_status(item_id, STATUS_CHOICES[status],
                                                    force)
        print(f"{item.full_id} {item.status.value}")
        return 0

    def obsolete(self, item_id: str) -> int:
        """Retires an item."""
        item = self.wiring.item_usecases.set_status(item_id, ItemStatus.OBSOLETE, False)
        print(f"{item.full_id} {item.status.value}")
        return 0

    def plan(self, action: str, item_id: str, draft: bool) -> int:
        """Runs one plan action."""
        usecases = self.wiring.plan_usecases
        if action == "edit":
            print(usecases.edit(item_id))
        elif action == "check":
            document = usecases.check(item_id)
            task_count = sum(len(block.tasks) for block in document.blocks)
            print(f"plan OK: {len(document.blocks)} blocks, {task_count} tasks")
        elif action == "commit":
            item = usecases.commit(item_id)
            print(f"{item.full_id} plan r{item.plan.revision} committed ({item.status.value})")
        elif action == "approve":
            item = usecases.approve(item_id)
            print(f"{item.full_id} plan r{item.plan.revision} approved ({item.status.value})")
        else:
            print(usecases.show(item_id, draft), end="")
        return 0

    def review(self, action: str, item_id: str, draft: bool) -> int:
        """Runs one review action."""
        usecases = self.wiring.review_usecases
        if action == "edit":
            print(usecases.edit(item_id))
        elif action == "check":
            print(f"review OK: {usecases.check(item_id)} decisions")
        elif action == "commit":
            item = usecases.commit(item_id)
            print(f"{item.full_id} review committed ({item.status.value})")
        else:
            print(usecases.show(item_id, draft), end="")
        return 0

    def schedule(self, item_id: str, before: Optional[str]) -> int:
        """Queues an item."""
        item = self.wiring.schedule_usecases.schedule(item_id, before)
        print(f"{item.full_id} {item.status.value}")
        return 0

    def unschedule(self, item_id: str) -> int:
        """Takes an item out of the queue."""
        item = self.wiring.schedule_usecases.unschedule(item_id)
        print(f"{item.full_id} {item.status.value}")
        return 0

    def queue(self, as_json: bool) -> int:
        """Prints the run queue."""
        entries = self.wiring.schedule_usecases.queue()
        if as_json:
            ToolCommandController.print_json([
                {"item": entry.item.full_id, "status": entry.item.status.value, "ready": entry.ready,
                 "unmet": entry.unmet, "host": entry.item.host}
                for entry in entries
            ])
            return 0
        rows = [[position + 1, entry.item.full_id, entry.item.status.value, entry.item.host,
                 "yes" if entry.ready else f"no ({', '.join(entry.unmet)})"]
                for position, entry in enumerate(entries)]
        print(TextTableHelper.render(["#", "item", "status", "host", "ready"], rows))
        self._print_as_of()
        return 0

    def next_item(self) -> int:
        """Prints the next ready item, or NONE."""
        item = self.wiring.schedule_usecases.next_ready()
        print(item.full_id if item else "NONE")
        return 0

    def task(self, action: str, item_id: str, values: List[str], stage: Optional[str], reason: str) -> int:
        """Prints a task handoff, moves tasks, or records a rework."""
        usecases = self.wiring.plan_usecases
        if action == "show":
            print(usecases.task_handoff(item_id, values[0]), end="")
            return 0
        if action == "rework":
            if not stage:
                raise SdlcError("task rework needs --stage")
            item = usecases.rework_task(item_id, values[0], stage, reason)
            print(f"{item.full_id} {values[0]} {item.tasks[values[0]].status.value}")
            return 0
        status_text, task_ids = values[0], values[1:]
        if status_text not in TASK_STATUS_CHOICES or not task_ids:
            raise SdlcError(f"usage: task set <item> <{'|'.join(TASK_STATUS_CHOICES)}> <TSK...|all>")
        item = usecases.set_task_status(item_id, TASK_STATUS_CHOICES[status_text], task_ids)
        print(f"{item.full_id} {self._task_progress(item)}")
        return 0

    def lock(
            self,
            action: str,
            name: Optional[str],
            holder: Optional[str],
            no_wait: bool,
            steal: bool,
            force: bool,
    ) -> int:
        """Acquires, releases, or inspects a lease."""
        usecases = self.wiring.lock_usecases
        if action == "status":
            for name, holder in usecases.status(name).items():
                print(f"{name}: free" if holder is None else
                      f"{name}: held by {holder.holder_id} on {holder.host} since {holder.acquired_at}")
            return 0
        if not name or not holder:
            raise SdlcError(f"lock {action} needs a lease name and --holder")
        if action == "check":
            usecases.require_holder(name, holder)
            print(f"{name}: held by {holder}")
            return 0
        if action == "acquire":
            acquisition = usecases.acquire(name, holder, not no_wait, steal)
            stolen = f", stolen from {acquisition.stolen_from}" if acquisition.stolen_from else ""
            print(f"{name}: acquired by {holder} after {acquisition.waited_seconds:.1f}s{stolen}")
            return 0
        released = usecases.release(name, holder, force)
        print(f"{name}: {'released' if released else 'already free'}")
        return 0

    def worktree(
            self,
            action: str,
            item_id: str,
            name: Optional[str],
            base: Optional[str],
            delete_branch: bool,
            message: Optional[str],
            expected_tree: Optional[str],
            expected_artifacts: Optional[str],
            expected_commit: Optional[str],
            codex_session: Optional[str],
            as_json: bool,
    ) -> int:
        """Adds, removes, or lists item worktrees, or presents, settles, or fingerprints the integration change."""
        usecases = self.wiring.worktree_usecases
        if expected_artifacts is not None and action not in (
                "verified", "approve", "settle", "prepare-promotion", "promote"):
            raise SdlcError(f"--expected-artifacts does not apply to worktree {action}")
        if codex_session is not None and action != "prepare-promotion":
            raise SdlcError("--codex-session applies only to worktree prepare-promotion")
        if action in ("verified", "approve", "settle") and not expected_tree:
            raise SdlcError(f"worktree {action} needs --expected-tree")
        if action == "promote":
            if not expected_commit:
                raise SdlcError("worktree promote needs --expected-commit")
            print(f"MERGED {usecases.promote(item_id, expected_commit, expected_artifacts)}")
            return 0
        if action in ("context", "snapshot", "verified", "approve", "prepare-promotion"):
            if action == "snapshot":
                session = usecases.snapshot(item_id)
            elif action == "verified":
                session = usecases.verified(item_id, expected_tree or "", expected_artifacts)
            elif action == "approve":
                session = usecases.approve(item_id, expected_tree or "", expected_artifacts)
            elif action == "prepare-promotion":
                session = usecases.prepare_promotion(item_id, codex_session, expected_artifacts)
            else:
                session = usecases.context(item_id)
            if as_json:
                ToolCommandController.print_json(session)
                return 0
            print(f"{session.phase}: {session.worktree} {session.branch}\n"
                  f"base {session.base_commit}; snapshot {session.snapshot_tree}; "
                  f"verified {session.verified_tree}; approved {session.approved_tree}\n"
                  f"verification {session.verification_worktree}; promotion {session.promotion_worktree} "
                  f"{session.promotion_commit}")
            if session.snapshot_artifacts is not None:
                print(f"INPUT {session.snapshot_artifacts.digest}; snapshot {session.snapshot_artifacts.snapshot_path}")
            if session.qa_artifacts is not None:
                print(f"RESULT {session.qa_artifacts.digest}; snapshot {session.qa_artifacts.snapshot_path}")
            return 0
        if action == "list":
            for path in usecases.list_paths(item_id):
                print(path)
            return 0
        if action == "present":
            presented = usecases.present(item_id, base)
            verb = "presented" if presented.created else "already presented"
            print(f"{verb}: {presented.file_count} files staged against {presented.merge_base[:12]}; "
                  f"built history kept at {presented.built_tip[:12]}")
            return 0
        if action == "settle":
            commit = usecases.settle(item_id, message or f"{item_id} review changes", expected_tree or "",
                                     expected_artifacts)
            print(f"committed {commit[:12]}" if commit else "nothing to commit")
            return 0
        if action == "fingerprint":
            print(usecases.fingerprint(item_id))
            return 0
        if not name:
            raise SdlcError(f"worktree {action} needs a name (block id or `integration`)")
        if action == "add":
            info = usecases.add(item_id, name, base)
            print(f"{info.path} {info.branch}")
            return 0
        usecases.remove(item_id, name, delete_branch)
        print(f"removed {item_id} {name}")
        return 0

    def ide(self, item_id: str, ide: Optional[str], host: Optional[str] = None,
            remote_path: Optional[str] = None) -> int:
        """Opens the item's integration worktree in the IDE and returns the IDE exit code."""
        opening = self.wiring.ide_usecases.open_integration(item_id, ide, host, remote_path)
        print(shlex.join(IdeCommandHelper.build(opening.ide, opening.folder, opening.host)))
        return opening.exit_code

    def chain_new(self, desc: str, description: Optional[str], description_file: Optional[Path], tag: List[str],
                  item: List[str]) -> int:
        """Mints a new chain and prints its full id."""
        description = self._text_argument(description, description_file, "--description")
        chain = self.wiring.chain_usecases.mint(desc, description, tag, item)
        print(chain.full_id)
        return 0

    def chain_amend(
            self,
            chain_id: str,
            desc: Optional[str],
            description: Optional[str],
            description_file: Optional[Path],
    ) -> int:
        """Amends a chain and prints what changed."""
        amendment = RecordAmendment(
            desc=desc,
            description=self._optional_text_argument(description, description_file, "--description"),
        )
        chain = self.wiring.chain_usecases.amend(chain_id, amendment)
        print(f"{chain.full_id} amended: {chain.history[-1].detail}")
        return 0

    def chain_items(self, chain_id: str, items: List[str]) -> int:
        """Replaces the ordered items of a chain."""
        members = [] if items == [CLEAR_MEMBERS] else items
        chain = self.wiring.chain_usecases.set_items(chain_id, members)
        print(f"{chain.full_id} items: {' -> '.join(chain.items) or '-'}")
        return 0

    def chain_list(self, status: List[str], exclude: List[str], with_tasks: bool, desc: bool,
                   colors: str, as_json: bool) -> int:
        """Prints every chain with its rolled-up status and member counts, optionally with its items."""
        views = self._chain_list_views(status, exclude, with_tasks)
        if as_json:
            ToolCommandController.print_json([self._chain_json(view) for view in views])
            return 0
        rows: List[List[Any]] = []
        descriptions: List[str] = []
        for view in views:
            rows.append([view.chain.full_id, view.status.value, ListingRenderHelper.prototype(view.chain.tags),
                         len(view.chain.items),
                         ", ".join(view.chain.tags)])
            descriptions.append(view.chain.description)

            # Lists the member items under their chain, indented, in chain order
            if with_tasks:
                rows.extend([f"{MEMBER_INDENT}{member.full_id}", member.status.value,
                             ListingRenderHelper.prototype(member.tags), None,
                             ", ".join(member.tags)] for member in view.members)
                descriptions.extend(member.description for member in view.members)
        print(ListingRenderHelper.render(["chain", "status", "prototype", "items", "tags"], rows,
                                        descriptions if desc else [], ListingRenderHelper.colors_enabled(colors)))
        self._print_as_of()
        return 0

    def _chain_list_views(self, status: List[str], exclude: List[str], with_tasks: bool) -> List[ChainView]:
        """Selects chains or member items while preserving complete chain summaries.

        Args:
            status: the included statuses, or no restriction when empty.
            exclude: the statuses removed after inclusion.
            with_tasks: whether filters select member items instead of chains.

        Returns:
            Chain views with matching members in their original order.

        Raises:
            click.BadParameter: an item-only status requires member output.
        """

        # Rejects item-only statuses before opening the repository for chain-only output
        if not with_tasks:
            for option, values in [("--include/--status", status), ("--exclude", exclude)]:
                for value in values:
                    if value not in CHAIN_STATUS_CHOICES:
                        raise click.BadParameter(f"{value} requires --with-tasks; chain statuses are BACKLOG, IN_PROGRESS, DONE",
                                                 param_hint=option)
            included = {CHAIN_STATUS_CHOICES[value] for value in status}
            excluded = {CHAIN_STATUS_CHOICES[value] for value in exclude}
            return [view for view in self.wiring.chain_usecases.list_views()
                    if (not included or view.status in included) and view.status not in excluded]

        # Filters members without changing the chain's original status, membership, or counts
        included_items = {STATUS_CHOICES[value] for value in status}
        excluded_items = {STATUS_CHOICES[value] for value in exclude}
        views = []
        for view in self.wiring.chain_usecases.list_views():
            members = [member for member in view.members
                       if (not included_items or member.status in included_items) and member.status not in excluded_items]
            if members or not (status or exclude):
                views.append(view.model_copy(update={"members": members}))
        return views

    def chain_show(self, chain_id: str, as_json: bool, colors: str = "auto") -> int:
        """Prints one chain with its items in chain order and its recent history."""
        view = self.wiring.chain_usecases.view(chain_id)
        if as_json:
            ToolCommandController.print_json(self._chain_json(view))
            return 0
        chain = view.chain
        use_color = ListingRenderHelper.colors_enabled(colors)
        print(ListingRenderHelper.details(chain.full_id, [
            ["status", view.status.value], ["prototype", ListingRenderHelper.prototype(chain.tags) or "-"],
            ["host", chain.host or "-"], ["tags", ', '.join(chain.tags) or "-"],
            ["counts", self._chain_counts(view)], ["description", chain.description],
        ], use_color))
        print()
        if view.members:
            rows = [[position + 1, member.full_id, member.kind.value, member.status.value, self._task_progress(member),
                     member.host] for position, member in enumerate(view.members)]
            print(ListingRenderHelper.render(["#", "item", "kind", "status", "tasks", "host"], rows, [], use_color))
        else:
            print("(no items)")
        print()
        for entry in chain.history[-8:]:
            print(f"{entry.at}  {entry.host}  {entry.event}  {entry.detail}")
        return 0

    @staticmethod
    def _chain_counts(view: ChainView) -> str:
        """Returns the member counts per status, such as `BACKLOG 2, DONE 1`, or `-` for an empty chain."""
        return ", ".join(f"{status.value} {count}" for status, count in view.counts.items()) or "-"

    @staticmethod
    def _chain_json(view: ChainView) -> Dict[str, Any]:
        """Returns the JSON record of a chain view: the chain, its status, counts, and member statuses."""
        return {
            **view.chain.model_dump(mode="json"),
            "status": view.status.value,
            "counts": {status.value: count for status, count in view.counts.items()},
            "members": [{"item": member.full_id, "status": member.status.value} for member in view.members],
        }

    def mark(self, item_id: str, stage: str) -> int:
        """Confirms a session mark; the PostToolUse telemetry hook records the attribution."""
        print(f"mark {item_id} {stage}")
        return 0

    def log(
            self,
            action: str,
            item_id: str,
            message: List[str],
            role: Optional[str],
            task: Optional[str],
            block: Optional[str],
            level: str,
            follow: bool,
            lines: Optional[int],
    ) -> int:
        """Appends one run-log line, or tails an item's run log with per-role color."""
        usecases = self.wiring.run_log_usecases
        if action == "write":
            if not role:
                raise SdlcError("log write needs --role")
            if not message:
                raise SdlcError("log write needs a message")
            entry = usecases.write(item_id, role, " ".join(message),
                                   LogLevel(level), task, block)
            print(f"logged {entry.item} {entry.role} {entry.level.value}")
            return 0
        use_color = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
        try:
            for entry in usecases.tail(item_id, follow, role, lines):
                print(LogRenderHelper.render(entry, use_color), flush=True)
        except KeyboardInterrupt:
            pass
        return 0

    def stats(self, report: str, item_id: Optional[str], sql: Optional[str], as_json: bool) -> int:
        """Prints a telemetry report."""
        usecases = self.wiring.stats_usecases
        item = self.wiring.item_usecases.normalize_id(item_id) if item_id else None
        if report not in STATS_COMMAND_REPORTS:
            self._print_table(usecases.item_summary(self._summary_item(report, item)), as_json)
            return 0
        if report == "harvest":
            report = self.wiring.telemetry_usecases.backfill(self.wiring.settings.main_root)
            print(f"harvested {report.sessions} sessions, {report.turns} turns, {report.agent_runs} agent runs")
            return 0
        if report == "sql":
            if not sql:
                raise SdlcError("stats sql needs --sql")
            table = usecases.query(sql)
        elif report == "doctor":
            table = usecases.doctor()
        else:
            table = usecases.report(report, item)
        self._print_table(table, as_json)
        return 0

    def test_domains(self, base: Optional[str]) -> int:
        """Prints the system test targets on standard output and the explanation lines on standard error."""
        selection = self.wiring.system_test_usecases.select(base)
        for explanation in selection.explanations:
            print(explanation, file=sys.stderr)
        for target in selection.targets:
            print(target)
        return 0

    def _summary_item(self, report: str, option_item: Optional[str]) -> str:
        """Returns the item id that a `stats <ITEM>` call names.

        Raises:
            SdlcError: the argument is neither a report nor an item id, or `--item` names another item.
        """

        # Reads the positional argument as an item id when it is not a report name
        try:
            item = self.wiring.item_usecases.normalize_id(report)
        except InvalidItemIdError as error:
            known = ", ".join(STATS_COMMAND_REPORTS)
            raise SdlcError(f"unknown report {report!r} (known: {known}; or an item id such as ITM-0001)") from error
        if option_item and option_item != item:
            raise SdlcError("give the item once")
        return item

    def _print_table(self, table: StatsTable, as_json: bool) -> None:
        """Prints a stats table as text or as JSON records."""
        if as_json:
            ToolCommandController.print_json([dict(zip(table.columns, row)) for row in table.rows])
        else:
            print(TextTableHelper.render(table.columns, table.rows) if table.columns else "(no rows)")

    def _print_as_of(self) -> None:
        """Prints the date of the local ledger mirror under a listing."""
        as_of = self.wiring.item_usecases.as_of()
        print(f"\nledger as of {as_of}" if as_of else "\nno local ledger yet; run `lets sdlc sync`")

    @staticmethod
    def _task_progress(item: Item) -> str:
        """Returns `done/total` task counts, or `-` for an item without tasks."""
        if not item.tasks:
            return "-"
        done = sum(1 for task in item.tasks.values() if task.status == TaskStatus.DONE)
        return f"{done}/{len(item.tasks)}"

    @staticmethod
    def _plan_approval(item: Item) -> str:
        """Returns `approved r{N}` for an approved plan revision, otherwise `not approved`."""
        return f"approved r{item.plan.approved_revision}" if item.plan.is_approved else "not approved"

    @staticmethod
    def _optional_text_argument(text: Optional[str], file_path: Optional[Path], name: str) -> Optional[str]:
        """Returns the text given inline or in a file, or `None` when neither form is given.

        Args:
            text: the inline text option.
            file_path: the file option holding the text.
            name: the inline option name, for the message.

        Returns:
            The inline text, the file content, or `None`.

        Raises:
            SdlcError: both forms were given.
        """
        if text is not None and file_path is not None:
            raise SdlcError(f"give at most one of {name} or {name}-file")
        if file_path is not None:
            return file_path.read_text(encoding="utf-8")
        return text

    @staticmethod
    def _text_argument(text: Optional[str], file_path: Optional[Path], name: str) -> str:
        """Returns the text given inline or in a file.

        Raises:
            SdlcError: neither or both forms were given.
        """
        result = SdlcCliController._optional_text_argument(text, file_path, name)
        if result is None:
            raise SdlcError(f"give exactly one of {name} or {name}-file")
        return result


class SdlcCliEntry:
    """Process entry point of the SDLC command line."""

    @staticmethod
    def main(argv: List[str]) -> int:
        """Runs the command line and returns the exit code."""
        controller = SdlcCliController(lambda: AppWiring.from_directory(Path.cwd()))
        return controller.run(argv)


if __name__ == "__main__":
    sys.exit(SdlcCliEntry.main(sys.argv[1:]))
