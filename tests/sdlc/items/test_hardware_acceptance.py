import hashlib
from pathlib import Path
from typing import Callable

import pytest

from sdlc.models.artifact import ArtifactBinding
from sdlc.models.errors import InvalidTransitionError, SdlcError
from sdlc.models.item import ItemStatus, TaskStatus
from sdlc.usecases.hardware_usecases import HardwareUsecases
from sdlc.wiring import AppWiring
from tests.sdlc.items.test_item_usecases import ItemFlowHelper
from tests.sdlc.items.test_leases_and_worktrees import WorktreeGitHelper


class HardwareFixtureHelper:
    """Builds an approved image item and a promoted package without touching an image."""

    @staticmethod
    def prepare(host: AppWiring, plan_text: str) -> Path:
        """Returns a committed package in the retained integration worktree.

        Args:
            host: the disposable item ledger and worktree wiring.
            plan_text: the validated plan fixture.

        Returns:
            The path of the exact promoted artifact.
        """
        item_id = ItemFlowHelper.mint(host)
        HardwareUsecases(host).record("require", item_id, None, None, None, False)
        ItemFlowHelper.plan_and_schedule(host, item_id, plan_text)
        host.item_usecases.set_status(item_id, ItemStatus.IN_PROGRESS, False)
        host.plan_usecases.set_task_status(item_id, TaskStatus.IN_PROGRESS, ["all"])
        host.plan_usecases.set_task_status(item_id, TaskStatus.VALIDATED, ["all"])
        built = WorktreeGitHelper.built_integration(host)
        WorktreeGitHelper.commit_file(built.path, ".gitignore", "/.lets\n/.codex/worktrees\n/var\n/build\n")
        WorktreeGitHelper.commit_file(built.path, "package.deb", "simulated package bytes\n")
        host.worktree_usecases.present(item_id, None)
        tree = WorktreeGitHelper.approve_snapshot(host)
        host.worktree_usecases.settle(item_id, "Approved package", tree)
        promotion = host.worktree_usecases.prepare_promotion(item_id)
        host.worktree_usecases.promote(item_id, promotion.promotion_commit)
        host.item_usecases.set_status(item_id, ItemStatus.TESTING, False)
        host.item_usecases.set_status(item_id, ItemStatus.REVIEW, False)
        return built.path / "package.deb"


class TestHardwareAcceptance:
    """Checks developer confirmation, exact artifact identity, and failed-result retention."""

    def test_missing_confirmation_and_changed_package_block_completion(
            self, make_host: Callable[[str], AppWiring], plan_text: str, tmp_path: Path) -> None:
        """Refuses DONE until the developer confirms the exact approved package."""
        host = make_host("alpha")
        package = HardwareFixtureHelper.prepare(host, plan_text)
        host.plan_usecases.set_task_status("ITM-0001", TaskStatus.DONE, ["all"])
        with pytest.raises(InvalidTransitionError, match="real-hardware success"):
            host.item_usecases.set_status("ITM-0001", ItemStatus.DONE, False)
        notes = tmp_path / "developer.txt"
        notes.write_text("Device SCR-1, image baseline: observed expected result. Confirmed success.")
        hardware = HardwareUsecases(host)
        with pytest.raises(SdlcError, match="confirmed-by-developer"):
            hardware.record("pass", "ITM-0001", str(package), "SCR-1 baseline", str(notes), False)
        package.write_text("changed after SHOW\n")
        with pytest.raises(SdlcError, match="changed after approval|differs from"):
            hardware.record("pass", "ITM-0001", str(package), "SCR-1 baseline", str(notes), True)
        package.write_text("simulated package bytes\n")
        hardware.record("pass", "ITM-0001", str(package), "SCR-1 baseline", str(notes), True)
        package.write_text("late artifact edit\n")
        with pytest.raises(SdlcError, match="changed after hardware acceptance"):
            host.item_usecases.set_status("ITM-0001", ItemStatus.DONE, False)
        package.write_text("simulated package bytes\n")
        assert host.item_usecases.set_status("ITM-0001", ItemStatus.DONE, False).hardware.result == "pass"

    def test_failed_hardware_report_survives_rework(
            self, make_host: Callable[[str], AppWiring], plan_text: str, tmp_path: Path) -> None:
        """Keeps original symptoms and invalidates hardware success when implementation resumes."""
        host = make_host("alpha")
        package = HardwareFixtureHelper.prepare(host, plan_text)
        notes = tmp_path / "developer.txt"
        notes.write_text("Observed RS485 response missing after restart.")
        hardware = HardwareUsecases(host)
        failed = hardware.record("fail", "ITM-0001", str(package), "SCR-1 baseline", str(notes), False)
        assert failed.hardware.result == "fail"
        assert failed.hardware.notes == notes.read_text()
        passed = hardware.record("pass", "ITM-0001", str(package), "SCR-1 baseline", str(notes), True)
        assert passed.hardware.result == "pass"
        restarted = host.item_usecases.set_status("ITM-0001", ItemStatus.IN_PROGRESS, False)
        assert restarted.hardware.result is None
        assert any("RS485 response missing" in entry.detail for entry in restarted.history)

    def test_ignored_build_package_matches_approved_input_artifact(
            self, make_host: Callable[[str], AppWiring], plan_text: str, tmp_path: Path,
            monkeypatch: pytest.MonkeyPatch) -> None:
        """Accepts an ignored package when its bytes match approved INPUT evidence."""
        host = make_host("alpha")
        committed_package = HardwareFixtureHelper.prepare(host, plan_text)
        package_bytes = committed_package.read_bytes()
        build_package = committed_package.parent / "build" / committed_package.name
        build_package.parent.mkdir()
        build_package.write_bytes(package_bytes)

        context = host.worktree_usecases.context("ITM-0001")
        input_path = tmp_path / "input"
        evidence_package = input_path / "items" / "ITM-0001" / committed_package.name
        evidence_package.parent.mkdir(parents=True)
        evidence_package.write_bytes(package_bytes)
        digest = "a" * 64
        binding = ArtifactBinding(
            item_id="ITM-0001", purpose="INPUT", stage="implementation", digest=digest,
            ledger_path=f"artifacts/bundles/{digest}.json", snapshot_path=input_path,
            source_tree=context.approved_tree,
        )
        monkeypatch.setattr(
            host.worktree_usecases, "context",
            lambda _: context.model_copy(update={"snapshot_artifacts": binding,
                                                   "approved_artifacts": digest}),
        )
        monkeypatch.setattr(host.artifact_usecases, "verify_review", lambda *_: None)
        notes = tmp_path / "developer.txt"
        notes.write_text("Developer confirmed acceptance of the exact package.")

        accepted = HardwareUsecases(host).record(
            "pass", "ITM-0001", str(build_package), "SCR-1 baseline", str(notes), True,
        )

        assert accepted.hardware.result == "pass"
        assert accepted.hardware.package_sha256 == hashlib.sha256(package_bytes).hexdigest()
