import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from sdlc.datasources.git_command import GitCommandRunner
from sdlc.datasources.review_session_source import ReviewSessionSource
from sdlc.models.artifact import ArtifactBinding
from sdlc.models.errors import SdlcError, WorktreeError
from sdlc.models.review_session import ReviewSession
from sdlc.models.worktree import PresentedChange, WorktreeInfo


# Worktree name of the item integration branch
INTEGRATION_NAME = "integration"


class WorktreeSource:
    """Owns item worktrees, immutable review revisions, and preservation of user files during promotion."""

    def __init__(self, runner: GitCommandRunner, worktrees_dir: Path, branch_prefix: str,
                 links: List[str], reviews: ReviewSessionSource, data_dirs: Optional[List[str]] = None,
                 artifact_capture: Optional[Callable[[str, str], Optional[ArtifactBinding]]] = None,
                 artifact_verify: Optional[Callable[[str, str, Optional[ArtifactBinding]], None]] = None,
                 artifact_result: Optional[Callable[[str, str, str], ArtifactBinding]] = None) -> None:
        """Initializes the source.

        Args:
            runner: the git runner for the main checkout.
            worktrees_dir: the directory that holds `<ITEM>/<NAME>` worktrees.
            branch_prefix: the prefix of every work branch, such as `work`.
            links: main-checkout entries to symlink into each worktree, such as `var` and `.lets`.
            reviews: the source that retains review ownership and selected tree hashes.
            data_dirs: link entries that the main checkout must hold, created when absent so that
                no worktree keeps a local copy of the data.
            artifact_capture: the callback that captures selected artifact inputs for a source tree.
            artifact_verify: the callback that verifies live and immutable artifact inputs.
            artifact_result: the callback that verifies the selected QA result for a source and input pair.
        """
        self._runner = runner
        self._worktrees_dir = worktrees_dir
        self._branch_prefix = branch_prefix
        self._links = links
        self._reviews = reviews
        self._data_dirs = data_dirs or []
        self._artifact_capture = artifact_capture
        self._artifact_verify = artifact_verify
        self._artifact_result = artifact_result

    def path(self, item_id: str, name: str) -> Path:
        """Returns the worktree path for the item and worktree name."""
        return self._worktrees_dir / item_id / name

    def branch(self, item_id: str, name: str) -> str:
        """Returns the work branch for the item and worktree name, such as `work/ITM-0001/BLK-0001`."""
        return f"{self._branch_prefix}/{item_id}/{name}"

    def current_branch(self) -> str:
        """Returns the branch the main checkout has checked out.

        Raises:
            WorktreeError: the main checkout is on a detached HEAD.
        """
        result = self._runner.run(["symbolic-ref", "--quiet", "--short", "HEAD"], check=False)
        if result.returncode != 0:
            raise WorktreeError("main checkout is on a detached HEAD; pass --base")
        return result.stdout.strip()

    def add(self, item_id: str, name: str, base: Optional[str]) -> WorktreeInfo:
        """Creates the worktree on its work branch, or returns the existing one.

        Args:
            item_id: the short item id.
            name: the worktree name, such as a block id or `integration`.
            base: the branch to cut the work branch from; None means the main checkout's branch.

        Returns:
            The worktree path and branch, and whether this call created it.
        """
        path = self.path(item_id, name)
        branch = self.branch(item_id, name)
        if (path / ".git").exists():
            self._link_state(path)
            return WorktreeInfo(path=path, branch=branch, created=False)

        # Reuses an existing work branch so a resumed run keeps its commits
        path.parent.mkdir(parents=True, exist_ok=True)
        branch_exists = self._runner.run(["rev-parse", "--verify", "--quiet", f"refs/heads/{branch}"],
                                         check=False).returncode == 0
        if branch_exists:
            self._runner.run(["worktree", "add", str(path), branch])
        else:
            self._runner.run(["worktree", "add", "-b", branch, str(path), base or self.current_branch()])
        self._link_state(path)
        return WorktreeInfo(path=path, branch=branch, created=True)

    def remove(self, item_id: str, name: str, delete_branch: bool) -> None:
        """Removes the worktree and, when asked, its merged work branch.

        Args:
            item_id: the short item id.
            name: the worktree name.
            delete_branch: whether to delete the work branch; git refuses an unmerged branch.

        Raises:
            WorktreeError: the worktree has uncommitted changes or the branch is not merged.
        """
        path = self.path(item_id, name)
        if path.exists():
            self._unlink_state(path)
            result = self._runner.run(["worktree", "remove", str(path)], check=False)
            if result.returncode != 0:
                self._link_state(path)
                raise WorktreeError(f"cannot remove {path}: {result.stderr.strip()}")
        if delete_branch:
            branch = self.branch(item_id, name)
            result = self._runner.run(["branch", "-d", branch], check=False)
            if result.returncode != 0 and "not found" not in result.stderr:
                raise WorktreeError(f"cannot delete {branch}: {result.stderr.strip()}")
            if name == INTEGRATION_NAME and result.returncode == 0:
                self._runner.run(["branch", "-D", self.built_branch(item_id)], check=False)
        if path.parent.exists() and not any(path.parent.iterdir()):
            path.parent.rmdir()

    def list_for_item(self, item_id: str) -> List[Path]:
        """Returns the worktree paths that exist for the item."""
        item_dir = self._worktrees_dir / item_id
        if not item_dir.exists():
            return []
        return sorted(child for child in item_dir.iterdir() if (child / ".git").exists())

    def built_branch(self, item_id: str) -> str:
        """Returns the branch that keeps the built history while the change is presented, such as `work/ITM-0001/built`."""
        return f"{self._branch_prefix}/{item_id}/built"

    def present(self, item_id: str, base: str) -> PresentedChange:
        """Shows the whole item change as staged, uncommitted changes in the integration worktree.

        Steps:
            1. Keep the built tip on the built branch, so the per-task history stays reachable.
            2. When HEAD differs from the diff base, in any phase, record the extra parents of the merges in HEAD
               before the reset, so a later settle adds them again.
            3. Move the diff base to the merge base of the target branch and HEAD, and move the integration branch
               there with a soft reset.
            4. In phase `PROMOTE`, return to phase `SHOW` and clear the approval.
            5. Leave the files and the index as they are, so git and the IDE list every item file as staged. The
               reset changes neither, so the fingerprint, the verification, and the approval stay valid.

        Args:
            item_id: the short item id.
            base: the working branch the item merges into.

        Returns:
            The merge base, the built tip, and the number of staged files; `created` is false when the change was
            already presented.

        Raises:
            WorktreeError: the integration worktree is missing or holds uncommitted changes.
        """
        worktree = self._integration_runner(item_id)
        built = self.built_branch(item_id)
        built_exists = self._runner.run(["rev-parse", "--verify", "--quiet", f"refs/heads/{built}"],
                                        check=False).returncode == 0
        if built_exists:
            tip = self._runner.run(["rev-parse", built]).stdout.strip()
            session = self._reviews.read(item_id)
            merge_base = session.base_commit if session else worktree.run(["rev-parse", "HEAD"]).stdout.strip()
            if session is None:
                self._start_review(item_id, base, merge_base, tip)
            else:
                update: Dict[str, Any] = {}
                head = worktree.run(["rev-parse", "HEAD"]).stdout.strip()
                if head != session.base_commit:
                    # Records the merges in HEAD before the soft reset drops them from the history
                    update["merged_parents"] = self._merged_parents(
                        worktree, session.built_tip, head, session.merged_parents)

                    # Moves the diff base to the merge base of the target branch and HEAD
                    merge_base = worktree.run(["merge-base", session.target_branch, head]).stdout.strip()
                    worktree.run(["reset", "--soft", merge_base])
                    update["base_commit"] = merge_base
                if session.phase == "PROMOTE":
                    update["phase"] = "SHOW"
                    update["approved_tree"] = None
                    update["approved_artifacts"] = None
                if update:
                    self._reviews.write(session.model_copy(update=update))
            return PresentedChange(merge_base=merge_base, built_tip=tip, created=False,
                                   file_count=self._staged_count(worktree))

        # Refuses to present while uncommitted work would be mixed into the built state
        if worktree.run(["status", "--porcelain"]).stdout.strip():
            raise WorktreeError(f"{self.path(item_id, INTEGRATION_NAME)} holds uncommitted changes; settle or discard them first")
        tip = worktree.run(["rev-parse", "HEAD"]).stdout.strip()
        merge_base = worktree.run(["merge-base", base, tip]).stdout.strip()
        self._runner.run(["branch", built, tip])
        worktree.run(["reset", "--soft", merge_base])
        self._start_review(item_id, base, merge_base, tip)
        return PresentedChange(merge_base=merge_base, built_tip=tip, created=True, file_count=self._staged_count(worktree))

    def settle(self, item_id: str, message: str, expected_tree: str,
               expected_artifacts: Optional[str] = None) -> Optional[str]:
        """Commits the exact approved tree on top of the built history without reading live files again.

        Steps:
            1. Require approval and a matching live worktree fingerprint.
            2. Create a commit from the approved tree with the built tip as its first parent and, as extra
               parents, the commits that merges on integration brought in and the built tip lacks. A `present`
               drops the merges from HEAD, so the parents that settle or a `present` recorded carry them.
            3. Move integration to that commit and update its index without overwriting IDE edits.
            4. Record the extra parents in the review context.

        Args:
            item_id: the short item id.
            message: the commit message of the review changes.
            expected_tree: the exact verified and approved tree.
            expected_artifacts: the exact input digest, required when artifacts are bound.

        Returns:
            The new commit, or None when the tree equals the built tree and no merge parent exists.

        Raises:
            WorktreeError: the worktree differs from the approved tree or approval is absent.
        """
        worktree = self._integration_runner(item_id)
        session = self._approved_review(item_id, expected_tree, expected_artifacts)
        previous = worktree.run(["rev-parse", "HEAD"]).stdout.strip()
        built_tree = worktree.run(["rev-parse", f"{session.built_tip}^{{tree}}"]).stdout.strip()

        # Collects the merged-in commits so promotion merges from the merged history, not the old base
        merged_parents = self._merged_parents(worktree, session.built_tip, previous, session.merged_parents)

        # Creates the commit from immutable objects so concurrent IDE edits cannot enter it
        commit: Optional[str] = None
        if expected_tree != built_tree or merged_parents:
            parent_arguments = ["-p", session.built_tip]
            for parent in merged_parents:
                parent_arguments.extend(["-p", parent])
            commit = worktree.run(["commit-tree", expected_tree, *parent_arguments, "-m", message]).stdout.strip()
        worktree.install_tree(f"refs/heads/{session.branch}", previous, commit or session.built_tip, update_files=False)
        self._reviews.write(session.model_copy(update={"phase": "PROMOTE", "merged_parents": merged_parents}))
        return commit

    @staticmethod
    def _merged_parents(worktree: GitCommandRunner, built_tip: str, previous: str, recorded: List[str]) -> List[str]:
        """Returns the parents that merges on integration brought in and the built tip does not contain.

        The method reads history only and never reads the target branch reference. A `present` drops the
        merges from HEAD, so the parents that settle or a `present` recorded carry them.

        Steps:
            1. Start the candidates with the recorded parents.
            2. Append the parents of the merge commits in `built_tip..previous`.
            3. Drop every parent that the built tip already contains.
            4. Keep only the parents that no other remaining parent or the built tip contains.

        Args:
            worktree: the integration checkout.
            built_tip: the last built commit.
            previous: the integration HEAD before settle.
            recorded: the extra parents that the review context holds from an earlier settle or present.

        Returns:
            The recorded parents, then the parents in the order that the merges list them, without duplicates.
        """

        # Reads each merge commit followed by its parents, after the recorded ones
        listing = worktree.run(["rev-list", "--merges", "--parents", f"{built_tip}..{previous}"]).stdout
        collected: List[str] = list(dict.fromkeys(recorded))
        for line in listing.splitlines():
            for parent in line.split()[1:]:
                if parent not in collected:
                    collected.append(parent)

        # Drops the parents that the built tip contains
        remaining = [
            parent for parent in collected
            if worktree.run(["merge-base", "--is-ancestor", parent, built_tip], check=False).returncode != 0
        ]
        if not remaining:
            return []

        # Keeps only the parents that no other candidate contains
        independent = set(worktree.run(["merge-base", "--independent", built_tip, *remaining]).stdout.split())
        return [parent for parent in remaining if parent in independent]

    def fingerprint(self, item_id: str) -> str:
        """Returns the tree hash of the whole integration working tree, staged or not, without touching its index.

        Raises:
            WorktreeError: the integration worktree is missing.
        """
        worktree = self._integration_runner(item_id)
        return self._fingerprint(worktree)

    @staticmethod
    def _fingerprint(worktree: GitCommandRunner) -> str:
        """Returns the full working tree hash without changing the real index.

        Args:
            worktree: the checkout whose index and working files form the snapshot.

        Returns:
            The tree hash, including tracked files that match ignore rules.
        """
        with tempfile.TemporaryDirectory() as directory:
            # Seeds from the real index so tracked ignored paths and staged additions remain tracked
            temporary_index = Path(directory) / "index"
            real_index = Path(worktree.run(["rev-parse", "--path-format=absolute", "--git-path", "index"]).stdout.strip())
            if real_index.exists():
                shutil.copyfile(real_index, temporary_index)
            index = {"GIT_INDEX_FILE": str(temporary_index)}
            worktree.run(["add", "-A"], extra_env=index)
            return worktree.run(["write-tree"], extra_env=index).stdout.strip()

    def context(self, item_id: str) -> ReviewSession:
        """Returns review ownership independently of the item or task status.

        Args:
            item_id: the short item id.

        Returns:
            The persistent workspace and review revision state.

        Raises:
            WorktreeError: presentation has not created review context.
        """
        session = self._reviews.read(item_id)
        if session is None:
            raise WorktreeError(f"no review context for {item_id}; run worktree present first")
        if session.worktree != self.path(item_id, INTEGRATION_NAME):
            raise WorktreeError("review context belongs to a different checkout")
        return session

    def snapshot(self, item_id: str) -> ReviewSession:
        """Freezes review files into a detached verification worktree and invalidates previous approval.

        Args:
            item_id: the short item id.

        Returns:
            The context with the snapshot tree, commit, and verification path.

        Raises:
            WorktreeError: context is absent or an existing verification worktree has edits.
        """
        session = self.context(item_id)
        tree = self.fingerprint(item_id)
        bound = any(value is not None for value in (session.snapshot_artifacts, session.verified_artifacts,
                                                     session.approved_artifacts, session.qa_artifacts))
        session = self._invalidate_acceptance(session)
        artifacts = self._artifact_capture(item_id, tree) if self._artifact_capture else None
        if (bound or artifacts is not None) and any(callback is None for callback in (
                self._artifact_capture, self._artifact_verify, self._artifact_result)):
            raise WorktreeError("artifact-bound review requires artifact callbacks")
        if bound and artifacts is None:
            raise WorktreeError("artifact-bound review cannot become source-only; restore artifact selection")
        commit = self._runner.run(["commit-tree", tree, "-p", session.built_tip,
                                   "-m", f"{item_id} verification snapshot"]).stdout.strip()
        path = self._detached_worktree(item_id, "verification", commit)
        return self._reviews.write(session.model_copy(update={
            "phase": "VERIFY", "snapshot_tree": tree, "snapshot_commit": commit,
            "verification_worktree": path, "verified_tree": None, "approved_tree": None,
            "snapshot_artifacts": artifacts, "verified_artifacts": None,
            "approved_artifacts": None, "qa_artifacts": None,
            "promotion_base": None, "promotion_commit": None, "promotion_worktree": None,
            "promotion_system_required": False,
        }))

    def verified(self, item_id: str, expected_tree: str,
                 expected_artifacts: Optional[str] = None) -> ReviewSession:
        """Records the tested snapshot only when both verification and integration worktrees still match it.

        Args:
            item_id: the short item id.
            expected_tree: the snapshot that passed validation and QA.
            expected_artifacts: the exact input digest, required when artifacts are bound.

        Returns:
            The context with the verified tree recorded.

        Raises:
            WorktreeError: either tree differs from the tested snapshot.
        """
        session = self.context(item_id)
        self._require_snapshot(session, expected_tree)
        self._require_tree(item_id, expected_tree)
        result = self._require_artifacts(session, expected_tree, expected_artifacts, False)
        return self._reviews.write(session.model_copy(update={"phase": "SHOW", "verified_tree": expected_tree,
                                                             "approved_tree": None,
                                                             "verified_artifacts": expected_artifacts,
                                                             "approved_artifacts": None, "qa_artifacts": result}))

    def approve(self, item_id: str, expected_tree: str,
                expected_artifacts: Optional[str] = None) -> ReviewSession:
        """Records explicit user approval of the exact verified revision.

        Args:
            item_id: the short item id.
            expected_tree: the exact verified tree selected by the user.
            expected_artifacts: the exact input digest, required when artifacts are bound.

        Returns:
            The context with approval tied to that tree.

        Raises:
            WorktreeError: verification is absent or the live tree changed.
        """
        session = self.context(item_id)
        if session.verified_tree != expected_tree:
            raise WorktreeError("expected tree has not passed verification")
        self._require_snapshot(session, expected_tree)
        self._require_tree(item_id, expected_tree)
        self._require_artifacts(session, expected_tree, expected_artifacts, True)
        return self._reviews.write(session.model_copy(update={"approved_tree": expected_tree,
                                                             "approved_artifacts": expected_artifacts}))

    def prepare_promotion(self, item_id: str, message: str,
                          expected_artifacts: Optional[str] = None) -> ReviewSession:
        """Merges approved integration into a clean detached worktree for promotion gates.

        Args:
            item_id: the short item id.
            message: the full commit message of the promotion merge.
            expected_artifacts: the exact input digest, required when artifacts are bound.

        Returns:
            The context with the captured main tip and candidate merge commit.

        Raises:
            WorktreeError: approval is absent, integration differs, or the merge has conflicts.
        """
        session = self.context(item_id)
        self._approved_review(item_id, session.approved_tree or "", expected_artifacts)
        integration_tree = self._runner.run(["rev-parse", f"{session.branch}^{{tree}}"]).stdout.strip()
        if integration_tree != session.approved_tree:
            raise WorktreeError("settle the approved tree before promotion")
        if self.current_branch() != session.target_branch:
            raise WorktreeError(f"main checkout must stay on {session.target_branch}")

        # Merges in isolation so unrelated main-checkout changes cannot block or affect the gate
        main_tip = self._runner.run(["rev-parse", "HEAD"]).stdout.strip()
        path = self._detached_worktree(item_id, "promotion", main_tip)
        promotion = GitCommandRunner(path)
        result = promotion.run(["merge", "--no-ff", "--no-edit", "-m", message, session.branch], check=False)
        if result.returncode != 0:
            promotion.run(["merge", "--abort"], check=False)
            raise WorktreeError(f"promotion merge needs review: {result.stderr.strip() or result.stdout.strip()}")
        commit = promotion.run(["rev-parse", "HEAD"]).stdout.strip()
        tree = promotion.run(["rev-parse", f"{commit}^{{tree}}"]).stdout.strip()
        return self._reviews.write(session.model_copy(update={"promotion_base": main_tip,
                                                             "promotion_commit": commit,
                                                             "promotion_worktree": path,
                                                             "promotion_system_required": tree != session.verified_tree}))

    def promote(self, item_id: str, expected_commit: str,
                expected_artifacts: Optional[str] = None) -> str:
        """Installs the tested promotion commit while preserving unrelated staged and unstaged main edits.

        Args:
            item_id: the short item id.
            expected_commit: the exact promotion commit that passed the integration gate.
            expected_artifacts: the exact input digest, required when artifacts are bound.

        Returns:
            The installed merge commit.

        Raises:
            WorktreeError: main moved, a merge is active, a user path overlaps, or either review tree changed.
        """
        session = self.context(item_id)
        self._approved_review(item_id, session.approved_tree or "", expected_artifacts)
        if session.promotion_commit != expected_commit or session.promotion_worktree is None:
            raise WorktreeError("expected commit is not the prepared promotion")
        tree = self._runner.run(["rev-parse", f"{expected_commit}^{{tree}}"]).stdout.strip()
        if self._fingerprint(GitCommandRunner(session.promotion_worktree)) != tree:
            raise WorktreeError("promotion worktree changed after the merge; repeat preparation and verification")
        current_tip = self._runner.run(["rev-parse", "HEAD"]).stdout.strip()
        if self.current_branch() != session.target_branch or current_tip != session.promotion_base:
            raise WorktreeError("main checkout moved; repeat promotion preparation and verification")
        merge_head = Path(self._runner.run(["rev-parse", "--path-format=absolute", "--git-path", "MERGE_HEAD"]).stdout.strip())
        if merge_head.exists():
            raise WorktreeError("main checkout has a merge in progress")

        # Protects exact paths and file-directory collisions, including untracked user files
        changed = self._runner.run(["diff", "--no-renames", "--name-only", "-z", current_tip, expected_commit]).stdout.split("\0")
        dirty = self._runner.run(["diff", "--name-only", "-z"]).stdout.split("\0")
        dirty += self._runner.run(["diff", "--cached", "--name-only", "-z"]).stdout.split("\0")
        dirty += self._runner.run(["ls-files", "--others", "-z"]).stdout.split("\0")
        overlaps = sorted({path for path in dirty if path and any(
            other and (path == other or path.startswith(other + "/") or other.startswith(path + "/"))
            for other in changed)})
        if overlaps:
            raise WorktreeError("promotion overlaps user changes: " + ", ".join(overlaps))

        # Carries unrelated index and working-tree entries through the two-tree update
        self._runner.install_tree(f"refs/heads/{session.target_branch}", current_tip, expected_commit)
        self._reviews.write(session.model_copy(update={"phase": "DONE"}))
        return expected_commit

    def _start_review(self, item_id: str, base: str, merge_base: str, tip: str) -> None:
        """Persists the integration path and diff base when presentation starts; a later present moves the base to the merge base after a target merge."""
        self._reviews.write(ReviewSession(item_id=item_id, worktree=self.path(item_id, INTEGRATION_NAME),
                                          branch=self.branch(item_id, INTEGRATION_NAME), target_branch=base,
                                          base_commit=merge_base, built_tip=tip))

    def _require_tree(self, item_id: str, expected_tree: str) -> None:
        """Rejects a changed review revision and clears its stale verification and approval.

        Args:
            item_id: the short item id.
            expected_tree: the revision required by the current operation.

        Raises:
            WorktreeError: the integration worktree differs from the required tree.
        """
        if self.fingerprint(item_id) != expected_tree:
            session = self.context(item_id)
            self._invalidate_acceptance(session)
            raise WorktreeError("integration worktree changed; repeat verification and obtain approval again")

    def _approved_review(self, item_id: str, expected_tree: str,
                         expected_artifacts: Optional[str] = None) -> ReviewSession:
        """Returns context only for the exact verified, approved, and current tree.

        Args:
            item_id: the short item id.
            expected_tree: the approved revision required for settlement or promotion.
            expected_artifacts: the exact input digest, required when artifacts are bound.

        Returns:
            The context for the matching revision.

        Raises:
            WorktreeError: verification or approval is absent, or the live tree changed.
        """
        session = self.context(item_id)
        if not expected_tree or session.verified_tree != expected_tree or session.approved_tree != expected_tree:
            raise WorktreeError("expected tree needs verification and explicit user approval")
        self._require_snapshot(session, expected_tree)
        self._require_tree(item_id, expected_tree)
        self._require_artifacts(session, expected_tree, expected_artifacts, True)
        if session.approved_artifacts != expected_artifacts:
            self._invalidate_acceptance(session)
            raise WorktreeError("expected artifacts need explicit user approval")
        return session

    def _invalidate_acceptance(self, session: ReviewSession) -> ReviewSession:
        """Clears source and artifact acceptance while retaining captured snapshot evidence."""
        phase = "PROMOTE" if session.phase == "PROMOTE" else "SHOW"
        return self._reviews.write(session.model_copy(update={
            "phase": phase, "verified_tree": None, "approved_tree": None,
            "verified_artifacts": None, "approved_artifacts": None, "qa_artifacts": None,
        }))

    def _require_snapshot(self, session: ReviewSession, expected_tree: str) -> None:
        """Rejects a changed immutable source snapshot and clears its acceptance.

        Args:
            session: the context that owns the verification checkout.
            expected_tree: the source tree required by the caller.

        Raises:
            WorktreeError: the snapshot is absent or its checkout changed.
        """
        try:
            if session.snapshot_tree != expected_tree or session.verification_worktree is None:
                raise WorktreeError("expected tree is not the review snapshot")
            if self._fingerprint(GitCommandRunner(session.verification_worktree)) != expected_tree:
                raise WorktreeError("verification worktree changed during validation; create a new snapshot")
        except SdlcError:
            self._invalidate_acceptance(session)
            raise

    def _require_artifacts(self, session: ReviewSession, expected_tree: str,
                           expected_artifacts: Optional[str], require_verified: bool) -> Optional[ArtifactBinding]:
        """Verifies the source and artifact pair and the selected immutable QA result.

        Args:
            session: the context that retains the captured input and pinned result.
            expected_tree: the source tree required by the caller.
            expected_artifacts: the explicit input digest, or None for an artifact-free item.
            require_verified: whether the current selected result must equal the verified result.

        Returns:
            The immutable QA result, or None for an artifact-free item.

        Raises:
            SdlcError: callbacks are missing, input changed, or the selected result changed.
        """
        try:
            binding = session.snapshot_artifacts
            if binding is None:
                if expected_artifacts is not None or any(value is not None for value in (
                        session.verified_artifacts, session.approved_artifacts, session.qa_artifacts)):
                    raise WorktreeError("artifact-bound review cannot become source-only; create a new snapshot")
                if self._artifact_verify is not None:
                    self._artifact_verify(session.item_id, expected_tree, None)
                return None

            # Requires explicit pair selection even when all Git trees still match
            if not expected_artifacts or expected_artifacts != binding.digest:
                raise WorktreeError("expected artifacts must match the review input; pass --expected-artifacts")
            if binding.item_id != session.item_id or binding.purpose != "INPUT" or binding.source_tree != expected_tree:
                raise WorktreeError("artifact input does not match the review source tree")
            if self._artifact_capture is None or self._artifact_verify is None or self._artifact_result is None:
                raise WorktreeError("artifact-bound review requires artifact callbacks")
            self._artifact_verify(session.item_id, expected_tree, binding)
            result = self._artifact_result(session.item_id, expected_tree, binding.digest)

            # Rejects unrelated results and later corrections until fresh verification and approval
            if (result.item_id != session.item_id or result.purpose != "RESULT" or
                    result.source_tree != expected_tree or result.input_digest != binding.digest):
                raise WorktreeError("QA result does not match the review source and artifact pair")
            if require_verified and (session.verified_artifacts != binding.digest or session.qa_artifacts != result):
                raise WorktreeError("QA result changed or lacks verification; repeat verification and obtain approval again")
            return result
        except SdlcError:
            self._invalidate_acceptance(session)
            raise

    def _detached_worktree(self, item_id: str, name: str, commit: str) -> Path:
        """Creates a clean detached worktree for immutable gates without changing integration files.

        Args:
            item_id: the short item id.
            name: the verification or promotion workspace name.
            commit: the exact commit to check out.

        Returns:
            The detached worktree path.

        Raises:
            WorktreeError: the previous gate worktree contains edits.
        """
        path = self.path(item_id, name)
        if (path / ".git").exists():
            previous = GitCommandRunner(path)
            if previous.run(["status", "--porcelain"]).stdout.strip():
                raise WorktreeError(f"{path} holds edits; preserve them before replacing this verification worktree")
            self._unlink_state(path)
            self._runner.run(["worktree", "remove", str(path)])
        self._runner.run(["worktree", "add", "--detach", str(path), commit])
        self._link_state(path)
        return path

    def _integration_runner(self, item_id: str) -> GitCommandRunner:
        """Returns a git runner inside the integration worktree.

        Args:
            item_id: the short item id.

        Returns:
            The runner bound to the expected integration branch and path.

        Raises:
            WorktreeError: the worktree is absent or another branch is checked out.
        """
        path = self.path(item_id, INTEGRATION_NAME)
        if not (path / ".git").exists():
            raise WorktreeError(f"no {INTEGRATION_NAME} worktree for {item_id}")
        worktree = GitCommandRunner(path)
        current = worktree.run(["symbolic-ref", "--quiet", "--short", "HEAD"], check=False)
        if current.stdout.strip() != self.branch(item_id, INTEGRATION_NAME):
            raise WorktreeError(f"{path} must stay on {self.branch(item_id, INTEGRATION_NAME)}")
        return worktree

    @staticmethod
    def _staged_count(worktree: GitCommandRunner) -> int:
        """Returns the number of files that the index holds against HEAD."""
        return len([line for line in worktree.run(["diff", "--cached", "--name-only"]).stdout.splitlines() if line])

    def _link_state(self, path: Path) -> None:
        """Symlinks each configured main-checkout entry into the worktree when it is absent there."""

        # Creates the data entries in the main checkout, so that every worktree links to it and none holds a local copy
        for entry in self._data_dirs:
            (self._runner.repo_dir / entry).mkdir(parents=True, exist_ok=True)

        for entry in self._links:
            source = self._runner.repo_dir / entry
            target = path / entry
            if source.exists() and not target.exists() and not target.is_symlink():
                target.symlink_to(source)

    def _unlink_state(self, path: Path) -> None:
        """Removes the state symlinks so `git worktree remove` sees a clean tree."""
        for entry in self._links:
            target = path / entry
            if target.is_symlink():
                target.unlink()
