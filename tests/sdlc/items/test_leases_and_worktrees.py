import subprocess
from abc import ABC
from pathlib import Path
from typing import Callable, List

import pytest
from pydantic import BaseModel, ConfigDict

from sdlc.datasources.lease_source import LeaseSource
from sdlc.models.errors import LockError, WorktreeError
from sdlc.wiring import AppWiring


class TestLeaseSource:
    """Covers atomic leases: re-entry, refusal, blocking, steal, and forced release."""

    def test_acquire_is_reentrant_and_exclusive(self, tmp_path: Path) -> None:
        """Lets the holder re-enter and refuses another holder without waiting."""
        leases = LeaseSource(tmp_path / "locks", "alpha", 0.01)
        assert leases.acquire("stack", "ITM-0001", wait=False, steal=False).holder.holder_id == "ITM-0001"
        assert leases.acquire("stack", "ITM-0001", wait=False, steal=False).waited_seconds < 1
        with pytest.raises(LockError, match="held by ITM-0001"):
            leases.acquire("stack", "ITM-0002", wait=False, steal=False)

    def test_waiter_blocks_until_release(self, tmp_path: Path) -> None:
        """Blocks a waiter until the holder releases, then hands it the lease."""
        polls: List[float] = []
        holder_side = LeaseSource(tmp_path / "locks", "alpha", 0.01)

        def release_on_second_poll(seconds: float) -> None:
            """Releases the first holder's lease on the waiter's second poll."""
            polls.append(seconds)
            if len(polls) == 2:
                holder_side.release("maintree", "ITM-0001", force=False)

        holder_side.acquire("maintree", "ITM-0001", wait=False, steal=False)
        waiter = LeaseSource(tmp_path / "locks", "alpha", 0.01, sleep=release_on_second_poll)
        acquisition = waiter.acquire("maintree", "ITM-0002", wait=True, steal=False)
        assert acquisition.holder.holder_id == "ITM-0002" and len(polls) == 2

    def test_steal_and_forced_release(self, tmp_path: Path) -> None:
        """Breaks a stranded lease by steal and refuses an unforced foreign release."""
        leases = LeaseSource(tmp_path / "locks", "alpha", 0.01)
        leases.acquire("stack", "ITM-0001", wait=False, steal=False)
        with pytest.raises(LockError, match="--force"):
            leases.release("stack", "ITM-0002", force=False)
        stolen = leases.acquire("stack", "ITM-0002", wait=False, steal=True)
        assert stolen.stolen_from == "ITM-0001" and leases.holder("stack").holder_id == "ITM-0002"
        assert leases.release("stack", "ITM-0003", force=True)
        assert leases.holder("stack") is None
        assert not leases.release("stack", "ITM-0003", force=False)


class TestLockUsecases:
    """Covers lease names and telemetry of lease use."""

    def test_rejects_unknown_lease_and_records_wait(self, make_host: Callable[[str], AppWiring]) -> None:
        """Refuses an unknown lease name and records acquire and release events."""
        host = make_host("alpha")
        with pytest.raises(LockError, match="unknown lease"):
            host.lock_usecases.acquire("database", "ITM-0001", wait=False, steal=False)
        host.lock_usecases.acquire("stack", "ITM-0001", wait=False, steal=False)
        assert host.lock_usecases.status(None)["stack"].holder_id == "ITM-0001"
        assert host.lock_usecases.release("stack", "ITM-0001", force=False)
        table = host.stats_usecases.report("leases", None)
        assert sorted(row[1] for row in table.rows) == ["lease_acquired", "lease_released"]


class TestWorktreeUsecases:
    """Covers block and integration worktrees with linked local state."""

    def test_adds_links_and_removes(self, make_host: Callable[[str], AppWiring]) -> None:
        """Creates a worktree on its work branch with state links, then removes it with its branch."""
        host = make_host("alpha")
        main_root = host.settings.main_root
        (main_root / "var").mkdir()
        (main_root / ".gitignore").write_text("/var\n/.lets\n")
        subprocess.run(["git", "add", ".gitignore"], cwd=main_root, check=True)
        subprocess.run(["git", "commit", "--quiet", "-m", "ignore"], cwd=main_root, check=True)

        info = host.worktree_usecases.add("ITM-0001-LEDGER", "BLK-0001", None)
        assert info.created and info.branch == "work/ITM-0001/BLK-0001"
        assert (info.path / "var").is_symlink()
        assert host.worktree_usecases.add("ITM-0001", "BLK-0001", None).created is False
        assert host.worktree_usecases.list_paths("ITM-0001") == [info.path]
        status = subprocess.run(["git", "status", "--porcelain"], cwd=info.path, capture_output=True, text=True)
        assert status.stdout == ""

        host.worktree_usecases.remove("ITM-0001", "BLK-0001", delete_branch=True)
        assert not info.path.exists()
        branches = subprocess.run(["git", "branch", "--list", "work/*"], cwd=main_root, capture_output=True,
                                  text=True)
        assert branches.stdout.strip() == ""

    def test_links_data_dir_created_in_main_checkout(self, make_host: Callable[[str], AppWiring]) -> None:
        """Creates a missing data directory in the main checkout, so the worktree links to it and keeps no copy."""
        host = make_host("alpha")
        main_root = host.settings.main_root
        assert not (main_root / "var").exists()

        info = host.worktree_usecases.add("ITM-0001", "BLK-0001", None)

        assert (main_root / "var").is_dir()
        assert (info.path / "var").is_symlink()
        assert (info.path / "var").resolve() == (main_root / "var").resolve()

    def test_rejects_bad_name_and_unmerged_branch(self, make_host: Callable[[str], AppWiring]) -> None:
        """Refuses a free-form worktree name and deleting an unmerged work branch."""
        host = make_host("alpha")
        with pytest.raises(WorktreeError):
            host.worktree_usecases.add("ITM-0001", "scratch", None)
        info = host.worktree_usecases.add("ITM-0001", "integration", None)
        (info.path / "new.txt").write_text("x\n")
        subprocess.run(["git", "add", "new.txt"], cwd=info.path, check=True)
        subprocess.run(["git", "-c", "user.email=t@e", "-c", "user.name=t", "commit", "--quiet", "-m", "x"],
                       cwd=info.path, check=True)
        with pytest.raises(WorktreeError, match="cannot delete"):
            host.worktree_usecases.remove("ITM-0001", "integration", delete_branch=True)


class BuiltIntegration(BaseModel):
    """An integration worktree with two built commits: its folder, the merge base, and the built tip."""

    model_config = ConfigDict(frozen=True)

    path: Path
    merge_base: str
    tip: str


class WorktreeGitHelper(ABC):
    """Runs git commands inside a worktree for the presentation tests."""

    @staticmethod
    def git(path: Path, *args: str) -> str:
        """Returns the output of a git command run in the folder."""
        completed = subprocess.run(["git", *args], cwd=path, capture_output=True, text=True, check=True)
        return completed.stdout.rstrip("\n")

    @staticmethod
    def commit_file(path: Path, name: str, text: str) -> str:
        """Writes a file, commits it, and returns the new commit."""
        (path / name).write_text(text)
        WorktreeGitHelper.git(path, "add", name)
        WorktreeGitHelper.git(path, "commit", "--quiet", "-m", f"add {name}")
        return WorktreeGitHelper.git(path, "rev-parse", "HEAD")

    @staticmethod
    def built_integration(host: AppWiring) -> BuiltIntegration:
        """Creates the integration worktree with two commits on top of the working branch."""
        WorktreeGitHelper.commit_file(host.settings.main_root, ".gitignore", "/.lets\n/.codex/worktrees\n/var\n")
        info = host.worktree_usecases.add("ITM-0001", "integration", None)
        merge_base = WorktreeGitHelper.git(info.path, "rev-parse", "HEAD")
        WorktreeGitHelper.commit_file(info.path, "a.txt", "a\n")
        tip = WorktreeGitHelper.commit_file(info.path, "b.txt", "b\n")
        return BuiltIntegration(path=info.path, merge_base=merge_base, tip=tip)

    @staticmethod
    def approve_snapshot(host: AppWiring) -> str:
        """Records successful verification and user approval of the current snapshot."""
        session = host.worktree_usecases.snapshot("ITM-0001")
        tree = session.snapshot_tree or ""
        host.worktree_usecases.verified("ITM-0001", tree)
        host.worktree_usecases.approve("ITM-0001", tree)
        return tree


class TestWorktreePresentation:
    """Covers showing the item change as staged changes for review and settling it afterwards."""

    def test_present_stages_the_item_change_and_keeps_the_built_history(self, make_host: Callable[[str], AppWiring]) -> None:
        """Lists every item file as staged against the merge base while the built commits stay on a branch."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        path, merge_base, tip = built.path, built.merge_base, built.tip
        presented = host.worktree_usecases.present("ITM-0001-LEDGER", None)
        assert presented.created and presented.file_count == 2
        assert presented.merge_base == merge_base and presented.built_tip == tip
        assert WorktreeGitHelper.git(path, "status", "--porcelain").splitlines() == ["A  a.txt", "A  b.txt"]
        assert WorktreeGitHelper.git(path, "rev-parse", "HEAD") == merge_base
        assert WorktreeGitHelper.git(path, "rev-parse", "work/ITM-0001/built") == tip
        assert (path / "a.txt").read_text() == "a\n"
        again = host.worktree_usecases.present("ITM-0001", None)
        assert again.created is False and again.built_tip == tip and again.file_count == 2

    def test_review_edits_stay_unstaged_and_settle_commits_them_on_top_of_the_built_history(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Keeps review edits apart from the staged item change, then commits them as one commit after the built tip."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        path, merge_base, tip = built.path, built.merge_base, built.tip
        host.worktree_usecases.present("ITM-0001", None)
        (path / "a.txt").write_text("a changed\n")
        (path / "c.txt").write_text("c\n")
        assert WorktreeGitHelper.git(path, "status", "--porcelain").splitlines() == ["AM a.txt", "A  b.txt", "?? c.txt"]
        expected_tree = WorktreeGitHelper.approve_snapshot(host)

        commit = host.worktree_usecases.settle("ITM-0001", "ITM-0001 review: D-01", expected_tree)
        assert commit == WorktreeGitHelper.git(path, "rev-parse", "HEAD")
        assert WorktreeGitHelper.git(path, "rev-parse", "HEAD^{tree}") == expected_tree
        assert WorktreeGitHelper.git(path, "rev-parse", "HEAD~1") == tip
        assert WorktreeGitHelper.git(path, "rev-list", "--count", f"{merge_base}..HEAD") == "3"
        assert WorktreeGitHelper.git(path, "status", "--porcelain") == ""
        assert WorktreeGitHelper.git(path, "rev-parse", "work/ITM-0001/built") == tip

    def test_settle_without_review_edits_restores_the_built_branch_and_commits_nothing(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Returns the branch to the built tip with no extra commit when the review changed nothing."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        path, merge_base, tip = built.path, built.merge_base, built.tip
        host.worktree_usecases.present("ITM-0001", None)
        tree = WorktreeGitHelper.approve_snapshot(host)
        assert host.worktree_usecases.settle("ITM-0001", "unused", tree) is None
        assert WorktreeGitHelper.git(path, "rev-parse", "HEAD") == tip
        assert WorktreeGitHelper.git(path, "status", "--porcelain") == ""
        assert WorktreeGitHelper.git(path, "rev-parse", "work/ITM-0001/built") == tip

    def test_fingerprint_names_the_whole_tree_and_leaves_the_index_alone(self, make_host: Callable[[str], AppWiring]) -> None:
        """Returns the tip tree for a clean worktree and a new tree after an edit, without staging anything."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        path, merge_base, tip = built.path, built.merge_base, built.tip
        clean = host.worktree_usecases.fingerprint("ITM-0001")
        assert clean == WorktreeGitHelper.git(path, "rev-parse", "HEAD^{tree}")
        (path / "a.txt").write_text("edited\n")
        (path / "new.txt").write_text("new\n")
        status_before = WorktreeGitHelper.git(path, "status", "--porcelain")
        edited = host.worktree_usecases.fingerprint("ITM-0001")
        assert edited != clean
        assert WorktreeGitHelper.git(path, "status", "--porcelain") == status_before == " M a.txt\n?? new.txt"

    def test_present_refuses_uncommitted_changes_and_a_missing_worktree(self, make_host: Callable[[str], AppWiring]) -> None:
        """Does not mix uncommitted work into the built state, and names a missing worktree."""
        host = make_host("alpha")
        with pytest.raises(WorktreeError, match="no integration worktree"):
            host.worktree_usecases.present("ITM-0001", None)
        with pytest.raises(WorktreeError, match="no integration worktree"):
            host.worktree_usecases.settle("ITM-0001", "x", "missing")
        with pytest.raises(WorktreeError, match="no integration worktree"):
            host.worktree_usecases.fingerprint("ITM-0001")
        built = WorktreeGitHelper.built_integration(host)
        path, merge_base, tip = built.path, built.merge_base, built.tip
        (path / "dirty.txt").write_text("x\n")
        with pytest.raises(WorktreeError, match="uncommitted"):
            host.worktree_usecases.present("ITM-0001", None)
        assert WorktreeGitHelper.git(path, "rev-parse", "HEAD") == tip
