---
name: git-pr
description: Use this skill to generate a pull-request message for the recent work on the current branch. By default it walks back from HEAD to the last merge on this branch (including that merge's brought-in work), or to the branch's creation point when the branch has no merge of its own — so on a long-lived branch it describes only the latest landed slice, not the whole branch. Then it prints a PR description as raw Markdown (in a fenced code block, copyable into a PR) — a goal title, a plain-English summary in the /caveman lite register, and key changes grouped by change domain (HLD, LLD, performance, security, bug fixes, UI/UX, SDLC pipeline, Project tools), listing only the domains the work actually touches. Omits file names, tests, and per-commit detail. Read-only: makes NO commits, staging, pushes, or file writes; it only prints the message. Optionally accepts a base branch to instead describe the whole branch since it forked from that base. Do NOT auto-invoke; only run when explicitly called with /git-pr.
allowed-tools: Bash(git --no-pager log:*), Bash(git --no-pager diff:*), Bash(git --no-pager rev-list:*), Bash(git --no-pager rev-parse:*), Bash(git --no-pager merge-base:*), Bash(git --no-pager symbolic-ref:*)
argument-hint: "[base branch — omit to describe recent work back to the last merge/creation event]"
---

# Git PR Message (`/git-pr`)

Walk the branch's **recent** work — from HEAD back to the last merge or, failing that, the branch's creation point — then **print** a pull-request message as **raw Markdown**. This skill is **read-only**: it never commits, stages, pushes, or writes a file. The message is emitted inside a fenced ` ```markdown ` code block so the user copies the literal Markdown source into a PR description — nothing else happens.

## What "recent work" means

The lower bound of the range is chosen so the message describes the **latest landed slice**, not the whole branch:

1. **Last merge (default).** On a branch where work lands as merges (e.g. a release branch taking `Merge sdlc/<ID>/integration`), the range starts at the most recent merge's **first parent** — so the range **includes that merge's payload** (the feature that just landed) plus any direct commits after it. Walking back further would re-describe already-shipped features.
2. **Creation event (fallback).** A branch with no merge of its own (a plain feature branch off its base) has no merge boundary, so the range starts at the **fork point** — every commit the branch adds over its base. This is the classic feature-branch PR.
3. **Explicit base (argument).** Passing a base branch forces mode 2 against that base: the **whole branch** since it forked from the given base, regardless of intervening merges.

## Arguments

`$ARGUMENTS` — optional. A base branch/ref (e.g. `master`, `origin/main`, a release tag). When given, the message covers the whole branch since it forked from that base (mode 3 above). When empty, the boundary is auto-detected: last merge, else creation point (modes 1–2). The default branch used for the creation-point fallback is `origin/HEAD`, falling back to `origin/master` → `origin/main` → `master` → `main`.

## Core constraint

**Read-only. Produce text, change nothing.** Never run `git commit`, `git add`, `git push`, `git reset`, or any write. Never create or edit a file. The only output is the printed Markdown message. If the range has no work commits, stop and say so — do not invent content.

## Procedure

1. **Resolve the boundary** — the lower bound of the range. Run this block; it uses `$ARGUMENTS` when given (whole branch since that base), else auto-detects the last merge, else the creation point:
   ```bash
   arg="$1"                        # the /git-pr argument, or empty
   def="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)"
   [ -n "$def" ] || for c in origin/master origin/main master main; do
     git rev-parse --verify --quiet "$c" >/dev/null && { def="$c"; break; }
   done
   if [ -n "$arg" ]; then
     lower="$(git merge-base "$arg" HEAD)"          # whole branch since fork from $arg
     mode="since fork from $arg"
   else
     fork="$(git merge-base "$def" HEAD)"           # creation event
     last_merge="$(git rev-list --first-parent --merges "$fork"..HEAD | head -n1)"
     if [ -n "$last_merge" ]; then
       lower="$(git rev-parse "$last_merge^1")"     # last merge + its payload
       mode="since last merge $last_merge"
     else
       lower="$fork"                                # no merge → whole branch since creation
       mode="since creation (fork from $def)"
     fi
   fi
   echo "branch=$(git --no-pager rev-parse --abbrev-ref HEAD)  lower=$lower  [$mode]"
   ```

2. **Guard for an empty range.** Count the work commits (merges excluded — they are assembly noise, not work):
   ```bash
   count="$(git --no-pager rev-list --no-merges --count "$lower"..HEAD)"
   echo "$count work commit(s) in range"
   ```
   If `count` is `0`, stop and tell the user there is no recent work in the range — there is no PR to describe.

3. **Walk the range's work commits** (oldest first, merges skipped — merge subjects are noise, but the range still carries their brought-in payload commits):
   ```bash
   git --no-pager log --reverse --no-merges --format='- %s%n%b' "$lower"..HEAD
   ```
   Read the subjects and bodies to understand what the work *achieves*. For a very large range (hundreds of commits), subjects alone carry the themes — use `--format='- %s'` to keep it scannable.

4. **(Optional) Pull the overall scope** for the summary line — a one-glance sense of blast radius (endpoint diff, so it reflects the merged payload too):
   ```bash
   git --no-pager diff --shortstat "$lower"..HEAD
   ```

5. **Classify and synthesize.** Sort the commits into the change domains listed in the format below; a commit can inform more than one. Keep only the domains the work actually touches. Give each kept domain one entry describing what changed there, and write the summary — indeed the whole message — in the `/caveman lite` register (plain simple words, full sentences, no filler). Discard the low-level noise (per-task commits, fixups, doc-sync commits, tests, file/function names).

6. **Print** the message as **raw Markdown inside a fenced ` ```markdown ` code block**, so the user copies the literal source into a PR description — the `#` title, `**bold**`, and `-` bullets stay as Markdown syntax, not terminal-rendered or plain text. Do not write it to a file. Do not offer to commit or push it.

## Rules

- Always use `--no-pager` for read commands.
- Never commit, stage, push, reset, amend, or write any file — this skill only reads and prints.
- **Output raw Markdown** inside a fenced ` ```markdown ` block — the copyable source, never terminal-rendered or plain text.
- Default (no argument): lower bound is the **last merge's first parent** (its payload is in range), else the **creation-point fork**. With an argument: lower bound is the **fork from that base**.
- **Skip merge commits** when reading the work (`--no-merges`); the range still includes the payload commits they brought in.
- **One bullet per touched change domain**, from the fixed set only. **Omit** every untouched domain; never invent a domain outside the set.
- Write the summary and every domain description in the **`/caveman lite`** register: plain simple everyday words, short full sentences, no filler or hedging.
- **No low-level detail** in the output: no file names, no function/class names, no test mentions, no commit hashes, no SDLC/ticket id prefixes. The one exception is naming a service or app in the **LLD** domain — that is the whole point of LLD.
- **Base-sync caveat.** The default mode includes the last merge's payload. If that last merge merged the **base into this branch** (a sync, not a feature landing), the payload is the base's commits, not yours — the message would describe them as your work. When the last merge is a sync, pass an explicit base argument (mode 3) or a tag so the range starts where your work really began.
- If the range has no work commits, print nothing but the "nothing to describe" note.

## PR message format

Write the whole message in the **`/caveman lite`** register (per the `caveman` skill): plain, simple, everyday words; short full sentences; keep articles; no filler, no hedging, no jargon the reader can't decode. Simple synonyms — "big" not "extensive", "fix" not "implement a solution for".

1. **Title** — one line: the PR's **goal** — what it delivers as a whole, not a list of commits. A plain statement. No id prefixes, no "PR:".
2. **Summary** — 1–3 short plain sentences: what the PR does, in simple words. High-altitude.
3. **Key changes by domain** — a bulleted list, **one bullet per change domain the work actually touches**, each `**Domain** — <plain description of what changed there>`. Consider the domains in this fixed order and include only the ones that apply:
   1. **HLD** — high-level / architectural design: the shape of the change and its reach (backend, frontend, or system-wide).
   2. **LLD** — low-level design: which specific service(s) or app(s) changed. (Naming a service/app is expected here — this is the one place a concrete component name belongs.)
   3. **Performance** — speed, throughput, memory, round-trips, fan-out.
   4. **Security** — auth, sessions, access control, tenant isolation, secrets, permissions.
   5. **Bug fixes** — defects corrected (user-visible or internal).
   6. **UI/UX** — the user interface and interaction.
   7. **SDLC pipeline** — the delivery process and its tooling (planning, chains, trackers, agent skills).
   8. **Project tools** — the developer tooling under `tools/` and the dev CLIs.
   **Omit every domain the work does not touch** — untouched domains never appear. Never add a domain outside this set.
4. **Nothing else.** No checklist, no "how to test", no file list, no sign-off or attribution.

## Example output

For a branch whose latest landed merge removed the editable project description end-to-end. Note how only the touched domains appear — this work had no performance or security change, so those domains are simply left out.

```markdown
# Remove the editable project description end-to-end

The project no longer has a free-text description field. The dashboard card
that showed it is now read-only, and the column behind it is dropped.

**Key changes by domain**

- **HLD** — System-wide: pulled the description out of the write path across
  the backend and the web client, then dropped its storage.
- **LLD** — Authoring service: removed the description read and write paths and
  dropped the project description column.
- **Bug fixes** — Fixed system-test seeds that still wrote the dropped column.
- **UI/UX** — The dashboard project card is now read-only; the edit screen for
  the description is gone.
```
