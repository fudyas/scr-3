import subprocess
from pathlib import Path
from typing import Callable

import pytest

from sdlc.algorithms.timestamps import TimestampHelper
from sdlc.settings import SdlcSettings
from sdlc.wiring import AppWiring


class GitFixtureHelper:
    """Creates throwaway git repositories for SDLC tests."""

    @staticmethod
    def git(repo_dir: Path, *args: str) -> str:
        """Runs a git command in the repository and returns its output."""
        completed = subprocess.run(["git", *args], cwd=repo_dir, capture_output=True, text=True, check=True)
        return completed.stdout.strip()

    @staticmethod
    def clone(remote: Path, target: Path) -> Path:
        """Clones the remote into the target and configures a test identity."""
        subprocess.run(["git", "clone", "--quiet", str(remote), str(target)], check=True, capture_output=True)
        GitFixtureHelper.git(target, "config", "user.email", "test@example.com")
        GitFixtureHelper.git(target, "config", "user.name", "test")
        return target


class SdlcFixtures:
    """Builds the git, wiring, and plan fixtures that the SDLC unit tests share."""

    @staticmethod
    def remote_repo(tmp_path: Path) -> Path:
        """Returns a bare remote whose `master` branch holds one commit."""
        remote = tmp_path / "remote.git"
        subprocess.run(["git", "init", "--quiet", "--bare", "-b", "master", str(remote)], check=True)
        seed = tmp_path / "seed"
        subprocess.run(["git", "init", "--quiet", "-b", "master", str(seed)], check=True)
        GitFixtureHelper.git(seed, "config", "user.email", "test@example.com")
        GitFixtureHelper.git(seed, "config", "user.name", "test")
        (seed / "README.md").write_text("seed\n")
        GitFixtureHelper.git(seed, "add", "README.md")
        GitFixtureHelper.git(seed, "commit", "--quiet", "-m", "seed")
        GitFixtureHelper.git(seed, "push", "--quiet", str(remote), "master")
        return remote

    @staticmethod
    def make_host(tmp_path: Path, remote_repo: Path) -> Callable[..., AppWiring]:
        """Returns a factory that builds the wiring of one simulated host with its own clone."""

        def build(host: str, now: Callable[[], str] = TimestampHelper.now) -> AppWiring:
            """Returns the wiring of a host named `host`, optionally on a deterministic clock."""
            checkout = GitFixtureHelper.clone(remote_repo, tmp_path / f"host-{host}")
            settings = SdlcSettings(
                main_root=checkout, host=host, ledger_remote="origin", ledger_branch="sdlc",
                work_branch_prefix="work", item_prefix="ITM", chain_prefix="CHN", push_retry_limit=5,
                lock_names=["maintree", "stack"], lock_poll_seconds=0.01,
                worktree_links=["var", ".lets"], worktree_data_dirs=["var"], ssh_key_path="admin/github", ssh_config_path="admin/config",
            )
            return AppWiring(settings, now=now)

        return build

    @staticmethod
    def plan_text() -> str:
        """Returns a valid two-block plan."""
        return """# ITM-0001-LEDGER-CORE-TOOLS — Plan

## Goal

Build the ledger core.

## Context

Records `ARC-0010`.

## Design

- **Fit:** fits.

## Out of scope

- Chains.

## BLK-0001 — Ledger source

### TSK-0001 — ADD LEDGER SOURCE

| Field | Value |
| --- | --- |
| depends_on | — |
| model | default |

**To do**

1. Add the source.

**Done when**

1. Tests pass.

### TSK-0002 — ADD LEDGER REPOSITORY

| Field | Value |
| --- | --- |
| depends_on | TSK-0001 |
| model | high |

**To do**

1. Add the repository.

**Done when**

1. Tests pass.

## BLK-0002 — Telemetry

### TSK-0003 — ADD TELEMETRY STORE

| Field | Value |
| --- | --- |
| depends_on | — |

**To do**

1. Add the store.

**Done when**

1. Tests pass.
"""


# Registers each builder as a function-scoped fixture; none is autouse
remote_repo = pytest.fixture(name="remote_repo")(SdlcFixtures.remote_repo)
make_host = pytest.fixture(name="make_host")(SdlcFixtures.make_host)
plan_text = pytest.fixture(name="plan_text")(SdlcFixtures.plan_text)
