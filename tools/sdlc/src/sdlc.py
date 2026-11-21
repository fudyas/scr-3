from __future__ import annotations

import argparse
import base64
import contextlib
import datetime as dt
import errno
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from abc import ABC
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple


# Recognizes retired commands only to refuse them before repository access
RETIRED_COMMANDS = frozenset({
    "init", "new", "list", "show", "path", "status", "stage", "checkpoint",
    "section", "approve", "follow-up", "abandon", "resume", "trivial-policy",
    "continuation-policy", "implement", "task-plan", "task-next", "brief",
    "task-result", "task-validate", "acceptance", "validate", "worktree",
    "implementation-commit", "validation-result", "merge",
})


class SDLCError(RuntimeError):
    """A refused retained workflow or image-safety operation."""


class Context:
    """Repository configuration and shared host locks."""

    def __init__(self, root: Path, command_root: Optional[Path] = None) -> None:
        """Initializes repository configuration and shared lock and runtime paths.

        Args:
            root: Identifies the repository or filesystem root.
            command_root: Selects the checkout providing package verification commands.
        """
        # Loads host configuration before deriving any shared paths
        self.root = root.resolve()
        self.command_root = (command_root or root).resolve()
        self.conf = SdlcRuntimeHelper.parse_conf(self.root / "etc/sdlc.conf")

        # Resolves shared host paths through the configuration contract
        self.runtime = self._configured_path("SDLC_RUNTIME_ROOT", ".codex/sdlc")
        self.lock_root = self._configured_path("SDLC_SHARED_LOCK_ROOT", ".codex/sdlc")
        common_dir = SdlcRuntimeHelper.git(self.root, ["rev-parse", "--git-common-dir"]).stdout.strip()
        common_path = Path(common_dir)
        self.main_tree_lock_root = ((self.root / common_path).resolve()
                                   if not common_path.is_absolute() else common_path.resolve()) / "sdlc-locks"
        # Creates runtime and lock directories without altering quarantine records
        self.runtime.mkdir(parents=True, exist_ok=True)
        (self.runtime / "locks").mkdir(parents=True, exist_ok=True)
        (self.runtime / "quarantine").mkdir(parents=True, exist_ok=True)
        (self.lock_root / "locks").mkdir(parents=True, exist_ok=True)
        (self.lock_root / "quarantine").mkdir(parents=True, exist_ok=True)
        self.main_tree_lock_root.mkdir(parents=True, exist_ok=True)

    def _configured_path(self, key: str, fallback: str) -> Path:
        """Resolves a configured host path relative to this checkout.

        Args:
            key: Selects the configuration assignment.
            fallback: Supplies the path used when the assignment is absent.

        Returns:
            Expanded absolute configuration path.
        """
        # Expands configured values without changing relative-path semantics
        raw = self.conf.get(key, fallback).replace("${LETS_PROJ_DIR}", str(self.root))
        expanded = Path(os.path.expandvars(raw)).expanduser()
        return (self.root / expanded).resolve() if not expanded.is_absolute() else expanded.resolve()


    def assert_image_available(self, identity: Optional[str] = None, recover: bool = False) -> None:
        """Rejects image work while global or image-specific quarantine is active.

        Args:
            identity: Selects image-specific quarantine state when supplied.
            recover: Permits approved recovery of image-specific quarantine state.

        Raises:
            SDLCError: global quarantine exists or image-specific quarantine blocks work.
        """
        # Refuses global quarantine before considering image-specific recovery
        dirty = self.lock_root / "quarantine" / "image-dirty.json"
        if dirty.exists() and os.environ.get("SDLC_RECOVERY") != "1":
            raise SDLCError(f"image operations are logically locked by quarantine: {dirty}")
        if identity is not None:
            quarantine = self.lock_root / "quarantine" / f"image-{identity}.json"
            if quarantine.exists() and not recover:
                raise SDLCError(f"image is quarantined: {quarantine}")

    @contextlib.contextmanager
    def lock(self, name: str, timeout: Optional[int] = None) -> Iterator[Path]:
        """Holds an advisory lock and repeats image quarantine checks after acquisition.

        Args:
            name: Selects the lock namespace.
            timeout: Overrides the configured lock wait limit when supplied.

        Yields:
            Lock file path while the advisory lock remains held.

        Raises:
            SDLCError: Required state, evidence, or safety preconditions are absent.
        """
        # Checks global image quarantine before entering the advisory-lock wait
        if name == "image":
            self.assert_image_available()
        lock_dir = self.main_tree_lock_root if name == "main-tree" else self.lock_root / "locks"
        path = lock_dir / f"{name}.lock"
        path.parent.mkdir(parents=True, exist_ok=True)
        limit = timeout if timeout is not None else int(self.conf.get("SDLC_LOCK_TIMEOUT", "3600"))
        with path.open("a+", encoding="utf-8") as handle:
            deadline = time.monotonic() + limit
            while True:
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise SDLCError(f"timed out waiting for lock: {path}")
                    time.sleep(0.2)
            # Records lock ownership only after advisory acquisition succeeds
            handle.seek(0)
            handle.truncate()
            json.dump({"pid": os.getpid(), "host": socket.gethostname(), "time": SdlcRuntimeHelper.now()}, handle)
            handle.flush()
            os.fsync(handle.fileno())
            try:
                # Closes quarantine race between preflight and flock acquisition
                if name == "image":
                    self.assert_image_available()
                yield path
            # Releases only this process advisory lock on every exit
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class SdlcRuntimeHelper(ABC):
    """Runs local commands and owns configuration, time, JSON, and hash utilities."""

    @staticmethod
    def run(args: List[str], cwd: Optional[Path] = None, check: bool = True,
            capture: bool = True) -> subprocess.CompletedProcess[str]:
        """Runs a command with optional output capture and exit-status enforcement.

        Args:
            args: Supplies the executable and its arguments.
            cwd: Selects the working directory, or inherits the current directory.
            check: Enforces successful exit status when enabled.
            capture: Captures stdout and stderr instead of inheriting parent streams.

        Returns:
            Completed command with its exit status and captured streams.

        Raises:
            subprocess.CalledProcessError: The command fails with exit enforcement enabled.
            OSError: The command cannot start.
        """
        # Preserves caller control of exit enforcement and inherited streams
        return subprocess.run(
            args, cwd=cwd, check=check, text=True,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
        )

    @staticmethod
    def git(root: Path, arguments: List[str], check: bool = True) -> subprocess.CompletedProcess[str]:
        """Runs Git with repository-managed SSH credentials when available.

        Args:
            root: Identifies the repository or filesystem root.
            arguments: Supplies Git arguments without the executable name.
            check: Enforces successful exit status when enabled.

        Returns:
            Completed Git command with its exit status and captured streams.

        Raises:
            subprocess.CalledProcessError: Git fails with exit enforcement enabled.
            OSError: Git cannot start.
        """
        command = ["git", "--no-pager"]

        # Finds credentials from both main and linked pipeline worktrees
        for parent in (root.resolve(), *root.resolve().parents):
            ssh_config = parent / "admin/ssh_config"
            identity = parent / "admin/github"
            known_hosts = parent / "admin/github_known_hosts"
            if ssh_config.is_file() and identity.is_file() and known_hosts.is_file():
                ssh_command = " ".join([
                    "ssh",
                    "-F", shlex.quote(str(ssh_config)),
                    "-i", shlex.quote(str(identity)),
                    "-o", "IdentitiesOnly=yes",
                    "-o", f"UserKnownHostsFile={shlex.quote(str(known_hosts))}",
                    "-o", "StrictHostKeyChecking=yes",
                ])
                command.extend(["-c", f"core.sshCommand={ssh_command}"])
                break

        return SdlcRuntimeHelper.run([*command, *arguments], cwd=root, check=check)

    @staticmethod
    def now() -> str:
        """Returns the current UTC timestamp at second precision."""
        return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


    @staticmethod
    def parse_conf(path: Path) -> Dict[str, str]:
        """Reads shell-style configuration assignments without evaluating their contents.

        Args:
            path: Identifies the file or filesystem entry.

        Returns:
            Configuration names and their unevaluated values.

        Raises:
            OSError: The configuration file cannot be read.
        """
        # Reads assignments literally so configuration never executes shell code
        values: Dict[str, str] = {}
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if value and value[0] in "\"'" and value[-1] == value[0]:
                value = value[1:-1]
            values[key] = value
        return values

    @staticmethod
    def repo_root() -> Path:
        """Returns the configured project root or the current Git checkout root.

        Returns:
            Project checkout path.
        """
        # Prefers the managed project root before inspecting the current checkout
        env = os.environ.get("LETS_PROJ_DIR")
        if env:
            return Path(env)
        result = SdlcRuntimeHelper.run(["git", "--no-pager", "rev-parse", "--show-toplevel"])
        return Path(result.stdout.strip())

    @staticmethod
    def atomic_json(path: Path, value: object) -> None:
        """Writes a JSON document through an atomic, synchronized replacement.

        Args:
            path: Identifies the file or filesystem entry.
            value: Supplies the value to normalize or serialize.

        Raises:
            OSError: The document cannot be synchronized or replaced.
        """
        # Synchronizes replacement content before exposing its final path
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)


    @staticmethod
    def file_sha256(path: Path) -> str:
        """Returns the SHA-256 digest of a file without loading it into memory.

        Args:
            path: Identifies the file or filesystem entry.

        Returns:
            Lowercase hexadecimal SHA-256 digest.

        Raises:
            OSError: The file cannot be read.
        """
        # Streams file blocks so large package and image hashes stay bounded
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()


class SdlcPackageHelper(ABC):
    """Owns reversible package scaffolds, restoration proof, and image quarantine."""

    @staticmethod
    def fingerprint_xattrs(path: Path) -> Dict[str, Any]:
        """Returns deterministic extended attributes without following symbolic links.

        Args:
            path: Identifies the file or filesystem entry.

        Returns:
            Attribute names mapped to base64 values, or explicit unsupported status.

        Raises:
            OSError: metadata inspection fails for a reason other than unsupported access.
        """
        try:
            names = sorted(os.listxattr(path, follow_symlinks=False))
            return {name: base64.b64encode(os.getxattr(
                path, name, follow_symlinks=False)).decode("ascii") for name in names}
        except OSError as exc:
            # Records platform/filesystem limits instead of weakening restoration proof silently
            unsupported = {errno.ENOTSUP, errno.EOPNOTSUPP}
            if exc.errno in unsupported:
                return {"status": "unsupported", "errno": exc.errno}
            raise

    @staticmethod
    def fingerprint_tree(root: Path, excludes: List[str]) -> Dict[str, Dict[str, Any]]:
        """Returns content and restoration metadata for a filesystem tree.

        Steps:
            1. READ metadata for every included path.
            2. HASH files and record symlinks and extended attributes.
            3. ENCODE hard-link groups with stable path names.

        Args:
            root: Identifies the repository or filesystem root.
            excludes: Lists absolute paths excluded by the restoration contract.

        Returns:
            Path-keyed fingerprints with timestamps, xattrs, and hard-link groups.
        """
        result: Dict[str, Dict[str, Any]] = {}
        inode_paths: Dict[Tuple[int, int], List[str]] = {}
        normalized = [x.rstrip("/") for x in excludes if x]
        # Includes mount-root metadata in restoration proof
        root_stat = root.lstat()
        result["/"] = {"type": "directory", "mode": root_stat.st_mode,
                       "uid": root_stat.st_uid, "gid": root_stat.st_gid,
                       "atime_ns": root_stat.st_atime_ns, "mtime_ns": root_stat.st_mtime_ns,
                       "xattrs": SdlcPackageHelper.fingerprint_xattrs(root)}
        # Traverses included paths without following directory symlinks
        for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
            base_path = Path(base)
            rel_base = "/" + str(base_path.relative_to(root)) if base_path != root else ""
            included_dirs = [d for d in dirs if not any((rel_base + "/" + d == x or
                                                           (rel_base + "/" + d).startswith(x + "/"))
                                                          for x in normalized)]
            # Records directory symlinks as links instead of silently dropping them
            symlink_dirs = [d for d in included_dirs if (base_path / d).is_symlink()]
            dirs[:] = [d for d in included_dirs if d not in symlink_dirs]
            for name in sorted(symlink_dirs):
                path = base_path / name
                rel = "/" + str(path.relative_to(root))
                st = path.lstat()
                result[rel] = {"type": "symlink", "link": os.readlink(path),
                               "mode": st.st_mode, "uid": st.st_uid, "gid": st.st_gid,
                               "size": st.st_size, "atime_ns": st.st_atime_ns,
                               "mtime_ns": st.st_mtime_ns, "xattrs": SdlcPackageHelper.fingerprint_xattrs(path)}
            if base_path != root:
                st = base_path.lstat()
                result[rel_base] = {"type": "directory", "mode": st.st_mode,
                                    "uid": st.st_uid, "gid": st.st_gid,
                                    "atime_ns": st.st_atime_ns, "mtime_ns": st.st_mtime_ns,
                                    "xattrs": SdlcPackageHelper.fingerprint_xattrs(base_path)}
            for name in sorted(files):
                path = base_path / name
                rel = "/" + str(path.relative_to(root))
                if any(rel == x or rel.startswith(x + "/") for x in normalized):
                    continue
                initial_stat = path.lstat()
                entry = {"type": "symlink" if path.is_symlink() else "file"}
                if path.is_symlink():
                    entry["link"] = os.readlink(path)
                elif path.is_file():
                    digest = hashlib.sha256()
                    with path.open("rb") as handle:
                        for block in iter(lambda: handle.read(1024 * 1024), b""):
                            digest.update(block)
                    entry["sha256"] = digest.hexdigest()
                    inode_paths.setdefault((initial_stat.st_dev, initial_stat.st_ino), []).append(rel)
                # Captures timestamps after reads so fingerprinting does not report its own atime update
                st = path.lstat()
                entry.update({"mode": st.st_mode, "uid": st.st_uid, "gid": st.st_gid,
                              "size": st.st_size, "atime_ns": st.st_atime_ns,
                              "mtime_ns": st.st_mtime_ns, "xattrs": SdlcPackageHelper.fingerprint_xattrs(path)})
                result[rel] = entry
        # Captures root timestamps after traversal so scanning does not create false drift
        root_stat = root.lstat()
        result["/"].update({"mode": root_stat.st_mode, "uid": root_stat.st_uid,
                            "gid": root_stat.st_gid, "atime_ns": root_stat.st_atime_ns,
                            "mtime_ns": root_stat.st_mtime_ns, "xattrs": SdlcPackageHelper.fingerprint_xattrs(root)})
        # Encodes stable path groups instead of unstable device/inode numbers
        for paths in inode_paths.values():
            if len(paths) > 1:
                group = sorted(paths)
                for rel in group:
                    result[rel]["hardlink_group"] = group
        return result

    @staticmethod
    def package_name(deb: Path) -> str:
        """Returns the Debian package name declared by an artifact.

        Args:
            deb: Identifies the Debian package artifact.

        Returns:
            Declared package name.

        Raises:
            SDLCError: Required state, evidence, or safety preconditions are absent.
        """
        # Reads package metadata without installing the artifact
        result = SdlcRuntimeHelper.run(["dpkg-deb", "-f", str(deb), "Package"])
        value = result.stdout.strip()
        if not value:
            raise SDLCError(f"cannot determine package name: {deb}")
        return value

    @staticmethod
    def package_architecture(deb: Path) -> str:
        """Returns the Debian package architecture declared by an artifact.

        Args:
            deb: Identifies the Debian package artifact.

        Returns:
            Declared package architecture.

        Raises:
            SDLCError: Required state, evidence, or safety preconditions are absent.
        """
        # Reads architecture metadata before any installation decision
        result = SdlcRuntimeHelper.run(["dpkg-deb", "-f", str(deb), "Architecture"])
        value = result.stdout.strip()
        if not value:
            raise SDLCError(f"cannot determine package architecture: {deb}")
        return value

    @staticmethod
    def root_dpkg_architecture(root: Path) -> str:
        """Returns the single machine architecture proven by an image package database.

        Args:
            root: Identifies the repository or filesystem root.

        Returns:
            Single installed machine architecture from the root package database.

        Raises:
            SDLCError: Required state, evidence, or safety preconditions are absent.
        """
        # Derives target architecture only from its installed package database
        status = root / "var/lib/dpkg/status"
        if not status.is_file():
            raise SDLCError(f"target root has no dpkg status database: {status}")
        architectures: Set[str] = set()
        # Ignores architecture-neutral packages while collecting installed machine architectures
        for paragraph in re.split(r"\n\s*\n", status.read_text(encoding="utf-8")):
            fields = {}
            for line in paragraph.splitlines():
                if ": " in line:
                    key, value = line.split(": ", 1)
                    fields[key] = value
            architecture = fields.get("Architecture")
            if (fields.get("Status") == "install ok installed" and architecture and
                    architecture != "all"):
                architectures.add(architecture)
        if len(architectures) != 1:
            values = ", ".join(sorted(architectures)) or "none"
            raise SDLCError(f"target root machine architecture is ambiguous: {values}")
        return architectures.pop()

    @staticmethod
    def package_install_command(root: Path, deb: Path) -> List[str]:
        """Builds a root-scoped dpkg command after proving cross-architecture intent.

        Args:
            root: Identifies the repository or filesystem root.
            deb: Identifies the Debian package artifact.

        Returns:
            Root-scoped dpkg arguments with architecture intent enforced.

        Raises:
            SDLCError: Required state, evidence, or safety preconditions are absent.
        """
        # Scopes dpkg to the supplied root before proving architecture compatibility
        command = ["dpkg", f"--root={root}", f"--admindir={root / 'var/lib/dpkg'}"]
        architecture = SdlcPackageHelper.package_architecture(deb)
        if architecture != "all":
            target_architecture = SdlcPackageHelper.root_dpkg_architecture(root)
            if architecture != target_architecture:
                raise SDLCError(
                    f"package architecture {architecture} does not match target root "
                f"architecture {target_architecture}")
            host_architecture = SdlcRuntimeHelper.run(["dpkg", "--print-architecture"]).stdout.strip()
            if not host_architecture:
                raise SDLCError("cannot determine host dpkg architecture")
            if architecture != host_architecture:
                command.append("--force-architecture")
        return [*command, "-i", str(deb)]

    @staticmethod
    def cmd_verify_package(ctx: Context, args: argparse.Namespace) -> None:
        """Verifies package installation and rollback under the image lock.

        Steps:
            1. HOLD the image lock and check quarantine.
            2. INSTALL the package and run its test command.
            3. REMOVE the package and verify the selected rollback contract.
            4. QUARANTINE failed restoration before reporting test errors.

        Args:
            ctx: Supplies repository configuration, ledger paths, and shared locks.
            args: Supplies parsed command arguments.

        Raises:
            SDLCError: Required state, evidence, or safety preconditions are absent.
        """
        # Validates disposable paths before creating restoration evidence
        root = Path(args.root).resolve()
        deb = Path(args.deb).resolve()
        if not root.is_dir() or not deb.is_file():
            raise SDLCError("--root must be a mounted directory and --deb must be a file")
        # Selects project rollback assertions when metadata verification belongs to dpkg
        rollback_command = getattr(args, "rollback_command", None)
        if rollback_command and args.recover:
            raise SDLCError("--rollback-command cannot release a quarantined image")
        identity = hashlib.sha256(str(root).encode()).hexdigest()[:20]
        quarantine = ctx.lock_root / "quarantine" / f"image-{identity}.json"
        dirty = ctx.lock_root / "quarantine" / "image-dirty.json"
        if quarantine.exists() and not args.recover:
            raise SDLCError(f"image is quarantined after a failed cleanup: {quarantine}")
        excludes = [x for x in ctx.conf.get("SDLC_VERIFY_EXCLUDES", "").split(",") if x]
        name = SdlcPackageHelper.package_name(deb)
        journal = {"run": str(uuid.uuid4()), "host": socket.gethostname(), "root": str(root),
                   "deb": str(deb), "package": name, "started": SdlcRuntimeHelper.now(), "phase": "waiting-lock",
                   "rollback_command": rollback_command}
        journal_path = ctx.runtime / f"verify-{journal['run']}.json"
        SdlcRuntimeHelper.atomic_json(journal_path, journal)
        lock_context = contextlib.nullcontext() if os.environ.get("SDLC_IMAGE_LOCK_HELD") == "1" else ctx.lock("image")
        with lock_context:
            # Rechecks both quarantine scopes after caller or local flock acquisition
            ctx.assert_image_available(identity, args.recover)
            # Captures the original tree before any package operation
            try:
                before = {} if rollback_command else SdlcPackageHelper.fingerprint_tree(root, excludes)
            # Quarantines any fingerprint failure before reporting its cause
            except Exception as exc:
                journal.update({"phase": "quarantined", "finished": SdlcRuntimeHelper.now(), "error": str(exc)})
                SdlcRuntimeHelper.atomic_json(journal_path, journal)
                SdlcRuntimeHelper.atomic_json(quarantine, journal)
                SdlcRuntimeHelper.atomic_json(dirty, journal)
                raise SDLCError(f"initial image fingerprint failed and was quarantined: {exc}") from exc
            install_attempted = False
            primary_error: Optional[Exception] = None
            cleanup_error: Optional[Exception] = None
            try:
                journal["phase"] = "installing"
                SdlcRuntimeHelper.atomic_json(journal_path, journal)
                install_attempted = True
                SdlcRuntimeHelper.run(SdlcPackageHelper.package_install_command(root, deb), capture=False)
                journal["phase"] = "testing"
                SdlcRuntimeHelper.atomic_json(journal_path, journal)
                if args.test_command:
                    SdlcRuntimeHelper.run(["chroot", str(root), "/bin/sh", "-c", args.test_command], capture=False)
            # Preserves cleanup and restoration after any command failure
            except Exception as exc:
                primary_error = exc
            finally:
                journal["phase"] = "uninstalling"
                SdlcRuntimeHelper.atomic_json(journal_path, journal)
                if install_attempted:
                    removed = SdlcRuntimeHelper.run(["dpkg", f"--root={root}", f"--admindir={root / 'var/lib/dpkg'}", "-r", name],
                                  check=False, capture=False)
                    if removed.returncode:
                        cleanup_error = SDLCError(f"dpkg removal failed with exit code {removed.returncode}")
            journal["phase"] = "verifying-clean"
            SdlcRuntimeHelper.atomic_json(journal_path, journal)
            # Requires restoration proof even after functional installation or test failure
            try:
                after = {} if rollback_command else SdlcPackageHelper.fingerprint_tree(root, excludes)
            # Quarantines any fingerprint failure before reporting its cause
            except Exception as exc:
                journal.update({"phase": "quarantined", "finished": SdlcRuntimeHelper.now(), "error": str(exc)})
                SdlcRuntimeHelper.atomic_json(journal_path, journal)
                SdlcRuntimeHelper.atomic_json(quarantine, journal)
                SdlcRuntimeHelper.atomic_json(dirty, journal)
                raise SDLCError(f"restoration fingerprint failed and was quarantined: {exc}") from exc
            # Verifies package-specific rollback without duplicating dpkg metadata behavior
            if rollback_command:
                try:
                    SdlcRuntimeHelper.run(["chroot", str(root), "/bin/sh", "-c", rollback_command], capture=False)
                except Exception as exc:
                    cleanup_error = exc
            # Retains both quarantine scopes when restoration or package removal fails
            if before != after or cleanup_error is not None:
                changed = sorted(set(before) ^ set(after) |
                                 {p for p in set(before) & set(after) if before[p] != after[p]})
                journal.update({"phase": "quarantined", "finished": SdlcRuntimeHelper.now(), "changed_paths": changed[:500],
                                "cleanup_error": str(cleanup_error) if cleanup_error else None})
                SdlcRuntimeHelper.atomic_json(journal_path, journal)
                SdlcRuntimeHelper.atomic_json(quarantine, journal)
                SdlcRuntimeHelper.atomic_json(dirty, journal)
                raise SDLCError(f"package removal did not restore the image; quarantined ({len(changed)} paths differ)")
            # Clears image-specific quarantine only after complete restoration proof
            quarantine.unlink(missing_ok=True)
            if args.recover:
                dirty.unlink(missing_ok=True)
            journal.update({"phase": "clean", "finished": SdlcRuntimeHelper.now()})
            SdlcRuntimeHelper.atomic_json(journal_path, journal)
            if primary_error is not None:
                raise SDLCError(f"package test failed after clean restoration: {primary_error}")
        print(f"verified reversible: {name}")

    @staticmethod
    def cmd_test_package(ctx: Context, args: argparse.Namespace) -> None:
        """Verifies a disposable image copy and quarantines any source-restoration or cleanup failure.

        Steps:
            1. LOCK the source image and hash its bytes.
            2. COPY and mount a disposable image for verification.
            3. UNMOUNT the copy and verify the source hash.
            4. REMOVE scratch data or quarantine cleanup failure.

        Args:
            ctx: Supplies repository configuration, ledger paths, and shared locks.
            args: Supplies parsed command arguments.

        Raises:
            SDLCError: Required state, evidence, or safety preconditions are absent.
        """
        # Validates artifacts before acquiring the full disposable-test lock window
        image = Path(args.image).resolve()
        deb = Path(args.deb).resolve()
        if not image.is_file() or not deb.is_file():
            raise SDLCError("--image and --deb must name existing files")
        identity = hashlib.sha256(str(image).encode()).hexdigest()[:20]
        quarantine = ctx.lock_root / "quarantine" / f"image-{identity}.json"
        dirty = ctx.lock_root / "quarantine" / "image-dirty.json"
        ctx.assert_image_available(identity)
        active_state = ctx.root / ".lets/scr/image/mount.state"
        with ctx.lock("image"):
            # Closes image-specific quarantine race after global image flock acquisition
            ctx.assert_image_available(identity)
            if active_state.exists():
                raise SDLCError("an image is already mounted; unmount it before SDLC package testing")
            # Holds the shared lock from source hashing through disposable cleanup
            original_hash = SdlcRuntimeHelper.file_sha256(image)
            run_id = str(uuid.uuid4())
            scratch = ctx.runtime / "tests" / run_id
            scratch.mkdir(parents=True, exist_ok=False)
            image_copy = scratch / image.name
            journal = {"run": run_id, "image": str(image), "source_sha256": original_hash,
                       "deb": str(deb), "phase": "copying", "started": SdlcRuntimeHelper.now()}
            SdlcRuntimeHelper.atomic_json(scratch / "journal.json", journal)
            mount_attempted = False
            functional_error: Optional[Exception] = None
            cleanup_error: Optional[Exception] = None
            try:
                SdlcRuntimeHelper.run(["cp", "--reflink=auto", "--sparse=always", "--", str(image), str(image_copy)], capture=False)
                journal["phase"] = "mounting-copy"
                SdlcRuntimeHelper.atomic_json(scratch / "journal.json", journal)
                mount_attempted = True
                SdlcRuntimeHelper.run([str(ctx.root / "bin/lets"), "scr", "image", "mount", "--image", str(image_copy), "--rw"],
                    cwd=ctx.root, capture=False)
                env = os.environ.copy()
                env["SDLC_IMAGE_LOCK_HELD"] = "1"
                command = [str(ctx.command_root / "bin/lets"), "sdlc", "verify-package", args.id,
                           "--root", str(ctx.root / "image"), "--deb", str(deb)]
                if args.test_command:
                    command.extend(["--test-command", args.test_command])
                if getattr(args, "rollback_command", None):
                    command.extend(["--rollback-command", args.rollback_command])
                journal["phase"] = "install-test-remove"
                SdlcRuntimeHelper.atomic_json(scratch / "journal.json", journal)
                completed = subprocess.run(command, cwd=ctx.command_root, env=env, check=False)
                if completed.returncode:
                    raise SDLCError(f"package verification failed with exit code {completed.returncode}")
            # Preserves cleanup and quarantine after any command failure
            except Exception as exc:
                functional_error = exc
            finally:
                if mount_attempted:
                    result = SdlcRuntimeHelper.run([str(ctx.root / "bin/lets"), "scr", "image", "umount"], cwd=ctx.root,
                                 check=False, capture=False)
                    if result.returncode or active_state.exists():
                        cleanup_error = SDLCError("failed to unmount disposable test image")
            # Verifies source bytes only after the disposable mount cleanup attempt
            try:
                if SdlcRuntimeHelper.file_sha256(image) != original_hash:
                    cleanup_error = SDLCError("source image changed during disposable package test")
            # Quarantines unreadable source-restoration proof
            except Exception as exc:
                cleanup_error = SDLCError(f"failed to verify source image restoration: {exc}")
            # Quarantines any unmount or source-restoration failure before scratch removal
            if cleanup_error is not None:
                journal.update({"phase": "quarantined", "finished": SdlcRuntimeHelper.now(), "error": str(cleanup_error)})
                SdlcRuntimeHelper.atomic_json(scratch / "journal.json", journal)
                SdlcRuntimeHelper.atomic_json(quarantine, journal)
                SdlcRuntimeHelper.atomic_json(dirty, journal)
                raise SDLCError(f"image package test cleanup failed and was quarantined: {cleanup_error}")
            if functional_error is not None:
                journal.update({"phase": "clean-after-test-failure", "finished": SdlcRuntimeHelper.now(),
                                "error": str(functional_error)})
                SdlcRuntimeHelper.atomic_json(scratch / "journal.json", journal)
            else:
                journal.update({"phase": "clean", "finished": SdlcRuntimeHelper.now()})
                SdlcRuntimeHelper.atomic_json(scratch / "journal.json", journal)
            # Requires scratch cleanup before reporting successful disposable verification
            try:
                shutil.rmtree(scratch)
            # Quarantines scratch-cleanup failure instead of reporting success
            except Exception as exc:
                journal.update({"phase": "quarantined", "finished": SdlcRuntimeHelper.now(),
                                "error": f"failed to remove test scratch: {exc}"})
                SdlcRuntimeHelper.atomic_json(quarantine, journal)
                SdlcRuntimeHelper.atomic_json(dirty, journal)
                raise SDLCError(f"image package test scratch cleanup failed and was quarantined: {exc}") from exc
            if functional_error is not None:
                raise SDLCError(f"package test failed; disposable image was cleaned: {functional_error}")
        print("package passed disposable-image restoration test; source image unchanged")
        print(f"source image SHA-256: {original_hash}")

    @staticmethod
    def cmd_lock_run(ctx: Context, args: argparse.Namespace) -> None:
        """Runs a command under the image lock after both quarantine checks.

        Args:
            ctx: Supplies repository configuration, ledger paths, and shared locks.
            args: Supplies parsed command arguments.

        Raises:
            SDLCError: Required state, evidence, or safety preconditions are absent.
        """
        # Checks image-specific quarantine before waiting for the shared image lock
        identity = hashlib.sha256(str(Path(args.image).resolve()).encode()).hexdigest()[:20]
        ctx.assert_image_available(identity)
        if not args.command:
            raise SDLCError("missing command after --")
        with ctx.lock("image"):
            # Closes image-specific quarantine race after global image flock acquisition
            ctx.assert_image_available(identity)
            result = subprocess.run(args.command, check=False)
            if result.returncode:
                raise SDLCError(f"locked command failed with exit code {result.returncode}")

    @staticmethod
    def validate_managed_path(value: str) -> str:
        """Returns a normalized absolute image path without root or parent traversal.

        Args:
            value: Supplies the value to normalize or serialize.

        Returns:
            Absolute managed path without a trailing slash.

        Raises:
            SDLCError: The path is relative, names root, or contains parent traversal.
        """
        if not value.startswith("/") or value == "/" or ".." in Path(value).parts:
            raise SDLCError(f"unsafe managed image path: {value}")
        return value.rstrip("/")

    @staticmethod
    def cmd_package_init(ctx: Context, args: argparse.Namespace, approved_state: Optional[Dict[str, Any]] = None) -> None:
        """Writes a reversible Debian scaffold for approved image operations.

        Steps:
            1. VALIDATE approved state and managed paths.
            2. WRITE Debian metadata and private payload installation rules.
            3. WRITE backup, overlap, installation, and restoration scripts.

        Args:
            ctx: Supplies repository configuration, ledger paths, and shared locks.
            args: Supplies parsed command arguments.
            approved_state: Supplies item state from the approved public adapter.

        Raises:
            SDLCError: Required state, evidence, or safety preconditions are absent.
        """
        # Requires caller-supplied item approval before reading context or writing output
        if approved_state is None:
            raise SDLCError("package scaffolding requires approved item state")
        state = approved_state
        if state["state"] not in {"approved", "auto-approved", "implementing"}:
            raise SDLCError(f"package scaffolding requires an approved plan, got {state['state']}")
        # Tracks exact operations and every path subject to overlap and backup protection
        operations: List[Tuple[str, str, str]] = []
        affected: Set[str] = set()
        for raw in args.operation:
            fields = raw.split(":", 2)
            kind = fields[0]
            if kind not in {"add", "replace", "delete", "move"}:
                raise SDLCError(f"unsupported package operation: {kind}")
            if (kind == "move" and len(fields) != 3) or (kind != "move" and len(fields) != 2):
                raise SDLCError(f"operation must be KIND:/path or move:/source:/dest: {raw}")
            source = SdlcPackageHelper.validate_managed_path(fields[1])
            dest = SdlcPackageHelper.validate_managed_path(fields[2]) if kind == "move" else ""
            affected.add(source)
            if dest:
                affected.add(dest)
            operations.append((kind, source, dest))
        if not operations:
            raise SDLCError("at least one --operation is required")
        # Validates package identity before writing Debian metadata
        package = args.package or f"scr-{state['id'].lower()}"
        if not re.fullmatch(r"[a-z0-9][a-z0-9+.-]+", package):
            raise SDLCError(f"invalid Debian package name: {package}")
        implementation = state.get("implementation", {})
        base = Path(args.output or implementation.get("worktree", ctx.root))
        out = base / "packages" / f"{state['id']}-round-{state['current_round']}"
        debian = out / "debian"
        if out.exists() and any(out.iterdir()) and not args.force:
            raise SDLCError(f"package directory already exists: {out}")
        debian.mkdir(parents=True, exist_ok=True)
        (debian / "source").mkdir(exist_ok=True)
        # Retains the original Debian control, changelog, and build metadata
        (debian / "control").write_text(
            f"Source: {package}\nSection: admin\nPriority: optional\nMaintainer: SCR SDLC Pipeline <noreply@localhost>\n"
        "Standards-Version: 4.6.2\nBuild-Depends: debhelper-compat (= 13)\nRules-Requires-Root: no\n\n"
        f"Package: {package}\nArchitecture: all\nDescription: Reversible SCR change for {state['id']} round {state['current_round']}\n",
            encoding="utf-8")
        (debian / "changelog").write_text(
            f"{package} (1.0.{state['current_round']}) unstable; urgency=medium\n\n"
        f"  * Implement {state['id']} round {state['current_round']}.\n\n"
        f" -- SCR SDLC Pipeline <noreply@localhost>  {dt.datetime.now(dt.timezone.utc).strftime('%a, %d %b %Y %H:%M:%S +0000')}\n",
            encoding="utf-8")
        (debian / "rules").write_text("#!/usr/bin/make -f\n%:\n\tdh $@\n", encoding="utf-8")
        (debian / "rules").chmod(0o755)
        (debian / "source/format").write_text("3.0 (native)\n", encoding="utf-8")
        (debian / "sdlc-operations").write_text(
            "".join(f"{kind}\t{source}\t{dest}\n" for kind, source, dest in operations), encoding="utf-8")
        (out / "payload").mkdir(exist_ok=True)
        (debian / "install").write_text(f"payload usr/lib/{package}/\n", encoding="utf-8")
        # Quotes all managed paths before generating overlap and original-backup checks
        quoted_paths = " ".join(shlex.quote(p) for p in sorted(affected))
        preinst = f"""#!/bin/sh
set -eu
PKG={shlex.quote(package)}
BACKUP=/var/lib/$PKG/sdlc-backup
OWNERS=/var/lib/scr-sdlc/owners
mkdir -p "$BACKUP" "$OWNERS"
for path in {quoted_paths}; do
  key=$(printf '%s' "$path" | sha256sum | cut -d' ' -f1)
  if [ -e "$OWNERS/$key" ] && [ "$(cat "$OWNERS/$key")" != "$PKG" ]; then
    echo "SDLC path overlap: $path is managed by $(cat "$OWNERS/$key")" >&2
    exit 1
  fi
  printf '%s' "$PKG" > "$OWNERS/$key"
  if [ ! -e "$BACKUP/$key.saved" ] && [ ! -e "$BACKUP/$key.missing" ]; then
    printf '%s' "$path" > "$BACKUP/$key.path"
    if [ -e "$path" ] || [ -L "$path" ]; then
      cp -a -- "$path" "$BACKUP/$key.saved"
    else
      : > "$BACKUP/$key.missing"
    fi
  fi
done
exit 0
"""
        # Copies private payloads into place only after preinst preserves the original tree
        postinst_ops = []
        for kind, source, dest in operations:
            if kind in {"add", "replace"}:
                payload = f"/usr/lib/{package}/payload{source}"
                postinst_ops.extend([
                    f"test -e {shlex.quote(payload)} || {{ echo 'missing SDLC payload: {payload}' >&2; exit 1; }}",
                    f"mkdir -p -- {shlex.quote(str(Path(source).parent))}",
                    f"rm -rf -- {shlex.quote(source)}",
                    f"cp -a -- {shlex.quote(payload)} {shlex.quote(source)}",
                ])
            elif kind == "delete":
                postinst_ops.append(f"rm -rf -- {shlex.quote(source)}")
            elif kind == "move":
                postinst_ops.extend([f"mkdir -p -- {shlex.quote(str(Path(dest).parent))}",
                                     f"mv -- {shlex.quote(source)} {shlex.quote(dest)}"])
        postinst = "#!/bin/sh\nset -eu\n" + "\n".join(postinst_ops) + "\nexit 0\n"
        # Restores original metadata and removes ownership claims during package removal
        postrm = f"""#!/bin/sh
set -eu
PKG={shlex.quote(package)}
BACKUP=/var/lib/$PKG/sdlc-backup
OWNERS=/var/lib/scr-sdlc/owners
case "$1" in
  remove|purge|abort-install|disappear)
    if [ -d "$BACKUP" ]; then
      for marker in "$BACKUP"/*.path; do
        [ -e "$marker" ] || continue
        key=$(basename "$marker" .path)
        path=$(cat "$marker")
        rm -rf -- "$path"
        if [ -e "$BACKUP/$key.saved" ] || [ -L "$BACKUP/$key.saved" ]; then
          mkdir -p -- "$(dirname "$path")"
          cp -a -- "$BACKUP/$key.saved" "$path"
        fi
        rm -f -- "$OWNERS/$key"
      done
      rm -rf -- "/var/lib/$PKG"
      rmdir "$OWNERS" /var/lib/scr-sdlc 2>/dev/null || true
    fi
    ;;
esac
exit 0
"""
        # Publishes executable maintainer scripts without changing their generated bytes
        for name, content in (("preinst", preinst), ("postinst", postinst), ("postrm", postrm)):
            path = debian / name
            path.write_text(content, encoding="utf-8")
            path.chmod(0o755)
        (out / "README.md").write_text(
            f"# {package}\n\nGenerated reversible package scaffold for `{state['id']}` round {state['current_round']}.\n\n"
        f"Place each add/replace source at `payload/<absolute-target-path>`; the DEB owns it privately under "
        f"`/usr/lib/{package}/payload`, and `postinst` copies it into place after backing up the baseline. "
        "Do not install managed replacements directly or declare them as conffiles. "
        "Build with `dpkg-buildpackage -us -uc -b`, then validate only through `./bin/lets sdlc verify-package`.\n",
            encoding="utf-8")
        print(out)


class SdlcCliHelper(ABC):
    """Owns retained command parsing, model listing, and CLI dispatch."""

    @staticmethod
    def cmd_models(ctx: Context, _args: argparse.Namespace) -> None:
        """Prints each configured SDLC role with its model and effort.

        Args:
            ctx: Supplies repository configuration, ledger paths, and shared locks.
            _args: Supplies unused command arguments.
        """
        # Keeps role order and tab-separated output stable for routing inspection
        roles = ["COORDINATOR", "REQUIREMENTS", "IMAGE_ANALYSIS", "PLANNER",
                 "IMPLEMENTATION", "VALIDATION", "INTEGRATION", "QA", "FOLLOW_UP"]
        # Shows missing values explicitly as empty tab-separated fields
        for role in roles:
            print(f"{role.lower()}\t{ctx.conf.get(f'SDLC_{role}_MODEL', '')}\t"
              f"{ctx.conf.get(f'SDLC_{role}_EFFORT', '')}")

    @staticmethod
    def parser() -> argparse.ArgumentParser:
        """Builds the retained CLI parser with its original command options and callbacks.

        Steps:
            1. CREATE retained commands with their original options.
            2. BIND callbacks to their owning helper methods.

        Returns:
            Parser with all retained options and callback bindings.
        """
        # Preserves supported safety command options and callback semantics
        p = argparse.ArgumentParser(prog="lets sdlc")
        sub = p.add_subparsers(dest="command", required=True)
        sub.add_parser("models").set_defaults(func=SdlcCliHelper.cmd_models)
        vp = sub.add_parser("verify-package")
        vp.add_argument("id")
        vp.add_argument("--root", required=True)
        vp.add_argument("--deb", required=True)
        vp.add_argument("--test-command")
        vp.add_argument("--rollback-command", help="Runs package-specific rollback assertions instead of metadata fingerprints")
        vp.add_argument("--recover", action="store_true")
        vp.set_defaults(func=SdlcPackageHelper.cmd_verify_package)
        it = sub.add_parser("test-package")
        it.add_argument("id")
        it.add_argument("--image", required=True)
        it.add_argument("--deb", required=True)
        it.add_argument("--test-command")
        it.add_argument("--rollback-command", help="Runs package-specific rollback assertions instead of metadata fingerprints")
        it.set_defaults(func=SdlcPackageHelper.cmd_test_package)
        lr = sub.add_parser("lock-run")
        lr.add_argument("--image", required=True)
        lr.add_argument("command", nargs=argparse.REMAINDER)
        lr.set_defaults(func=SdlcPackageHelper.cmd_lock_run)
        pi = sub.add_parser("package-init")
        pi.add_argument("id")
        pi.add_argument("--package")
        pi.add_argument("--output")
        pi.add_argument("--operation", action="append", default=[])
        pi.add_argument("--force", action="store_true")
        pi.set_defaults(func=SdlcPackageHelper.cmd_package_init)
        return p

    @staticmethod
    def main() -> int:
        """Runs supported safety commands and refuses retired ceremonies at the retained CLI entry point.

        Returns:
            Zero after success, or one after a reported error.
        """
        # Keeps retired-command refusal ahead of repository context creation
        try:
            arguments = sys.argv[1:]
            if arguments and arguments[0] in RETIRED_COMMANDS:
                raise SDLCError("legacy ceremony retired; use ./bin/lets sdlc items --help")
            args = SdlcCliHelper.parser().parse_args(arguments)
            # Consumes only the CLI separator before forwarding the child command
            if arguments[0] == "lock-run" and args.command[:1] == ["--"]:
                args.command = args.command[1:]
            if getattr(args, "recover", False):
                os.environ["SDLC_RECOVERY"] = "1"
            ctx = Context(SdlcRuntimeHelper.repo_root())
            args.func(ctx, args)
            return 0
        except (SDLCError, subprocess.CalledProcessError, OSError, json.JSONDecodeError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
                print(exc.stderr.strip(), file=sys.stderr)
            return 1


if __name__ == "__main__":
    raise SystemExit(SdlcCliHelper.main())
