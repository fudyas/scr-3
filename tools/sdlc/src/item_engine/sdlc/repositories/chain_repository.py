from typing import Callable, Dict, List, Optional

from sdlc.models.chain import Chain
from sdlc.models.errors import ChainNotFoundError
from sdlc.models.item import Item
from sdlc.models.ledger import LedgerChange
from sdlc.repositories.item_repository import ItemRepository
from sdlc.repositories.ledger_ids import IDS_FILE, LedgerIdHelper
from sdlc.repositories.ledger_repository import LedgerRepository, LedgerSnapshot

# Ledger directory that holds one folder per chain
CHAINS_DIR = "chains"

# Builds a new chain from its allocated number, every chain by short id, and every item by short id
ChainBuilder = Callable[[int, Dict[str, Chain], Dict[str, Item]], Chain]

# Returns the changed chain from the current chain, every chain by short id, and every item by short id
ChainChange = Callable[[Chain, Dict[str, Chain], Dict[str, Item]], Chain]


class ChainRepository:
    """Stores chains on the shared ledger and reads them together with their member items."""

    def __init__(self, ledger: LedgerRepository, items: ItemRepository, prefix: str) -> None:
        """Initializes the repository.

        Args:
            ledger: the ledger repository that serializes writes.
            items: the item repository that reads member items from the same ledger.
            prefix: the chain id prefix, such as `CHN`.
        """
        self._ledger = ledger
        self._items = items
        self._prefix = prefix

    def snapshot(self) -> LedgerSnapshot:
        """Returns a view of the local ledger mirror, so that chains and items read one state."""
        return self._ledger.snapshot()

    def list_chains(self, snapshot: Optional[LedgerSnapshot] = None) -> List[Chain]:
        """Returns every chain, ordered by number."""
        view = snapshot or self._ledger.snapshot()
        paths = [path for path in view.list_paths(CHAINS_DIR) if path.endswith("/chain.json")]
        texts = view.read_texts(paths)
        chains = [Chain.model_validate_json(text) for text in texts.values() if text]
        return sorted(chains, key=lambda chain: chain.number)

    def get(self, short_id: str, snapshot: Optional[LedgerSnapshot] = None) -> Chain:
        """Returns one chain.

        Raises:
            ChainNotFoundError: the ledger holds no chain with the id.
        """
        view = snapshot or self._ledger.snapshot()
        text = view.read_text(self._chain_path(short_id))
        if text is None:
            raise ChainNotFoundError(f"no chain {short_id} on the ledger (run `lets sdlc sync`?)")
        return Chain.model_validate_json(text)

    def list_items(self, snapshot: LedgerSnapshot) -> List[Item]:
        """Returns every item at the snapshot, ordered by number."""
        return self._items.list_items(snapshot)

    def mint(self, build: ChainBuilder) -> Chain:
        """Allocates the next chain number across all hosts and stores the built chain in one commit.

        Args:
            build: creates the chain for the allocated number; it raises to refuse the chain.

        Returns:
            The stored chain.
        """
        def mutator(snapshot: LedgerSnapshot) -> LedgerChange:
            """Returns the change that allocates the next number and writes the chain."""
            chains = {chain.short_id: chain for chain in self.list_chains(snapshot)}
            items = {item.short_id: item for item in self._items.list_items(snapshot)}
            highest_existing = max((chain.number for chain in chains.values()), default=0)
            allocation = LedgerIdHelper.allocate(snapshot, self._prefix, highest_existing)
            chain = build(allocation.number, chains, items)
            return LedgerChange(
                changes={IDS_FILE: allocation.ids_text, self._chain_path(chain.short_id): self._serialize(chain)},
                message=f"{chain.full_id}: mint",
                result=chain,
            )

        return self._ledger.transact(mutator)

    def modify(self, short_id: str, change: ChainChange, message: str) -> Chain:
        """Applies a change to one chain on fresh ledger data and stores the result.

        Args:
            short_id: the chain to change.
            change: returns the changed chain; it raises to refuse the change.
            message: the ledger commit message.

        Returns:
            The stored chain.

        Raises:
            ChainNotFoundError: the ledger holds no chain with the id.
        """
        def mutator(snapshot: LedgerSnapshot) -> LedgerChange:
            """Returns the change that writes the updated chain."""
            chains = {chain.short_id: chain for chain in self.list_chains(snapshot)}
            if short_id not in chains:
                raise ChainNotFoundError(f"no chain {short_id} on the ledger")
            items = {item.short_id: item for item in self._items.list_items(snapshot)}
            updated = change(chains[short_id], chains, items)
            return LedgerChange(
                changes={self._chain_path(short_id): self._serialize(updated)},
                message=f"{updated.full_id}: {message}",
                result=updated,
            )

        return self._ledger.transact(mutator)

    @staticmethod
    def _chain_path(short_id: str) -> str:
        """Returns the ledger path of a chain record."""
        return f"{CHAINS_DIR}/{short_id}/chain.json"

    @staticmethod
    def _serialize(chain: Chain) -> str:
        """Returns the stable JSON text of a chain record."""
        return chain.model_dump_json(indent=2) + "\n"
