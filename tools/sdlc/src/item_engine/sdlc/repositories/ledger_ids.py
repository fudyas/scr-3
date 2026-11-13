import json
from abc import ABC

from sdlc.models.ledger import IdAllocation
from sdlc.repositories.ledger_repository import LedgerSnapshot

# Ledger file that records the last minted number per id prefix
IDS_FILE = "ids.json"


class LedgerIdHelper(ABC):
    """Allocates cross-host unique record numbers from the ledger ids file."""

    @staticmethod
    def allocate(snapshot: LedgerSnapshot, prefix: str, highest_existing: int) -> IdAllocation:
        """Returns the next number for the prefix and the ids file text that records it.

        The caller writes `ids_text` to `IDS_FILE` in the same ledger change as the new record,
        so the compare-and-swap push makes the allocation unique across hosts.

        Args:
            snapshot: the ledger state the change builds on.
            prefix: the id prefix, such as `ITM` or `CHN`.
            highest_existing: the highest number among the stored records of the prefix.

        Returns:
            The allocated number and the updated ids file text.
        """
        ids = json.loads(snapshot.read_text(IDS_FILE) or "{}")
        number = max(int(ids.get(prefix, 0)), highest_existing) + 1
        ids[prefix] = number
        return IdAllocation(number=number, ids_text=json.dumps(ids, indent=2, sort_keys=True) + "\n")
