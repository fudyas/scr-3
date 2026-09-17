"""Deterministic state and safety tooling for the SCR agentic SDLC pipeline."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
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
from pathlib import Path

SCHEMA_VERSION = 1
ID_RE = re.compile(r"^REQ-(\d{4})-([A-Z0-9]+(?:-[A-Z0-9]+){0,3})$")
STATES = {
    "requirements-analysis", "image-analysis", "planner-questions",
    "drafting-plan", "draft-ready", "awaiting-approval", "auto-approved",
    "approved", "implementing", "implementation-ready", "validating",
    "awaiting-hardware", "hardware-failed", "passed", "abandoned",
    "recovery-required",
}
ALLOWED_TRANSITIONS = {
    "requirements-analysis": {"image-analysis", "abandoned", "recovery-required"},
    "image-analysis": {"planner-questions", "abandoned", "recovery-required"},
    "planner-questions": {"drafting-plan", "abandoned"},
    "drafting-plan": {"draft-ready", "abandoned", "recovery-required"},
    "draft-ready": {"awaiting-approval", "auto-approved", "drafting-plan", "abandoned"},
    "awaiting-approval": {"approved", "drafting-plan", "abandoned"},
    "auto-approved": {"implementing", "abandoned"},
    "approved": {"implementing", "abandoned"},
    "implementing": {"implementation-ready", "recovery-required", "abandoned"},
    "implementation-ready": {"validating", "implementing", "abandoned"},
    "validating": {"awaiting-hardware", "implementing", "recovery-required", "abandoned"},
    "awaiting-hardware": {"passed", "requirements-analysis", "abandoned"},
    "hardware-failed": {"requirements-analysis", "abandoned"},
    "recovery-required": {"implementing", "validating", "abandoned"},
}


class SDLCError(RuntimeError):
    pass


def run(args: list[str], *, cwd: Path | None = None, check: bool = True,
        capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args, cwd=cwd, check=check, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["git", "--no-pager", *args], cwd=root, check=check)


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def slug(value: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", value.upper())[:4]
    if not words:
        raise SDLCError("description must contain at least one letter or digit")
    return "-".join(words)


def parse_conf(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
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


class Context:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.conf = parse_conf(self.root / "etc/sdlc.conf")
        self.branch = self.conf.get("SDLC_LEDGER_BRANCH", "sdlc")
        self.remote = self.conf.get("SDLC_REMOTE", "origin")
        self.auto_push = self.conf.get("SDLC_AUTO_PUSH", "1") == "1"
        def configured_path(key: str, fallback: str) -> Path:
            raw = self.conf.get(key, fallback).replace("${LETS_PROJ_DIR}", str(self.root))
            expanded = Path(os.path.expandvars(raw)).expanduser()
            return (self.root / expanded).resolve() if not expanded.is_absolute() else expanded.resolve()

        self.worktrees = configured_path("SDLC_WORKTREE_ROOT", ".codex/worktrees")
        self.runtime = configured_path("SDLC_RUNTIME_ROOT", ".codex/sdlc")
        self.lock_root = configured_path("SDLC_SHARED_LOCK_ROOT", ".codex/sdlc")
        self.ledger = self.worktrees / "sdlc"
        self.req_dir_name = self.conf.get("SDLC_REQUIREMENTS_DIR", "docs/requirements")
        self.runtime.mkdir(parents=True, exist_ok=True)
        (self.runtime / "locks").mkdir(parents=True, exist_ok=True)
        (self.runtime / "quarantine").mkdir(parents=True, exist_ok=True)
        (self.lock_root / "locks").mkdir(parents=True, exist_ok=True)
        (self.lock_root / "quarantine").mkdir(parents=True, exist_ok=True)

    @property
    def req_dir(self) -> Path:
        return self.ledger / self.req_dir_name

    @contextlib.contextmanager
    def lock(self, name: str, timeout: int | None = None):
        dirty = self.lock_root / "quarantine" / "image-dirty.json"
        if name == "image" and dirty.exists() and os.environ.get("SDLC_RECOVERY") != "1":
            raise SDLCError(f"image operations are logically locked by quarantine: {dirty}")
        path = self.lock_root / "locks" / f"{name}.lock"
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
            handle.seek(0)
            handle.truncate()
            json.dump({"pid": os.getpid(), "host": socket.gethostname(), "time": now()}, handle)
            handle.flush()
            os.fsync(handle.fileno())
            try:
                yield path
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def repo_root() -> Path:
    env = os.environ.get("LETS_PROJ_DIR")
    if env:
        return Path(env)
    result = run(["git", "--no-pager", "rev-parse", "--show-toplevel"])
    return Path(result.stdout.strip())


def remote_branch_exists(ctx: Context) -> bool:
    return git(ctx.root, "show-ref", "--verify", "--quiet",
               f"refs/remotes/{ctx.remote}/{ctx.branch}", check=False).returncode == 0


def local_branch_exists(ctx: Context) -> bool:
    return git(ctx.root, "show-ref", "--verify", "--quiet",
               f"refs/heads/{ctx.branch}", check=False).returncode == 0


def ensure_ledger(ctx: Context) -> None:
    if (ctx.ledger / ".git").exists():
        return
    ctx.worktrees.mkdir(parents=True, exist_ok=True)
    if ctx.ledger.exists() and any(ctx.ledger.iterdir()):
        raise SDLCError(f"ledger worktree path is not empty: {ctx.ledger}")
    if ctx.ledger.exists():
        ctx.ledger.rmdir()
    if not local_branch_exists(ctx):
        git(ctx.root, "fetch", ctx.remote, ctx.branch, check=False)
    if local_branch_exists(ctx):
        git(ctx.root, "worktree", "add", str(ctx.ledger), ctx.branch)
    elif remote_branch_exists(ctx):
        git(ctx.root, "worktree", "add", "-b", ctx.branch, str(ctx.ledger),
            f"{ctx.remote}/{ctx.branch}")
    else:
        base = git(ctx.root, "rev-parse", "HEAD").stdout.strip()
        git(ctx.root, "worktree", "add", "-b", ctx.branch, str(ctx.ledger), base)
    ctx.req_dir.mkdir(parents=True, exist_ok=True)


def sync_ledger(ctx: Context) -> None:
    if not ctx.auto_push:
        return
    fetched = git(ctx.ledger, "fetch", ctx.remote, ctx.branch, check=False)
    if fetched.returncode != 0:
        return
    if remote_branch_exists(ctx):
        result = git(ctx.ledger, "rebase", f"{ctx.remote}/{ctx.branch}", check=False)
        if result.returncode != 0:
            git(ctx.ledger, "rebase", "--abort", check=False)
            raise SDLCError(f"cannot synchronize sdlc ledger: {result.stderr.strip()}")


def push_ledger(ctx: Context) -> None:
    if not ctx.auto_push:
        return
    result = git(ctx.ledger, "push", "-u", ctx.remote, ctx.branch, check=False)
    if result.returncode != 0:
        raise SDLCError(f"cannot push sdlc ledger: {result.stderr.strip()}")


def atomic_json(path: Path, value: object) -> None:
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


def state_path(ctx: Context, req_id: str) -> Path:
    return ctx.req_dir / ".state" / f"{req_id}.json"


def doc_path(ctx: Context, req_id: str) -> Path:
    return ctx.req_dir / f"{req_id}.md"


def load_state(ctx: Context, req_id: str) -> dict:
    match = resolve_id(ctx, req_id)
    path = state_path(ctx, match)
    if not path.exists():
        raise SDLCError(f"unknown requirement: {req_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_id(ctx: Context, value: str) -> str:
    if ID_RE.match(value):
        return value
    token = value.upper()
    candidates = [p.stem for p in (ctx.req_dir / ".state").glob(f"{token}*.json")]
    if len(candidates) != 1:
        raise SDLCError(f"requirement id is unknown or ambiguous: {value}")
    return candidates[0]


def frontmatter(state: dict) -> str:
    approval = state.get("approval", {}).get("status", "none")
    impl = state.get("implementation", {})
    return "\n".join([
        "---", f"schema: {state['schema_version']}", f"id: {state['id']}",
        f"title: {state['title']}", f"state: {state['state']}",
        f"round: {state['current_round']}", f"sequence: {state['sequence']}",
        f"approval: {approval}", f"implementation_branch: {impl.get('branch', '')}",
        f"implementation_commit: {impl.get('commit', '')}",
        f"updated: {state['updated']}", "---",
    ])


def update_doc_metadata(ctx: Context, state: dict) -> None:
    path = doc_path(ctx, state["id"])
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise SDLCError(f"requirement document has no managed frontmatter: {path}")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise SDLCError(f"requirement document frontmatter is malformed: {path}")
    path.write_text(frontmatter(state) + text[end + 4:], encoding="utf-8")


def append_event(ctx: Context, state: dict, message: str) -> None:
    round_no = state["current_round"]
    event = {"sequence": state["sequence"], "time": now(), "state": state["state"],
             "message": message}
    state["rounds"][round_no - 1]["events"].append(event)
    path = doc_path(ctx, state["id"])
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"\n- `{event['time']}` [{event['state']}] {message}\n")


def save_state(ctx: Context, state: dict, message: str) -> None:
    state["sequence"] += 1
    state["updated"] = now()
    append_event(ctx, state, message)
    atomic_json(state_path(ctx, state["id"]), state)
    update_doc_metadata(ctx, state)


def commit_ledger(ctx: Context, req_id: str, message: str) -> None:
    rel_doc = doc_path(ctx, req_id).relative_to(ctx.ledger)
    rel_state = state_path(ctx, req_id).relative_to(ctx.ledger)
    claim_number = ID_RE.match(req_id).group(1)  # type: ignore[union-attr]
    claim = (ctx.req_dir / ".ids" / claim_number).relative_to(ctx.ledger)
    paths = [str(rel_doc), str(rel_state)]
    if (ctx.ledger / claim).exists():
        paths.append(str(claim))
    git(ctx.ledger, "add", "--", *paths)
    staged = git(ctx.ledger, "diff", "--cached", "--quiet", check=False)
    if staged.returncode == 0:
        return
    git(ctx.ledger, "commit", "-m", message)
    push_ledger(ctx)


def next_id(ctx: Context) -> int:
    used = []
    ids = ctx.req_dir / ".ids"
    if ids.exists():
        for path in ids.iterdir():
            if path.name.isdigit():
                used.append(int(path.name))
    return max(used, default=0) + 1


def cmd_init(ctx: Context, _args: argparse.Namespace) -> None:
    with ctx.lock("registry"):
        ensure_ledger(ctx)
        sync_ledger(ctx)
        ctx.req_dir.mkdir(parents=True, exist_ok=True)
        (ctx.req_dir / ".ids").mkdir(exist_ok=True)
        (ctx.req_dir / ".state").mkdir(exist_ok=True)
    print(ctx.ledger)


def cmd_new(ctx: Context, args: argparse.Namespace) -> None:
    retry = False
    with ctx.lock("registry"):
        ensure_ledger(ctx)
        sync_ledger(ctx)
        number = next_id(ctx)
        if number > 9999:
            raise SDLCError("requirement id space exhausted")
        tag = slug(args.description)
        req_id = f"REQ-{number:04d}-{tag}"
        claim = ctx.req_dir / ".ids" / f"{number:04d}"
        claim.parent.mkdir(parents=True, exist_ok=True)
        claim.write_text(req_id + "\n", encoding="utf-8")
        state = {
            "schema_version": SCHEMA_VERSION, "id": req_id, "title": args.title or args.description,
            "state": "requirements-analysis", "current_round": 1, "sequence": 0,
            "created": now(), "updated": now(), "approval": {"status": "none"},
            "implementation": {},
            "rounds": [{"number": 1, "status": "active",
                        "customer_requirements": args.description,
                        "additional_instructions": args.instructions or "", "events": []}],
        }
        document = f"""{frontmatter(state)}

# {req_id}: {state['title']}

## Round 1

### Customer requirements

{args.description}

### Developer instructions

{args.instructions or 'None.'}

### Requirements analysis

Pending.

### Image analysis

Pending.

### Planner questions and answers

Pending.

### Solution plan — DRAFT

Pending.

### Approval

Pending.

### Implementation

Pending. Every realization must be a reversible Debian package.

### Validation

Pending.

### Hardware follow-up

Pending.

### Event log
"""
        doc_path(ctx, req_id).parent.mkdir(parents=True, exist_ok=True)
        doc_path(ctx, req_id).write_text(document, encoding="utf-8")
        save_state(ctx, state, "Round 1 created from customer requirements")
        atomic_json(state_path(ctx, req_id), state)
        try:
            commit_ledger(ctx, req_id, f"Created {req_id} round 1")
        except SDLCError:
            attempt = getattr(args, "_mint_attempt", 0)
            fetched = git(ctx.ledger, "fetch", ctx.remote, ctx.branch, check=False)
            if ctx.auto_push and fetched.returncode == 0 and remote_branch_exists(ctx) and attempt < 4:
                # The ledger worktree is pipeline-owned. A rejected optimistic push
                # means another host won the ID race; discard only this unpushed
                # attempt, recompute from the authoritative branch, and retry.
                git(ctx.ledger, "reset", "--hard", f"{ctx.remote}/{ctx.branch}")
                git(ctx.ledger, "clean", "-fd", "--", ctx.req_dir_name)
                args._mint_attempt = attempt + 1
                retry = True
            else:
                raise
    if retry:
        return cmd_new(ctx, args)
    print(req_id)
    print(doc_path(ctx, req_id))


def cmd_list(ctx: Context, _args: argparse.Namespace) -> None:
    ensure_ledger(ctx)
    for path in sorted((ctx.req_dir / ".state").glob("REQ-*.json")):
        state = json.loads(path.read_text(encoding="utf-8"))
        print(f"{state['id']}\t{state['state']}\tround {state['current_round']}\t{state['title']}")


def cmd_show(ctx: Context, args: argparse.Namespace) -> None:
    ensure_ledger(ctx)
    req_id = resolve_id(ctx, args.id)
    print(doc_path(ctx, req_id).read_text(encoding="utf-8"), end="")


def cmd_status(ctx: Context, args: argparse.Namespace) -> None:
    ensure_ledger(ctx)
    state = load_state(ctx, args.id)
    print(json.dumps(state, indent=2) if args.json else
          f"{state['id']}: {state['state']} (round {state['current_round']}, sequence {state['sequence']})")


def cmd_path(ctx: Context, args: argparse.Namespace) -> None:
    ensure_ledger(ctx)
    print(doc_path(ctx, resolve_id(ctx, args.id)))


def transition(ctx: Context, req_id_value: str, target: str, message: str) -> None:
    if target not in STATES:
        raise SDLCError(f"invalid pipeline state: {target}")
    with ctx.lock("registry"):
        ensure_ledger(ctx)
        sync_ledger(ctx)
        state = load_state(ctx, req_id_value)
        source = state["state"]
        if source in {"passed", "abandoned"}:
            raise SDLCError(f"closed requirement cannot transition: {state['state']}")
        if target not in ALLOWED_TRANSITIONS.get(source, set()):
            raise SDLCError(f"invalid transition: {source} -> {target}")
        state["state"] = target
        save_state(ctx, state, message)
        commit_ledger(ctx, state["id"], f"Updated {state['id']} to {target}")


def cmd_stage(ctx: Context, args: argparse.Namespace) -> None:
    if args.state in {"implementation-ready", "awaiting-hardware", "passed"}:
        raise SDLCError(f"{args.state} is evidence-gated and cannot be set with stage")
    transition(ctx, args.id, args.state, args.message or f"Entered {args.state}")


def cmd_checkpoint(ctx: Context, args: argparse.Namespace) -> None:
    with ctx.lock("registry"):
        ensure_ledger(ctx)
        sync_ledger(ctx)
        state = load_state(ctx, args.id)
        commit_ledger(ctx, state["id"], args.message)


SECTION_HEADINGS = {
    "requirements-analysis": "Requirements analysis",
    "image-analysis": "Image analysis",
    "planner-questions": "Planner questions and answers",
    "solution-plan": "Solution plan — DRAFT",
    "approval": "Approval",
    "implementation": "Implementation",
    "validation": "Validation",
    "hardware-follow-up": "Hardware follow-up",
}


def cmd_section(ctx: Context, args: argparse.Namespace) -> None:
    content = Path(args.file).read_text(encoding="utf-8").strip() if args.file else sys.stdin.read().strip()
    if not content:
        raise SDLCError("section content is empty")
    heading = SECTION_HEADINGS[args.name]
    with ctx.lock("registry"):
        ensure_ledger(ctx)
        sync_ledger(ctx)
        state = load_state(ctx, args.id)
        path = doc_path(ctx, state["id"])
        text = path.read_text(encoding="utf-8")
        round_marker = f"## Round {state['current_round']}"
        start_round = text.rfind(round_marker)
        if start_round < 0:
            raise SDLCError(f"current round section is missing: {round_marker}")
        if args.name == "solution-plan":
            revision = state.get("plan", {}).get("revision", 0) + 1
            digest = hashlib.sha256(content.encode()).hexdigest()
            state["plan"] = {"revision": revision, "sha256": digest, "status": "draft"}
            heading = f"Solution plan — DRAFT revision {revision}"
        marker = f"### {heading}"
        start = text.find(marker, start_round)
        if args.name == "solution-plan" and start < 0 and state["plan"]["revision"] == 1:
            old_marker = "### Solution plan — DRAFT"
            start = text.find(old_marker, start_round)
            if start >= 0:
                text = text[:start] + marker + text[start + len(old_marker):]
        if start < 0:
            insert_at = text.find("\n### Event log", start_round)
            if insert_at < 0:
                insert_at = len(text)
            text = text[:insert_at] + f"\n### {heading}\n\n{content}\n" + text[insert_at:]
        else:
            body_start = start + len(marker)
            next_heading = re.search(r"\n(?:###|##) ", text[body_start:])
            body_end = body_start + next_heading.start() if next_heading else len(text)
            text = text[:body_start] + f"\n\n{content}\n" + text[body_end:]
        path.write_text(text, encoding="utf-8")
        save_state(ctx, state, f"Updated round {state['current_round']} {args.name} section")
        commit_ledger(ctx, state["id"], f"Updated {state['id']} {args.name}")


def cmd_approve(ctx: Context, args: argparse.Namespace) -> None:
    with ctx.lock("registry"):
        ensure_ledger(ctx)
        sync_ledger(ctx)
        state = load_state(ctx, args.id)
        if state["state"] not in {"awaiting-approval", "draft-ready"}:
            raise SDLCError(f"plan cannot be approved from state {state['state']}")
        if args.auto and not args.reason:
            raise SDLCError("automatic approval requires a recorded triviality reason")
        plan = state.get("plan")
        if not plan or not plan.get("sha256"):
            raise SDLCError("a persisted DRAFT plan revision is required before approval")
        state["approval"] = {"status": "auto-approved" if args.auto else "approved",
                             "time": now(), "reason": args.reason or "Developer approved plan",
                             "plan_revision": plan["revision"], "plan_sha256": plan["sha256"]}
        state["state"] = "auto-approved" if args.auto else "approved"
        save_state(ctx, state, state["approval"]["reason"])
        commit_ledger(ctx, state["id"], f"Approved {state['id']} plan")


def cmd_follow_up(ctx: Context, args: argparse.Namespace) -> None:
    with ctx.lock("registry"):
        ensure_ledger(ctx)
        sync_ledger(ctx)
        state = load_state(ctx, args.id)
        if state["state"] != "awaiting-hardware":
            raise SDLCError(f"hardware feedback requires awaiting-hardware, got {state['state']}")
        current = state["rounds"][state["current_round"] - 1]
        current["hardware_feedback"] = args.notes
        path = doc_path(ctx, state["id"])
        text = path.read_text(encoding="utf-8")
        marker = "### Hardware follow-up"
        start_round = text.rfind(f"## Round {state['current_round']}")
        start = text.find(marker, start_round)
        if start >= 0:
            body = start + len(marker)
            match = re.search(r"\n(?:###|##) ", text[body:])
            end = body + match.start() if match else len(text)
            text = text[:body] + f"\n\nResult: {args.result}\n\n{args.notes}\n" + text[end:]
            path.write_text(text, encoding="utf-8")
        if args.result == "pass":
            current["status"] = "passed"
            state["state"] = "passed"
            message = "Developer confirmed successful real-hardware validation"
        else:
            current["status"] = "failed"
            state["state"] = "requirements-analysis"
            state["current_round"] += 1
            state["approval"] = {"status": "none"}
            state["rounds"].append({"number": state["current_round"], "status": "active",
                                    "customer_requirements": "Bug-fix follow-up",
                                    "additional_instructions": args.notes, "events": []})
            with doc_path(ctx, state["id"]).open("a", encoding="utf-8") as handle:
                handle.write(f"\n## Round {state['current_round']}\n\n### Customer requirements\n\nBug-fix follow-up.\n"
                             f"\n### Developer instructions\n\n{args.notes}\n\n### Requirements analysis\n\nPending.\n"
                             "\n### Image analysis\n\nPending.\n\n### Planner questions and answers\n\nPending.\n"
                             "\n### Solution plan — DRAFT\n\nPending.\n\n### Approval\n\nPending.\n"
                             "\n### Implementation\n\nPending. Every realization must be a reversible Debian package.\n"
                             "\n### Validation\n\nPending.\n\n### Hardware follow-up\n\nPending.\n\n### Event log\n")
            message = f"Opened round {state['current_round']} from hardware failure feedback"
        save_state(ctx, state, message)
        commit_ledger(ctx, state["id"], f"Recorded {state['id']} hardware {args.result}")


def cmd_abandon(ctx: Context, args: argparse.Namespace) -> None:
    transition(ctx, args.id, "abandoned", args.reason)


def cmd_models(ctx: Context, _args: argparse.Namespace) -> None:
    roles = ["COORDINATOR", "REQUIREMENTS", "IMAGE_ANALYSIS", "PLANNER",
             "IMPLEMENTATION", "VALIDATION", "FOLLOW_UP"]
    for role in roles:
        print(f"{role.lower()}\t{ctx.conf.get(f'SDLC_{role}_MODEL', '')}\t"
              f"{ctx.conf.get(f'SDLC_{role}_EFFORT', '')}")


def cmd_resume(ctx: Context, args: argparse.Namespace) -> None:
    ensure_ledger(ctx)
    state = load_state(ctx, args.id)
    actions = {
        "requirements-analysis": ("agent", "sdlc_requirements", "analyze the current round requirements"),
        "image-analysis": ("agent", "sdlc_image_analysis", "inspect relevant image contents read-only"),
        "planner-questions": ("agent", "sdlc_planner", "collect all load-bearing developer answers"),
        "drafting-plan": ("agent", "sdlc_planner", "write and checkpoint the DRAFT plan"),
        "draft-ready": ("tool", "trivial-policy", "classify whether approval may be waived"),
        "awaiting-approval": ("human", "approval", "display the committed DRAFT for approval or amendment"),
        "approved": ("tool", "implement", "begin implementation automatically"),
        "auto-approved": ("tool", "implement", "begin implementation automatically"),
        "implementing": ("agent", "sdlc_implementation", "implement the approved plan as a DEB"),
        "implementation-ready": ("tool", "validate", "begin independent validation automatically"),
        "validating": ("agent", "sdlc_validation", "validate requirements, plan, DEB, and restoration"),
        "awaiting-hardware": ("human", "hardware-follow-up", "run the package on real hardware"),
        "recovery-required": ("human", "recovery", "resolve the recorded safety failure"),
        "passed": ("done", "passed", "requirement completed"),
        "abandoned": ("done", "abandoned", "requirement abandoned"),
    }
    kind, action, detail = actions[state["state"]]
    result = {"id": state["id"], "round": state["current_round"], "state": state["state"],
              "kind": kind, "action": action, "detail": detail}
    print(json.dumps(result, indent=2) if args.json else
          f"{result['kind']}: {result['action']} - {result['detail']}")


def cmd_trivial_policy(ctx: Context, args: argparse.Namespace) -> None:
    ensure_ledger(ctx)
    state = load_state(ctx, args.id)
    if state["state"] != "draft-ready":
        raise SDLCError(f"trivial policy requires draft-ready, got {state['state']}")
    risks = [args.boot, args.service, args.storage, args.security, args.overlap,
             args.custom_maintainer_scripts]
    eligible = args.files <= 2 and not any(risks) and args.tests
    reason = ("Trivial policy passed: at most two payload files, tests defined, and no boot, service, "
              "storage, security, overlap, or custom-maintainer-script risk") if eligible else \
             "Trivial policy failed; developer approval is required"
    if eligible:
        cmd_approve(ctx, argparse.Namespace(id=state["id"], auto=True, reason=reason))
    else:
        transition(ctx, state["id"], "awaiting-approval", reason)
    print("auto-approved" if eligible else "awaiting-approval")


def cmd_implement(ctx: Context, args: argparse.Namespace) -> None:
    ensure_ledger(ctx)
    state = load_state(ctx, args.id)
    if state["state"] not in {"approved", "auto-approved"}:
        raise SDLCError(f"implementation requires an approved plan, got {state['state']}")
    plan = state.get("plan", {})
    approval = state.get("approval", {})
    if (approval.get("plan_revision"), approval.get("plan_sha256")) != (plan.get("revision"), plan.get("sha256")):
        raise SDLCError("the current DRAFT differs from the approved plan")
    cmd_worktree(ctx, argparse.Namespace(id=state["id"], base=args.base))
    transition(ctx, state["id"], "implementing", "Implementation started from the approved plan")


def cmd_validate(ctx: Context, args: argparse.Namespace) -> None:
    ensure_ledger(ctx)
    state = load_state(ctx, args.id)
    if state["state"] != "implementation-ready":
        raise SDLCError(f"validation requires implementation-ready, got {state['state']}")
    transition(ctx, state["id"], "validating", "Independent validation started")


def cmd_validation_result(ctx: Context, args: argparse.Namespace) -> None:
    report = Path(args.report_file).read_text(encoding="utf-8").strip()
    if not report:
        raise SDLCError("validation report is empty")
    with ctx.lock("registry"):
        ensure_ledger(ctx)
        sync_ledger(ctx)
        state = load_state(ctx, args.id)
        if state["state"] != "validating":
            raise SDLCError(f"validation result requires validating, got {state['state']}")
        implementation = state.get("implementation", {})
        commit = implementation.get("commit")
        deb = Path(implementation.get("deb", ""))
        if not commit or not deb.is_file() or file_sha256(deb) != implementation.get("deb_sha256"):
            raise SDLCError("recorded implementation commit and unchanged DEB artifact are required")
        state["validation"] = {"status": args.result, "time": now(),
                               "implementation_commit": commit,
                               "deb_sha256": implementation["deb_sha256"]}
        state["state"] = "validating" if args.result == "pass" else "implementing"
        path = doc_path(ctx, state["id"])
        text = path.read_text(encoding="utf-8")
        marker = "### Validation"
        start = text.rfind(marker)
        body = start + len(marker)
        match = re.search(r"\n(?:###|##) ", text[body:])
        end = body + match.start() if match else len(text)
        text = text[:body] + f"\n\nResult: {args.result}\n\n{report}\n" + text[end:]
        path.write_text(text, encoding="utf-8")
        save_state(ctx, state, f"Independent validation {args.result}")
        commit_ledger(ctx, state["id"], f"Recorded {state['id']} validation {args.result}")


def cmd_worktree(ctx: Context, args: argparse.Namespace) -> None:
    with ctx.lock("registry"):
        ensure_ledger(ctx)
        sync_ledger(ctx)
        state = load_state(ctx, args.id)
        req_id = state["id"]
        path = ctx.worktrees / req_id
        branch = f"sdlc/{req_id.lower()}"
        if not (path / ".git").exists():
            if git(ctx.root, "show-ref", "--verify", "--quiet", f"refs/heads/{branch}", check=False).returncode == 0:
                git(ctx.root, "worktree", "add", str(path), branch)
            else:
                git(ctx.root, "worktree", "add", "-b", branch, str(path), args.base or "HEAD")
        values = {"branch": branch, "worktree": str(path),
                  "worktree_head": git(path, "rev-parse", "HEAD").stdout.strip()}
        if "base_commit" not in state["implementation"]:
            values["base_commit"] = values["worktree_head"]
        state["implementation"].update(values)
        save_state(ctx, state, f"Prepared implementation worktree {branch}")
        commit_ledger(ctx, req_id, f"Recorded {req_id} implementation worktree")
        print(path)


def cmd_implementation_commit(ctx: Context, args: argparse.Namespace) -> None:
    with ctx.lock("registry"):
        ensure_ledger(ctx)
        sync_ledger(ctx)
        state = load_state(ctx, args.id)
        if state["state"] != "implementing":
            raise SDLCError(f"implementation cannot be committed from {state['state']}")
        worktree = Path(state.get("implementation", {}).get("worktree", ""))
        if not (worktree / ".git").exists():
            raise SDLCError("requirement implementation worktree is missing")
        git(worktree, "add", "-A")
        if git(worktree, "diff", "--cached", "--quiet", check=False).returncode != 0:
            git(worktree, "commit", "-m", args.message)
        commit = git(worktree, "rev-parse", "HEAD").stdout.strip()
        deb = Path(args.deb).resolve()
        if not deb.is_file() or not deb.is_relative_to(worktree.resolve()):
            raise SDLCError("--deb must identify a built package inside the implementation worktree")
        state["implementation"].update({"commit": commit, "deb": str(deb),
                                         "deb_sha256": file_sha256(deb)})
        state["state"] = "implementation-ready"
        save_state(ctx, state, f"Recorded implementation commit {commit}")
        commit_ledger(ctx, state["id"], f"Recorded {state['id']} implementation commit")
        print(commit)


def cmd_merge(ctx: Context, args: argparse.Namespace) -> None:
    with ctx.lock("registry"):
        ensure_ledger(ctx)
        sync_ledger(ctx)
        state = load_state(ctx, args.id)
        if state["state"] != "validating" or state.get("validation", {}).get("status") != "passed":
            raise SDLCError(f"merge requires validated work, got {state['state']}")
        branch = state.get("implementation", {}).get("branch")
        commit = state.get("implementation", {}).get("commit")
        if not branch or not commit:
            raise SDLCError("implementation branch and commit must be recorded before merge")
        branch_head = git(ctx.root, "rev-parse", branch).stdout.strip()
        if branch_head != commit or state["validation"].get("implementation_commit") != commit:
            raise SDLCError("implementation branch moved after the validated commit")
        target = Path(args.target).resolve() if args.target else ctx.root
        if git(target, "status", "--porcelain").stdout.strip():
            raise SDLCError(f"target worktree is not clean: {target}")
        result = git(target, "merge", "--no-ff", commit, "-m", f"Merged {state['id']} implementation", check=False)
        if result.returncode != 0:
            git(target, "merge", "--abort", check=False)
            raise SDLCError(f"implementation merge needs developer conflict resolution: {result.stderr.strip()}")
        merge_commit = git(target, "rev-parse", "HEAD").stdout.strip()
        state["implementation"]["merge_commit"] = merge_commit
        state["state"] = "awaiting-hardware"
        save_state(ctx, state, f"Merged implementation as {merge_commit}")
        commit_ledger(ctx, state["id"], f"Recorded {state['id']} merge commit")
        print(merge_commit)


def fingerprint_tree(root: Path, excludes: list[str]) -> dict[str, dict]:
    result: dict[str, dict] = {}
    normalized = [x.rstrip("/") for x in excludes if x]
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
        base_path = Path(base)
        rel_base = "/" + str(base_path.relative_to(root)) if base_path != root else ""
        dirs[:] = [d for d in dirs if not any((rel_base + "/" + d == x or
                                                (rel_base + "/" + d).startswith(x + "/"))
                                               for x in normalized)]
        if base_path != root:
            st = base_path.lstat()
            result[rel_base] = {"type": "directory", "mode": st.st_mode,
                                "uid": st.st_uid, "gid": st.st_gid}
        for name in sorted(files):
            path = base_path / name
            rel = "/" + str(path.relative_to(root))
            if any(rel == x or rel.startswith(x + "/") for x in normalized):
                continue
            st = path.lstat()
            entry = {"type": "symlink" if path.is_symlink() else "file", "mode": st.st_mode,
                     "uid": st.st_uid, "gid": st.st_gid, "size": st.st_size}
            if path.is_symlink():
                entry["link"] = os.readlink(path)
            elif path.is_file():
                digest = hashlib.sha256()
                with path.open("rb") as handle:
                    for block in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(block)
                entry["sha256"] = digest.hexdigest()
            result[rel] = entry
    return result


def package_name(deb: Path) -> str:
    result = run(["dpkg-deb", "-f", str(deb), "Package"])
    value = result.stdout.strip()
    if not value:
        raise SDLCError(f"cannot determine package name: {deb}")
    return value


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cmd_verify_package(ctx: Context, args: argparse.Namespace) -> None:
    root = Path(args.root).resolve()
    deb = Path(args.deb).resolve()
    if not root.is_dir() or not deb.is_file():
        raise SDLCError("--root must be a mounted directory and --deb must be a file")
    identity = hashlib.sha256(str(root).encode()).hexdigest()[:20]
    quarantine = ctx.lock_root / "quarantine" / f"image-{identity}.json"
    dirty = ctx.lock_root / "quarantine" / "image-dirty.json"
    if quarantine.exists() and not args.recover:
        raise SDLCError(f"image is quarantined after a failed cleanup: {quarantine}")
    excludes = [x for x in ctx.conf.get("SDLC_VERIFY_EXCLUDES", "").split(",") if x]
    name = package_name(deb)
    journal = {"run": str(uuid.uuid4()), "host": socket.gethostname(), "root": str(root),
               "deb": str(deb), "package": name, "started": now(), "phase": "waiting-lock"}
    journal_path = ctx.runtime / f"verify-{journal['run']}.json"
    atomic_json(journal_path, journal)
    lock_context = contextlib.nullcontext() if os.environ.get("SDLC_IMAGE_LOCK_HELD") == "1" else ctx.lock("image")
    with lock_context:
        before = fingerprint_tree(root, excludes)
        install_attempted = False
        primary_error: Exception | None = None
        cleanup_error: Exception | None = None
        try:
            journal["phase"] = "installing"; atomic_json(journal_path, journal)
            install_attempted = True
            run(["dpkg", f"--root={root}", f"--admindir={root / 'var/lib/dpkg'}", "-i", str(deb)], capture=False)
            journal["phase"] = "testing"; atomic_json(journal_path, journal)
            if args.test_command:
                run(["chroot", str(root), "/bin/sh", "-c", args.test_command], capture=False)
        except Exception as exc:  # noqa: BLE001 - cleanup and restoration must still run
            primary_error = exc
        finally:
            journal["phase"] = "uninstalling"; atomic_json(journal_path, journal)
            if install_attempted:
                removed = run(["dpkg", f"--root={root}", f"--admindir={root / 'var/lib/dpkg'}", "-r", name],
                              check=False, capture=False)
                if removed.returncode:
                    cleanup_error = SDLCError(f"dpkg removal failed with exit code {removed.returncode}")
        journal["phase"] = "verifying-clean"; atomic_json(journal_path, journal)
        after = fingerprint_tree(root, excludes)
        if before != after or cleanup_error is not None:
            changed = sorted(set(before) ^ set(after) |
                             {p for p in set(before) & set(after) if before[p] != after[p]})
            journal.update({"phase": "quarantined", "finished": now(), "changed_paths": changed[:500]})
            atomic_json(journal_path, journal)
            atomic_json(quarantine, journal)
            atomic_json(dirty, journal)
            raise SDLCError(f"package removal did not restore the image; quarantined ({len(changed)} paths differ)")
        quarantine.unlink(missing_ok=True)
        if args.recover:
            dirty.unlink(missing_ok=True)
        journal.update({"phase": "clean", "finished": now()})
        atomic_json(journal_path, journal)
        if primary_error is not None:
            raise SDLCError(f"package test failed after clean restoration: {primary_error}")
    print(f"verified reversible: {name}")


def cmd_test_package(ctx: Context, args: argparse.Namespace) -> None:
    image = Path(args.image).resolve()
    deb = Path(args.deb).resolve()
    if not image.is_file() or not deb.is_file():
        raise SDLCError("--image and --deb must name existing files")
    identity = hashlib.sha256(str(image).encode()).hexdigest()[:20]
    quarantine = ctx.lock_root / "quarantine" / f"image-{identity}.json"
    dirty = ctx.lock_root / "quarantine" / "image-dirty.json"
    if quarantine.exists():
        raise SDLCError(f"image is quarantined: {quarantine}")
    active_state = ctx.root / ".lets/scr/image/mount.state"
    with ctx.lock("image"):
        if active_state.exists():
            raise SDLCError("an image is already mounted; unmount it before SDLC package testing")
        original_hash = file_sha256(image)
        run_id = str(uuid.uuid4())
        scratch = ctx.runtime / "tests" / run_id
        scratch.mkdir(parents=True, exist_ok=False)
        image_copy = scratch / image.name
        journal = {"run": run_id, "image": str(image), "source_sha256": original_hash,
                   "deb": str(deb), "phase": "copying", "started": now()}
        atomic_json(scratch / "journal.json", journal)
        mounted = False
        functional_error: Exception | None = None
        cleanup_error: Exception | None = None
        try:
            run(["cp", "--reflink=auto", "--sparse=always", "--", str(image), str(image_copy)], capture=False)
            journal["phase"] = "mounting-copy"; atomic_json(scratch / "journal.json", journal)
            run([str(ctx.root / "bin/lets"), "scr", "image", "mount", "--image", str(image_copy), "--rw"],
                cwd=ctx.root, capture=False)
            mounted = True
            env = os.environ.copy()
            env["SDLC_IMAGE_LOCK_HELD"] = "1"
            command = [str(ctx.root / "bin/lets"), "sdlc", "verify-package", args.id,
                       "--root", str(ctx.root / "image"), "--deb", str(deb)]
            if args.test_command:
                command.extend(["--test-command", args.test_command])
            journal["phase"] = "install-test-remove"; atomic_json(scratch / "journal.json", journal)
            completed = subprocess.run(command, cwd=ctx.root, env=env, check=False)
            if completed.returncode:
                raise SDLCError(f"package verification failed with exit code {completed.returncode}")
        except Exception as exc:  # noqa: BLE001 - cleanup and quarantine must still run
            functional_error = exc
        finally:
            if mounted:
                result = run([str(ctx.root / "bin/lets"), "scr", "image", "umount"], cwd=ctx.root,
                             check=False, capture=False)
                if result.returncode:
                    cleanup_error = SDLCError("failed to unmount disposable test image")
        if file_sha256(image) != original_hash:
            cleanup_error = SDLCError("source image changed during disposable package test")
        if cleanup_error is not None:
            journal.update({"phase": "quarantined", "finished": now(), "error": str(cleanup_error)})
            atomic_json(scratch / "journal.json", journal)
            atomic_json(quarantine, journal)
            atomic_json(dirty, journal)
            raise SDLCError(f"image package test cleanup failed and was quarantined: {cleanup_error}")
        if functional_error is not None:
            journal.update({"phase": "clean-after-test-failure", "finished": now(),
                            "error": str(functional_error)})
            atomic_json(scratch / "journal.json", journal)
            raise SDLCError(f"package test failed; disposable image was cleaned: {functional_error}")
        journal.update({"phase": "clean", "finished": now()})
        atomic_json(scratch / "journal.json", journal)
        shutil.rmtree(scratch)
    print("package passed disposable-image restoration test; source image unchanged")


def cmd_lock_run(ctx: Context, args: argparse.Namespace) -> None:
    identity = hashlib.sha256(str(Path(args.image).resolve()).encode()).hexdigest()[:20]
    quarantine = ctx.runtime / "quarantine" / f"image-{identity}.json"
    if quarantine.exists():
        raise SDLCError(f"image is quarantined: {quarantine}")
    if not args.command:
        raise SDLCError("missing command after --")
    with ctx.lock("image"):
        result = subprocess.run(args.command, check=False)
        if result.returncode:
            raise SDLCError(f"locked command failed with exit code {result.returncode}")


def validate_managed_path(value: str) -> str:
    if not value.startswith("/") or value == "/" or ".." in Path(value).parts:
        raise SDLCError(f"unsafe managed image path: {value}")
    return value.rstrip("/")


def cmd_package_init(ctx: Context, args: argparse.Namespace) -> None:
    ensure_ledger(ctx)
    state = load_state(ctx, args.id)
    if state["state"] not in {"approved", "auto-approved", "implementing"}:
        raise SDLCError(f"package scaffolding requires an approved plan, got {state['state']}")
    operations: list[tuple[str, str, str]] = []
    affected: set[str] = set()
    for raw in args.operation:
        fields = raw.split(":", 2)
        kind = fields[0]
        if kind not in {"add", "replace", "delete", "move"}:
            raise SDLCError(f"unsupported package operation: {kind}")
        if (kind == "move" and len(fields) != 3) or (kind != "move" and len(fields) != 2):
            raise SDLCError(f"operation must be KIND:/path or move:/source:/dest: {raw}")
        source = validate_managed_path(fields[1])
        dest = validate_managed_path(fields[2]) if kind == "move" else ""
        affected.add(source)
        if dest:
            affected.add(dest)
        operations.append((kind, source, dest))
    if not operations:
        raise SDLCError("at least one --operation is required")
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


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lets sdlc")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init").set_defaults(func=cmd_init)
    n = sub.add_parser("new"); n.add_argument("--description", required=True); n.add_argument("--title"); n.add_argument("--instructions"); n.set_defaults(func=cmd_new)
    sub.add_parser("list").set_defaults(func=cmd_list)
    for name, func in (("show", cmd_show), ("path", cmd_path)):
        q = sub.add_parser(name); q.add_argument("id"); q.set_defaults(func=func)
    s = sub.add_parser("status"); s.add_argument("id"); s.add_argument("--json", action="store_true"); s.set_defaults(func=cmd_status)
    st = sub.add_parser("stage"); st.add_argument("id"); st.add_argument("state", choices=sorted(STATES)); st.add_argument("--message"); st.set_defaults(func=cmd_stage)
    cp = sub.add_parser("checkpoint"); cp.add_argument("id"); cp.add_argument("--message", required=True); cp.set_defaults(func=cmd_checkpoint)
    sc = sub.add_parser("section"); sc.add_argument("id"); sc.add_argument("--name", choices=sorted(SECTION_HEADINGS), required=True); sc.add_argument("--file"); sc.set_defaults(func=cmd_section)
    ap = sub.add_parser("approve"); ap.add_argument("id"); ap.add_argument("--auto", action="store_true"); ap.add_argument("--reason"); ap.set_defaults(func=cmd_approve)
    fu = sub.add_parser("follow-up"); fu.add_argument("id"); fu.add_argument("--result", choices=["pass", "fail"], required=True); fu.add_argument("--notes", required=True); fu.set_defaults(func=cmd_follow_up)
    ab = sub.add_parser("abandon"); ab.add_argument("id"); ab.add_argument("--reason", required=True); ab.set_defaults(func=cmd_abandon)
    sub.add_parser("models").set_defaults(func=cmd_models)
    rs = sub.add_parser("resume"); rs.add_argument("id"); rs.add_argument("--json", action="store_true"); rs.set_defaults(func=cmd_resume)
    tp = sub.add_parser("trivial-policy"); tp.add_argument("id"); tp.add_argument("--files", type=int, required=True)
    for flag in ("boot", "service", "storage", "security", "overlap", "custom-maintainer-scripts"):
        tp.add_argument(f"--{flag}", action="store_true")
    tp.add_argument("--tests", action="store_true"); tp.set_defaults(func=cmd_trivial_policy)
    im = sub.add_parser("implement"); im.add_argument("id"); im.add_argument("--base"); im.set_defaults(func=cmd_implement)
    va = sub.add_parser("validate"); va.add_argument("id"); va.set_defaults(func=cmd_validate)
    wt = sub.add_parser("worktree"); wt.add_argument("id"); wt.add_argument("--base"); wt.set_defaults(func=cmd_worktree)
    ic = sub.add_parser("implementation-commit"); ic.add_argument("id"); ic.add_argument("--message", required=True); ic.add_argument("--deb", required=True); ic.set_defaults(func=cmd_implementation_commit)
    vr = sub.add_parser("validation-result"); vr.add_argument("id"); vr.add_argument("--result", choices=["pass", "fail"], required=True); vr.add_argument("--report-file", required=True); vr.set_defaults(func=cmd_validation_result)
    mg = sub.add_parser("merge"); mg.add_argument("id"); mg.add_argument("--target"); mg.set_defaults(func=cmd_merge)
    vp = sub.add_parser("verify-package"); vp.add_argument("id"); vp.add_argument("--root", required=True); vp.add_argument("--deb", required=True); vp.add_argument("--test-command"); vp.add_argument("--recover", action="store_true"); vp.set_defaults(func=cmd_verify_package)
    it = sub.add_parser("test-package"); it.add_argument("id"); it.add_argument("--image", required=True); it.add_argument("--deb", required=True); it.add_argument("--test-command"); it.set_defaults(func=cmd_test_package)
    lr = sub.add_parser("lock-run"); lr.add_argument("--image", required=True); lr.add_argument("command", nargs=argparse.REMAINDER); lr.set_defaults(func=cmd_lock_run)
    pi = sub.add_parser("package-init"); pi.add_argument("id"); pi.add_argument("--package"); pi.add_argument("--output")
    pi.add_argument("--operation", action="append", default=[]); pi.add_argument("--force", action="store_true"); pi.set_defaults(func=cmd_package_init)
    return p


def main() -> int:
    try:
        args = parser().parse_args()
        if getattr(args, "recover", False):
            os.environ["SDLC_RECOVERY"] = "1"
        ctx = Context(repo_root())
        args.func(ctx, args)
        return 0
    except (SDLCError, subprocess.CalledProcessError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            print(exc.stderr.strip(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
