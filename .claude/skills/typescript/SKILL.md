---
name: typescript
description: Apply the project's TypeScript coding and documentation conventions. Auto-invoke when writing or editing TypeScript (.ts/.tsx) files — covers JSDoc, types, the Result pattern, wire-type provenance, imports, naming, and style.
---

# TypeScript Conventions

Apply when writing or editing `.ts` / `.tsx` files in this repo (today: the web client under `src/app/clients/web`). These are the conventions the existing code already follows — match them, don't invent a new style. The architectural rationale lives in `docs/arch/v1/WEB-CLIENT.md` and the client's `README.md`.

The compiler is the floor, not the ceiling: `tsconfig.json` runs `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noUnusedLocals/Parameters`, and `verbatimModuleSyntax`. Write code that passes `npm run typecheck` clean; everything below is what the compiler can't enforce.

> **Note on the Python conventions.** Two `/python` rules **invert** under TypeScript idiom and are flipped here on purpose: module-level functions are *welcome* (not grouped onto a helper class), and a file-level doc-comment header is *welcome* (Python forbids module docstrings). The reasons are spelled out in the relevant sections.

## Modules and files

- **No barrel `index.ts` / `index.tsx` files.** Import each module by its own path. Barrels hide the dependency graph, defeat tree-shaking, and invite import cycles. (This is the TS analog of the `/python` "no `__init__.py`" rule.)
- **Filenames carry meaning.** Component files (`.tsx` exporting a React component) are **PascalCase** — `ThemeToggle.tsx`, `CommandPalette.tsx`. Every other file — hooks, utilities, FSM, types, data sources, fixtures — is **kebab-case** — `use-auto-scroll-on-append.ts`, `document-tree.ts`, `rendered-account-stats-data-source.ts`. Never camelCase or snake_case.
- **One responsibility per file.** Pure helpers live in `src/lib/`, never colocated with the component that happens to use them first (see `document-tree.ts`: "the tree shape is data, not UI"). UI-view models live in `src/domain/models/rendering/` with the `Rendered*` prefix. Wire-type aliases live in `src/api/types.ts`.

## Functions and classes

TypeScript does **not** share Python's "no bare module-level functions" rule — the opposite. Pick the shape by what the code holds:

- **Module-level functions** are the default for pure, stateless logic and for React hooks. `flattenDfs(nodes)`, `useAutoScrollOnAppend(ref, key)`, `getJson<T>(path)` are all free functions and should stay that way. Do not wrap them in a class to "namespace" them.
- **Classes** carry state, identity, or a lifecycle: data sources (`RenderedAccountStatsDataSource`), the FSM building blocks (`State`, `Signal`, `Transition`, `StateMachine`), value objects with a controlled constructor (`Result`, `ErrorNo`), and `Error` subclasses (`AuthoringApiError`). When a class is the right shape, expose a private constructor + static factories where construction must stay consistent (see `Result.success` / `Result.error`), and prefer chainable `setX()` builders for declarative wiring (see `State.setHints().setConsumesPrompt()`).
- **Hooks** are module functions named `useX`, returning either a value or a small object. Keep React/Zustand/TanStack/FSM concerns on their own side of the boundary (see the four-layer split in `WEB-CLIENT.md`).
- **Module-level constants** stay module-level — a `SCREAMING_SNAKE_CASE` catalog (`SLASH_COMMANDS`) or a sentinel (`UNSET`). Document a constant with a `//` comment on the line above it.

## JSDoc

Use `/** ... */` JSDoc, not `//` line comments, for the doc of an entity. Scale depth to the entity (obvious vs. complex, below).

- **File-level header.** A non-trivial module opens with a `/** ... */` block (above the imports) stating the module's responsibility and any load-bearing "why" — see `result.ts`, `fsm.ts`, `use-auto-scroll-on-append.ts`. This is the TS counterpart of a one-paragraph orientation; unlike Python, it is encouraged. A component file may instead carry that doc on the component function itself (see `ThemeToggle.tsx`).
- **Every exported class, function, interface, and type alias carries a JSDoc** stating its responsibility — what it is and what it owns — in plain, fluent English. A near-empty marker interface (`interface ThemeToggleProps extends BaseProps {}`) needs none.
- **Purpose line.** One line stating what the entity does — `"Outcome of an operation: status, reason, and optional data payload."`, `"Single-button theme switcher."`. Describe purpose, not types — the signature already carries the types; never restate them in prose.
- **Obvious entities** (simple getters, trivial pass-throughs, one-line factories): the purpose line **alone**. Skip `@param`/`@returns` ceremony — it only adds noise.

  ```ts
  /** Successful Result with optional data. */
  static success<T = void>(data?: T): Result<T> { ... }
  ```

- **Non-trivial entities**: after the purpose line, document the parameters and the meaningful return. Prefer prose that names the arguments over a wall of `@param` tags when the function is small; reach for `@param` / `@returns` tags when there are several arguments or the contract is subtle.
- **Complex entities**: under the purpose line, add a short **algorithm outline** — the ordered steps — then the argument/return notes. `fsm.ts`'s `onSignal` and `use-auto-scroll-on-append.ts` are the model: they explain the *why* (the two-rAF reason, the IGNORED-vs-error routing) that the code can't.
- **Document interface members inline** with `/** ... */` above the field (see `SlashCommand`, `KeyHint`).
- Cross-reference other entities with `{@link Name}` (see `StateMachine.onSignal`).
- Present the **intended design as it stands now**. Do not narrate prior approaches, rejected alternatives, or iteration history.

## Comments

- Add a short comment before each meaningful block — every block longer than two lines and every subtle one-liner — hinting what it does and **why**. Never restate the obvious line by line.
- A comment sits on its **own line, directly above** the code it describes (see the `onMouseDown` comment in `ThemeToggle.tsx`). Avoid trailing same-line comments except for an unavoidable tooling pragma (`// eslint-disable-next-line ...`).
- Never use `//====`, `//----`, or any divider/banner comment.
- Dev-only logging is guarded — `if (import.meta.env.DEV) { console.debug(...) }`, with an `// eslint-disable-next-line no-console` immediately above the call (see `fsm.ts`'s `devLog`). Never leave a bare `console.log`.
- Present the final decision only. Do not record prior discussion, rejected options, or claim IDs (e.g. `INFER-`, `SAL-`) in code.

## Imports

- **All imports at the top of the file**, grouped: external packages (`react`, `zustand`, `@tanstack/...`) first, then internal `@/...` modules. The compiler keeps them top-level for static imports; use a dynamic `import()` only for genuine code-splitting.
- **Use `import type` for type-only imports** — `verbatimModuleSyntax` is on, so a value import of a type is an error. Mixed imports inline the modifier: `import { toRenderedAccountStats, type RenderedAccountStats } from "..."`.
- **Use the `@/` path alias**, not deep relative climbs. `import { postJson } from "@/api/http"`, never `../../../api/http`. A same-directory `./sibling` is fine.

## Types

- **Never `any`.** Use `unknown` at untyped boundaries and narrow with a type guard before use — see `http.ts` (`const data = (await res.json()) as unknown; if (isWireError(data)) ...`). The codebase has zero `any`.
- **Be precise.** `Dict`-style escape hatches (`Record<string, unknown>`) are a last resort; prefer a named shape. Mark immutable data `readonly` / `ReadonlyArray<T>` / `ReadonlySet<T>` (see `State`, `KeyHint`, `SlashCommand`).
- **`interface` for object shapes and component props; `type` for unions, aliases, and function types.** String-literal unions stand in for enums where the values are data (`SlashGroup`, `HintTone`); a real `enum` is reserved for a closed status set (`StateMachineResult`).
- **Wire types come from OpenAPI codegen — never hand-write a backend shape.** Regenerate `src/api/generated/openapi.ts` (`lets scr web codegen`) and add a friendly alias in `src/api/types.ts` (`export type DraftSpecItem = components["schemas"]["DraftSpecItem"]`). `types.ts` is the only module that touches the `components["schemas"]` indirection.
- **UI-view models are `Rendered*` types** in `src/domain/models/rendering/`; a data source is the only place that projects a wire type into its `Rendered*` shape (see `rendered-account-stats-data-source.ts`).
- **Explicit return types on exported functions** (`: Promise<RenderedAccountStats>`, `: void`). A React component may rely on the inferred JSX return.

## Result vs. throw

- **Known, anticipated failures flow as data** via `Result<T>` + `ErrorNo` (`src/lib/result.ts`) — mirroring the Python `lib/utils/result.py`. FSM `Condition.check` and `Action.execute` return `Result`; a use case that can fail in expected ways returns `Result`.
- **`throw` is reserved for genuinely unexpected bugs.** The HTTP layer is the boundary that turns transport failures into a thrown `AuthoringApiError` for TanStack Query's `onError`; above that boundary, prefer `Result`.
- Chain causes with `Result.fromResult(prev, error, reason)` so the underlying reason is preserved.

## Function signatures

TypeScript has no bare `*` marker, but the same spirit applies — keep the call site readable:

- **Few parameters stay positional.** Don't wrap a one- or two-argument function in an options object for ceremony.
- **Reach for an options object** when a function takes several parameters, or two of the same type that a caller could transpose, or any boolean that would read as a mystery `true` at the call site (avoid the boolean-trap; see `scrollBlockIntoView(scroller, el, { smooth: true })`).
- Required parameters first, then optional (`?`) ones, then a rest parameter last.

## Style

- Template literals, not string concatenation.
- Strict equality `===` / `!==` only — never `==` / `!=`.
- `const` by default; `let` only when reassigned; never `var`.
- Two-space indentation, double quotes, semicolons, trailing commas in multiline literals — match the surrounding file (the formatter settles the rest).
- American spelling — `initialize`, `color`, `normalize` — never the British `-ise` / `colour` forms.
- Tone: concise, precise, neutral.

## Naming

- **Name by essence — full, self-explanatory words.** `generationCompleter`, not `genCmpl`; `retryCount`, not `rc`. Clarity beats brevity. Never name a type by a generic suffix (`Data`, `Info`, `Manager`) when an essence name exists.
- PascalCase for components, classes, interfaces, type aliases, and enums. camelCase for variables, functions, and hooks (`useX`). `SCREAMING_SNAKE_CASE` for module-level constant catalogs and sentinels. Enum members are `SCREAMING_SNAKE_CASE`.

## When editing existing code

- Bring JSDoc and comments in line with these rules; improve docs rather than rewriting logic.
- Preserve behavior unless explicitly asked to change it.
- After editing, the change is not done until `npm run typecheck` (and any touched `vitest` suite) passes — run them through LETS (`./bin/lets devenv node npm --work-dir src/app/clients/web run typecheck`).

## Project document references

In JSDoc, comments, or code, reference the project's spec documents by name only (e.g. `PRD`, `SRS`). Do not link to specific sections or claim IDs — those churn.
