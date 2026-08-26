---
name: typescript-style
description: Use this skill to audit TypeScript code against the `/typescript` conventions and report every violation with its file:line and fix. Borrows the rule definitions from the `/typescript` skill — runs a deterministic checker for the mechanical rules plus a judgment read-pass for the rest. Do NOT auto-invoke; only run when explicitly called with /typescript-style.
argument-hint: "[paths or globs; defaults to changed .ts/.tsx files]"
allowed-tools: Read, Grep, Glob, Bash(./bin/lets devenv node npx:*), Bash(git --no-pager diff:*), Bash(git --no-pager status:*), Bash(find:*)
---

# TypeScript Style Audit (`/typescript-style`)

Check TypeScript code against the project conventions, then report each violation as `path:line — [RULE] — fix`. This skill **audits**; it does not rewrite code unless the user asks.

## Source of truth

The rules are **not** restated here — that would let them drift. There are exactly two authorities:

1. **`/typescript` skill** (`.claude/skills/typescript/SKILL.md`) — the prose definition of every convention. Read it before the judgment pass.
2. **`check.ts`** (next to this file) — the deterministic checker for the rules that can be decided mechanically.

Every check below maps to a `/typescript` section. Keep this skill and `check.ts` aligned with `/typescript`; if a rule there changes, update the corresponding check.

## Arguments

`$ARGUMENTS` — optional. Paths, directories, or globs to audit. If empty, default to the TypeScript files changed in the working tree (`git --no-pager diff --name-only` plus untracked `.ts` / `.tsx`). If there are none, ask the user what to audit.

## Procedure

1. **Scope.** Resolve `$ARGUMENTS` into a concrete file list. With no arguments, collect changed/untracked `.ts` / `.tsx` files from git. State the file list before checking.

2. **Mechanical pass.** Run the bundled checker over the scope. It runs through LETS via `vite-node`, which resolves the `typescript` compiler API from the web client's `node_modules`. Pass the checker by absolute path and the targets as repo-root-relative paths (the checker resolves them against the git root, so `git diff` paths work as-is):
   ```bash
   ./bin/lets devenv node npx --work-dir src/app/clients/web vite-node \
     "$(pwd)/.claude/skills/typescript-style/check.ts" -- <path> [<path> ...]
   ```
   It prints one line per violation (`path:line: [RULE] message`) and exits non-zero if any are found. LETS prepends a couple of banner lines and npm may print a `notice`; ignore those. The findings are authoritative — do not second-guess them.

3. **Judgment pass.** For each file, read it and check the rules `check.ts` cannot decide (see the checklist). Apply the `/typescript` definitions exactly; when a call is genuinely ambiguous, say so rather than inventing a verdict.

4. **Report.** Merge both passes and present findings grouped by file, each as `path:line — [RULE] — problem → fix`. Separate **must-fix** (clear rule breaches) from **consider** (judgment calls). End with a one-line count. If a file is clean, say so.

5. **Offer to fix.** Do not edit anything during the audit. After reporting, ask whether to apply the fixes. Fix only on consent, smallest-diff first, preserving behavior — then re-run the mechanical pass to confirm and, if any `.ts`/`.tsx` in the web client changed, `npm run typecheck`.

## Checklist

`[auto]` = decided by `check.ts`. `[judgment]` = read-pass against `/typescript`.

| Check | `/typescript` section | Pass |
| --- | --- | --- |
| No barrel `index.ts` / `index.tsx` | Modules and files | [auto] `BARREL_INDEX` |
| Filename casing — components PascalCase, else kebab-case; no camel/snake | Modules and files | [auto] `FILENAME_CASE` |
| Module functions for pure/stateless logic and hooks; classes only for state/identity/lifecycle | Functions and classes | [judgment] |
| Private constructor + static factories where construction must stay consistent | Functions and classes | [judgment] |
| File-level header on non-trivial modules; every exported class/fn/interface/type documented | JSDoc | [judgment] |
| Purpose line states responsibility, not types; depth scaled (obvious vs complex); no history narration | JSDoc | [judgment] |
| Interface members documented inline; `{@link}` for cross-refs | JSDoc | [judgment] |
| Comment before each meaningful block; explains *why*; on its own line above the code | Comments | [judgment] |
| No divider/banner comments | Comments | [auto] `BANNER_COMMENT` |
| Dev logging guarded behind `import.meta.env.DEV`; no bare `console.log` | Comments | [auto] `CONSOLE_LOG` |
| All imports at top; `@/` alias not deep relative climbs | Imports | [auto] `DEEP_RELATIVE_IMPORT` |
| `import type` for type-only imports (verbatimModuleSyntax) | Imports | [judgment] |
| Never `any`; `unknown` + narrowing at boundaries | Types | [auto] `EXPLICIT_ANY` |
| Precise types; `readonly` for immutable data; `interface` vs `type` used correctly | Types | [judgment] |
| Wire types from OpenAPI codegen aliased in `api/types.ts`; never hand-written | Types | [judgment] |
| UI-view models are `Rendered*` in `domain/models/rendering/` | Types | [judgment] |
| Known failures return `Result<T>`; `throw` reserved for unexpected bugs | Result vs. throw | [judgment] |
| Options object over boolean-trap / many positional params | Function signatures | [judgment] |
| Strict equality `===` / `!==` | Style | [auto] `LOOSE_EQUALITY` |
| `const` / `let`, never `var` | Style | [auto] `VAR_KEYWORD` |
| Template literals; double quotes; American spelling | Style | [judgment] |
| Names by essence — full, self-explanatory words | Naming (memory: essence naming) | [judgment] |
| Spec docs referenced by name only; no synthetic claim IDs | Project document references | [judgment] |

## Rules

- Audit only — never edit during steps 1–4. Editing happens after consent, in step 5.
- The mechanical pass is authoritative; never override a `check.ts` finding by eye.
- Report exact `file:line`; a finding without a location is not actionable.
- When `/typescript` and this skill seem to disagree, `/typescript` wins — and flag the drift to the user.
- Keep the report concise: fact (`path:line`) → which rule → the fix. No essays.
