from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from sdlc.algorithms.timestamps import TimestampHelper
from sdlc.datasources.artifact_source import ArtifactSource
from sdlc.datasources.draft_source import DraftSource
from sdlc.datasources.git_command import GitCommandRunner, GitSshEnvironmentHelper, MainRootHelper
from sdlc.datasources.git_ledger_source import GitLedgerSource
from sdlc.datasources.ide_launcher_source import IdeLauncherSource
from sdlc.datasources.jsonl_store import JsonlStore
from sdlc.datasources.lease_source import LeaseSource
from sdlc.datasources.review_session_source import ReviewSessionSource
from sdlc.datasources.transcript_source import TranscriptSource
from sdlc.datasources.worktree_source import WorktreeSource
from sdlc.repositories.chain_repository import ChainRepository
from sdlc.repositories.artifact_repository import ArtifactRepository
from sdlc.repositories.checkout_repository import CheckoutRepository
from sdlc.repositories.item_repository import ItemRepository
from sdlc.repositories.ledger_repository import LedgerRepository
from sdlc.repositories.run_log_repository import RunLogRepository
from sdlc.repositories.telemetry_repository import TelemetryRepository
from sdlc.settings import SdlcSettings, SdlcSettingsHelper
from sdlc.usecases.chain_usecases import ChainUsecases
from sdlc.usecases.artifact_usecases import ArtifactUsecases
from sdlc.usecases.ide_usecases import IdeUsecases
from sdlc.usecases.item_usecases import ItemUsecases
from sdlc.usecases.hardware_usecases import HardwareUsecases
from sdlc.usecases.lock_usecases import LockUsecases
from sdlc.usecases.plan_usecases import PlanUsecases
from sdlc.usecases.review_usecases import ReviewUsecases
from sdlc.usecases.run_log_usecases import RunLogUsecases
from sdlc.usecases.schedule_usecases import ScheduleUsecases
from sdlc.usecases.stats_usecases import StatsUsecases
from sdlc.usecases.system_test_usecases import SystemTestUsecases
from sdlc.usecases.telemetry_usecases import TelemetryUsecases
from sdlc.usecases.worktree_usecases import WorktreeUsecases

# Shared settings folder of the LETS tools, `tools/scr/shared/etc`
TOOLS_ETC_DIR = Path(__file__).resolve().parents[1] / "etc"

# Checkout that holds the running tool, which is the snapshot or promotion worktree during a gate
PROJECT_ROOT = Path(__file__).resolve().parents[5]


class AppWiring:
    """Wires data sources, repositories, and usecases from settings at startup."""

    def __init__(self, settings: SdlcSettings, now: Callable[[], str] = TimestampHelper.now) -> None:
        """Builds every entity of the SDLC tool.

        Args:
            settings: the resolved settings.
            now: the source of telemetry record timestamps, replaceable in tests.
        """
        self.settings = settings
        main_runner = GitCommandRunner(settings.main_root)
        network_runner = GitCommandRunner(
            settings.main_root,
            GitSshEnvironmentHelper.build(settings.main_root, settings.ssh_key_path, settings.ssh_config_path),
        )

        # Builds the data sources, the only entities that perform I/O
        ledger_source = GitLedgerSource(
            network_runner, settings.ledger_remote, settings.ledger_branch, settings.ledger_network_timeout_seconds
        )
        drafts = DraftSource(settings.drafts_dir, "PLAN.md")
        review_drafts = DraftSource(settings.drafts_dir, "REVIEW.md")
        leases = LeaseSource(settings.locks_dir, settings.host, settings.lock_poll_seconds)
        transcripts = TranscriptSource(settings.state_dir / "transcripts")

        # Builds the repositories over the data sources
        ledger = LedgerRepository(ledger_source, settings.push_retry_limit)
        items = ItemRepository(ledger, settings.item_prefix)
        self.artifact_usecases = ArtifactUsecases(
            ArtifactRepository(ledger), ArtifactSource(settings.artifacts_dir, settings.worktrees_dir),
            items, settings.item_prefix, settings.host,
        )
        worktrees = WorktreeSource(main_runner, settings.worktrees_dir, settings.work_branch_prefix,
                                   settings.worktree_links, ReviewSessionSource(settings.logs_dir),
                                   settings.worktree_data_dirs, self.artifact_usecases.capture_review,
                                   self.artifact_usecases.verify_review, self.artifact_usecases.result_for)
        chains = ChainRepository(ledger, items, settings.chain_prefix)
        telemetry = TelemetryRepository(JsonlStore(settings.telemetry_dir), settings.host, now, settings.telemetry_blacklist)
        run_log = RunLogRepository(settings.logs_dir, settings.host)
        checkout = CheckoutRepository(GitCommandRunner(PROJECT_ROOT))

        # Builds the usecases over the repositories
        self.items = items
        self.item_usecases = ItemUsecases(items, telemetry, settings.item_prefix, settings.host,
                                          HardwareUsecases(self).check_completion)
        self.chain_usecases = ChainUsecases(chains, settings.chain_prefix, settings.item_prefix, settings.host)
        self.plan_usecases = PlanUsecases(items, drafts, telemetry, TOOLS_ETC_DIR / "PLAN.template.md",
                                          settings.item_prefix, settings.host)
        self.review_usecases = ReviewUsecases(items, review_drafts, telemetry, TOOLS_ETC_DIR / "REVIEW.template.md",
                                              settings.item_prefix, settings.host)
        self.schedule_usecases = ScheduleUsecases(items, telemetry, settings.item_prefix, settings.host)
        self.lock_usecases = LockUsecases(leases, telemetry, settings.lock_names)
        self.worktree_usecases = WorktreeUsecases(worktrees, settings.item_prefix)
        self.ide_usecases = IdeUsecases(worktrees, IdeLauncherSource(), settings.item_prefix, settings.ide)
        self.telemetry_usecases = TelemetryUsecases(telemetry, transcripts, settings.item_prefix)
        self.stats_usecases = StatsUsecases(telemetry)
        self.run_log_usecases = RunLogUsecases(run_log, settings.item_prefix)
        self.system_test_usecases = SystemTestUsecases(checkout, settings.system_tests)

    @staticmethod
    def from_directory(start_dir: Path) -> AppWiring:
        """Returns the wiring for the repository that contains the directory."""
        main_root = MainRootHelper.resolve(start_dir)
        return AppWiring(SdlcSettingsHelper.load(TOOLS_ETC_DIR / "sdlc.json", main_root))

