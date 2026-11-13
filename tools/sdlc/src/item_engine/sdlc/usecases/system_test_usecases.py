from typing import Optional

from sdlc.algorithms.system_test_domains import SystemTestDomainRules
from sdlc.models.system_test_selection import SystemTestSelection
from sdlc.repositories.checkout_repository import CheckoutRepository
from sdlc.settings import SystemTestDomainSettings


class SystemTestUsecases:
    """Chooses the system test domains that a change under test requires."""

    def __init__(self, checkout: CheckoutRepository, settings: SystemTestDomainSettings) -> None:
        """Initializes the usecases.

        Args:
            checkout: the repository of the checkout under test.
            settings: the domain mapping.
        """
        self._checkout = checkout
        self._settings = settings

    def select(self, base: Optional[str]) -> SystemTestSelection:
        """Returns the run targets and explanation lines for the change since the base.

        Steps:
            1. Select all domains when there is no base.
            2. Read the changed paths, and select all domains when git fails.
            3. Select the domains of the changed paths.

        Args:
            base: the git revision that the change starts from, or None for a full run.

        Returns:
            The run targets (empty when no domain is selected) and the explanation lines.
        """

        # Runs every domain without a base
        if base is None:
            return SystemTestDomainRules.select(None, self._settings, "no --base: all domains")

        # Runs every domain when git cannot produce the diff
        changed_paths = self._checkout.changed_paths(base)
        if changed_paths is None:
            return SystemTestDomainRules.select(None, self._settings, f"git diff {base} failed: all domains")
        return SystemTestDomainRules.select(changed_paths, self._settings, "")
