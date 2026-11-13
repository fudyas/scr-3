import fcntl
import os
import tempfile
from contextlib import contextmanager
from typing import Dict, Iterator, List, Optional

from sdlc.datasources.git_command import GitCommandRunner
from sdlc.models.errors import GitTimeoutError, LedgerUnreachableError
from sdlc.models.git import PushOutcome

# File mode git records for every ledger file
FILE_MODE = "100644"


class GitLedgerSource:
    """Reads and writes the ledger branch through git plumbing, never checking it out."""

    def __init__(self, runner: GitCommandRunner, remote: str, branch: str, network_timeout_seconds: float) -> None:
        """Initializes the source.

        Args:
            runner: the git runner for the main checkout, carrying the SSH environment.
            remote: the remote name or repository path that holds the shared ledger.
            branch: the ledger branch name.
            network_timeout_seconds: the longest each `ls-remote`, `fetch`, and `push` may run.
        """
        self._runner = runner
        self._remote = remote
        self._branch = branch
        self._network_timeout_seconds = network_timeout_seconds

    @property
    def local_ref(self) -> str:
        """Returns the local ref that mirrors the remote ledger."""
        return f"refs/heads/{self._branch}"

    @property
    def tracking_ref(self) -> str:
        """Returns the ref that receives fetched ledger commits."""
        return f"refs/sdlc-ledger/{self._branch}"

    @contextmanager
    def exclusive(self) -> Iterator[None]:
        """Serializes sync and write operations in the main checkout.

        Yields:
            Control while the process holds the ledger lock.
        """

        # Uses a kernel lock so an interrupted command cannot leave a stranded holder
        path = self._runner.repo_dir / ".lets" / "sdlc" / "locks" / "ledger-write.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def remote_tip(self) -> Optional[str]:
        """Returns the ledger commit on the remote, or None when the branch does not exist yet.

        Raises:
            LedgerUnreachableError: the remote cannot be reached or does not answer within the time limit.
        """
        try:
            result = self._runner.run(
                ["ls-remote", "--heads", self._remote, self._branch],
                check=False, timeout_seconds=self._network_timeout_seconds,
            )
        except GitTimeoutError as timeout:
            raise self._no_answer_error() from timeout
        if result.returncode != 0:
            raise LedgerUnreachableError(
                f"ledger remote {self._remote!r} is unreachable: {result.stderr.strip()}"
            )
        for line in result.stdout.splitlines():
            sha, _, ref = line.partition("\t")
            if ref.strip() == self.local_ref:
                return sha.strip()
        return None

    def fetch(self, tip: str) -> None:
        """Fetches the given remote ledger commit into the tracking ref.

        Raises:
            LedgerUnreachableError: the fetch fails or does not finish within the time limit.
        """
        try:
            result = self._runner.run(
                ["fetch", "--quiet", "--no-tags", self._remote, f"+{self.local_ref}:{self.tracking_ref}"],
                check=False, timeout_seconds=self._network_timeout_seconds,
            )
        except GitTimeoutError as timeout:
            raise self._no_answer_error() from timeout
        if result.returncode != 0:
            raise LedgerUnreachableError(f"ledger fetch failed: {result.stderr.strip()}")
        self._runner.run(["cat-file", "-e", f"{tip}^{{commit}}"])

    def _no_answer_error(self) -> LedgerUnreachableError:
        """Returns the error for a ledger remote that did not answer within the time limit."""
        return LedgerUnreachableError(
            f"ledger remote {self._remote!r} did not answer within {self._network_timeout_seconds:g} s"
        )

    def local_tip(self) -> Optional[str]:
        """Returns the local ledger commit, or None before the first sync."""
        result = self._runner.run(["rev-parse", "--verify", "--quiet", self.local_ref], check=False)
        return result.stdout.strip() or None

    def set_local_tip(self, commit: str) -> None:
        """Points the local ledger ref at the given commit."""
        self._runner.run(["update-ref", self.local_ref, commit])

    def commit_date(self, commit: str) -> str:
        """Returns the ISO commit date of a ledger commit."""
        return self._runner.run(["show", "-s", "--format=%cI", commit]).stdout.strip()

    def read_texts(self, commit: str, paths: List[str]) -> Dict[str, Optional[str]]:
        """Returns the text of each path at the commit; a missing path maps to None.

        Args:
            commit: the ledger commit to read.
            paths: file paths inside the ledger tree.

        Returns:
            Each requested path mapped to its text or None.
        """
        if not paths:
            return {}
        request = "".join(f"{commit}:{path}\n" for path in paths).encode("utf-8")
        output = self._runner.run_binary(["cat-file", "--batch"], request)
        texts: Dict[str, Optional[str]] = {}
        position = 0

        # Reads each `<sha> <type> <size>` header and its body, or a `missing` line
        for path in paths:
            header_end = output.index(b"\n", position)
            header = output[position:header_end].decode("utf-8")
            position = header_end + 1
            if header.endswith(" missing"):
                texts[path] = None
                continue
            size = int(header.split(" ")[2])
            texts[path] = output[position:position + size].decode("utf-8")
            position += size + 1
        return texts

    def list_paths(self, commit: str, directory: str) -> List[str]:
        """Returns every file path under the directory at the commit."""
        result = self._runner.run(["ls-tree", "-r", "--name-only", commit, "--", directory], check=False)
        return [line for line in result.stdout.splitlines() if line]

    def commit_changes(self, parent: Optional[str], changes: Dict[str, Optional[str]], message: str) -> str:
        """Returns a new ledger commit that applies the changes on top of the parent.

        Steps:
            1. Load the parent tree into a temporary index (or start empty).
            2. Write each changed file as a blob; remove each path mapped to None.
            3. Write the tree and commit it with the parent.

        Args:
            parent: the commit to build on, or None for the first ledger commit.
            changes: file paths mapped to new text, or None to remove the file.
            message: the commit message.

        Returns:
            The new commit id.
        """
        with tempfile.TemporaryDirectory() as temporary_dir:
            index_env = {"GIT_INDEX_FILE": os.path.join(temporary_dir, "index")}
            if parent is not None:
                self._runner.run(["read-tree", parent], extra_env=index_env)
            for path, text in sorted(changes.items()):
                if text is None:
                    self._runner.run(["update-index", "--force-remove", "--", path], extra_env=index_env)
                    continue
                blob = self._runner.run(["hash-object", "-w", "--stdin"], input_text=text).stdout.strip()
                self._runner.run(
                    ["update-index", "--add", "--cacheinfo", f"{FILE_MODE},{blob},{path}"], extra_env=index_env
                )
            tree = self._runner.run(["write-tree"], extra_env=index_env).stdout.strip()
        parent_args = ["-p", parent] if parent is not None else []
        identity_env = {
            "GIT_AUTHOR_NAME": "sdlc", "GIT_AUTHOR_EMAIL": "sdlc@localhost",
            "GIT_COMMITTER_NAME": "sdlc", "GIT_COMMITTER_EMAIL": "sdlc@localhost",
        }
        return self._runner.run(
            ["commit-tree", tree, *parent_args, "-m", message], extra_env=identity_env
        ).stdout.strip()

    def push(self, commit: str) -> PushOutcome:
        """Pushes the commit to the remote ledger branch without force.

        Returns:
            Whether the remote accepted the commit, with git's message when it refused.

        Raises:
            LedgerUnreachableError: the remote cannot be reached at all, or the push did not finish
                within the time limit and the write can have landed.
        """
        try:
            result = self._runner.run(
                ["push", "--quiet", self._remote, f"{commit}:{self.local_ref}"],
                check=False, timeout_seconds=self._network_timeout_seconds,
            )
        except GitTimeoutError as timeout:
            raise LedgerUnreachableError(
                f"ledger push to {self._remote!r} did not finish within {self._network_timeout_seconds:g} s; "
                "the write can have landed: run `lets sdlc sync` and read the record before a repeat"
            ) from timeout
        if result.returncode == 0:
            return PushOutcome(accepted=True)

        # Separates an unreachable remote from a refused push; the tip read raises when unreachable
        self.remote_tip()
        return PushOutcome(accepted=False, detail=result.stderr.strip())
