from __future__ import annotations

import argparse
import importlib.util
import json
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
