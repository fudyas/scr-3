import json
import hashlib
import re
import shlex
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional

import pytest

from sdlc.datasources.git_command import GitCommandRunner
from sdlc.datasources.review_session_source import ReviewSessionSource
from sdlc.datasources.worktree_source import WorktreeSource
from sdlc.controllers.cli import EXIT_ERROR, SdlcCliController
from sdlc.models.artifact import ArtifactBinding
from sdlc.models.errors import GitCommandError, SdlcError, WorktreeError
from sdlc.models.git import GitResult
from sdlc.models.item import ItemKind, ItemStatus, TaskStatus
from sdlc.models.review_session import ReviewSession
from sdlc.usecases.worktree_usecases import WorktreeUsecases
from sdlc.wiring import AppWiring
from tests.sdlc.items.test_leases_and_worktrees import WorktreeGitHelper


class ReviewArtifactFixture:
    """Supplies file-backed artifact callbacks for review lifecycle unit tests."""

    def __init__(self, host: AppWiring) -> None:
        """Creates ignored live files and connects test callbacks to the worktree source."""
        self.root = host.settings.main_root / ".lets" / "review-artifacts"
        self.root.mkdir(parents=True)
        self.live = self.root / "input.bin"
        self.live.write_bytes(b"selected input\x00\xff")
        self.live.chmod(0o640)
        self.input: Optional[ArtifactBinding] = None
        self.result: Optional[ArtifactBinding] = None
        self.selected = True
        self.source = WorktreeSource(
            GitCommandRunner(host.settings.main_root), host.settings.worktrees_dir,
            host.settings.work_branch_prefix, host.settings.worktree_links,
            ReviewSessionSource(host.settings.logs_dir), host.settings.worktree_data_dirs,
            self.capture, self.verify, self.result_for,
        )
        self.worktrees = WorktreeUsecases(self.source, host.settings.item_prefix)

    def capture(self, item_id: str, tree: str) -> Optional[ArtifactBinding]:
        """Captures selected bytes into a separate immutable test input bundle."""
        if not self.selected:
            return None
        self.input = self._binding(item_id, tree, "INPUT", self.live.read_bytes())
        return self.input

    def verify(self, item_id: str, tree: str, binding: Optional[ArtifactBinding]) -> None:
        """Rejects missing selections and changed live or immutable test input files."""
        if binding is None:
            if self.selected:
                raise SdlcError("selected artifacts cannot become source-only")
            return
        if binding != self.input or binding.item_id != item_id or binding.source_tree != tree:
            raise SdlcError("selected artifact input changed")
        path = binding.snapshot_path / "payload"
        if not path.exists() or not self.live.exists() or path.read_bytes() != self.live.read_bytes():
            raise SdlcError("artifact input bytes changed or missing")
        if path.stat().st_mode & 0o7777 != self.live.stat().st_mode & 0o7777:
            raise SdlcError("artifact input mode changed")

    def publish_result(self, tree: str, payload: bytes = b"QA report") -> ArtifactBinding:
        """Publishes a separate test result bound to the current source and input pair."""
        assert self.input is not None
        self.result = self._binding(self.input.item_id, tree, "RESULT", payload, self.input.digest)
        return self.result

    def result_for(self, item_id: str, tree: str, digest: str) -> ArtifactBinding:
        """Returns the selected test result only for its exact source and input pair."""
        result = self.result
        if result is None:
            raise SdlcError("matching QA result missing")
        if result.item_id != item_id or result.source_tree != tree or result.input_digest != digest:
            raise SdlcError("QA result pair mismatch")
        path = result.snapshot_path / "payload"
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != result.digest:
            raise SdlcError("QA result bytes changed or missing")
        return result

    def _binding(self, item_id: str, tree: str, purpose: str, payload: bytes,
                 input_digest: Optional[str] = None) -> ArtifactBinding:
        """Stores payload separately and returns the test bundle locator."""
        digest = hashlib.sha256(payload).hexdigest()
        directory = self.root / "snapshots" / digest
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "payload").write_bytes(payload)
        (directory / "payload").chmod(0o640)
        return ArtifactBinding(item_id=item_id, purpose=purpose, stage="qa" if purpose == "RESULT" else "implementation",
                               digest=digest, ledger_path=f"artifacts/bundles/{digest}.json", snapshot_path=directory,
                               source_tree=tree, input_digest=input_digest)

    def accept(self) -> ReviewSession:
        """Captures a snapshot and records verification and approval with a separate test QA result."""
        snapshot = self.worktrees.snapshot("ITM-0001")
        assert snapshot.snapshot_artifacts is not None
        tree = snapshot.snapshot_tree or ""
        digest = snapshot.snapshot_artifacts.digest
        self.publish_result(tree)
        self.worktrees.verified("ITM-0001", tree, digest)
        return self.worktrees.approve("ITM-0001", tree, digest)

    def operation(self, operation: str, session: ReviewSession, digest: Optional[str]) -> None:
        """Calls a selected acceptance operation with an explicit artifact digest."""
        tree = session.snapshot_tree or ""
        if operation == "verified":
            self.worktrees.verified("ITM-0001", tree, digest)
        elif operation == "approve":
            self.worktrees.approve("ITM-0001", tree, digest)
        elif operation == "settle":
            self.worktrees.settle("ITM-0001", "review", tree, digest)
        elif operation == "prepare":
            self.worktrees.prepare_promotion("ITM-0001", None, digest)
        elif operation == "promote":
            self.worktrees.promote("ITM-0001", session.promotion_commit or "", digest)
        else:
            raise AssertionError(operation)


class TestArtifactReviewBinding:
    """Covers exact source, ignored artifact input, and immutable QA result acceptance."""

    @staticmethod
    def _fixture(host: AppWiring) -> ReviewArtifactFixture:
        """Builds a presented integration checkout with file-backed artifact callbacks."""
        WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        return ReviewArtifactFixture(host)

    @staticmethod
    def _assert_invalidated(fixture: ReviewArtifactFixture) -> None:
        """Requires all acceptance fields to clear while captured input evidence stays available."""
        context = fixture.worktrees.context("ITM-0001")
        assert context.snapshot_artifacts is not None
        assert context.verified_tree is None and context.approved_tree is None
        assert context.verified_artifacts is None and context.approved_artifacts is None
        assert context.qa_artifacts is None

    @pytest.mark.parametrize("operation", ["verified", "approve", "settle", "prepare", "promote"])
    @pytest.mark.parametrize("location", ["live", "immutable", "missing", "mode"])
    def test_ignored_artifact_changes_invalidate_every_acceptance_guard(
            self, make_host: Callable[[str], AppWiring], operation: str, location: str) -> None:
        """Rejects artifact changes despite an unchanged Git tree and preserves staged source files."""
        host = make_host("alpha")
        fixture = self._fixture(host)
        session = fixture.accept()
        binding = session.snapshot_artifacts
        assert binding is not None
        if operation in ("prepare", "promote"):
            fixture.worktrees.settle("ITM-0001", "review", session.snapshot_tree or "", binding.digest)
        if operation == "promote":
            session = fixture.worktrees.prepare_promotion("ITM-0001", None, binding.digest)
        before = WorktreeGitHelper.git(session.worktree, "status", "--porcelain")
        path = fixture.live if location == "live" else binding.snapshot_path / "payload"
        if location == "missing":
            path.unlink()
        elif location == "mode":
            path.chmod(0o600)
        else:
            path.write_bytes(b"changed artifact")
        assert fixture.worktrees.fingerprint("ITM-0001") == session.snapshot_tree
        with pytest.raises(SdlcError, match="artifact input"):
            fixture.operation(operation, session, binding.digest)
        self._assert_invalidated(fixture)
        assert WorktreeGitHelper.git(session.worktree, "status", "--porcelain") == before

    @pytest.mark.parametrize("operation", ["verified", "approve", "settle", "prepare", "promote"])
    @pytest.mark.parametrize("digest", [None, "", "0" * 64])
    def test_artifact_bound_calls_require_explicit_exact_digest(
            self, make_host: Callable[[str], AppWiring], operation: str, digest: Optional[str]) -> None:
        """Prevents a missing, empty, or wrong digest from downgrading a bound review."""
        fixture = self._fixture(make_host("alpha"))
        session = fixture.accept()
        with pytest.raises(WorktreeError, match="expected artifacts"):
            fixture.operation(operation, session, digest)
        self._assert_invalidated(fixture)

    @pytest.mark.parametrize("callback", ["_artifact_capture", "_artifact_verify", "_artifact_result"])
    def test_missing_callbacks_cannot_accept_bound_context(
            self, make_host: Callable[[str], AppWiring], callback: str, monkeypatch: pytest.MonkeyPatch) -> None:
        """Clears old acceptance when a restarted bound context lacks any required callback."""
        fixture = self._fixture(make_host("alpha"))
        session = fixture.accept()
        assert session.snapshot_artifacts is not None
        monkeypatch.setattr(fixture.source, callback, None)
        with pytest.raises(WorktreeError, match="requires artifact callbacks"):
            fixture.worktrees.approve("ITM-0001", session.snapshot_tree or "", session.snapshot_artifacts.digest)
        self._assert_invalidated(fixture)

    def test_verification_requires_a_separate_exact_pair_qa_result(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Pins the exact QA result without adding result bytes to the source or input selection."""
        fixture = self._fixture(make_host("alpha"))
        snapshot = fixture.worktrees.snapshot("ITM-0001")
        binding = snapshot.snapshot_artifacts
        assert binding is not None
        tree = snapshot.snapshot_tree or ""
        with pytest.raises(SdlcError, match="matching QA result missing"):
            fixture.worktrees.verified("ITM-0001", tree, binding.digest)
        result = fixture.publish_result(tree)
        verified = fixture.worktrees.verified("ITM-0001", tree, binding.digest)
        assert verified.qa_artifacts == result and verified.verified_artifacts == binding.digest
        assert verified.snapshot_artifacts == binding and fixture.input == binding
        assert fixture.worktrees.fingerprint("ITM-0001") == tree

    @pytest.mark.parametrize("operation", ["approve", "settle", "prepare", "promote"])
    @pytest.mark.parametrize("mutation", ["new-result", "tamper", "missing"])
    def test_selected_result_changes_require_new_verification_and_approval(
            self, make_host: Callable[[str], AppWiring], operation: str, mutation: str) -> None:
        """Rejects later selected QA reports and damaged pinned result files at every later guard."""
        fixture = self._fixture(make_host("alpha"))
        session = fixture.accept()
        assert session.snapshot_artifacts is not None and session.qa_artifacts is not None
        digest = session.snapshot_artifacts.digest
        if mutation == "new-result":
            fixture.publish_result(session.snapshot_tree or "", b"corrected QA report")
        elif mutation == "tamper":
            (session.qa_artifacts.snapshot_path / "payload").write_bytes(b"tampered report")
        else:
            (session.qa_artifacts.snapshot_path / "payload").unlink()
        with pytest.raises(SdlcError, match="QA result"):
            fixture.operation(operation, session, digest)
        self._assert_invalidated(fixture)

    def test_backend_selection_blocks_source_only_downgrade(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Rejects source-only context when the backend discovers selected artifact history."""
        fixture = self._fixture(make_host("alpha"))
        fixture.selected = False
        snapshot = fixture.worktrees.snapshot("ITM-0001")
        fixture.selected = True
        with pytest.raises(SdlcError, match="cannot become source-only"):
            fixture.worktrees.verified("ITM-0001", snapshot.snapshot_tree or "")
        assert fixture.worktrees.context("ITM-0001").verified_tree is None

    @pytest.mark.parametrize("mutation", ["missing-capture", "missing-verify", "missing-result", "no-selection", "capture-error"])
    def test_failed_recapture_clears_acceptance_without_discarding_old_evidence(
            self, make_host: Callable[[str], AppWiring], mutation: str, monkeypatch: pytest.MonkeyPatch) -> None:
        """Rejects snapshot downgrade and backend failures while retaining the previous artifact locator."""
        fixture = self._fixture(make_host("alpha"))
        accepted = fixture.accept()
        if mutation.startswith("missing-"):
            monkeypatch.setattr(fixture.source, "_artifact_" + mutation.removeprefix("missing-"), None)
        elif mutation == "no-selection":
            fixture.selected = False
        else:
            fixture.live.unlink()

            def failed_capture(item_id: str, tree: str) -> Optional[ArtifactBinding]:
                """Simulates a backend that rejects the missing selected managed file."""
                raise SdlcError("selected artifact file missing")

            monkeypatch.setattr(fixture.source, "_artifact_capture", failed_capture)
        with pytest.raises(SdlcError):
            fixture.worktrees.snapshot("ITM-0001")
        self._assert_invalidated(fixture)
        assert fixture.worktrees.context("ITM-0001").snapshot_artifacts == accepted.snapshot_artifacts

    def test_source_snapshot_damage_clears_artifact_acceptance(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Clears both accepted digests when the detached source snapshot changes after approval."""
        fixture = self._fixture(make_host("alpha"))
        accepted = fixture.accept()
        assert accepted.verification_worktree is not None and accepted.snapshot_artifacts is not None
        (accepted.verification_worktree / "a.txt").write_text("changed source snapshot\n")
        with pytest.raises(WorktreeError, match="verification worktree changed"):
            fixture.worktrees.settle("ITM-0001", "review", accepted.snapshot_tree or "",
                                      accepted.snapshot_artifacts.digest)
        self._assert_invalidated(fixture)

    def test_source_only_context_restart_preserves_old_positional_calls(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Loads an old context without artifact fields and completes the source-only promotion flow."""
        host = make_host("alpha")
        WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        snapshot = host.worktree_usecases.snapshot("ITM-0001")
        context_path = host.settings.logs_dir / "ITM-0001" / "review-context.json"
        document = json.loads(context_path.read_text())
        for name in ("snapshot_artifacts", "verified_artifacts", "approved_artifacts", "qa_artifacts"):
            document.pop(name)
        context_path.write_text(json.dumps(document))
        resumed = AppWiring(host.settings)
        tree = snapshot.snapshot_tree or ""
        resumed.worktree_usecases.verified("ITM-0001", tree)
        resumed.worktree_usecases.approve("ITM-0001", tree)
        resumed.worktree_usecases.settle("ITM-0001", "review", tree)
        prepared = resumed.worktree_usecases.prepare_promotion("ITM-0001")
        resumed.worktree_usecases.promote("ITM-0001", prepared.promotion_commit or "")
        assert resumed.worktree_usecases.context("ITM-0001").phase == "DONE"


class TestReviewWorkspace:
    """Covers persistent review ownership and verification of exact integration revisions."""

    def test_failed_review_keeps_workspace_ownership_after_status_changes(
            self, make_host: Callable[[str], AppWiring], plan_text: str) -> None:
        """Restores review context for failed validation and QA without rebuilding block worktrees."""
        host = make_host("alpha")
        item = host.item_usecases.mint(ItemKind.TASK, "LEDGER-CORE-TOOLS", "idea", "description", [], [])
        host.plan_usecases.edit(item.short_id).write_text(plan_text)
        host.plan_usecases.approve(item.short_id)
        host.schedule_usecases.schedule(item.short_id, None)
        host.item_usecases.set_status(item.short_id, ItemStatus.IN_PROGRESS, False)
        host.plan_usecases.set_task_status(item.short_id, TaskStatus.IN_PROGRESS, ["all"])
        host.plan_usecases.set_task_status(item.short_id, TaskStatus.VALIDATED, ["all"])
        built = WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present(item.short_id, None)
        for status in [ItemStatus.TESTING, ItemStatus.IN_PROGRESS]:
            host.item_usecases.set_status(item.short_id, status, False)
            resumed = AppWiring(host.settings)
            assert resumed.worktree_usecases.context(item.short_id).worktree == built.path
            assert resumed.worktree_usecases.context(item.short_id).phase == "SHOW"

    def test_branch_switch_blocks_review_operations(self, make_host: Callable[[str], AppWiring]) -> None:
        """Rejects a detached integration checkout instead of editing or verifying the wrong branch."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        WorktreeGitHelper.git(built.path, "checkout", "--detach")
        with pytest.raises(WorktreeError, match="must stay on work/ITM-0001/integration"):
            host.worktree_usecases.fingerprint("ITM-0001")

    def test_context_and_diff_base_survive_session_restart_and_main_changes(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Keeps the integration path and captured base after the main branch advances."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        (built.path / "a.txt").write_text("IDE fix\n")
        WorktreeGitHelper.commit_file(host.settings.main_root, "main-only.txt", "main\n")
        resumed = AppWiring(host.settings)
        context = resumed.worktree_usecases.context("ITM-0001")
        assert context.worktree == built.path and context.branch == "work/ITM-0001/integration"
        assert context.base_commit == built.merge_base and context.target_branch == "master"
        assert resumed.worktree_usecases.present("ITM-0001", None).merge_base == built.merge_base
        assert (built.path / "a.txt").read_text() == "IDE fix\n"

    def test_failed_promotion_restores_complete_ide_diff_without_losing_edits(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Reopens SHOW with the entire item staged and late IDE edits still unstaged."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        tree = WorktreeGitHelper.approve_snapshot(host)
        host.worktree_usecases.settle("ITM-0001", "review", tree)
        (built.path / "a.txt").write_text("manual fix after promotion halt\n")
        with pytest.raises(WorktreeError, match="changed"):
            host.worktree_usecases.prepare_promotion("ITM-0001")
        host.worktree_usecases.present("ITM-0001", None)
        assert WorktreeGitHelper.git(built.path, "rev-parse", "HEAD") == built.merge_base
        assert WorktreeGitHelper.git(built.path, "status", "--porcelain").splitlines() == ["AM a.txt", "A  b.txt"]
        assert host.worktree_usecases.context("ITM-0001").approved_tree is None
        assert (built.path / "a.txt").read_text() == "manual fix after promotion halt\n"

    def test_fingerprint_retains_tracked_ignored_files_and_staged_new_files(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Detects edits to tracked ignore matches without changing the real index."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        WorktreeGitHelper.commit_file(built.path, ".gitignore", "/.lets\n/.codex/worktrees\n/var\na.txt\nnew.py\n")
        host.worktree_usecases.present("ITM-0001", None)
        before = host.worktree_usecases.fingerprint("ITM-0001")
        (built.path / "a.txt").write_text("tracked ignored edit\n")
        (built.path / "new.py").write_text("value = 1\n")
        WorktreeGitHelper.git(built.path, "add", "-f", "new.py")
        index_before = WorktreeGitHelper.git(built.path, "write-tree")
        after = host.worktree_usecases.fingerprint("ITM-0001")
        assert after != before and WorktreeGitHelper.git(built.path, "write-tree") == index_before
        assert WorktreeGitHelper.git(built.path, "show", f"{after}:a.txt") == "tracked ignored edit"
        assert WorktreeGitHelper.git(built.path, "show", f"{after}:new.py") == "value = 1"

    def test_snapshot_includes_untracked_files_and_deletions_in_gate_diff(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Includes new Python files and deletions without staging live IDE edits."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        (built.path / "new_module.py").write_text("value = 1\n")
        (built.path / "a.txt").unlink()
        before = WorktreeGitHelper.git(built.path, "status", "--porcelain")
        snapshot = host.worktree_usecases.snapshot("ITM-0001")
        assert snapshot.verification_worktree is not None
        assert (snapshot.verification_worktree / "new_module.py").read_text() == "value = 1\n"
        assert not (snapshot.verification_worktree / "a.txt").exists()
        assert "new_module.py" in WorktreeGitHelper.git(snapshot.verification_worktree, "diff", "--name-only",
                                                        "--diff-filter=ACMR", snapshot.base_commit, "HEAD")
        assert WorktreeGitHelper.git(built.path, "status", "--porcelain") == before

    @pytest.mark.parametrize("edit_location", ["integration", "verification"])
    def test_edits_during_verification_reject_pass(
            self, make_host: Callable[[str], AppWiring], edit_location: str) -> None:
        """Refuses to label an edited worktree as the snapshot that passed gates."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        snapshot = host.worktree_usecases.snapshot("ITM-0001")
        location = built.path if edit_location == "integration" else snapshot.verification_worktree
        assert location is not None
        (location / "a.txt").write_text("edit during QA\n")
        with pytest.raises(WorktreeError, match="changed"):
            host.worktree_usecases.verified("ITM-0001", snapshot.snapshot_tree or "")
        assert host.worktree_usecases.context("ITM-0001").verified_tree is None

    def test_edits_after_approval_require_new_verification_and_approval(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Leaves live edits and staged presentation intact when settlement rejects a stale approval."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        tree = WorktreeGitHelper.approve_snapshot(host)
        (built.path / "a.txt").write_text("late IDE edit\n")
        with pytest.raises(WorktreeError, match="obtain approval again"):
            host.worktree_usecases.settle("ITM-0001", "review", tree)
        assert WorktreeGitHelper.git(built.path, "rev-parse", "HEAD") == built.merge_base
        assert (built.path / "a.txt").read_text() == "late IDE edit\n"
        assert host.worktree_usecases.context("ITM-0001").approved_tree is None

    def test_edit_between_settlement_check_and_commit_stays_outside_approved_commit(
            self, make_host: Callable[[str], AppWiring], monkeypatch: pytest.MonkeyPatch) -> None:
        """Commits immutable approved objects while a concurrent IDE edit remains uncommitted."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        (built.path / "a.txt").write_text("approved fix\n")
        tree = WorktreeGitHelper.approve_snapshot(host)
        original = GitCommandRunner.run

        def edit_then_run(runner: GitCommandRunner, args: List[str], input_text: Optional[str] = None,
                          check: bool = True, extra_env: Optional[Dict[str, str]] = None,
                          timeout_seconds: Optional[float] = None) -> GitResult:
            """Injects a live edit immediately before settlement creates its commit."""
            if args[0] == "commit-tree" and runner.repo_dir == built.path:
                (built.path / "a.txt").write_text("concurrent IDE edit\n")
            return original(runner, args, input_text, check, extra_env, timeout_seconds)

        monkeypatch.setattr(GitCommandRunner, "run", edit_then_run)
        commit = host.worktree_usecases.settle("ITM-0001", "review", tree)
        assert WorktreeGitHelper.git(built.path, "rev-parse", f"{commit}^{{tree}}") == tree
        assert WorktreeGitHelper.git(built.path, "show", "HEAD:a.txt") == "approved fix"
        assert (built.path / "a.txt").read_text() == "concurrent IDE edit\n"
        with pytest.raises(WorktreeError, match="changed"):
            host.worktree_usecases.prepare_promotion("ITM-0001")


class TestReviewPromotion:
    """Covers isolated promotion gates and preservation of user changes in the main checkout."""

    def test_failed_reference_compare_and_swap_leaves_checkout_unchanged(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Rejects a stale target before any checkout update begins."""
        host = make_host("alpha")
        main = host.settings.main_root
        previous = WorktreeGitHelper.git(main, "rev-parse", "HEAD")
        next_commit = WorktreeGitHelper.commit_file(main, "later.txt", "later\n")
        (main / "README.md").write_text("user edit\n")
        runner = GitCommandRunner(main)
        with pytest.raises(GitCommandError, match="cannot prepare"):
            runner.install_tree("refs/heads/master", previous, next_commit)
        assert WorktreeGitHelper.git(main, "rev-parse", "HEAD") == next_commit
        assert (main / "README.md").read_text() == "user edit\n"

    def test_promotion_preserves_unrelated_staged_unstaged_and_untracked_changes(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Installs integration while retaining both index and worktree versions of unrelated user files."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        tree = WorktreeGitHelper.approve_snapshot(host)
        host.worktree_usecases.settle("ITM-0001", "review", tree)
        main = host.settings.main_root
        (main / "README.md").write_text("staged user edit\n")
        WorktreeGitHelper.git(main, "add", "README.md")
        (main / "README.md").write_text("unstaged user edit\n")
        (main / "notes.txt").write_text("untracked user file\n")
        before = WorktreeGitHelper.git(main, "diff", "--cached")
        promotion = host.worktree_usecases.prepare_promotion("ITM-0001")
        assert promotion.promotion_worktree is not None
        assert (promotion.promotion_worktree / "README.md").read_text() == "seed\n"
        commit = host.worktree_usecases.promote("ITM-0001", promotion.promotion_commit or "")
        assert WorktreeGitHelper.git(main, "rev-parse", "HEAD") == commit
        assert WorktreeGitHelper.git(main, "diff", "--cached") == before
        assert WorktreeGitHelper.git(main, "show", ":README.md") == "staged user edit"
        assert (main / "README.md").read_text() == "unstaged user edit\n"
        assert (main / "notes.txt").read_text() == "untracked user file\n"
        assert (main / "a.txt").read_text() == "a\n"
        assert host.worktree_usecases.context("ITM-0001").phase == "DONE"

    def test_settle_keeps_a_target_merge_so_promotion_merges_cleanly(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Gives the settled commit the merged target tip as a parent so promotion reports no false conflict."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)

        # The target adds the same file as the item, so a merge from the old base would conflict
        target_tip = WorktreeGitHelper.commit_file(host.settings.main_root, "a.txt", "target a\n")
        WorktreeGitHelper.git(built.path, "commit", "--quiet", "-m", "review")
        merge = GitCommandRunner(built.path).run(["merge", "master"], check=False)
        assert merge.returncode != 0
        (built.path / "a.txt").write_text("a\ntarget a\n")
        WorktreeGitHelper.git(built.path, "add", "a.txt")
        WorktreeGitHelper.git(built.path, "commit", "--quiet", "--no-edit")
        tree = WorktreeGitHelper.approve_snapshot(host)

        commit = host.worktree_usecases.settle("ITM-0001", "review", tree)
        parents = WorktreeGitHelper.git(built.path, "rev-list", "--parents", "-n", "1", commit or "").split()[1:]
        assert parents[0] == built.tip
        assert target_tip in parents
        prepared = host.worktree_usecases.prepare_promotion("ITM-0001")
        assert prepared.promotion_system_required is False
        promotion_tree = WorktreeGitHelper.git(
            host.settings.main_root, "rev-parse", f"{prepared.promotion_commit}^{{tree}}")
        assert promotion_tree == tree

    def test_settle_without_a_merge_keeps_one_parent(self, make_host: Callable[[str], AppWiring]) -> None:
        """Keeps the built tip as the only parent when the target moved but integration never merged it."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        WorktreeGitHelper.git(built.path, "commit", "--quiet", "-m", "review")
        (built.path / "a.txt").write_text("a changed\n")
        WorktreeGitHelper.commit_file(host.settings.main_root, "other-item.txt", "other\n")
        tree = WorktreeGitHelper.approve_snapshot(host)

        commit = host.worktree_usecases.settle("ITM-0001", "review", tree)
        parents = WorktreeGitHelper.git(built.path, "rev-list", "--parents", "-n", "1", commit or "").split()[1:]
        assert parents == [built.tip]

    def test_main_advance_rejects_stale_promotion(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Requires a fresh merge and gate after another commit changes the main tip."""
        host = make_host("alpha")
        WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        tree = WorktreeGitHelper.approve_snapshot(host)
        host.worktree_usecases.settle("ITM-0001", "review", tree)
        prepared = host.worktree_usecases.prepare_promotion("ITM-0001")
        main = host.settings.main_root
        latest = WorktreeGitHelper.commit_file(main, "later.txt", "later\n")
        with pytest.raises(WorktreeError, match="main checkout moved"):
            host.worktree_usecases.promote("ITM-0001", prepared.promotion_commit or "")
        assert WorktreeGitHelper.git(main, "rev-parse", "HEAD") == latest

    def test_overlapping_untracked_file_blocks_promotion_without_overwrite(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Names overlapping user files and leaves both main HEAD and file contents untouched."""
        host = make_host("alpha")
        WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        tree = WorktreeGitHelper.approve_snapshot(host)
        host.worktree_usecases.settle("ITM-0001", "review", tree)
        prepared = host.worktree_usecases.prepare_promotion("ITM-0001")
        main = host.settings.main_root
        before = WorktreeGitHelper.git(main, "rev-parse", "HEAD")
        (main / "a.txt").write_text("user file\n")
        with pytest.raises(WorktreeError, match="overlaps user changes: a.txt"):
            host.worktree_usecases.promote("ITM-0001", prepared.promotion_commit or "")
        assert WorktreeGitHelper.git(main, "rev-parse", "HEAD") == before
        assert (main / "a.txt").read_text() == "user file\n"


class TestReviewWorkspaceCli:
    """Covers revision guards and workspace context through the actual command interface."""

    def test_exact_revision_flow_and_missing_approval(
            self, make_host: Callable[[str], AppWiring], capsys: pytest.CaptureFixture) -> None:
        """Requires verification and approval before settlement and exposes the exact workspace as JSON."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        cli = SdlcCliController(lambda: host)
        assert cli.run(["worktree", "present", "ITM-0001"]) == 0
        capsys.readouterr()
        assert cli.run(["worktree", "snapshot", "ITM-0001", "--json"]) == 0
        context = json.loads(capsys.readouterr().out)
        tree = context["snapshot_tree"]
        assert context["worktree"] == str(built.path)
        assert context["base_commit"] == built.merge_base
        assert cli.run(["worktree", "settle", "ITM-0001"]) == EXIT_ERROR
        assert "needs --expected-tree" in capsys.readouterr().err
        assert cli.run(["worktree", "approve", "ITM-0001", "--expected-tree", tree]) == EXIT_ERROR
        assert "has not passed verification" in capsys.readouterr().err
        assert cli.run(["worktree", "verified", "ITM-0001", "--expected-tree", tree]) == 0
        assert cli.run(["worktree", "settle", "ITM-0001", "--expected-tree", tree]) == EXIT_ERROR
        assert "explicit user approval" in capsys.readouterr().err
        assert cli.run(["worktree", "approve", "ITM-0001", "--expected-tree", tree]) == 0
        assert cli.run(["worktree", "settle", "ITM-0001", "--expected-tree", tree]) == 0

