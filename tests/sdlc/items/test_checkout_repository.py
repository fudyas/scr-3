import subprocess
from pathlib import Path

from sdlc.datasources.git_command import GitCommandRunner
from sdlc.repositories.checkout_repository import CheckoutRepository


class TestCheckoutRepository:
    """Covers the changed paths of a real git checkout."""

    @staticmethod
    def git(repo_dir: Path, *args: str) -> str:
        """Runs a git command in the repository and returns its output."""
        completed = subprocess.run(["git", *args], cwd=repo_dir, capture_output=True, text=True, check=True)
        return completed.stdout.strip()

    @staticmethod
    def init(repo_dir: Path) -> None:
        """Creates a repository with a test identity."""
        TestCheckoutRepository.git(repo_dir, "init", "--quiet", "-b", "master")
        TestCheckoutRepository.git(repo_dir, "config", "user.email", "test@example.com")
        TestCheckoutRepository.git(repo_dir, "config", "user.name", "test")

    @staticmethod
    def commit(repo_dir: Path, message: str) -> str:
        """Commits every change in the repository and returns the new commit id."""
        TestCheckoutRepository.git(repo_dir, "add", "-A")
        TestCheckoutRepository.git(repo_dir, "commit", "--quiet", "-m", message)
        return TestCheckoutRepository.git(repo_dir, "rev-parse", "HEAD")

    def test_changed_paths_between_two_commits(self, tmp_path: Path) -> None:
        """Lists added, modified, and renamed paths, with a rename as both paths."""
        self.init(tmp_path)
        (tmp_path / "keep.txt").write_text("keep\n")
        (tmp_path / "old.txt").write_text("a long enough body to be detected as a rename\n" * 5)
        first = self.commit(tmp_path, "first")
        (tmp_path / "keep.txt").write_text("changed\n")
        (tmp_path / "old.txt").rename(tmp_path / "new.txt")
        (tmp_path / "added.txt").write_text("added\n")
        self.commit(tmp_path, "second")
        repository = CheckoutRepository(GitCommandRunner(tmp_path))
        paths = repository.changed_paths(first)
        assert paths is not None
        assert sorted(paths) == ["added.txt", "keep.txt", "new.txt", "old.txt"]

    def test_unknown_base_returns_none(self, tmp_path: Path) -> None:
        """Returns None when git cannot resolve the base."""
        self.init(tmp_path)
        (tmp_path / "a.txt").write_text("a\n")
        self.commit(tmp_path, "first")
        assert CheckoutRepository(GitCommandRunner(tmp_path)).changed_paths("no-such-revision") is None
