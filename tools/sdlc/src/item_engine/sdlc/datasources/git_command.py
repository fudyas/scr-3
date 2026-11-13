import os
import signal
import subprocess
from abc import ABC
from pathlib import Path
from typing import Dict, List, Optional

from sdlc.models.errors import GitCommandError, GitTimeoutError
from sdlc.models.git import GitResult


class GitCommandRunner:
    """Runs git commands in one repository with an optional extra environment."""

    def __init__(self, repo_dir: Path, extra_env: Optional[Dict[str, str]] = None) -> None:
        """Initializes the runner.

        Args:
            repo_dir: the directory every command runs in.
            extra_env: variables added to the process environment, such as `GIT_SSH_COMMAND`.
        """
        self._repo_dir = repo_dir
        self._extra_env = dict(extra_env or {})

    @property
    def repo_dir(self) -> Path:
        """Returns the directory every command runs in."""
        return self._repo_dir

    def run(self, args: List[str], input_text: Optional[str] = None, check: bool = True,
            extra_env: Optional[Dict[str, str]] = None, timeout_seconds: Optional[float] = None) -> GitResult:
        """Returns the result of a git command.

        Steps:
            1. Start git in its own process group so child processes, such as SSH, share its fate.
            2. Wait for the command, within the time limit when one is given.
            3. On a timeout, kill the whole process group and raise, also when `check` is false.

        Args:
            args: the git arguments, without the leading `git`.
            input_text: text written to the command's standard input.
            check: whether a non-zero exit raises.
            extra_env: variables added for this command only, such as `GIT_INDEX_FILE`.
            timeout_seconds: the longest the command may run; no limit when unset.

        Returns:
            The exit code and captured output.

        Raises:
            GitCommandError: the command failed and `check` is set.
            GitTimeoutError: the command did not finish within the time limit, whatever `check` says.
        """
        environment = {**os.environ, **self._extra_env, **(extra_env or {})}
        process = subprocess.Popen(
            ["git", "--no-pager", *args],
            cwd=self._repo_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=environment,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(input_text, timeout=timeout_seconds)
        except subprocess.TimeoutExpired as timeout:
            # Kills the group so a child that holds the output pipes cannot keep the call alive
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise GitTimeoutError(f"git {args[0]} did not finish within {timeout_seconds:g} s") from timeout
        result = GitResult(returncode=process.returncode, stdout=stdout, stderr=stderr)
        if check and result.returncode != 0:
            raise GitCommandError(f"git {' '.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}")
        return result

    def run_binary(self, args: List[str], input_bytes: bytes) -> bytes:
        """Returns the raw standard output of a git command that exchanges bytes.

        Args:
            args: the git arguments, without the leading `git`.
            input_bytes: bytes written to the command's standard input.

        Returns:
            The captured standard output.

        Raises:
            GitCommandError: the command failed.
        """
        completed = subprocess.run(
            ["git", "--no-pager", *args],
            cwd=self._repo_dir,
            input=input_bytes,
            capture_output=True,
            env={**os.environ, **self._extra_env},
        )
        if completed.returncode != 0:
            raise GitCommandError(f"git {' '.join(args)} failed: {completed.stderr.decode(errors='replace').strip()}")
        return completed.stdout

    def install_tree(self, branch_ref: str, previous_commit: str, next_commit: str,
                     update_files: bool = True) -> None:
        """Updates the checkout while a prepared reference transaction protects the target branch.

        Args:
            branch_ref: the full branch reference to advance.
            previous_commit: the captured tip required by the compare-and-swap.
            next_commit: the tested merge commit to install.
            update_files: whether to update working files, or only the index for review settlement.

        Raises:
            GitCommandError: the branch changed, checkout update failed, or the reference transaction failed.
        """

        # Locks the reference before checkout changes so a failed compare-and-swap leaves files untouched
        with subprocess.Popen(["git", "--no-pager", "update-ref", "--stdin"], cwd=self._repo_dir,
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, encoding="utf-8", env={**os.environ, **self._extra_env}) as process:
            assert process.stdin is not None and process.stdout is not None
            process.stdin.write(f"start\nupdate {branch_ref} {next_commit} {previous_commit}\nprepare\n")
            process.stdin.flush()
            started = process.stdout.readline().strip()
            prepared = process.stdout.readline().strip()
            if started != "start: ok" or prepared != "prepare: ok":
                _, error = process.communicate()
                raise GitCommandError(f"cannot prepare promotion reference: {error.strip()}")
            try:
                if self.run(["symbolic-ref", "--quiet", "HEAD"]).stdout.strip() != branch_ref:
                    raise GitCommandError("checkout branch changed before installation")
                if update_files:
                    self.run(["read-tree", "-m", "-u", previous_commit, next_commit])
                else:
                    self.run(["read-tree", next_commit])
            except Exception:
                process.communicate("abort\n")
                raise
            output, error = process.communicate("commit\n")
            if process.returncode != 0 or "commit: ok" not in output:
                raise GitCommandError(f"cannot commit promotion reference: {error.strip()}")


class MainRootHelper(ABC):
    """Resolves the main checkout that owns all host-local SDLC state."""

    @staticmethod
    def resolve(start_dir: Path) -> Path:
        """Returns the main checkout root, also when called from a linked worktree.

        Args:
            start_dir: any directory inside the repository or one of its worktrees.

        Returns:
            The directory that holds the shared git common dir.

        Raises:
            GitCommandError: the directory is not inside a git repository.
        """
        result = GitCommandRunner(start_dir).run(["rev-parse", "--path-format=absolute", "--git-common-dir"])
        return Path(result.stdout.strip()).parent


class GitSshEnvironmentHelper(ABC):
    """Builds the SSH environment that authenticates ledger network operations."""

    @staticmethod
    def build(main_root: Path, key_path: str, config_path: str) -> Dict[str, str]:
        """Returns `GIT_SSH_COMMAND` for the repository key, or nothing when the key is absent.

        Args:
            main_root: the main checkout root.
            key_path: the private key path relative to the main root.
            config_path: the SSH host config path relative to the main root.

        Returns:
            The environment variables to add to network git commands.
        """
        key_file = main_root / key_path
        config_file = main_root / config_path
        if not key_file.is_file() or not config_file.is_file():
            return {}
        command = (
            f"ssh -F {config_file} -i {key_file} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
        )
        return {"GIT_SSH_COMMAND": command}
