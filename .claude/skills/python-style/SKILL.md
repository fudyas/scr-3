---
name: python-style
description: Use this skill to audit Python code against the `/python` conventions and report every violation with its file:line and fix. Borrows the rule definitions from the `/python` skill — runs a deterministic checker for the mechanical rules plus a judgment read-pass for the rest. Do NOT auto-invoke; only run when explicitly called with /python-style.
argument-hint: "[paths or globs; defaults to changed .py files]"
allowed-tools: Read, Grep, Glob, Bash(./bin/lets devenv python run:*), Bash(git --no-pager diff:*), Bash(git --no-pager status:*), Bash(find:*)
---

# Python Style Audit (`/python-style`)

Check Python code against the project conventions, then report each violation as `path:line — [RULE] — fix`. This skill **audits**; it does not rewrite code unless the user asks.

## Source of truth

The rules are **not** restated here — that would let them drift. There are exactly two authorities:

1. **`/python` skill** (`.claude/skills/python/SKILL.md`) — the prose definition of every convention. Read it before the judgment pass.
2. **`check.py`** (next to this file) — the deterministic checker for the rules that can be decided mechanically.

Every check below maps to a `/python` section. Keep this skill and `check.py` aligned with `/python`; if a rule there changes, update the corresponding check.

## Arguments

`$ARGUMENTS` — optional. Paths, directories, or globs to audit. If empty, default to the Python files changed in the working tree (`git --no-pager diff --name-only` plus untracked `.py`). If there are none, ask the user what to audit.

## Procedure

1. **Scope.** Resolve `$ARGUMENTS` into a concrete file list. With no arguments, collect changed/untracked `.py` files from git. State the file list before checking.

2. **Mechanical pass.** Run the bundled checker over the scope:
   ```bash
   ./bin/lets devenv python run .claude/skills/python-style/check.py <path> [<path> ...]
   ```
   It prints one line per violation (`path:line: [RULE] message`) and exits non-zero if any are found. These findings are authoritative — do not second-guess them.

3. **Judgment pass.** For each file, read it and check the rules `check.py` cannot decide (see the checklist). Apply the `/python` definitions exactly; when a call is genuinely ambiguous, say so rather than inventing a verdict.

4. **Report.** Merge both passes and present findings grouped by file, each as `path:line — [RULE] — problem → fix`. Separate **must-fix** (clear rule breaches) from **consider** (judgment calls). End with a one-line count. If a file is clean, say so.

5. **Offer to fix.** Do not edit anything during the audit. After reporting, ask whether to apply the fixes. Fix only on consent, smallest-diff first, preserving behavior — then re-run the mechanical pass to confirm.

## Checklist

`[auto]` = decided by `check.py`. `[judgment]` = read-pass against `/python`.

| Check | `/python` section | Pass |
| --- | --- | --- |
| No `__init__.py` files | Packages | [auto] `INIT_PY` |
| No bare module-level functions (singleton accessors exempt) | Module-level functions | [auto] `MODULE_FUNCTION` |
| Related free functions grouped on a `XxxHelper(ABC)` | Module-level functions | [judgment] |
| No module-level docstring | Docstrings | [auto] `MODULE_DOCSTRING` |
| Every class/function/method has a docstring | Docstrings | [auto] `MISSING_DOCSTRING` |
| Purpose line opens in the third-person singular present, not the imperative (`Reads`, not `Read`) | Docstrings | [auto] `IMPERATIVE_MOOD` |
| Comment opens in the third-person singular present, not the imperative (`Resets`, not `Reset`) | Comments | [auto] `IMPERATIVE_MOOD` |
| Depth scaled (obvious vs complex); `Args`/`Returns`/`Raises` correct; no history narration | Docstrings | [judgment] |
| Comment before each meaningful block; explains *why*; starts capital; no trailing period | Comments | [judgment] |
| No inline comment on a statement line | Comments | [auto] `INLINE_COMMENT` |
| No divider/banner comments | Comments | [auto] `BANNER_COMMENT` |
| All imports at top; none inline | Imports | [auto] `IMPORT_NOT_TOP`, `INLINE_IMPORT` |
| Import grouping order (stdlib / third-party / local) | Imports | [judgment] |
| Everything type-hinted | Type hints | [auto] `MISSING_HINT`, `MISSING_RETURN_HINT` |
| `typing` forms, not lowercase builtins or `\|` unions | Type hints | [auto] `LOWERCASE_GENERIC`, `PEP604_UNION` |
| Hints precise (`Dict[str, Any]`, not bare `Dict`); no string annotations | Type hints | [judgment] |
| No bare `*` keyword-only marker; variadics last | Function signatures | [auto] `KEYWORD_ONLY_STAR` |
| No multi-value tuple return; return a named immutable class (variadic `Tuple[X, ...]` exempt) | Return values | [auto] `MULTI_VALUE_RETURN` |
| f-strings, not `%` formatting | Style | [auto] `PERCENT_FORMAT` |
| Names by essence — full, self-explanatory words | (memory: essence naming) | [judgment] |
| Spec docs referenced by name only; no synthetic claim IDs | Project document references | [judgment] |

## Rules

- Audit only — never edit during steps 1–4. Editing happens after consent, in step 5.
- The mechanical pass is authoritative; never override a `check.py` finding by eye.
- `IMPERATIVE_MOOD` is a curated-verb heuristic (it matches a base-form verb at the start of a docstring or comment, including after a leading adverb). It has near-zero false positives but cannot know every verb — so a *clean* mechanical pass does not prove third-person. The judgment read-pass still scans every opening word, and a missed imperative means the verb belongs in `check.py`'s `IMPERATIVE_VERBS` set.
- Report exact `file:line`; a finding without a location is not actionable.
- When `/python` and this skill seem to disagree, `/python` wins — and flag the drift to the user.
- Keep the report concise: fact (`path:line`) → which rule → the fix. No essays.
