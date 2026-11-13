from typing import List, Optional, Set

import pytest

from sdlc.algorithms.system_test_domains import SystemTestDomainRules
from sdlc.settings import SystemTestDomainSettings

SETTINGS = SystemTestDomainSettings(
    root="tests/system",
    domains={
        "embedding": ["src/lib/embedding/**", "data/sal/**"],
        "graph": ["src/app/services/graph/**"],
        "retrieval": ["src/lib/embedding/**", "data/sal/**"],
    },
    shared_globs=["src/primitives/**", "tests/system/conftest.py", "docs/shared.md"],
    ignored_globs=["docs/**", "**/*.md"],
)


class TestSystemTestDomainRules:
    """Covers the mapping of changed paths to system test domains."""

    def test_shared_path_selects_all(self) -> None:
        """Runs the whole system root for a shared path."""
        selection = SystemTestDomainRules.select(["src/primitives/ids.py"], SETTINGS, "unused")
        assert selection.targets == ["tests/system"]
        assert SystemTestDomainRules.resolve_path("src/primitives/ids.py", SETTINGS) is None

    def test_path_below_a_domain_directory_selects_that_domain(self) -> None:
        """Selects the domain whose directory holds the path."""
        selection = SystemTestDomainRules.select(["tests/system/graph/test_a.py"], SETTINGS, "unused")
        assert selection.targets == ["tests/system/graph"]

    def test_source_path_in_two_domains_selects_both_in_name_order(self) -> None:
        """Selects the union of the domains whose source globs match."""
        selection = SystemTestDomainRules.select(["src/lib/embedding/client.py"], SETTINGS, "unused")
        assert selection.targets == ["tests/system/embedding", "tests/system/retrieval"]

    def test_targets_of_several_paths_are_sorted_and_unique(self) -> None:
        """Lists each selected domain once, in name order."""
        paths = ["src/app/services/graph/a.py", "data/sal/x.json", "tests/system/graph/test_b.py"]
        selection = SystemTestDomainRules.select(paths, SETTINGS, "unused")
        assert selection.targets == ["tests/system/embedding", "tests/system/graph", "tests/system/retrieval"]

    def test_ignored_path_selects_none(self) -> None:
        """Gives no target for an ignored path."""
        selection = SystemTestDomainRules.select(["docs/arch/MAP.md"], SETTINGS, "unused")
        assert selection.targets == []
        assert SystemTestDomainRules.resolve_path("docs/arch/MAP.md", SETTINGS) == set()

    def test_unmapped_path_selects_all(self) -> None:
        """Runs the whole system root for a path that no rule maps."""
        selection = SystemTestDomainRules.select(["scripts/new_tool.sh"], SETTINGS, "unused")
        assert selection.targets == ["tests/system"]

    def test_unmapped_path_beside_a_domain_path_still_selects_all(self) -> None:
        """Lets one unmapped path widen the run of a domain path."""
        selection = SystemTestDomainRules.select(["tests/system/graph/test_a.py", "scripts/x.sh"], SETTINGS, "unused")
        assert selection.targets == ["tests/system"]

    def test_shared_path_wins_over_an_ignored_glob(self) -> None:
        """Selects all domains when a path is both shared and ignored."""
        assert SystemTestDomainRules.resolve_path("docs/shared.md", SETTINGS) is None

    def test_domain_directory_wins_over_an_ignored_glob(self) -> None:
        """Selects the domain for a markdown file below a domain directory."""
        resolved: Optional[Set[str]] = SystemTestDomainRules.resolve_path("tests/system/graph/NOTES.md", SETTINGS)
        assert resolved == {"graph"}

    def test_no_diff_selects_all_with_the_given_reason(self) -> None:
        """Runs the whole system root and explains it with the given reason."""
        selection = SystemTestDomainRules.select(None, SETTINGS, "no --base given")
        assert selection.targets == ["tests/system"]
        assert selection.explanations == ["no --base given"]

    def test_empty_diff_selects_nothing(self) -> None:
        """Gives no target and no explanation for an empty list of changed paths."""
        selection = SystemTestDomainRules.select([], SETTINGS, "unused")
        assert selection.targets == []
        assert selection.explanations == []

    @pytest.mark.parametrize(
        "path, expected",
        [
            ("src/primitives/ids.py", "src/primitives/ids.py -> all (shared)"),
            ("scripts/new_tool.sh", "scripts/new_tool.sh -> all (unmapped)"),
            ("docs/arch/MAP.md", "docs/arch/MAP.md -> none (ignored)"),
            ("src/app/services/graph/app.py", "src/app/services/graph/app.py -> graph"),
            ("data/sal/x.json", "data/sal/x.json -> embedding, retrieval"),
        ],
    )
    def test_explanation_line_form(self, path: str, expected: str) -> None:
        """Writes one explanation line of the contract form per changed path."""
        paths: List[str] = [path]
        assert SystemTestDomainRules.select(paths, SETTINGS, "unused").explanations == [expected]
