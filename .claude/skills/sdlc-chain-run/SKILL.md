---
name: sdlc-chain-run
description: Implement an entire SDLC chain end to end. Reads the chain's ordered items and chain-dependencies from the shared ledger (`sdlc chains info <CHN-NN>`), verifies every chain it depends on is fully `DONE`, then drives each item to `DONE` in sequence by invoking `/sdlc-plan` → `/sdlc-implement` → `/sdlc-approve` as each item's status requires. One chain, run strictly in order. Do NOT auto-invoke; only run when explicitly called with /sdlc-chain-run <CHN-NN>.
argument-hint: "<CHAIN-ID> (e.g. CHN-07)"
---

# Run an SDLC Chain (`/sdlc-chain-run`)

> **Migration note (ledger tracker).** The item paths and folder moves below are the **un-migrated** folder model, still in force on the main tree. On a host that has run `sdlc migrate`, items live flat at `docs/devel/items/<ID>-NAME/` and `sdlc tasks status set` writes the shared ledger — no folder move, nothing committed for the status change. The `sdlc …` commands auto-detect the mode, so the steps below hold either way; a status transition simply stops touching git once migrated. See `docs/SDLC.md` → *Ledger tracker & migration*.

Implements one **chain** from the shared ledger (`./bin/lets scr sdlc chains info <CHN-NN>`) end to end. A chain
(`CHN-NN`) is a set of items implemented **strictly in sequence** — each item reaches `DONE` before the next
starts (a later item may depend on an earlier one). This skill is the chain-level orchestrator: it drives each
item through the existing pipeline skills — `/sdlc-plan`, `/sdlc-implement`, `/sdlc-approve` — one item at a time.

**The chain is the unit of promotion to the main tree.** The whole chain is built inside **one chain
integration worktree** (`.claude/worktrees/<CHN>/integration` on `sdlc/<CHN>/integration`, cut from the working
branch): every item builds **on** that branch, so item N+1 sits atop item N and each item's QA exercises the
accumulated chain. Nothing reaches the main tree per item — the chain reaches the main tree as **one merge**,
only when every item is `DONE` (step 5). This is what makes features and releases manageable: the main tree
gains a chain at a time, reviewed and merged as a unit, not a churn of per-item promotions.

**Clean on the ledger.** Item status is a **shared ledger field**, so an item reaches `DONE` in the ledger
while its code accumulates in the chain branch — no folder moves, no tracking documents in the working tree, so
the chain merges to the main tree without tracking-doc conflicts.

**Chains are the unit of parallel work.** This skill runs exactly **one** chain sequentially. To run
independent chains in parallel, launch `/sdlc-chain-run` for each in its own session (each owns its own chain
worktree; the shared QA stack-lock serializes their QA, and the main-tree lock serializes their final
promotions).

## Arguments

`$ARGUMENTS` — the chain id to run (e.g. `CHN-07`). Required; if omitted, ask which chain, listing the chains
with `./bin/lets scr sdlc chains list`.

## Procedure

1. **Read the chain from the registry.** Run `./bin/lets scr sdlc chains info <CHAIN-ID>` — it prints the
   chain's priority, tags, dependency chains, and its member items in implementation order:
   1.1. The `deps` line names the chains this one depends on (each with its rolled-up status), or is absent
        when there are none.
   1.2. The `items (in order)` list is the member item ids in implementation order (left to right).
   If the chain id is unknown the command errors and lists the valid chains; stop and say so.

2. **Chain-dependency gate.** For each chain in this chain's `deps`, confirm it is **`DONE` and its code is on
   the working branch** — its rolled-up status is `DONE` exactly when every one of its (non-obsolete) member
   items is `DONE` (`./bin/lets scr sdlc chains info <dep>`), **and** its work has actually merged to the main
   tree: either its integration branch `sdlc/<dep>/integration` is an ancestor of the working branch (it has
   promoted), or that branch no longer exists (promoted and pruned). If a dep reads `DONE` but its branch is not
   yet merged (its chain is still mid-promotion in another session), **wait and retry**; if a dep is not `DONE`,
   **stop** and recommend running it first (`/sdlc-chain-run <blocking-chain>`). This is stricter than the old
   per-item model needed: because a chain no longer lands item-by-item on the main tree, "dep `DONE`" alone no
   longer guarantees its code is on the branch this chain will build from — the merge check restores that.

3. **Open (or resume) the chain integration worktree.** Create the chain's staging tree once:
   `./bin/lets scr sdlc worktree add <CHAIN-ID> integration` — adds `.claude/worktrees/<CHAIN-ID>/integration`
   on branch `sdlc/<CHAIN-ID>/integration`, **cut from the working branch**, and links `var/` + `admin/`. It is
   idempotent: a resumed chain re-attaches to the existing branch, keeping the items already landed into it.
   Every item in step 4 builds **on** this branch; the main tree is not touched until step 5.

4. **Run the items in order, building on the chain.** For each item id in the chain's `items:` list, left to
   right:
   4.1. **Read its live status** — `./bin/lets scr sdlc tasks info <ID>`. Never trust a status written in the
        plan; the plan carries structure only.
   4.2. **If `DONE`** — skip it (already landed into the chain) and move to the next item.
   4.3. **Confirm its own dependencies are met** — `./bin/lets scr sdlc tasks depends check <ID>` (exit 0 =
        ready). If it reports blocked (exit 3), **stop** — the plan and the item's real `depends_on` disagree (a
        partition error); report the unmet dependency rather than forcing the item.
   4.4. **Drive it to `DONE` by its status, directing every step at the chain branch** (never the bare main
        tree), invoking the pipeline skills in turn and letting each finish before the next:
        - `BACKLOG` → `/sdlc-plan <ID>` (authors the plan) → `/sdlc-implement <ID>` → `/sdlc-approve <ID>`.
        - `TODO` → `/sdlc-implement <ID>` → `/sdlc-approve <ID>`.
        - `IN PROGRESS` → `/sdlc-implement <ID>` (resume) → `/sdlc-approve <ID>`.
        - `TESTING` → `/sdlc-approve <ID>`.
        When you invoke **`/sdlc-implement <ID>`**, tell it the **base branch is `sdlc/<CHAIN-ID>/integration`**
        (its invariant 7 — it cuts the item's block + integration worktrees from the chain with `--base`). When
        you invoke **`/sdlc-approve <ID>`**, tell it the **land target is the chain branch
        `sdlc/<CHAIN-ID>/integration`** (its step 2b — it merges the item into the chain, no main-tree lock, and
        marks the item `DONE`). `/sdlc-plan` is unaffected. The item reaches `DONE` **inside the chain**, not on
        the main tree.
   4.5. **Respect every gate.** Each pipeline skill has its own stops — `/sdlc-plan`'s relevance / spec / code
        audits, `/sdlc-implement`'s QA failure or a question, `/sdlc-approve`'s conflict. **If any halts for a
        decision or fails, stop the chain at that item** and report: the item, the step that halted, and what it
        needs. Do not skip the item or jump ahead — a later item may depend on it.
   4.6. **Verify the item reached `DONE`** (`tasks info <ID>`) before starting the next. If it did not (stopped
        at `TESTING`, `TODO`, etc.), stop and report.

5. **Promote the chain to the main tree (one merge), serialized by the main-tree lock.** Only once **every**
   item is `DONE` (the chain's rolled-up status is `DONE`):
   5.1. **Acquire the main-tree lock first** — `./bin/lets scr sdlc maintree lock <CHAIN-ID>` (blocks until it
        takes the main tree). This is the **very first** promote action; launch no Integrator until it holds.
   5.2. **Promote.** Launch the **integrator** agent (promote-a-chain role): merge **source**
        `sdlc/<CHAIN-ID>/integration` into **target** the working branch, in the main checkout, telling it this
        is a **promote into the main tree** so it runs the **cross-chain precedence check** — many chains touch
        the same files, and git commit order need not reflect the intended design, so if precedence is unclear it
        **stops and asks the user** which change wins. Relay any precedence or unresolvable-conflict question to
        the user and wait — do not force the merge. Keep the lock held while a half-finished merge sits on the
        main tree.
   5.3. **Release on every exit** — `./bin/lets scr sdlc maintree unlock <CHAIN-ID>` once the merge is
        committed and the main tree is clean, or on a stop/abort with the merge undone.
   5.4. **Safely remove the chain worktree** on a clean, building merge:
        `./bin/lets scr sdlc worktree remove <CHAIN-ID> integration --prune-branch` (refuses a dirty tree; the
        per-item block/integration worktrees were already removed as each item landed).

6. **Report.** On success — every item `DONE` and the chain merged to the main tree — report each item and that
   the chain landed as one merge, and that the chain worktree was removed. On a halt — report which item/step
   stopped it, its current status, and that re-running `/sdlc-chain-run <CHAIN-ID>` resumes: it re-attaches the
   chain worktree, skips every `DONE` item, continues at the first unfinished one, and (if all items are already
   `DONE` but the chain never promoted) runs the step-5 promotion.

## Notes

- **Strictly sequential.** Never begin item N+1 before item N is `DONE`. Within a single item,
  `/sdlc-implement` still parallelizes that item's own task blocks — the sequencing here is *across* items.
- **The chain lands as one merge, not per item.** Each item lands into the chain branch (`/sdlc-approve` step
  2b, no main-tree lock); the chain reaches the main tree only at step 5, as a single reviewed merge. To review
  the assembled chain before it promotes, inspect `.claude/worktrees/<CHN>/integration` after step 4; to build
  without any promotion, drive the items with `/sdlc-implement` yourself (stopping at `TESTING`).
- **Cross-chain precedence is the Integrator's call, surfaced to you.** At step 5 the Integrator intersects this
  chain's changed files with what other chains merged since the fork; if two chains reworked the same region and
  the intended order is unclear, it **stops and asks** rather than letting commit order decide. Relay that
  question to the user.
- **Mid-run migration to the ledger.** A chain already running on the folder model can move to the ledger
  **between items** (the clean seam — no live item worktree then, since the run is sequential): migrate the main
  tree first, then run `./bin/lets scr sdlc migrate` in the chain integration worktree
  (`.claude/worktrees/<CHN>/integration`) — it flattens that worktree's item folders identically to the main
  tree (so the eventual chain merge stays conflict-free) and switches the chain's status writes to the shared
  ledger. Seeding is union-by-id, so items the main tree already seeded are untouched; the run's own
  `status set` calls bring them current. Resume the chain afterward on the ledger model.
- **Resumable.** Re-running the same chain re-attaches its integration worktree, skips every `DONE` item,
  continues at the first unfinished one, and promotes at step 5 if all items are already `DONE` but the chain
  never merged — so a chain that halted (a QA fix, a user decision) is resumed by fixing the cause and
  re-invoking the skill.
- **No auto-invoke.** Only run when explicitly called with `/sdlc-chain-run <CHN-NN>`.
