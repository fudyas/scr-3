import json
import os
import socket
from abc import ABC
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import Field

from primitives.models.strict_model import StrictModel

# Environment variable that overrides the host name recorded in the ledger and telemetry
HOST_ENV_VARIABLE = "SDLC_HOST"

# Environment variable that overrides the ledger remote (a remote name or a repository path)
REMOTE_ENV_VARIABLE = "SDLC_LEDGER_REMOTE"

# Environment variable that carries the default IDE; `ide.sh` exports it from `SCR_SDLC_IDE` in etc/proj.conf
IDE_ENV_VARIABLE = "SDLC_IDE"


class SystemTestDomainSettings(StrictModel):
    """Maps changed paths to the system test domains that the system gate runs."""

    root: str = Field(default="tests/system", description="Names the directory that holds one directory per domain.")
    domains: Dict[str, List[str]] = Field(
        default_factory=dict, description="Maps each domain name to the source globs that select it."
    )
    shared_globs: List[str] = Field(
        default_factory=list, description="Lists the globs of shared paths, which select every domain."
    )
    ignored_globs: List[str] = Field(
        default_factory=list, description="Lists the globs of paths that no system test covers."
    )


class SdlcSettings(StrictModel):
    """Configuration that wires every SDLC data source, repository, and usecase."""

    # Locates the main checkout, which owns all host-local state
    main_root: Path

    # Names the host recorded in the ledger and telemetry
    host: str

    # Names the git remote or repository path that holds the ledger branch
    ledger_remote: str

    # Names the branch that holds the ledger
    ledger_branch: str

    # Gives the prefix of every item work branch
    work_branch_prefix: str

    # Gives the id prefix of item records
    item_prefix: str

    # Gives the id prefix of chain records
    chain_prefix: str

    # Caps the compare-and-swap retries of one ledger write
    push_retry_limit: int

    # Lists the lease names that the pipeline knows
    lock_names: List[str]

    # Sets the pause between two attempts to take a held lease, in seconds
    lock_poll_seconds: float

    # Lists the main-checkout entries that each worktree links to
    worktree_links: List[str]
    worktree_data_dirs: List[str] = Field(
        default_factory=list,
        description="Lists the link entries that the main checkout must hold as data directories.",
    )
    telemetry_blacklist: List[str] = Field(
        default_factory=list, description="Lists the item ids left out of telemetry statistics."
    )

    ledger_network_timeout_seconds: float = Field(
        default=60.0,
        description="Limits each ledger ls-remote, fetch, and push, in seconds.",
    )

    system_tests: SystemTestDomainSettings = Field(
        default_factory=SystemTestDomainSettings,
        description="Maps changed paths to the system test domains of the system gate.",
    )

    # Locates the SSH key for ledger pushes, relative to the main checkout
    ssh_key_path: str

    # Locates the SSH config for ledger pushes, relative to the main checkout
    ssh_config_path: str

    # Names the default IDE that opens a worktree
    ide: Optional[str] = None

    @property
    def state_dir(self) -> Path:
        """Returns the host-local SDLC state directory in the main checkout."""
        return self.main_root / ".lets" / "sdlc"

    @property
    def drafts_dir(self) -> Path:
        """Returns the directory that holds local plan drafts."""
        return self.state_dir / "drafts"

    @property
    def locks_dir(self) -> Path:
        """Returns the directory that holds the host-local leases."""
        return self.state_dir / "locks"

    @property
    def telemetry_dir(self) -> Path:
        """Returns the directory that holds the local telemetry streams."""
        return self.state_dir / "telemetry"

    @property
    def logs_dir(self) -> Path:
        """Returns the directory that holds pipeline logs, such as QA runs."""
        return self.state_dir / "logs"

    @property
    def worktrees_dir(self) -> Path:
        """Returns the directory that holds the item worktrees."""
        return self.main_root / ".codex" / "worktrees"

    @property
    def artifacts_dir(self) -> Path:
        """Returns the managed stage-artifact directory in the main checkout."""
        return self.main_root / ".codex" / "sdlc" / "artifacts"


class SdlcSettingsHelper(ABC):
    """Loads SDLC settings from the tool configuration file and the environment."""

    @staticmethod
    def load(settings_file: Path, main_root: Path) -> SdlcSettings:
        """Returns settings read from the given file, with environment overrides applied.

        Args:
            settings_file: path to the JSON settings file.
            main_root: the main checkout root that owns all host-local state.

        Returns:
            The resolved settings.

        Raises:
            FileNotFoundError: the settings file does not exist.
        """
        values = json.loads(settings_file.read_text(encoding="utf-8"))
        values["main_root"] = main_root
        values["host"] = os.environ.get(HOST_ENV_VARIABLE) or socket.gethostname()
        values["ledger_remote"] = os.environ.get(REMOTE_ENV_VARIABLE) or values["ledger_remote"]
        values["ide"] = os.environ.get(IDE_ENV_VARIABLE) or None
        return SdlcSettings.from_document(values)
