---
name: sdlc-plan
description: Plan a PRD feature, a backlog brief (BLG-NNNN), or ad-hoc free-text work for implementation — first check the item is still worth building (relevance-auditor; ask the user when in doubt, stop and recommend /sdlc-obsolete when stale), then audit the spec slice and the existing code, decompose into parallel task blocks (BLK-NNNN) and tasks (TSK-NNNN) covering TASK/IMPROVE/REFACTOR/FIX work, review the plan, author its plan (PROGRESS.md + TSK files) under `sdlc tasks path <ID>` and commit it with `sdlc plan commit <ID>`, then move it to TODO via `sdlc tasks status set <ID> TODO` (origin PRD for a feature, ADHOC for a BLG brief / free text — a brief keeps its BLG id, free text mints a fresh one). Do NOT auto-invoke; only run when explicitly called with /sdlc-plan.
argument-hint: "FTR-XXXX, BLG-NNNN, or free text describing ad-hoc work"
---

# Feature / Ad-hoc Plan (`/sdlc-plan`)

> **Ledger model.** All SDLC bookkeeping — every item / chain / task record and every item document (`BRIEF.md`, `PROGRESS.md`, `TSK-*.md`) — now lives on the shared **`sdlc`** git branch, not the working tree (`docs/devel/` holds only a tombstone README). Author an item's plan under `$(./bin/lets scr sdlc tasks path <ID>)` (the materialized branch worktree), then persist it — records + documents — with `./bin/lets scr sdlc plan commit <ID>`. Move status with `sdlc tasks status set` (a ledger write, no folder move). Any working-tree folder path mentioned below is historical — resolve the real one through the tooling. See `docs/SDLC.md` → *Ledger tracker*.

Plan stage of the SDLC pipeline. Plans either a **PRD feature** or an **ad-hoc free-text work item**.
First it **checks the item is still worth building** (relevance-auditor) — asking the user followup questions
when the answer is in doubt, and stopping when the item is stale — then audits its specification slice **and
its existing code**, decomposes the work into a traceable, parallelizable breakdown, reviews that breakdown,
and registers it.

**Read [`docs/SDLC.md`](../../../docs/SDLC.md) first** — it is the source of truth for all
notation, ids, task kinds, status, the gate, the templates, and the two conventions this skill enforces:
artifacts authored in `/caveman full`, and subagent runs in `/caveman full`.

**Every pipeline subagent runs in `/caveman full` at all three phases** — you author the handoff terse, the
agent works terse, and it reports back terse (each agent definition enforces the run + report). Keep every id,
file path, code symbol, CLI command, and error string verbatim; code, edits, and commit messages stay normal.

## Arguments

`$ARGUMENTS` — one of: a PRD feature id (`FTR-XXXX` / `FTR-XXXX-NAME`); a backlog brief id (`BLG-NNNN` /
`BLG-NNNN-NAME`) filed as a `BACKLOG` record on the `sdlc` branch; or free text describing ad-hoc work that
belongs to no PRD feature (a refactor, a performance pass, a cleanup). Required. The user owns the detail of a
free-text brief; plan to what it says. Planning authors the item's plan under `$(./bin/lets scr sdlc tasks
path <ID>)`, commits it with `./bin/lets scr sdlc plan commit <ID>`, then moves the item to `TODO` with
`./bin/lets scr sdlc tasks status set <ID> TODO` (a ledger write — no folder move).

## Procedure

1. **Determine the mode + resolve the scope.**
   1.1. **Feature mode** — `$ARGUMENTS` is a PRD feature id (`FTR-\d+`). Find the `#### FTR-XXXX-…` header in
        `docs/PRD.md`. If none, **stop** — report the id is not a PRD feature. Read its status from
        the ledger (`./bin/lets scr sdlc tasks info <ID>`); a feature with no ledger record is `BACKLOG` by
        default (it may carry a scheduling record). Planning is allowed from **any** state — a re-plan
        overwrites the item's task records + plan documents and re-authors a fresh `TODO` breakdown, so step 9
        resets the item to `TODO`. Before re-planning an `IN PROGRESS` or `TESTING` feature, **warn the user**
        that any in-flight implementation (block worktrees / branches, an integration branch) is theirs to
        reconcile; re-planning a `DONE` feature reopens it as new `TODO` work.
   1.2. **Brief mode** — `$ARGUMENTS` is a backlog brief id (`BLG-\d+`). Read its record + brief
        (`./bin/lets scr sdlc tasks info <ID>`); if none, **stop** — report the brief id is unknown. Its
        `title` + brief body are the spec; its `priority` and `depends_on` carry onto the planned item. The
        brief **keeps its `BLG` id** — no new id is minted; it moves to `TODO` as-is (step 9.2).
   1.3. **Ad-hoc mode** — `$ARGUMENTS` is free text. Treat the text as the spec. Mint a fresh `BLG-NNNN`
        with `./bin/lets scr sdlc briefs mint --label <short-slug>` (parallel-safe across hosts via the shared
        `sdlc` ledger branch, reusing a released hole; it prints the id — if it reports it cannot reach the
        remote, stop and tell the user rather than passing `--offline`), then append a 3–5 word UPPERCASE name
        drawn from the brief: `BLG-NNNN-<UPPER-SHORT-NAME>`. It has no record yet — step 7 files it with
        `./bin/lets scr sdlc items file <ID> --origin ADHOC …` (a `BACKLOG` record + its `BRIEF.md` on the
        branch). Release it (`./bin/lets scr sdlc briefs release <BLG-NNNN>`) once it is filed at step 9.3.
2. **Relevance gate — is the item still worth building? (subagent, own context).** Runs **first**, before any
   deep read, spec/code audit, or authoring — no effort is spent on a dead item. Launch the
   **relevance-auditor** agent with the item id, its mode, its **main idea** (the `FTR` prose / the `BLG-NNNN`
   title + brief body / the ad-hoc free text), its current status, and pointers to the context (PRD/SRS,
   `docs/arch/*`, the plan `./bin/lets scr sdlc plan show`, the item records + documents on the `sdlc`
   branch) — author the handoff in `/caveman full` and ask it to
   reply in kind (ids/paths verbatim). It judges **supersession, invalidated premise, direction drift,
   duplication, and stale-brief ambiguity** — not spec consistency (step 4) or code maturity (step 5). Act on
   its verdict:
   2.1. **RELEVANT** → proceed to step 3. Fold any advisory (e.g. narrow the scope to the still-relevant
        part) into the plan's task notes at step 7.
   2.2. **STALE** → **stop.** Author no plan and leave the ledger untouched. Present the auditor's
        findings and **recommend `/sdlc-obsolete <ID>`** (or, for a shelvable ad-hoc item, demoting it to
        `BACKLOG`).
        Do not tombstone it yourself — obsoleting is its own pipeline stage and the user's call.
   2.3. **UNSURE** → **put the auditor's followup questions to the user** (via `AskUserQuestion`) before
        deciding. Then branch on the answers: if the user affirms the item is still wanted (possibly narrowing
        its scope), proceed to step 3, folding the clarification into the plan context; if the user agrees it
        is stale, stop as in 2.2 and recommend `/sdlc-obsolete`.
   A freshly-typed ad-hoc brief is presumptively relevant — the user just asked for it — so the gate rarely
   stops it; it bites on parked `BACKLOG` features, dated `BLG` briefs, and re-plans of a `DONE`/`TESTING`/
   `IN PROGRESS` item.
3. **Read the documentation slice** so the plan traces to the source of truth.
   3.1. Feature mode: the `FTR` prose in `PRD.md`; the realizing `FNC`(s) in `SRS.md`
        (`grep -nE "implements.*FTR-XXXX" docs/SRS.md`); their `CON`/`ASM`/`NFR`/`ENT`; the related
        `docs/arch/*`.
   3.2. Ad-hoc / brief mode: the brief text (the free-text argument, or the `BLG-NNNN` folder's `title` +
        brief body);
        the architecture and standards it touches (`docs/arch/*`, `CLAUDE.md`, and any `CON`/`NFR` in
        `SRS.md` the work must obey).
4. **Pre-plan gate — spec audit (subagent, own context).** Launch the **spec-auditor** agent with the scope
   and the doc slice — author the handoff in `/caveman full` and ask it to reply in kind (ids/paths verbatim).
   Feature mode: it checks PRD↔SRS↔arch alignment. Ad-hoc mode: it checks the brief against the architecture
   and standards (does the requested work contradict them?). **A blocking (no-go) verdict STOPS planning** —
   present the contradictions and await the user. Author no plan.
5. **Code-assessment gate — implementation audit (subagent, own context).** Launch the **code-auditor** agent
   with the scope and the doc slice — handoff in `/caveman full`, reply in kind. It surveys the existing
   codebase and returns: what already exists, its **maturity** (none / partial / full), its compliance with
   CLEAN layering + standards + style, performance concerns, and gaps versus the documentation. **If it
   reports the scope is already fully implemented and compliant with no findings**, author no plan — tell the
   user there is nothing to do and do not register the item.
6. **Decompose into blocks + tasks**, sized to the code audit. The breakdown must cover **all** the work the
   audit surfaced, across the four task **kinds** (canonical defs in the SDLC guide):
   6.1. **TASK** — net-new scope with no implementation.
   6.2. **IMPROVE** — a performance / enhancement pass over working code.
   6.3. **REFACTOR** — code that violates the architecture / standards / style.
   6.4. **FIX** — code that diverges from the documentation (or the brief).
   Block/task rules: **blocks** (`BLK-NNNN`, step 1 from `BLK-0001`) are **fully parallel — never any
   cross-block dependency**; **tasks** (`TSK-NNNN`, step 1 from `TSK-0001`, monotonic across the item) order by
   `Depends on` within a
   block; use **CLEAN layering as the decomposition guide**; each task description is an **UPPERCASE
   imperative 3–4 word phrase**; each task names its **Kind** and traces to its source (the
   `FTR`+`FNC`/`CON`/… for a feature, or the brief + the arch/standards it serves for an ad-hoc item, plus
   the audit finding an IMPROVE/REFACTOR/FIX task addresses).
7. **Author the plan** under `$(./bin/lets scr sdlc tasks path <ID>)` — the item's folder in the branch
   worktree, beside its `BRIEF.md`. When the item has no record yet — a fresh **ad-hoc** item, or an unscheduled
   PRD **feature** — first file it with `./bin/lets scr sdlc items file <ID> --origin <PRD|ADHOC> --title <T>
   [--body-file <brief>]` (feature: `origin PRD`, description owned by `PRD.md`; ad-hoc: `origin ADHOC`, the
   brief body), which mints its `BACKLOG` record + `BRIEF.md` on the branch, so `tasks path` then resolves its
   folder. All tasks at status `TODO`, to the **guide's templates** (Task file + PROGRESS.md sections of
   `docs/SDLC.md`): `PROGRESS.md` and one `TSK-NNNN-<UPPER-DESC>.md` per task.
   7.1. **Author in `/caveman full`** — the prose only (Title, Overview, To Do, DoD). Every id, file path,
        code symbol, CLI command, status token, and the metadata / trace **tables** stay verbatim. Keep each
        To Do step unambiguous (no order-dependent fragments).
   7.2. **`PROGRESS.md` is trace-only** — the `# <Feature ID> Progress Tracking` title, a `## References`
        section (**only** the SDLC guide + PRD + SRS; ad-hoc: the guide + the item's `BRIEF.md`), then
        a `## Implementation Blocks` rollup table (Block / Title / Status, all `PENDING` on a fresh plan) and
        one `## BLK-NNNN` task-tracking table per block (columns **Task | Kind | Status | Depends on | Last
        modified** = `yyyy-mm-dd`, today on a fresh plan). No Description column, no pipeline narrative, no
        status vocab, no gate prose, no finer doc refs (the tasks cite those) — those live in the guide / the
        task files.
   7.3. **Per-plan context goes in the task files** — spec-auditor advisories the task must honor, relevance
        advisories (a scope narrowed at step 2), scope notes (deliberate deferrals) belong in the relevant
        task's To Do / DoD, self-contained. Not in PROGRESS.md.
   7.4. Copy the **Standards block verbatim** from the guide into each task (it is a fixed contract, not
        compressed prose).
8. **Post-plan gate — plan review (subagent, own context).** Launch the **plan-reviewer** agent with the
   authored plan files (the item's folder) and the doc slice / brief — handoff in `/caveman full`, reply in
   kind. It checks
   the tasks correctly + completely cover the work (coverage including the audit findings, dependency
   ordering, block parallelism, traceability, task kinds). **Apply its fixable corrections** (re-author the
   affected files); surface decisions to the user.
9. **Register + report — commit the plan, move the item to `TODO`.** First `./bin/lets scr sdlc plan commit
   <ID>` — it derives the item's task records from the authored `PROGRESS.md` + `TSK-*.md` and lands the records
   + documents on the branch. Then `./bin/lets scr sdlc tasks status set <ID> TODO` — a ledger write that
   flips the item's `status` to `TODO` and appends a dated history entry (**no folder move, nothing committed to
   the working tree**). The item's priority / `depends_on` / `tags` are ledger fields; **carry them forward**
   from the backlog brief when one existed, otherwise priority `NONE`, `depends_on []`, tags from the resolved
   work.
   9.1. Feature mode → the `FTR` feature's record moves to `TODO`, carrying its `priority` / `depends_on` /
        `tags`; origin `PRD`.
   9.2. Brief mode → the `BLG` brief's **same record** moves to `TODO`, keeping its `BLG` id and its `priority`
        / `depends_on` / `tags`; its `title` + brief body stay the spec. Origin `ADHOC` is implicit (a `BLG` id
        with no PRD feature behind it).
   9.3. Ad-hoc mode → the freshly minted `BLG` (filed at step 7) moves to `TODO`; **release its reservation**
        (`./bin/lets scr sdlc briefs release <BLG-NNNN>`) once filed; priority `NONE`, `depends_on []`.
   9.4. Re-plan → an item already `TODO`/`IN PROGRESS`/`TESTING`/`DONE`/`OBSOLETE` already has a record; step 7
        re-authored its plan, `plan commit` re-derived the task records, and `tasks status set <ID> TODO` moves
        it back to `TODO` (a no-op when already there), preserving its fields.
   9.5. **Dependencies.** If the work cannot be implemented until another feature is `DONE` (it builds on that
        feature), record it in the `BRIEF.md` `depends_on` frontmatter or via
        `./bin/lets scr sdlc tasks depends set <ID> <DEP-ID>...`. A dependency is enforced at implement
        time, not here — `/sdlc-plan` may plan a feature
        whose dependencies are still open.
   Present the decomposition (blocks + tasks + kinds) and the **four** gate verdicts (relevance / spec / code
   / plan). Do not start implementation — that is `/sdlc-implement`.

## Templates

The canonical templates live in [`docs/SDLC.md`](../../../docs/SDLC.md) — author to them, in
`/caveman full` (step 7); do not duplicate them here:

1. **PROGRESS.md** — guide → *PROGRESS.md — trace only*. The `# <Feature ID> Progress Tracking` title, a
   `## References` section (SDLC guide + PRD + SRS only), a `## Implementation Blocks` rollup table, then one
   `## BLK-NNNN` task table (Task | Kind | Status | Depends on | Last modified). Nothing else.
2. **TSK-NNNN-<UPPER-DESC>.md** — guide → *Task file*. The metadata table, then Title / Overview /
   Documentation reference slice / To Do / Standards (the verbatim Standards block) / Definition of Done. The
   DoD names the task's `<svc>` for the gate.

The TSK metadata table (most error-prone — get it exact):

| Field | Value |
| ---------- | ----- |
| Feature ID | <ID> |
| Block ID | BLK-NNNN |
| Kind | TASK \| IMPROVE \| REFACTOR \| FIX |
| Status | TODO |
| Depends on | TSK-NNNN, … \| — |
