import time
from abc import ABC
from typing import Callable

import pytest

from sdlc.datasources.git_command import GitCommandRunner
from sdlc.datasources.git_ledger_source import GitLedgerSource
from sdlc.models.errors import GitTimeoutError, LedgerUnreachableError
from sdlc.wiring import AppWiring

# Remote whose SSH transport hangs in the tests
HUNG_REMOTE = "ssh://ledger.invalid/ledger.git"

# Time limit of each hung ledger call in the tests
HUNG_LIMIT_SECONDS = 0.5

# Longest a timed-out call may take to return
RETURN_CEILING_SECONDS = 5

# Environment that makes the SSH transport sleep instead of answering
HUNG_SSH_ENVIRONMENT = {"GIT_SSH_COMMAND": "sleep 30; true", "GIT_SSH_VARIANT": "ssh"}

# Message fragment of a ledger remote that did not answer within the limit
NO_ANSWER_PATTERN = f"did not answer within {HUNG_LIMIT_SECONDS:g} s"


class HungSshHelper(ABC):
    """Builds git runners and ledger sources over a hung SSH transport."""

    @staticmethod
    def runner(make_host: Callable[[str], AppWiring]) -> GitCommandRunner:
        """Returns a git runner in a host checkout whose SSH transport never answers."""
        return GitCommandRunner(make_host("alpha").settings.main_root, HUNG_SSH_ENVIRONMENT)

    @staticmethod
    def source(make_host: Callable[[str], AppWiring]) -> GitLedgerSource:
        """Returns a ledger source for the hung remote, limited to the test time limit."""
        return GitLedgerSource(HungSshHelper.runner(make_host), HUNG_REMOTE, "sdlc", HUNG_LIMIT_SECONDS)


class TestGitCommandTimeout:
    """Covers the time limit of git commands against a hung SSH transport."""

    def test_hung_network_command_stops_at_the_limit(self, make_host: Callable[[str], AppWiring]) -> None:
        """Raises at the limit although the SSH child keeps the output pipes open."""
        runner = HungSshHelper.runner(make_host)
        started = time.monotonic()
        with pytest.raises(GitTimeoutError):
            runner.run(["ls-remote", HUNG_REMOTE], check=False, timeout_seconds=HUNG_LIMIT_SECONDS)
        assert time.monotonic() - started < RETURN_CEILING_SECONDS

    def test_command_within_the_limit_returns_its_output(self, make_host: Callable[[str], AppWiring]) -> None:
        """Returns the commit hash of a quick command run under a limit."""
        clone = make_host("alpha").settings.main_root
        runner = GitCommandRunner(clone)
        result = runner.run(["rev-parse", "HEAD"], timeout_seconds=10)
        assert len(result.stdout.strip()) == 40


class TestLedgerNetworkTimeout:
    """Covers the bounded ledger network calls against a hung SSH transport."""

    def test_remote_tip_times_out_as_unreachable(self, make_host: Callable[[str], AppWiring]) -> None:
        """Raises the unreachable error within seconds when ls-remote hangs."""
        source = HungSshHelper.source(make_host)
        started = time.monotonic()
        with pytest.raises(LedgerUnreachableError, match=NO_ANSWER_PATTERN):
            source.remote_tip()
        assert time.monotonic() - started < RETURN_CEILING_SECONDS

    def test_fetch_times_out_as_unreachable(self, make_host: Callable[[str], AppWiring]) -> None:
        """Raises the unreachable error within seconds when fetch hangs."""
        source = HungSshHelper.source(make_host)
        started = time.monotonic()
        with pytest.raises(LedgerUnreachableError, match=NO_ANSWER_PATTERN):
            source.fetch("HEAD")
        assert time.monotonic() - started < RETURN_CEILING_SECONDS

    def test_push_timeout_says_the_write_can_have_landed(self, make_host: Callable[[str], AppWiring]) -> None:
        """Tells the caller to sync and read the record before a repeat when push hangs."""
        source = HungSshHelper.source(make_host)
        started = time.monotonic()
        with pytest.raises(LedgerUnreachableError, match="can have landed"):
            source.push("HEAD")
        assert time.monotonic() - started < RETURN_CEILING_SECONDS
