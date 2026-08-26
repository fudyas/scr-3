---
name: sdlc-implement
description: Implement a planned PRD feature or ad-hoc item — orchestrate SWE, Validator, and Integrator subagents across parallel task blocks, assemble the blocks into a feature integration worktree, and run QA inline in the foreground there (so its stack rebuild + test run streams live), then stop at TESTING for /sdlc-approve (which promotes it to the main tree and lands it DONE). Tracks task status via `sdlc tasks task status set` (a ledger record + PROGRESS/TSK mirrors) and item status via `sdlc tasks status set` (a ledger write). Do NOT auto-invoke; only run when explicitly called with /sdlc-implement.
argument-hint: "FTR-XXXX or BLG-NNNN (id or full name)"
---

# Implement (`/sdlc-implement`)

> **Ledger model.** All SDLC bookkeeping — every item / chain / task record and every item document (`BRIEF.md`, `PROGRESS.md`, `TSK-*.md`) — now lives on the shared **`sdlc`** git branch, not the working tree (`docs/devel/` holds only a tombstone README). Read an item's plan at `$(./bin/lets scr sdlc tasks path <ID>)`. Move a **task** through its lifecycle with `./bin/lets scr sdlc tasks task status set <ID> <TSK-NNNN> <STATUS>` (writes the ledger record and regenerates the `PROGRESS.md` + `TSK` mirrors) and the **item** with `sdlc tasks status set <ID> <STATUS>` — both ledger writes, no folder move. Any working-tree folder path mentioned below is historical. See `docs/SDLC.md` → *Ledger tracker*.

Implement stage of the SDLC pipeline. You are the **orchestrator** (this runs in the main
conversation). You drive a planned item — a PRD feature (`FTR-XXXX`) or an ad-hoc work item (`BLG-NNNN`, or a
legacy `ADHOC-NNNN`) —
through block implementation and validation, **assemble** the blocks into a feature integration worktree, and
run **QA yourself, inline in this foreground conversation** (not a spawned subagent) on that worktree — so its
stack rebuild and test run stream live for the user to watch — landing the item at `TESTING` for the user to
approve. You never merge into the main tree or mark the item `DONE` — that is `/sdlc-approve`. You delegate
every code change to subagents and keep the task records + the item status in lockstep through the
`sdlc tasks … set` commands; you never write feature code yourself.

**The [SDLC guide](../../../docs/SDLC.md)** is the source of truth for ids, task kinds, status
lifecycles, the gate, and the caveman conventions this skill enforces.

## Arguments

`$ARGUMENTS` — the item to implement: a `FTR-XXXX` / `FTR-XXXX-NAME` feature or a `BLG-NNNN` / full ad-hoc
id (or a legacy `ADHOC-NNNN`). Required.

## Invariants

1. **Concurrent features, one run per item.** Several items may be `IN PROGRESS` at once — each `/sdlc-implement`
   run drives its own item in its own block + integration worktrees (namespaced by `<ID>`), so features
   implement in parallel. Refuse only if **this** item is already `IN PROGRESS` (a second run racing the same
   item). The single shared stack is no longer protected by an item-count rule — it is protected by the stack
   lock (invariant 3).
2. **Status is a ledger write.** Every **task** transition is
   `./bin/lets scr sdlc tasks task status set <ID> <TSK-NNNN> <STATUS>` — it writes the task's `tasks.jsonl`
   record and regenerates that item's `PROGRESS.md` roll-up (re-rolling the block status: `PENDING` →
   `IN PROGRESS` once any task leaves `TODO`, `COMPLETED` once all are `DONE`) and the `TSK-*.md` `Status` row
   as mirrors on the branch — never hand-edit those. Every **item** transition is
   `./bin/lets scr sdlc tasks status set <ID> <STATUS>` — a ledger write that flips the item's `status` field
   and appends a dated history entry (**no folder move, nothing committed to the working tree**). The ledger's
   compare-and-swap plus a per-host `flock` serialize concurrent runs, so writes never clobber. Always go
   through the tooling; never hand-edit the records or the mirrors.
3. **Stack ownership = you, the orchestrator, hold the lock around your own inline QA window.** No pipeline
   stage touches the Docker stack until the **QA gate**, which you run **inline in this foreground conversation**
   (not a spawned subagent) so its dn/rebuild/up and test output stream live for the user. Because the stack is
   a hard singleton (fixed ports + one shared `var/`) and separate runs cannot see each other, QA serializes
   across features through a **cross-process stack lock** — a file lock in the main checkout's `.lets/sdlc/`
   (`.lets/sdlc/stack.lock`), resolved from the shared git common dir so every run contends on the one same
   lease wherever its worktree lives. **You** acquire it (`./bin/lets scr sdlc stack lock <ID>`, which
   **blocks until it takes the stack** — naming the holder each poll and re-contending atomically when it frees)
   before you bring the stack up, and release it (`./bin/lets scr sdlc stack unlock <ID>`) after you bring the
   stack down, pass or fail. The lease **never times out and never auto-reclaims**: a live holder paused on a
   user question keeps the stack for as long as the pause lasts, and your acquire simply waits it out, taking the
   stack only once it actually wins the lease (never on the assumption a release was its own). A holder a crash
   truly stranded is broken by hand (`stack unlock <holder> --force` / `stack lock <ID> --steal`). **Validators run stack-free** — unit + style/codegen
   only — so any number run **fully in parallel**, with no serialization. **Integrators** still serialize
   **within a feature** (they all merge into that feature's one `sdlc/<ID>/integration` branch): do not launch
   a second Integrator for this item until the running one returns; across features they are independent.
4. **Subagents pause through you.** A subagent cannot prompt the user; if a Validator or Integrator needs a
   decision, it returns the question in its result; relay it to the user and wait. QA is **not** a subagent —
   you run it inline (step 5), so you surface any QA decision to the user directly and you wait on the stack
   lock yourself: `stack lock` blocks in your own foreground bash (naming the holder each poll and re-contending
   atomically when it frees), so a busy stack just blocks that one call until it wins the lease.
5. **Caveman full mode (all three phases).** Every pipeline subagent (swe, validator, integrator,
   ulidator) runs in `/caveman full` at launch/handoff, while running, and on report: you author each handoff
   terse, the agent works terse, and it reports terse (its definition enforces the run + report). Keep every
   id, file path, code symbol, CLI command, and error string verbatim; code, edits, and commit messages stay
   normal.
6. **Shared-registry coordination runs from the main checkout.** Every registry/worktree command —
   `sdlc tasks … set` (status / priority / depends / tag) and `sdlc worktree add` — is run by **you**, the
   orchestrator, from the main tree; subagents work *inside* their worktrees and run only code / build / test
   there, never one of these. This is the rule that makes a tooling fix landed in the main tree take effect
   immediately for every in-flight feature: the registry tooling always executes the one canonical main-tree
   copy, never the frozen per-worktree copy a worktree checked out at branch time. **QA's stack commands are the
   exception you run from the worktree** — at the QA gate (step 5) you `cd` into the integration worktree and
   run `dc up/dn`, `test`, `logs`, and `sdlc stack lock/unlock/status` there, because the stack and its
   `var/`+`admin/` links live in that worktree (the lease still resolves to the main checkout's `.lets/sdlc/`
   from anywhere, so every run shares it, and the integration worktree is cut fresh at assembly time so its lock
   helper is current).
7. **Base branch — working branch, or the chain branch under `/sdlc-chain-run`.** This item's worktrees (the
   blocks and the item integration) are cut from a **base branch**. Run **standalone**, that base is the working
   branch (the default, as before). Driven by **`/sdlc-chain-run`**, the caller gives you the chain's integration
   branch `sdlc/<CHN>/integration` as the base — pass it as `--base sdlc/<CHN>/integration` to every
   `sdlc worktree add`, so the item builds **on** the chain (atop the chain's already-landed items), never on the
   bare main tree. Either way you still stop at `TESTING` and never touch the main tree. Which base is in force is
   the caller's to state; when none is given it is the working branch.

## Procedure

1. **Validate + open.**
   1.1. Resolve the item — `./bin/lets scr sdlc tasks info <ID>` reports its status. The item must be `TODO`
        (a planned feature or ad-hoc item). Refuse `BACKLOG` — an un-planned brief with no tasks yet; plan it
        first with `/sdlc-plan`. Refuse `DONE` and `OBSOLETE`. Refuse only if **this** item is already
        `IN PROGRESS` (a second run racing it); other items being `IN PROGRESS` is fine — features run in
        parallel and serialize only at the QA stack lock.
   1.2. **Dependency gate.** Run `./bin/lets scr sdlc tasks depends check <ID>`. If it reports
        `BLOCKED`, **stop** — the item depends on one or more features that are not yet `DONE`. Report the
        unmet dependencies it lists (each must be implemented first) and do not open the item. Only a
        `READY` verdict proceeds.
   1.3. Move the item to `IN PROGRESS`: `./bin/lets scr sdlc tasks status set <ID> "IN PROGRESS"` (a ledger
        write).
   1.4. Read the plan at `$(./bin/lets scr sdlc tasks path <ID>)/PROGRESS.md` — the blocks, tasks, `Depends
        on`, and current statuses. Resume cleanly: skip tasks already `DONE`; pick up
        `IN PROGRESS`/`TESTING`/`QA READY` where they left.

2. **S1 — implement blocks (parallel across blocks).** For each not-yet-complete block:
   2.1. Create its worktree once: `./bin/lets scr sdlc worktree add <ID> <BLK-NNNN>` (add
        `--base sdlc/<CHN>/integration` when this run is part of a `/sdlc-chain-run`, per invariant 7). This adds
        the worktree at `.claude/worktrees/<ID>/<BLK-NNNN>` on branch `sdlc/<ID>/<BLK-NNNN>` (off the base
        branch — the working branch standalone, the chain branch in a chain) **and** soft-links the gitignored
        `var/` (Qdrant index, PG cluster, Ollama model weights,
        FastEmbed caches, authoring state) and `admin/` (LLM provider keys) from the main checkout. Block
        validation is **stack-free**, so a block worktree never mounts these itself — the links are harmless
        there and matter at the **integration** worktree, whose QA stack mounts the real data. The tracked
        `src/data/*` mounts are git-checked-out in the worktree and deliberately left alone. The command is
        idempotent, so a clean resume re-runs it safely. All of the block's tasks are built here.
   2.2. Run the block's tasks in `Depends on` order. For each task:
        - Mark it `IN PROGRESS`: `./bin/lets scr sdlc tasks task status set <ID> <TSK-NNNN> "IN PROGRESS"`.
        - Launch the **swe** agent (one task per agent). Give it: the task file path (under
          `$(./bin/lets scr sdlc tasks path <ID>)`), the **block worktree path** to work in, and the
          documentation reference slice. It implements the task and writes unit tests; it does **not** touch the
          stack.
        - On successful return, mark the task `TESTING`: `sdlc tasks task status set <ID> <TSK-NNNN> TESTING`.
   2.3. Independent blocks may run concurrently — you may launch SWE agents for different blocks in parallel.

3. **S1 — validate each block (Validators run in parallel, stack-free).** When **all** tasks in a block are
   `TESTING`:
   3.1. Launch the **validator** agent for that block worktree — **no waiting**, as many in parallel as you
        have ready blocks (across this feature and others). It independently re-runs the block's stack-free
        gates only: the unit suite plus the style/codegen gates. It brings up **no** stack; real-stack system
        criteria are deferred to QA.
   3.2. **Pass** → mark every task in the block `QA READY` (`sdlc tasks task status set <ID> <TSK-NNNN> "QA READY"`).
   3.3. **Per-task fail** → mark that task `IN PROGRESS` (`sdlc tasks task status set`), re-launch **swe** with
        the Validator's findings to fix it (in the same block worktree), then re-validate the block.
   3.4. Relay any Validator question to the user before continuing.

4. **S1 — assemble each block into the integration worktree (Integrators serialized within this feature).**
   The blocks are gathered for QA in **one feature integration worktree**, not the main tree — nothing reaches
   the main tree until `/sdlc-approve`. They all merge into this feature's single `sdlc/<ID>/integration`
   branch, so run them one at a time within this run (other features' Integrators, on their own branches, are
   independent — no global serialization).
   4.1. Create the integration worktree once (before the first block merge):
        `./bin/lets scr sdlc worktree add <ID> integration` (add `--base sdlc/<CHN>/integration` under a
        `/sdlc-chain-run`, per invariant 7) — adds `.claude/worktrees/<ID>/integration` on branch
        `sdlc/<ID>/integration` (cut from the base branch — the working branch standalone, the chain branch in a
        chain) and links `var/` + `admin/` so QA's stack mounts the real data.
   4.2. After a block passes validation, launch the **integrator** agent (wait for any running Integrator to
        finish first): merge **source** `sdlc/<ID>/<BLK-NNNN>` into **target** `sdlc/<ID>/integration`,
        working in the integration worktree. It resolves conflicts and confirms the unit build.
   4.3. On a clean merge, remove the block worktree: `git worktree remove .claude/worktrees/<ID>/<BLK-NNNN>`.
   4.4. Relay any Integrator question (e.g. an unresolvable conflict) to the user before continuing.

5. **S3 — item QA on the integration worktree (you run it inline, in the foreground).** When **every** block is
   assembled into `sdlc/<ID>/integration` (all tasks `QA READY`):
   5.1. Move the item to `TESTING`: `./bin/lets scr sdlc tasks status set <ID> TESTING` (a ledger write).
   5.2. **Run QA yourself, inline in this foreground conversation — do not spawn a subagent.** Work in the
        integration worktree (`.claude/worktrees/<ID>/integration`); every command is your own foreground Bash
        call, so its rebuild and test output streams live for the user to track. Follow the QA procedure in
        [`.claude/agents/qa.md`](../../agents/qa.md):
        - **First, before anything else, acquire the stack lock through the LETS tool, run from the main
          checkout** — `./bin/lets scr sdlc stack lock <ID>` (blocks until it takes the singleton stack —
          naming the holder each poll and re-contending atomically when it frees). Run the lock from the **main checkout**, not the integration worktree, so
          its lease tooling is the live main-tree copy — a worktree carries only the pipeline tooling frozen at
          its branch cut-point, so locking from there could desync the cross-process serialization if the lock
          logic was improved in the main tree mid-flight. The lock is the **very first** QA action: do no
          `dc`/`test`/`logs` work until it returns success. Acquire and release the lease **only** through the
          LETS commands (`sdlc stack lock` / `unlock`) — never `mkdir`/`rm` the lease directory by hand.
        - **Guard the window so the lock always releases — on success, on any failing step, and on a user
          abort.** Open the stack-touching sequence (rebuild the touched services, `dc up`, the unit suite + each
          touched component's system suite + a feature-wide `test suite --system` regression pass) in **one** foreground
          bash invocation whose first line installs a release trap:
          ```bash
          # Resolve the main checkout so the lock release runs from the LIVE pipeline tooling,
          # not the worktree's frozen copy (dc/test stay in the worktree to build the branch).
          MAIN_ROOT="$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")"
          trap './bin/lets scr dc dn; (cd "$MAIN_ROOT" && ./bin/lets scr sdlc stack unlock <ID>)' EXIT INT TERM
          ```
          so the stack comes down and the lock is released on normal completion, on an error, and on SIGINT/SIGTERM
          from the user terminating the run. (Do **not** `set -e` — let every suite run so you can judge each task;
          the trap, not early-exit, owns cleanup. The lease never times out, so a hard kill no trap can catch
          leaves it stranded until a human clears it with `sdlc stack unlock <ID> --force`.)
        - Judge **each task** against its full DoD from the streamed results. The main tree stays untouched.
   5.3. **Any failure** → move the item back to `IN PROGRESS`
        (`./bin/lets scr sdlc tasks status set <ID> "IN PROGRESS"`), mark the affected task(s) `IN PROGRESS`
        (`sdlc tasks task status set`), and **return to step 2 (S1)** for them; already-`QA READY` tasks keep
        their status.
   5.4. If QA surfaces a question that needs a user decision, raise it to the user and wait before continuing.

6. **Hand off for approval.** On an all-pass QA, **stop**: leave the item at `TESTING` and its tasks at
   `QA READY` — do **not** mark anything `DONE` and do **not** touch the main tree. Report the blocks
   assembled, the QA result, and the integration worktree to review, then tell the user to inspect it and run
   **`/sdlc-approve <ID>`** to land it `DONE`. Standalone, approve promotes the item into the **main tree**;
   under a `/sdlc-chain-run`, approve instead lands the item into the **chain** integration branch
   `sdlc/<CHN>/integration` (the chain reaches the main tree only when it is wholly done — the chain run drives
   this, so you need not prompt for it).

## Notes

- **Never destroy the shared project database without user consent.** If the project runs a persistent
  datastore (e.g. a PostgreSQL cluster bind-mounted under `var/`), the QA window must preserve it by design
  (`dc dn` keeps the bind mount, `alembic upgrade` only goes forward). If any step — a task migration, a
  diagnosis, or a manual fix — would drop or delete that data (`down -v`, `docker volume rm`, `rm` of the data
  mount, `DROP SCHEMA/DATABASE`, `TRUNCATE`, `alembic downgrade`, or a re-baseline that drops a schema),
  **pause the pipeline and await user instructions**. A `PreToolUse` hook backstops the command-line forms by
  pausing them for consent; the schema-dropping-migration path is on you and the SWE to catch.
- Confirm `./bin/lets scr sdlc tasks list --verbose --include "IN PROGRESS"` reflects the live task
  statuses as you go.
- If the plan looks wrong mid-run (a missing task, a bad dependency), pause and recommend `/sdlc-plan` to
  re-plan rather than improvising the breakdown here.
- When another feature holds the stack, your inline `sdlc stack lock <ID>` blocks in the foreground — naming the
  holder each poll and re-contending atomically — until the holder releases, then takes it (it never times out,
  so a live holder paused on a user question rightly keeps the stack and your call simply waits). Check the
  holder any time from another session with `./bin/lets scr sdlc stack status` (run it from anywhere — the
  lease lives in the main checkout's `.lets/sdlc/stack.lock` and resolves the same from every worktree) — it
  names the holding item and how long it has held the stack. A crash the trap could not catch strands the lease;
  break it by hand with `./bin/lets scr sdlc stack unlock <holder-ID> --force` (or `stack lock <ID> --steal`)
  only after confirming no QA is actually running against the stack.
