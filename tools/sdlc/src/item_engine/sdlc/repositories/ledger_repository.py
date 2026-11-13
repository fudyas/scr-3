from typing import Any, Callable, Dict, List, Optional

from sdlc.datasources.git_ledger_source import GitLedgerSource
from sdlc.models.errors import LedgerContentionError
from sdlc.models.ledger import LedgerChange


class LedgerSnapshot:
    """A read-only view of the ledger tree at one commit."""

    def __init__(self, source: GitLedgerSource, commit: Optional[str]) -> None:
        """Initializes the view.

        Args:
            source: the ledger data source.
            commit: the commit to read; None means an empty ledger.
        """
        self._source = source
        self._commit = commit

    @property
    def commit(self) -> Optional[str]:
        """Returns the commit this view reads."""
        return self._commit

    def read_text(self, path: str) -> Optional[str]:
        """Returns the text of one ledger file, or None when it does not exist."""
        return self.read_texts([path])[path]

    def read_texts(self, paths: List[str]) -> Dict[str, Optional[str]]:
        """Returns the text of each ledger file; a missing file maps to None."""
        if self._commit is None:
            return {path: None for path in paths}
        return self._source.read_texts(self._commit, paths)

    def list_paths(self, directory: str) -> List[str]:
        """Returns every file path under the ledger directory."""
        if self._commit is None:
            return []
        return self._source.list_paths(self._commit, directory)


class LedgerRepository:
    """Serializes ledger writes across hosts with a fetch, rebuild, and non-forced push loop."""

    def __init__(self, source: GitLedgerSource, retry_limit: int) -> None:
        """Initializes the repository.

        Args:
            source: the ledger data source.
            retry_limit: the most compare-and-swap attempts one write makes.
        """
        self._source = source
        self._retry_limit = retry_limit

    def snapshot(self) -> LedgerSnapshot:
        """Returns a view of the local ledger mirror; reads never touch the network."""
        return LedgerSnapshot(self._source, self._source.local_tip())

    def as_of(self) -> Optional[str]:
        """Returns the commit date of the local ledger mirror, or None before the first sync."""
        tip = self._source.local_tip()
        return self._source.commit_date(tip) if tip else None

    def sync(self) -> Optional[str]:
        """Refreshes the local mirror from the remote ledger.

        Returns:
            The remote ledger commit, or None when the remote has no ledger yet.

        Raises:
            LedgerUnreachableError: the remote cannot be reached.
        """
        with self._source.exclusive():
            return self._sync()

    def _sync(self) -> Optional[str]:
        """Refreshes the mirror while the caller holds the local ledger lock."""
        tip = self._source.remote_tip()
        if tip is not None:
            self._source.fetch(tip)
            self._source.set_local_tip(tip)
        return tip

    def transact(self, mutator: Callable[[LedgerSnapshot], LedgerChange]) -> Any:
        """Applies one change to the shared ledger and returns the mutator's result.

        Steps:
            1. Read the remote tip and fetch it.
            2. Run the mutator against that tip; it re-checks every rule on fresh data.
            3. Commit the changes on top of the tip and push without force.
            4. When another host pushed first, repeat from step 1.

        Args:
            mutator: builds the change from a snapshot of the current remote ledger.

        Returns:
            The `result` of the change that landed.

        Raises:
            LedgerUnreachableError: the remote cannot be reached; writes fail closed.
            LedgerContentionError: every attempt lost the race to another host.
            SdlcError: the mutator refused the change.
        """

        # Protects shared refs and the final mirror update across the entire retry loop
        last_detail = ""
        with self._source.exclusive():
            for _ in range(self._retry_limit):
                tip = self._sync()
                change = mutator(LedgerSnapshot(self._source, tip))
                if not change.changes:
                    return change.result
                commit = self._source.commit_changes(tip, change.changes, change.message)
                outcome = self._source.push(commit)
                if outcome.accepted:
                    self._source.set_local_tip(commit)
                    return change.result
                last_detail = outcome.detail
        raise LedgerContentionError(
            f"ledger write lost {self._retry_limit} compare-and-swap attempts: {last_detail}"
        )
