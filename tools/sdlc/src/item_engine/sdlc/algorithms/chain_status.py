from abc import ABC
from typing import Dict, List

from sdlc.models.chain import ChainStatus
from sdlc.models.item import ItemStatus

# Item statuses of members that have not started yet
NOT_STARTED_STATUSES = (ItemStatus.BACKLOG, ItemStatus.PLANNED, ItemStatus.SCHEDULED)


class ChainStatusHelper(ABC):
    """Rolls member item statuses up into one chain status."""

    @staticmethod
    def rollup(member_statuses: List[ItemStatus]) -> ChainStatus:
        """Returns the chain status that the member statuses imply.

        Steps:
            1. Drop OBSOLETE members; they no longer belong to the work.
            2. Return BACKLOG for a chain without members and DONE when every remaining member is DONE.
            3. Return BACKLOG when no remaining member has started, else IN PROGRESS.

        Args:
            member_statuses: the status of each member item, in chain order.

        Returns:
            The rolled-up chain status.
        """
        active = [status for status in member_statuses if status != ItemStatus.OBSOLETE]
        if not member_statuses:
            return ChainStatus.BACKLOG
        if all(status == ItemStatus.DONE for status in active):
            return ChainStatus.DONE
        if all(status in NOT_STARTED_STATUSES for status in active):
            return ChainStatus.BACKLOG
        return ChainStatus.IN_PROGRESS

    @staticmethod
    def counts(member_statuses: List[ItemStatus]) -> Dict[ItemStatus, int]:
        """Returns the number of members in each status, in lifecycle order, without empty statuses."""
        return {status: member_statuses.count(status) for status in ItemStatus if status in member_statuses}
