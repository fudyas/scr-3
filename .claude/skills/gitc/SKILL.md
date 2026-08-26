---
name: gitc
description: Use this skill to commit currently staged git changes (no auto-add). Reviews staged changes and writes a short, informative commit message with a title and bulleted list of key changes. If `/gitc` is followed by a line of text, that text is treated as a focus hint and the commit message is prioritized accordingly. Do NOT auto-invoke; only run when explicitly called with /gitc.
allowed-tools: Bash(git --no-pager status:*), Bash(git --no-pager diff:*), Bash(git --no-pager log:*), Bash(git commit:*)
argument-hint: "[focus hint or commit title]"
---

# Git Commit (`/gitc`)

Commit **already-staged** changes. Never run `git add` or otherwise stage.

## Arguments

`$ARGUMENTS` — optional. If non-empty, use as commit title verbatim and weight body bullets toward that focus. If empty, derive title and body from the staged diff.

## Procedure

1. **Verify staged changes** with `git --no-pager status` and `git --no-pager diff --staged --stat`. If nothing is staged, stop and tell the user — never auto-stage. If unstaged changes exist alongside staged ones, proceed with staged only and mention the unstaged files were left untouched.
2. **Review** the staged diff (`git --no-pager diff --staged`) and recent style (`git --no-pager log -n 5 --oneline`).
3. **Compose** the message per the format below.
4. **Commit** using a HEREDOC:
   ```bash
   git commit -m "$(cat <<'EOF'
   <title>

   - <bullet 1>
   - <bullet 2>
   EOF
   )"
   ```
   Never pass `--no-verify`, `--amend`, or `-a`. Never push.
5. **Verify** with `git --no-pager status` and report the new commit hash.

## Rules

- Always use `--no-pager` (e.g. `git --no-pager log`).
- Never run `git add`, `git stage`, `git commit -a`, or anything that modifies the index.
- Never commit without staged changes.

## Commit message format

1. **Title** — one line.
   - With focus text: use it verbatim.
   - Without: short description starting with a past-tense verb (`Added`, `Fixed`, `Updated`, `Refactored`, `Removed`, …).
2. **Body** — bulleted list, one logical change per bullet. Plain language, focus on purpose/impact, not implementation. **No file/function/class names.** With a focus hint, order bullets so the focus area leads.
3. **Nothing else.** No trailing summary, sign-off, co-author, or attribution.

## Example

```
Implemented a basic build system framework for the project.

- Implemented bootstrap script for SDK installation and configuration.
- Added utility libraries for logging, command execution, and configuration parsing.
- Updated project configuration to exclude temporary build artifacts.
```
