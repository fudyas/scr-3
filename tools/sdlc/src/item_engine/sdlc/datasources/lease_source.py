import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from sdlc.models.errors import LockError
from sdlc.models.lease import LeaseAcquisition, LeaseHolder

# File inside a lease directory that names the holder
HOLDER_FILE = "holder.json"


class LeaseSource:
    """Owns host-local leases as atomic directories under the main checkout's state dir."""

    def __init__(self, locks_dir: Path, host: str, poll_seconds: float,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        """Initializes the source.

        Args:
            locks_dir: the directory that holds one `<name>.lock` directory per held lease.
            host: the host name written into each holder record.
            poll_seconds: the wait between attempts while another holder keeps the lease.
            sleep: the wait function, replaceable in tests.
        """
        self._locks_dir = locks_dir
        self._host = host
        self._poll_seconds = poll_seconds
        self._sleep = sleep

    def holder(self, name: str) -> Optional[LeaseHolder]:
        """Returns the current holder of the lease, or None when it is free."""
        holder_file = self._lease_dir(name) / HOLDER_FILE
        try:
            return LeaseHolder.from_document(json.loads(holder_file.read_text(encoding="utf-8")))
        except FileNotFoundError:
            return None
        except (json.JSONDecodeError, TypeError, ValueError):
            return LeaseHolder(name=name, holder_id="unknown", host="unknown", pid=0, acquired_at="", acquired_epoch=0)

    def acquire(self, name: str, holder_id: str, wait: bool, steal: bool) -> LeaseAcquisition:
        """Takes the lease, blocking while another holder keeps it.

        Steps:
            1. Steal the lease first when asked: remove the current holder's directory.
            2. Try an atomic `mkdir`; success means this caller holds the lease.
            3. Re-entry by the same holder id succeeds at once.
            4. Otherwise report the holder, wait one poll, and try again; never time out.

        Args:
            name: the lease name, such as `stack` or `maintree`.
            holder_id: the id of the caller, usually an item id.
            wait: whether to block until the lease frees; False fails at once when held.
            steal: whether to break the current holder's lease first.

        Returns:
            The holder record and the seconds spent waiting.

        Raises:
            LockError: the lease is held by another holder and `wait` is False.
        """
        self._locks_dir.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        stolen_from: Optional[str] = None
        if steal:
            current = self.holder(name)
            if current is not None and current.holder_id != holder_id:
                stolen_from = current.holder_id
                shutil.rmtree(self._lease_dir(name), ignore_errors=True)

        # Contends atomically on every attempt so a waiter proceeds only after it wins
        announced_holder: Optional[str] = None
        while True:
            try:
                self._lease_dir(name).mkdir()
                record = self._write_holder(name, holder_id)
                return LeaseAcquisition(holder=record, waited_seconds=time.monotonic() - started,
                                        stolen_from=stolen_from)
            except FileExistsError:
                current = self.holder(name)
                if current is not None and current.holder_id == holder_id:
                    return LeaseAcquisition(holder=current, waited_seconds=time.monotonic() - started,
                                            stolen_from=stolen_from)
                if not wait:
                    raise LockError(f"lease {name!r} is held by {self._describe(current)}")
                description = self._describe(current)
                if description != announced_holder:
                    print(f"waiting for lease {name!r} held by {description}", file=sys.stderr, flush=True)
                    announced_holder = description
                self._sleep(self._poll_seconds)

    def release(self, name: str, holder_id: str, force: bool) -> bool:
        """Releases the lease.

        Args:
            name: the lease name.
            holder_id: the id of the caller.
            force: whether to release a lease another holder keeps.

        Returns:
            True when a lease was released; False when it was already free.

        Raises:
            LockError: another holder keeps the lease and `force` is not set.
        """
        current = self.holder(name)
        if current is None:
            return False
        if current.holder_id != holder_id and not force:
            raise LockError(f"lease {name!r} is held by {self._describe(current)}; use --force to break it")
        shutil.rmtree(self._lease_dir(name), ignore_errors=True)
        return True

    @staticmethod
    def now_epoch() -> float:
        """Returns the current time in seconds since the epoch, the clock of every holder record."""
        return time.time()

    def _lease_dir(self, name: str) -> Path:
        """Returns the directory whose existence means the lease is held."""
        return self._locks_dir / f"{name}.lock"

    def _write_holder(self, name: str, holder_id: str) -> LeaseHolder:
        """Writes and returns the holder record for a freshly taken lease."""
        now = datetime.now(timezone.utc)
        record = LeaseHolder(
            name=name, holder_id=holder_id, host=self._host, pid=os.getppid(),
            acquired_at=now.isoformat(timespec="seconds"), acquired_epoch=now.timestamp(),
        )
        (self._lease_dir(name) / HOLDER_FILE).write_text(record.model_dump_json(), encoding="utf-8")
        return record

    @staticmethod
    def _describe(holder: Optional[LeaseHolder]) -> str:
        """Returns a one-line description of a lease holder."""
        if holder is None:
            return "an unknown holder"
        held_seconds = int(time.time() - holder.acquired_epoch) if holder.acquired_epoch else 0
        return f"{holder.holder_id} on {holder.host} for {held_seconds}s"
