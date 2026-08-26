---
name: sdlc-approve
description: Approve a QA-passed feature (or ad-hoc item) sitting at TESTING and promote it — launch the Integrator to merge the feature integration branch (sdlc/<ID>/integration) into the working branch (the main tree), then land every task and the item DONE. The human gate after /sdlc-implement's QA. Do NOT auto-invoke; only run when explicitly called with /sdlc-approve.
argument-hint: "FTR-XXXX or BLG-NNNN (id or full name)"
---

# Approve (`/sdlc-approve`)

> **Migration note (ledger tracker).** The item paths and folder moves below are the **un-migrated** folder model, still in force on the main tree. On a host that has run `sdlc migrate`, items live flat at `docs/devel/items/<ID>-NAME/` and `sdlc tasks status set` writes the shared ledger — no folder move, nothing committed for the status change. The `sdlc …` commands auto-detect the mode, so the steps below hold either way; a status transition simply stops touching git once migrated. See `docs/SDLC.md` → *Ledger tracker & migration*.

Approve stage of the SDLC pipeline. You are the **orchestrator** (this runs in the main conversation).
`/sdlc-implement` assembled the item's blocks into a feature integration worktree, ran **QA** there, and left
the item at `TESTING` — built and QA-passed, but not yet landed. `/sdlc-approve` is the **human gate**: once
the user has reviewed the QA result (and the integration worktree), it lands the item `DONE`. You never write
feature code; the only merge is the Integrator's.

**Land target — the main tree, or the chain branch under `/sdlc-chain-run`.** Run **standalone**, approve
promotes the item integration `sdlc/<ID>/integration` into the working branch (the main tree) under the
main-tree lock — the classic per-item promotion (step 2a). Driven by **`/sdlc-chain-run`**, the caller instead
directs you to land the item into the chain's integration branch `sdlc/<CHN>/integration` (step 2b): the chain
accumulates its items there and reaches the main tree only when the **whole chain** is done (the chain run's
final step, not this skill's). Landing into a chain takes **no** main-tree lock — that branch is single-writer
within one chain run — and merges via the Integrator's *land an item into its chain* role. Which target is in
force is the caller's to state; when none is given it is the main tree. Everything else (item → `DONE`, worktree
teardown) is identical.

**The [SDLC guide](../../../docs/SDLC.md)** is the source of truth for ids, statuses, the gate, and the
caveman conventions this skill enforces.

## Arguments

`$ARGUMENTS` — the item to approve: a `FTR-XXXX` / `FTR-XXXX-NAME` feature or a `BLG-NNNN` / full ad-hoc
id (or a legacy `ADHOC-NNNN`). Required.

## Caveman full mode

The Integrator runs in **`/caveman full`** at launch/handoff, while running, and on report (its definition
enforces the run + report); you author its handoff terse. Keep every id, file path, code symbol, CLI command,
and error string verbatim; code, edits, and commit messages stay normal.

## Procedure

1. **Resolve + validate.**
   1.1. Resolve `$ARGUMENTS` — `./bin/lets scr sdlc tasks info <ID>` (by `FTR-NNNN` / `BLG-NNNN` key, or a
        legacy `ADHOC-NNNN`) reports its status. If there is no record, **stop** — the item has not been
        implemented; there is nothing to approve.
   1.2. The item's status must be `TESTING` (QA-passed on the integration worktree, awaiting approval).
        **Refuse** any other status with a pointer to the right command: `TODO` → run `/sdlc-implement` first;
        `IN PROGRESS` → still implementing, let `/sdlc-implement` finish; `DONE` → already approved;
        `BACKLOG` / `OBSOLETE` → not in QA.
   1.3. Confirm the integration worktree and branch exist: `.claude/worktrees/<ID>/integration` on
        `sdlc/<ID>/integration`. If missing, **stop** — re-run `/sdlc-implement` to rebuild and re-QA; do not
        improvise a merge.
   1.4. Confirm every task is `QA READY` — read `$(./bin/lets scr sdlc tasks path <ID>)/PROGRESS.md`, or
        `./bin/lets scr sdlc tasks list --with-tasks`. If any is
        `IN PROGRESS` (a QA fail went back to the SWE), **stop** — `/sdlc-implement` is not finished.

2. **Land the item (Integrator).** Take the branch below for the land target in force.

   **2a. Standalone — promote into the main tree, serialized by the main-tree lock.** The promote merges into
   the working branch in the **main checkout** — one working tree, index, and HEAD shared by every concurrent
   approval — so it must take turns with any other promote at the same time.
   - **Acquire the main-tree promote lock first, through the LETS tool** —
     `./bin/lets scr sdlc maintree lock <ID>` (blocks until it takes the main tree — naming the holder each
     poll and re-contending atomically when it frees). This is the **very first** promote action: launch no
     Integrator until it returns holding the lock. Acquire and release the lease **only** through the LETS
     commands (`sdlc maintree lock` / `unlock`) — never `mkdir`/`rm` the lease directory by hand. The lease
     lives in the main checkout's `.lets/sdlc/maintree.lock`, resolved from the shared git common dir, so every
     session contends on the one same lock.
   - **Promote.** Launch the **integrator** agent (promote-into-main role): merge **source**
     `sdlc/<ID>/integration` into **target** the working branch (the main tree), in the main checkout, telling
     it this is a promote into the main tree so it runs the **cross-chain precedence check**. It resolves
     conflicts faithfully and confirms the unit build. Relay any unresolvable-conflict or precedence question to
     the user and wait — do not force a merge. **Keep the lock held while a half-finished merge sits on the main
     tree.**
   - **Release on every exit** — once the merge is committed and the main tree is clean, or the approve is
     abandoned with the merge aborted back to clean: `./bin/lets scr sdlc maintree unlock <ID>`. Release on
     success, on a stop, and on a user abort. The lease never times out, so a hard kill no release can catch
     leaves it stranded until a human clears it (`./bin/lets scr sdlc maintree status`;
     `./bin/lets scr sdlc maintree unlock <ID> --force`).

   **2b. Under `/sdlc-chain-run` — land into the chain branch, no lock.** Launch the **integrator** agent
   (land-an-item-into-its-chain role): merge **source** `sdlc/<ID>/integration` into **target**
   `sdlc/<CHN>/integration`, working in the **chain** integration worktree (`.claude/worktrees/<CHN>/integration`).
   Take **no** main-tree lock — the chain branch is single-writer within the one chain run — and skip the
   precedence check (that belongs to the chain → main promotion). It resolves conflicts faithfully and confirms
   the unit build; relay any unresolvable-conflict question to the user and wait. The main tree stays untouched;
   the item simply joins the chain.

3. **Land DONE.**
   3.1. On a clean, building merge, safely remove the item integration worktree:
        `./bin/lets scr sdlc worktree remove <ID> integration`.
   3.2. Mark every task `DONE` — `./bin/lets scr sdlc tasks task status set <ID> <TSK-NNNN> DONE` for each,
        which writes the record and re-rolls each block to `COMPLETED` in the regenerated `PROGRESS.md` mirror.
        Then move the item to `DONE`: `./bin/lets scr sdlc tasks status set <ID> DONE` (a ledger write).

4. **Report.** Confirm the promotion (the merged branch/commit), the new status (`DONE`), and any follow-ups
   the Integrator raised. Note that `./bin/lets scr sdlc tasks list` now shows the item green.

## Notes

- This is a no-code gate: do not re-run QA or re-validate here — `/sdlc-implement` already proved the feature on
  the integration worktree. `/sdlc-approve` records the user's approval and promotes; if the user is not
  satisfied, they run `/sdlc-implement` (fixes) or `/sdlc-obsolete` instead of this.
- The branches (`sdlc/<ID>/integration`, `sdlc/<ID>/<BLK-NNNN>`) are left in place after the worktree is
  removed — cheap and recoverable; prune them later if desired.
- Approve takes **no stack lock**: it neither rebuilds nor brings the stack up (the Integrator confirms only
  the unit build), so it never contends with a running QA window. Its `DONE` transition goes through
  `./bin/lets scr sdlc tasks status set` — already serialized under the registry lock — so approving one
  feature while another is mid-implementation is safe.
- A **standalone** promote into the main tree (step 2a) **does** take the **main-tree promote lock**: it merges
  into the working branch in the one shared main checkout, so two approvals running close together must not
  drive two Integrators into that working tree at once. The lock makes them take turns — the second's
  `maintree lock` blocks until the first's promote lands, then re-contends atomically — instead of racing a
  shared index and HEAD. It is a **separate** lease from the stack lock (a different singleton), so a promote
  never contends with a QA window and vice versa. A **chain-land** (step 2b) takes **no** lock: it merges into
  the chain's own integration branch, which only that one `/sdlc-chain-run` writes — the main tree is untouched
  until the chain's final promotion, which is where the lock is taken (by `/sdlc-chain-run`).
