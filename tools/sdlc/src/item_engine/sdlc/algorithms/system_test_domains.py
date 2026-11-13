from abc import ABC
from pathlib import PurePosixPath
from typing import List, Optional, Set

from sdlc.models.system_test_selection import SystemTestSelection
from sdlc.settings import SystemTestDomainSettings


class SystemTestDomainRules(ABC):
    """Maps changed paths to the system test domains that must run."""

    @staticmethod
    def matches(path: str, globs: List[str]) -> bool:
        """Returns whether the path matches any of the globs."""
        return any(PurePosixPath(path).full_match(glob) for glob in globs)

    @staticmethod
    def is_shared(path: str, settings: SystemTestDomainSettings) -> bool:
        """Returns whether the path is shared, so that it selects every domain."""
        return SystemTestDomainRules.matches(path, settings.shared_globs)

    @staticmethod
    def resolve_path(path: str, settings: SystemTestDomainSettings) -> Optional[Set[str]]:
        """Returns the domains that the changed path selects.

        Steps:
            1. A shared path selects all domains.
            2. A path below a domain directory or a match of domain source globs selects those domains.
            3. An ignored path selects no domain.
            4. Any other path is unmapped and selects all domains.

        Args:
            path: the changed path, relative to the repository root.
            settings: the domain mapping.

        Returns:
            None for all domains, otherwise the selected domain names (empty for an ignored path).
        """

        # Selects all domains for a shared path
        if SystemTestDomainRules.is_shared(path, settings):
            return None

        # Collects the domains that own the path by directory or by source glob
        selected = {
            domain
            for domain, source_globs in settings.domains.items()
            if SystemTestDomainRules.matches(path, [f"{settings.root}/{domain}/**", *source_globs])
        }
        if selected:
            return selected

        # Selects no domain for an ignored path, and all domains for an unmapped one
        if SystemTestDomainRules.matches(path, settings.ignored_globs):
            return set()
        return None

    @staticmethod
    def select(
        changed_paths: Optional[List[str]], settings: SystemTestDomainSettings, reason_for_all: str
    ) -> SystemTestSelection:
        """Returns the run targets and the explanation lines for the changed paths.

        Steps:
            1. Select all domains with the given reason when there is no diff.
            2. Resolve each changed path and write its explanation line.
            3. Run the whole system root when any path selects all domains, else one directory per domain.

        Args:
            changed_paths: the changed paths, or None when the diff is unknown.
            settings: the domain mapping.
            reason_for_all: the explanation of a full run when the diff is unknown.

        Returns:
            The run targets (empty when no domain is selected) and one explanation line per path.
        """

        # Runs every domain when the diff is unknown
        if changed_paths is None:
            return SystemTestSelection(targets=[settings.root], explanations=[reason_for_all])

        # Resolves each path to its domains and writes the explanation line
        run_all = False
        selected_domains: Set[str] = set()
        explanations: List[str] = []
        for path in changed_paths:
            domains = SystemTestDomainRules.resolve_path(path, settings)
            if domains is None:
                run_all = True
                kind = "shared" if SystemTestDomainRules.is_shared(path, settings) else "unmapped"
                explanations.append(f"{path} -> all ({kind})")
            elif not domains:
                explanations.append(f"{path} -> none (ignored)")
            else:
                selected_domains.update(domains)
                explanations.append(f"{path} -> {', '.join(sorted(domains))}")

        # Builds the targets from the whole root or from the selected domain directories
        if run_all:
            targets = [settings.root]
        else:
            targets = [f"{settings.root}/{domain}" for domain in sorted(selected_domains)]
        return SystemTestSelection(targets=targets, explanations=explanations)
