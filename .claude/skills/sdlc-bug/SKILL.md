---
name: sdlc-bug
description: File a reported defect as a BUG brief (`BUG-NNNN`) onto the shared `sdlc` ledger branch (a BACKLOG record + BRIEF.md via `sdlc items file`, origin BUG) from a free-text bug description — triage the report by reviewing the relevant code and documentation to pin down the probable root cause, then prompt the user to categorize the bug's severity (HIGH|MEDIUM|LOW) and pick a tag, reserve + mint the next free `BUG-NNNN-NAME` id (parallel-safe, reusing released holes), and file the item with its frontmatter manifest. The defect analogue of `/sdlc-new`. Do NOT auto-invoke; only run when explicitly called with /sdlc-bug.
argument-hint: "free text describing the bug — symptom, repro (or omit to be asked)"
---

# New Bug Brief (`/sdlc-bug`)

> **Ledger model.** All SDLC bookkeeping — every item / chain / task record and every item document (`BRIEF.md`, `PROGRESS.md`, `TSK-*.md`) — now lives on the shared **`sdlc`** git branch, not the working tree (`docs/devel/` holds only a tombstone README). The `sdlc …` commands read and write that branch; open an item's documents at `$(./bin/lets scr sdlc tasks path <ID>)`. Any working-tree folder path mentioned below is historical — resolve the real one through the tooling. See `docs/SDLC.md` → *Ledger tracker*.

Intake stage of the SDLC pipeline for **reported defects**. Turns a free-text bug report into a
**ready-to-plan BUG brief** (`BUG-NNNN`) filed as a `BACKLOG` item on the shared `sdlc` ledger branch — the
waiting room before `/sdlc-plan`. Each item is a ledger record plus a `BRIEF.md` at `items/<ID>-NAME/` on the
branch. A `BUG-NNNN` brief is a **defect** — its **origin is BUG**, a
first-class item type beside PRD features (`FTR`) and ad-hoc work (`BLG`). It flows through the same pipeline
as any item (`/sdlc-plan` → `/sdlc-implement` → `/sdlc-approve`), where it decomposes predominantly into
**FIX** tasks (code that diverges from the documentation / the brief).

This skill differs from `/sdlc-new` in two ways: it **triages** the report first — reviewing the relevant code
and docs to pin down the probable **root cause** before filing — and it **requires** a severity and a tag from
the user rather than leaving them optional. It is otherwise the defect twin of `/sdlc-new`.

**Read the [SDLC guide's Tags section](../../../docs/SDLC.md#tags) first** — it owns the item-kind
rules, the tag legend this skill enforces, and the priority scale that carries the bug's severity. This is a
docs-only edit; no stack rebuild, and the triage **reads** code but never changes it. The `BUG` id is minted
through `./bin/lets scr sdlc briefs mint --prefix BUG`, which reserves it under the shared registry lock and on
the shared `sdlc` ledger branch, so **several `/sdlc-bug` runs can go at once — on the same host or on
different machines — without ever colliding on an id** (the local reservation is transient runtime state under
`.lets/sdlc/`, not a doc change), on its own `BUG` numbering space independent of `BLG`. If the mint reports it
cannot reach the remote, **stop and tell the user** rather than re-running with `--offline`.

## Arguments

`$ARGUMENTS` — free text describing the defect: the symptom, the steps to reproduce, the observed vs expected
behavior. Optional; if omitted, ask the user what is broken. The user owns the report — capture what they say,
and ask only to close a load-bearing gap (see step 3).

## Procedure

1. **Take the report.** `$ARGUMENTS` is the bug's raw material. If empty, ask the user what defect they want to
   file — the symptom, when it happens, and what they expected instead — before going further.
2. **Read the conventions + scan the pool.** Read the SDLC guide's *Tags* section (the tag legend + the
   main/secondary rule) and its *Status lifecycles* priority scale (the severity vocabulary). Skim a few existing
   briefs (open one at `$(./bin/lets scr sdlc tasks path <ID>)/BRIEF.md`) so the new brief matches their shape
   (a frontmatter **manifest** + a terse full-sentence body) and you can spot a duplicate.
3. **Understand the symptom — ask only where needed.** From the report, extract the **symptom** (what breaks,
   observed vs expected) and the **repro** (the steps / conditions that trigger it). Where the report leaves a
   load-bearing gap, **put the specific gaps to the user** via `AskUserQuestion` — one focused question per
   gap, at most a few in one batch. Gaps worth asking about: the exact **repro steps**, the **surface /
   service** where it shows (a backend service, the web client, the SAL corpus, the DB), the **observed vs
   expected** outcome, and whether it is a **regression** (worked before) or always-broken. A crisp report that
   already answers these needs **no** questions.
4. **Triage — review the code and docs to pin down the cause.** This is the step that sets `/sdlc-bug` apart.
   Investigate the probable **root cause** — enough to name it and its blast radius, *not* a full code audit
   (that is `/sdlc-plan`'s code-auditor). Read only, changing nothing:
   4.1. **Locate the surface.** From the symptom, find the layer and module in play — grep the affected service
        / web area for the symptom's symbols, error strings, and endpoints, then read the closest code (follow
        the CLEAN path `controller → usecase → repository → data source` to the layer that owns the broken
        behavior).
   4.2. **Cross-check the intent.** Compare what the code does against what the docs say it should — the arch
        docs (`docs/arch/*`, layer READMEs) and the spec (PRD/SRS) for the affected feature — so the bug is
        framed as a **divergence from documented intent** (the `FIX` kind), not a preference.
   4.3. **Form the hypothesis.** State the **probable root cause** and the **suspected files / symbols / layer**
        — verbatim. If the evidence is thin, say so and give the most likely candidate; the planner's audit will
        confirm. Do **not** fix anything here.
5. **Duplicate gate.** Scan the ledger for an item already covering this defect — `./bin/lets scr sdlc tasks
   list` for the titles, reading a candidate's brief via `sdlc tasks path`. If one exists, **stop** — point the
   user at it (it may just want a severity bump via `./bin/lets scr sdlc tasks priority set`, or a re-plan)
   rather than filing a
   near-duplicate.
6. **Categorize the severity — required.** Prompt the user via `AskUserQuestion` to categorize the bug as
   **HIGH | MEDIUM | LOW** (offer your recommended rank first, based on the triage). This is the manifest
   `priority` — the SDLC model carries a bug's severity in the priority field (`HIGH` = blocks work / data loss
   / a broken core path, pull it in next; `MEDIUM` = degraded with a workaround, schedule soon; `LOW` =
   cosmetic / rare, fix eventually). A bug is always ranked — never leave it `NONE`.
7. **Pick a tag — required.** Prompt the user via `AskUserQuestion` to pick the bug's **main** tag — its
   primary **engineering area** or affected surface — from the fixed vocabulary (the legend in the SDLC guide
   §Tags), with an optional **secondary** tag (a cross-cutting concern or a second area). **Reuse an existing
   tag;** suggest your best pick (the area the triage pointed to) first, and only mint a new tag if nothing in
   the legend fits and the user agrees — and say so in the report.
8. **Reserve + mint the id.** Do **not** hand-scan for the max id — the CLI owns id selection. Run
   `./bin/lets scr sdlc briefs mint --prefix BUG --label <short-slug>` (a terse slug from the report) and
   capture the `BUG-NNNN` it prints to stdout. Under the shared registry lock it scans the **whole item tree**
   for used `BUG` numbers, **reuses the highest genuine released hole** before advancing the frontier by one,
   and records the choice in the `BUG` reservation ledger — so a `BUG` id is never reused and **parallel
   `/sdlc-bug` runs never collide** (its numbering is independent of `BLG`). The reservation is **held for the
   rest of this run** — release it at step 11 once the folder is filed (or if you abort before filing). Append
   a 3–5 word **UPPERCASE** `-NAME` drawn from the symptom: `BUG-NNNN-<UPPER-SHORT-NAME>`.
9. **Author the `BRIEF.md`.** Compose the YAML frontmatter **manifest** (the item's single source of truth),
   then the brief body:
   9.1. **`origin:`** — `BUG`. **`status:`** — `BACKLOG` (mirrors the folder, which is authoritative).
   9.2. **`priority:`** — the severity from step 6 (`HIGH` / `MEDIUM` / `LOW`).
   9.3. **`depends_on:`** — an inline `[...]` list; default `[]`; list any `BLG` / `FTR` / `BUG` ids this fix
        cannot land before.
   9.4. **`tags:`** — an inline `[...]` list; the resolved `[main, secondary]` from step 7.
   9.5. **`title:`** — a short noun phrase naming the defect. **`updated:`** — today's date. **`history:`** —
        one entry `- <today> BACKLOG filed`.
   9.6. **Brief body** — after the frontmatter's `---` fence, a terse full-sentence body in the surrounding
        briefs' register (the `/caveman lite` register — no filler, but full sentences and articles), with
        every id / file path / code symbol verbatim, covering: **Symptom** (what breaks, observed vs expected),
        **Repro** (the trigger conditions), **Suspected cause** (the step-4 triage finding — probable root
        cause + affected files / symbols / layer), and **Acceptance intent** (what "fixed" looks like).
10. **File the item onto the ledger.** Write the composed brief **body** to a temp file, then file the defect:
    `./bin/lets scr sdlc items file <BUG-NNNN-NAME> --origin BUG --title "<TITLE>" --priority <SEVERITY> [--tag <T>]... --body-file <tmp>`.
    One command **upserts the item's `BACKLOG` record** (origin `BUG`, the severity as its `priority`) into the
    shared ledger **and** writes its `BRIEF.md` onto the `sdlc` branch under `items/<ID>/` — so the defect is
    immediately listed by `sdlc tasks list` and plannable. File **only** the brief; `PROGRESS.md` / `TSK-NNNN-*.md`
    come from `/sdlc-plan`. There is **no working-tree folder** — all bookkeeping is on the branch.
11. **Release the reservation, then report.** Once the item is filed, release the id's hold with
    `./bin/lets scr sdlc briefs release <BUG-NNNN>` — the id is now durably recorded on the branch. If you
    **abort before filing**, still release the id so it returns to the pool. Then show the filed brief — id,
    severity, tags, suspected cause, and any deps. Note the item is now `BACKLOG` (it appears in
    `./bin/lets scr sdlc tasks list` with origin `BUG`), that its severity / deps /
    tags can be adjusted with `./bin/lets scr sdlc tasks priority|depends|tag …`, and that it enters the
    pipeline via `/sdlc-plan <ID>` (which decomposes the fix, predominantly into `FIX` tasks) →
    `/sdlc-implement` → `/sdlc-approve`. Do not plan or fix it here.

## Brief template

The `BUG-NNNN` `BRIEF.md` — a frontmatter manifest then the brief body:

```markdown
---
id: BUG-NNNN-UPPER-SHORT-NAME
origin: BUG
status: BACKLOG
priority: HIGH
depends_on: []
tags: [main, secondary]
title: Short defect title
updated: 2026-07-19
history:
  - 2026-07-19 BACKLOG filed
---

**Symptom** — what breaks, observed vs expected, symbols verbatim.
**Repro** — the steps / conditions that trigger it.
**Suspected cause** — probable root cause + affected files / symbols / layer (the triage finding).
**Acceptance intent** — what "fixed" looks like.
```
