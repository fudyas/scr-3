from typing import List, Optional

from sdlc.repositories.checkout_repository import CheckoutRepository
from sdlc.settings import SystemTestDomainSettings
from sdlc.usecases.system_test_usecases import SystemTestUsecases

SETTINGS = SystemTestDomainSettings(
    root="tests/system",
    domains={"graph": ["src/app/services/graph/**"], "stack": ["tools/scr/stack/**"]},
    shared_globs=["src/primitives/**"],
    ignored_globs=["docs/**"],
)


class FakeCheckout(CheckoutRepository):
    """Answers the changed paths from a canned list and records the requested base."""

    def __init__(self, paths: Optional[List[str]]) -> None:
        """Holds the canned paths, or None to simulate a failed diff."""
        self.paths = paths
        self.requested_bases: List[str] = []

    def changed_paths(self, base: str) -> Optional[List[str]]:
        """Returns the canned paths."""
        self.requested_bases.append(base)
        return self.paths


class TestSystemTestUsecases:
    """Covers the selection of system test targets from the checkout diff."""

    def test_no_base_runs_all_domains_without_reading_git(self) -> None:
        """Selects the whole root and names the missing base."""
        checkout = FakeCheckout(["src/app/services/graph/app.py"])
        selection = SystemTestUsecases(checkout, SETTINGS).select(None)
        assert selection.targets == ["tests/system"]
        assert selection.explanations == ["no --base: all domains"]
        assert checkout.requested_bases == []

    def test_failed_diff_runs_all_domains(self) -> None:
        """Selects the whole root and names the base that git could not diff."""
        selection = SystemTestUsecases(FakeCheckout(None), SETTINGS).select("missing")
        assert selection.targets == ["tests/system"]
        assert selection.explanations == ["git diff missing failed: all domains"]

    def test_graph_path_selects_only_the_graph_domain(self) -> None:
        """Selects the graph directory for a diff with one graph path."""
        checkout = FakeCheckout(["src/app/services/graph/app.py"])
        selection = SystemTestUsecases(checkout, SETTINGS).select("abc123")
        assert selection.targets == ["tests/system/graph"]
        assert selection.explanations == ["src/app/services/graph/app.py -> graph"]
        assert checkout.requested_bases == ["abc123"]

    def test_ignored_diff_selects_no_target(self) -> None:
        """Selects nothing when every changed path is ignored."""
        selection = SystemTestUsecases(FakeCheckout(["docs/a.md"]), SETTINGS).select("abc123")
        assert selection.targets == []
