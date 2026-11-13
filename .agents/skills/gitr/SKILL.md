---
name: gitr
description: >-
  Use this skill to review all pending git changes (staged and unstaged), group them into functionally related commits, present the proposed commit sequence to the user, and — only after explicit consent — commit everything using that sequence. Never splits files across commits (no `git add -p`); each file goes whole into exactly one commit. Do NOT auto-invoke; only run when explicitly called with $gitr.
---

# Git Review & Grouped Commit (`$gitr`)

Review **all** pending changes, propose a sequence of functionally related commits, get the user's approval, then commit.

## Arguments

Invocation arguments are optional. A hint about how to group or what to emphasize (e.g. "keep docs separate", "one commit for the indexer refactor"). Honor it when forming groups and writing messages. If empty, derive grouping from the changes alone.

## Core constraint

**A file is never split across commits.** Do not use `git add -p`, `git add --patch`, or interactive staging. Every changed file (modified, added, deleted, renamed, or currently untracked) belongs to exactly one proposed commit. If a single file mixes unrelated changes, keep it whole and assign it to the commit that best fits its dominant change — note the compromise to the user rather than splitting it.

## Procedure

1. **Survey** all pending changes:
   - `git --no-pager status` — staged, unstaged, and untracked.
   - `git --no-pager diff --stat` and `git --no-pager diff --staged --stat` — scope per file.
   - `git --no-pager diff` and `git --no-pager diff --staged` — actual content for grouping.
   - `git --no-pager log -n 5 --oneline` — recent message style.

   If there are no pending changes at all, stop and tell the user. Untracked files **are** included — list them explicitly so the user knows they will be added.

2. **Group** every changed file into functionally related commits. A group is a set of files that together accomplish one logical change (a feature, a fix, a refactor, a docs update, etc.). Order the groups so dependencies land first (e.g. a model change before code that uses it). Each file appears in exactly one group.

3. **Compose** a commit message per group using the format below.

4. **Present** the full proposed sequence to the user and **await explicit consent**. Show, for each commit in order: the title, the body bullets, and the exact list of files it will include. After the list, ask the user to approve, and use the `AskUserQuestion` tool with options to **Proceed**, **Adjust grouping**, or **Cancel**. Do not commit anything before the user approves.

5. **Commit** — only after approval. Apply the sequence exactly as approved:
   ```bash
   git reset            # clear the index so groups are clean
   ```
   Then for each group, in order:
   ```bash
   git add -- <file1> <file2> ...        # whole files only, never -p
   git commit -m "$(cat <<'EOF'
   <title>

   - <bullet 1>
   - <bullet 2>
   EOF
   )"
   ```
   Use `--` before paths and pass each path explicitly (no broad globs that could pull in unintended files). Never pass `--no-verify`, `--amend`, or `-a`. Never push.

6. **Verify** with `git --no-pager status` and `git --no-pager log -n <N> --oneline` (N = number of commits made). Report each new commit hash and confirm the working tree is clean (or note anything deliberately left out).

## Rules

- Always use `--no-pager` for read commands.
- Never split a file across commits; never use `git add -p` / `--patch` / interactive add.
- Never commit before the user has explicitly approved the sequence.
- Stage with explicit pathspecs (`git add -- <paths>`), one group at a time.
- Never `git commit -a`, `--amend`, `--no-verify`, or push.
- If the user asks to adjust the grouping, revise and re-present; only commit once approved.

## Commit message format

Same as standard project commits:

1. **Title** — one line, starting with a past-tense verb (`Added`, `Fixed`, `Updated`, `Refactored`, `Removed`, …). Conventional-commit prefixes are fine if recent history uses them.
2. **Body** — bulleted list, one logical change per bullet. Plain language about purpose/impact, not implementation. **No file/function/class names.**
3. **Nothing else.** No trailing summary, sign-off, co-author, or attribution.

## Example presentation

```
Proposed commit sequence (3 commits):

[1/3] Added v2 corpus normalization pass
  - Introduced a flat seed-driven layout for the corpus.
  - Split document kinds into separate homogeneous collections.
  Files: src/domain/models/sal/document_seed.py, src/domain/models/sal/sal_entity.py

[2/3] Updated indexer to consume the normalized corpus
  - Pointed the indexer at the consolidated collection.
  Files: tools/indexer/src/index.py, src/app/searcher/settings.py

[3/3] Refreshed architecture docs for the v2 layout
  - Documented the new collection split and authoring flow.
  Files: docs/arch/INDEXER-v1.md, docs/arch/SPEC-SAL-v2.md
```
