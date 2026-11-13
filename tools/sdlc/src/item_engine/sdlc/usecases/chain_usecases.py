from typing import Dict, List

from sdlc.algorithms.chain_membership import ChainMembershipHelper
from sdlc.algorithms.chain_status import ChainStatusHelper
from sdlc.algorithms.desc_slug import DescSlugHelper
from sdlc.algorithms.item_ids import ItemIdHelper
from sdlc.algorithms.record_amendment import RecordAmendmentHelper
from sdlc.algorithms.record_history import RecordHistoryHelper
from sdlc.algorithms.timestamps import TimestampHelper
from sdlc.algorithms.unique_values import UniqueValuesHelper
from sdlc.models.chain import Chain
from sdlc.models.item import Item
from sdlc.models.record import HistoryEntry, RecordAmendment
from sdlc.models.views import ChainView
from sdlc.repositories.chain_repository import ChainRepository


class ChainUsecases:
    """Mints chains, sets their ordered member items, and reports their rolled-up status."""

    def __init__(self, chains: ChainRepository, chain_prefix: str, item_prefix: str, host: str) -> None:
        """Initializes the usecases.

        Args:
            chains: the chain repository.
            chain_prefix: the chain id prefix, such as `CHN`.
            item_prefix: the item id prefix, such as `ITM`.
            host: this host's name, recorded in the chain history.
        """
        self._chains = chains
        self._chain_prefix = chain_prefix
        self._item_prefix = item_prefix
        self._host = host

    def normalize_id(self, text: str) -> str:
        """Returns the short chain id for a short or full chain id."""
        return ItemIdHelper.normalize_item(text, self._chain_prefix)

    def mint(self, desc: str, description: str, tags: List[str], members: List[str]) -> Chain:
        """Mints a new chain with a cross-host unique number and an optional ordered member list.

        Args:
            desc: the DESC slug of the chain id.
            description: what the chain frames, in a few sentences.
            tags: free-text labels.
            members: short or full item ids, in implementation order.

        Returns:
            The minted chain.

        Raises:
            InvalidDescError: the slug breaks the notation rules.
            ChainMembershipError: a member is unknown, repeated, or already in another chain.
        """
        DescSlugHelper.validate(desc)
        member_ids = self._normalize_items(members)
        now = TimestampHelper.now()

        def build(number: int, chains: Dict[str, Chain], items: Dict[str, Item]) -> Chain:
            """Returns the new chain for the allocated number after the membership checks pass."""
            chain_id = ItemIdHelper.format_item(self._chain_prefix, number)
            ChainMembershipHelper.validate(chain_id, member_ids, {key: value.items for key, value in chains.items()},
                                           set(items))
            return Chain(
                prefix=self._chain_prefix, number=number, desc=desc, description=description.strip(),
                tags=UniqueValuesHelper.ordered(tags), items=member_ids, host=self._host,
                created_at=now, updated_at=now,
                history=[HistoryEntry(at=now, host=self._host, event="minted", detail=", ".join(member_ids))],
            )

        return self._chains.mint(build)

    def set_items(self, chain_id: str, members: List[str]) -> Chain:
        """Replaces the ordered member list of a chain; an empty list clears it.

        Raises:
            ChainNotFoundError: the ledger holds no chain with the id.
            ChainMembershipError: a member is unknown, repeated, or already in another chain.
        """
        short_id = self.normalize_id(chain_id)
        member_ids = self._normalize_items(members)

        def change(chain: Chain, chains: Dict[str, Chain], items: Dict[str, Item]) -> Chain:
            """Returns the chain with its members replaced after the membership checks pass."""
            ChainMembershipHelper.validate(short_id, member_ids, {key: value.items for key, value in chains.items()},
                                           set(items))
            return RecordHistoryHelper.touch(chain, {"items": member_ids}, self._host, "items",
                                             ", ".join(member_ids) or "none")

        return self._chains.modify(short_id, change, "items")

    def amend(self, chain_id: str, amendment: RecordAmendment) -> Chain:
        """Replaces the description or the DESC slug of a chain that is not DONE.

        Args:
            chain_id: the short or full chain id.
            amendment: the replacement text per field.

        Returns:
            The amended chain, with the old values in its last history entry.

        Raises:
            AmendmentRefusedError: the chain is DONE, or the amendment is empty, unchanged, or names a missing field.
            InvalidDescError: the slug breaks the notation rules.
            ChainNotFoundError: the ledger holds no chain with the id.
        """

        def change(chain: Chain, chains: Dict[str, Chain], items: Dict[str, Item]) -> Chain:
            """Returns the amended chain after the rolled-up status check passes on fresh ledger data."""
            status = self._view(chain, items).status
            RecordAmendmentHelper.check_chain_status(chain.short_id, status)
            return RecordAmendmentHelper.apply(chain, amendment, self._host)

        return self._chains.modify(self.normalize_id(chain_id), change, "amend")

    def list_views(self) -> List[ChainView]:
        """Returns every chain with its rolled-up status, from one state of the local ledger mirror."""
        snapshot = self._chains.snapshot()
        items = {item.short_id: item for item in self._chains.list_items(snapshot)}
        return [self._view(chain, items) for chain in self._chains.list_chains(snapshot)]

    def view(self, chain_id: str) -> ChainView:
        """Returns one chain with its rolled-up status and member items.

        Raises:
            ChainNotFoundError: the ledger holds no chain with the id.
        """
        snapshot = self._chains.snapshot()
        chain = self._chains.get(self.normalize_id(chain_id), snapshot)
        items = {item.short_id: item for item in self._chains.list_items(snapshot)}
        return self._view(chain, items)

    def _view(self, chain: Chain, items: Dict[str, Item]) -> ChainView:
        """Returns the view of a chain, joining its members with their item records."""
        members = [items[member] for member in chain.items if member in items]
        statuses = [member.status for member in members]
        return ChainView(chain=chain, status=ChainStatusHelper.rollup(statuses), members=members,
                         counts=ChainStatusHelper.counts(statuses))

    def _normalize_items(self, members: List[str]) -> List[str]:
        """Returns the short item ids of the members, in the given order."""
        return [ItemIdHelper.normalize_item(member, self._item_prefix) for member in members]
