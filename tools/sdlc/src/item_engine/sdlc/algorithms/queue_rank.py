from abc import ABC
from typing import List


class QueueRankHelper(ABC):
    """Computes the queue rank that orders scheduled items."""

    @staticmethod
    def rank_last(ranks: List[float]) -> float:
        """Returns a rank that places an item after every ranked item."""
        return max(ranks) + 1.0 if ranks else 1.0

    @staticmethod
    def rank_before(ranks: List[float], target_rank: float) -> float:
        """Returns a rank that places an item directly before the target rank.

        Args:
            ranks: the ranks of every other scheduled item.
            target_rank: the rank of the item to precede.

        Returns:
            The midpoint between the target and the closest lower rank.
        """
        lower_ranks = [rank for rank in ranks if rank < target_rank]
        predecessor = max(lower_ranks) if lower_ranks else target_rank - 1.0
        return (predecessor + target_rank) / 2.0
