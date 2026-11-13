from abc import ABC
from typing import Dict, List, Set

from sdlc.models.errors import ChainMembershipError


class ChainMembershipHelper(ABC):
    """Checks a chain member list against the known items and the members of other chains."""

    @staticmethod
    def validate(chain_id: str, members: List[str], other_chains: Dict[str, List[str]],
                 known_items: Set[str]) -> None:
        """Checks that every member exists, appears once, and belongs to no other chain.

        Args:
            chain_id: the chain that receives the members.
            members: the short item ids in chain order.
            other_chains: the member list of every other chain, by short chain id.
            known_items: the short ids of every item on the ledger.

        Raises:
            ChainMembershipError: a member is unknown, repeated, or already in another chain.
        """
        problems: List[str] = []
        repeated = sorted({member for member in members if members.count(member) > 1})
        if repeated:
            problems.append(f"listed more than once: {', '.join(repeated)}")
        unknown = [member for member in members if member not in known_items]
        if unknown:
            problems.append(f"unknown items: {', '.join(unknown)}")

        # Keeps each item in at most one chain, so a chain status describes one body of work
        for other_id, other_members in sorted(other_chains.items()):
            taken = [member for member in members if member in other_members]
            if taken and other_id != chain_id:
                problems.append(f"already in {other_id}: {', '.join(taken)}")
        if problems:
            raise ChainMembershipError(f"{chain_id} members refused; " + "; ".join(problems))
