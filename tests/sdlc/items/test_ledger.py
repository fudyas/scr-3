import multiprocessing
from abc import ABC
from multiprocessing.queues import Queue
from multiprocessing.synchronize import Barrier
from pathlib import Path
from typing import Callable, List

import pytest

from sdlc.datasources.git_command import GitCommandRunner
from sdlc.datasources.git_ledger_source import GitLedgerSource
from sdlc.models.errors import LedgerContentionError, LedgerUnreachableError
from sdlc.models.item import ItemKind
from sdlc.models.ledger import LedgerChange
from sdlc.repositories.ledger_repository import LedgerRepository, LedgerSnapshot
from sdlc.settings import SdlcSettings
from sdlc.wiring import AppWiring


class LedgerFixtureHelper:
    """Builds ledger sources over a host's clone."""

    @staticmethod
    def source(wiring: AppWiring, remote: str = "origin") -> GitLedgerSource:
        """Returns a ledger source for the host's main checkout."""
        return GitLedgerSource(GitCommandRunner(wiring.settings.main_root), remote, "sdlc", 60)


class ConcurrentLedgerHelper(ABC):
    """Runs independent pipeline processes against one checkout."""

    @staticmethod
    def mint_items(settings: SdlcSettings, barrier: Barrier, results: Queue) -> None:
        """Mints items and refreshes the mirror while other processes use the same repository.

        Args:
            settings: shared checkout and ledger configuration.
            barrier: the rendezvous before writes and concurrent sync calls.
            results: the channel for completed ids or an error.
        """

        # Reports child errors to the parent instead of silently losing a worker
        try:
            host = AppWiring(settings)
            barrier.wait(timeout=20)
            ids = [host.item_usecases.mint(ItemKind.TASK, "PARALLEL-WORK", "idea", "text", [], []).short_id
                   for _ in range(4)]
            barrier.wait(timeout=20)
            for _ in range(4):
                host.item_usecases.sync()
            results.put({"ids": ids, "error": ""})
        except Exception as error:
            results.put({"ids": [], "error": str(error)})


class TestGitLedgerSource:
    """Covers plumbing writes, batch reads, and pushes against a real bare remote."""

    def test_writes_reads_and_pushes_without_checkout(self, make_host: Callable[[str], AppWiring]) -> None:
        """Writes a root commit, pushes it, reads non-ASCII text back, and removes a file."""
        host = make_host("alpha")
        source = LedgerFixtureHelper.source(host)
        assert source.remote_tip() is None
        first = source.commit_changes(None, {"a.txt": "alpha — one\n", "dir/b.txt": "b\n"}, "first")
        assert source.push(first).accepted
        assert source.remote_tip() == first
        second = source.commit_changes(first, {"a.txt": None, "dir/c.txt": "c\n"}, "second")
        assert source.push(second).accepted
        texts = source.read_texts(first, ["a.txt", "dir/b.txt", "missing.txt"])
        assert texts == {"a.txt": "alpha — one\n", "dir/b.txt": "b\n", "missing.txt": None}
        assert source.list_paths(second, "dir") == ["dir/b.txt", "dir/c.txt"]
        assert (host.settings.main_root / "a.txt").exists() is False

    def test_refuses_non_fast_forward_push(self, make_host: Callable[[str], AppWiring]) -> None:
        """Refuses a push built on a stale tip."""
        source = LedgerFixtureHelper.source(make_host("alpha"))
        base = source.commit_changes(None, {"x": "1\n"}, "base")
        assert source.push(base).accepted
        winner = source.commit_changes(base, {"x": "2\n"}, "winner")
        loser = source.commit_changes(base, {"x": "3\n"}, "loser")
        assert source.push(winner).accepted
        outcome = source.push(loser)
        assert not outcome.accepted and outcome.detail

    def test_unreachable_remote_fails_closed(self, make_host: Callable[[str], AppWiring], tmp_path: Path) -> None:
        """Raises when the remote does not exist."""
        source = LedgerFixtureHelper.source(make_host("alpha"), remote=str(tmp_path / "nowhere.git"))
        with pytest.raises(LedgerUnreachableError):
            source.remote_tip()


class TestLedgerRepository:
    """Covers the compare-and-swap retry loop across two hosts."""

    def test_retries_after_another_host_wins(self, make_host: Callable[[str], AppWiring]) -> None:
        """Re-runs the mutator on fresh data when another host pushes in between."""
        alpha_source = LedgerFixtureHelper.source(make_host("alpha"))
        beta_source = LedgerFixtureHelper.source(make_host("beta"))
        alpha = LedgerRepository(alpha_source, retry_limit=3)
        beta = LedgerRepository(beta_source, retry_limit=3)
        alpha.transact(lambda snapshot: LedgerChange(changes={"counter": "1"}, message="init"))
        seen: List[str] = []

        def increment(snapshot: LedgerSnapshot) -> LedgerChange:
            """Increments the counter; on the first attempt another host increments it first."""
            value = int(snapshot.read_text("counter") or "0")
            seen.append(str(value))
            if len(seen) == 1:
                beta.transact(lambda other: LedgerChange(
                    changes={"counter": str(int(other.read_text("counter")) + 1)}, message="beta"))
            return LedgerChange(changes={"counter": str(value + 1)}, message="alpha", result=value + 1)

        assert alpha.transact(increment) == 3
        assert seen == ["1", "2"]
        assert alpha.snapshot().read_text("counter") == "3"
        beta.sync()
        assert beta.snapshot().read_text("counter") == "3"

    def test_gives_up_after_retry_limit(self, make_host: Callable[[str], AppWiring]) -> None:
        """Raises contention when every attempt loses."""
        alpha = LedgerRepository(LedgerFixtureHelper.source(make_host("alpha")), retry_limit=2)
        beta = LedgerRepository(LedgerFixtureHelper.source(make_host("beta")), retry_limit=2)
        alpha.transact(lambda snapshot: LedgerChange(changes={"n": "0"}, message="init"))

        def always_lose(snapshot: LedgerSnapshot) -> LedgerChange:
            """Lets the other host write before every attempt."""
            beta.transact(lambda other: LedgerChange(changes={"n": str(int(other.read_text("n")) + 1)},
                                                     message="beta"))
            return LedgerChange(changes={"n": "alpha"}, message="alpha")

        with pytest.raises(LedgerContentionError):
            alpha.transact(always_lose)

    def test_concurrent_processes_share_one_checkout_without_losing_items(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Preserves every concurrent write, the final mirror, and unrelated working files."""
        host = make_host("alpha")
        source = LedgerFixtureHelper.source(host)
        runner = GitCommandRunner(host.settings.main_root)
        main_tip = runner.run(["rev-parse", "HEAD"]).stdout
        (host.settings.main_root / "README.md").write_text("user edit\n")
        main_diff = runner.run(["diff"]).stdout

        # Starts separate interpreters so the kernel lock must coordinate real processes
        context = multiprocessing.get_context("spawn")
        barrier = context.Barrier(4)
        results = context.Queue()
        processes = [context.Process(target=ConcurrentLedgerHelper.mint_items,
                                     args=(host.settings, barrier, results)) for _ in range(4)]
        try:
            for process in processes:
                process.start()
            reports = [results.get(timeout=40) for _ in processes]
            for process in processes:
                process.join(timeout=10)
            assert all(process.exitcode == 0 for process in processes)
            assert all(not report["error"] for report in reports), reports
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=10)
            results.close()

        # Verifies globally allocated ids and the mirror without an extra repairing sync
        ids = [item_id for report in reports for item_id in report["ids"]]
        assert len(ids) == len(set(ids)) == 16
        assert {item.short_id for item in host.item_usecases.list_items([], [])} == set(ids)
        assert source.local_tip() == source.remote_tip()
        assert runner.run(["rev-parse", "HEAD"]).stdout == main_tip
        assert runner.run(["diff"]).stdout == main_diff
        assert runner.run(["diff", "--cached"]).stdout == ""
