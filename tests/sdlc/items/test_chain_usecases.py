from typing import Callable, List

import pytest

from sdlc.models.chain import ChainStatus
from sdlc.models.errors import AmendmentRefusedError, ChainMembershipError, ChainNotFoundError, InvalidDescError
from sdlc.models.item import ItemKind, ItemStatus
from sdlc.models.record import RecordAmendment
from sdlc.wiring import AppWiring


class ChainFlowHelper:
    """Mints items and chains for chain tests."""

    @staticmethod
    def mint_items(wiring: AppWiring, count: int) -> List[str]:
        """Mints the given number of items and returns their short ids."""
        slugs = ["LEDGER-CORE-TOOLS", "GRAPH-CLAIM-AMEND", "RETRIEVAL-FALLBACK-FIX", "EMBEDDING-SAL-RUN"]
        return [wiring.item_usecases.mint(ItemKind.TASK, slugs[index], "raw idea", "Normalized idea.", [], []).short_id
                for index in range(count)]


class TestChainUsecases:
    """Covers chain minting, membership, and status rollup on a real ledger."""

    def test_mints_unique_numbers_across_hosts(self, make_host: Callable[[str], AppWiring]) -> None:
        """Gives two hosts consecutive chain numbers that never collide with item numbers."""
        alpha, beta = make_host("alpha"), make_host("beta")
        ChainFlowHelper.mint_items(alpha, 2)
        first = alpha.chain_usecases.mint("EMBEDDING-PIPELINE", "Embed the corpus.", ["p1"], ["ITM-0001"])
        second = beta.chain_usecases.mint("PROMPTING-STACK", "Stand up Prompting.", [], ["itm-0002-graph-claim-amend"])
        assert (first.full_id, second.full_id) == ("CHN-0001-EMBEDDING-PIPELINE", "CHN-0002-PROMPTING-STACK")
        assert second.items == ["ITM-0002"] and second.host == "beta"
        assert alpha.item_usecases.mint(ItemKind.FIX, "X-Y-Z", "a", "b", [], []).short_id == "ITM-0003"

    def test_refuses_bad_desc_unknown_repeated_and_shared_members(
            self, make_host: Callable[[str], AppWiring]) -> None:
        """Refuses a bad slug, unknown or repeated items, and items another chain holds."""
        host = make_host("alpha")
        first, second = ChainFlowHelper.mint_items(host, 2)
        with pytest.raises(InvalidDescError):
            host.chain_usecases.mint("lowercase", "x", [], [])
        with pytest.raises(ChainMembershipError, match="unknown items: ITM-0042"):
            host.chain_usecases.mint("EMBEDDING-PIPELINE", "x", [], [first, "ITM-0042"])
        with pytest.raises(ChainMembershipError, match="more than once"):
            host.chain_usecases.mint("EMBEDDING-PIPELINE", "x", [], [first, first])
        chain = host.chain_usecases.mint("EMBEDDING-PIPELINE", "x", [], [first])
        with pytest.raises(ChainMembershipError, match=f"already in {chain.short_id}"):
            host.chain_usecases.mint("PROMPTING-STACK", "y", [], [second, first])
        assert [view.chain.short_id for view in host.chain_usecases.list_views()] == ["CHN-0001"]

    def test_replaces_and_clears_members(self, make_host: Callable[[str], AppWiring]) -> None:
        """Replaces the ordered member list, keeps its order, and clears it."""
        host = make_host("alpha")
        first, second, third = ChainFlowHelper.mint_items(host, 3)
        chain = host.chain_usecases.mint("EMBEDDING-PIPELINE", "x", [], [first])
        updated = host.chain_usecases.set_items(chain.full_id, [third, first, second])
        assert updated.items == [third, first, second]
        assert updated.history[-1].event == "items"
        assert host.chain_usecases.set_items("CHN-0001", []).items == []
        with pytest.raises(ChainNotFoundError):
            host.chain_usecases.set_items("CHN-0009", [first])

    def test_view_rolls_up_member_statuses(self, make_host: Callable[[str], AppWiring]) -> None:
        """Reports BACKLOG until a member starts, and DONE when only obsolete members remain unfinished."""
        host = make_host("alpha")
        first, second = ChainFlowHelper.mint_items(host, 2)
        host.chain_usecases.mint("EMBEDDING-PIPELINE", "x", [], [first, second])
        view = host.chain_usecases.view("CHN-0001")
        assert view.status == ChainStatus.BACKLOG and view.counts == {ItemStatus.BACKLOG: 2}
        assert [member.short_id for member in view.members] == [first, second]
        host.item_usecases.set_status(second, ItemStatus.OBSOLETE, False)
        host.item_usecases.set_status(first, ItemStatus.OBSOLETE, False)
        assert host.chain_usecases.view("CHN-0001").status == ChainStatus.DONE

    def test_amends_description_and_desc_of_a_backlog_chain(self, make_host: Callable[[str], AppWiring]) -> None:
        """Replaces the description and the slug, keeps the members, and records the old values."""
        host = make_host("alpha")
        first, second = ChainFlowHelper.mint_items(host, 2)
        host.chain_usecases.mint("EMBEDDING-PIPELINE", "Old framing.", [], [first, second])
        amended = host.chain_usecases.amend(
            "CHN-0001", RecordAmendment(desc="VECTOR-PIPELINE", description="  New framing.  "))
        assert amended.full_id == "CHN-0001-VECTOR-PIPELINE" and amended.description == "New framing."
        assert amended.items == [first, second]
        last = amended.history[-1]
        assert last.event == "amended" and last.detail == "desc EMBEDDING-PIPELINE -> VECTOR-PIPELINE, description"
        assert last.previous == {"desc": "EMBEDDING-PIPELINE", "description": "Old framing."}

        # Reads the chain back through the old full id to prove the short id stays the key
        stored = host.chain_usecases.view("CHN-0001-EMBEDDING-PIPELINE").chain
        assert stored.full_id == "CHN-0001-VECTOR-PIPELINE" and stored.history[-1].previous == last.previous

    def test_refuses_to_amend_a_done_chain(self, make_host: Callable[[str], AppWiring]) -> None:
        """Refuses an amendment when the members roll up to DONE and leaves the chain unchanged."""
        host = make_host("alpha")
        first, second = ChainFlowHelper.mint_items(host, 2)
        host.chain_usecases.mint("EMBEDDING-PIPELINE", "Old framing.", [], [first, second])
        host.item_usecases.set_status(first, ItemStatus.OBSOLETE, False)
        host.item_usecases.set_status(second, ItemStatus.OBSOLETE, False)
        with pytest.raises(AmendmentRefusedError, match="CHN-0001 is DONE"):
            host.chain_usecases.amend("CHN-0001", RecordAmendment(description="New framing."))
        stored = host.chain_usecases.view("CHN-0001").chain
        assert stored.description == "Old framing." and stored.history[-1].event == "minted"

    def test_amend_refuses_an_unknown_chain(self, make_host: Callable[[str], AppWiring]) -> None:
        """Raises when the ledger holds no chain with the id."""
        host = make_host("alpha")
        with pytest.raises(ChainNotFoundError):
            host.chain_usecases.amend("CHN-0009", RecordAmendment(description="New framing."))
