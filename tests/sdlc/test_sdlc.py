from __future__ import annotations

import argparse
import contextlib
import errno
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[2] / "tools/sdlc/src/sdlc.py"
SPEC = importlib.util.spec_from_file_location("scr_sdlc", MODULE_PATH)
assert SPEC and SPEC.loader
sdlc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sdlc)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.name", "SDLC Test")
    _git(tmp_path, "config", "user.email", "sdlc@example.invalid")
    (tmp_path / "etc").mkdir()
    (tmp_path / "etc/sdlc.conf").write_text(
        'SDLC_LEDGER_BRANCH="sdlc"\nSDLC_AUTO_PUSH="0"\n'
        'SDLC_VERIFY_EXCLUDES="/proc,/sys"\n', encoding="utf-8")
    (tmp_path / ".gitignore").write_text("/.codex/worktrees/\n/.codex/sdlc/\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("test\n", encoding="utf-8")
    _git(tmp_path, "add", "README.md", ".gitignore", "etc/sdlc.conf")
    _git(tmp_path, "commit", "-m", "Initial test repository")
    return tmp_path


def test_slug_is_uppercase_and_limited_to_four_words() -> None:
    assert sdlc.slug("count system restarts reliably forever") == "COUNT-SYSTEM-RESTARTS-RELIABLY"
    with pytest.raises(sdlc.SDLCError):
        sdlc.slug("---")


def test_new_requirement_mints_id_and_commits_ledger(repo: Path) -> None:
    ctx = sdlc.Context(repo)
    args = argparse.Namespace(description="Count system restarts reliably", title=None,
                              instructions="Preserve the existing counter.")
    sdlc.cmd_new(ctx, args)
    req_id = "REQ-0001-COUNT-SYSTEM-RESTARTS-RELIABLY"
    state = json.loads(sdlc.state_path(ctx, req_id).read_text(encoding="utf-8"))
    assert state["state"] == "requirements-analysis"
    assert state["current_round"] == 1
    assert "## Round 1" in sdlc.doc_path(ctx, req_id).read_text(encoding="utf-8")
    assert (ctx.req_dir / ".ids/0001").read_text(encoding="utf-8").strip() == req_id
    tracked = subprocess.run(["git", "ls-files", "docs/requirements/.ids/0001"], cwd=ctx.ledger,
                             check=True, capture_output=True, text=True)
    assert tracked.stdout.strip()
    result = subprocess.run(["git", "log", "-1", "--format=%s"], cwd=ctx.ledger,
                            check=True, capture_output=True, text=True)
    assert req_id in result.stdout


def test_state_machine_rejects_skipped_stage(repo: Path) -> None:
    ctx = sdlc.Context(repo)
    sdlc.cmd_new(ctx, argparse.Namespace(description="Safe service restart", title=None, instructions=None))
    req_id = "REQ-0001-SAFE-SERVICE-RESTART"
    with pytest.raises(sdlc.SDLCError, match="invalid transition"):
        sdlc.transition(ctx, req_id, "implementing", "skip")
    sdlc.transition(ctx, req_id, "image-analysis", "requirements analyzed")
    assert sdlc.load_state(ctx, req_id)["state"] == "image-analysis"


def test_models_and_resume_dispatch_validated_work_to_integration(
        repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Routes passed validation to dedicated integration agent."""
    ctx = sdlc.Context(repo)
    sdlc.cmd_models(ctx, argparse.Namespace())
    assert "integration\t" in capsys.readouterr().out
    sdlc.cmd_new(ctx, argparse.Namespace(
        description="Integrate validated package", title=None, instructions=None))
    req_id = "REQ-0001-INTEGRATE-VALIDATED-PACKAGE"
    state = sdlc.load_state(ctx, req_id)
    state["state"] = "validating"
    state["validation"] = {"status": "pass"}
    sdlc.atomic_json(sdlc.state_path(ctx, req_id), state)
    capsys.readouterr()
    sdlc.cmd_resume(ctx, argparse.Namespace(id=req_id, json=True))
    result = json.loads(capsys.readouterr().out)
    assert result["action"] == "sdlc_integration"


def test_main_tree_lock_key_is_shared_by_linked_worktrees(repo: Path, tmp_path: Path) -> None:
    """Uses one Git-common-directory lock across repository worktrees."""
    linked = tmp_path / "linked"
    _git(repo, "worktree", "add", "-b", "linked", str(linked))
    (linked / "etc/sdlc.conf").write_text(
        'SDLC_LEDGER_BRANCH="sdlc"\nSDLC_AUTO_PUSH="0"\n', encoding="utf-8")
    main_ctx = sdlc.Context(repo)
    linked_ctx = sdlc.Context(linked)
    assert main_ctx.main_tree_lock_root == linked_ctx.main_tree_lock_root
    with main_ctx.lock("main-tree") as main_lock:
        assert main_lock == main_ctx.main_tree_lock_root / "main-tree.lock"


def test_merge_enters_main_tree_lock_before_registry(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Acquires main-tree lock before any registry-backed merge inspection."""
    ctx = sdlc.Context(repo)
    entered = []

    @contextlib.contextmanager
    def recording_lock(name: str, timeout: int | None = None):
        """Records lock acquisition order."""
        entered.append(name)
        if name == "registry":
            raise sdlc.SDLCError("stop after lock ordering")
        yield Path("/lock")

    monkeypatch.setattr(ctx, "lock", recording_lock)
    with pytest.raises(sdlc.SDLCError, match="stop after lock ordering"):
        sdlc.cmd_merge(ctx, argparse.Namespace(id="REQ-0001-NOT-USED", target=None))
    assert entered == ["main-tree", "registry"]


def test_generic_stage_rejects_evidence_gated_states(repo: Path) -> None:
    ctx = sdlc.Context(repo)
    sdlc.cmd_new(ctx, argparse.Namespace(description="Gate implementation evidence", title=None,
                                          instructions=None))
    with pytest.raises(sdlc.SDLCError, match="evidence-gated"):
        sdlc.cmd_stage(ctx, argparse.Namespace(
            id="REQ-0001-GATE-IMPLEMENTATION-EVIDENCE", state="implementation-ready", message=None))


def test_plan_revisions_are_hashed_and_approval_is_pinned(repo: Path, tmp_path: Path) -> None:
    ctx = sdlc.Context(repo)
    sdlc.cmd_new(ctx, argparse.Namespace(description="Pin approved plan", title=None, instructions=None))
    req_id = "REQ-0001-PIN-APPROVED-PLAN"
    state = sdlc.load_state(ctx, req_id)
    state["state"] = "draft-ready"
    sdlc.atomic_json(sdlc.state_path(ctx, req_id), state)
    plan = tmp_path / "plan.md"
    plan.write_text("Replace one file and verify restoration.", encoding="utf-8")
    sdlc.cmd_section(ctx, argparse.Namespace(id=req_id, name="solution-plan", file=str(plan)))
    sdlc.cmd_approve(ctx, argparse.Namespace(id=req_id, auto=False, reason="Approved in test"))
    state = sdlc.load_state(ctx, req_id)
    assert state["approval"]["plan_revision"] == 1
    assert state["approval"]["plan_sha256"] == state["plan"]["sha256"]
    assert "DRAFT revision 1" in sdlc.doc_path(ctx, req_id).read_text(encoding="utf-8")


def _prepare_task_plan(ctx: object, tmp_path: Path) -> str:
    req_id = "REQ-0001-SPLIT-APPROVED-PLAN"
    sdlc.cmd_new(ctx, argparse.Namespace(description="Split approved plan", title=None, instructions=None))
    state = sdlc.load_state(ctx, req_id)
    state["state"] = "draft-ready"
    sdlc.atomic_json(sdlc.state_path(ctx, req_id), state)
    plan = tmp_path / "plan.md"
    plan.write_text("Implement bounded tasks.", encoding="utf-8")
    sdlc.cmd_section(ctx, argparse.Namespace(id=req_id, name="solution-plan", file=str(plan)))
    state = sdlc.load_state(ctx, req_id)
    state["state"] = "awaiting-approval"
    sdlc.atomic_json(sdlc.state_path(ctx, req_id), state)
    (tmp_path / "contract.md").write_text("Preserve safety.", encoding="utf-8")
    (tmp_path / "interfaces.md").write_text("T01 writes output consumed by T02.", encoding="utf-8")
    (tmp_path / "acceptance.json").write_text(json.dumps({"criteria": [
        {"id": "AC-01", "text": "Core works"}, {"id": "AC-02", "text": "Package works"}
    ]}), encoding="utf-8")
    (tmp_path / "T01.md").write_text("Build core.\n", encoding="utf-8")
    (tmp_path / "T02.md").write_text("Build package.\n", encoding="utf-8")
    manifest = {"plan_sha256": state["plan"]["sha256"], "contract": "contract.md",
                "interfaces": "interfaces.md", "acceptance": "acceptance.json",
                "tasks": [
                    {"id": "T01", "file": "T01.md", "depends_on": [], "acceptance": ["AC-01"]},
                    {"id": "T02", "file": "T02.md", "depends_on": ["T01"], "acceptance": ["AC-02"]},
                ]}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    sdlc.cmd_task_plan(ctx, argparse.Namespace(id=req_id, manifest=str(manifest_path)))
    return req_id


def test_task_plan_binds_plan_and_copies_bounded_artifacts(repo: Path, tmp_path: Path) -> None:
    ctx = sdlc.Context(repo)
    req_id = _prepare_task_plan(ctx, tmp_path)
    state = sdlc.load_state(ctx, req_id)
    root = sdlc.task_artifact_dir(ctx, req_id, 1)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["approved_plan_sha256"] == state["plan"]["sha256"]
    assert manifest["tasks"][1]["depends_on"] == ["T01"]
    assert state["task_workflow"]["tasks"]["T01"]["status"] == "pending"
    tracked = subprocess.run(["git", "ls-files", str((root / "tasks/T01.md").relative_to(ctx.ledger))],
                             cwd=ctx.ledger, check=True, capture_output=True, text=True)
    assert tracked.stdout.strip()


def test_task_execution_enforces_result_and_validation_gates(repo: Path, tmp_path: Path) -> None:
    ctx = sdlc.Context(repo)
    req_id = _prepare_task_plan(ctx, tmp_path)
    sdlc.cmd_approve(ctx, argparse.Namespace(id=req_id, auto=False, reason="Approved in test"))
    state = sdlc.load_state(ctx, req_id)
    state["state"] = "implementing"
    sdlc.atomic_json(sdlc.state_path(ctx, req_id), state)
    sdlc.update_doc_metadata(ctx, state)
    sdlc.cmd_task_next(ctx, argparse.Namespace(id=req_id))
    with pytest.raises(sdlc.SDLCError, match="task already active"):
        sdlc.cmd_task_next(ctx, argparse.Namespace(id=req_id))
    result = tmp_path / "result.json"
    result.write_text('{"commit":"abc","tests":["unit"]}', encoding="utf-8")
    validation = tmp_path / "validation.json"
    validation.write_text('{"checks":["diff","tests"]}', encoding="utf-8")
    sdlc.cmd_task_result(ctx, argparse.Namespace(id=req_id, task="T01", report_file=str(result)))
    with pytest.raises(sdlc.SDLCError, match="no task is runnable"):
        state = sdlc.load_state(ctx, req_id)
        state["task_workflow"]["active"] = None
        sdlc.atomic_json(sdlc.state_path(ctx, req_id), state)
        sdlc.cmd_task_next(ctx, argparse.Namespace(id=req_id))
    state = sdlc.load_state(ctx, req_id)
    state["task_workflow"]["active"] = "T01"
    sdlc.atomic_json(sdlc.state_path(ctx, req_id), state)
    sdlc.cmd_task_validate(ctx, argparse.Namespace(
        id=req_id, task="T01", result="pass", report_file=str(validation)))
    sdlc.cmd_task_next(ctx, argparse.Namespace(id=req_id))
    assert sdlc.load_state(ctx, req_id)["task_workflow"]["active"] == "T02"


def test_failed_task_validation_preserves_attempt_evidence(repo: Path, tmp_path: Path) -> None:
    ctx = sdlc.Context(repo)
    req_id = _prepare_task_plan(ctx, tmp_path)
    sdlc.cmd_approve(ctx, argparse.Namespace(id=req_id, auto=False, reason="Approved in test"))
    state = sdlc.load_state(ctx, req_id)
    state["state"] = "implementing"
    sdlc.atomic_json(sdlc.state_path(ctx, req_id), state)
    sdlc.cmd_task_next(ctx, argparse.Namespace(id=req_id))
    report = tmp_path / "report.json"
    report.write_text('{"evidence":"first"}', encoding="utf-8")
    sdlc.cmd_task_result(ctx, argparse.Namespace(id=req_id, task="T01", report_file=str(report)))
    sdlc.cmd_task_validate(ctx, argparse.Namespace(
        id=req_id, task="T01", result="fail", report_file=str(report)))
    sdlc.cmd_task_next(ctx, argparse.Namespace(id=req_id))
    root = sdlc.task_artifact_dir(ctx, req_id, 1)
    assert (root / "evidence/T01-validation-001.json").is_file()
    assert sdlc.load_state(ctx, req_id)["task_workflow"]["tasks"]["T01"]["attempts"] == 2


def test_hardware_failure_opens_next_round(repo: Path) -> None:
    ctx = sdlc.Context(repo)
    sdlc.cmd_new(ctx, argparse.Namespace(description="Repair watchdog loop", title=None, instructions=None))
    req_id = "REQ-0001-REPAIR-WATCHDOG-LOOP"
    state = sdlc.load_state(ctx, req_id)
    state["state"] = "awaiting-hardware"
    sdlc.atomic_json(sdlc.state_path(ctx, req_id), state)
    sdlc.update_doc_metadata(ctx, state)
    sdlc.cmd_follow_up(ctx, argparse.Namespace(id=req_id, result="fail", notes="Unit rebooted after 20 minutes"))
    state = sdlc.load_state(ctx, req_id)
    assert state["current_round"] == 2
    assert state["state"] == "requirements-analysis"
    assert state["rounds"][0]["status"] == "failed"


def test_fingerprint_detects_content_and_mode_changes(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = root / "etc.conf"
    target.write_text("a", encoding="utf-8")
    before = sdlc.fingerprint_tree(root, [])
    target.write_text("b", encoding="utf-8")
    after = sdlc.fingerprint_tree(root, [])
    assert before != after
    empty = root / "empty"
    empty.mkdir()
    assert "/empty" in sdlc.fingerprint_tree(root, [])


def test_fingerprint_detects_timestamp_changes(tmp_path: Path) -> None:
    """Detects restored content carrying changed filesystem timestamps."""
    root = tmp_path / "root"
    root.mkdir()
    target = root / "value"
    target.write_text("same", encoding="utf-8")
    before = sdlc.fingerprint_tree(root, [])
    stat = target.stat()
    os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
    assert before != sdlc.fingerprint_tree(root, [])


def test_fingerprint_detects_hardlink_relationship_changes(tmp_path: Path) -> None:
    """Detects replacement of one hard link by an independent identical file."""
    root = tmp_path / "root"
    root.mkdir()
    first = root / "first"
    second = root / "second"
    first.write_text("same", encoding="utf-8")
    os.link(first, second)
    before = sdlc.fingerprint_tree(root, [])
    second.unlink()
    second.write_text("same", encoding="utf-8")
    stat = first.stat()
    os.utime(second, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    assert before != sdlc.fingerprint_tree(root, [])


def test_fingerprint_detects_xattr_changes(tmp_path: Path) -> None:
    """Detects changed extended attributes when filesystem supports user xattrs."""
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
    before = sdlc.fingerprint_tree(root, [])
    os.setxattr(target, "user.sdlc-test", b"after")
    assert before != sdlc.fingerprint_tree(root, [])


def test_fingerprint_records_root_and_directory_symlink(tmp_path: Path) -> None:
    """Records mount-root metadata and directory links without following them."""
    root = tmp_path / "root"
    root.mkdir()
    target = root / "target"
    target.mkdir()
    link = root / "linked-directory"
    link.symlink_to(target, target_is_directory=True)
    fingerprint = sdlc.fingerprint_tree(root, [])
    assert fingerprint["/"]["type"] == "directory"
    assert fingerprint["/linked-directory"]["type"] == "symlink"
    assert fingerprint["/linked-directory"]["link"] == str(target)


def test_image_lock_rechecks_global_quarantine_after_flock(
        repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Rejects quarantine created between image-lock preflight and acquisition."""
    ctx = sdlc.Context(repo)
    original_flock = sdlc.fcntl.flock
    created = False

    def racing_flock(fd: int, operation: int) -> None:
        """Creates quarantine when exclusive flock succeeds."""
        nonlocal created
        original_flock(fd, operation)
        if operation & sdlc.fcntl.LOCK_EX and not created:
            created = True
            sdlc.atomic_json(ctx.lock_root / "quarantine/image-dirty.json", {"phase": "quarantined"})

    monkeypatch.setattr(sdlc.fcntl, "flock", racing_flock)
    with pytest.raises(sdlc.SDLCError, match="logically locked by quarantine"):
        with ctx.lock("image"):
            pytest.fail("quarantined image work started")


def test_verify_package_fingerprint_failure_quarantines(
        repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Quarantines image when initial restoration fingerprint cannot be read."""
    ctx = sdlc.Context(repo)
    root = tmp_path / "mounted"
    root.mkdir()
    deb = tmp_path / "package.deb"
    deb.write_bytes(b"deb")
    monkeypatch.setattr(sdlc, "package_name", lambda _deb: "test-package")
    monkeypatch.setattr(sdlc, "fingerprint_tree",
                        lambda _root, _excludes: (_ for _ in ()).throw(OSError("read failed")))
    args = argparse.Namespace(root=str(root), deb=str(deb), recover=False, test_command=None)
    with pytest.raises(sdlc.SDLCError, match="fingerprint failed and was quarantined"):
        sdlc.cmd_verify_package(ctx, args)
    identity = sdlc.hashlib.sha256(str(root.resolve()).encode()).hexdigest()[:20]
    assert (ctx.lock_root / f"quarantine/image-{identity}.json").is_file()
    assert (ctx.lock_root / "quarantine/image-dirty.json").is_file()


def test_failed_mount_attempts_cleanup_and_quarantines_if_still_mounted(
        repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Attempts cleanup after partial mount and quarantines unproved cleanup."""
    ctx = sdlc.Context(repo)
    image = tmp_path / "image.img"
    image.write_bytes(b"image")
    deb = tmp_path / "package.deb"
    deb.write_bytes(b"deb")
    active_state = repo / ".lets/scr/image/mount.state"
    calls = []

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        """Simulates partial mount followed by failed unmount."""
        calls.append(command)
        if command[0] == "cp":
            Path(command[-1]).write_bytes(image.read_bytes())
            return subprocess.CompletedProcess(command, 0, "", "")
        if command[-1] == "--rw":
            active_state.parent.mkdir(parents=True, exist_ok=True)
            active_state.write_text("partial", encoding="utf-8")
            raise subprocess.CalledProcessError(1, command)
        return subprocess.CompletedProcess(command, 1, "", "")

    monkeypatch.setattr(sdlc, "run", fake_run)
    args = argparse.Namespace(id="REQ-0001-TEST", image=str(image), deb=str(deb), test_command=None)
    with pytest.raises(sdlc.SDLCError, match="cleanup failed and was quarantined"):
        sdlc.cmd_test_package(ctx, args)
    assert any(command[-2:] == ["image", "umount"] for command in calls)
    assert (ctx.lock_root / "quarantine/image-dirty.json").is_file()


def test_scratch_cleanup_failure_quarantines(
        repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Quarantines image when disposable scratch cannot be removed."""
    ctx = sdlc.Context(repo)
    image = tmp_path / "image.img"
    image.write_bytes(b"image")
    deb = tmp_path / "package.deb"
    deb.write_bytes(b"deb")

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        """Simulates successful copy, mount, and unmount commands."""
        if command[0] == "cp":
            Path(command[-1]).write_bytes(image.read_bytes())
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(sdlc, "run", fake_run)
    monkeypatch.setattr(sdlc.subprocess, "run",
                        lambda command, **_kwargs: subprocess.CompletedProcess(command, 0, "", ""))
    monkeypatch.setattr(sdlc.shutil, "rmtree",
                        lambda _path: (_ for _ in ()).throw(OSError("scratch busy")))
    args = argparse.Namespace(id="REQ-0001-TEST", image=str(image), deb=str(deb), test_command=None)
    with pytest.raises(sdlc.SDLCError, match="scratch cleanup failed and was quarantined"):
        sdlc.cmd_test_package(ctx, args)
    assert (ctx.lock_root / "quarantine/image-dirty.json").is_file()


def test_worktree_links_shared_untracked_runtime_paths(repo: Path) -> None:
    """Links main checkout runtime paths into created requirement worktrees."""
    (repo / "var").mkdir()
    (repo / "admin").mkdir()
    ctx = sdlc.Context(repo)
    sdlc.cmd_new(ctx, argparse.Namespace(
        description="Link shared runtime paths", title=None, instructions=None))
    req_id = "REQ-0001-LINK-SHARED-RUNTIME-PATHS"
    sdlc.cmd_worktree(ctx, argparse.Namespace(id=req_id, base=None))
    worktree = ctx.worktrees / req_id
    for name in ("var", "admin"):
        assert (worktree / name).is_symlink()
        assert (worktree / name).resolve() == (repo / name).resolve()


def test_worktree_refuses_unexpected_shared_path(repo: Path) -> None:
    """Refuses replacement when a shared-path destination already exists."""
    (repo / "var").mkdir()
    worktree = repo / "manual-worktree"
    worktree.mkdir()
    (worktree / "var").mkdir()
    with pytest.raises(sdlc.SDLCError, match="unexpected existing worktree path"):
        sdlc.link_shared_worktree_paths(repo, worktree)


def test_managed_paths_must_be_safe_absolute_paths() -> None:
    assert sdlc.validate_managed_path("/etc/monitrc") == "/etc/monitrc"
    for value in ("etc/monitrc", "/", "/etc/../root"):
        with pytest.raises(sdlc.SDLCError):
            sdlc.validate_managed_path(value)


def test_package_scaffold_contains_reversible_maintainer_scripts(repo: Path) -> None:
    ctx = sdlc.Context(repo)
    sdlc.cmd_new(ctx, argparse.Namespace(description="Replace monit configuration", title=None,
                                          instructions=None))
    req_id = "REQ-0001-REPLACE-MONIT-CONFIGURATION"
    state = sdlc.load_state(ctx, req_id)
    state["state"] = "approved"
    sdlc.atomic_json(sdlc.state_path(ctx, req_id), state)
    output = repo / "implementation"
    sdlc.cmd_package_init(ctx, argparse.Namespace(
        id=req_id, package=None, output=str(output), force=False,
        operation=["replace:/etc/monit/monitrc", "move:/etc/old.conf:/etc/new.conf"],
    ))
    package_root = output / "packages" / f"{req_id}-round-1"
    for script in ("preinst", "postinst", "postrm"):
        subprocess.run(["sh", "-n", str(package_root / "debian" / script)], check=True)
    assert "SDLC path overlap" in (package_root / "debian/preinst").read_text(encoding="utf-8")
    assert "sdlc-backup" in (package_root / "debian/postrm").read_text(encoding="utf-8")
    control = (package_root / "debian/control").read_text(encoding="utf-8")
    assert f"Package: scr-{req_id.lower()}\n" in control
