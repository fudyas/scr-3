---
name: sdlc-new
description: File a new ad-hoc backlog brief (`BLG-NNNN`) onto the shared `sdlc` ledger branch (a BACKLOG record + BRIEF.md via `sdlc items file`) from a free-text description — ask followup questions where needed to pin the item's purpose / idea, resolve + suggest its tags from the fixed vocabulary, reserve + mint the next free `BLG-NNNN-NAME` id (parallel-safe, reusing released holes), and file the item with its frontmatter manifest. The inverse of `/sdlc-plan` (files a brief in, rather than pulling one out). Do NOT auto-invoke; only run when explicitly called with /sdlc-new.
argument-hint: "free text describing the backlog item (or omit to be asked)"
---

# New Backlog Brief (`/sdlc-new`)

> **Ledger model.** All SDLC bookkeeping — every item / chain / task record and every item document (`BRIEF.md`, `PROGRESS.md`, `TSK-*.md`) — now lives on the shared **`sdlc`** git branch, not the working tree (`docs/devel/` holds only a tombstone README). The `sdlc …` commands read and write that branch; open an item's documents at `$(./bin/lets scr sdlc tasks path <ID>)` and persist an authored plan with `sdlc plan commit`. Any working-tree folder path mentioned below is historical — resolve the real one through the tooling. See `docs/SDLC.md` → *Ledger tracker*.

Intake stage of the SDLC pipeline. Turns a free-text description into a **ready-to-plan ad-hoc brief**
(`BLG-NNNN`) filed as a `BACKLOG` item on the shared `sdlc` ledger branch — the waiting room before `/sdlc-plan`.
Each item is a ledger record plus a `BRIEF.md` at `items/<ID>-NAME/` on the branch. A `BLG-NNNN` brief is
**curated work the PRD does not cover** — its **origin is ADHOC** (added outside the PRD): a task or churn, a
fix, a performance pass, a refactor / hygiene job, a doc-sync, a testing gap, an infra obligation, or a non-PRD /
net-new capability that still needs a PRD `FTR` authored first. It is **not** a PRD feature (those are
`FTR-XXXX` items owned by [`PRD.md`](../../../docs/PRD.md), scheduled through a lean scheduling record
— this skill never files one).

**Read the [SDLC guide's Tags section](../../../docs/SDLC.md#tags) first** — it owns the item-kind rules,
the type vocabulary, and the fixed tag legend this skill enforces. This is a docs-only edit; no stack rebuild.
The `BLG` id is minted through `./bin/lets scr sdlc briefs mint`, which reserves it under the shared registry
lock and on the shared `sdlc` ledger branch, so **several `/sdlc-new` runs can go at once — on the same host
or on different machines — without ever colliding on an id** (the local reservation is transient runtime state
under `.lets/sdlc/`, not a doc change). If the mint reports it cannot reach the remote, **stop and tell the
user** rather than re-running with `--offline`; minting blind is what causes cross-host collisions.

## Arguments

`$ARGUMENTS` — free text describing the item to add (the problem, the idea, the work). Optional; if omitted,
ask the user what to add. The user owns the detail — capture what they say, and ask only to close a
load-bearing gap.

## Procedure

1. **Take the description.** `$ARGUMENTS` is the brief's raw material. If empty, ask the user what backlog item
   they want to add before going further.
2. **Read the conventions + scan the pool.** Read the SDLC guide's *Tags* section (the two item kinds, the
   **type vocabulary**, the **tag legend** + the main/secondary rule). Skim a few existing briefs (open one at
   `$(./bin/lets scr sdlc tasks path <ID>)/BRIEF.md`) so the new brief matches their shape (a frontmatter
   **manifest** + a terse full-sentence body) and you can spot a duplicate.
3. **Duplicate gate.** Scan the ledger for an item already covering this work — `./bin/lets scr sdlc tasks
   list` for the titles, reading a candidate's brief via `sdlc tasks path`. If one exists, **stop** — point the
   user at it (it may just want a priority bump via `./bin/lets scr sdlc tasks priority set`, or a re-plan)
   rather than filing a
   near-duplicate.
4. **Understand the purpose — ask only where needed.** From the description, extract three things: **what** the
   item is, **why** it matters, and its rough **acceptance intent** (what "done" looks like). Where the
   description leaves a load-bearing gap, **put the specific gaps to the user** via `AskUserQuestion` — one
   focused question per gap, at most a few in one batch. Gaps worth asking about:
   4.1. The **goal / value** — why this is worth building, if the description only states a symptom.
   4.2. The **scope boundary** — what is in vs deliberately out.
   4.3. The **work type** — is it a fix, a performance pass, a refactor, a testing gap, an infra obligation, or
        a net-new capability? (This informs the main tag at step 5.)
   4.4. The **surface / service** it touches (a backend service, the web client, the SAL corpus, the DB), if
        unclear.
   A crisp description that already answers these needs **no** questions — do not ask what it already tells you.
5. **Resolve the type + tags.** Classify the work by **type** (`feature` / `fix` / `performance` / `refactor` /
   `doc` / `data`, plus the `testing` / `infra` areas) and pick its **tags** from the fixed vocabulary (the
   legend in the SDLC guide §Tags): a **main** tag — a backlog item's primary **engineering area**
   — and an optional **secondary** tag — a cross-cutting concern or a second area. **Reuse an existing tag;**
   prefer it over coining a new one. **Suggest your best pick to the user and confirm** via `AskUserQuestion`
   (offer the recommended tag first). Only mint a new tag if nothing in the legend fits and the user agrees —
   and say so in the report.
6. **Reserve + mint the id.** Do **not** hand-scan for the max id — the CLI owns id selection now. Run
   `./bin/lets scr sdlc briefs mint --label <short-slug>` (a terse slug from the brief, for the reservation
   ledger) and capture the `BLG-NNNN` it prints to stdout. Under the shared registry lock it scans the **whole
   ledger** (every item + the id records), **reuses the highest genuine released hole**
   (an id absent from the ledger that fits the numbering grid — a legacy multiple of ten, or a dense-band
   integer; the fine numbers the old step-10 scheme skipped are **not** holes) before advancing the frontier by
   one, and records the choice in a shared reservation ledger — so a `BLG` id is never reused (a filed brief
   keeps its id on the branch) and **parallel `/sdlc-new` runs never collide**. The reservation is **held for
   the rest of this run** — release it at step 9 once the item is filed (or if you abort before filing). Append
   a 3–5 word
   **UPPERCASE** `-NAME` drawn from the brief: `BLG-NNNN-<UPPER-SHORT-NAME>`, mirroring the `FTR-NNNN-NAME`
   shape.
7. **Author the `BRIEF.md`.** Compose the YAML frontmatter **manifest** (the item's single source of truth),
   then the brief body:
   7.1. **`priority:`** — default `NONE`; use `HIGH` / `MEDIUM` / `LOW` only if the user gave one (ask if the
        item is plainly urgent, otherwise leave `NONE` — it can be set later with
        `./bin/lets scr sdlc tasks priority set`).
   7.2. **`depends_on:`** — an inline `[...]` list; default `[]`; list any `BLG` / `FTR` ids this cannot be
        implemented before.
   7.3. **`tags:`** — an inline `[...]` list; the resolved `[main, secondary]`, from step 5.
   7.4. **`title:`** — a short noun phrase naming the item.
   7.5. **`origin:`** — `ADHOC` (a `BLG` id with no PRD feature behind it). **`status:`** — `BACKLOG` (mirrors
        the folder, which is authoritative). **`updated:`** — today's date. **`history:`** — one entry
        `- <today> BACKLOG filed`.
   7.6. **Brief body** — the frontmatter's `---` fence, then a terse, full-sentence paragraph in the
        surrounding briefs' register (the `/caveman lite` register — no filler, but full sentences and
        articles): **what** the work is, **why**, and the **acceptance intent**, with every id / file path /
        code symbol verbatim. For a **feature**-type brief (a net-new capability), state that it **needs a PRD
        `FTR` authored first** — it cannot be `/sdlc-plan`-ned until `PRD.md` covers it.
8. **File the item onto the ledger.** Write the composed brief **body** to a temp file, then file the item:
   `./bin/lets scr sdlc items file <BLG-NNNN-NAME> --origin ADHOC --title "<TITLE>" [--priority <P>] [--tag <T>]... --body-file <tmp>`.
   One command **upserts the item's `BACKLOG` record** into the shared ledger **and** writes its `BRIEF.md`
   (mirror frontmatter + the body) onto the `sdlc` branch under `items/<ID>/` — so a filed item is immediately
   listed by `sdlc tasks list` and plannable (the record is what `/sdlc-plan`'s `tasks status set` needs). The
   `tags` classify it; the main tag must agree with the work's nature. File **only** the brief; `PROGRESS.md` /
   `TSK-NNNN-*.md` come from `/sdlc-plan`. There is **no working-tree folder** — all bookkeeping is on the branch.
9. **Release the reservation, then report.** Once the item is filed, release the id's hold with
   `./bin/lets scr sdlc briefs release <BLG-NNNN>` — the id is now durably recorded on the ledger branch, so
   the hold is spent (leaving it un-released only defers the TTL auto-reclaim). If you **abort before filing**,
   still release the id so it returns to the pool. Then show the filed brief — id, tags, priority, and any deps.
   Note the item is now `BACKLOG` (it appears in `./bin/lets scr sdlc tasks list`), that its priority / deps /
   tags can be adjusted with `./bin/lets scr sdlc tasks priority|depends|tag …`, and that it enters the pipeline
   via `/sdlc-plan <ID>` (which authors its plan on the branch and moves it to `TODO` via
   `./bin/lets scr sdlc tasks status set <ID> TODO`, keeping its `BLG` id).
   Do not plan it here — that is `/sdlc-plan`.

## Brief template

The `BLG-NNNN` `BRIEF.md` — a frontmatter manifest then the brief body (the same shape every item's `BRIEF.md`
uses):

```markdown
---
id: BLG-NNNN-UPPER-SHORT-NAME
origin: ADHOC
status: BACKLOG
priority: NONE
depends_on: []
tags: [main, secondary]
title: Short title
updated: 2026-07-04
history:
  - 2026-07-04 BACKLOG filed
---

Terse full-sentence brief: what, why, and acceptance intent, symbols verbatim.
```
