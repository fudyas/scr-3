import json
from typing import Callable, List

import pytest
from pydantic import BaseModel, ConfigDict

from sdlc.controllers.cli import EXIT_ERROR, SdlcCliController
from sdlc.datasources.git_command import GitCommandRunner
from sdlc.models.errors import WorktreeError
from sdlc.wiring import AppWiring
from tests.sdlc.items.test_leases_and_worktrees import BuiltIntegration, WorktreeGitHelper
from tests.sdlc.items.test_review_workspace import ReviewArtifactFixture


class SettledMerge(BaseModel):
    """The built integration, the target tip that integration merged, and the first settled commit."""

    model_config = ConfigDict(frozen=True)

    built: BuiltIntegration
    target_tip: str
    commit: str


class TestArtifactPromotionHistory:
    """Covers artifact-bound promotion without weakening history and target movement guards."""

    def test_bound_pair_settlement_and_promotion_preserve_source_history(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Installs the accepted source tree with independent input and result locators intact."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        fixture = ReviewArtifactFixture(host)
        (built.path / "a.txt").write_text("accepted source fix\n")
        session = fixture.accept()
        assert session.snapshot_artifacts is not None
        digest = session.snapshot_artifacts.digest
        tree = session.snapshot_tree or ""
        commit = fixture.worktrees.settle("ITM-0001", "review", tree, digest) or ""
        assert WorktreeGitHelper.git(built.path, "rev-list", "--parents", "-n", "1", commit).split()[1:] == [built.tip]
        prepared = fixture.worktrees.prepare_promotion("ITM-0001", None, digest)
        installed = fixture.worktrees.promote("ITM-0001", prepared.promotion_commit or "", digest)
        assert WorktreeGitHelper.git(host.settings.main_root, "rev-parse", f"{installed}^{{tree}}") == tree
        context = fixture.worktrees.context("ITM-0001")
        assert context.phase == "DONE" and context.snapshot_tree == tree
        assert context.verified_artifacts == context.approved_artifacts == digest
        assert context.snapshot_artifacts == session.snapshot_artifacts and context.qa_artifacts == session.qa_artifacts

    def test_present_retains_bound_snapshot_and_clears_pair_approval_after_settlement(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Keeps verified input and result evidence when presentation reopens promotion for review."""
        host = make_host("alpha")
        WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        fixture = ReviewArtifactFixture(host)
        accepted = fixture.accept()
        assert accepted.snapshot_artifacts is not None
        digest = accepted.snapshot_artifacts.digest
        tree = accepted.snapshot_tree or ""
        fixture.worktrees.settle("ITM-0001", "review", tree, digest)
        fixture.worktrees.present("ITM-0001", None)
        reopened = fixture.worktrees.context("ITM-0001")
        assert reopened.approved_tree is None and reopened.approved_artifacts is None
        assert reopened.verified_tree == tree and reopened.verified_artifacts == digest
        assert reopened.snapshot_artifacts == accepted.snapshot_artifacts and reopened.qa_artifacts == accepted.qa_artifacts
        fixture.worktrees.approve("ITM-0001", tree, digest)
        fixture.worktrees.settle("ITM-0001", "review", tree, digest)

    @pytest.mark.parametrize("change", ["advance", "conflict", "overlap"])
    def test_bound_pair_keeps_target_and_user_file_conflict_guards(
            self, make_host: Callable[[str], AppWiring], change: str) -> None:
        """Blocks target movement and conflicts while retaining exact artifact approval and source files."""
        host = make_host("alpha")
        WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        fixture = ReviewArtifactFixture(host)
        accepted = fixture.accept()
        assert accepted.snapshot_artifacts is not None
        digest = accepted.snapshot_artifacts.digest
        fixture.worktrees.settle("ITM-0001", "review", accepted.snapshot_tree or "", digest)
        main = host.settings.main_root
        if change == "conflict":
            target = WorktreeGitHelper.commit_file(main, "a.txt", "target conflict\n")
            with pytest.raises(WorktreeError, match="promotion merge needs review"):
                fixture.worktrees.prepare_promotion("ITM-0001", None, digest)
        else:
            prepared = fixture.worktrees.prepare_promotion("ITM-0001", None, digest)
            if change == "advance":
                target = WorktreeGitHelper.commit_file(main, "later.txt", "later\n")
                error = "main checkout moved"
            else:
                target = WorktreeGitHelper.git(main, "rev-parse", "HEAD")
                (main / "a.txt").write_text("user file\n")
                error = "overlaps user changes"
            with pytest.raises(WorktreeError, match=error):
                fixture.worktrees.promote("ITM-0001", prepared.promotion_commit or "", digest)
        assert WorktreeGitHelper.git(main, "rev-parse", "HEAD") == target
        assert fixture.worktrees.context("ITM-0001").approved_artifacts == digest
        if change == "overlap":
            assert (main / "a.txt").read_text() == "user file\n"


class TestMergeParentsAcrossPresent:
    """Covers the merge parents that settle records and a later present in phase PROMOTE keeps."""

    @staticmethod
    def _parents(host: AppWiring, commit: str) -> List[str]:
        """Returns the parents of the commit in order."""
        return WorktreeGitHelper.git(host.settings.main_root, "rev-list", "--parents", "-n", "1", commit).split()[1:]

    @staticmethod
    def _settle_with_target_merge(host: AppWiring) -> SettledMerge:
        """Presents, merges a conflicting target commit into integration, settles, and returns the result."""
        built = WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)

        # The target adds the same file as the item, so a merge from the old base would conflict
        target_tip = WorktreeGitHelper.commit_file(host.settings.main_root, "a.txt", "target a\n")
        WorktreeGitHelper.git(built.path, "commit", "--quiet", "-m", "review")
        GitCommandRunner(built.path).run(["merge", "master"], check=False)
        (built.path / "a.txt").write_text("a\ntarget a\n")
        WorktreeGitHelper.git(built.path, "add", "a.txt")
        WorktreeGitHelper.git(built.path, "commit", "--quiet", "--no-edit")
        tree = WorktreeGitHelper.approve_snapshot(host)
        commit = host.worktree_usecases.settle("ITM-0001", "review", tree) or ""
        return SettledMerge(built=built, target_tip=target_tip, commit=commit)

    def test_present_again_in_promote_keeps_the_settled_merge_parents(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Gives the second settled commit the target tip as a parent so promotion reports no false conflict."""
        host = make_host("alpha")
        settled = self._settle_with_target_merge(host)
        built = settled.built
        assert settled.target_tip in self._parents(host, settled.commit)
        recorded = host.worktree_usecases.context("ITM-0001").merged_parents
        assert settled.target_tip in recorded
        assert recorded == self._parents(host, settled.commit)[1:]

        # Presents again, which drops the merge from HEAD
        host.worktree_usecases.present("ITM-0001", None)
        assert host.worktree_usecases.context("ITM-0001").phase == "SHOW"
        assert WorktreeGitHelper.git(built.path, "rev-parse", "HEAD") == settled.target_tip
        assert host.worktree_usecases.context("ITM-0001").base_commit == settled.target_tip

        # Settles again and expects the recorded parent to return
        second_tree = WorktreeGitHelper.approve_snapshot(host)
        second_commit = host.worktree_usecases.settle("ITM-0001", "review", second_tree) or ""
        second_parents = self._parents(host, second_commit)
        assert second_parents[0] == built.tip
        assert second_parents[1:] == recorded
        prepared = host.worktree_usecases.prepare_promotion("ITM-0001")
        assert prepared.promotion_system_required is False
        promotion_tree = WorktreeGitHelper.git(
            host.settings.main_root, "rev-parse", f"{prepared.promotion_commit}^{{tree}}")
        assert promotion_tree == second_tree

    def test_present_in_promote_keeps_a_target_merge_committed_after_settle(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Records a target merge that review commits after settle, so the next settle and promotion keep it."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)

        # Settles a review edit before any merge exists
        (built.path / "b.txt").write_text("b reviewed\n")
        first_tree = WorktreeGitHelper.approve_snapshot(host)
        first_commit = host.worktree_usecases.settle("ITM-0001", "review", first_tree) or ""
        assert self._parents(host, first_commit) == [built.tip]
        assert host.worktree_usecases.context("ITM-0001").merged_parents == []

        # Merges a conflicting target commit into integration after the settlement
        target_tip = WorktreeGitHelper.commit_file(host.settings.main_root, "a.txt", "target a\n")
        GitCommandRunner(built.path).run(["merge", "master"], check=False)
        (built.path / "a.txt").write_text("a\ntarget a\n")
        WorktreeGitHelper.git(built.path, "add", "a.txt")
        WorktreeGitHelper.git(built.path, "commit", "--quiet", "--no-edit")

        # Presents again, which drops the merge from HEAD but records its parents
        host.worktree_usecases.present("ITM-0001", None)
        session = host.worktree_usecases.context("ITM-0001")
        assert session.phase == "SHOW"
        assert WorktreeGitHelper.git(built.path, "rev-parse", "HEAD") == target_tip
        assert session.base_commit == target_tip
        assert target_tip in session.merged_parents

        # Settles again and expects the target tip as a parent of the settled commit
        second_tree = WorktreeGitHelper.approve_snapshot(host)
        second_commit = host.worktree_usecases.settle("ITM-0001", "review", second_tree) or ""
        second_parents = self._parents(host, second_commit)
        assert second_parents[0] == built.tip
        assert target_tip in second_parents
        assert second_parents[1:] == session.merged_parents
        prepared = host.worktree_usecases.prepare_promotion("ITM-0001")
        assert prepared.promotion_system_required is False
        promotion_tree = WorktreeGitHelper.git(
            host.settings.main_root, "rev-parse", f"{prepared.promotion_commit}^{{tree}}")
        assert promotion_tree == second_tree

    def test_present_in_promote_without_a_new_merge_keeps_the_recorded_parents(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Leaves the recorded parents unchanged when a present in phase PROMOTE finds no new merge."""
        host = make_host("alpha")
        self._settle_with_target_merge(host)
        recorded = host.worktree_usecases.context("ITM-0001").merged_parents
        assert recorded

        # Presents, snapshots, settles, and presents a second time without any new merge
        host.worktree_usecases.present("ITM-0001", None)
        assert host.worktree_usecases.context("ITM-0001").merged_parents == recorded
        tree = WorktreeGitHelper.approve_snapshot(host)
        host.worktree_usecases.settle("ITM-0001", "review", tree)
        host.worktree_usecases.present("ITM-0001", None)
        assert host.worktree_usecases.context("ITM-0001").merged_parents == recorded

    def test_snapshot_keeps_the_recorded_merge_parents(self, make_host: Callable[[str], AppWiring]) -> None:
        """Leaves the recorded parents in the review context after a present and a snapshot."""
        host = make_host("alpha")
        settled = self._settle_with_target_merge(host)

        recorded = host.worktree_usecases.context("ITM-0001").merged_parents
        assert settled.target_tip in recorded
        host.worktree_usecases.present("ITM-0001", None)
        host.worktree_usecases.snapshot("ITM-0001")
        assert host.worktree_usecases.context("ITM-0001").merged_parents == recorded


class TestRestageAfterReviewCommits:
    """Covers a present in phase SHOW or VERIFY after review committed its state and merged the target branch."""

    @staticmethod
    def _merge_target_conflict(host: AppWiring, built: BuiltIntegration) -> str:
        """Commits a review edit, merges a conflicting target commit into integration, and returns the target tip."""
        (built.path / "b.txt").write_text("b reviewed\n")
        WorktreeGitHelper.git(built.path, "add", "-A")
        WorktreeGitHelper.git(built.path, "commit", "--quiet", "-m", "review")
        WorktreeGitHelper.commit_file(host.settings.main_root, "target-only.txt", "t\n")
        target_tip = WorktreeGitHelper.commit_file(host.settings.main_root, "a.txt", "target a\n")
        GitCommandRunner(built.path).run(["merge", "master"], check=False)
        (built.path / "a.txt").write_text("a\ntarget a\n")
        WorktreeGitHelper.git(built.path, "add", "a.txt")
        WorktreeGitHelper.git(built.path, "commit", "--quiet", "--no-edit")
        return target_tip

    def test_present_in_show_restages_a_review_commit_and_a_target_merge(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Stages only the item files against the merged target tip and keeps the approval and the merge parents."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        target_tip = self._merge_target_conflict(host, built)
        tree = WorktreeGitHelper.approve_snapshot(host)

        # Presents again in phase SHOW and expects the diff base to move to the target tip
        presented = host.worktree_usecases.present("ITM-0001", None)
        session = host.worktree_usecases.context("ITM-0001")
        assert WorktreeGitHelper.git(built.path, "rev-parse", "HEAD") == target_tip
        assert session.base_commit == target_tip
        assert presented.merge_base == target_tip

        # Expects the item files as staged and nothing else
        staged = WorktreeGitHelper.git(built.path, "diff", "--cached", "--name-only").splitlines()
        assert sorted(staged) == ["a.txt", "b.txt"]
        status = WorktreeGitHelper.git(built.path, "status", "--porcelain").splitlines()
        assert all(line[1] == " " for line in status) and len(status) == 2
        assert (built.path / "b.txt").read_text() == "b reviewed\n"

        # Expects the fingerprint, the phase, and the approval to survive the reset
        assert host.worktree_usecases.fingerprint("ITM-0001") == tree
        assert session.phase == "SHOW"
        assert session.verified_tree == tree
        assert session.approved_tree == tree
        assert target_tip in session.merged_parents

        # Settles without a new approval and expects the merge parents on the settled commit
        commit = host.worktree_usecases.settle("ITM-0001", "review", tree) or ""
        parents = TestMergeParentsAcrossPresent._parents(host, commit)
        assert parents[0] == built.tip
        assert parents[1:] == session.merged_parents
        assert target_tip in parents
        prepared = host.worktree_usecases.prepare_promotion("ITM-0001")
        assert prepared.promotion_system_required is False
        promotion_tree = WorktreeGitHelper.git(
            host.settings.main_root, "rev-parse", f"{prepared.promotion_commit}^{{tree}}")
        assert promotion_tree == tree

    def test_present_in_verify_restages_and_keeps_the_snapshot(self, make_host: Callable[[str], AppWiring]) -> None:
        """Keeps phase VERIFY and the snapshot tree when the present moves the diff base."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        target_tip = self._merge_target_conflict(host, built)
        snapshot_tree = host.worktree_usecases.snapshot("ITM-0001").snapshot_tree or ""

        # Presents in phase VERIFY and expects the same snapshot and a valid verification
        host.worktree_usecases.present("ITM-0001", None)
        session = host.worktree_usecases.context("ITM-0001")
        assert WorktreeGitHelper.git(built.path, "rev-parse", "HEAD") == target_tip
        assert session.phase == "VERIFY"
        assert session.snapshot_tree == snapshot_tree
        assert host.worktree_usecases.verified("ITM-0001", snapshot_tree).verified_tree == snapshot_tree

    def test_present_in_show_restages_a_review_commit_without_a_merge(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Keeps the built base when review commits without merging the target branch."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        (built.path / "b.txt").write_text("b reviewed\n")
        WorktreeGitHelper.git(built.path, "add", "-A")
        WorktreeGitHelper.git(built.path, "commit", "--quiet", "-m", "review")
        WorktreeGitHelper.commit_file(host.settings.main_root, "main-only.txt", "m\n")

        # Presents and expects the base to stay at the built merge base
        host.worktree_usecases.present("ITM-0001", None)
        session = host.worktree_usecases.context("ITM-0001")
        assert WorktreeGitHelper.git(built.path, "rev-parse", "HEAD") == built.merge_base
        assert session.base_commit == built.merge_base
        assert session.merged_parents == []
        staged = WorktreeGitHelper.git(built.path, "diff", "--cached", "--name-only").splitlines()
        assert "b.txt" in staged
        assert not (built.path / "main-only.txt").exists()

        # Settles and expects a single parent, the built tip
        tree = WorktreeGitHelper.approve_snapshot(host)
        commit = host.worktree_usecases.settle("ITM-0001", "review", tree) or ""
        assert TestMergeParentsAcrossPresent._parents(host, commit) == [built.tip]

    def test_present_in_show_without_review_commits_changes_nothing(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Leaves HEAD and the review context unchanged when HEAD already equals the diff base."""
        host = make_host("alpha")
        built = WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        first = host.worktree_usecases.context("ITM-0001")
        host.worktree_usecases.present("ITM-0001", None)
        assert WorktreeGitHelper.git(built.path, "rev-parse", "HEAD") == built.merge_base
        assert host.worktree_usecases.context("ITM-0001") == first


class TestPromotionSessionTrailer:
    """Covers the Codex-Session trailer of the promotion merge commit."""

    SESSION_URL = "https://claude.ai/code/session_test"
    SUBJECT = "Merge work/ITM-0001/integration (ITM-0001)"

    @staticmethod
    def _settle_approved_change(host: AppWiring) -> None:
        """Presents the built change, then settles its approved snapshot."""
        WorktreeGitHelper.built_integration(host)
        host.worktree_usecases.present("ITM-0001", None)
        tree = WorktreeGitHelper.approve_snapshot(host)
        host.worktree_usecases.settle("ITM-0001", "review", tree)

    @staticmethod
    def _message(host: AppWiring, commit: str) -> str:
        """Returns the full message of the commit."""
        return WorktreeGitHelper.git(host.settings.main_root, "log", "-1", "--format=%B", commit)

    @staticmethod
    def _trailer(host: AppWiring, commit: str) -> str:
        """Returns the Codex-Session trailer value of the commit."""
        return WorktreeGitHelper.git(host.settings.main_root, "log", "-1",
                                     "--format=%(trailers:key=Codex-Session,valueonly)", commit)

    def test_promotion_merge_carries_the_session_trailer(self, make_host: Callable[[str], AppWiring]) -> None:
        """Writes the subject and the Codex-Session trailer into the promotion merge commit."""
        host = make_host("alpha")
        self._settle_approved_change(host)

        prepared = host.worktree_usecases.prepare_promotion("ITM-0001", self.SESSION_URL)
        commit = prepared.promotion_commit or ""
        assert self._message(host, commit).splitlines()[0] == self.SUBJECT
        assert self._trailer(host, commit) == self.SESSION_URL

    def test_promotion_merge_without_a_session_has_no_trailer(self, make_host: Callable[[str], AppWiring]) -> None:
        """Keeps the subject as the whole message when no session is given."""
        host = make_host("alpha")
        self._settle_approved_change(host)

        prepared = host.worktree_usecases.prepare_promotion("ITM-0001")
        commit = prepared.promotion_commit or ""
        assert self._message(host, commit) == self.SUBJECT
        assert self._trailer(host, commit) == ""

    def test_cli_passes_the_session_to_prepare_promotion(
            self, make_host: Callable[[str], AppWiring], capsys: pytest.CaptureFixture[str]) -> None:
        """Forwards --codex-session from the command line into the merge commit trailer."""
        host = make_host("alpha")
        self._settle_approved_change(host)
        cli = SdlcCliController(lambda: host)
        capsys.readouterr()

        exit_code = cli.run(["worktree", "prepare-promotion", "ITM-0001", "--codex-session", self.SESSION_URL,
                             "--json"])
        assert exit_code == 0
        commit = json.loads(capsys.readouterr().out)["promotion_commit"]
        assert self._trailer(host, commit) == self.SESSION_URL

    def test_cli_refuses_the_session_option_for_other_actions(self, make_host: Callable[[str], AppWiring]) -> None:
        """Rejects --codex-session on every action except prepare-promotion."""
        host = make_host("alpha")
        WorktreeGitHelper.built_integration(host)
        cli = SdlcCliController(lambda: host)

        assert cli.run(["worktree", "context", "ITM-0001", "--codex-session", self.SESSION_URL]) == EXIT_ERROR
