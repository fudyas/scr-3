from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import errno
import hashlib
import importlib.util
import json
import locale
import os
import shlex
import subprocess
from abc import ABC
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Union
from unittest.mock import Mock

import pytest

from sdlc.controllers import safety_cli
from sdlc.controllers.safety_cli import SafetyCliHelper
from sdlc.models.item import HardwareAcceptance, Item, ItemKind, ItemStatus, PlanState
from sdlc.wiring import AppWiring

# Selects the retained safety engine under test
MODULE_PATH = Path(__file__).parents[2] / "tools/sdlc/src/sdlc.py"
# Loads a separate engine identity for isolated monkeypatches
SPEC = importlib.util.spec_from_file_location("scr_sdlc", MODULE_PATH)
assert SPEC and SPEC.loader
sdlc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sdlc)


class SdlcTestClock(dt.datetime):
    """Supplies a fixed UTC clock for generated package metadata."""

    @classmethod
    def now(cls, tz: Optional[dt.tzinfo] = None) -> dt.datetime:
        """Returns the fixed package timestamp in the requested timezone.

        Args:
            tz: Selects the output timezone.

        Returns:
            The fixed timestamp.
        """
        fixed = cls(2024, 1, 2, 3, 4, 5, tzinfo=dt.timezone.utc)
        return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)


class SdlcTestHelper(ABC):
    """Creates isolated repositories for retained safety commands."""

    @staticmethod
    def _git(root: Path, *args: str) -> None:
        """Runs Git in an isolated test repository.

        Args:
            root: Selects the isolated repository.
            args: Supplies Git arguments.

        Raises:
            subprocess.CalledProcessError: Git rejects the fixture operation.
        """
        # Limits Git effects to the disposable test repository
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)

    @staticmethod
    def repo(tmp_path: Path) -> Path:
        """Creates an isolated repository with retained SDLC configuration.

        Args:
            tmp_path: Supplies isolated temporary paths.

        Returns:
            The isolated repository.
        """
        # Seeds a disposable repository with local ledger configuration
        SdlcTestHelper._git(tmp_path, "init", "-b", "main")
        SdlcTestHelper._git(tmp_path, "config", "user.name", "SDLC Test")
        SdlcTestHelper._git(tmp_path, "config", "user.email", "sdlc@example.invalid")

        # Keeps runtime worktrees outside the fixture's tracked source
        (tmp_path / "etc").mkdir()
        (tmp_path / "etc/sdlc.conf").write_text(
            'SDLC_LEDGER_BRANCH="sdlc"\nSDLC_AUTO_PUSH="0"\n'
            'SDLC_VERIFY_EXCLUDES="/proc,/sys"\n', encoding="utf-8")
        (tmp_path / ".gitignore").write_text("/.codex/worktrees/\n/.codex/sdlc/\n", encoding="utf-8")
        (tmp_path / "README.md").write_text("test\n", encoding="utf-8")

        # Gives retained ledger operations a committed local base
        SdlcTestHelper._git(tmp_path, "add", "README.md", ".gitignore", "etc/sdlc.conf")
        SdlcTestHelper._git(tmp_path, "commit", "-m", "Initial test repository")
        return tmp_path

# Registers the repository fixture without an additional wrapper
repo = pytest.fixture(name="repo")(SdlcTestHelper.repo)


class TestSdlc:
    """Verifies SDLC command boundaries and disposable package safety."""

    @staticmethod
    @pytest.mark.parametrize("failure", [None, "install", "installed", "remove", "rollback"])
    def test_dpkg_rollback_contract(
            repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: Optional[str]) -> None:
        """Verifies package cleanup and quarantine without metadata fingerprints.

        Args:
            repo: Supplies an isolated repository.
            tmp_path: Supplies disposable paths.
            monkeypatch: Replaces external package processes.
            failure: Selects the failed package operation.
        """
        # Prepares a disposable root and prohibits metadata scans
        ctx = sdlc.Context(repo)
        root = tmp_path / "root"
        root.mkdir()
        deb = tmp_path / "change.deb"
        deb.write_bytes(b"test")
        monkeypatch.setattr(sdlc.SdlcPackageHelper, "package_name", Mock(return_value="scr-example"))
        monkeypatch.setattr(sdlc.SdlcPackageHelper, "package_install_command", Mock(return_value=["install"]))
        monkeypatch.setattr(sdlc.SdlcPackageHelper, "fingerprint_tree", Mock(side_effect=AssertionError("metadata scan")))
        commands = []

        def run(command: List[str], **kwargs: bool) -> subprocess.CompletedProcess[str]:
            """Simulates package operations and captures their order.

            Args:
                command: Supplies the process arguments.
                kwargs: Supplies process execution options.

            Returns:
                The selected process result.

            Raises:
                SDLCError: The selected checked command fails.
            """
            # Maps only the expected package and project assertion operations
            assert command[:2] == ["chroot", str(root)]
            operation = command[-1]
            if command[2] == "/usr/bin/dpkg":
                operation = "install" if command[3] == "-i" else "remove"
                if operation == "install":
                    assert (root / command[4].lstrip("/")).read_bytes() == b"test"
                else:
                    assert command[3:] == ["-r", "scr-example"]
            commands.append(operation)
            if operation == failure and kwargs.get("check", True):
                raise sdlc.SDLCError(f"{operation} failed")
            return subprocess.CompletedProcess(command, int(operation == failure), "", "")

        # Requires cleanup after install failure and quarantines failed rollback
        monkeypatch.setattr(sdlc.SdlcRuntimeHelper, "run", run)
        args = argparse.Namespace(root=str(root), deb=str(deb), recover=False,
                                  test_command="installed", rollback_command="rollback")
        if failure:
            with pytest.raises(sdlc.SDLCError):
                sdlc.SdlcPackageHelper.cmd_verify_package(ctx, args)
        else:
            sdlc.SdlcPackageHelper.cmd_verify_package(ctx, args)
        expected = ["install"] + ([] if failure == "install" else ["installed"]) + ["remove", "rollback"]
        assert commands == expected
        assert not list(root.glob(".sdlc-*.deb"))
        assert (ctx.lock_root / "quarantine/image-dirty.json").exists() == (failure in {"remove", "rollback"})

    @staticmethod
    def test_dpkg_rollback_cannot_release_quarantine(repo: Path, tmp_path: Path) -> None:
        """Refuses recovery through a weaker rollback contract.

        Args:
            repo: Supplies an isolated repository.
            tmp_path: Supplies disposable paths.
        """
        # Refuses recovery before any package process can run
        deb = tmp_path / "change.deb"
        deb.write_bytes(b"test")
        args = argparse.Namespace(root=str(tmp_path), deb=str(deb), recover=True, rollback_command="true")
        with pytest.raises(sdlc.SDLCError, match="cannot release a quarantined image"):
            sdlc.SdlcPackageHelper.cmd_verify_package(sdlc.Context(repo), args)

    """Checks retained CLI behavior and image-safety boundaries."""

    @staticmethod
    def test_models_preserves_configured_rows_and_main_checkout_resolution(
            repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
        """Checks configured routing, missing values, and main-checkout model dispatch.

        Args:
            repo: Supplies an isolated repository for model dispatch.
            capsys: Captures model-list output.
            monkeypatch: Selects the temporary main checkout for CLI dispatch.
        """
        # Checks every role against the actual project configuration
        configured_ctx = sdlc.Context(MODULE_PATH.parents[3])
        sdlc.SdlcCliHelper.cmd_models(configured_ctx, argparse.Namespace())
        expected_rows = [
            "coordinator\tgpt-6.1-sol\thigh",
            "requirements\tgpt-6-astra\txhigh",
            "image_analysis\tgpt-6.1-terra\thigh",
            "planner\tgpt-6-astra\thigh",
            "implementation\tgpt-6.1-sol\thigh",
            "validation\tgpt-6-astra\thigh",
            "integration\tgpt-6-astra\thigh",
            "qa\tgpt-6-astra\thigh",
            "follow_up\tgpt-6.1-sol\thigh",
        ]
        assert capsys.readouterr().out.splitlines() == expected_rows

        # Keeps missing QA configuration visible for dispatch preflight
        ctx = sdlc.Context(repo)
        sdlc.SdlcCliHelper.cmd_models(ctx, argparse.Namespace())
        assert "qa\t\t" in capsys.readouterr().out.splitlines()

        # Exercises main-root CLI resolution with the exact candidate configuration
        conf_path = repo / "etc/sdlc.conf"
        fixture_configuration = conf_path.read_text(encoding="utf-8")
        candidate_configuration = (configured_ctx.root / "etc/sdlc.conf").read_text(encoding="utf-8")
        conf_path.write_text(candidate_configuration, encoding="utf-8")
        monkeypatch.chdir(repo)
        assert SafetyCliHelper.main(["models"]) == 0
        assert capsys.readouterr().out.splitlines() == expected_rows
        conf_path.write_text(fixture_configuration, encoding="utf-8")

    @staticmethod
    def test_main_tree_lock_key_is_shared_by_linked_worktrees(repo: Path, tmp_path: Path) -> None:
        """Uses one Git-common-directory lock across repository worktrees.

        Args:
            repo: Supplies an isolated repository.
            tmp_path: Supplies isolated temporary paths.
        """
        # Uses one Git-common-directory lock across repository worktrees
        linked = tmp_path / "linked"
        SdlcTestHelper._git(repo, "worktree", "add", "-b", "linked", str(linked))
        (linked / "etc/sdlc.conf").write_text(
            'SDLC_LEDGER_BRANCH="sdlc"\nSDLC_AUTO_PUSH="0"\n', encoding="utf-8")
        main_ctx = sdlc.Context(repo)
        linked_ctx = sdlc.Context(linked)
        assert main_ctx.main_tree_lock_root == linked_ctx.main_tree_lock_root
        with main_ctx.lock("main-tree") as main_lock:
            assert main_lock == main_ctx.main_tree_lock_root / "main-tree.lock"

    @staticmethod
    def test_fingerprint_detects_content_and_mode_changes(tmp_path: Path) -> None:
        """Checks payload, permission, and empty-directory fingerprints.

        Args:
            tmp_path: Supplies isolated temporary paths.
        """
        # Checks payload, permission, and empty-directory fingerprints
        root = tmp_path / "root"
        root.mkdir()
        target = root / "etc.conf"
        target.write_text("a", encoding="utf-8")
        before = sdlc.SdlcPackageHelper.fingerprint_tree(root, [])
        target.write_text("b", encoding="utf-8")
        after = sdlc.SdlcPackageHelper.fingerprint_tree(root, [])
        assert before != after

        # Checks permission sensitivity through the recorded mode field
        before_mode = sdlc.SdlcPackageHelper.fingerprint_tree(root, [])
        target.chmod(target.stat().st_mode ^ 0o100)
        after_mode = sdlc.SdlcPackageHelper.fingerprint_tree(root, [])
        assert before_mode != after_mode
        assert before_mode["/etc.conf"]["mode"] != after_mode["/etc.conf"]["mode"]
        empty = root / "empty"
        empty.mkdir()
        assert "/empty" in sdlc.SdlcPackageHelper.fingerprint_tree(root, [])

    @staticmethod
    def test_fingerprint_detects_timestamp_changes(tmp_path: Path) -> None:
        """Detects restored content carrying changed filesystem timestamps.

        Args:
            tmp_path: Supplies isolated temporary paths.
        """
        # Detects restored content carrying changed filesystem timestamps
        root = tmp_path / "root"
        root.mkdir()
        target = root / "value"
        target.write_text("same", encoding="utf-8")
        before = sdlc.SdlcPackageHelper.fingerprint_tree(root, [])
        stat = target.stat()
        os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
        assert before != sdlc.SdlcPackageHelper.fingerprint_tree(root, [])

    @staticmethod
    def test_fingerprint_detects_hardlink_relationship_changes(tmp_path: Path) -> None:
        """Detects replacement of one hard link by an independent identical file.

        Args:
            tmp_path: Supplies isolated temporary paths.
        """
        # Detects replacement of one hard link by an independent identical file
        root = tmp_path / "root"
        root.mkdir()
        first = root / "first"
        second = root / "second"
        first.write_text("same", encoding="utf-8")
        os.link(first, second)
        before = sdlc.SdlcPackageHelper.fingerprint_tree(root, [])
        second.unlink()
        second.write_text("same", encoding="utf-8")
        stat = first.stat()
        os.utime(second, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        assert before != sdlc.SdlcPackageHelper.fingerprint_tree(root, [])

    @staticmethod
    def test_fingerprint_detects_xattr_changes(tmp_path: Path) -> None:
        """Detects changed extended attributes when filesystem supports user xattrs.

        Args:
            tmp_path: Supplies isolated temporary paths.
        """
        # Detects changed extended attributes when filesystem supports user xattrs
        root = tmp_path / "root"
        root.mkdir()
        target = root / "value"
        target.write_text("same", encoding="utf-8")
        try:
            os.setxattr(target, "user.sdlc-test", b"before")
        except OSError as exc:
            if exc.errno in {errno.ENOTSUP, errno.EOPNOTSUPP}:
                pytest.skip("test filesystem lacks user xattrs")
            raise
        before = sdlc.SdlcPackageHelper.fingerprint_tree(root, [])
        os.setxattr(target, "user.sdlc-test", b"after")
        assert before != sdlc.SdlcPackageHelper.fingerprint_tree(root, [])

    @staticmethod
    def test_fingerprint_records_root_and_directory_symlink(tmp_path: Path) -> None:
        """Records mount-root metadata and directory links without following them.

        Args:
            tmp_path: Supplies isolated temporary paths.
        """
        # Records mount-root metadata and directory links without following them
        root = tmp_path / "root"
        root.mkdir()
        target = root / "target"
        target.mkdir()
        link = root / "linked-directory"
        link.symlink_to(target, target_is_directory=True)
        fingerprint = sdlc.SdlcPackageHelper.fingerprint_tree(root, [])
        assert fingerprint["/"]["type"] == "directory"
        assert fingerprint["/linked-directory"]["type"] == "symlink"
        assert fingerprint["/linked-directory"]["link"] == str(target)

    @staticmethod
    def test_image_lock_rechecks_global_quarantine_after_flock(
            repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Rejects quarantine created between image-lock preflight and acquisition.

        Args:
            repo: Supplies an isolated repository.
            monkeypatch: Replaces external effects within the test.
        """
        # Rejects quarantine created between image-lock preflight and acquisition
        ctx = sdlc.Context(repo)
        original_flock = sdlc.fcntl.flock
        created = False

        def racing_flock(fd: int, operation: int) -> None:
            """Creates quarantine when exclusive flock succeeds.

            Args:
                fd: Identifies the real temporary lock descriptor.
                operation: Supplies the requested flock operation.
            """
            # Introduces quarantine in the preflight-to-acquisition race window
            nonlocal created
            original_flock(fd, operation)
            if operation & sdlc.fcntl.LOCK_EX and not created:
                created = True
                sdlc.SdlcRuntimeHelper.atomic_json(ctx.lock_root / "quarantine/image-dirty.json", {"phase": "quarantined"})

        monkeypatch.setattr(sdlc.fcntl, "flock", racing_flock)
        with pytest.raises(sdlc.SDLCError, match="logically locked by quarantine"):
            with ctx.lock("image"):
                pytest.fail("quarantined image work started")

    @staticmethod
    def test_verify_package_fingerprint_failure_quarantines(
            repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Quarantines image when initial restoration fingerprint cannot be read.

        Args:
            repo: Supplies an isolated repository.
            tmp_path: Supplies isolated temporary paths.
            monkeypatch: Replaces external effects within the test.
        """
        # Quarantines image when initial restoration fingerprint cannot be read
        ctx = sdlc.Context(repo)
        root = tmp_path / "mounted"
        root.mkdir()
        deb = tmp_path / "package.deb"
        deb.write_bytes(b"deb")
        monkeypatch.setattr(sdlc.SdlcPackageHelper, "package_name", Mock(return_value="test-package"))
        monkeypatch.setattr(sdlc.SdlcPackageHelper, "fingerprint_tree", Mock(side_effect=OSError("read failed")))
        monkeypatch.setattr(sdlc.subprocess, "run", Mock(side_effect=pytest.fail.Exception("unexpected process")))
        args = argparse.Namespace(root=str(root), deb=str(deb), recover=False, test_command=None)
        with pytest.raises(sdlc.SDLCError, match="fingerprint failed and was quarantined"):
            sdlc.SdlcPackageHelper.cmd_verify_package(ctx, args)
        identity = sdlc.hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:20]
        assert (ctx.lock_root / f"quarantine/image-{identity}.json").is_file()
        assert (ctx.lock_root / "quarantine/image-dirty.json").is_file()

    @staticmethod
    def test_package_install_command_allows_proven_cross_architecture_root(
            tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Forces architecture only when the package matches the image package database.

        Args:
            tmp_path: Supplies isolated temporary paths.
            monkeypatch: Replaces external effects within the test.
        """
        # Forces architecture only when the package matches the image package database
        root = tmp_path / "root"
        status = root / "var/lib/dpkg/status"
        status.parent.mkdir(parents=True)
        status.write_text(
            "Package: base-files\nStatus: install ok installed\nArchitecture: armhf\n\n"
            "Package: scripts\nStatus: install ok installed\nArchitecture: all\n",
            encoding="utf-8",
        )
        deb = tmp_path / "counter.deb"
        deb.write_bytes(b"deb")
        monkeypatch.setattr(sdlc.SdlcPackageHelper, "package_architecture", Mock(return_value="armhf"))
        def host_architecture(command: List[str]) -> subprocess.CompletedProcess[str]:
            """Returns the simulated host architecture for the expected query.

            Args:
                command: Supplies the architecture query.

            Returns:
                The simulated host architecture.
            """
            assert command == ["dpkg", "--print-architecture"]
            return subprocess.CompletedProcess(command, 0, "amd64\n", "")

        monkeypatch.setattr(sdlc.SdlcRuntimeHelper, "run", host_architecture)
        monkeypatch.setattr(sdlc.subprocess, "run", Mock(side_effect=pytest.fail.Exception("unexpected process")))

        command = sdlc.SdlcPackageHelper.package_install_command(root, deb)

        assert command[-3:] == ["--force-architecture", "-i", str(deb)]

    @staticmethod
    def test_package_install_command_rejects_target_architecture_mismatch(
            tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Refuses host override when package and image architectures differ.

        Args:
            tmp_path: Supplies isolated temporary paths.
            monkeypatch: Replaces external effects within the test.
        """
        # Refuses host override when package and image architectures differ
        root = tmp_path / "root"
        status = root / "var/lib/dpkg/status"
        status.parent.mkdir(parents=True)
        status.write_text(
            "Package: base-files\nStatus: install ok installed\nArchitecture: armhf\n",
            encoding="utf-8",
        )
        deb = tmp_path / "counter.deb"
        deb.write_bytes(b"deb")
        monkeypatch.setattr(sdlc.SdlcPackageHelper, "package_architecture", Mock(return_value="amd64"))
        monkeypatch.setattr(sdlc.subprocess, "run", Mock(side_effect=pytest.fail.Exception("unexpected process")))

        with pytest.raises(sdlc.SDLCError, match="does not match target root"):
            sdlc.SdlcPackageHelper.package_install_command(root, deb)

    @staticmethod
    def test_failed_mount_attempts_cleanup_and_quarantines_if_still_mounted(
            repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Attempts cleanup after partial mount and quarantines unproved cleanup.

        Args:
            repo: Supplies an isolated repository.
            tmp_path: Supplies isolated temporary paths.
            monkeypatch: Replaces external effects within the test.
        """
        # Attempts cleanup after partial mount and quarantines unproved cleanup
        ctx = sdlc.Context(repo)
        image = tmp_path / "image.img"
        image.write_bytes(b"image")
        deb = tmp_path / "package.deb"
        deb.write_bytes(b"deb")
        active_state = repo / ".lets/scr/image/mount.state"
        calls = []

        def fake_run(command: List[str], **_kwargs: Union[Path, bool]) -> subprocess.CompletedProcess[str]:
            """Simulates partial mount followed by failed unmount.

            Args:
                command: Supplies the copy, mount, or unmount invocation.
                _kwargs: Supplies process options.

            Returns:
                The simulated copy or failed-unmount result.

            Raises:
                subprocess.CalledProcessError: The simulated mount fails partway.
            """
            # Records only bounded copy and image-tool invocations
            calls.append(command)
            if command[0] == "cp":
                assert command[1:-1] == ["--reflink=auto", "--sparse=always", "--", str(image)]
                Path(command[-1]).write_bytes(image.read_bytes())
                return subprocess.CompletedProcess(command, 0, "", "")
            if command[-1] == "--rw":
                assert command[:5] == [str(repo / "bin/lets"), "scr", "image", "mount", "--image"]
                active_state.parent.mkdir(parents=True, exist_ok=True)
                active_state.write_text("partial", encoding="utf-8")
                raise subprocess.CalledProcessError(1, command)
            assert command == [str(repo / "bin/lets"), "scr", "image", "umount"]
            return subprocess.CompletedProcess(command, 1, "", "")

        monkeypatch.setattr(sdlc.subprocess, "run", Mock(side_effect=pytest.fail.Exception("unexpected process")))
        monkeypatch.setattr(sdlc.SdlcRuntimeHelper, "run", fake_run)
        args = argparse.Namespace(id="REQ-0001-TEST", image=str(image), deb=str(deb), test_command=None)
        with pytest.raises(sdlc.SDLCError, match="cleanup failed and was quarantined"):
            sdlc.SdlcPackageHelper.cmd_test_package(ctx, args)
        assert any(command[-2:] == ["image", "umount"] for command in calls)
        assert (ctx.lock_root / "quarantine/image-dirty.json").is_file()

    @staticmethod
    def test_scratch_cleanup_failure_quarantines(
            repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Quarantines image when disposable scratch cannot be removed.

        Args:
            repo: Supplies an isolated repository.
            tmp_path: Supplies isolated temporary paths.
            monkeypatch: Replaces external effects within the test.
        """
        # Quarantines image when disposable scratch cannot be removed
        ctx = sdlc.Context(repo, repo / "candidate")
        image = tmp_path / "image.img"
        image.write_bytes(b"image")
        deb = tmp_path / "package.deb"
        deb.write_bytes(b"deb")

        def fake_run(command: List[str], **_kwargs: Union[Path, bool]) -> subprocess.CompletedProcess[str]:
            """Simulates successful copy, mount, and unmount commands.

            Args:
                command: Supplies the copy, mount, or unmount invocation.
                _kwargs: Supplies process options.

            Returns:
                A successful simulated process result.
            """
            # Rejects every process shape outside the disposable test sequence
            if command[0] == "cp":
                assert command[1:-1] == ["--reflink=auto", "--sparse=always", "--", str(image)]
                Path(command[-1]).write_bytes(image.read_bytes())
            elif command[-1] == "--rw":
                assert command[:5] == [str(repo / "bin/lets"), "scr", "image", "mount", "--image"]
            else:
                assert command == [str(repo / "bin/lets"), "scr", "image", "umount"]
            return subprocess.CompletedProcess(command, 0, "", "")

        monkeypatch.setattr(sdlc.SdlcRuntimeHelper, "run", fake_run)

        def verify_process(command: List[str], **_kwargs: Union[Path, bool, Dict[str, str]]) -> subprocess.CompletedProcess[str]:
            """Returns success only for the simulated package verifier.

            Args:
                command: Supplies the verifier invocation.
                _kwargs: Supplies process options.

            Returns:
                The simulated verifier result.
            """
            assert command[:3] == [str(repo / "candidate/bin/lets"), "sdlc", "verify-package"]
            assert command[-2:] == ["--rollback-command", "check-project-rollback"]
            assert _kwargs["cwd"] == repo / "candidate"
            return subprocess.CompletedProcess(command, 0, "", "")

        monkeypatch.setattr(sdlc.subprocess, "run", verify_process)
        monkeypatch.setattr(sdlc.shutil, "rmtree", Mock(side_effect=OSError("scratch busy")))
        args = argparse.Namespace(id="REQ-0001-TEST", image=str(image), deb=str(deb), test_command=None,
                                  rollback_command="check-project-rollback")
        with pytest.raises(sdlc.SDLCError, match="scratch cleanup failed and was quarantined"):
            sdlc.SdlcPackageHelper.cmd_test_package(ctx, args)
        assert (ctx.lock_root / "quarantine/image-dirty.json").is_file()

    @staticmethod
    def test_managed_paths_must_be_safe_absolute_paths() -> None:
        """Checks managed-path acceptance and traversal refusal.
        """
        # Checks managed-path acceptance and traversal refusal
        assert sdlc.SdlcPackageHelper.validate_managed_path("/etc/monitrc") == "/etc/monitrc"
        for value in ("etc/monitrc", "/", "/etc/../root"):
            with pytest.raises(sdlc.SDLCError):
                sdlc.SdlcPackageHelper.validate_managed_path(value)

    @staticmethod
    def test_package_scaffold_contains_reversible_maintainer_scripts(repo: Path) -> None:
        """Checks reversible scaffold scripts and package metadata.

        Args:
            repo: Supplies an isolated repository.
        """
        # Checks reversible scaffold scripts and package metadata
        ctx = sdlc.Context(repo)
        req_id = "ITM-0002"
        output = repo / "implementation"
        sdlc.SdlcPackageHelper.cmd_package_init(ctx, argparse.Namespace(
            id=req_id, package=None, output=str(output), force=False,
            operation=["replace:/etc/monit/monitrc", "move:/etc/old.conf:/etc/new.conf"],
        ), {"id": req_id, "state": "implementing", "current_round": 1})
        package_root = output / "packages" / f"{req_id}-round-1"
        for script in ("preinst", "postinst", "postrm"):
            subprocess.run(["sh", "-n", str(package_root / "debian" / script)], check=True)
        assert "SDLC path overlap" in (package_root / "debian/preinst").read_text(encoding="utf-8")
        assert "sdlc-backup" in (package_root / "debian/postrm").read_text(encoding="utf-8")
        control = (package_root / "debian/control").read_text(encoding="utf-8")
        assert f"Package: scr-{req_id.lower()}\n" in control

    @staticmethod
    @pytest.mark.parametrize("arguments, expected", [
        (["models"], {"command": "models"}),
        (["package-init", "ITM-0002", "--package", "scr-example", "--output", "/work/block",
          "--operation", "replace:/etc/example", "--operation", "delete:/etc/old", "--force"],
         {"command": "package-init", "id": "ITM-0002", "package": "scr-example",
          "output": "/work/block", "operation": ["replace:/etc/example", "delete:/etc/old"], "force": True}),
        (["verify-package", "ITM-0002", "--root", "/root", "--deb", "/change.deb",
          "--test-command", "service example status", "--recover"],
         {"command": "verify-package", "id": "ITM-0002", "root": "/root", "deb": "/change.deb",
          "test_command": "service example status", "recover": True, "rollback_command": None}),
        (["test-package", "ITM-0002", "--image", "/source.img", "--deb", "/change.deb"],
         {"command": "test-package", "id": "ITM-0002", "image": "/source.img",
          "deb": "/change.deb", "test_command": None, "rollback_command": None}),
        (["test-package", "ITM-0007", "--image", "/source.img", "--deb", "/change.deb",
          "--rollback-command", "test ! -e /usr/bin/scr-raom"],
         {"command": "test-package", "id": "ITM-0007", "image": "/source.img", "deb": "/change.deb",
          "test_command": None, "rollback_command": "test ! -e /usr/bin/scr-raom"}),
        (["lock-run", "--image", "/source.img", "--", "printf", "%s", "two words"],
         {"image": "/source.img", "command": ["--", "printf", "%s", "two words"]}),
    ])
    def test_safety_parser_preserves_arguments(
            arguments: List[str], expected: Dict[str, Union[str, bool, List[str], None]]) -> None:
        """Checks retained safety arguments, repeated operations, and command remainder.

        Args:
            arguments: Supplies one retained safety command.
            expected: Supplies its public argument values.
        """
        # Checks the user-facing argument contract without executing callbacks
        parsed = vars(sdlc.SdlcCliHelper.parser().parse_args(arguments))
        assert callable(parsed.pop("func"))
        assert parsed == expected

    @staticmethod
    @pytest.mark.parametrize("command", [
        "init", "new", "list", "show", "path", "status", "stage", "checkpoint", "section",
        "approve", "follow-up", "abandon", "resume", "trivial-policy", "continuation-policy",
        "implement", "task-plan", "task-next", "brief", "task-result", "task-validate",
        "acceptance", "validate", "worktree", "implementation-commit", "validation-result", "merge",
    ])
    def test_retired_entry_points_refuse_before_repository_access(
            tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
            command: str) -> None:
        """Checks retired-command refusal before either entry point accesses a repository.

        Args:
            tmp_path: Supplies a directory without repository context.
            monkeypatch: Blocks repository access and supplies command arguments.
            capsys: Captures exact refusal diagnostics.
            command: Selects one retired command name.
        """
        # Preserves real legacy evidence while blocking repository resolution
        legacy = tmp_path / "docs/requirements/REQ-0001-EXISTING.json"
        legacy.parent.mkdir(parents=True)
        legacy.write_bytes(b'{"evidence":"retain exact bytes"}\n')
        legacy.chmod(0o640)
        original = legacy.stat()
        paths = sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*"))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sdlc.SdlcRuntimeHelper, "repo_root", Mock(side_effect=AssertionError("repository accessed")))
        monkeypatch.setattr(safety_cli.MainRootHelper, "resolve", Mock(side_effect=AssertionError("repository accessed")))
        monkeypatch.setattr(sdlc.sys, "argv", ["sdlc.py", command, "--description", "retired"])
        assert sdlc.SdlcCliHelper.main() == 1
        assert capsys.readouterr().err == "error: legacy ceremony retired; use ./bin/lets sdlc items --help\n"
        assert SafetyCliHelper.main([command, "--description", "retired"]) == 1
        assert capsys.readouterr().err == "error: retired ceremony command\n"

        # Detects scaffold creation and changes to retained legacy bytes or metadata
        assert sorted(str(path.relative_to(tmp_path)) for path in tmp_path.rglob("*")) == paths
        assert legacy.read_bytes() == b'{"evidence":"retain exact bytes"}\n'
        retained = legacy.stat()
        assert (retained.st_mode, retained.st_mtime_ns, retained.st_uid, retained.st_gid) == (
            original.st_mode, original.st_mtime_ns, original.st_uid, original.st_gid)

    @staticmethod
    def test_package_init_without_approved_state_refuses_before_legacy_read_or_output(
            repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Checks absent item approval before legacy reads or scaffold writes.

        Args:
            repo: Supplies an isolated repository and retained legacy evidence.
            monkeypatch: Rejects legacy reads and repository commands.
        """
        # Supplies real legacy state that cannot authorize a scaffold
        ctx = sdlc.Context(repo)
        legacy = repo / "docs/requirements/REQ-0001-EXISTING/state.json"
        legacy.parent.mkdir(parents=True)
        legacy.write_bytes(b'{"state":"approved","current_round":1}\n')
        legacy.chmod(0o640)
        original = legacy.stat()
        output = repo / "forbidden-output"
        original_read = Path.read_text

        def reject_legacy_read(path: Path, *args: str, **kwargs: str) -> str:
            """Rejects access to the synthetic legacy state.

            Args:
                path: Selects the requested file.
                args: Supplies text-read positional options.
                kwargs: Supplies text-read named options.

            Returns:
                The text from other files.

            Raises:
                AssertionError: The scaffold reads legacy state.
            """
            assert path != legacy, "legacy state accessed"
            return original_read(path, *args, **kwargs)

        # Blocks fallback before any process or legacy state lookup
        monkeypatch.setattr(Path, "read_text", reject_legacy_read)
        monkeypatch.setattr(sdlc.SdlcRuntimeHelper, "git", Mock(side_effect=AssertionError("repository accessed")))
        args = argparse.Namespace(id="REQ-0001-EXISTING", package=None, output=str(output), force=False,
                                  operation=["replace:/etc/example"])
        with pytest.raises(sdlc.SDLCError, match="^package scaffolding requires approved item state$"):
            sdlc.SdlcPackageHelper.cmd_package_init(ctx, args)
        assert not output.exists()
        assert legacy.read_bytes() == b'{"state":"approved","current_round":1}\n'
        retained = legacy.stat()
        assert (retained.st_mode, retained.st_mtime_ns, retained.st_uid, retained.st_gid) == (
            original.st_mode, original.st_mtime_ns, original.st_uid, original.st_gid)

    @staticmethod
    @pytest.mark.parametrize("adapter", [False, True])
    @pytest.mark.parametrize("remainder, expected, outcome", [
        (["--", "printf", "--flag", "two words"], ["printf", "--flag", "two words"], "success"),
        (["printf", "--flag", "two words"], ["printf", "--flag", "two words"], "success"),
        (["--", "--", "two words"], ["--", "two words"], "success"),
        (["--"], [], "empty"),
        (["--", "printf", "--flag", "two words"], ["printf", "--flag", "two words"], "exit"),
        (["--", "printf", "--flag", "two words"], ["printf", "--flag", "two words"], "error"),
    ])
    def test_lock_run_entry_points_preserve_remainder_and_hold_image_lock(
            repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
            adapter: bool, remainder: List[str], expected: List[str], outcome: str) -> None:
        """Checks command dispatch with real temporary locks and simulated process effects.

        Args:
            repo: Supplies an isolated repository and lock directory.
            monkeypatch: Bounds process execution and repository resolution.
            capsys: Captures exact child-error diagnostics.
            adapter: Selects the public safety adapter or retained engine entry point.
            remainder: Supplies command arguments after the image path.
            expected: Supplies exact child arguments after separator removal.
            outcome: Selects child success, failure, exception, or absent command.
        """
        # Creates the context before replacing process effects
        engine = safety_cli.LEGACY if adapter else sdlc
        ctx = engine.Context(repo)
        original_lock = ctx.lock
        locked = False
        calls: List[List[str]] = []

        @contextlib.contextmanager
        def recording_lock(name: str, timeout: Optional[int] = None) -> Iterator[Path]:
            """Records the real shared lock around simulated command execution.

            Args:
                name: Selects the image lock.
                timeout: Supplies the lock timeout.

            Yields:
                The temporary image lock path.
            """
            nonlocal locked
            assert name == "image"
            with original_lock(name, timeout) as path:
                locked = True
                try:
                    yield path
                finally:
                    locked = False

        def process(command: List[str], check: bool) -> subprocess.CompletedProcess[str]:
            """Checks exact remainder dispatch while the image lock remains held.

            Args:
                command: Supplies the parsed command remainder.
                check: Supplies the process error policy.

            Returns:
                A successful simulated command result.

            Raises:
                OSError: The selected child process cannot start.
            """
            assert locked
            assert command == expected
            assert check is False
            calls.append(command)
            if outcome == "error":
                raise OSError("synthetic child failed")
            return subprocess.CompletedProcess(command, 7 if outcome == "exit" else 0)

        # Exercises parser and callback dispatch through each retained entry point
        monkeypatch.setattr(engine, "Context", Mock(return_value=ctx))
        monkeypatch.setattr(ctx, "lock", recording_lock)
        monkeypatch.setattr(engine.subprocess, "run", process)
        monkeypatch.setattr(sdlc.SdlcRuntimeHelper, "repo_root", Mock(return_value=repo))
        monkeypatch.setattr(safety_cli.MainRootHelper, "resolve", Mock(return_value=repo))
        arguments = ["lock-run", "--image", str(repo / "synthetic.img"), *remainder]
        if adapter:
            result = SafetyCliHelper.main(arguments)
        else:
            monkeypatch.setattr(sdlc.sys, "argv", ["sdlc.py", *arguments])
            result = sdlc.SdlcCliHelper.main()

        # Proves failure and exceptions release the same real temporary lock
        errors = {"empty": "missing command after --", "exit": "locked command failed with exit code 7",
                  "error": "synthetic child failed"}
        assert result == (0 if outcome == "success" else 1)
        assert capsys.readouterr().err == (f"error: {errors[outcome]}\n" if outcome in errors else "")
        assert calls == ([] if outcome == "empty" else [expected])
        assert not locked
        with original_lock("image", timeout=0):
            assert not locked

    @staticmethod
    def test_safety_adapter_catches_its_loaded_engine_error(
            repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        """Checks error identity across independently loaded copies of the safety engine.

        Args:
            repo: Supplies an isolated repository.
            monkeypatch: Replaces the adapter callback with a controlled refusal.
            capsys: Captures the adapter diagnostic.
        """
        # Uses the adapter's exception class rather than the test loader's class
        assert safety_cli.LEGACY.SDLCError is not sdlc.SDLCError
        legacy_ctx = safety_cli.LEGACY.Context(repo)
        monkeypatch.setattr(safety_cli.MainRootHelper, "resolve", Mock(return_value=repo))
        monkeypatch.setattr(safety_cli.LEGACY, "Context", Mock(return_value=legacy_ctx))
        callback = Mock(side_effect=safety_cli.LEGACY.SDLCError("adapter boundary"))
        monkeypatch.setattr(safety_cli.LEGACY.SdlcCliHelper, "cmd_models", callback)
        monkeypatch.setattr(sdlc.subprocess, "run", Mock(side_effect=pytest.fail.Exception("unexpected process")))
        assert SafetyCliHelper.main(["models"]) == 1
        callback.assert_called_once()
        assert callback.call_args.args[0] is legacy_ctx
        assert capsys.readouterr().err == "error: adapter boundary\n"

    @staticmethod
    @pytest.mark.parametrize("approved, hardware, output_suffix, expected", [
        (False, True, "ITM-0002/BLK-0002", "package scaffolding requires a running approved item"),
        (True, False, "ITM-0002/BLK-0002", "image item requires ./bin/lets sdlc hardware require ID"),
        (True, True, "other", "--output must identify the assigned item block or integration worktree"),
        (True, True, "ITM-0002", "--output must identify the assigned item block or integration worktree"),
        (True, True, "ITM-0002/BLK-0002", ""),
    ])
    def test_package_adapter_preserves_approval_hardware_and_output_gates(
            repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
            approved: bool, hardware: bool, output_suffix: str, expected: str) -> None:
        """Checks item approval, hardware marking, and assigned output before scaffolding.

        Args:
            repo: Supplies an isolated repository.
            monkeypatch: Replaces ledger access and scaffold generation.
            capsys: Captures refusal diagnostics.
            approved: Selects plan approval state.
            hardware: Selects the required hardware marker.
            output_suffix: Selects the requested output under the worktree directory.
            expected: Supplies the refusal diagnostic, or an empty success marker.
        """
        # Supplies a real item model while isolating ledger and package effects
        item = Item(prefix="ITM", number=2, desc="EXAMPLE", description="Example", kind=ItemKind.TASK,
                    idea="Example", created_at="2024-01-01", updated_at="2024-01-01",
                    status=ItemStatus.IN_PROGRESS,
                    plan=PlanState(revision=1, approved_revision=1 if approved else None),
                    hardware=HardwareAcceptance(required=hardware))
        legacy_ctx = safety_cli.LEGACY.Context(repo)
        wiring = Mock(spec=AppWiring)
        wiring.item_usecases = Mock()
        wiring.settings = Mock()
        wiring.item_usecases.get.return_value = item
        wiring.settings.worktrees_dir = repo / "worktrees"
        output = wiring.settings.worktrees_dir / output_suffix
        scaffold = Mock()
        monkeypatch.setattr(safety_cli.MainRootHelper, "resolve", Mock(return_value=repo))
        monkeypatch.setattr(safety_cli.LEGACY, "Context", Mock(return_value=legacy_ctx))
        monkeypatch.setattr(safety_cli.AppWiring, "from_directory", Mock(return_value=wiring))
        monkeypatch.setattr(safety_cli.LEGACY.SdlcPackageHelper, "cmd_package_init", scaffold)
        monkeypatch.setattr(sdlc.subprocess, "run", Mock(side_effect=pytest.fail.Exception("unexpected process")))

        # Exercises parser-to-adapter dispatch without creating package payloads
        result = SafetyCliHelper.main(["package-init", "ITM-0002", "--output", str(output),
                                       "--operation", "replace:/etc/example"])
        if expected:
            assert result == 1
            scaffold.assert_not_called()
            assert capsys.readouterr().err == f"error: {expected}\n"
        else:
            assert result == 0
            scaffold.assert_called_once()
            assert scaffold.call_args.args[0] is legacy_ctx
            assert scaffold.call_args.args[1].output == str(output.resolve())
            assert scaffold.call_args.args[2] == {"id": "ITM-0002", "state": "implementing", "current_round": 1}

    @staticmethod
    @pytest.mark.parametrize("credentials", [False, True])
    def test_git_preserves_arguments_and_quoted_ssh_options(
            tmp_path: Path, monkeypatch: pytest.MonkeyPatch, credentials: bool) -> None:
        """Checks Git arguments and credential discovery through a path containing spaces.

        Args:
            tmp_path: Supplies isolated credential and worktree paths.
            monkeypatch: Captures Git execution without starting a process.
            credentials: Selects whether complete SSH credentials exist.
        """
        # Locates credentials above a nested worktree with shell-sensitive paths
        root = tmp_path / "project with ' quote"
        worktree = root / ".codex/worktrees/block"
        worktree.mkdir(parents=True)
        admin = root / "admin"
        admin.mkdir()
        if credentials:
            for name in ("ssh_config", "github", "github_known_hosts"):
                (admin / name).write_text("fixture", encoding="utf-8")
        captured = Mock(return_value=subprocess.CompletedProcess([], 7, "output", "error"))
        monkeypatch.setattr(sdlc.SdlcRuntimeHelper, "run", captured)
        monkeypatch.setattr(sdlc.subprocess, "run", Mock(side_effect=pytest.fail.Exception("unexpected process")))
        arguments = ["status", "--porcelain", "--", "two words"]
        result = sdlc.SdlcRuntimeHelper.git(worktree, arguments, check=False)

        # Preserves option boundaries and quoted SSH identity arguments
        captured.assert_called_once()
        command = captured.call_args.args[0]
        assert command[:2] == ["git", "--no-pager"]
        assert command[-4:] == arguments
        assert captured.call_args.kwargs == {"cwd": worktree, "check": False}
        assert result.returncode == 7
        assert result.stdout == "output"
        assert arguments == ["status", "--porcelain", "--", "two words"]
        if credentials:
            assert command[2] == "-c"
            assert command[3].startswith("core.sshCommand=")
            assert shlex.split(command[3].split("=", 1)[1]) == [
                "ssh", "-F", str(admin / "ssh_config"), "-i", str(admin / "github"),
                "-o", "IdentitiesOnly=yes", "-o", f"UserKnownHostsFile={admin / 'github_known_hosts'}",
                "-o", "StrictHostKeyChecking=yes",
            ]
        else:
            assert command == ["git", "--no-pager", *arguments]

    @staticmethod
    def test_package_scaffold_has_deterministic_payload(
            repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Checks every generated file against a fixed reversible package payload.

        Args:
            repo: Supplies an isolated repository.
            monkeypatch: Freezes changelog time without installing a package.
        """
        # Fixes time and exercises all operation kinds including shell-sensitive paths
        ctx = sdlc.Context(repo)
        monkeypatch.setattr(sdlc.dt, "datetime", SdlcTestClock)
        # Controls locale and default permissions for fixed scaffold bytes and modes
        previous_locale: str = locale.setlocale(locale.LC_TIME)
        previous_umask: int = os.umask(0o022)
        try:
            locale.setlocale(locale.LC_TIME, "C")
            sdlc.SdlcPackageHelper.cmd_package_init(ctx, argparse.Namespace(
                id="ITM-0002", package="scr-deterministic", output=str(repo), force=False,
                operation=["add:/etc/new file", "replace:/etc/monit/monitrc",
                           "delete:/etc/retired.conf", "move:/etc/old.conf:/etc/new.conf"]),
                {"id": "ITM-0002", "state": "implementing", "current_round": 1})
            package_root = repo / "packages/ITM-0002-round-1"
            expected = {
                "README.md": "c7af91af8abde03ecd43045010a30cd1f30d471d4ca4dff851c0c83036aef89f",
                "debian/changelog": "0526e0fc7e0b20873458335c8c12092586d1008fe4cdb6260914bdd551e572b6",
                "debian/control": "179f42ac56e320e1e0f09bba4300755c563078fc8e9f6e91c6a460aac5bd50cc",
                "debian/install": "81d9f5b046f4d85e071e5a38c49063f2db6c61ac9139eef47308d94b0529f5b9",
                "debian/postinst": "653c643e07967e5bb41e1481042e63bb5b6863f068b60b4bd13e6b9591c74139",
                "debian/postrm": "a7ea8fcfbada7d185672e289e452c9451065ea27cdf3c69559cc77c6f6a18ef6",
                "debian/preinst": "a0a926bbe51d312a123774ace2241e7d0bf08f2e9f5c5f01fffd926666bb80b4",
                "debian/rules": "4a137aac0bc1ad2e455aa688026a08ac1dcff6b581838abecd75a5c808811016",
                "debian/sdlc-operations": "c5bea211256a61505a8828a484868c31e4f3822b7cc4619da683853c4a61d653",
                "debian/source/format": "e8e18df40bcd69d6aa404282679186d9b8256ac63a5b4e80d7f081e8a0095a2e",
            }

            # Detects byte changes, unexpected payload files, and executable-mode changes
            actual = {str(path.relative_to(package_root)): hashlib.sha256(path.read_bytes()).hexdigest()
                      for path in package_root.rglob("*") if path.is_file()}
            assert actual == expected
            assert sorted(str(path.relative_to(package_root)) for path in package_root.rglob("*") if path.is_dir()) == [
                "debian", "debian/source", "payload",
            ]
            for relative in expected:
                mode = 0o755 if relative in {"debian/preinst", "debian/postinst", "debian/postrm", "debian/rules"} else 0o644
                assert (package_root / relative).stat().st_mode & 0o777 == mode
        finally:
            # Restores both process settings even when generation or assertions fail
            try:
                locale.setlocale(locale.LC_TIME, previous_locale)
            finally:
                os.umask(previous_umask)


    @staticmethod
    @pytest.mark.parametrize("restoration_mismatch", [False, True])
    def test_disposable_package_window_holds_lock_through_restoration_and_cleanup(
            repo: Path, monkeypatch: pytest.MonkeyPatch, restoration_mismatch: bool) -> None:
        """Checks the full disposable test order with real temporary-tree fingerprints.

        Steps:
            1. CREATE isolated source, package, and mounted-tree fixtures.
            2. REPLACE process boundaries with bounded simulations.
            3. RUN the complete locked test and restoration window.
            4. CHECK operation order, cleanup, source hash, and quarantine state.

        Args:
            repo: Supplies isolated source, mounted-root, and package fixtures.
            monkeypatch: Replaces every process and image operation with bounded fakes.
            restoration_mismatch: Selects successful restoration or a changed payload.
        """
        # Creates ordinary temporary files without accessing any source image
        ctx = sdlc.Context(repo)
        source = repo / "source.img"
        source.write_bytes(b"simulated image")
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        deb = repo / "change.deb"
        deb.write_bytes(b"simulated package")
        mounted = repo / "image"
        mounted.mkdir()
        target = mounted / "value"
        target.write_text("original", encoding="utf-8")
        # Prevents relatime reads from changing the fixture's restored access time
        os.utime(target, ns=(2_100_000_000_000_000_000, 1_700_000_000_000_000_000))
        active_state = repo / ".lets/scr/image/mount.state"
        events: List[str] = []
        locked = False
        installed_stat: Optional[os.stat_result] = None
        original_lock = ctx.lock
        original_fingerprint = sdlc.SdlcPackageHelper.fingerprint_tree
        original_hash = sdlc.SdlcRuntimeHelper.file_sha256
        original_remove = sdlc.shutil.rmtree

        @contextlib.contextmanager
        def recording_lock(name: str, timeout: Optional[int] = None) -> Iterator[Path]:
            """Records the real temporary lock around all simulated image effects.

            Args:
                name: Selects the expected shared image lock.
                timeout: Supplies the existing lock timeout.

            Yields:
                The acquired temporary lock path.
            """
            # Holds a real temporary flock while simulated effects record their order
            nonlocal locked
            assert name == "image"
            assert not locked
            with original_lock(name, timeout) as path:
                locked = True
                events.append("lock")
                try:
                    yield path
                finally:
                    events.append("unlock")
                    locked = False

        def fingerprint(root: Path, excludes: List[str]) -> Dict[str, Dict[str, Union[str, int, List[str], Dict[str, str]]]]:
            """Records restoration proofs while retaining actual filesystem comparison.

            Args:
                root: Selects the temporary mounted tree.
                excludes: Supplies the configured fingerprint exclusions.

            Returns:
                The actual temporary-tree fingerprint.
            """
            assert locked and root == mounted
            events.append("fingerprint")
            return original_fingerprint(root, excludes)

        def source_digest(path: Path) -> str:
            """Records source-integrity checks within the image lock.

            Args:
                path: Selects the temporary source file.

            Returns:
                The actual source-file hash.
            """
            assert locked and path == source
            events.append("source-hash")
            return original_hash(path)

        def remove_scratch(path: Path) -> None:
            """Removes only the test's disposable scratch while the lock remains held.

            Args:
                path: Selects the current scratch directory.
            """
            assert locked and path.parent == ctx.runtime / "tests"
            assert not active_state.exists()
            events.append("cleanup")
            original_remove(path)

        def simulated_run(command: List[str], cwd: Optional[Path] = None,
                          check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
            """Simulates only the expected copy, mount, package, test, and unmount commands.

            Args:
                command: Supplies the operation under test.
                cwd: Supplies the working directory.
                check: Selects process error handling.
                capture: Selects output capture.

            Returns:
                A successful simulated process result.
            """
            # Restricts each process shape to its expected temporary paths
            nonlocal installed_stat
            assert locked
            assert capture is False
            if command[0] == "cp":
                assert command[1:-1] == ["--reflink=auto", "--sparse=always", "--", str(source)]
                destination = Path(command[-1])
                assert destination.parent.parent == ctx.runtime / "tests"
                events.append("copy")
                destination.write_bytes(source.read_bytes())
            elif command[:4] == [str(repo / "bin/lets"), "scr", "image", "mount"]:
                assert cwd == repo and command[-1] == "--rw"
                assert Path(command[-2]).parent.parent == ctx.runtime / "tests"
                events.append("mount")
                active_state.parent.mkdir(parents=True, exist_ok=True)
                active_state.write_text("simulated", encoding="utf-8")
            elif command == [str(repo / "bin/lets"), "scr", "image", "umount"]:
                assert cwd == repo and check is False
                events.append("unmount")
                active_state.unlink()
            elif command == ["dpkg", f"--root={mounted}", f"--admindir={mounted / 'var/lib/dpkg'}", "-i", str(deb)]:
                events.append("install")
                installed_stat = target.stat()
                target.write_text("changed", encoding="utf-8")
            elif command == ["chroot", str(mounted), "/bin/sh", "-c", "test temporary behavior"]:
                events.append("test")
                assert target.read_text(encoding="utf-8") == "changed"
            else:
                assert command == ["dpkg", f"--root={mounted}", f"--admindir={mounted / 'var/lib/dpkg'}", "-r", "test-package"]
                assert check is False and installed_stat is not None
                events.append("remove")
                if not restoration_mismatch:
                    target.write_text("original", encoding="utf-8")
                    os.utime(target, ns=(installed_stat.st_atime_ns, installed_stat.st_mtime_ns))
            return subprocess.CompletedProcess(command, 0, "", "")

        def verify_process(command: List[str], cwd: Path, env: Dict[str, str], check: bool) -> subprocess.CompletedProcess[str]:
            """Runs the real verifier in-process with simulated external effects.

            Args:
                command: Supplies the exact child verifier invocation.
                cwd: Supplies the expected repository directory.
                env: Supplies the inherited image-lock marker.
                check: Selects non-raising child status handling.

            Returns:
                The simulated child process status.
            """
            # Carries the parent's lock marker into the actual in-process verifier
            assert locked and cwd == repo and check is False
            assert env["SDLC_IMAGE_LOCK_HELD"] == "1"
            assert command == [str(repo / "bin/lets"), "sdlc", "verify-package", "ITM-0002",
                               "--root", str(mounted), "--deb", str(deb),
                               "--test-command", "test temporary behavior"]
            events.append("verify")
            with monkeypatch.context() as child_environment:
                child_environment.setenv("SDLC_IMAGE_LOCK_HELD", env["SDLC_IMAGE_LOCK_HELD"])
                try:
                    sdlc.SdlcPackageHelper.cmd_verify_package(ctx, argparse.Namespace(
                        root=str(mounted), deb=str(deb), recover=False, test_command="test temporary behavior"))
                except sdlc.SDLCError:
                    return subprocess.CompletedProcess(command, 1, "", "")
            return subprocess.CompletedProcess(command, 0, "", "")

        # Replaces both process boundaries and retains real restoration fingerprints
        monkeypatch.delenv("SDLC_IMAGE_LOCK_HELD", raising=False)
        monkeypatch.setattr(ctx, "lock", recording_lock)
        monkeypatch.setattr(sdlc.SdlcRuntimeHelper, "run", simulated_run)
        monkeypatch.setattr(sdlc.SdlcRuntimeHelper, "file_sha256", source_digest)
        monkeypatch.setattr(sdlc.SdlcPackageHelper, "package_name", Mock(return_value="test-package"))
        monkeypatch.setattr(sdlc.SdlcPackageHelper, "package_architecture", Mock(return_value="all"))
        monkeypatch.setattr(sdlc.SdlcPackageHelper, "fingerprint_tree", fingerprint)
        monkeypatch.setattr(sdlc.subprocess, "run", verify_process)
        monkeypatch.setattr(sdlc.shutil, "rmtree", remove_scratch)
        args = argparse.Namespace(id="ITM-0002", image=str(source), deb=str(deb), test_command="test temporary behavior")
        if restoration_mismatch:
            with pytest.raises(sdlc.SDLCError, match="package test failed; disposable image was cleaned"):
                sdlc.SdlcPackageHelper.cmd_test_package(ctx, args)
        else:
            sdlc.SdlcPackageHelper.cmd_test_package(ctx, args)

        # Proves cleanup precedes unlock and mismatch retains logical quarantine
        assert events == ["lock", "source-hash", "copy", "mount", "verify", "fingerprint",
                          "install", "test", "remove", "fingerprint", "unmount", "source-hash", "cleanup", "unlock"]
        assert locked is False
        assert hashlib.sha256(source.read_bytes()).hexdigest() == source_hash
        assert not active_state.exists()
        assert not list((ctx.runtime / "tests").iterdir())
        dirty = ctx.lock_root / "quarantine/image-dirty.json"
        if restoration_mismatch:
            assert dirty.is_file()
            journal = json.loads(dirty.read_text(encoding="utf-8"))
            assert journal["phase"] == "quarantined"
            assert journal["changed_paths"] == ["/value"]
            with pytest.raises(sdlc.SDLCError, match="logically locked by quarantine"):
                ctx.assert_image_available()
        else:
            assert not dirty.exists()
            assert target.read_text(encoding="utf-8") == "original"
