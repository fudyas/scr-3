from typing import Dict, List, Optional

from sdlc.datasources.lease_source import LeaseSource
from sdlc.models.errors import LockError
from sdlc.models.lease import LeaseAcquisition, LeaseHolder
from sdlc.repositories.telemetry_repository import TelemetryRepository


class LockUsecases:
    """Takes and releases the host-local leases that serialize promotion and the QA window."""

    def __init__(self, leases: LeaseSource, telemetry: TelemetryRepository, lock_names: List[str]) -> None:
        """Initializes the usecases.

        Args:
            leases: the lease data source.
            telemetry: the telemetry repository that records lease waits.
            lock_names: the lease names the pipeline knows, such as `maintree` and `stack`.
        """
        self._leases = leases
        self._telemetry = telemetry
        self._lock_names = lock_names

    def acquire(self, name: str, holder_id: str, wait: bool, steal: bool) -> LeaseAcquisition:
        """Takes the lease, blocking while another holder keeps it, and records the wait.

        Raises:
            LockError: the name is unknown, or the lease is held and `wait` is False.
        """
        self._check_name(name)
        acquisition = self._leases.acquire(name, holder_id, wait, steal)
        self._telemetry.record_event(
            "lease_acquired", holder_id, value=round(acquisition.waited_seconds, 3),
            detail={"lease": name, "stolen_from": acquisition.stolen_from},
        )
        return acquisition

    def release(self, name: str, holder_id: str, force: bool) -> bool:
        """Releases the lease and records the release.

        Returns:
            True when a lease was released; False when it was already free.

        Raises:
            LockError: the name is unknown, or another holder keeps the lease and `force` is not set.
        """
        self._check_name(name)
        holder = self._leases.holder(name)
        released = self._leases.release(name, holder_id, force)
        if released and holder is not None:
            held_seconds = max(0.0, self._now_epoch() - holder.acquired_epoch)
            self._telemetry.record_event("lease_released", holder.holder_id, value=round(held_seconds, 3),
                                         detail={"lease": name, "forced_by": holder_id if force else None})
        return released

    def status(self, name: Optional[str]) -> Dict[str, Optional[LeaseHolder]]:
        """Returns the holder of each known lease, or of the named one."""
        names = [name] if name else self._lock_names
        for lock_name in names:
            self._check_name(lock_name)
        return {lock_name: self._leases.holder(lock_name) for lock_name in names}

    def require_holder(self, name: str, holder_id: str) -> None:
        """Requires the named lease to belong to the supplied holder.

        Args:
            name: the lease to inspect.
            holder_id: the caller's expected holder id.

        Raises:
            LockError: the lease is unknown, free, or belongs to another holder.
        """
        self._check_name(name)
        holder = self._leases.holder(name)
        if holder is None:
            raise LockError(f"lease {name!r} is free; acquire it with --holder {holder_id} first")
        if holder.holder_id != holder_id:
            raise LockError(f"lease {name!r} is held by {holder.holder_id}, not {holder_id}")

    def _check_name(self, name: str) -> None:
        """Checks that the lease name is one the pipeline knows.

        Raises:
            LockError: the name is unknown.
        """
        if name not in self._lock_names:
            raise LockError(f"unknown lease {name!r} (known: {', '.join(self._lock_names)})")

    @staticmethod
    def _now_epoch() -> float:
        """Returns the current time in seconds since the epoch."""
        return LeaseSource.now_epoch()
