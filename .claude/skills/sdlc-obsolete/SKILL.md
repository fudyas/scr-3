---
name: sdlc-obsolete
description: Mark a not-yet-implemented item (a BACKLOG or TODO feature, brief, or ad-hoc item) as OBSOLETE — a ledger write flipping its status to OBSOLETE and recording the tombstone in its BRIEF.md manifest on the `sdlc` branch. Refuses items already IN PROGRESS, TESTING, or DONE. Do NOT auto-invoke; only run when explicitly called with /sdlc-obsolete.
argument-hint: "FTR-XXXX or BLG-NNNN, or legacy ADHOC-NNNN (id or full name)"
---

# Obsolete (`/sdlc-obsolete`)

> **Migration note (ledger tracker).** The item paths and folder moves below are the **un-migrated** folder model, still in force on the main tree. On a host that has run `sdlc migrate`, items live flat at `docs/devel/items/<ID>-NAME/` and `sdlc tasks status set` writes the shared ledger — no folder move, nothing committed for the status change. The `sdlc …` commands auto-detect the mode, so the steps below hold either way; a status transition simply stops touching git once migrated. See `docs/SDLC.md` → *Ledger tracker & migration*.

Obsolete stage of the SDLC pipeline. Marks an item that will not be built as **OBSOLETE** — allowed
only before implementation has begun. An SDLC item's status is a ledger field, so obsoleting is a ledger write
that sets `status: OBSOLETE`. `OBSOLETE` is the
**irreversible tombstone**; to merely shelve a planned `BLG` item without discarding its plan, demote it to
`BACKLOG` instead (`./bin/lets scr sdlc tasks status set <BLG-ID> BACKLOG`), which keeps its plan files
(the folder just moves back into `backlog/`) and lets you promote it back with `TODO` later.

## Arguments

`$ARGUMENTS` — the item to obsolete: a `FTR-XXXX` / `FTR-XXXX-NAME` feature, a `BLG-NNNN` brief / item, or a
legacy `ADHOC-NNNN` id. Required.

## Procedure

1. **Resolve.** For an `FTR-XXXX` id, find its `#### FTR-XXXX-…` header in `docs/PRD.md`; if none,
   **stop** — report that the id is not a PRD feature. For a `BLG-NNNN` id (or a legacy `ADHOC-NNNN`), find its
   item record (`./bin/lets scr sdlc tasks info <ID>` reports it); if none, **stop** — report that the id is
   unknown.
2. **Validate state.** Read the item's status (`./bin/lets scr sdlc tasks info <ID>`); a PRD feature with no
   ledger record is `BACKLOG` by default.
   It must be `BACKLOG` or `TODO`. **Refuse** an `IN PROGRESS`, `TESTING`, or `DONE` item — only a
   not-yet-implemented item can be obsoleted (a `TESTING` item is already built and QA-passed, awaiting
   `/sdlc-approve`). An item already `OBSOLETE` is a no-op.
3. **Mark obsolete.** Run `./bin/lets scr sdlc tasks status set <ID> OBSOLETE` — a ledger write that flips
   the item's `status` field to `OBSOLETE` and appends a dated history entry. The `OBSOLETE` record is the
   tombstone; its bookkeeping:
   3.1. A `TODO` item keeps its plan documents (`PROGRESS.md` + `TSK-NNNN-*.md`) on the branch as the record of
        the discarded plan. Note the reason in the `BRIEF.md` body so the tombstone explains itself.
   3.2. A `BACKLOG` item simply flips status. A **PRD feature with no record yet** has nothing to flip — first
        file it with `./bin/lets scr sdlc items file <FTR> --origin PRD --title <T>` (a `BACKLOG` record,
        description owned by `PRD.md`), then run
        `features status set <ID> OBSOLETE` on it.
4. **Clear dependents.** Any item (`FTR` or `BLG`) whose `depends_on` frontmatter names this id can never
   satisfy its gate once this item is obsolete. Find them (`./bin/lets scr sdlc tasks list --with-deps`)
   and drop this id from each — `./bin/lets scr sdlc tasks depends set <DEPENDENT> <REMAINING-DEPS|none>`
   (it rewrites the dependent's `BRIEF.md` frontmatter) — reporting what you changed.
5. **Report.** Confirm the new status, and that `./bin/lets scr sdlc tasks list` now shows the item in
   gray.
